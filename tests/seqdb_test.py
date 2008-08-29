import pygrtest_common
from pygr.seqdb import BlastDB, PrefixUnionDict, AnnotationDB
from pygr.sequence import Sequence

class BlastDB_Test(object):
    """
    Test for all of the basic dictionary functions on 'BlastDB'.
    """
    def setup(self):
        self.db = BlastDB('dnaseq')     # contains 'seq1', 'seq2'
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
            self.db.copy()              # what should 'copy' do on BlastDB?
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
        "Make sure that the BlastDB KeyError is informative."
        try:
            self.db['foo']
        except KeyError, e:
            assert "no key 'foo' in database <BlastDB" in str(e), str(e)

class PrefixUnionDict_Test(object):
    """
    Test for all of the basic dictionary functions on 'PrefixUnionDict'.
    """
    def setup(self):
        blastdb = BlastDB('dnaseq')     # contains 'seq1', 'seq2'
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
    def equality_test(self):
        key = 'annot1'
        db = self.db
        
        x = db.sliceAnnotation(key, db.sliceDB[key])
        y = db.sliceAnnotation(key, db.sliceDB[key])
        assert x == y
