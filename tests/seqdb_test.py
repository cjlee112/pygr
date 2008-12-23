import pygrtest_common
from pygr.seqdb import SequenceFileDB, PrefixUnionDict, AnnotationDB, \
     TranslationAnnot, TranslationAnnotSlice
from pygr.sequence import Sequence
from pygr.cnestedlist import NLMSA
import gc

class SequenceFileDB_Test(object):
    """
    Test for all of the basic dictionary functions on 'SequenceFileDB'.
    """
    def setup(self):
        self.db = SequenceFileDB('dnaseq')     # contains 'seq1', 'seq2'
    def keys_test(self):
        k = self.db.keys()
        k.sort()
        assert k == ['seq1', 'seq2']
    def contains_test(self):
        assert 'seq1' in self.db, self.db.keys()
        assert 'seq2' in self.db
        assert 'foo' not in self.db
    def keys_info_test(self):
        k = self.db.seqInfoDict.keys()
        k.sort()
        assert k == ['seq1', 'seq2']
    def contains_info_test(self):
        assert 'seq1' in self.db.seqInfoDict
        assert 'seq2' in self.db.seqInfoDict
        assert 'foo' not in self.db.seqInfoDict
    def has_key_test(self):
        assert self.db.has_key('seq1')
        assert self.db.has_key('seq2')
        assert not self.db.has_key('foo')
    def get_test(self):
        assert self.db.get('foo') is None
        assert self.db.get('seq1') is not None
        assert str(self.db.get('seq1')).startswith('atggtgtca')
        assert self.db.get('seq2') is not None
        assert str(self.db.get('seq2')).startswith('GTGTTGAA')
    def items_test(self):
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == ['seq1', 'seq2']
    def iterkeys_test(self):
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik
    def itervalues_test(self):
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv
    def iteritems_test(self):
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii
    def readonly_test(self):
        try:
            self.db.copy()              # what should 'copy' do on SequenceFileDB?
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
    def keyerror_test(self):
        "Make sure that the SequenceFileDB KeyError is informative."
        try:
            self.db['foo']
        except KeyError, e:
            assert "no key 'foo' in database <SequenceFileDB" in str(e), str(e)

class PrefixUnionDict_Test(object):
    """
    Test for all of the basic dictionary functions on 'PrefixUnionDict'.
    """
    def setup(self):
        blastdb = SequenceFileDB('dnaseq')     # contains 'seq1', 'seq2'
        self.db = PrefixUnionDict({ 'prefix' : blastdb })
    def keys_test(self):
        k = self.db.keys()
        k.sort()
        assert k == ['prefix.seq1', 'prefix.seq2']
    def contains_test(self):
        assert 'prefix.seq1' in self.db
        assert 'prefix.seq2' in self.db
        assert 'foo' not in self.db
        assert 'prefix.foo' not in self.db
    def has_key_test(self):
        assert self.db.has_key('prefix.seq1')
        assert self.db.has_key('prefix.seq2')
        assert not self.db.has_key('prefix.foo')
        assert not self.db.has_key('foo')
    def get_test(self):
        assert self.db.get('foo') is None
        assert self.db.get('prefix.foo') is None
        assert self.db.get('prefix.seq1') is not None
        assert str(self.db.get('prefix.seq1')).startswith('atggtgtca')
        assert self.db.get('prefix.seq2') is not None
        assert str(self.db.get('prefix.seq2')).startswith('GTGTTGAA')
    def items_test(self):
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == ['prefix.seq1', 'prefix.seq2']
    def iterkeys_test(self):
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik
    def itervalues_test(self):
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv
    def iteritems_test(self):
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii
    # test some things other than dict behavior
    def keyerror_test(self):
        "Make sure that the PrefixUnionDict KeyError is informative."
        try:
            self.db['prefix.foo']
        except KeyError, e:
            assert "no key 'prefix.foo' in " in str(e), str(e)
        try:
            self.db['foo']
        except KeyError, e:
            assert "invalid id format; no prefix: foo" in str(e), str(e)
    def readonly_test(self):
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

class AnnotationDB_Test(object):
    """
    Test for all of the basic dictionary functions on 'AnnotationDB'.
    """
    def setup(self):
        class Annotation(object):
            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)
        slicedb = dict(annot1=Annotation(id='seq', start=0, stop=10),
                       annot2=Annotation(id='seq', start=5, stop=9))
        sequence_dict = dict(seq = Sequence('ATGGGGCCGATTG', 'seq'))
        
        self.db = AnnotationDB(slicedb, sequence_dict)
    def keys_test(self):
        k = self.db.keys()
        k.sort()
        assert k == ['annot1', 'annot2'], k
    def contains_test(self):
        assert 'annot1' in self.db, self.db.keys()
        assert 'annot2' in self.db
        assert 'foo' not in self.db
    def has_key_test(self):
        assert self.db.has_key('annot1')
        assert self.db.has_key('annot2')
        assert not self.db.has_key('foo')
    def get_test(self):
        assert self.db.get('foo') is None
        assert self.db.get('annot1') is not None
        assert str(self.db.get('annot1').sequence).startswith('ATGGGGC')
        assert self.db.get('annot2') is not None
        assert str(self.db.get('annot2').sequence).startswith('GCCG')
    def items_test(self):
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == ['annot1', 'annot2']
    def iterkeys_test(self):
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik
    def itervalues_test(self):
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv[0] == iv[0]
        assert kv == iv, (kv, iv)
    def iteritems_test(self):
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii, (ki, ii)
    def readonly_test(self):
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
    def equality_test(self):
        "Check that separately generated annotation objects test equal"
        key = 'annot1'
        db = self.db
        x = db.sliceAnnotation(key, db.sliceDB[key])
        y = db.sliceAnnotation(key, db.sliceDB[key])
        assert x == y
    def bad_seqdict_test(self):
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
    def translation_annot_test(self):
        db = SequenceFileDB('hbb1_mouse.fa')
        adb = AnnotationDB({1:('gi|171854975|dbj|AB364477.1|',3,441)},
                           db, itemClass=TranslationAnnot,
                           itemSliceClass=TranslationAnnotSlice,
                           sliceAttrDict=dict(id=0,start=1,stop=2))
        trseq = adb[1]
        assert len(trseq) == 146, 'wrong translation length!'
        assert len(trseq.sequence) == 438, 'wrong sequence length!'
        s = trseq[-10:]
        assert len(s) == 10, 'wrong translation length!'
        assert str(s.sequence) == 'GTGGCCACTGCCCTGGCTCACAAGTACCAC'
        assert str(s) == 'VATALAHKYH', 'bad ORF translation!'
        
                                                
class SeqDBCache_Test(object):
    def cache_test(self):
        "Test basic sequence slice cache mechanics."
        db = SequenceFileDB('dnaseq')

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

    def nlmsaslice_cache_test(self):
        "Test NLMSASlice sequence caching & removal"
        # set up sequences
        db = SequenceFileDB('dnaseq', autoGC=-1) # use pure WeakValueDict...
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
        print 'this should not be empty:', db._cache.values()
        n1 = len(db._cache)
        assert n1 == 1, "should be exactly one cache entry, not %d" % (n1,)

        # ok, now trash referencing arguments & make sure of cleanup
        del x
        gc.collect()
        print 'this should be empty:', db._cache.values()
        n2 = len(db._cache)
        assert n2 == 0, '%d objects remain; cache memory leak!' % n2
        # FAIL because of __dealloc__ error in cnestedlist.NLMSASlice.

        del mymap, ival, seq1, seq2 # drop our references, cache should empty
        gc.collect()
        # check that db._weakValueDict cache is empty
        assert len(db._weakValueDict)==0, '_weakValueDict should be empty'
