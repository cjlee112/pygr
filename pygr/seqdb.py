from __future__ import generators
import os
from sequence import *
from sqlgraph import *
import classutil
import UserDict
import weakref

class SQLSequence(SQLRow,SequenceBase):
    "Transparent access to a DB row representing a sequence; no caching."
    #@classmethod # decorators don't work prior to Python 2.4
    def _init_subclass(cls, db, **kwargs):
        db.seqInfoDict = db # db will act as its own seqInfoDict
        SQLRow._init_subclass(db=db, **kwargs)
    _init_subclass = classmethod(_init_subclass)
    def __init__(self, id):
        SQLRow.__init__(self, id)
        SequenceBase.__init__(self)
    def __len__(self):
        'simply returns self.length; use attrAlias dict to provide this attr!'
        return self.length
    def strslice(self,start,end):
        "Efficient access to slice of a sequence, useful for huge contigs"
        return self._select('substring(%s FROM %d FOR %d)'
                            %(self.db._attrSQL('seq'),start+1,end-start))

class DNASQLSequence(SQLSequence):
    _seqtype=DNA_SEQTYPE

class RNASQLSequence(SQLSequence):
    _seqtype=RNA_SEQTYPE

class ProteinSQLSequence(SQLSequence):
    _seqtype=PROTEIN_SEQTYPE


class SeqLenObject(object):
    def __init__(self, seqID, seqDB):
        self.id = seqID
        self.db = seqDB
        t = seqDB.seqLenDict[seqID]
        self.length = t[0]
        self.offset = t[1]

class SeqLenDictWrapper(object,UserDict.DictMixin):
    'seqInfoDict interface based on SequenceDB.seqLenDict'
    def __init__(self, db):
        self.seqDB = db
    def __getitem__(self, k):
        return SeqLenObject(k, self.seqDB)
    def __len__(self):
        return len(self.seqDB.seqLenDict)
    def __iter__(self):
        return iter(self.seqDB.seqLenDict)
    def keys(self):
        return self.seqDB.seqLenDict.keys()


class SeqLenDictSaver(object):
    'support for generic reading function'
    def __init__(self, reader):
        self.reader = reader
    def __call__(self, d, ifile, filename):
        offset = 0L
        ifile2 = file(filename+'.pureseq', 'w')
        try:
            for o in reader(ifile, filename): # run the reader as iterator
                d[o.id] = o.length,offset # save to seqlendict
                offset += o.length
                if o.length!=len(o.sequence):
                    raise ValueError('length does not match sequence: %s,%d'
                                     %(o.id,o.length))
                ifile2.write(o.sequence) # save to pureseq file
        finally:
            ifile2.close()

def store_seqlen_dict(d, filename, ifile=None, idFilter=None, reader=None):
    "store sequence lengths in a dictionary"
    if reader is not None: # run the user's custom reader() function.
        builder = SeqLenDictSaver(reader)
    else:
        try: # TRY TO USE OUR FAST COMPILED PARSER
            import seqfmt
            builder = seqfmt.read_fasta_lengths
        except ImportError:
            import sys
            raise ImportError('''
Unable to import extension module pygr.seqfmt that should be part of this package.
Either you are working with an incomplete install, or an installation of pygr
compiled with an incompatible Python version.  Please check your PYTHONPATH
setting and make sure it is compatible with this Python version (%d.%d).
When in doubt, rebuild your pygr installation using the
python setup.py build --force
option to force a clean install''' % sys.version_info[:2])
    if idFilter is not None: # need to wrap seqlendict to apply filter...
        class dictwrapper(object):
            def __init__(self, idFilter, d):
                self.d = d
                self.idFilter = idFilter
            def __setitem__(self, k, v):
                id = self.idFilter(k)
                self.d[id] = v
        d = dictwrapper(idFilter, d) # force builder to write to wrapper...
    if ifile is not None:
        builder(d, ifile, filename) # run the builder on our sequence set
    else:
        ifile = file(filename)
        try:
            builder(d, ifile, filename) # run the builder on our sequence set
        finally:
            ifile.close()
    
class FileDBSeqDescriptor(object):
    "Get sequence from a concatenated pureseq database for obj.id"
    def __get__(self,obj,objtype):
        return obj.strslice(0,obj.db.seqLenDict[obj.id][0])

class FileDBSequence(SequenceBase):
    seq=FileDBSeqDescriptor()
    __reduce__ = classutil.item_reducer
    #@classmethod # decorators don't work prior to Python 2.4
    def _init_subclass(cls, db, filepath, **kwargs):
        'open or build seqLenDict if needed'
        cls.db = db # all instances of this class are now bound to this database
        from dbfile import NoSuchFileError
        try: # THIS WILL FAIL IF SHELVE NOT ALREADY PRESENT...
            db.seqLenDict = classutil.open_shelve(filepath+'.seqlen','r') # READ-ONLY
        except NoSuchFileError: # BUILD: READ ALL SEQ LENGTHS, STORE IN PERSIST DICT
            db.seqLenDict = classutil.open_shelve(filepath+'.seqlen','n') # NEW EMPTY FILE
            import sys
            print >>sys.stderr,'Building sequence length index...'
            store_seqlen_dict(db.seqLenDict, filepath, **kwargs)
            db.seqLenDict.close() # FORCE IT TO WRITE DATA TO DISK
            db.seqLenDict = classutil.open_shelve(filepath+'.seqlen','r') # READ-ONLY
        db.seqInfoDict = SeqLenDictWrapper(db) # standard interface
    _init_subclass = classmethod(_init_subclass)
    def __init__(self,db,id):
        self.id=id
        SequenceBase.__init__(self)
        self.checkID() # RAISE KeyError IF THIS SEQ NOT IN db
    def __len__(self):
        "Use persistent storage of sequence lengths to avoid reading whole sequence"
        return self.db.seqLenDict[self.id][0]
    def checkID(self):
        'check whether this seq ID actually present in the DB, KeyError if not'
        return self.db.seqLenDict[self.id][0]
    def strslice(self,start,end,useCache=True):
        "Efficient access to slice of a sequence, useful for huge contigs"
        if useCache:
            try:
                return self.db.strsliceCache(self,start,end)
            except IndexError: # NOT FOUND IN CACHE
                pass # JUST USE OUR REGULAR METHOD
        try:
            ifile=self.db._pureseq
        except AttributeError:
            ifile=file(self.db.filepath+'.pureseq')
            self.db._pureseq=ifile
        ifile.seek(self.db.seqLenDict[self.id][1]+start)
        return ifile.read(end-start)
    

class SequenceDBInverse(object):
    'implements trivial inverse mapping seq --> id'
    def __init__(self,db):
        self.db=db
    def __getitem__(self,seq):
        return seq.pathForward.id
    def __contains__(self,seq):
        try:
            return seq.pathForward.db is self.db
        except AttributeError:
            return False

class SeqDBDescriptor(object):
    'forwards attribute requests to self.pathForward'
    def __init__(self,attr):
        self.attr=attr
    def __get__(self,obj,objtype):
        return getattr(obj.pathForward,self.attr) # RAISES AttributeError IF NONE

class SeqDBSlice(SeqPath):
    'JUST A WRAPPER FOR SCHEMA TO HANG SHADOW ATTRIBUTES ON...'
    id=SeqDBDescriptor('id')
    db=SeqDBDescriptor('db')

class SequenceDB(object, UserDict.DictMixin):
    itemSliceClass=SeqDBSlice # CLASS TO USE FOR SLICES OF SEQUENCE
    def __init__(self, autoGC=True, dbname='generic', **kwargs):
        "Initialize seq db from filepath or ifile"
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {}  # object cache
        self.autoGC = autoGC
        kwargs = kwargs.copy() # get a copy we can modify w/o side effects
        classutil.apply_itemclass(self, kwargs)
        kwargs['db'] = self
        classutil.get_bound_subclass(self, 'itemClass', dbname,
                                     subclassArgs=kwargs)
        self.set_seqtype()

    __getstate__ = classutil.standard_getstate ############### pickling methods
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(autoGC=0)

    __invert__ = classutil.standard_invert
    _inverseClass = SequenceDBInverse
    def __hash__(self):
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)
    def set_seqtype(self):
        'guess seqtype from 100 res of 1st seq if not already known'
        try: # if already known, no need to do anything
            return self._seqtype
        except AttributeError:
            pass
        try:
            ifile = file(self.filepath) # read one sequence to check its type
            try: # this only works for FASTA file...
                id,title,seq = read_fasta_one_line(ifile) 
                self._seqtype = guess_seqtype(seq) # record protein vs. DNA...
                return self._seqtype
            finally:
                ifile.close()
        except (IOError,AttributeError):
            pass
        for seqID in self: # get an iterator
            seq = self[seqID] # get the 1st sequence
            self._seqtype = guess_seqtype(str(seq[:100]))
            return self._seqtype
    _cache_max=10000
    def cacheHint(self, ivalDict, owner):
        'save a cache hint dict of {id:(start,stop)}; return reference owner'
        d={}
        for id,ival in ivalDict.items(): # BUILD THE CACHE DICTIONARY FOR owner
            if ival[0]<0: # FORCE IVAL INTO POSITIVE ORIENTATION
                ival=(-ival[1],-ival[0])
            if ival[1]-ival[0]>self._cache_max: # TRUNCATE EXCESSIVE LENGTH
                ival=(ival[0],ival[0]+self._cache_max)
            d[id]=[ival[0],ival[1]]
        try:
            self._cache[owner] = d # ADD TO EXISTING CACHE
        except AttributeError:
            self._cache = weakref.WeakKeyDictionary()  # AUTOMATICALLY REMOVE
            self._cache[owner] = d # FROM CACHE IF owner GOES OUT OF SCOPE
    def strsliceCache(self,seq,start,stop):
        'get strslice using cache hints, if any'
        try:
            cacheDict=self._cache
        except AttributeError:
            raise IndexError('no cache present')
        for owner,d in cacheDict.items():
            try:
                ival=d[seq.id]
            except KeyError:
                continue # NOT IN THIS CACHE, SO SKIP
            if start>=ival[0] and stop<=ival[1]: # CONTAINED IN ival
                try:
                    s=ival[2] # GET SEQ STRING FROM OUR CACHE
                except IndexError: # NEED TO CACHE ival SEQ STRING
                    s=seq.strslice(ival[0],ival[1],useCache=False)
                    ival.append(s)
                    try: # does owner want to reference this cached seq?
                        save_f = owner.cache_reference
                    except AttributeError:
                        pass # no, so nothing to do
                    else: # let owner control caching in our _weakValueDict
                        save_f(seq)
                return s[start-ival[0]:stop-ival[0]]
        raise IndexError('interval not found in cache')

    # these methods should all be implemented on all SeqDBs.
    def __iter__(self):
        return iter(self.seqInfoDict)
    def iteritems(self):
        for seqID in self:
            yield seqID,self[seqID]
    def __len__(self):
        "number of total entries in this database"
        return len(self.seqInfoDict)
    def __getitem__(self, seqID):
        "Get sequence matching this ID, using dict as local cache"
        try:
            return self._weakValueDict[seqID]
        except KeyError: # NOT FOUND IN DICT, SO CREATE A NEW OBJECT
            try:
                s = self.itemClass(self, seqID)
            except KeyError:
                raise KeyError, "no key '%s' in database %s" \
                      % (seqID, repr(self))
            self._weakValueDict[seqID] = s # CACHE IT
            return s
    def keys(self):
        return self.seqInfoDict.keys()
    def __contains__(self, key):
        return key in self.seqInfoDict
    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.filepath)
    def clear_cache(self):
        'empty the cache'
        self._weakValueDict.clear()

    # these methods should not be implemented for read-only database.
    clear = setdefault = pop = popitem = copy = update = \
            classutil.read_only_error

class SequenceFileDB(SequenceDB):
    itemClass = FileDBSequence # CLASS TO USE FOR SAVING EACH SEQUENCE
    _pickleAttrs = SequenceDB._pickleAttrs.copy()
    _pickleAttrs['filepath'] = 0
    def __init__(self, filepath=None, **kwargs):
        if filepath is None:
            try: # get filepath from ifile arg
                filepath = kwargs['ifile'].name
            except (KeyError, AttributeError):
                raise TypeError("unable to obtain a filename")
        self.filepath = classutil.SourceFileName(str(filepath))
        SequenceDB.__init__(self, filepath=filepath,
                            dbname=os.path.basename(filepath), **kwargs)
        try: # signal that we're done constructing, by closing the file object
            kwargs['ifile'].close()
        except (KeyError, AttributeError): pass

class BlastDB(SequenceFileDB):
    '''Deprecated interface provided for backwards compatibility.
    Provides blast() and megablast() methods for searching your seq db.
    Instead of this, you should use the blast.BlastMapping, which provides
    a graph interface to BLAST, or MegablastMapping for megablast.'''
    def __init__(self, filepath=None, blastReady=False, blastIndexPath=None,
                 blastIndexDirs=None, **kwargs):
        "format database and build indexes if needed. Provide filepath or file object"
        SequenceFileDB.__init__(self, filepath, **kwargs)
    def __repr__(self):
        return "<BlastDB '%s'>" % (self.filepath)
    def blast(self, seq, al=None, blastpath='blastall',
              blastprog=None, expmax=0.001, maxseq=None, verbose=True,
              opts='', **kwargs):
        'run blast with the specified parameters, return NLMSA alignment'
        blastmap = self.formatdb()
        return blastmap(seq, al, blastpath, blastprog, expmax, maxseq,
                        verbose, opts, **kwargs)
    def megablast(self,seq, al=None, blastpath='megablast', expmax=1e-20,
                  maxseq=None, minIdentity=None, maskOpts='-U T -F m',
                  rmPath='RepeatMasker', rmOpts='-xsmall',
                  verbose=True, opts='', **kwargs):
        'run megablast with the specified parameters, return NLMSA alignment'
        from blast import MegablastMapping
        blastmap = self.formatdb(attr='megablastMap', mapClass=MegablastMapping)
        return blastmap(seq, al, blastpath, expmax, maxseq, minIdentity,
                        maskOpts, rmPath, rmOpts, verbose, opts, **kwargs)
    def formatdb(self, filepath=None, attr='blastMap', mapClass=None):
        'create a blast mapping object if needed, and ensure it is indexed'
        try: # see if mapping object already exists
            blastmap = getattr(self, attr)
        except AttributeError:
            if mapClass is None: # default: BlastMapping
                from blast import BlastMapping
                mapClass = BlastMapping
            blastmap = mapClass(self)
            setattr(self, attr, blastmap) # re-use this in the future
        blastmap.formatdb(filepath) # create index file if not already present
        return blastmap

def getAnnotationAttr(self,attr):
    'forward attributes from slice object if available'
    return self.db.getSliceAttr(self.db.sliceDB[self.id], attr)

def annotation_repr(self):
    if self.annotationType is not None:
        title = self.annotationType
    else:
        title = 'annot'
    if self.orientation>0:
        return '%s%s[%d:%d]' % (title,self.id,self.start,self.stop)
    else:
        return '-%s%s[%d:%d]' % (title,self.id,-self.stop,-self.start)

class AnnotationSeqDescr(object):
    'get the sequence interval corresponding to this annotation'
    def __get__(self,obj,objtype):
        return absoluteSlice(obj._anno_seq,obj._anno_start,obj._anno_start+obj.stop)
class AnnotationSliceDescr(object):
    'get the sequence interval corresponding to this annotation'
    def __get__(self,obj,objtype):
        return relativeSlice(obj.pathForward.sequence,obj.start,obj.stop)
class AnnotationSeqtypeDescr(object):
    'get seqtype of the sequence interval corresponding to this annotation'
    def __get__(self,obj,objtype):
        return obj._anno_seq.seqtype()

class AnnotationSeq(SeqPath):
    'base class representing an annotation'
    start=0
    step=1
    orientation=1
    def __init__(self,id,db,parent,start,stop):
        self.id = id
        self.db = db
        self.stop = stop-start
        self._anno_seq = parent
        self._anno_start = start
        self.path = self
    __getattr__ = getAnnotationAttr
    sequence = AnnotationSeqDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    _seqtype = AnnotationSeqtypeDescr()
    __repr__ =  annotation_repr
    def __cmp__(self, other):
        if not isinstance(other, AnnotationSeq):
            return -1
        if cmp(self.sequence, other.sequence) == 0:
            if self.id == other.id and self.db is other.db:
                return cmp((self.start,self.stop),(other.start,other.stop))
        return NOT_ON_SAME_PATH
    
    def strslice(self,start,stop):
        raise ValueError('''this is an annotation, and you cannot get a sequence string from it.
Use its sequence attribute to get a sequence object representing this interval.''')


class AnnotationSlice(SeqDBSlice):
    'represents subslice of an annotation'
    __getattr__=getAnnotationAttr
    sequence = AnnotationSliceDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    __repr__ =  annotation_repr

class AnnotationDB(object, UserDict.DictMixin):
    'container of annotations as specific slices of db sequences'
    def __init__(self, sliceDB, seqDB, annotationType=None,
                 itemClass=AnnotationSeq,
                 itemSliceClass=AnnotationSlice,
                 itemAttrDict=None, # GET RID OF THIS BACKWARDS-COMPATIBILITY KLUGE!!
                 sliceAttrDict=None,maxCache=None, autoGC=True, **kwargs):
        '''sliceDB must map identifier to a sliceInfo object;
sliceInfo must have name,start,stop,ori attributes;
seqDB must map sequence ID to a sliceable sequence object;
sliceAttrDict gives optional dict of item attributes that
should be mapped to sliceDB item attributes.
maxCache specfies the maximum number of annotation objects to keep in the cache.'''
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {} # object cache
        self.autoGC = autoGC
        if sliceAttrDict is None:
            sliceAttrDict = {}
        if sliceDB is not None:
            self.sliceDB = sliceDB
        else: # NEED TO CREATE / OPEN A DATABASE FOR THE USER
            self.sliceDB = classutil.get_shelve_or_dict(**kwargs)
        self.seqDB = seqDB
        self.annotationType = annotationType
        self.itemClass=itemClass
        self.itemSliceClass=itemSliceClass
        self.sliceAttrDict=sliceAttrDict # USER-PROVIDED ALIASES
        if maxCache is not None:
            self.maxCache = maxCache
        try:
            sample_value = self.itervalues().next()
        except KeyError:
            raise KeyError('''\
 cannot create annotation object; sequence database %s may not be correct''' %\
                           (repr(seqDB),))
        except StopIteration:
            pass # dataset is empty so there is nothing we can check...
    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(sliceDB=0,seqDB=0,annotationType=0, autoGC=0,
                        itemClass=0,itemSliceClass=0,sliceAttrDict=0,maxCache=0)
    def __hash__(self):
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)
    def __getitem__(self,k):
        'get annotation object by its ID'
        try: # GET FROM OUR CACHE
            return self._weakValueDict[k]
        except KeyError:
            pass
        return self.sliceAnnotation(k,self.sliceDB[k])
    def __setitem__(self,k,v):
        raise KeyError('''you cannot save annotations directly using annoDB[k] = v
Instead, use annoDB.new_annotation(k,sliceInfo) where sliceInfo provides
a sequence ID, start, stop (and any additional info desired), and will be
saved directly to the sliceDB.''')
    def getSliceAttr(self,sliceInfo,attr):
        try:
            k = self.sliceAttrDict[attr] # USE ALIAS IF PROVIDED
        except KeyError:
            return getattr(sliceInfo,attr) # GET ATTRIBUTE AS USUAL
        try: # REMAP TO ANOTHER ATTRIBUTE NAME
            return getattr(sliceInfo,k)
        except TypeError: # TREAT AS int INDEX INTO A TUPLE
            return sliceInfo[k]
    def sliceAnnotation(self,k,sliceInfo,limitCache=True):
        'create annotation and cache it'
        start = int(self.getSliceAttr(sliceInfo,'start'))
        stop = int(self.getSliceAttr(sliceInfo,'stop'))
        try:
            if int(self.getSliceAttr(sliceInfo,'orientation'))<0 and start>=0:
                start,stop = (-stop,-start) # NEGATIVE ORIENTATION COORDINATES
        except AttributeError:
            pass
        if start>=stop:
            raise IndexError('annotation %s has zero or negative length [%s:%s]!'
                             %(k,start,stop))
        a = self.itemClass(k,self,self.seqDB[self.getSliceAttr(sliceInfo,'id')],start,stop)
        try: # APPLY CACHE SIZE LIMIT IF ANY
            if limitCache and self.maxCache<len(self._weakValueDict):
                self._weakValueDict.clear()
        except AttributeError:
            pass
        self._weakValueDict[k] = a # CACHE THIS IN OUR DICT
        return a
    def new_annotation(self,k,sliceInfo):
        'save sliceInfo to the annotation database and return annotation object'
        a = self.sliceAnnotation(k,sliceInfo) # 1st CHECK IT GIVES A VALID ANNOTATION
        try:
            self.sliceDB[k] = sliceInfo # NOW SAVE IT TO THE SLICE DATABASE
        except:
            try:
                del self._weakValueDict[k] # DELETE FROM CACHE
            except:
                pass
            raise
        self._wroteSliceDB = True
        return a
    def foreignKey(self,attr,k):
        'iterate over items matching specified foreign key'
        for t in self.sliceDB.foreignKey(attr,k):
            try: # get from cache if exists
                yield self._weakValueDict[t.id]
            except KeyError:
                yield self.sliceAnnotation(t.id,t)
    def __contains__(self, k): return k in self.sliceDB
    def __len__(self): return len(self.sliceDB)
    def __iter__(self): return iter(self.sliceDB) ########## ITERATORS
    def keys(self): return self.sliceDB.keys()
    def iteritems(self):
        'uses maxCache to manage caching of annotation objects'
        for k,sliceInfo in self.sliceDB.iteritems():
            yield k,self.sliceAnnotation(k,sliceInfo)
    def itervalues(self):
        'uses maxCache to manage caching of annotation objects'
        for k,v in self.iteritems():
            yield v
    def items(self):
        'forces load of all annotation objects into cache'
        return [(k,self.sliceAnnotation(k,sliceInfo,limitCache=False))
                for (k,sliceInfo) in self.sliceDB.items()]
    def values(self):
        'forces load of all annotation objects into cache'
        return [self.sliceAnnotation(k,sliceInfo,limitCache=False)
                for (k,sliceInfo) in self.sliceDB.items()]
    def add_homology(self,seq,search='blast',id=None,idFormat='%s_%d',
                     autoIncrement=False,maxAnnot=999999,
                     maxLoss=None,sliceInfo=None,**kwargs):
        'find homology in our seq db and add as annotations'
        try: # ENSURE THAT sliceAttrDict COMPATIBLE WITH OUR TUPLE FORMAT
            if self.sliceAttrDict['id'] != 0:
                raise KeyError
        except KeyError:
            sliceAttrDict['id'] = 0 # USE TUPLE AS OUR INTERNAL STANDARD FORMAT
            sliceAttrDict['start'] = 1
            sliceAttrDict['stop'] = 2
        if autoIncrement:
            id = len(self.sliceDB)
        elif id is None:
            id = seq.id
        if isinstance(search,str): # GET SEARCH METHOD
            search = getattr(self.seqDB,search)
        if isinstance(seq,str): # CREATE A SEQ OBJECT
            seq = Sequence(seq,str(id))
        al = search(seq,**kwargs) # RUN THE HOMOLOGY SEARCH
        if maxLoss is not None: # REQUIRE HIT BE AT LEAST A CERTAIN LENGTH
            kwargs['minAlignSize'] = len(seq)-maxLoss
        hits = al[seq].keys(**kwargs) # OBTAIN LIST OF HIT INTERVALS
        if len(hits)>maxAnnot:
            raise ValueError('too many hits for %s: %d' %(id,len(hits)))
        out = []
        i = 0
        k = id
        for ival in hits: # CREATE ANNOTATION FOR EACH HIT
            if len(hits)>1: # NEED TO CREATE AN ID FOR EACH HIT
                if autoIncrement:
                    k = len(self.sliceDB)
                else:
                    k = idFormat %(id,i)
                i += 1
            if sliceInfo is not None: # SAVE SLICE AS TUPLE WITH INFO
                a = self.new_annotation(k, (ival.id,ival.start,ival.stop)+sliceInfo)
            else:
                a = self.new_annotation(k, (ival.id,ival.start,ival.stop))
            out.append(a) # RETURN THE ANNOTATION
        return out
    def close(self):
        'if sliceDB needs to be closed, do it and return True, otherwise False'
        try:
            if self._wroteSliceDB:
                self.sliceDB.close()
                self._wroteSliceDB = False # DISK FILE IS UP TO DATE
                return True
        except AttributeError:
            pass
        return False
    def __del__(self):
        if self.close():
            import sys
            print >>sys.stderr,'''
WARNING: you forgot to call AnnotationDB.close() after writing
new annotation data to it.  This could result in failure to properly
store the data in the associated disk file.  To avoid this, we
have automatically called AnnotationDB.sliceDB.close() to write the data
for you, when the AnnotationDB was deleted.'''

    def clear_cache(self):
        'empty the cache'
        self._weakValueDict.clear()
    # not clear what this should do for AnnotationDB
    def copy(self):
        raise NotImplementedError, "nonsensical in AnnotationDB"
    def setdefault(self, k, d=None):
        raise NotImplementedError, "nonsensical in AnnotationDB"
    def update(self, other):
        raise NotImplementedError, "nonsensical in AnnotationDB"
    
    # these methods should not be implemented for read-only database.
    def clear(self):
        raise NotImplementedError, "no deletions allowed"
    def pop(self):
        raise NotImplementedError, "no deletions allowed"
    def popitem(self):
        raise NotImplementedError, "no deletions allowed"
            

class AnnotationServer(AnnotationDB):
    'XMLRPC-ready server for AnnotationDB'
    xmlrpc_methods={'get_slice_tuple':0,'get_slice_items':0,
                    'get_annotation_attr':0, 'keys':0,
                    '__len__':0, '__contains__':0}
    def get_slice_tuple(self, k):
        'get (seqID,start,stop) for a given key'
        try:
            sliceInfo = self.sliceDB[k]
        except KeyError:
            return '' # XMLRPC-acceptable failure code
        start = int(self.getSliceAttr(sliceInfo,'start'))
        stop = int(self.getSliceAttr(sliceInfo,'stop'))
        try:
            if int(self.getSliceAttr(sliceInfo,'orientation'))<0 and start>=0:
                start,stop = (-stop,-start) # NEGATIVE ORIENTATION COORDINATES
        except AttributeError:
            pass
        return (self.getSliceAttr(sliceInfo, 'id'), start, stop)
    def get_slice_items(self):
        'get all (key,tuple) pairs in one query'
        l = []
        for k in self.sliceDB:
            l.append((k,self.get_slice_tuple(k)))
        return l
    def get_annotation_attr(self, k, attr):
        'get the requested attribute of the requested key'
        try:
            sliceInfo = self.sliceDB[k]
        except KeyError:
            return ''
        try:
            return self.getSliceAttr(sliceInfo, attr)
        except AttributeError:
            return ''

class AnnotationClientSliceDB(dict):
    'proxy just queries the server'
    def __init__(self, db):
        self.db = db
        dict.__init__(self)
    def __getitem__(self, k):
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            t = self.db.server.get_slice_tuple(k)
            if t == '':
                raise KeyError('no such annotation: ' + str(k))
            dict.__setitem__(self, k, t)
            return t
    def __setitem__(self, k, v): raise ValueError('XMLRPC client is read-only')
    def keys(self): return self.db.server.keys()
    def __iter__(self): return iter(self.keys())
    def items(self): return self.db.server.get_slice_items()
    def iteritems(self): return iter(self.items())
    def __len__(self): return self.db.server.__len__()
    def __contains__(self, k): return self.db.server.__contains__(k)

class AnnotationClient(AnnotationDB):
    'XMLRPC AnnotationDB client'
    def __init__(self, url, name, seqDB,itemClass=AnnotationSeq,
                 itemSliceClass=AnnotationSlice, autoGC=True, **kwargs):
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {} # object cache
        self.autoGC = autoGC
        import coordinator
        self.server = coordinator.get_connection(url, name)
        self.url = url
        self.name = name
        self.seqDB = seqDB
        self.sliceDB = AnnotationClientSliceDB(self)
        self.itemClass = itemClass
        self.itemSliceClass = itemSliceClass
    def __getstate__(self):
        return dict(url=self.url, name=self.name, seqDB=self.seqDB,
                    autoGC=self.autoGC)
    def getSliceAttr(self, sliceInfo, attr):
        if attr=='id': return sliceInfo[0]
        elif attr=='start': return sliceInfo[1]
        elif attr=='stop': return sliceInfo[2]
        elif attr=='orientation': raise AttributeError('ori not saved')
        else:
            v = self.server.get_annotation_attr(sliceInfo[0], attr)
            if v=='':
                raise AttributeError('this annotation has no attr: ' + attr)
            return v


class SliceDB(dict):
    'associates an ID with a specific slice of a specific db sequence'
    def __init__(self,sliceDB,seqDB,leftOffset=0,rightOffset=0):
        '''sliceDB must map identifier to a sliceInfo object;
        sliceInfo must have name,start,stop,ori attributes;
        seqDB must map sequence ID to a sliceable sequence object'''
        dict.__init__(self)
        self.sliceDB=sliceDB
        self.seqDB=seqDB
        self.leftOffset=leftOffset
        self.rightOffset=rightOffset
    def __getitem__(self,k):
        try:
            return dict.__getitem__(self,k)
        except KeyError:
            pass
        sliceInfo=self.sliceDB[k]
        seq=self.seqDB[sliceInfo.name]
        myslice=seq[sliceInfo.start-self.leftOffset:sliceInfo.stop+self.rightOffset]
        if sliceInfo.ori<0:
            myslice= -myslice
        self[k]=myslice
        return myslice



class VirtualSeq(SeqPath):
    """Empty sequence object acts purely as a reference system.
    Automatically elongates if slice extends beyond current stop.
    This class avoids setting the stop attribute, taking advantage
    of SeqPath's mechanism for allowing a sequence to grow in length."""
    start=0
    step=1 # JUST DO OUR OWN SIMPLE INIT RATHER THAN CALLING SeqPath.__init__
    _seqtype=DNA_SEQTYPE # ALLOW THIS VIRTUAL COORD SYSTEM TO BE REVERSIBLE
    def __init__(self,id,length=1):
        self.path=self # DANGEROUS TO CALL SeqPath.__init__ WITH path=self!
        self._current_length=length # SO LET'S INIT OURSELVES TO AVOID THOSE PROBLEMS
        self.id=id
    def __getitem__(self,k):
        "Elongate if slice extends beyond current self.stop"
        if isinstance(k,types.SliceType):
            if k.stop>self._current_length:
                self._current_length=k.stop
        return SeqPath.__getitem__(self,k)
    def __len__(self):
        return self._current_length
    def strslice(self,start,end):
        "NO sequence access!  Raise an exception."
        raise ValueError('VirtualSeq has no actual sequence')

class VirtualSeqDB(dict):
    "return a VirtualSeq for any ID requested"
    def __getitem__(self,k):
        try: # IF WE ALREADY CREATED A SEQUENCE FOR THIS ID, RETURN IT
            return dict.__getitem__(self,k)
        except KeyError: # CREATE A VirtualSeq FOR THIS NEW ID
            s=VirtualSeq(k)
            self[k]=s
            return s


class PrefixDictInverse(object):
    def __init__(self,db):
        self.db=db
    def __getitem__(self,seq):
        try: # INSTEAD GET FROM seq.pathForward
            return self.db.dicts[seq.pathForward.db] \
                   +self.db.separator+str(seq.pathForward.id)
        except KeyError:
            try:
                if seq.pathForward._anno_seq in self:
                    raise KeyError('this annotation is not in the PrefixUnion, but its sequence is.  You ccan get that using its sequence attribute.')
            except AttributeError:
                pass
            raise KeyError('seq not in PrefixUnionDict')
    def __contains__(self,seq):
        try:
            return seq.pathForward.db in self.db.dicts
        except AttributeError:
            return False


class PrefixUnionMemberDict(dict):
    'd[prefix]=value; d[k] returns value if k is a member of prefix'
    def __init__(self,puDict,default=None,attrMethod=lambda x:x.pathForward.db):
        dict.__init__(self)
        self.puDict=puDict
        self._attrMethod=attrMethod
        if default is not None:
            self.default=default
    def possibleKeys(self):
        for k in self.puDict.prefixDict:
            yield k
    def __setitem__(self,k,v):
        try:
            dict.__setitem__(self,self.puDict.prefixDict[k],v)
        except KeyError:
            raise KeyError('key must be a valid union prefix string!')
    def __getitem__(self,k):
        try:
            return dict.__getitem__(self,self._attrMethod(k))
        except AttributeError:
            raise TypeError('wrong key type? _attrMethod() failed.')
        except KeyError:
            try: # RETURN A DEFAULT VALUE IF WE HAVE ONE
                return self.default
            except AttributeError:
                raise KeyError('key not a member of this union!')

class PUDSeqInfoDict(object,UserDict.DictMixin):
    'seqInfoDict interface based on SequenceDB.seqLenDict'
    def __init__(self, db):
        self.seqDB = db
    def __iter__(self):
        return iter(self.seqDB)
    def keys(self): return list(iter(self.seqDB))
    def iteritems(self):
        for p,d in self.seqDB.prefixDict.items():
            for seqID,info in d.seqInfoDict.iteritems():
                yield self.seqDB.format_id(p,seqID),info
    def __getitem__(self, k):
        prefix,seqID = self.seqDB.get_prefix_id(k)
        return self.seqDB.get_subitem(self.seqDB.prefixDict[prefix].seqInfoDict,
                                      seqID)
    def has_key(self, k):
        return k in self.seqDB

class PrefixUnionDict(object, UserDict.DictMixin):
    """union interface to a series of dicts, each assigned a unique prefix
       ID 'foo.bar' --> ID 'bar' in dict f associated with prefix 'foo'."""
    def __init__(self,prefixDict=None,separator='.',filename=None,
                 dbClass=BlastDB,trypath=None):
        '''can either be created using prefixDict, or a header file
        for a previously created PrefixUnionDict'''
        if filename is not None: # READ UNION HEADER FILE
            if trypath is None: # DEFAULT: LOOK IN SAME DIRECTORY AS UNION HEADER
                trypath=[os.path.dirname(filename)]
            ifile=file(filename)
            it=iter(ifile)
            separator=it.next().strip('\r\n') # DROP TRAILING CR
            prefixDict={}
            for line in it:
                prefix,filepath=line.strip().split('\t')[:2]
                try:
                    prefixDict[prefix] = \
                      dbClass(classutil.search_dirs_for_file(filepath, trypath))
                except IOError:
                    raise IOError('''unable to open database %s: check path or privileges.
Set trypath to give a list of directories to search.'''
                                  % filepath)
            ifile.close()
        self.separator=separator
        if prefixDict is not None:
            self.prefixDict=prefixDict
        else:
            self.prefixDict={}
        d={}
        for k,v in self.prefixDict.items():
            d[v]=k # CREATE A REVERSE MAPPING
        self.dicts=d
        self.seqInfoDict = PUDSeqInfoDict(self) # standard interface
    def format_id(self, prefix, seqID):
        return prefix + self.separator + seqID
    def get_prefix_id(self, k):
        'subdivide key into prefix, id using separator'
        try:
            t = k.split(self.separator)
        except AttributeError:
            raise KeyError('key should be string! ' + repr(k))
        l = len(t)
        if l == 2:
            return t
        elif l<2:
            raise KeyError('invalid id format; no prefix: '+k)
        else: # id CONTAINS separator CHARACTER?
            prefix = t[0] # ASSUME PREFIX DOESN'T CONTAIN separator
            id = k[len(prefix)+1:] # SKIP PAST PREFIX
            return prefix,id
    def get_subitem(self, d, seqID):
        try: # TRY TO USE int KEY FIRST
            return d[int(seqID)]
        except (ValueError,KeyError,TypeError): # USE DEFAULT str KEY
            try:
                return d[seqID]
            except KeyError:
                raise KeyError, "no key '%s' in %s" % (seqID, repr(d))
    def __getitem__(self,k):
        "for ID 'foo.bar', return item 'bar' in dict f associated with prefix 'foo'"
        prefix,seqID = self.get_prefix_id(k)
        try:
            return self.get_subitem(self.prefixDict[prefix], seqID)
        except KeyError, e:
            #msg = ("no key '%s' in %s because " % (k,repr(self))) + str(e)
            raise KeyError("no key '%s' in %s" % (k,repr(self)))

    def __contains__(self,k):
        "test whether ID in union; also check whether seq key in one of our DBs"
        if isinstance(k,str):
            try:
                (prefix,id) = self.get_prefix_id(k)
                return id in self.prefixDict[prefix]
            except KeyError:
                return False
        else: # TREAT KEY AS A SEQ, CHECK IF IT IS FROM ONE OF OUR DB
            try:
                db=k.pathForward.db
            except AttributeError:
                raise AttributeError('key must be a sequence with db attribute!')
            return db in self.dicts

    def has_key(self,k):
        return self.__contains__(k)

    def __iter__(self):
        "generate union of all dicts IDs, each with appropriate prefix."
        for p,d in self.prefixDict.items():
            for id in d:
                yield self.format_id(p, id)

    def keys(self):
        return list(self.iterkeys())

    def iterkeys(self):
        return iter(self)
    
    def iteritems(self):
        "generate union of all dicts items, each id with appropriate prefix."
        for p,d in self.prefixDict.items():
            for id,seq in d.iteritems():
                yield self.format_id(p, id),seq

    def getName(self,path):
        "return fully qualified ID i.e. 'foo.bar'"
        path=path.pathForward
        return self.dicts[path.db]+self.separator+path.id

    def newMemberDict(self,**kwargs):
        'return a new member dictionary (empty)'
        return PrefixUnionMemberDict(self,**kwargs)

    def writeHeaderFile(self,filename):
        'save a header file for this union, to reopen later'
        ifile=file(filename,'w')
        print >>ifile,self.separator
        for k,v in self.prefixDict.items():
            try:
                print >>ifile,'%s\t%s\t' %(k,v.filepath)
            except AttributeError:
                raise AttributeError('seq db %s has no filepath; you can save this to pygr.Data but not to a text HeaderFile!' % k)
        ifile.close()
    __invert__ = classutil.standard_invert
    _inverseClass = PrefixDictInverse
    def __len__(self):
        "number of total entries in this database"
        n=0
        for db in self.dicts:
            n+=len(db)
        return n
    def cacheHint(self, ivalDict, owner=None):
        'save a cache hint dict of {id:(start,stop)}; return reference owner'
        d={}
        for id,ival in ivalDict.items(): # EXTRACT SEPARATE SUBDICT FOR EACH prefix
            prefix=id.split(self.separator)[0] # EXTRACT PREFIX, SEQID
            seqID=id[len(prefix)+1:]
            try: # SAVE TO SEPARATE DICTIONARY FOR EACH prefix
                d[prefix][seqID]=ival
            except KeyError:
                d[prefix]={seqID:ival}
        for prefix,seqDict in d.items():
            try:
                m=self.prefixDict[prefix].cacheHint
            except AttributeError: # CAN'T cacheHint, SO JUST IGNORE
                pass
            else:
                # pass cache hint down to subdictionary
                return m(seqDict, owner)

    # not clear what this should do for PrefixUnionDict
    def copy(self):
        raise NotImplementedError, "nonsensical in PrefixUnionDict"
    def setdefault(self, k, d=None):
        raise NotImplementedError, "nonsensical in PrefixUnionDict"
    def update(self, other):
        raise NotImplementedError, "nonsensical in PrefixUnionDict"
    
    # these methods should not be implemented for read-only database.
    def clear(self):
        raise NotImplementedError, "no deletions allowed"
    def pop(self):
        raise NotImplementedError, "no deletions allowed"
    def popitem(self):
        raise NotImplementedError, "no deletions allowed"

class PrefixDictInverseAdder(PrefixDictInverse):
    def getName(self,seq):
        'also handle seq with no db attribute...'
        try:
            return PrefixDictInverse.__getitem__(self,seq)
        except AttributeError: # NO db?  THEN TREAT AS A user SEQUENCE
            userID='user'+self.db.separator+seq.pathForward.id
            s=self.db[userID] # MAKE SURE ALREADY IN user SEQ DICTIONARY
            return userID # ALREADY THERE
                
    def __getitem__(self,seq):
        'handles optional mode that adds seq if not already present'
        try:
            return self.getName(seq)
        except KeyError:
            if self.db.addAll:
                self.db+=seq # FORCE self.db TO ADD THIS TO ITS INDEX
                return self.getName(seq) # THIS SHOULD SUCCEED NOW...
            else: # OTHERWISE JUST RE-RAISE THE ORIGINAL EXCEPTION
                raise


class SeqPrefixUnionDict(PrefixUnionDict):
    'adds method for easily adding a seq or its database to the PUD'
    def __init__(self,addAll=False,**kwargs):
        PrefixUnionDict.__init__(self,**kwargs)
        self._inverse=PrefixDictInverseAdder(self)
        self.addAll=addAll # FORCE AUTOMATIC ADDING

    def __iadd__(self,k):
        'add a sequence or database to prefix-union, with a unique prefix'
        if k in (~self): # k ALREADY IN ONE OF OUR DATABASES
            return self
        try: # OK, JUST ADD ITS DATABASE!
            db=k.db # GET DB DIRECTLY FROM SeqPath object
        except AttributeError:
            try:
                db=k.pathForward.db # GET DB FROM pathForward
            except AttributeError: # USER SEQUENCE, NOT FROM ANY CONTAINER?!
                try: # SAVE TO user SEQUENCE DICT
                    d=self.prefixDict['user']
                except KeyError: # NEED TO CREATE A user DICT
                    d=KeepUniqueDict()
                    self.prefixDict['user']=d
                    self.dicts[d]='user'
                d[k.pathForward.id]=k.pathForward # ADD TO user DICTIONARY
                return self
        # db MUST BE A SEQ DATABASE STYLE DICT...
        if db in self.dicts: # ALREADY IS ONE OF OUR DATABASES
            return self # NOTHING FURTHER TO DO
        try: # USE LAST FIELD OF ITS persistent_id
            id=db._persistent_id.split('.')[-1]
        except AttributeError:
            try: # TRY TO GET THE NAME FROM filepath ATTRIBUTE
                id = os.path.basename(db.filepath).split('.')[0]
                if id in self.prefixDict:
                    raise ValueError('''
It appears that two different sequence databases are being
assigned the same prefix ("%s", based on the filepath)!
For this reason, the attempted automatic construction of
a PrefixUnionDict for you cannot be completed!
You should instead construct a PrefixUnionDict that assigns
a unique prefix to each sequence database, and supply it
directly as the seqDict argument to the NLMSA constructor.''' % id)
            except AttributeError:
                id = 'noname%d'%len(self.dicts) # CREATE AN ARBITRARY UNIQUE ID
        self.prefixDict[id]=db
        self.dicts[db]=id
        return self # IADD MUST RETURN SELF!
        

class BlastDBXMLRPC(BlastDB):
    'XMLRPC server wrapper around a standard BlastDB'
    xmlrpc_methods = dict(getSeqLen=0, strslice=0, getSeqLenDict=0,
                          get_db_size=0, get_seqtype=0)
    def getSeqLen(self,id):
        'get sequence length, or -1 if not found'
        try:
            return len(self[id]) 
        except KeyError:
            return -1  # SEQUENCE OBJECT DOES NOT EXIST
    def getSeqLenDict(self):
        'return seqLenDict over XMLRPC'
        d = {}
        for k,v in self.seqLenDict.items():
            d[k] = v[0],str(v[1]) # CONVERT TO STR TO ALLOW OFFSET>2GB
        return d # XML-RPC CANNOT HANDLE INT > 2 GB, SO FORCED TO CONVERT...
    def get_db_size(self):
        return len(self)
    def strslice(self,id,start,stop):
        'return string sequence for specified interval in the specified sequence'
        if start<0: # HANDLE NEGATIVE ORIENTATION
            return str((-(self[id]))[-stop:-start])
        else: # POSITIVE ORIENTATION
            return str(self[id][start:stop])
    def get_seqtype(self):
        return self._seqtype



    
class XMLRPCSequence(SequenceBase):
    "Represents a sequence in a blast database, accessed via XMLRPC"
    #@classmethod # decorators don't work prior to Python 2.4
    def _init_subclass(cls, db, url, name, **kwargs):
        import coordinator
        db.server = coordinator.get_connection(url,name)
        db.url = url
        db.name = name
        db.seqInfoDict = SeqLenDictWrapper(db)
    _init_subclass = classmethod(_init_subclass)
    def __init__(self, db, id):
        self.length = db.server.getSeqLen(id)
        if self.length<=0:
            raise KeyError('%s not in this database' % id)
        self.db = db
        self.id = id
        SequenceBase.__init__(self)
    def strslice(self,start,end,useCache=True):
        "XMLRPC access to slice of a sequence"
        if useCache:
            try:
                return self.db.strsliceCache(self,start,end)
            except IndexError: # NOT FOUND IN CACHE
                pass # JUST USE OUR REGULAR XMLRPC METHOD
        return self.db.server.strslice(self.id,start,end) # GET FROM XMLRPC
    def __len__(self):
        return self.length

class XMLRPCSeqLenDescr(object):
    'descriptor that returns dictionary of remote server seqLenDict'
    def __init__(self,attr):
        self.attr = attr
    def __get__(self,obj,objtype):
        'only called if attribute does not already exist. Saves result as attribute'
        d = obj.server.getSeqLenDict()
        for k,v in d.items():
            d[k] = v[0],int(v[1]) # CONVERT OFFSET STR BACK TO INT
        obj.__dict__[self.attr] = d # PROVIDE DIRECTLY TO THE __dict__
        return d

class XMLRPCSequenceDB(SequenceDB):
    'XMLRPC client: access sequence database over XMLRPC'
    itemClass = XMLRPCSequence # sequence storage interface
    seqLenDict = XMLRPCSeqLenDescr('seqLenDict') # INTERFACE TO SEQLENDICT
    def __getstate__(self): # DO NOT pickle self.itemClass! We provide our own.
        return dict(url=self.url, name=self.name) # just need XMLRPC info
    def __len__(self):
        return self.server.get_db_size()
    def __contains__(self, k):
        if self.server.getSeqLen(k)>0:
            return True
        else:
            return False
    def set_seqtype(self):
        'efficient way to determine sequence type of this database'
        try: # if already known, no need to do anything
            return self._seqtype
        except AttributeError:
            self._seqtype = self.server.get_seqtype()
            return self._seqtype

def fastaDB_unpickler(klass,srcfile,kwargs):
    if klass is BlastDB or klass == 'BlastDB':
        klass = BlastDB
    else:
        raise ValueError('Caught attempt to unpickle untrusted class %s' %klass)
    o = klass(srcfile,**kwargs) # INITIALIZE, BUILD INDEXES, ETC.
    o._saveLocalBuild = True # MARK FOR LOCAL PYGR.DATA SAVE
    return o
fastaDB_unpickler.__safe_for_unpickling__ = 1
class FastaDB(object):
    'unpickling this object will attempt to construct BlastDB from filepath'
    def __init__(self,filepath,klass=BlastDB,**kwargs):
        self.filepath = filepath
        self.klass = klass
        self.kwargs = kwargs
    def __reduce__(self):
        return (fastaDB_unpickler,(self.klass,self.filepath,self.kwargs))
