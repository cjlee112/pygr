from itertools import *
import unittest
from testlib import testutil, logger
import pygr.Data
from pygr import sequence, cnestedlist, seqdb, blast

class Blast_Test(unittest.TestCase):
    def setUp(self):
        tempdir = testutil.TempDir('blast-test')
        testutil.change_pygrdatapath(tempdir.path)

class Blastx_Test(unittest.TestCase):
    def test_blastx(self):
        "Testing blastx"

        hbb1_mouse = testutil.datafile('hbb1_mouse.fa')
        sp_hbb1 = testutil.datafile('sp_hbb1')

        dna = seqdb.SequenceFileDB(hbb1_mouse)
        prot = seqdb.SequenceFileDB(sp_hbb1)

        blastmap = blast.BlastxMapping(prot, verbose=False)
        
        correct = [(146, 146, 438, '0.979'), (146, 146, 438, '0.911'),
                   (146, 146, 438, '0.747'), (146, 146, 438, '0.664'),
                   (146, 146, 438, '0.623'), (146, 146, 438, '0.596'),
                   (145, 145, 435, '0.510'), (143, 143, 429, '0.531'),
                   (146, 146, 438, '0.473'), (146, 146, 438, '0.473'),
                   (146, 146, 438, '0.486'), (144, 144, 432, '0.451'),
                   (145, 145, 435, '0.455'), (144, 144, 432, '0.451'),
                   (146, 146, 438, '0.466'), (146, 146, 438, '0.459'),
                   (52, 52, 156, '0.442'), (90, 90, 270, '0.322'),
                   (23, 23, 69, '0.435'), (120, 120, 360, '0.283'),
                   (23, 23, 69, '0.435'), (120, 120, 360, '0.258'),
                   (23, 23, 69, '0.435'), (120, 120, 360, '0.275'),
                   (23, 23, 69, '0.435'), (120, 120, 360, '0.267')]
        
        results = blastmap[dna['gi|171854975|dbj|AB364477.1|']]
        
        found = []
        for result in results:
            for src,dest,edge in result.edges():
                found.append((len(src), len(dest), len(src.sequence),
                              '%0.3f' % edge.pIdentity()))

        # order it identically
        correct.sort()
        found.sort()

        # this is to help troubleshooting the mismatches if there are any
        mismatch = [ (a, b) for a, b in zip(correct, found) if a != b ]
        if mismatch:
            logger.warn('blastx mismatches found')
            for m in mismatch:
                logger.warn('%s != %s' % m)
        
        # this is the actual test
        self.assertEqual(correct, found)

        try:
            results = blastmap[ prot['HBB1_MOUSE'] ]
            raise AssertionError('failed to trap blastp in BlastxMapping')
        except ValueError:
            pass
                

class Blastn_Test(unittest.TestCase):
    def test_tblastn(self):
        "Blastn test"
        
        hbb1_mouse = testutil.datafile('hbb1_mouse.fa')
        sp_hbb1 = testutil.datafile('sp_hbb1')


        dna = seqdb.SequenceFileDB(hbb1_mouse)
        prot = seqdb.SequenceFileDB(sp_hbb1)
        blastmap = blast.BlastMapping(dna)
        result = blastmap[prot['HBB1_XENLA']]
        src,dest,edge = iter(result.edges()).next()
        
        self.assertEqual(str(src),
            'LTAHDRQLINSTWGKLCAKTIGQEALGRLLWTYPWTQRYFSSFGNLNSADAVFHNEAVAAHGEK'
            'VVTSIGEAIKHMDDIKGYYAQLSKYHSETLHVDPLNFKRFGGCLSIALARHFHEEYTPELHAAY'
            'EHLFDAIADALGKGYH')
        self.assertEqual(str(dest),
            'LTDAEKAAVSGLWGKVNSDEVGGEALGRLLVVYPWTQRYFDSFGDLSSASAIMGNAKVKAHGKK'
            'VITAFNEGLNHLDSLKGTFASLSELHCDKLHVDPENFRLLGNMIVIVLGHHLGKDFTPAAQAAF'
            'QKVMAGVATALAHKYH')
        self.assertEqual(str(dest.sequence),
            'CTGACTGATGCTGAGAAGGCTGCTGTCTCTGGCCTGTGGGGAAAGGTGAACTCCGATGAAGTTG'
            'GTGGTGAGGCCCTGGGCAGGCTGCTGGTTGTCTACCCTTGGACCCAGAGGTACTTTGATAGCTT'
            'TGGAGACCTATCCTCTGCCTCTGCTATCATGGGTAATGCCAAAGTGAAGGCCCATGGCAAGAAA'
            'GTGATAACTGCCTTTAACGAGGGCCTGAATCACTTGGACAGCCTCAAGGGCACCTTTGCCAGCC'
            'TCAGTGAGCTCCACTGTGACAAGCTCCATGTGGATCCTGAGAACTTCAGGCTCCTGGGCAATAT'
            'GATCGTGATTGTGCTGGGCCACCACCTGGGCAAGGATTTCACCCCCGCTGCACAGGCTGCCTTC'
            'CAGAAGGTGATGGCTGGAGTGGCCACTGCCCTGGCTCACAAGTACCAC')
        
        self.assertAlmostEqual(edge.pIdentity(), 0.451, 3)

        blastmap = blast.BlastMapping(prot)
        try:
            results = blastmap[dna['gi|171854975|dbj|AB364477.1|']]
            raise AssertionError('failed to trap blastx in BlastMapping')
        except ValueError:
            pass

    def test_bad_subject(self):
        "Test bad subjects"

        # file not added to repository
        from pygr import parse_blast
        from pygr.nlmsa_utils import CoordsGroupStart,CoordsGroupEnd

        correctCoords = ((12,63,99508,99661),
                 (65,96,99661,99754),
                 (96,108,99778,99814),
                 (108,181,99826,100045))
        
        fp = file(testutil.datafile('bad_tblastn.txt'))
        try:
            p = parse_blast.BlastHitParser()
            it = iter(correctCoords)
            for ival in p.parse_file(fp):
                if not isinstance(ival,(CoordsGroupStart,
                            CoordsGroupEnd)):
                    assert (ival.src_start,ival.src_end,
                        ival.dest_start,ival.dest_end) \
                        == it.next()
        finally:
            fp.close()

def all_vs_all_blast_save():
    """
    Creates the blast files used during testing. 
    Must be called before running the tests
    """

    tempdir = testutil.TempDir('blast-test')
    testutil.change_pygrdatapath(tempdir.path)

    sp_hbb1 = testutil.datafile('sp_hbb1')
    all_vs_all = testutil.tempdatafile('all_vs_all')

    sp = seqdb.BlastDB(sp_hbb1)
    msa = cnestedlist.NLMSA(all_vs_all ,mode='w', pairwiseMode=True, bidirectional=False)
    
    # get strong homologs, save alignment in msa for every sequence
    reader = islice(sp.iteritems(), None)
    for id, s in reader:
        sp.blast(s, msa, expmax=1e-10, verbose=False) 

    # done constructing the alignment, so build the alignment db indexes
    msa.build(saveSeqDict=True) 

    db = msa.seqDict.dicts.keys()[0]
    working, result = {}, {}
    for k in db.values():
        edges = msa[k].edges(minAlignSize=12, pIdentityMin=0.5)
        for t in edges:
            assert len(t[0]) >= 12
        tmpdict = dict(map(lambda x:(x, None), [(str(t[0]), str(t[1]), t[2].pIdentity(trapOverflow=False)) for t in edges]))
        result[repr(k)] = tmpdict.keys()
        result[repr(k)].sort()
    
    # save it into pygr.Data
    data = testutil.TestData()
    data.__doc__ = 'sp_allvall'
    data.result = result
    pygr.Data.Bio.Blast = data
    pygr.Data.save()

    #return msa

def get_suite():
    "Returns the testsuite"

    # save the data that will be tested
    # all_vs_all_blast_save()

    tests  = [ 
        Blast_Test,
        Blastx_Test,
        Blastn_Test,
    ]

    return testutil.make_suite(tests)

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)

