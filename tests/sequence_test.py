import unittest
from pygr import sequence
from nosebase import *

class SequenceSuite(unittest.TestCase):
    'basic sequence class tests'
    def setUp(self):
        self.seq=sequence.Sequence('atttgactatgctccag','foo')     
    def testLength(self):
        self.assertEqual(len(self.seq),17)
    def testSlice(self):
        self.assertEqual(str(self.seq[5:10]),'actat')
    def testSliceRC(self):
        self.assertEqual(str(-(self.seq[5:10])),'atagt')
    def testRCSlice(self):
        self.assertEqual(str((-self.seq)[5:10]),'gcata')
    def testTruncate(self):
        self.assertEqual(str(self.seq[-202020202:5]),'atttg')
        self.assertEqual(self.seq[-202020202:5],self.seq[0:5])
        self.assertEqual(self.seq[-2020202:],self.seq)
        self.assertEqual(str(self.seq[-202020202:-5]),'atttgactatgc')
        self.assertEqual(str(self.seq[-5:2029]),'tccag')
        self.assertEqual(str(self.seq[-5:]),'tccag')
        self.assertRaises(IndexError,lambda x:x[999:10000],self.seq)
        self.assertRaises(IndexError,lambda x:x[-10000:-3000],self.seq)
        self.assertRaises(IndexError,lambda x:x[1000:],self.seq)
    def testRCTruncate(self):
        seq= -self.seq
        self.assertEqual(str(seq[-202020202:5]),'ctgga')
        self.assertEqual(seq[-202020202:5],seq[0:5])
        self.assertEqual(seq[-2020202:],seq)
        self.assertEqual(str(seq[-202020202:-5]),'ctggagcatagt')
        self.assertEqual(str(seq[-5:2029]),'caaat')
        self.assertEqual(str(seq[-5:]),'caaat')
        self.assertRaises(IndexError,lambda x:x[999:10000],seq)
        self.assertRaises(IndexError,lambda x:x[-10000:-3000],seq)
        self.assertRaises(IndexError,lambda x:x[1000:],seq)
    def testjoin(self):
        self.assertEqual(str(self.seq[5:15]*self.seq[8:]),'atgctcc')
    def testRCjoin(self):
        self.assertEqual(str((-(self.seq[5:10]))*((-self.seq)[5:10])),'ata')
    def testseqtype(self):
        self.assertEqual(self.seq.seqtype(),sequence.DNA_SEQTYPE)
        self.assertEqual(sequence.Sequence('auuugacuaugcuccag','foo').seqtype(),
                         sequence.RNA_SEQTYPE)
        self.assertEqual(sequence.Sequence('kqwestvvarphal','foo').seqtype(),
                         sequence.PROTEIN_SEQTYPE)

from pygrdata_test import PygrSwissprotBase
class Blast_Test(PygrSwissprotBase):
    @skip_errors(OSError,KeyError)
    def setup(self):
        PygrSwissprotBase.setup(self)
        import pygr.Data
        self.sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        self.sp.formatdb()
    def blast_test(self):
        hbb = self.sp['HBB1_TORMA']
        hits = self.sp.blast(hbb)
        edges = hits[hbb].edges(maxgap=1,maxinsert=1,
                                minAlignSize=14,pIdentityMin=0.5)
        for t in edges:
            assert len(t[0])>=14, 'result shorter than minAlignSize!'
        result = [(t[0],t[1],t[2].pIdentity()) for t in edges]
        store = PygrDataTextFile('results/seqdb1.pickle')
        correct = store['hbb blast 1']
        assert approximate_cmp(result,correct,.0001)==0, 'blast results should match'
        result = [(t[0],t[1],t[2].pIdentity()) for t in hits[hbb].generateSeqEnds()]
        correct = store['hbb blast 2']
        assert approximate_cmp(result,correct,.0001)==0, 'blast results should match'
        trypsin = self.sp['PRCA_ANASP']
        try:
            hits[trypsin]
            raise ValueError('failed to catch bad alignment query')
        except KeyError:
            pass
