import pygrtest_common
from pygr.seqdb import BlastDB, PrefixUnionDict

class BlastDB_Test(object):
    def setup(self):
        self.db = BlastDB('dnaseq')     # contains 'seq1', 'seq2'
    def keys_test(self):
        k = self.db.keys()
        k.sort()
        assert k == ['seq1', 'seq2']
    def contains_test(self):
        assert 'seq1' in self.db
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

class PrefixUnionDict_Test(object):
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
