"""
@CTB

discuss seqLenDict, seqInfoDict.

add a close method to SequenceFileDB?
is ifile necessary?
set_seqtype
 - code chunk necessity?? refactor/remove.
 - rename to _
 - stop returning
make _cacheMax configurable as a kwarg?
is idfilter used at all?

PrefixUnionDict __contains__ is inconsistent with getitem
PUD 'trypath' => 'trypaths'?
PUD remove 'newMemberDict' function? not used anywhere (but in docs);
   what about associated PrefixUnionDictMember class??
   for PUDMember class, '.default' handling...?
PUD remove 'writeHeaderFile' function? not used anywhere (but in docs)

PrefixDictInverse KeyError abstraction violation

what about adding __iadd__ directly into PUD?
SeqPrefixUnionDict: if statement can never be reached?

should we explicitly test seqInfoDict interfaces for the various seqdb
   implementations?  what uses them, anyway -- NLMSAs, right? anything else?

use logging instead of sys.stderr.write.

could delegate inverse to actual class method; why implement it the way it is,
   in separate classes?

should Sequence classes be private (_)?
SQLsequence stuff => another file (e.g. sqlgraph)?

class/inheritance hierarchy naming..?
    class names in this file still confuse me!

doctests & examples
-------------------

intro:
 - loading a FASTA file
 - using a PUD
   + combining dbs, etc.
   + inverse
 
advanced:
 - writing your own sequence reader
 - extending to your own backend

prefixUnionDict defaulted to BlastDB; correct or not?  (I changed.)

"""

from __future__ import generators
import sys
import os
from sequence import *                  # @CTB
from sqlgraph import *                  # @CTB
import classutil
import UserDict
import weakref
from annotation import AnnotationDB, AnnotationSeq, AnnotationSlice, \
     AnnotationServer, AnnotationClient

from dbfile import NoSuchFileError

####
#
# SequenceDB and associated support classes.
#

class _SequenceDBInverse(object):
    """Implements __inverse__ on SequenceDB objects, returning seq name."""
    def __init__(self, db):
        self.db = db
    def __getitem__(self, seq):
        return seq.pathForward.id
    def __contains__(self, seq):
        try:
            return seq.pathForward.db is self.db
        except AttributeError:
            return False

class SequenceDB(object, UserDict.DictMixin):
    """Base class for sequence databases.

    SequenceDB provides a few basic (base) behaviors:
      - dict-like interface to sequence objects each with an ID
      - the ~ (invert) operator returns an 'inverted' database, which is a
        dict-like object that returns sequence names when given a sequence.
      - weakref-based automatic flushing of seq objects no longer in use;
        use autoGC=0 to turn this off.
      - cacheHint() system for caching a given set of sequence
        intervals associated with an owner object, which are flushed
        from cache if the owner object is garbage-collected.

    """
    # class to use for sequence slices; see sequence.SeqPath.classySlice.
    itemSliceClass=SeqDBSlice
    
    # pickling methods & what attributes to pickle.
    __getstate__ = classutil.standard_getstate
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(autoGC=0)

    # define ~ (invert) operator to return ... @CTB document.
    __invert__ = classutil.standard_invert
    _inverseClass = _SequenceDBInverse
    
    def __init__(self, autoGC=True, dbname='__generic__', **kwargs):
        "Initialize seq db from filepath or ifile"
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {}    # object cache @CTB not tested
        self.autoGC = autoGC

        # override itemClass and itemSliceClass if specified
        self.itemClass = kwargs.get('itemClass', self.itemClass)
        self.itemSliceClass = kwargs.get('itemSliceClass', self.itemSliceClass)

        # get a copy we can modify w/o side effects and bind itemClass.
        kwargs = kwargs.copy() 
        kwargs['db'] = self
        classutil.get_bound_subclass(self, 'itemClass', dbname,
                                     subclassArgs=kwargs)
        
        # guess the sequence type
        self.set_seqtype()

    def __hash__(self):
        """Define a hash function to allow this object to be used as a key."""
        return id(self)
    
    def set_seqtype(self):
        """Guess the seqtype from 100 chars of 1st seq if not already known.

        @CTB why return seqtype??  Used only in this one function.  Rename _?
        """
        try: # if already known, no need to do anything
            return self._seqtype
        except AttributeError:
            pass
        try:                                  # @CTB is this necessary?
            ifile = file(self.filepath, 'rU') # read one sequence to check type
            try: # this only works for FASTA file...
                id,title,seq = read_fasta_one_line(ifile) 
                self._seqtype = guess_seqtype(seq) # record protein vs. DNA...
                return self._seqtype
            finally:
                ifile.close()
        except (IOError,AttributeError): # @CTB ??
            pass
        for seqID in self: # get an iterator  @CTB untested
            seq = self[seqID] # get the 1st sequence
            ch100 = str(seq[:100])
            self._seqtype = guess_seqtype(ch100)
            return self._seqtype
    _cache_max=10000                    # @CTB move? make settable?
    def cacheHint(self, ivalDict, owner):
        """Save a cache hint dict: {id: (start, stop)}.

        @CTB document!
        """
        d={}
        # @CTB refactor, test
        for id, ival in ivalDict.items(): # BUILD THE CACHE DICTIONARY FOR owner
            if ival[0] < 0: # FORCE IVAL INTO POSITIVE ORIENTATION
                ival=(-ival[1], -ival[0])        # @CTB untested
            if ival[1]-ival[0] > self._cache_max: # TRUNCATE EXCESSIVE LENGTH
                ival=(ival[0], ival[0] + self._cache_max) # @CTB untested
            d[id]=[ival[0], ival[1]]
        try:
            self._cache[owner] = d # ADD TO EXISTING CACHE
        except AttributeError:
            self._cache = weakref.WeakKeyDictionary()  # AUTOMATICALLY REMOVE
            self._cache[owner] = d # FROM CACHE IF owner GOES OUT OF SCOPE
    def strsliceCache(self, seq, start, stop):
        """Get strslice using cache hints, if any available."""
        try:
            cacheDict=self._cache
        except AttributeError:
            raise IndexError('no cache present')
        for owner, d in cacheDict.items():
            try:
                ival = d[seq.id]
            except KeyError:
                continue # NOT IN THIS CACHE, SO SKIP  @CTB untested
            ival_start, ival_stop = ival[:2]
            if start >= ival_start and stop <= ival_stop: # CONTAINED IN ival
                if len(ival) != 3:
                    s = seq.strslice(ival_start, ival_stop, useCache=False)
                    ival.append(s)
                    try: # does owner want to reference this cached seq?
                        save_f = owner.cache_reference
                    except AttributeError:
                        pass # no, so nothing to do
                    else: # let owner control caching in our _weakValueDict
                        save_f(seq)     # # @CTB untested
                else:
                    s = ival[2] # GET SEQ STRING FROM OUR CACHE
                return s[start - ival_start:stop - ival_stop]
        raise IndexError('interval not found in cache') # @CTB untested

    # these methods should all be implemented on all SequenceDBs.
    def __iter__(self):
        return iter(self.seqInfoDict)
    
    def iteritems(self):
        for seqID in self:
            yield seqID,self[seqID]
            
    def __len__(self):
        return len(self.seqInfoDict)
    
    def __getitem__(self, id):
        """Retrieve sequence by id, using cache if available."""
        s = self._weakValueDict.get(id)
        if s is None:                   # not in cache?  try loading.
            try:
                s = self.itemClass(self, id)
            except KeyError:
                raise KeyError, "no key '%s' in database %s" % (id, repr(self))
            self._weakValueDict[id] = s # save in cache.
        return s
    
    def keys(self):
        return self.seqInfoDict.keys()
    
    def __contains__(self, key):
        return key in self.seqInfoDict
    
    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.filepath)
    
    def clear_cache(self):
        """Empty the cache."""
        self._weakValueDict.clear()

    # these methods should not be implemented for read-only database.
    clear = setdefault = pop = popitem = copy = update = \
            classutil.read_only_error

####
#
# FileDBSequence and SequenceFileDB, and associated support classes.
#

class _FileDBSeqDescriptor(object):
    """Descriptor to retrieve entire sequence from seqLenDict."""
    def __get__(self, obj, objtype):
        length = obj.db.seqLenDict[obj.id][0]
        return obj.strslice(0, length)

class FileDBSequence(SequenceBase):
    """Default sequence object for file-based storage mechanism.

    By default, FileDBSequence uses a seqLenDict, a.k.a. a shelve
    index of sequence lengths and offsets, to retrieve sequence slices
    with fseek.  Thus entire chromosomes (for example) do not have to
    be loaded to retrieve a subslice.

    See SequenceFileDB for the associated database class.

    In general, you should not create object from this class directly;
    retrieve them from SequenceFileDB objects, instead.

    """
    seq = _FileDBSeqDescriptor()        # dynamically retrieve 'seq'.
    __reduce__ = classutil.item_reducer # for pickling purposes.

    def _init_subclass(cls, db, filepath, **kwargs):
        """Main initialization function (class method).

        Initialize our indexes if needed, and provide db with a
        seqInfoDict attribute for looking up length and offset info.
        Open or build seqLenDict if needed

        Called by classutil.get_bound_subclass in SequenceDB.

        @CTB where does kwargs come from?
        @CTB point out pass into _store_seqlen_dict...

        """
        # bind all instances of this class to this database
        cls.db = db
        fullpath = filepath + '.seqlen'
        
        # build the seqLenDict if it doesn't already exist
        try:                            # @CTB refactor; make testable?
            seqLenDict = classutil.open_shelve(fullpath, 'r')
        except NoSuchFileError:
            seqLenDict = classutil.open_shelve(fullpath, 'n')
            print >>sys.stderr,'Building sequence length index...' # @CTB log?
            _store_seqlen_dict(seqLenDict, filepath, **kwargs)
            # force a flush; reopen in read-only mode.
            seqLenDict.close() 
            seqLenDict = classutil.open_shelve(fullpath, 'r')
            
        db.seqLenDict = seqLenDict
        db.seqInfoDict = _SeqLenDictWrapper(db) # standard interface
    _init_subclass = classmethod(_init_subclass)
    
    def __init__(self, db, id):
        self.id = id
        SequenceBase.__init__(self)
        if self.id not in self.db.seqLenDict:
            raise KeyError('sequence %s not in db %s' % (self.id, self.db))
                           
    def __len__(self):
        """Unpack this sequence's length from the seqLenDict."""
        return self.db.seqLenDict[self.id][0]
    
    def strslice(self, start, end, useCache=True):
        """Access slice of a sequence efficiently, using seqLenDict info."""
        if useCache:                    # If it's in the cache, use that!
            try:
                return self.db.strsliceCache(self, start, end)
            except IndexError:
                pass

        # The requested slice is not in the cache, or there is no
        # cache; retrieve sequence from the .pureseq file based on
        # seqLenDict information.
        try:
            ifile=self.db._pureseq      # @CTB refactor - move to db?
        except AttributeError:
            fullpath = self.db.filepath + '.pureseq'
            ifile = file(fullpath, 'rb')
            self.db._pureseq = ifile

        # Now, read in the actual slice.
        offset = self.db.seqLenDict[self.id][1]
        ifile.seek(offset + start)
        return ifile.read(end - start)


class SequenceFileDB(SequenceDB):
    """Main class for file-based storage of a sequence database.

    By default, uses FileDBSequence, which implements the seqLenDict
    method of sequence storage & retrieval.  By specifying a different
    itemClass, you can change that behavior.

    Takes one argument, 'filepath', which should be the name of a
    FASTA file (or a file whose format is understood by your
    itemClass).  Alternatively, you can pass an open file in as the
    'ifile' keyword arg. SequenceFileDB will retrieve the filepath
    from that, and close 'ifile' when it is finished constructing the
    seqLenDict.

    Note that all of the logic used to actually *create* the seqLenDict
    is in FileDBSequence._init_subclass.

    """
    itemClass = FileDBSequence

    # copy _pickleAttrs and add 'filepath'
    _pickleAttrs = SequenceDB._pickleAttrs.copy()
    _pickleAttrs['filepath'] = 0
    
    def __init__(self, filepath=None, **kwargs):
        if filepath is None:
            try: # get filepath from ifile arg
                filepath = kwargs['ifile'].name
            except (KeyError, AttributeError):
                raise TypeError("unable to obtain a filename")

        # make filepath a pickleable attribute.
        self.filepath = classutil.SourceFileName(str(filepath))

        # initialize base class.
        dbname = os.path.basename(filepath)
        SequenceDB.__init__(self, filepath=filepath, dbname=dbname, **kwargs)
        
        try: # signal that we're done constructing, by closing the file object
            kwargs['ifile'].close()
        except (KeyError, AttributeError): pass

# Some support classes for the SeqLenDict mechanism.

class _SeqLenObject(object):
    """Wrapper to provide the correct seqInfoDict-style object information.

    This boils down to providing id, db, length, and offset.
    
    """
    def __init__(self, seqID, seqDB):
        self.id = seqID
        self.db = seqDB
        self.length, self.offset = seqDB.seqLenDict[seqID]

class _SeqLenDictWrapper(object, UserDict.DictMixin):
    """Wrapper around SequenceDB.seqLenDict to provide seqInfoDict behavior.

    The default storage mechanism for sequences implemented by FileDBSequence
    and SequenceFileDB puts everything in seqLenDict, a shelve index of
    lenghts and offsets.  This class wraps that dictionary to provide the
    interface that SequenceDB expects to see.
    
    """
    def __init__(self, db):
        self.seqDB = db
        
    def __getitem__(self, k):
        return _SeqLenObject(k, self.seqDB)
    
    def __len__(self):
        return len(self.seqDB.seqLenDict)
    
    def __iter__(self):
        return iter(self.seqDB.seqLenDict)
    
    def keys(self):
        return self.seqDB.seqLenDict.keys()

class _SeqLenDictSaver(object):
    """Support for generic reading functions, called by _store_seqlen_dict.

    This allows you to specify your own 'reader' function when
    constructing a FileSequenceDB, e.g. so that you could read
    something other than FASTA files into a seqLenDict.  Pass in this
    function as the 'reader' kwarg to FileSequenceDB.

    Custom reader functions should take a file handle and a filename,
    and return a list of sequence info objects with 'id', 'length',
    and 'sequence' attributes for each sequence in the given
    file/filename.  _SeqLenDictSaver will then construct a '.pureseq'
    file containing the concatenated sequences and fill in the
    seqLenDict appropriately.
    
    """
    def __init__(self, reader):
        self.reader = reader
        
    def __call__(self, d, ifile, filename):
        offset = 0L
        pureseq_fp = file(filename + '.pureseq', 'wb')
        try:
            for o in self.reader(ifile, filename):
                # store the length & offset in the seqLenDict
                d[o.id] = o.length, offset
                offset += o.length
                if o.length != len(o.sequence):
                    raise ValueError('length does not match sequence: %s,%d'
                                     % (o.id, o.length))
                pureseq_fp.write(o.sequence)
        finally:
            pureseq_fp.close()

def _store_seqlen_dict(d, filename, ifile=None, idFilter=None, reader=None,
                      mode='rU'):
    """Store sequence lengths in a dictionary, e.g. a seqLenDict.

    @CTB document reader
    @CTB document idfilter.
    """
    # if a custom reader function was passed in, run that.
    if reader is not None:
        builder = _SeqLenDictSaver(reader)
    else:
        # use our own fast compiled parser.
        try:
            import seqfmt
            builder = seqfmt.read_fasta_lengths
        except ImportError:             # @CTB move?
            raise ImportError('''
Unable to import extension module pygr.seqfmt that should be part of this package.
Either you are working with an incomplete install, or an installation of pygr
compiled with an incompatible Python version.  Please check your PYTHONPATH
setting and make sure it is compatible with this Python version (%d.%d).
When in doubt, rebuild your pygr installation using the
python setup.py build --force
option to force a clean install''' % sys.version_info[:2])
    if idFilter is not None: # need to wrap seqlendict to apply filter...
        class dictwrapper(object):      # @CTB move?
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
        ifile = file(filename, mode)
        try:
            builder(d, ifile, filename) # run the builder on our sequence set
        finally:
            ifile.close()
    
####
#
# class PrefixUnionDict and associated support classes.
#

class _PrefixUnionDictInverse(object):        # @CTB untested
    """Provide inverse (~) operator behavior for PrefixUnionDicts.

    This enables ~pud to return a database that, given a sequence
    object, returns the corresponding key (prefix.id) to retrieve that
    sequence object in the pud.
    
    """
    
    def __init__(self, db):
        self.db = db
        
    def __getitem__(self, seq):
        path = seq.pathForward
        db = path.db
        if db not in self.db.dicts:
            # @CTB abstraction boundary violation! keep? how test?
            anno_seq_attr = getattr(path, '_anno_seq', None)
            if anno_seq_attr.db in self.db.dicts:
                raise KeyError('''\
this annotation is not in the PrefixUnion, but its sequence is.
You can get that using its \'sequence\' attribute.''')
            
            raise KeyError('seq not in PrefixUnionDict')

        id = path.id
        prefix = self.db.dicts[db]
        return prefix + self.db.separator + str(id)
    
    def __contains__(self, seq):
        try:
            return seq.pathForward.db in self.db.dicts
        except AttributeError:
            return False


class _PrefixUnionMemberDict(object, UserDict.DictMixin):
    """
    @CTB confusing/inappropriate use of a dict interface! keep??
    @CTB document.
    'd[prefix]=value; d[k] returns value if k is a member of prefix'
    """
    def __init__(self, puDict, default=None,
                 attrMethod=lambda x:x.pathForward.db):
        self.values = {}
        self.puDict = puDict
        self._attrMethod = attrMethod
        if default is not None:
            self.default = default      # @CTB can we use setdefault for this?
            
    def keys(self):
        return self.puDict.prefixDict.keys()
    possibleKeys = keys                 # legacy interface (?)
            
    def __setitem__(self, k, v):
        if k not in self.puDict.prefixDict:
            raise KeyError('key %s is not a valid union prefix string!' % k)
        new_k = self.puDict.prefixDict[k]
        self.values[new_k] = v
        
    def __getitem__(self, k):
        try:
            db = self._attrMethod(k)
        except AttributeError:
            raise TypeError('wrong key type? _attrMethod() failed.')

        if db not in self.values:
            try:
                return self.default
            except AttributeError:      # no default value - raise KeyError.
                raise KeyError('key not a member of this union!')

        return self.values[db]

class PrefixUnionDict(object, UserDict.DictMixin):
    """Interface to a set of sequence DBs, each assigned a unique prefix.

    For example, the sequence ID 'foo.bar' would unpack to ID 'bar' in
    the dictionary associated with the prefix 'foo'.  This is a useful
    way to combine disparate seqdbs into a single db, without actually
    altering the individual seqdbs.

    PrefixUnionDicts can be created in one of two ways: either
      - pass in a dictionary containing prefix-to-seqdb mappings as
        'prefixDict', or
      - pass in a header file containing the information necessary to create
        such a dictionary.

    In the latter case, see the 'writeHeaderFile' method for format
    information.  The optional kwarg 'trypath' contains a list of
    directories to search for the database file named in each line.
    The optional kwarg 'dbClass' specifies the database class to use
    to load each sequence file; it defaults to SequenceFileDB.

    The default ID separator is '.'; use the 'separator' kwarg to
    change it.

    @CTB trypath => trypaths?
    
    """
    # define ~ (invert) operator to return ... @CTB document.
    __invert__ = classutil.standard_invert
    _inverseClass = _PrefixUnionDictInverse

    def __init__(self, prefixDict=None, separator='.', filename=None,
                 dbClass=SequenceFileDB, trypath=None):
        # read union header file
        if filename is not None:
            if prefixDict:
                raise TypeError('''
cannot create with prefixDict and filename both!''')
            
            if trypath is None:
                trypath = [os.path.dirname(filename)]
            ifile = file(filename, 'rU')
            it = iter(ifile)
            separator = it.next().strip('\r\n') # remove leading/trailing CR
            prefixDict = {}
            for line in it:
                prefix, filepath=line.strip().split('\t')[:2]
                try:
                    dbfile = classutil.search_dirs_for_file(filepath, trypath)
                    db = dbClass(dbfile)
                    prefixDict[prefix] = db
                except IOError:
                    raise IOError('''\
unable to open database %s: check path or privileges.
Set 'trypath' to give a list of directories to search.''' % filepath)
            ifile.close()
            
        self.separator = separator
        if prefixDict is not None:
            self.prefixDict = prefixDict
        else:
            self.prefixDict = {}

        # also create a reverse mapping            
        d = {}
        for k, v in self.prefixDict.items():
            d[v] = k
            
        self.dicts = d
        self.seqInfoDict = _PUDSeqInfoDict(self) # supply standard interface
        
    def format_id(self, prefix, seqID):
        return prefix + self.separator + seqID
    
    def get_prefix_id(self, k):
        """Subdivide a key into a prefix and ID using the given separator."""
        try:
            t = k.split(self.separator, 2)
        except AttributeError:
            raise KeyError('key should be a string! ' + repr(k))
        if len(t) < 2:
            raise KeyError('invalid id format; no prefix: ' + k)
        return t
        
    def get_subitem(self, d, seqID):
        # try int key first
        try:
            return d[int(seqID)]
        except (ValueError, KeyError, TypeError):
            pass
        
        # otherwise, use default (str) key
        try:
            return d[seqID]
        except KeyError:
            raise KeyError, "no key '%s' in %s" % (seqID, repr(d))
        
    def __getitem__(self, k):
        """For 'foo.bar', return 'bar' in dict associated with prefix 'foo'"""
        prefix, seqID = self.get_prefix_id(k)
        try:
            d = self.prefixDict[prefix]
        except KeyError, e:
            raise KeyError("no key '%s' in %s" % (k, repr(self)))
        return self.get_subitem(d, seqID)
    
    def __contains__(self,k):
        """Is the given ID in our PrefixUnionDict?"""
        # try it out as an ID.
        if isinstance(k, str):
            try:
                (prefix, id) = self.get_prefix_id(k)
                return id in self.prefixDict[prefix]
            except KeyError:
                return False

        # otherwise, try treating key as a sequence.
        # @CTB inconsistent with 'getitem'.
        try: 
            db = k.pathForward.db
        except AttributeError:
            raise AttributeError('key must be a sequence with db attribute!')
        return db in self.dicts

    def has_key(self, k):
        return self.__contains__(k)

    def __iter__(self):
        for p, d in self.prefixDict.items():
            for id in d:
                yield self.format_id(p, id)

    def keys(self):
        return list(self.iterkeys())

    def iterkeys(self):
        return iter(self)
    
    def iteritems(self):
        for p,d in self.prefixDict.items():
            for id, seq in d.iteritems():
                yield self.format_id(p, id), seq

    def getName(self, seq):
        """For a given sequence, return a fully qualified name, 'prefix.id'."""
        path = seq.pathForward
        return self.dicts[path.db] + self.separator + path.id

    def newMemberDict(self, **kwargs):  # @CTB untested; not used; necessary?
        """return a new member dictionary (empty)"""
        return _PrefixUnionMemberDict(self, **kwargs)

    def writeHeaderFile(self,filename):  # @CTB not used; necessary?
        """Save a header file, suitable for later re-creation."""
        ifile = file(filename, 'w')
        print >>ifile, self.separator
        for k, v in self.prefixDict.items():
            try:
                print >>ifile, '%s\t%s' % (k, v.filepath)
            except AttributeError:
                raise AttributeError('''\
seq db '%s' has no filepath; you may be able to save this to pygr.Data,
but not to a text HeaderFile!''' % k)
        ifile.close()

    def __len__(self):
        n=0
        for db in self.dicts:
            n += len(db)
        return n
    
    def cacheHint(self, ivalDict, owner=None):  # @CTB untested
        '''save a cache hint dict of {id:(start,stop)}; return ref owner'''
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
    copy = setdefault = update = classutil.method_not_implemented
    
    # these methods should not be implemented for read-only database.
    clear = pop = popitem = classutil.read_only_error


class _PrefixDictInverseAdder(_PrefixUnionDictInverse):
    """
    @CTB document.
    """
    def getName(self, seq):
        """
        @CTB document
        """
        try:
            return _PrefixUnionDictInverse.__getitem__(self, seq)
        except AttributeError: # no seq.db?  treat as a user sequence.
            new_id = 'user' + self.db.separator + seq.pathForward.id
            # check to make sure it's already in the user seq db...
            _ = self.db[new_id]
            return new_id
                
    def __getitem__(self,seq):
        """@CTB document."""
        try:
            return self.getName(seq)
        except KeyError:
            if not self.db.addAll:
                raise

            # if we should add, add seq & re-try.
            self.db += seq
            return self.getName(seq)


class SeqPrefixUnionDict(PrefixUnionDict):
    """
    @CTB document.
    @CTB doc addAll.
    """
    'adds method for easily adding a seq or its database to the PUD'
    def __init__(self, addAll=False, **kwargs):
        PrefixUnionDict.__init__(self, **kwargs)

        # override default PrefixUnionDict __invert__ to add sequences.
        self._inverse = _PrefixDictInverseAdder(self)
        self.addAll = addAll  # see self._inverse behavior.

    def __iadd__(self, k):
        """Add a sequence or database to the PUD, with a unique prefix.

        NOTE: __iadd__ must return self.

        """
        # seq or db already present?
        if k in (~self):
            return self

        db = getattr(k, 'db', None)
        if db is None:                  # annotation sequence?
            db = getattr(k.pathForward, 'db', None) # @CTB untested

        if db is None:  # this is a user sequence, with no container; create.
            if not self.prefixDict.has_key('user'):
                d = KeepUniqueDict()
                self._add_prefix_dict('user', d)
            else:
                d = self.prefixDict['user']
                
            # now add the sequence
            d[k.pathForward.id] = k.pathForward
            return self

        # already contain?  nothing to do.
        if db in self.dicts:            # @CTB can this if ever be true?
            return self

        # ok, not present; add, with a unique name.  does it have
        # _persistent_id?
        try:
            name = db._persistent_id.split('.')[-1]
        except AttributeError:          # no; retrieve from filepath?
            name = getattr(db, 'filepath', None)
            if name:                    # got one; clean up.
                name = os.path.basename(name)
                name = name.split('.')[0]
            else:                       # generate one.
                name = 'noname%d' % len(self.dicts)
            
            if name in self.prefixDict:
                raise ValueError('''
It appears that two different sequence databases are being assigned
the same prefix ("%s").  For this reason, the attempted automatic
construction of a PrefixUnionDict for you cannot be completed!  You
should instead construct a PrefixUnionDict that assigns a unique
prefix to each sequence database, and supply it directly as the
seqDict argument to the NLMSA constructor.''' % id)

        self._add_prefix_dict(name, db)

        return self

    def _add_prefix_dict(self, name, d):
        self.prefixDict[name] = d
        self.dicts[d] = name
        
class _PUDSeqInfoDict(object, UserDict.DictMixin):
    """A wrapper object supplying a standard seqInfoDict interface for PUDs.

    This class simply provides a standard dict interface that rewrites
    individual sequence IDs into the compound PrefixUnionDict seq IDs
    on the fly.

    """
    def __init__(self, db):
        self.seqDB = db
        
    def __iter__(self):
        return iter(self.seqDB)
    
    def keys(self):
        return list(self.iterkeys())

    def iterkeys(self):
        for (k, v) in self.iteritems():
            yield k

    def itervalues(self):
        for (k, v) in self.iteritems():
            yield v
    
    def iteritems(self):
        for p, d in self.seqDB.prefixDict.items():
            for seqID, info in d.seqInfoDict.iteritems():
                yield self.seqDB.format_id(p, seqID), info
                
    def __getitem__(self, k):
        prefix, seqID = self.seqDB.get_prefix_id(k)
        db = self.seqDB.prefixDict[prefix]
        return self.seqDB.get_subitem(db.seqInfoDict, seqID)
    
    def has_key(self, k):
        return k in self.seqDB

#
# @CTB stopped review here. ###################################################
#

class BlastDB(SequenceFileDB):          # @CTB untested?
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



class SliceDB(dict):                    # @CTB untested; what does it do?
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



class VirtualSeq(SeqPath):              # @CTB untested
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

class VirtualSeqDB(dict):               # @CTB untested
    "return a VirtualSeq for any ID requested"
    def __getitem__(self,k):
        try: # IF WE ALREADY CREATED A SEQUENCE FOR THIS ID, RETURN IT
            return dict.__getitem__(self,k)
        except KeyError: # CREATE A VirtualSeq FOR THIS NEW ID
            s=VirtualSeq(k)
            self[k]=s
            return s

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
    def _init_subclass(cls, db, url, name, **kwargs):
        import coordinator
        db.server = coordinator.get_connection(url,name)
        db.url = url
        db.name = name
        db.seqInfoDict = _SeqLenDictWrapper(db)
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

def fastaDB_unpickler(klass,srcfile,kwargs):  # @CTB untested
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

####

class SQLSequence(SQLRow, SequenceBase):
    """Transparent access to a DB row representing a sequence.

    Use attrAlias dict to rename 'length' to something else.
    """
    def _init_subclass(cls, db, **kwargs):
        db.seqInfoDict = db # db will act as its own seqInfoDict
        SQLRow._init_subclass(db=db, **kwargs)
    _init_subclass = classmethod(_init_subclass)
    def __init__(self, id):
        SQLRow.__init__(self, id)
        SequenceBase.__init__(self)
    def __len__(self):
        return self.length
    def strslice(self,start,end):
        "Efficient access to slice of a sequence, useful for huge contigs"
        return self._select('%%(SUBSTRING)s(%s %%(SUBSTR_FROM)s %d %%(SUBSTR_FOR)s %d)'
                            %(self.db._attrSQL('seq'),start+1,end-start))

class DNASQLSequence(SQLSequence):
    _seqtype=DNA_SEQTYPE

class RNASQLSequence(SQLSequence):
    _seqtype=RNA_SEQTYPE

class ProteinSQLSequence(SQLSequence):
    _seqtype=PROTEIN_SEQTYPE
