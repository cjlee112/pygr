import unittest
from testlib import testutil, PygrTestProgram
from pygr import sequence


class Sequence_Test(unittest.TestCase):
    'basic sequence class tests'

    def setUp(self):
        self.seq = sequence.Sequence('atttgactatgctccag', 'foo')

    def test_length(self):
        "Sequence lenght"
        assert len(self.seq) == 17

    def test_slice(self):
        "Sequence slice"
        assert str(self.seq[5:10]) == 'actat'

    def test_slicerc(self):
        "Sequence slice then reverse complement"
        assert str(-(self.seq[5:10])) == 'atagt'

    def test_rcslice(self):
        "Sequence reverse complement then slice"
        assert str((-self.seq)[5:10]) == 'gcata'

    def test_truncate(self):
        "Sequence truncate"
        assert str(self.seq[-202020202:5]) == 'atttg'
        assert self.seq[-202020202:5] == self.seq[0:5]
        assert self.seq[-2020202:] == self.seq
        assert str(self.seq[-202020202:-5]) == 'atttgactatgc'
        assert str(self.seq[-5:2029]) == 'tccag'
        assert str(self.seq[-5:]) == 'tccag'
        try:
            self.seq[999:10000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            self.seq[-10000:-3000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            self.seq[1000:]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass

    def test_rctruncate(self):
        "Sequence reverse complement truncate"
        seq= -self.seq
        assert str(seq[-202020202:5]) == 'ctgga'
        assert seq[-202020202:5] == seq[0:5]
        assert seq[-2020202:] == seq
        assert str(seq[-202020202:-5]) == 'ctggagcatagt'
        assert str(seq[-5:2029]) == 'caaat'
        assert str(seq[-5:]) == 'caaat'
        try:
            seq[999:10000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            seq[-10000:-3000]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass
        try:
            seq[1000:]
            raise ValueError('failed to trap out of bounds slice')
        except IndexError:
            pass

    def test_join(self):
        "Sequence join"
        assert str(self.seq[5:15] * self.seq[8:]) == 'atgctcc'

    def test_rcjoin(self):
        "Sequence reverse complement join"
        assert str((-(self.seq[5:10])) * ((-self.seq)[5:10])) == 'ata'

    def test_seqtype(self):
        "Sequence lenght"
        assert self.seq.seqtype() == sequence.DNA_SEQTYPE
        assert sequence.Sequence('auuugacuaugcuccag', 'foo').seqtype() == \
                         sequence.RNA_SEQTYPE
        assert sequence.Sequence('kqwestvvarphal', 'foo').seqtype() == \
                         sequence.PROTEIN_SEQTYPE

# @CTB
'''
#from pygrdata_test import PygrSwissprotBase
class Blast_Test(PygrSwissprotBase):
    'test basic blast functionality'
    @skip_errors(OSError, KeyError)
    def setup(self):
        PygrSwissprotBase.setup(self)
        import pygr.Data
        self.sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        import os
        blastIndexPath = os.path.join(os.path.dirname(self.sp.filepath),
                                      'wikiwacky')
        self.sp.formatdb(blastIndexPath)
    def blast(self):
        hbb = self.sp['HBB1_TORMA']
        hits = self.sp.blast(hbb)
        edges = hits[hbb].edges(maxgap=1, maxinsert=1,
                                minAlignSize=14,pIdentityMin=0.5)
        for t in edges:
            assert len(t[0])>=14, 'result shorter than minAlignSize!'
        result = [(t[0], t[1], t[2].pIdentity()) for t in edges]
        store = PygrDataTextFile(os.path.join('results', 'seqdb1.pickle'))
        correct = store['hbb blast 1']
        assert approximate_cmp(result, correct, .0001) == 0, 'blast results should match'
        result = [(t[0], t[1], t[2].pIdentity()) for t in hits[hbb].generateSeqEnds()]
        correct = store['hbb blast 2']
        assert approximate_cmp(result, correct, .0001) == 0, 'blast results should match'
        trypsin = self.sp['PRCA_ANASP']
        try:
            hits[trypsin]
            raise ValueError('failed to catch bad alignment query')
        except KeyError:
            pass
class Blast_reindex_untest(Blast_Test):
    'test building blast indexes under a different name'
    @skip_errors(OSError, KeyError)
    def setup(self):
        PygrSwissprotBase.setup(self)
        import pygr.Data
        self.sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        import os
        blastIndexPath = os.path.join(os.path.dirname(self.sp.filepath), 'wikiwacky')
        self.sp.formatdb()
        #self.sp.formatdb(blastIndexPath) # FORCE IT TO STORE INDEX WITH DIFFERENT NAME
        #print 'blastIndexPath is', self.sp.blastIndexPath

'''

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
