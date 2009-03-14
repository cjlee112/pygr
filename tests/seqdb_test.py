"""
Tests for the pygr.seqdb module.
"""

import os
import unittest
from testlib import testutil
from pygr.seqdb import SequenceFileDB, PrefixUnionDict, AnnotationDB
from pygr.sequence import Sequence
from pygr.cnestedlist import NLMSA
import gc
from pygr.annotation import AnnotationDB, AnnotationSeq, AnnotationSlice, \
    AnnotationServer, AnnotationClient

class SequenceFileDB_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'SequenceFileDB',
    among other things.
    """
    def setUp(self):
        "Test setup"
        dnaseq = testutil.datafile('dnaseq.fasta')
        self.db = SequenceFileDB(dnaseq) # contains 'seq1', 'seq2'

    def test_len(self):
        assert len(self.db) == 2

    def test_seqInfoDict_len(self):
        assert len(self.db.seqInfoDict) == 2

    def test_no_file_given(self):
        "Make sure that a TypeError is raised when no file is available"
        try:
            db = SequenceFileDB()
            assert 0, "should not reach this point"
        except TypeError:
            pass
        
        try:
            db = SequenceFileDB(ifile=None)
            assert 0, "should not reach this point"
        except TypeError:
            pass

    def test_seq_descriptor(self):
        "Check the '.seq' attribute (tied to a descriptor)"
        s = self.db['seq1']
        assert str(s) == str(s.seq)

    def test_cache(self):
        "SequenceDB cache test"
        assert len(self.db._weakValueDict) == 0
        seq1 = self.db['seq1']
        
        # cache populated?
        assert len(self.db._weakValueDict) == 1
        assert 'seq1' in self.db._weakValueDict

        # cache functions?
        seq1_try2 = self.db['seq1']
        assert seq1 is seq1_try2

    def test_clear_cache(self):
        "SequenceDB clear_cache test"
        assert len(self.db._weakValueDict) == 0
        seq1 = self.db['seq1']
        
        # cache populated?
        assert len(self.db._weakValueDict) == 1
        assert 'seq1' in self.db._weakValueDict

        # clear_cache functions?
        self.db.clear_cache()
        seq1_try3 = self.db['seq1']
        assert seq1 is not seq1_try3
        
    def test_keys(self):
        "SequenceFileDB keys"
        k = self.db.keys()
        k.sort()
        assert k == ['seq1', 'seq2']

    def test_contains(self):
        "SequenceFileDB contains"
        assert 'seq1' in self.db, self.db.keys()
        assert 'seq2' in self.db
        assert 'foo' not in self.db

    def test_invert_class(self):
        "SequenceFileDB __invert__"
        seq = self.db['seq1']
        inversedb = ~self.db
        assert inversedb[seq] == 'seq1'
        assert seq in inversedb
        assert 'foo' not in inversedb

    def test_keys_info(self):
        "SequenceFileDB keys info"
        k = self.db.seqInfoDict.keys()
        k.sort()
        assert k == ['seq1', 'seq2']

    def test_contains_info(self):
        "SequenceFileDB contains info"
        assert 'seq1' in self.db.seqInfoDict
        assert 'seq2' in self.db.seqInfoDict
        assert 'foo' not in self.db.seqInfoDict
    
    def test_has_key(self):
        "SequenceFileDB has key"
        assert self.db.has_key('seq1')
        assert self.db.has_key('seq2')
        assert not self.db.has_key('foo')
    
    def test_get(self):
        "SequenceFileDB get"
        assert self.db.get('foo') is None
        assert self.db.get('seq1') is not None
        assert str(self.db.get('seq1')).startswith('atggtgtca')
        assert self.db.get('seq2') is not None
        assert str(self.db.get('seq2')).startswith('GTGTTGAA')
    
    def test_items(self):
        "SequenceFileDB items"
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == ['seq1', 'seq2']
    
    def test_iterkeys(self):
        "SequenceFileDB iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "SequenceFileDB itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv

    def test_iteritems(self):
        "SequenceFileDB iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii

    def test_readonly(self):
        "SequenceFileDB readonly"
        try:
            self.db.copy()          # what should 'copy' do on SequenceFileDB?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
            
    # test some things other than dict behavior
    def test_keyerror(self):
        "SequenceFileDB keyerror"
        "Make sure that the SequenceFileDB KeyError is informative."
        try:
            self.db['foo']
        except KeyError, e:
            assert "no key 'foo' in database <SequenceFileDB" in str(e), str(e)

class SequenceFileDB_Creation_Test(unittest.TestCase):
    """
    Test some of the nastier / more polluting creation code in an
    isolated (and slower...) class that cleans up after itself.
    """
    def trash_intermediate_files(self):
        seqlen = testutil.datafile('dnaseq.fasta.seqlen')
        pureseq = testutil.datafile('dnaseq.fasta.pureseq')
        try:
            os.unlink(seqlen)
            os.unlink(pureseq)
        except OSError:
            pass
        
    def setUp(self):
        "Test setup"
        self.trash_intermediate_files()
        self.dbfile = testutil.datafile('dnaseq.fasta')

    def tearDown(self):
        self.trash_intermediate_files()

    def test_basic_construction(self):
        self.db = SequenceFileDB(self.dbfile)
        assert str(self.db.get('seq1')).startswith('atggtgtca')
        assert str(self.db.get('seq2')).startswith('GTGTTGAA')

    def test_build_seqLenDict_with_reader(self):
        "Test that building things works properly when specifying a reader."

        class InfoBag(object):
            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first, load the db & save the sequence info in a list
        l = []
        db = SequenceFileDB(self.dbfile)
        for k, v in db.items():
            info = InfoBag(id=k, length=len(v), sequence=str(v))
            l.append(info)
            
        # now, erase the existing files, and recreate the db.
        del db
        self.trash_intermediate_files()

        # create a fake reader with access to the saved info
        def my_fake_reader(fp, filename, info_list=l):
            return info_list

        # now try creating with the fake reader
        db = SequenceFileDB(self.dbfile, reader=my_fake_reader)

        # did it work?
        assert str(db.get('seq1')).startswith('atggtgtca')
        assert str(db.get('seq2')).startswith('GTGTTGAA')

    def test_build_seqLenDict_with_bad_reader(self):
        "Test that building things fails properly with a bad reader."

        class InfoBag(object):
            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first, load the db & save the sequence info in a list
        l = []
        db = SequenceFileDB(self.dbfile)
        for k, v in db.items():
            info = InfoBag(id=k, length=0, sequence=str(v))
            l.append(info)
            
        # now, erase the existing files, and recreate the db.
        del db
        self.trash_intermediate_files()

        # create a fake reader with access to the saved info
        def my_fake_reader(fp, filename, info_list=l):
            return info_list

        # now try creating with the fake reader
        try:
            db = SequenceFileDB(self.dbfile, reader=my_fake_reader)
            assert 0, "should not reach here; db construction should fail!"
        except ValueError:
            pass                        # ValueError is expected

    def test_ifile_arg(self):
        "Test that we can pass in an 'ifile' arg instead of 'filepath'."
        
        dnaseq = testutil.datafile('dnaseq.fasta')
        fp = file(dnaseq)
        self.db = SequenceFileDB(ifile=fp)

        assert str(self.db.get('seq1')).startswith('atggtgtca')
        assert str(self.db.get('seq2')).startswith('GTGTTGAA')

class PrefixUnionDict_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'PrefixUnionDict'.
    """
    def setUp(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        blastdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        self.db = PrefixUnionDict({ 'prefix' : blastdb })

    def test_keys(self):
        "PrefixUnionDict keys"
        k = self.db.keys()
        k.sort()
        assert k == ['prefix.seq1', 'prefix.seq2']

    def test_contains(self):
        "PrefixUnionDict contains"
        assert 'prefix.seq1' in self.db
        assert 'prefix.seq2' in self.db
        assert 'foo' not in self.db
        assert 'prefix.foo' not in self.db

    def test_has_key(self):
        "PrefixUnionDict has key"
        assert self.db.has_key('prefix.seq1')
        assert self.db.has_key('prefix.seq2')
        assert not self.db.has_key('prefix.foo')
        assert not self.db.has_key('foo')

    def test_get(self):
        "PrefixUnionDict get"
        assert self.db.get('foo') is None
        assert self.db.get('prefix.foo') is None
        assert self.db.get('prefix.seq1') is not None
        assert str(self.db.get('prefix.seq1')).startswith('atggtgtca')
        assert self.db.get('prefix.seq2') is not None
        assert str(self.db.get('prefix.seq2')).startswith('GTGTTGAA')

    def test_items(self):
        "PrefixUnionDict items"
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == ['prefix.seq1', 'prefix.seq2']

    def test_iterkeys(self):
        "PrefixUnionDict iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "PrefixUnionDict itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv

    def test_iteritems(self):
        "PrefixUnionDict iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii

    # test some things other than dict behavior
    def test_keyerror(self):
        "PrefixUnionDict keyerror"
        "Make sure that the PrefixUnionDict KeyError is informative."
        try:
            self.db['prefix.foo']
        except KeyError, e:
            assert "no key 'prefix.foo' in " in str(e), str(e)
        try:
            self.db['foo']
        except KeyError, e:
            assert "invalid id format; no prefix: foo" in str(e), str(e)

    def test_readonly(self):
        "PrefixUnionDict readonly"
        try:
            self.db.copy()              # what should 'copy' do on PUD?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'setdefault' do on PUD?
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'update' do on PUD?
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass

class AnnotationDB_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'AnnotationDB'.
    """
    def setUp(self):
        class Annotation(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        slicedb = dict(annot1=Annotation(id='seq', start=0, stop=10),
                       annot2=Annotation(id='seq', start=5, stop=9))
        sequence_dict = dict(seq = Sequence('ATGGGGCCGATTG', 'seq'))
        self.db = AnnotationDB(slicedb, sequence_dict)

    def test_keys(self):
        "AnnotationDB keys"
        k = self.db.keys()
        k.sort()
        assert k == ['annot1', 'annot2'], k

    def test_contains(self):
        "AnnotationDB contains"
        assert 'annot1' in self.db, self.db.keys()
        assert 'annot2' in self.db
        assert 'foo' not in self.db

    def test_has_key(self):
        "AnnotationDB has key"
        assert self.db.has_key('annot1')
        assert self.db.has_key('annot2')
        assert not self.db.has_key('foo')

    def test_get(self):
        "AnnotationDB get"
        assert self.db.get('foo') is None
        assert self.db.get('annot1') is not None
        assert str(self.db.get('annot1').sequence).startswith('ATGGGGC')
        assert self.db.get('annot2') is not None
        assert str(self.db.get('annot2').sequence).startswith('GCCG')
    
    def test_items(self):
        "AnnotationDB items"
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == ['annot1', 'annot2']
    
    def test_iterkeys(self):
        "AnnotationDB iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik
    
    def test_itervalues(self):
        "AnnotationDB itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv[0] == iv[0]
        assert kv == iv, (kv, iv)
    
    def test_iteritems(self):
        "AnnotationDB iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii, (ki, ii)
    
    def test_readonly(self):
        "AnnotationDB readonly"
        try:
            self.db.copy()              # what should 'copy' do on AD?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'setdefault' do on AD?
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'update' do on AD?
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
    
    def test_equality(self):
        "AnnotationDB equality"
        # Check that separately generated annotation objects test equal"
        key = 'annot1'
        db = self.db
        x = db.sliceAnnotation(key, db.sliceDB[key])
        y = db.sliceAnnotation(key, db.sliceDB[key])
        assert x == y
    
    def test_bad_seqdict(self):
        "AnnotationDB bad seqdict"
        class Annotation(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        slicedb = dict(annot1=Annotation(id='seq', start=0, stop=10),
                       annot2=Annotation(id='seq', start=5, stop=9))
        foo_dict = dict(foo=Sequence('ATGGGGCCGATTG', 'foo'))
        try:
            db = AnnotationDB(slicedb, foo_dict)
            assert 0, "incorrect seqdb; key error should be raised"
        except KeyError:
            pass

class SeqDBCache_Test(unittest.TestCase):
    
    def test_cache(self):
        "Sequence slice cache mechanics."

        dnaseq = testutil.datafile('dnaseq.fasta')
        db = SequenceFileDB(dnaseq)

        # create cache components
        cacheDict = {}
        cacheHint = db.cacheHint

        # get seq1
        seq1 = db['seq1']

        # _cache is only created on first cache attempt
        assert not hasattr(db, '_cache')

        # build an 'owner' object
        class AnonymousOwner(object):
            pass
        owner = AnonymousOwner()

        # save seq1 in cache
        cacheDict['seq1'] = (seq1.start, seq1.stop)
        cacheHint(cacheDict, owner)
        del cacheDict                   # 'owner' now holds reference

        # peek into _cache and assert that only the ival coordinates are stored
        v = db._cache.values()[0]
        assert len(v['seq1']) == 2
        del v

        # force a cache access & check that now we've stored actual string
        ival = str(seq1[5:10])
        v = db._cache.values()[0]
        # ...check that we've stored actual string
        assert len(v['seq1']) == 3

        # again force a cache access, this time to the stored sequence string
        ival = str(seq1[5:10])

        # now, eliminate all references to the cache proxy dict
        del owner

        # trash unused objects - not strictly necessary, because there are no
        # islands of circular references & so all objects are already
        # deallocated, but that's implementation dependent.
        gc.collect()

        # ok, cached values should now be gone.
        v = db._cache.values()
        assert len(v) == 0

    def test_nlmsaslice_cache(self):
        "NLMSASlice sequence caching & removal"
        
        # set up sequences
        dnaseq = testutil.datafile('dnaseq.fasta')

        db = SequenceFileDB(dnaseq, autoGC=-1) # use pure WeakValueDict...
        gc.collect()
        assert len(db._weakValueDict)==0, '_weakValueDict should be empty'
        seq1, seq2 = db['seq1'], db['seq2']
        assert len(db._weakValueDict)==2, '_weakValueDict should have 2 seqs'

        # build referencing NLMSA
        mymap = NLMSA('test', 'memory', db, pairwiseMode=True)
        mymap += seq1
        mymap[seq1] += seq2
        mymap.build()

        # check: no cache
        assert not hasattr(db, '_cache'), 'should be no cache yet'

        seq1, seq2 = db['seq1'], db['seq2'] # re-retrieve
        # now retrieve a NLMSASlice, forcing entry of seq into cache
        ival = seq1[5:10]
        x = mymap[ival]

        assert len(db._cache.values()) != 0

        n1 = len(db._cache)
        assert n1 == 1, "should be exactly one cache entry, not %d" % (n1,)

        # ok, now trash referencing arguments & make sure of cleanup
        del x
        gc.collect()
        
        assert len(db._cache.values()) == 0
        
        
        n2 = len(db._cache)
        assert n2 == 0, '%d objects remain; cache memory leak!' % n2
        # FAIL because of __dealloc__ error in cnestedlist.NLMSASlice.

        del mymap, ival, seq1, seq2 # drop our references, cache should empty
        gc.collect()
        # check that db._weakValueDict cache is empty
        assert len(db._weakValueDict)==0, '_weakValueDict should be empty'

def get_suite():
    "Returns the testsuite"
    tests = [ 
        SequenceFileDB_Test, SequenceFileDB_Creation_Test,
        PrefixUnionDict_Test, 
        AnnotationDB_Test, SeqDBCache_Test
    ]
    return testutil.make_suite(tests)

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)
