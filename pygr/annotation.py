from __future__ import generators
from sequence import *
import classutil
import UserDict
import weakref


def getAnnotationAttr(self, attr):
    'forward attributes from slice object if available'
    return self.db.getSliceAttr(self.db.sliceDB[self.id], attr)


def annotation_repr(self):
    if self.annotationType is not None:
        title = self.annotationType
    else:
        title = 'annot'
    if self.orientation > 0:
        return '%s%s[%d:%d]' % (title, self.id, self.start, self.stop)
    else:
        return '-%s%s[%d:%d]' % (title, self.id, -self.stop, -self.start)


class AnnotationSeqDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return absoluteSlice(obj._anno_seq, obj._anno_start,
                             obj._anno_start + obj.stop)


class AnnotationSliceDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return relativeSlice(obj.pathForward.sequence, obj.start, obj.stop)


class AnnotationSeqtypeDescr(object):
    'get seqtype of the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return obj._anno_seq.seqtype()


class AnnotationSeq(SeqPath):
    'base class representing an annotation'
    start = 0
    step = 1
    orientation = 1

    def __init__(self, id, db, parent, start, stop):
        self.id = id
        self.db = db
        self.stop = stop - start
        self._anno_seq = parent
        self._anno_start = start
        self.path = self

    __getattr__ = getAnnotationAttr
    sequence = AnnotationSeqDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    _seqtype = AnnotationSeqtypeDescr()
    __repr__ = annotation_repr

    def __cmp__(self, other):
        if not isinstance(other, AnnotationSeq):
            return -1
        if cmp(self.sequence, other.sequence) == 0:
            if self.id == other.id and self.db is other.db:
                return cmp((self.start, self.stop), (other.start, other.stop))
        return NOT_ON_SAME_PATH

    def strslice(self, start, stop):
        raise ValueError('''this is an annotation, and you cannot get
                         a sequence string from it. Use its sequence attribute
                         to get a sequence object representing this interval.
                         ''')


class AnnotationSlice(SeqDBSlice):
    'represents subslice of an annotation'
    __getattr__=getAnnotationAttr
    sequence = AnnotationSliceDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    __repr__ = annotation_repr


class TranslationAnnotSeqDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return absoluteSlice(obj._anno_seq, obj._anno_start, obj._anno_stop)


class TranslationAnnotFrameDescr(object):
    """Get the frame of this protein translation, relative to original DNA."""

    def __get__(self, obj, objtype):
        orig = obj.pathForward.sequence
        if orig.orientation > 0:
            frame = (orig.start % 3) + 1
        else:
            return -((orig.start + 1) % 3 + 1)
        return frame


class TranslationAnnot(AnnotationSeq):
    'annotation representing aa translation of a given nucleotide interval'

    def __init__(self, id, db, parent, start, stop):
        AnnotationSeq.__init__(self, id, db, parent, start, stop)
        self.stop /= 3
        self._anno_stop = stop
    sequence = TranslationAnnotSeqDescr()
    frame = TranslationAnnotFrameDescr()
    _seqtype = PROTEIN_SEQTYPE

    def strslice(self, start, stop):
        'get the aa translation of our associated ORF'
        try:
            aa = self._translation
        except AttributeError:
            aa = self._translation = translate_orf(str(self.sequence))
        return aa[start:stop]


class TranslationAnnotSliceDescr(object):
    'get the sequence interval corresponding to this annotation'

    def __get__(self, obj, objtype):
        return relativeSlice(obj.pathForward.sequence, 3 * obj.start,
                             3 * obj.stop)


class TranslationAnnotSlice(AnnotationSlice):
    sequence = TranslationAnnotSliceDescr()
    frame = TranslationAnnotFrameDescr()


class AnnotationDB(object, UserDict.DictMixin):
    'container of annotations as specific slices of db sequences'

    def __init__(self, sliceDB, seqDB, annotationType=None,
                 itemClass=AnnotationSeq,
                 itemSliceClass=AnnotationSlice,
                 itemAttrDict=None, # GET RID OF THIS BACKWARDS-COMPATIBILITY KLUGE!!
                 sliceAttrDict=None, maxCache=None, autoGC=True,
                 checkFirstID=True, **kwargs):
        '''sliceDB must map identifier to a sliceInfo object;
        sliceInfo must have attributes: id, start, stop, orientation;
        seqDB must map sequence ID to a sliceable sequence object;
        sliceAttrDict gives optional dict of item attributes that
        should be mapped to sliceDB item attributes.
        maxCache specfies the maximum number of annotation objects
        to keep in the cache.'''
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
        self.itemClass = itemClass
        self.itemSliceClass = itemSliceClass
        self.sliceAttrDict = sliceAttrDict # USER-PROVIDED ALIASES
        if maxCache is not None:
            self.maxCache = maxCache
        if checkFirstID:
            try: # don't cache anything now; schema may change itemClass!
                k = iter(self).next() # get the first ID if any
                self.get_annot_obj(k, self.sliceDB[k]) # valid annotation?
            except KeyError: # a convenient warning to the user...
                raise KeyError('''\
cannot create annotation object %s; sequence database %s may not be correct'''
                               % (k, repr(seqDB), ))
            except StopIteration:
                pass # dataset is empty so there is nothing we can check...
    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(sliceDB=0, seqDB=0, annotationType=0, autoGC=0,
                        itemClass=0, itemSliceClass=0, sliceAttrDict=0,
                        maxCache=0)

    def __hash__(self):                 # @CTB unnecessary??
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)

    def __getitem__(self, k):
        'get annotation object by its ID'
        try: # GET FROM OUR CACHE
            return self._weakValueDict[k]
        except KeyError:
            pass
        return self.sliceAnnotation(k, self.sliceDB[k])

    def __setitem__(self, k, v):
        raise KeyError('''you cannot save annotations directly using annoDB[k]
                       = v. Instead, use annoDB.new_annotation(k,sliceInfo)
                       where sliceInfo provides a sequence ID, start, stop (and
                       any additional info desired), and will be saved directly
                       to the sliceDB.''')

    def getSliceAttr(self, sliceInfo, attr):
        try:
            k = self.sliceAttrDict[attr] # USE ALIAS IF PROVIDED
        except KeyError:
            return getattr(sliceInfo, attr) # GET ATTRIBUTE AS USUAL
        try: # REMAP TO ANOTHER ATTRIBUTE NAME
            return getattr(sliceInfo, k)
        except TypeError: # TREAT AS int INDEX INTO A TUPLE
            return sliceInfo[k]

    def get_annot_obj(self, k, sliceInfo):
        'create an annotation object based on the input sliceInfo'
        start = int(self.getSliceAttr(sliceInfo, 'start'))
        stop = int(self.getSliceAttr(sliceInfo, 'stop'))

        try:
            orientation = self.getSliceAttr(sliceInfo, 'orientation')
            orientation = int(orientation)
            if orientation < 0 and start >= 0:
                start, stop = (-stop, -start) # Negative-orientation coords
        except (AttributeError, IndexError):
            pass                        # ok if no orientation is specified.

        if start >= stop:
            raise IndexError('annotation %s has zero or negative length \
                             [%s:%s]!' % (k, start, stop))
        seq_id = self.getSliceAttr(sliceInfo, 'id')
        seq = self.seqDB[seq_id]
        return self.itemClass(k, self, seq, start, stop)

    def sliceAnnotation(self, k, sliceInfo, limitCache=True):
        'create annotation and cache it'
        a = self.get_annot_obj(k, sliceInfo)
        try: # APPLY CACHE SIZE LIMIT IF ANY
            if limitCache and self.maxCache < len(self._weakValueDict):
                self._weakValueDict.clear()
        except AttributeError:
            pass
        self._weakValueDict[k] = a # CACHE THIS IN OUR DICT
        return a

    def new_annotation(self, k, sliceInfo):
        'save sliceInfo to the annotation database \
                and return annotation object'
        # First, check if it gives a valid annotation
        a = self.sliceAnnotation(k, sliceInfo)
        try:
            # Now, save it in the slice database
            self.sliceDB[k] = sliceInfo
        except:
            try:
                # Delete it from cache
                del self._weakValueDict[k]
            except:
                pass
            raise
        self._wroteSliceDB = True
        return a

    def foreignKey(self, attr, k):
        'iterate over items matching specified foreign key'
        for t in self.sliceDB.foreignKey(attr, k):
            try: # get from cache if exists
                yield self._weakValueDict[t.id]
            except KeyError:
                yield self.sliceAnnotation(t.id, t)

    def __contains__(self, k):
        return k in self.sliceDB

    def __len__(self):
        return len(self.sliceDB)

    def __iter__(self):
        return iter(self.sliceDB) ########## ITERATORS

    def  keys(self):
        return self.sliceDB.keys()

    def iteritems(self):
        'uses maxCache to manage caching of annotation objects'
        for k, sliceInfo in self.sliceDB.iteritems():
            yield k, self.sliceAnnotation(k, sliceInfo)

    def itervalues(self):
        'uses maxCache to manage caching of annotation objects'
        for k, v in self.iteritems():
            yield v

    def items(self):
        'forces load of all annotation objects into cache'
        return [(k, self.sliceAnnotation(k, sliceInfo, limitCache=False))
                for (k, sliceInfo) in self.sliceDB.items()]

    def values(self):
        'forces load of all annotation objects into cache'
        return [self.sliceAnnotation(k, sliceInfo, limitCache=False)
                for (k, sliceInfo) in self.sliceDB.items()]

    def add_homology(self, seq, search, id=None, idFormat='%s_%d',
                     autoIncrement=False, maxAnnot=999999,
                     maxLoss=None, sliceInfo=None, **kwargs):
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
        if isinstance(search, str): # GET SEARCH METHOD
            search = getattr(self.seqDB, search)
        if isinstance(seq, str): # CREATE A SEQ OBJECT
            seq = Sequence(seq, str(id))
        al = search(seq, **kwargs) # RUN THE HOMOLOGY SEARCH
        if maxLoss is not None: # REQUIRE HIT BE AT LEAST A CERTAIN LENGTH
            kwargs['minAlignSize'] = len(seq)-maxLoss
        hits = al[seq].keys(**kwargs) # OBTAIN LIST OF HIT INTERVALS
        if len(hits) > maxAnnot:
            raise ValueError('too many hits for %s: %d' % (id, len(hits)))
        out = []
        i = 0
        k = id
        for ival in hits: # CREATE ANNOTATION FOR EACH HIT
            if len(hits)>1: # NEED TO CREATE AN ID FOR EACH HIT
                if autoIncrement:
                    k = len(self.sliceDB)
                else:
                    k = idFormat % (id, i)
                i += 1
            if sliceInfo is not None: # SAVE SLICE AS TUPLE WITH INFO
                a = self.new_annotation(k, (ival.id, ival.start, ival.stop)
                                        + sliceInfo)
            else:
                a = self.new_annotation(k, (ival.id, ival.start, ival.stop))
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
            print >>sys.stderr, '''
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
        raise NotImplementedError("nonsensical in AnnotationDB")

    def setdefault(self, k, d=None):
        raise NotImplementedError("nonsensical in AnnotationDB")

    def update(self, other):
        raise NotImplementedError("nonsensical in AnnotationDB")

    # these methods should not be implemented for read-only database.

    def clear(self):
        raise NotImplementedError("no deletions allowed")

    def pop(self):
        raise NotImplementedError("no deletions allowed")

    def popitem(self):
        raise NotImplementedError("no deletions allowed")


class AnnotationServer(AnnotationDB):
    'XMLRPC-ready server for AnnotationDB'
    xmlrpc_methods={'get_slice_tuple': 0, 'get_slice_items': 0,
                    'get_annotation_attr': 0, 'keys': 0,
                    '__len__': 0, '__contains__': 0}

    def get_slice_tuple(self, k):
        'get (seqID,start,stop) for a given key'
        try:
            sliceInfo = self.sliceDB[k]
        except KeyError:
            return '' # XMLRPC-acceptable failure code
        start = int(self.getSliceAttr(sliceInfo, 'start'))
        stop = int(self.getSliceAttr(sliceInfo, 'stop'))
        try:
            if int(self.getSliceAttr(sliceInfo, 'orientation')) < 0 \
               and start >= 0:
                start, stop = (-stop, -start) # Negative-orientation coords
        except AttributeError:
            pass
        return (self.getSliceAttr(sliceInfo, 'id'), start, stop)

    def get_slice_items(self):
        'get all (key,tuple) pairs in one query'
        l = []
        for k in self.sliceDB:
            l.append((k, self.get_slice_tuple(k)))
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

    def __setitem__(self, k, v):
        raise ValueError('XMLRPC client is read-only')

    def keys(self):
        return self.db.server.keys()

    def __iter__(self):
        return iter(self.keys())

    def items(self):
        return self.db.server.get_slice_items()

    def iteritems(self):
        return iter(self.items())

    def __len__(self):
        return self.db.server.__len__()

    def __contains__(self, k):
        return self.db.server.__contains__(k)


class AnnotationClient(AnnotationDB):
    'XMLRPC AnnotationDB client'

    def __init__(self, url, name, seqDB, itemClass=AnnotationSeq,
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
        if attr=='id':
            return sliceInfo[0]
        elif attr=='start':
            return sliceInfo[1]
        elif attr=='stop':
            return sliceInfo[2]
        elif attr=='orientation':
            raise AttributeError('ori not saved')
        else:
            v = self.server.get_annotation_attr(sliceInfo[0], attr)
            if v=='':
                raise AttributeError('this annotation has no attr: ' + attr)
            return v
