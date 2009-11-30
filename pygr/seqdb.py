"""
seqdb contains a set of classes for interacting with sequence databases.

Primary sequence database classes:

  - SequenceDB         - base class for sequence databases
  - SequenceFileDB     - file-based sequence database
  - PrefixUnionDict    - container to combine multiple sequence databases
  - XMLRPCSequenceDB   - XML-RPC-accessible sequence database

Extensions:

  - SeqPrefixUnionDict - extends PrefixUnionDict to automatically add seqs
  - BlastDB            - implements NCBI-style name munging for lookups

Associated sequence classes:

  - FileDBSequence     - sequence associated with a SequenceFileDB
  - XMLRPCSequence     - sequence associated with a XMLRPCSequenceDB

----

SequenceDB provides some basic behaviors for sequence databases:
dictionary behavior, an invert operator interface, and caching for
both sequence objects and sequence intervals.  It also relies on a
'seqInfoDict' attribute to contain summary information about
sequences, so that e.g. slice operations can be done without loading
the entire sequence into memory.  (See below for more info on
seqInfoDict.)

SequenceFileDB extends SequenceDB to contain a file-based database of
sequences.  It constructs a seqLenDict that allows direct on-disk lookup
of sequence intervals.  (See below for more info on seqLenDict.)

PrefixUnionDict provides a unified SequenceDB-like interface to a
collection of sequence databases by combining the database name with
the sequence ID into a new sequence id.  For example, the ID
'genome.chrI' would return the sequence 'chrI' in the 'genome'
database.  This is particularly handy for situations where you want to
have seqdbs of multiple sequence types (DNA, protein, annotations,
etc.) all associated together.

@CTB document XMLRPCSequenceDB.
@CTB document SeqPrefixUnionDict.
@CTB document BlastDB.

----

The seqInfoDict interface
-------------------------

The seqInfoDict attribute of a SequenceDB is a dictionary-like object,
keyed by sequence IDs, with associated values being an information
object containing various attributes.  seqInfoDict is essentially an
optimization that permits other pygr-aware components to access
information *about* sequences without actually loading the entire
sequence.

The only required attribute at the moment is 'length', which is
required by some of the NLMSA code.  However, seqInfoDict is a good
mechanism for the storage of any summary information on a sequence,
and so it may be expanded in the future.

The seqLenDict interface
------------------------

The seqLenDict attribute is specific to a SequenceFileDB, where it
provides a file-backed storage of length and offset sequence metadata.
It is used to implement a key optimization in SequenceFileDB, in which
a sequence's offset within a file is used to read only the required
part of the sequence into memory.  This optimization is particularly
important for large sequences, e.g. chromosomes, where reading the
entire sequence into memory shouldn't be done unless it's necessary.

The seqLenDict is keyed by sequence ID and the associated values are a
2-tuple (length, offset), where the offset indicates the byte offset
within the '.pureseq' index file created for each SequenceFileDB.

get_bound_subclass and the 'self.db' attribute
----------------------------------------------

The SequenceDB constructor calls classutil.get_bound_subclass on its
itemClass.  What does that do, and what is it for?

get_bound_subclass takes an existing class, makes a new subclass of
it, binds the variable 'db' to it, and then calls the _init_subclass
classmethod (if it exists) on the new class.  This has the effect of
creating a new class for each SequenceDB instance, tied specifically
to that instance and initialized by the _init_subclass method.

The main effect of this for SequenceDBs is that for any SequenceDB
descendant, the '.db' attribute is automatically set for each Sequence
retrieved from the database.

CTB: I think this is an optimization?

Caching
-------

@CTB discuss caching.

Pickling sequence databases and sequences
-----------------------------------------

@CTB document pickling issues.
programmer notes:

extending SequenceDB
 - seqInfoDict, itemclass

extending SequenceFileDB
 - seqLenDict
 - using your own itemclass
 - using your own reader

doctests & examples
-------------------

update docs for these classes!

intro:
 - loading a FASTA file
 - using a PUD
   + combining dbs, etc.
   + inverse

Code review issues, short term:

 - @CTB get_bound_subclass stuff refers directly to itemClass to set 'db'.
 - @CTB fix 'import *'s
 - @CTB run lint/checker?
 - @CTB test _create_seqLenDict
 - @CTB XMLRPCSequenceDB vs SequenceFileDB

Some long term issues:

 - it should be possible to remove _SeqLenDictSaver and just combine its
   functionality with _store_seqlen_dict.  --titus 3/21/09

"""

from __future__ import generators
import sys
import os
import UserDict
import weakref

from sequence import *                  # @CTB
from sqlgraph import *                  # @CTB
import classutil
from annotation import AnnotationDB, AnnotationSeq, AnnotationSlice, \
     AnnotationServer, AnnotationClient
import logger
import seqfmt

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

    For subclassing, note that self.seqInfoDict must be set before
    SequenceDB.__init__ is called!

    """
    # class to use for database-linked sequences; no default.
    itemClass = None
    # class to use for sequence slices; see sequence.SeqPath.classySlice.
    itemSliceClass = SeqDBSlice

    # pickling methods & what attributes to pickle.
    __getstate__ = classutil.standard_getstate
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(autoGC=0)

    # define ~ (invert) operator to return a lazily-created _SequenceDBInverse
    __invert__ = classutil.lazy_create_invert(_SequenceDBInverse)

    def __init__(self, autoGC=True, dbname=None, **kwargs):
        """Initialize seq db from filepath or ifile."""
        if autoGC: # automatically garbage collect unused objects
            self._weakValueDict = classutil.RecentValueDictionary(autoGC)
        else:
            self._weakValueDict = {}    # object cache @CTB not tested
        self.autoGC = autoGC

        # override itemClass and itemSliceClass if specified
        self.itemClass = kwargs.get('itemClass', self.itemClass)
        self.itemSliceClass = kwargs.get('itemSliceClass', self.itemSliceClass)

        if self.itemClass is None:
            raise TypeError("must supply itemClass to SequenceDB")

        # get a copy we can modify w/o side effects and bind itemClass.
        kwargs = kwargs.copy()
        kwargs['db'] = self
        classutil.get_bound_subclass(self, 'itemClass', dbname,
                                     subclassArgs=kwargs)

        # guess the sequence type
        self._set_seqtype()

    def __hash__(self):
        """Define a hash function to allow this object to be used as a key."""
        return id(self)

    def _set_seqtype(self):
        """Guess the seqtype from 100 chars of 1st seq if not already known."""
        seqtype = getattr(self, '_seqtype', None)
        if seqtype is not None:
            return

        for seqID in self: # get an iterator
            seq = self[seqID] # get the 1st sequence
            ch100 = str(seq[:100])
            self._seqtype = guess_seqtype(ch100)
            break # only process the 1st sequence!!!

    _cache_max=10000                    # @CTB move? make settable?

    def cacheHint(self, ivalDict, owner):
        """Save a cache hint dict: {id: (start, stop)}.

        @CTB document!
        """
        d={}
        # @CTB refactor, test
        # Build the cache dictionary for owner.
        for id, ival in ivalDict.items():
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
                try:
                    s = ival[2] # get seq string from our cache
                except IndexError: # use strslice() to retrieve from storage
                    s = seq.strslice(ival_start, ival_stop, useCache=False)
                    ival.append(s)
                    try: # does owner want to reference this cached seq?
                        save_f = owner.cache_reference
                    except AttributeError:
                        pass # no, so nothing to do
                    else: # let owner control caching in our _weakValueDict
                        save_f(seq)     # # @CTB untested
                return s[start - ival_start:stop - ival_start]
        raise IndexError('interval not found in cache') # @CTB untested

    # these methods should all be implemented on all SequenceDBs.
    def close(self):
        pass # subclass should implement closing of its open resources!

    def __iter__(self):
        return iter(self.seqInfoDict)

    def iteritems(self):
        for seqID in self:
            yield seqID, self[seqID]

    def __len__(self):
        return len(self.seqInfoDict)

    def __getitem__(self, seqID):
        """Retrieve sequence by id, using cache if available."""
        try: # for speed, default case (cache hit) should return immediately
            return self._weakValueDict[seqID]
        except KeyError: # not in cache?  try loading.
            try:
                s = self.itemClass(self, seqID)
            except KeyError:
                raise KeyError("no key '%s' in database %s"
                               % (seqID, repr(self)))
            self._weakValueDict[seqID] = s # save in cache.
            return s

    def keys(self):
        return self.seqInfoDict.keys()

    def __contains__(self, key):
        return key in self.seqInfoDict

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__,
                              self.itemClass.__class__.__name__)

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

    See SequenceFileDB for the associated database class.

    In general, you should not create objects from this class directly;
    retrieve them from SequenceFileDB objects, instead.

    NOTE: 'self.db' is attached to all instances of this class that come
    from a particular database by 'classutil.get_bound_subclass'.

    """
    seq = _FileDBSeqDescriptor()        # dynamically retrieve 'seq'.
    __reduce__ = classutil.item_reducer # for pickling purposes.

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

        return self.db.strslice(self.id, start, end)


class SequenceFileDB(SequenceDB):
    """Main class for file-based storage of a sequence database.

    By default, SequenceFileDB uses a seqLenDict, a.k.a. a shelve
    index of sequence lengths and offsets, to retrieve sequence slices
    with fseek.  Thus entire chromosomes (for example) do not have to
    be loaded to retrieve a subslice.

    Takes one required argument, 'filepath', which should be the name
    of a FASTA file (or a file whose format is understood by your
    custom reader; see 'reader' kw arg, and the _store_seqlen_dict
    function).

    The SequenceFileDB seqInfoDict interface is a wrapper around the
    seqLenDict created by the __init__ function.

    """
    itemClass = FileDBSequence

    # copy _pickleAttrs and add 'filepath'
    _pickleAttrs = SequenceDB._pickleAttrs.copy()
    _pickleAttrs['filepath'] = 0

    def __init__(self, filepath, reader=None, **kwargs):
        # make filepath a pickleable attribute.
        self.filepath = classutil.SourceFileName(str(filepath))

        fullpath = self.filepath + '.seqlen'
        # build the seqLenDict if it doesn't already exist
        try:
            seqLenDict = classutil.open_shelve(fullpath, 'r')
        except NoSuchFileError:
            seqLenDict = self._create_seqLenDict(fullpath, filepath, reader)

        self.seqLenDict = seqLenDict
        self.seqInfoDict = _SeqLenDictWrapper(self) # standard interface

        # initialize base class.
        dbname = os.path.basename(filepath)
        SequenceDB.__init__(self, filepath=filepath, dbname=dbname, **kwargs)

    def close(self):
        '''close our open shelve index file and _pureseq...'''
        self.seqLenDict.close()
        try:
            do_close = self._pureseq.close
        except AttributeError:
            pass # _pureseq not open yet, so nothing to do
        else:
            do_close()

    def __repr__(self):
        return "<%s '%s'>" % (self.__class__.__name__, self.filepath)

    def _create_seqLenDict(self, dictpath, seqpath, reader=None):
        """Create a seqLenDict from 'seqpath' and store in 'dictpath'."""
        seqLenDict = classutil.open_shelve(dictpath, 'n')
        try:
            logger.debug('Building sequence length index...')
            _store_seqlen_dict(seqLenDict, seqpath, reader)
        finally:
            seqLenDict.close() # close after writing, no matter what!
        return classutil.open_shelve(dictpath, 'r') # re-open read-only

    def strslice(self, seqID, start, end, useCache=True):
        """Access slice of a sequence efficiently, using seqLenDict info."""
        # Retrieve sequence from the .pureseq file based on seqLenDict
        # information.
        try:
            ifile=self._pureseq
        except AttributeError:
            fullpath = self.filepath + '.pureseq'
            ifile = file(fullpath, 'rb')
            self._pureseq = ifile

        # Now, read in the actual slice.
        offset = self.seqLenDict[seqID][1]
        ifile.seek(offset + start)
        return ifile.read(end - start)


# Some support classes for the SeqLenDict mechanism.

class BasicSeqInfo(object):
    """Wrapper to provide the correct seqInfoDict-style object information.

    This boils down to providing id, db, length, and possibly offset.

    """

    def __init__(self, seqID, seqDB, length=None):
        self.id = seqID
        self.db = seqDB
        if length is None:
            self.length = len(seqDB[seqID]) # generic but possibly slow
        else:
            self.length = length


class _SeqLenObject(BasicSeqInfo):
    """Wrapper for use with a seqLenDict """

    def __init__(self, seqID, seqDB):
        length, self.offset = seqDB.seqLenDict[seqID]
        BasicSeqInfo.__init__(self, seqID, seqDB, length)


class BasicSeqInfoDict(object, UserDict.DictMixin):
    """Wrapper around SequenceDB.seqLenDict to provide seqInfoDict behavior.
    This basic version just gets the length from the sequence object itself.
    """
    itemClass = BasicSeqInfo

    def __init__(self, db):
        self.seqDB = db

    def __getitem__(self, k):
        return self.itemClass(k, self.seqDB)

    def __len__(self):
        return len(self.seqDB.seqLenDict)

    def __iter__(self):
        return iter(self.seqDB.seqLenDict)

    def keys(self):
        return self.seqDB.seqLenDict.keys()


class _SeqLenDictWrapper(BasicSeqInfoDict):
    """
    The default storage mechanism for sequences implemented by FileDBSequence
    and SequenceFileDB puts everything in seqLenDict, a shelve index of
    lengths and offsets.  This class wraps that dictionary to provide the
    interface that SequenceDB expects to see.

 """
    itemClass = _SeqLenObject


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


def _store_seqlen_dict(d, filename, reader=None, mode='rU'):
    """Store sequence lengths in a dictionary, e.g. a seqLenDict.

    Used by SequenceFileDB._create_seqLenDict.

    The 'reader' function implements a custom sequence format reader;
    by default, _store_seqlen_dict uses seqfmt.read_fasta_lengths,
    which reads FASTA-format files.  See _SeqLenDictSaver for
    information on building a custom 'reader', and see the seqdb docs
    for an example.

    """
    # if a custom reader function was passed in, run that.
    builder = seqfmt.read_fasta_lengths
    if reader is not None:
        builder = _SeqLenDictSaver(reader)

    ifile = file(filename, mode)
    try:
        builder(d, ifile, filename) # run the builder on our sequence set
    finally:
        ifile.close()


####
#
# class PrefixUnionDict and associated support classes.
#

class _PrefixUnionDictInverse(object):
    """Provide inverse (~) operator behavior for PrefixUnionDicts.

    This enables ~pud to return a database that, given a sequence
    object, returns the corresponding key (prefix.id) to retrieve that
    sequence object in the pud.

    """

    def __init__(self, db):
        self.db = db

    def __getitem__(self, ival):
        seq = ival.pathForward # get the top-level sequence object
        try: # for speed, normal case should execute immediately
            prefix = self.db.dicts[seq.db]
        except KeyError:
            try:
                # @CTB abstraction boundary violation! keep? how test?
                if seq.pathForward._anno_seq.db in self.db.dicts:
                    raise KeyError('''\
this annotation is not in the PrefixUnion, but its sequence is.
You can get that using its \'sequence\' attribute.''')
            except AttributeError:
                pass
            raise KeyError('seq.db not in PrefixUnionDict')

        return prefix + self.db.separator + str(seq.id)

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
                 attrMethod=lambda x: x.pathForward.db):
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
    # define ~ (invert) operator to return a lazily-created _PUDInverse.
    __invert__ = classutil.lazy_create_invert(_PrefixUnionDictInverse)

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
            try:
                it = iter(ifile)
                # Remove leading/trailing CR+LF.
                separator = it.next().strip('\r\n')
                prefixDict = {}
                for line in it:
                    prefix, filepath=line.strip().split('\t')[:2]
                    try:
                        dbfile = classutil.search_dirs_for_file(filepath,
                                                                trypath)
                        db = dbClass(dbfile)
                    except IOError:
                        for db in prefixDict.values():
                            db.close() # close databases before exiting
                        raise IOError('''\
    unable to open database %s: check path or privileges.
    Set 'trypath' to give a list of directories to search.''' % filepath)
                    else:
                        prefixDict[prefix] = db
            finally:
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
            t = k.split(self.separator, 2) # split into no more than 3 fields
        except AttributeError:
            raise KeyError('key should be a string! ' + repr(k))
        l = len(t)
        if l == 2:
            return t
        elif l<2:
            raise KeyError('invalid id format; no prefix: ' + k)
        else: # id contains separator character?
            prefix = t[0] # assume prefix doesn't contain separator @CTB untested
            seqID = k[len(prefix) + 1:] # skip past prefix
            return prefix, seqID

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
            raise KeyError("no key '%s' in %s" % (seqID, repr(d)))

    def __getitem__(self, k):
        """For 'foo.bar', return 'bar' in dict associated with prefix 'foo'"""
        prefix, seqID = self.get_prefix_id(k)
        try:
            d = self.prefixDict[prefix]
        except KeyError, e:
            raise KeyError("no key '%s' in %s" % (k, repr(self)))
        return self.get_subitem(d, seqID)

    def __contains__(self, k):
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
        for p, d in self.prefixDict.items():
            for id, seq in d.iteritems():
                yield self.format_id(p, id), seq

    def getName(self, ival):
        """For a given sequence, return a fully qualified name, 'prefix.id'."""
        seq = ival.pathForward # get the top-level sequence object
        return self.dicts[seq.db] + self.separator + seq.id

    def newMemberDict(self, **kwargs):  # @CTB not used; necessary?
        """return a new member dictionary (empty)"""
        return _PrefixUnionMemberDict(self, **kwargs)

    def writeHeaderFile(self, filename):  # @CTB not used; necessary?
        """Save a header file, suitable for later re-creation."""
        ifile = file(filename, 'w')
        print >>ifile, self.separator
        for k, v in self.prefixDict.items():
            try:
                print >>ifile, '%s\t%s' % (k, v.filepath)
            except AttributeError:
                raise AttributeError('''\
seq db '%s' has no filepath; you may be able to save this to worldbase,
but not to a text HeaderFile!''' % k)
        ifile.close()

    def __len__(self):
        n=0
        for db in self.dicts:
            n += len(db)
        return n

    def cacheHint(self, ivalDict, owner=None):  # @CTB untested
        '''save a cache hint dict of {id:(start,stop)}'''
        d={}
        # extract separate cache hint dict for each prefix
        for longID, ival in ivalDict.items():
            prefix, seqID = self.get_prefix_id(longID)
            d.setdefault(prefix, {})[seqID] = ival
        for prefix, seqDict in d.items():
            try:
                m = self.prefixDict[prefix].cacheHint
            except AttributeError: # subdict can't cacheHint(), so just ignore
                pass
            else:
                # pass cache hint down to subdictionary
                m(seqDict, owner)

    # not clear what this should do for PrefixUnionDict
    copy = setdefault = update = classutil.method_not_implemented

    # these methods should not be implemented for read-only database.
    clear = pop = popitem = classutil.read_only_error


class _PrefixDictInverseAdder(_PrefixUnionDictInverse):
    """Inverse class for SeqPrefixUnionDict; adds sequences when looked up.

    @CTB is getName only used by __getitem__?  Make private?
    """

    def getName(self, seq):
        """Find in or add the given sequence to the inverse of a PUD."""
        try:
            return _PrefixUnionDictInverse.__getitem__(self, seq)
        except AttributeError: # no seq.db?  treat as a user sequence.
            new_id = 'user' + self.db.separator + seq.pathForward.id
            # check to make sure it's already in the user seq db...
            _ = self.db[new_id]
            return new_id

    def __getitem__(self, seq):
        """__getitem__ interface that calls getName."""
        try:
            return self.getName(seq)
        except KeyError:
            if not self.db.addAll:
                raise

            # if we should add, add seq & re-try.
            self.db += seq
            return self.getName(seq)


class SeqPrefixUnionDict(PrefixUnionDict):
    """SeqPrefixUnionDict provides += functionality to add seqs to a PUD.

    See the __iadd__ method for details.

    If addAll is True, then looking a sequence up in the inverse db will
    automatically add it to the PrefixUnionDict.
    """

    __invert__ = classutil.lazy_create_invert(_PrefixDictInverseAdder)

    def __init__(self, addAll=False, **kwargs):
        PrefixUnionDict.__init__(self, **kwargs)

        # override default PrefixUnionDict __invert__ to add sequences;
        # see classutil.lazy_create_invert.
        self.addAll = addAll  # see _PrefixDictInverseAdder behavior.

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
            if 'user' not in self.prefixDict:
                d = KeepUniqueDict()
                self._add_prefix_dict('user', d)
            else:
                d = self.prefixDict['user']

            # now add the sequence
            d[k.pathForward.id] = k.pathForward
            return self

        # already contain?  nothing to do.
        if db in self.dicts:            # @CTB can this 'if' ever be true?
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
                logger.debug('''
It appears that two different sequence databases are being assigned
the same prefix ("%s").  For this reason, the attempted automatic
construction of a PrefixUnionDict for you cannot be completed!  You
should instead construct a PrefixUnionDict that assigns a unique
prefix to each sequence database, and supply it directly as the
seqDict argument to the NLMSA constructor.''' % id)
                raise ValueError('''\
cannot automatically construct PrefixUnionDict''')

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

    def __reduce__(self): # provided only for compatibility w/ 0.7 clients
        return (classutil.ClassicUnpickler, (self.__class__,
                                             self.__getstate__()))

    def __init__(self, filepath=None, blastReady=False, blastIndexPath=None,
                 blastIndexDirs=None, **kwargs):
        """format database and build indexes if needed. Provide filepath
        or file object"""
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

    def megablast(self, seq, al=None, blastpath='megablast', expmax=1e-20,
                  maxseq=None, minIdentity=None, maskOpts='-U T -F m',
                  rmPath='RepeatMasker', rmOpts='-xsmall',
                  verbose=True, opts='', **kwargs):
        'run megablast with the specified parameters, return NLMSA alignment'
        from blast import MegablastMapping
        blastmap = self.formatdb(attr='megablastMap',
                                 mapClass=MegablastMapping)
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


class BlastDBXMLRPC(BlastDB):
    'XMLRPC server wrapper around a standard BlastDB'
    xmlrpc_methods = dict(getSeqLen=0, get_strslice=0, getSeqLenDict=0,
                          get_db_size=0, get_seqtype=0,
                          strslice='get_strslice')

    def getSeqLen(self, id):
        'get sequence length, or -1 if not found'
        try:
            return len(self[id])
        except KeyError:
            return -1  # SEQUENCE OBJECT DOES NOT EXIST

    def getSeqLenDict(self):
        'return seqLenDict over XMLRPC'
        d = {}
        for k, v in self.seqLenDict.items():
            d[k] = v[0], str(v[1]) # CONVERT TO STR TO ALLOW OFFSET>2GB
        return d # XML-RPC CANNOT HANDLE INT > 2 GB, SO FORCED TO CONVERT...

    def get_db_size(self):
        return len(self)

    def get_strslice(self, id, start, stop):
        '''return string sequence for specified interval
        in the specified sequence'''
        if start < 0: # HANDLE NEGATIVE ORIENTATION
            return str((-(self[id]))[-stop:-start])
        else: # POSITIVE ORIENTATION
            return str(self[id][start:stop])

    def get_seqtype(self):
        return self._seqtype


class XMLRPCSequence(SequenceBase):
    "Represents a sequence in a blast database, accessed via XMLRPC"

    def __init__(self, db, id):
        self.length = db.server.getSeqLen(id)
        if self.length <= 0:
            raise KeyError('%s not in this database' % id)
        self.id = id
        SequenceBase.__init__(self)

    def strslice(self, start, end, useCache=True):
        "XMLRPC access to slice of a sequence"
        if useCache:
            try:
                return self.db.strsliceCache(self, start, end)
            except IndexError: # NOT FOUND IN CACHE
                pass # JUST USE OUR REGULAR XMLRPC METHOD
        # Get from XMLRPC.
        return self.db.server.get_strslice(self.id, start, end)

    def __len__(self):
        return self.length


class XMLRPCSeqLenDescr(object):
    'descriptor that returns dictionary of remote server seqLenDict'

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        '''only called if attribute does not already exist. Saves result
        as attribute'''
        d = obj.server.getSeqLenDict()
        for k, v in d.items():
            d[k] = v[0], int(v[1]) # CONVERT OFFSET STR BACK TO INT
        obj.__dict__[self.attr] = d # PROVIDE DIRECTLY TO THE __dict__
        return d


class XMLRPCSequenceDB(SequenceDB):
    'XMLRPC client: access sequence database over XMLRPC'
    itemClass = XMLRPCSequence # sequence storage interface
    seqLenDict = XMLRPCSeqLenDescr('seqLenDict') # INTERFACE TO SEQLENDICT

    def __init__(self, url, name, *args, **kwargs):
        import coordinator
        self.server = coordinator.get_connection(url, name)
        self.url = url
        self.name = name
        self.seqInfoDict = _SeqLenDictWrapper(self)
        SequenceDB.__init__(self, *args, **kwargs)

    def __reduce__(self): # provided only for compatibility w/ 0.7 clients
        return (classutil.ClassicUnpickler, (self.__class__,
                                             self.__getstate__()))

    def __getstate__(self): # DO NOT pickle self.itemClass! We provide our own.
        return dict(url=self.url, name=self.name) # just need XMLRPC info

    def __len__(self):
        return self.server.get_db_size()

    def __contains__(self, k):
        if self.server.getSeqLen(k)>0:
            return True
        else:
            return False

    def _set_seqtype(self):
        'efficient way to determine sequence type of this database'
        try: # if already known, no need to do anything
            return self._seqtype
        except AttributeError:
            self._seqtype = self.server.get_seqtype()
            return self._seqtype
