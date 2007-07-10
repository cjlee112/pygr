import unittest
from pygr import sequence

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
