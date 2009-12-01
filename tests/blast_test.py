from itertools import *
import re
import unittest
import glob
import os
from testlib import testutil, SkipTest, PygrTestProgram
from pygr import worldbase
from pygr import sequence, cnestedlist, seqdb, blast, logger, parse_blast
from pygr.nlmsa_utils import CoordsGroupStart, CoordsGroupEnd
from pygr import translationDB


def check_results(results, correct, formatter, delta=0.01,
                  reformatCorrect=False, reformatResults=True):
    if reformatResults:
        results = reformat_results(results, formatter)

    if reformatCorrect: # reformat these data too
        correct = reformat_results(correct, formatter)
    else:
        correct.sort()

    # this is to help troubleshooting the mismatches if there are any
    mismatch = [(a, b) for a, b in zip(correct, results) if
                 testutil.approximate_cmp([a], [b], delta)]
    if mismatch:
        logger.warn('blast mismatches found')
        for m in mismatch:
            logger.warn('%s != %s' % m)

    # this is the actual test
    assert testutil.approximate_cmp(correct, results, delta) == 0


def check_results_relaxed_blastp(results, correct, formatter, delta=0.01,
                                 reformatCorrect=False, allowedLengthDiff=0,
                                 identityMin=0.6, reformatResults=True):
    if reformatResults:
        results = reformat_results(results, formatter)

    if reformatCorrect: # reformat these data too
        correct = reformat_results(correct, formatter)
    else:
        correct.sort()

    # Length of output
    assert abs(len(results) - len(correct)) <= allowedLengthDiff

    # Format check
    key_re = re.compile('^[A-Z]{3}[A-Z0-9]?_[A-Z]{2,5}$')
    for result in results:
        assert key_re.search(result[0])
        assert key_re.search(result[1])
        assert (0. < result[2] and result[2] <= 1.)

    # High-identity comparison
    results_high = []
    correct_high = []
    for result in results:
        if result[2] > identityMin:
            results_high.append(result)
    for result in correct:
        if result[2] > identityMin:
            correct_high.append(result)
    assert testutil.approximate_cmp(correct_high, results_high, delta) == 0


def check_results_relaxed_blastx(results, correct, formatter, delta=0.01,
                                 reformatCorrect=False, allowedLengthDiff=0,
                                 identityMin=0.6):
    results = reformat_results(results, formatter)

    if reformatCorrect: # reformat these data too
        correct = reformat_results(correct, formatter)
    else:
        correct.sort()

    # Length of output
    assert abs(len(results) - len(correct)) <= allowedLengthDiff

    # Format check
    for result in results:
        assert 3 * result[0] == result[2]
        assert (0. < result[3] and result[3] <= 1.)

    # High-identity comparison
    results_high = []
    correct_high = []
    for result in results:
        if result[3] > identityMin:
            results_high.append(result)
    for result in correct:
        if result[3] > identityMin:
            correct_high.append(result)
    assert testutil.approximate_cmp(correct_high, results_high, delta) == 0


def reformat_results(results, formatter):
    reffed = []
    for result in results:
        for t in result.edges(mergeMost=True):
            reffed.append(formatter(t))
    reffed.sort()
    return reffed


def pair_identity_tuple(t):
    'standard formatter for blast matches'
    return (t[0].id, t[1].id, t[2].pIdentity())


class BlastBase(unittest.TestCase):

    def setUp(self):
        hbb1_mouse = testutil.datafile('hbb1_mouse.fa')
        hbb1_mouse_rc = testutil.datafile('hbb1_mouse_rc.fa')
        sp_hbb1 = testutil.datafile('sp_hbb1')
        gapping = testutil.datafile('gapping.fa')

        self.dna = seqdb.SequenceFileDB(hbb1_mouse)
        self.dna_rc = seqdb.SequenceFileDB(hbb1_mouse_rc)
        self.prot = seqdb.SequenceFileDB(sp_hbb1)
        self.gapping = seqdb.SequenceFileDB(gapping)

    def tearDown(self):
        'do the RIGHT thing... close resources that have been opened!'
        self.dna.close()
        self.dna_rc.close()
        self.prot.close()
        self.gapping.close()


_multiblast_results = None


class Blast_Test(BlastBase):
    """
    Test basic BLAST stuff (using blastp).
    """

    def test_blastp(self):
        "Testing blastp"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.prot, verbose=False)
        results = blastmap[self.prot['HBB1_XENLA']]

        check_results_relaxed_blastp([results], blastp_correct_results,
                                     pair_identity_tuple,
                                     allowedLengthDiff=2)

    def test_repr(self):
        blastmap = blast.BlastMapping(self.prot, verbose=False)
        assert '<BlastMapping' in repr(blastmap)

    def test_no_query(self):
        blastmap = blast.BlastMapping(self.dna, verbose=False)
        try:
            blastmap()
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_both_seq_and_db(self):
        "Testing db arg present"
        blastmap = blast.BlastMapping(self.prot, verbose=False)
        seq = self.prot['HBB1_XENLA']

        try:
            blastmap(seq=seq, queryDB=self.prot)
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_multiblast(self):
        "testing multi sequence blast"
        results = self.get_multiblast_results()
        check_results_relaxed_blastp(results, correct_multiblast_results,
                                     None, reformatResults=False,
                                     allowedLengthDiff=10)

    def get_multiblast_results(self):
        """return saved results or generate them if needed;
        results are saved so we only do this time-consuming operation once"""
        global _multiblast_results

        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        if not _multiblast_results:
            logger.info("running expensive multiblast")
            blastmap = blast.BlastMapping(self.prot, verbose=False)
            al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                                   bidirectional=False)

            blastmap(al=al, queryDB=self.prot) # all vs all

            al.build() # construct the alignment indexes
            results = [al[seq] for seq in self.prot.values()]
            _multiblast_results = reformat_results(results,
                                                   pair_identity_tuple)

        return _multiblast_results

    def test_multiblast_single(self):
        "Test multi-sequence BLAST results, for BLASTs run one by one."
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.prot, verbose=False)
        al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                               bidirectional=False)

        for seq in self.prot.values():
            blastmap(seq, al) # all vs all, one by one

        al.build() # construct the alignment indexes
        results = [al[seq] for seq in self.prot.values()]
        results_multi = self.get_multiblast_results()
        # Strict check must work here even on live BLAST output
        check_results(results, results_multi, pair_identity_tuple)

    def test_multiblast_long(self):
        "testing multi sequence blast with long db"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        longerFile = testutil.datafile('sp_all_hbb')

        sp_all_hbb = seqdb.SequenceFileDB(longerFile)
        blastmap = blast.BlastMapping(self.prot, verbose=False)
        al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                               bidirectional=False)
        blastmap(None, al, queryDB=sp_all_hbb) # all vs all
        al.build() # construct the alignment indexes

    def test_maskEnd(self):
        """
        This tests against a minor bug in cnestedlist where maskEnd
        is used to clip the end to the mask region.
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        db = self.gapping
        blastmap = blast.BlastMapping(db)
        ungapped = db['ungapped']
        gapped = db['gapped']
        results = blastmap[gapped]

        results[ungapped]

    def test_no_bidirectional(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        db = self.gapping
        gapped = db['gapped']
        ungapped = db['ungapped']

        blastmap = blast.BlastMapping(db)
        al = blastmap(queryDB=db)
        slice = al[gapped]

        found_once = False
        for src, dest, edge in al[gapped].edges():
            if src == gapped[0:40] and dest == ungapped[0:40]:
                assert not found_once, \
                       "BLAST results should not be bidirectional"
                found_once = True

        assert found_once, "should have found this match exactly once!"

    def test_formatdb_fail(self):
        db = self.gapping
        try:
            blastmap = blast.BlastMapping(db, filepath='foobarbaz.fa',
                                          blastReady=True,
                                          showFormatdbMessages=False)
            assert 0, "should not reach this point"
        except IOError:                 # should fail with 'cannot build'
            pass

        remnants = glob.glob('foobarbaz.fa.n??')
        for filename in remnants:
            os.unlink(filename)

    def test_seq_without_db(self):
        "Check that sequences without associated DBs work as query strings"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastMapping(self.prot, verbose=False)

        seq = self.prot['HBB1_XENLA']
        seq_no_db = sequence.Sequence(str(seq), 'HBB1_XENLA_no_db')
        slice = blastmap(seq=seq_no_db)[seq_no_db]
        assert len(slice)


class Blastx_Test(BlastBase):

    def test_blastx(self):
        "Testing blastx"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        correct = [(143, 143, 429, 0.53146853146853146),
                   (143, 145, 429, 0.28275862068965518),
                   (143, 145, 429, 0.28965517241379313),
                   (143, 145, 429, 0.29655172413793102),
                   (143, 145, 429, 0.30344827586206896),
                   (144, 144, 432, 0.4513888888888889),
                   (144, 144, 432, 0.4513888888888889),
                   (145, 145, 435, 0.45517241379310347),
                   (145, 145, 435, 0.51034482758620692),
                   (146, 142, 438, 0.35616438356164382),
                   (146, 146, 438, 0.4589041095890411),
                   (146, 146, 438, 0.46575342465753422),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4863013698630137),
                   (146, 146, 438, 0.59589041095890416),
                   (146, 146, 438, 0.62328767123287676),
                   (146, 146, 438, 0.66438356164383561),
                   (146, 146, 438, 0.74657534246575341),
                   (146, 146, 438, 0.91095890410958902),
                   (146, 146, 438, 0.97945205479452058)]

        results = blastmap[self.dna['gi|171854975|dbj|AB364477.1|']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

    def test_blastx_rc(self):
        "Testing blastx with negative frames"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        correct = [(143, 143, 429, 0.53146853146853146),
                   (143, 145, 429, 0.28275862068965518),
                   (143, 145, 429, 0.28965517241379313),
                   (143, 145, 429, 0.29655172413793102),
                   (143, 145, 429, 0.30344827586206896),
                   (144, 144, 432, 0.4513888888888889),
                   (144, 144, 432, 0.4513888888888889),
                   (145, 145, 435, 0.45517241379310347),
                   (145, 145, 435, 0.51034482758620692),
                   (146, 142, 438, 0.35616438356164382),
                   (146, 146, 438, 0.4589041095890411),
                   (146, 146, 438, 0.46575342465753422),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4863013698630137),
                   (146, 146, 438, 0.59589041095890416),
                   (146, 146, 438, 0.62328767123287676),
                   (146, 146, 438, 0.66438356164383561),
                   (146, 146, 438, 0.74657534246575341),
                   (146, 146, 438, 0.91095890410958902),
                   (146, 146, 438, 0.97945205479452058)]

        results = blastmap[self.dna_rc['hbb1_mouse_RC']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

        results = blastmap[self.dna_rc['hbb1_mouse_RC_2']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

        results = blastmap[self.dna_rc['hbb1_mouse_RC_3']]
        check_results_relaxed_blastx(results, correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()), allowedLengthDiff=2)

    def test_repr(self):
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        assert '<BlastxMapping' in repr(blastmap)

    def test_blastx_no_blastp(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        try:
            results = blastmap(self.prot['HBB1_MOUSE'])
            raise AssertionError('failed to trap blastp in BlastxMapping')
        except ValueError:
            pass

    def test_no_query(self):
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        try:
            blastmap()
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_both_seq_and_db(self):
        "Testing blastp"
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        seq = self.prot['HBB1_XENLA']

        try:
            blastmap(seq=seq, queryDB=self.prot)
            assert 0, "should fail before this"
        except ValueError:
            pass

    def test_translation_db_in_results_of_db_search(self):
        """
        Test that the NLMSA in a BlastxMapping properly picks up the
        translationDB from the query sequence dict.
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)
        results = blastmap(queryDB=self.dna)

        tdb = translationDB.get_translation_db(self.dna)
        assert tdb.annodb in results.seqDict.dicts

    def test_translation_db_in_results_of_seq_search(self):
        """
        Test that the NLMSA in a BlastxMapping properly picks up the
        translationDB from a single input sequence.
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        query_seq = self.dna['gi|171854975|dbj|AB364477.1|']
        results = blastmap(seq=query_seq)

        tdb = translationDB.get_translation_db(self.dna)
        assert tdb.annodb in results.seqDict.dicts

    def test_translated_seqs_in_results(self):
        """
        Only NLMSASlices for the query sequence should show up in
        BlastxMapping.__getitem__, right?
        """
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        query_seq = self.dna['gi|171854975|dbj|AB364477.1|']
        results = blastmap[query_seq]

        tdb = translationDB.get_translation_db(self.dna)
        annodb = tdb.annodb

        for slice in results:
            assert slice.seq.id in annodb, '%s not in annodb!' % slice.seq.id

    def test_non_consumable_results(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")
        blastmap = blast.BlastxMapping(self.prot, verbose=False)

        query_seq = self.dna['gi|171854975|dbj|AB364477.1|']
        results = blastmap[query_seq]

        x = list(results)
        y = list(results)

        assert len(x), x
        assert x == y, "BlastxMapping.__getitem__ should return list"


class Tblastn_Test(BlastBase):

    def test_tblastn(self):
        "tblastn test"
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.dna, verbose=False)
        correct = [(144, 144, 432, 0.451)]

        result = blastmap[self.prot['HBB1_XENLA']]
        check_results_relaxed_blastx([result], correct,
                      lambda t: (len(t[1]), len(t[0]), len(t[1].sequence),
                                 t[2].pIdentity()))

    def test_tblastn_no_blastx(self):
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.BlastMapping(self.prot)
        try:
            results = blastmap[self.dna['gi|171854975|dbj|AB364477.1|']]
            raise AssertionError('failed to trap blastx in BlastMapping')
        except ValueError:
            pass

    def test_megablast(self):
        '''test megablast'''
        if not testutil.blast_enabled():
            raise SkipTest("no BLAST installed")

        blastmap = blast.MegablastMapping(self.dna, verbose=False)
        # must use copy of sequence to get "self matches" from NLMSA...
        query = seqdb.Sequence(str(self.dna['gi|171854975|dbj|AB364477.1|']),
                               'foo')
        try:
            result = blastmap[query]
        except OSError: # silently ignore missing RepeatMasker, megablast
            return
        found = [(len(t[0]), len(t[1])) for t in result.edges()]
        assert found == [(444, 444)]

    def test_megablast_repr(self):
        blastmap = blast.MegablastMapping(self.dna, verbose=False)
        assert '<MegablastMapping' in repr(blastmap)

    def test_bad_subject(self):
        "Test bad subjects"

        correctCoords = ((12, 63, 99508, 99661),
                         (65, 96, 99661, 99754),
                         (96, 108, 99778, 99814),
                         (108, 181, 99826, 100045))

        fp = file(testutil.datafile('bad_tblastn.txt'))
        try:
            p = parse_blast.BlastHitParser()
            it = iter(correctCoords)
            for ival in p.parse_file(fp):
                if not isinstance(ival, (CoordsGroupStart, CoordsGroupEnd)):
                    assert (ival.src_start, ival.src_end,
                            ival.dest_start, ival.dest_end) \
                        == it.next()
        finally:
            fp.close()


class BlastParsers_Test(BlastBase):

    def test_blastp_parser(self):
        "Testing blastp parser"
        blastp_output = open(testutil.datafile('blastp_output.txt'), 'r')

        seq_dict = {'HBB1_XENLA': self.prot['HBB1_XENLA']}
        prot_index = blast.BlastIDIndex(self.prot)
        try:
            alignment = blast.read_blast_alignment(blastp_output, seq_dict,
                                                   prot_index)
            results = alignment[self.prot['HBB1_XENLA']]
        finally:
            blastp_output.close()

        check_results([results], blastp_correct_results, pair_identity_tuple)

    def test_multiblast_parser(self):
        "Testing multiblast parser"
        multiblast_output = open(testutil.datafile('multiblast_output.txt'),
                                 'r')

        try:
            al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                                   bidirectional=False)
            al = blast.read_blast_alignment(multiblast_output, self.prot,
                                            blast.BlastIDIndex(self.prot), al)
        finally:
            multiblast_output.close()
        al.build()
        results = [al[seq] for seq in self.prot.values()]

        check_results(results, correct_multiblast_results,
                      pair_identity_tuple)

    def test_multiblast_parser_long(self):
        "Testing multiblast parser with long input"
        longerFile = testutil.datafile('sp_all_hbb')
        sp_all_hbb = seqdb.SequenceFileDB(longerFile)

        filename = testutil.datafile('multiblast_long_output.txt')
        multiblast_output = open(filename, 'r')
        try:
            al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                                   bidirectional=False)
            al = blast.read_blast_alignment(multiblast_output, sp_all_hbb,
                                            self.prot, al)
        finally:
            multiblast_output.close()
        al.build()

        results = []
        for seq in sp_all_hbb.values():
            try:
                results.append(al[seq])
            except KeyError:
                pass
        correctfile = file(testutil.datafile('multiblast_long_correct.txt'),
                           'r')
        try:
            correct = []
            for line in correctfile:
                t = line.split()
                correct.append((t[0], t[1], float(t[2])))
        finally:
            correctfile.close()
        check_results(results, correct, pair_identity_tuple)

    def test_blastx_parser(self):
        "Testing blastx parser"
        blastx_output = open(testutil.datafile('blastx_output.txt'), 'r')
        seq_dict = {'gi|171854975|dbj|AB364477.1|':
                    self.dna['gi|171854975|dbj|AB364477.1|']}
        try:
            results = blast.read_blast_alignment(blastx_output,
                                                 seq_dict,
                                                 blast.BlastIDIndex(self.prot),
                                                 translateSrc=True)
        finally:
            blastx_output.close()
        correct = [(143, 143, 429, 0.53146853146853146),
                   (143, 145, 429, 0.28275862068965518),
                   (143, 145, 429, 0.28965517241379313),
                   (143, 145, 429, 0.29655172413793102),
                   (143, 145, 429, 0.30344827586206896),
                   (144, 144, 432, 0.4513888888888889),
                   (144, 144, 432, 0.4513888888888889),
                   (145, 145, 435, 0.45517241379310347),
                   (145, 145, 435, 0.51034482758620692),
                   (146, 142, 438, 0.35616438356164382),
                   (146, 146, 438, 0.4589041095890411),
                   (146, 146, 438, 0.46575342465753422),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4726027397260274),
                   (146, 146, 438, 0.4863013698630137),
                   (146, 146, 438, 0.59589041095890416),
                   (146, 146, 438, 0.62328767123287676),
                   (146, 146, 438, 0.66438356164383561),
                   (146, 146, 438, 0.74657534246575341),
                   (146, 146, 438, 0.91095890410958902),
                   (146, 146, 438, 0.97945205479452058)]

        check_results([results], correct,
                      lambda t: (len(t[0]), len(t[1]), len(t[0].sequence),
                                 t[2].pIdentity()))

    def test_tblastn_parser(self):
        "Testing tblastn parser"
        seq_dict = {'HBB1_XENLA': self.prot['HBB1_XENLA']}
        dna_db = blast.BlastIDIndex(self.dna)
        tblastn_output = open(testutil.datafile('tblastn_output.txt'), 'r')
        try:
            al = blast.read_blast_alignment(tblastn_output, seq_dict,
                                            dna_db, translateDest=True)
            result = al[self.prot['HBB1_XENLA']]
        finally:
            tblastn_output.close()
        src, dest, edge = iter(result.edges()).next()

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


# not used currently
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
    msa = cnestedlist.NLMSA(all_vs_all, mode='w', pairwiseMode=True,
                            bidirectional=False)

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
        tmpdict = dict(map(lambda x: (x, None),
                           [(str(t[0]), str(t[1]),
                             t[2].pIdentity(trapOverflow=False)) for t in
                            edges]))
        result[repr(k)] = tmpdict.keys()
        result[repr(k)].sort()

    # save it into worldbase
    data = testutil.TestData()
    data.__doc__ = 'sp_allvall'
    data.result = result
    worldbase.Bio.Blast = data
    worldbase.commit()

    #return msa

###

blastp_correct_results = \
        [('HBB1_XENLA', 'HBB0_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_ANAMI', 0.45323741007194246),
         ('HBB1_XENLA', 'HBB1_CYGMA', 0.46715328467153283),
         ('HBB1_XENLA', 'HBB1_IGUIG', 0.48951048951048953),
         ('HBB1_XENLA', 'HBB1_MOUSE', 0.44444444444444442),
         ('HBB1_XENLA', 'HBB1_ONCMY', 0.39436619718309857),
         ('HBB1_XENLA', 'HBB1_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_RAT', 0.45833333333333331),
         ('HBB1_XENLA', 'HBB1_SPHPU', 0.4825174825174825),
         ('HBB1_XENLA', 'HBB1_TAPTE', 0.47222222222222221),
         ('HBB1_XENLA', 'HBB1_TORMA', 0.33793103448275863),
         ('HBB1_XENLA', 'HBB1_TRICR', 0.49305555555555558),
         ('HBB1_XENLA', 'HBB1_UROHA', 0.3776223776223776),
         ('HBB1_XENLA', 'HBB1_VAREX', 0.5174825174825175),
         ('HBB1_XENLA', 'HBB1_XENBO', 0.96551724137931039),
         ('HBB1_XENLA', 'HBB1_XENLA', 1.0),
         ('HBB1_XENLA', 'HBB1_XENTR', 0.75),
         ('HBB1_XENLA', 'MYG_DIDMA', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ELEMA', 0.26415094339622641),
         ('HBB1_XENLA', 'MYG_ERIEU', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ESCGI', 0.28282828282828282),
         ('HBB1_XENLA', 'MYG_GALCR', 0.32075471698113206)]


correct_multiblast_results = \
        [('HBB0_PAGBO', 'HBB0_PAGBO', 1.0),
         ('HBB0_PAGBO', 'HBB1_ANAMI', 0.66896551724137931),
         ('HBB0_PAGBO', 'HBB1_CYGMA', 0.68493150684931503),
         ('HBB0_PAGBO', 'HBB1_IGUIG', 0.4863013698630137),
         ('HBB0_PAGBO', 'HBB1_MOUSE', 0.45205479452054792),
         ('HBB0_PAGBO', 'HBB1_ONCMY', 0.55172413793103448),
         ('HBB0_PAGBO', 'HBB1_PAGBO', 0.69178082191780821),
         ('HBB0_PAGBO', 'HBB1_RAT', 0.4589041095890411),
         ('HBB0_PAGBO', 'HBB1_SPHPU', 0.4589041095890411),
         ('HBB0_PAGBO', 'HBB1_TAPTE', 0.4863013698630137),
         ('HBB0_PAGBO', 'HBB1_TORMA', 0.31506849315068491),
         ('HBB0_PAGBO', 'HBB1_TRICR', 0.4375),
         ('HBB0_PAGBO', 'HBB1_UROHA', 0.4041095890410959),
         ('HBB0_PAGBO', 'HBB1_VAREX', 0.49315068493150682),
         ('HBB0_PAGBO', 'HBB1_XENBO', 0.43356643356643354),
         ('HBB0_PAGBO', 'HBB1_XENLA', 0.44055944055944057),
         ('HBB0_PAGBO', 'HBB1_XENTR', 0.4726027397260274),
         ('HBB0_PAGBO', 'MYG_DIDMA', 0.22222222222222221),
         ('HBB0_PAGBO', 'MYG_ELEMA', 0.20833333333333334),
         ('HBB0_PAGBO', 'MYG_ERIEU', 0.21527777777777779),
         ('HBB0_PAGBO', 'MYG_ESCGI', 0.25),
         ('HBB0_PAGBO', 'MYG_GALCR', 0.24305555555555555),
         ('HBB1_ANAMI', 'HBB0_PAGBO', 0.66896551724137931),
         ('HBB1_ANAMI', 'HBB1_ANAMI', 1.0),
         ('HBB1_ANAMI', 'HBB1_CYGMA', 0.75862068965517238),
         ('HBB1_ANAMI', 'HBB1_IGUIG', 0.47586206896551725),
         ('HBB1_ANAMI', 'HBB1_MOUSE', 0.45517241379310347),
         ('HBB1_ANAMI', 'HBB1_ONCMY', 0.59310344827586203),
         ('HBB1_ANAMI', 'HBB1_PAGBO', 0.75862068965517238),
         ('HBB1_ANAMI', 'HBB1_RAT', 0.48965517241379308),
         ('HBB1_ANAMI', 'HBB1_SPHPU', 0.46206896551724136),
         ('HBB1_ANAMI', 'HBB1_TAPTE', 0.48965517241379308),
         ('HBB1_ANAMI', 'HBB1_TORMA', 0.32413793103448274),
         ('HBB1_ANAMI', 'HBB1_TRICR', 0.41258741258741261),
         ('HBB1_ANAMI', 'HBB1_UROHA', 0.38620689655172413),
         ('HBB1_ANAMI', 'HBB1_VAREX', 0.48275862068965519),
         ('HBB1_ANAMI', 'HBB1_XENBO', 0.4460431654676259),
         ('HBB1_ANAMI', 'HBB1_XENLA', 0.45323741007194246),
         ('HBB1_ANAMI', 'HBB1_XENTR', 0.4689655172413793),
         ('HBB1_CYGMA', 'HBB0_PAGBO', 0.68493150684931503),
         ('HBB1_CYGMA', 'HBB1_ANAMI', 0.75862068965517238),
         ('HBB1_CYGMA', 'HBB1_CYGMA', 1.0),
         ('HBB1_CYGMA', 'HBB1_IGUIG', 0.5),
         ('HBB1_CYGMA', 'HBB1_MOUSE', 0.47945205479452052),
         ('HBB1_CYGMA', 'HBB1_ONCMY', 0.53103448275862064),
         ('HBB1_CYGMA', 'HBB1_PAGBO', 0.86986301369863017),
         ('HBB1_CYGMA', 'HBB1_RAT', 0.50684931506849318),
         ('HBB1_CYGMA', 'HBB1_SPHPU', 0.47945205479452052),
         ('HBB1_CYGMA', 'HBB1_TAPTE', 0.4726027397260274),
         ('HBB1_CYGMA', 'HBB1_TORMA', 0.33561643835616439),
         ('HBB1_CYGMA', 'HBB1_TRICR', 0.4375),
         ('HBB1_CYGMA', 'HBB1_UROHA', 0.36986301369863012),
         ('HBB1_CYGMA', 'HBB1_VAREX', 0.4863013698630137),
         ('HBB1_CYGMA', 'HBB1_XENBO', 0.45985401459854014),
         ('HBB1_CYGMA', 'HBB1_XENLA', 0.46715328467153283),
         ('HBB1_CYGMA', 'HBB1_XENTR', 0.47945205479452052),
         ('HBB1_CYGMA', 'MYG_ESCGI', 0.2361111111111111),
         ('HBB1_IGUIG', 'HBB0_PAGBO', 0.4863013698630137),
         ('HBB1_IGUIG', 'HBB1_ANAMI', 0.47586206896551725),
         ('HBB1_IGUIG', 'HBB1_CYGMA', 0.5),
         ('HBB1_IGUIG', 'HBB1_IGUIG', 1.0),
         ('HBB1_IGUIG', 'HBB1_MOUSE', 0.63013698630136983),
         ('HBB1_IGUIG', 'HBB1_ONCMY', 0.51034482758620692),
         ('HBB1_IGUIG', 'HBB1_PAGBO', 0.4863013698630137),
         ('HBB1_IGUIG', 'HBB1_RAT', 0.61643835616438358),
         ('HBB1_IGUIG', 'HBB1_SPHPU', 0.71232876712328763),
         ('HBB1_IGUIG', 'HBB1_TAPTE', 0.64383561643835618),
         ('HBB1_IGUIG', 'HBB1_TORMA', 0.36301369863013699),
         ('HBB1_IGUIG', 'HBB1_TRICR', 0.47916666666666669),
         ('HBB1_IGUIG', 'HBB1_UROHA', 0.64383561643835618),
         ('HBB1_IGUIG', 'HBB1_VAREX', 0.77397260273972601),
         ('HBB1_IGUIG', 'HBB1_XENBO', 0.4825174825174825),
         ('HBB1_IGUIG', 'HBB1_XENLA', 0.48951048951048953),
         ('HBB1_IGUIG', 'HBB1_XENTR', 0.49315068493150682),
         ('HBB1_IGUIG', 'MYG_DIDMA', 0.25179856115107913),
         ('HBB1_IGUIG', 'MYG_ERIEU', 0.28368794326241137),
         ('HBB1_IGUIG', 'MYG_ESCGI', 0.27659574468085107),
         ('HBB1_IGUIG', 'MYG_GALCR', 0.28368794326241137),
         ('HBB1_MOUSE', 'HBB0_PAGBO', 0.45205479452054792),
         ('HBB1_MOUSE', 'HBB1_ANAMI', 0.45517241379310347),
         ('HBB1_MOUSE', 'HBB1_CYGMA', 0.47945205479452052),
         ('HBB1_MOUSE', 'HBB1_IGUIG', 0.63013698630136983),
         ('HBB1_MOUSE', 'HBB1_MOUSE', 1.0),
         ('HBB1_MOUSE', 'HBB1_ONCMY', 0.50344827586206897),
         ('HBB1_MOUSE', 'HBB1_PAGBO', 0.4726027397260274),
         ('HBB1_MOUSE', 'HBB1_RAT', 0.9178082191780822),
         ('HBB1_MOUSE', 'HBB1_SPHPU', 0.65753424657534243),
         ('HBB1_MOUSE', 'HBB1_TAPTE', 0.76027397260273977),
         ('HBB1_MOUSE', 'HBB1_TORMA', 0.35616438356164382),
         ('HBB1_MOUSE', 'HBB1_TRICR', 0.52083333333333337),
         ('HBB1_MOUSE', 'HBB1_UROHA', 0.47945205479452052),
         ('HBB1_MOUSE', 'HBB1_VAREX', 0.6095890410958904),
         ('HBB1_MOUSE', 'HBB1_XENBO', 0.44444444444444442),
         ('HBB1_MOUSE', 'HBB1_XENLA', 0.44444444444444442),
         ('HBB1_MOUSE', 'HBB1_XENTR', 0.4589041095890411),
         ('HBB1_MOUSE', 'MYG_DIDMA', 0.29655172413793102),
         ('HBB1_MOUSE', 'MYG_ELEMA', 0.27586206896551724),
         ('HBB1_MOUSE', 'MYG_ERIEU', 0.30344827586206896),
         ('HBB1_MOUSE', 'MYG_ESCGI', 0.28965517241379313),
         ('HBB1_MOUSE', 'MYG_GALCR', 0.28275862068965518),
         ('HBB1_ONCMY', 'HBB0_PAGBO', 0.55172413793103448),
         ('HBB1_ONCMY', 'HBB1_ANAMI', 0.59310344827586203),
         ('HBB1_ONCMY', 'HBB1_CYGMA', 0.53103448275862064),
         ('HBB1_ONCMY', 'HBB1_IGUIG', 0.51034482758620692),
         ('HBB1_ONCMY', 'HBB1_MOUSE', 0.50344827586206897),
         ('HBB1_ONCMY', 'HBB1_ONCMY', 1.0),
         ('HBB1_ONCMY', 'HBB1_PAGBO', 0.56551724137931036),
         ('HBB1_ONCMY', 'HBB1_RAT', 0.50344827586206897),
         ('HBB1_ONCMY', 'HBB1_SPHPU', 0.46206896551724136),
         ('HBB1_ONCMY', 'HBB1_TAPTE', 0.50344827586206897),
         ('HBB1_ONCMY', 'HBB1_TORMA', 0.33793103448275863),
         ('HBB1_ONCMY', 'HBB1_TRICR', 0.41258741258741261),
         ('HBB1_ONCMY', 'HBB1_UROHA', 0.44827586206896552),
         ('HBB1_ONCMY', 'HBB1_VAREX', 0.48965517241379308),
         ('HBB1_ONCMY', 'HBB1_XENBO', 0.40140845070422537),
         ('HBB1_ONCMY', 'HBB1_XENLA', 0.39436619718309857),
         ('HBB1_ONCMY', 'HBB1_XENTR', 0.39310344827586208),
         ('HBB1_ONCMY', 'MYG_DIDMA', 0.25694444444444442),
         ('HBB1_ONCMY', 'MYG_ERIEU', 0.2361111111111111),
         ('HBB1_ONCMY', 'MYG_ESCGI', 0.25),
         ('HBB1_ONCMY', 'MYG_GALCR', 0.24305555555555555),
         ('HBB1_PAGBO', 'HBB0_PAGBO', 0.69178082191780821),
         ('HBB1_PAGBO', 'HBB1_ANAMI', 0.75862068965517238),
         ('HBB1_PAGBO', 'HBB1_CYGMA', 0.86986301369863017),
         ('HBB1_PAGBO', 'HBB1_IGUIG', 0.4863013698630137),
         ('HBB1_PAGBO', 'HBB1_MOUSE', 0.4726027397260274),
         ('HBB1_PAGBO', 'HBB1_ONCMY', 0.56551724137931036),
         ('HBB1_PAGBO', 'HBB1_PAGBO', 1.0),
         ('HBB1_PAGBO', 'HBB1_RAT', 0.4863013698630137),
         ('HBB1_PAGBO', 'HBB1_SPHPU', 0.4726027397260274),
         ('HBB1_PAGBO', 'HBB1_TAPTE', 0.46575342465753422),
         ('HBB1_PAGBO', 'HBB1_TORMA', 0.34931506849315069),
         ('HBB1_PAGBO', 'HBB1_TRICR', 0.4375),
         ('HBB1_PAGBO', 'HBB1_UROHA', 0.35616438356164382),
         ('HBB1_PAGBO', 'HBB1_VAREX', 0.4726027397260274),
         ('HBB1_PAGBO', 'HBB1_XENBO', 0.43356643356643354),
         ('HBB1_PAGBO', 'HBB1_XENLA', 0.44055944055944057),
         ('HBB1_PAGBO', 'HBB1_XENTR', 0.47945205479452052),
         ('HBB1_RAT', 'HBB0_PAGBO', 0.4589041095890411),
         ('HBB1_RAT', 'HBB1_ANAMI', 0.48965517241379308),
         ('HBB1_RAT', 'HBB1_CYGMA', 0.50684931506849318),
         ('HBB1_RAT', 'HBB1_IGUIG', 0.61643835616438358),
         ('HBB1_RAT', 'HBB1_MOUSE', 0.9178082191780822),
         ('HBB1_RAT', 'HBB1_ONCMY', 0.50344827586206897),
         ('HBB1_RAT', 'HBB1_PAGBO', 0.4863013698630137),
         ('HBB1_RAT', 'HBB1_RAT', 1.0),
         ('HBB1_RAT', 'HBB1_SPHPU', 0.66438356164383561),
         ('HBB1_RAT', 'HBB1_TAPTE', 0.76712328767123283),
         ('HBB1_RAT', 'HBB1_TORMA', 0.35616438356164382),
         ('HBB1_RAT', 'HBB1_TRICR', 0.52777777777777779),
         ('HBB1_RAT', 'HBB1_UROHA', 0.5),
         ('HBB1_RAT', 'HBB1_VAREX', 0.62328767123287676),
         ('HBB1_RAT', 'HBB1_XENBO', 0.45833333333333331),
         ('HBB1_RAT', 'HBB1_XENLA', 0.45833333333333331),
         ('HBB1_RAT', 'HBB1_XENTR', 0.45205479452054792),
         ('HBB1_RAT', 'MYG_DIDMA', 0.29655172413793102),
         ('HBB1_RAT', 'MYG_ELEMA', 0.28275862068965518),
         ('HBB1_RAT', 'MYG_ERIEU', 0.29655172413793102),
         ('HBB1_RAT', 'MYG_ESCGI', 0.28275862068965518),
         ('HBB1_RAT', 'MYG_GALCR', 0.27586206896551724),
         ('HBB1_SPHPU', 'HBB0_PAGBO', 0.4589041095890411),
         ('HBB1_SPHPU', 'HBB1_ANAMI', 0.46206896551724136),
         ('HBB1_SPHPU', 'HBB1_CYGMA', 0.47945205479452052),
         ('HBB1_SPHPU', 'HBB1_IGUIG', 0.71232876712328763),
         ('HBB1_SPHPU', 'HBB1_MOUSE', 0.65753424657534243),
         ('HBB1_SPHPU', 'HBB1_ONCMY', 0.46206896551724136),
         ('HBB1_SPHPU', 'HBB1_PAGBO', 0.4726027397260274),
         ('HBB1_SPHPU', 'HBB1_RAT', 0.66438356164383561),
         ('HBB1_SPHPU', 'HBB1_SPHPU', 1.0),
         ('HBB1_SPHPU', 'HBB1_TAPTE', 0.63698630136986301),
         ('HBB1_SPHPU', 'HBB1_TORMA', 0.38356164383561642),
         ('HBB1_SPHPU', 'HBB1_TRICR', 0.47916666666666669),
         ('HBB1_SPHPU', 'HBB1_UROHA', 0.54109589041095896),
         ('HBB1_SPHPU', 'HBB1_VAREX', 0.69178082191780821),
         ('HBB1_SPHPU', 'HBB1_XENBO', 0.48951048951048953),
         ('HBB1_SPHPU', 'HBB1_XENLA', 0.4825174825174825),
         ('HBB1_SPHPU', 'HBB1_XENTR', 0.4726027397260274),
         ('HBB1_TAPTE', 'HBB0_PAGBO', 0.4863013698630137),
         ('HBB1_TAPTE', 'HBB1_ANAMI', 0.48965517241379308),
         ('HBB1_TAPTE', 'HBB1_CYGMA', 0.4726027397260274),
         ('HBB1_TAPTE', 'HBB1_IGUIG', 0.64383561643835618),
         ('HBB1_TAPTE', 'HBB1_MOUSE', 0.76027397260273977),
         ('HBB1_TAPTE', 'HBB1_ONCMY', 0.50344827586206897),
         ('HBB1_TAPTE', 'HBB1_PAGBO', 0.46575342465753422),
         ('HBB1_TAPTE', 'HBB1_RAT', 0.76712328767123283),
         ('HBB1_TAPTE', 'HBB1_SPHPU', 0.63698630136986301),
         ('HBB1_TAPTE', 'HBB1_TAPTE', 1.0),
         ('HBB1_TAPTE', 'HBB1_TORMA', 0.34931506849315069),
         ('HBB1_TAPTE', 'HBB1_TRICR', 0.4861111111111111),
         ('HBB1_TAPTE', 'HBB1_UROHA', 0.51369863013698636),
         ('HBB1_TAPTE', 'HBB1_VAREX', 0.62328767123287676),
         ('HBB1_TAPTE', 'HBB1_XENBO', 0.4861111111111111),
         ('HBB1_TAPTE', 'HBB1_XENLA', 0.47222222222222221),
         ('HBB1_TAPTE', 'HBB1_XENTR', 0.45205479452054792),
         ('HBB1_TAPTE', 'MYG_DIDMA', 0.26277372262773724),
         ('HBB1_TAPTE', 'MYG_ERIEU', 0.27007299270072993),
         ('HBB1_TAPTE', 'MYG_ESCGI', 0.30344827586206896),
         ('HBB1_TAPTE', 'MYG_GALCR', 0.27007299270072993),
         ('HBB1_TORMA', 'HBB0_PAGBO', 0.31506849315068491),
         ('HBB1_TORMA', 'HBB1_ANAMI', 0.32413793103448274),
         ('HBB1_TORMA', 'HBB1_CYGMA', 0.33561643835616439),
         ('HBB1_TORMA', 'HBB1_IGUIG', 0.36301369863013699),
         ('HBB1_TORMA', 'HBB1_MOUSE', 0.35616438356164382),
         ('HBB1_TORMA', 'HBB1_ONCMY', 0.33793103448275863),
         ('HBB1_TORMA', 'HBB1_PAGBO', 0.34931506849315069),
         ('HBB1_TORMA', 'HBB1_RAT', 0.35616438356164382),
         ('HBB1_TORMA', 'HBB1_SPHPU', 0.38356164383561642),
         ('HBB1_TORMA', 'HBB1_TAPTE', 0.34931506849315069),
         ('HBB1_TORMA', 'HBB1_TORMA', 1.0),
         ('HBB1_TORMA', 'HBB1_TRICR', 0.31724137931034485),
         ('HBB1_TORMA', 'HBB1_UROHA', 0.29452054794520549),
         ('HBB1_TORMA', 'HBB1_VAREX', 0.35616438356164382),
         ('HBB1_TORMA', 'HBB1_XENBO', 0.34482758620689657),
         ('HBB1_TORMA', 'HBB1_XENLA', 0.33793103448275863),
         ('HBB1_TORMA', 'HBB1_XENTR', 0.33561643835616439),
         ('HBB1_TORMA', 'MYG_ESCGI', 0.25675675675675674),
         ('HBB1_TRICR', 'HBB0_PAGBO', 0.4375),
         ('HBB1_TRICR', 'HBB1_ANAMI', 0.41258741258741261),
         ('HBB1_TRICR', 'HBB1_CYGMA', 0.4375),
         ('HBB1_TRICR', 'HBB1_IGUIG', 0.47916666666666669),
         ('HBB1_TRICR', 'HBB1_MOUSE', 0.52083333333333337),
         ('HBB1_TRICR', 'HBB1_ONCMY', 0.41258741258741261),
         ('HBB1_TRICR', 'HBB1_PAGBO', 0.4375),
         ('HBB1_TRICR', 'HBB1_RAT', 0.52777777777777779),
         ('HBB1_TRICR', 'HBB1_SPHPU', 0.47916666666666669),
         ('HBB1_TRICR', 'HBB1_TAPTE', 0.4861111111111111),
         ('HBB1_TRICR', 'HBB1_TORMA', 0.31724137931034485),
         ('HBB1_TRICR', 'HBB1_TRICR', 1.0),
         ('HBB1_TRICR', 'HBB1_UROHA', 0.3611111111111111),
         ('HBB1_TRICR', 'HBB1_VAREX', 0.4513888888888889),
         ('HBB1_TRICR', 'HBB1_XENBO', 0.4861111111111111),
         ('HBB1_TRICR', 'HBB1_XENLA', 0.49305555555555558),
         ('HBB1_TRICR', 'HBB1_XENTR', 0.49305555555555558),
         ('HBB1_UROHA', 'HBB0_PAGBO', 0.4041095890410959),
         ('HBB1_UROHA', 'HBB1_ANAMI', 0.42857142857142855),
         ('HBB1_UROHA', 'HBB1_CYGMA', 0.36986301369863012),
         ('HBB1_UROHA', 'HBB1_IGUIG', 0.64383561643835618),
         ('HBB1_UROHA', 'HBB1_MOUSE', 0.51666666666666672),
         ('HBB1_UROHA', 'HBB1_ONCMY', 0.50420168067226889),
         ('HBB1_UROHA', 'HBB1_PAGBO', 0.38333333333333336),
         ('HBB1_UROHA', 'HBB1_RAT', 0.54166666666666663),
         ('HBB1_UROHA', 'HBB1_SPHPU', 0.54109589041095896),
         ('HBB1_UROHA', 'HBB1_TAPTE', 0.55833333333333335),
         ('HBB1_UROHA', 'HBB1_TORMA', 0.31034482758620691),
         ('HBB1_UROHA', 'HBB1_TRICR', 0.39316239316239315),
         ('HBB1_UROHA', 'HBB1_UROHA', 1.0),
         ('HBB1_UROHA', 'HBB1_VAREX', 0.59589041095890416),
         ('HBB1_UROHA', 'HBB1_XENBO', 0.42608695652173911),
         ('HBB1_UROHA', 'HBB1_XENLA', 0.41739130434782606),
         ('HBB1_UROHA', 'HBB1_XENTR', 0.40000000000000002),
         ('HBB1_UROHA', 'MYG_ERIEU', 0.27927927927927926),
         ('HBB1_VAREX', 'HBB0_PAGBO', 0.49315068493150682),
         ('HBB1_VAREX', 'HBB1_ANAMI', 0.48275862068965519),
         ('HBB1_VAREX', 'HBB1_CYGMA', 0.4863013698630137),
         ('HBB1_VAREX', 'HBB1_IGUIG', 0.77397260273972601),
         ('HBB1_VAREX', 'HBB1_MOUSE', 0.6095890410958904),
         ('HBB1_VAREX', 'HBB1_ONCMY', 0.48965517241379308),
         ('HBB1_VAREX', 'HBB1_PAGBO', 0.4726027397260274),
         ('HBB1_VAREX', 'HBB1_RAT', 0.62328767123287676),
         ('HBB1_VAREX', 'HBB1_SPHPU', 0.69178082191780821),
         ('HBB1_VAREX', 'HBB1_TAPTE', 0.62328767123287676),
         ('HBB1_VAREX', 'HBB1_TORMA', 0.35616438356164382),
         ('HBB1_VAREX', 'HBB1_TRICR', 0.4513888888888889),
         ('HBB1_VAREX', 'HBB1_UROHA', 0.59589041095890416),
         ('HBB1_VAREX', 'HBB1_VAREX', 1.0),
         ('HBB1_VAREX', 'HBB1_XENBO', 0.51048951048951052),
         ('HBB1_VAREX', 'HBB1_XENLA', 0.5174825174825175),
         ('HBB1_VAREX', 'HBB1_XENTR', 0.4726027397260274),
         ('HBB1_VAREX', 'MYG_DIDMA', 0.25531914893617019),
         ('HBB1_VAREX', 'MYG_ERIEU', 0.25531914893617019),
         ('HBB1_VAREX', 'MYG_ESCGI', 0.24822695035460993),
         ('HBB1_VAREX', 'MYG_GALCR', 0.24822695035460993),
         ('HBB1_XENBO', 'HBB0_PAGBO', 0.43356643356643354),
         ('HBB1_XENBO', 'HBB1_ANAMI', 0.4460431654676259),
         ('HBB1_XENBO', 'HBB1_CYGMA', 0.45985401459854014),
         ('HBB1_XENBO', 'HBB1_IGUIG', 0.4825174825174825),
         ('HBB1_XENBO', 'HBB1_MOUSE', 0.44444444444444442),
         ('HBB1_XENBO', 'HBB1_ONCMY', 0.40140845070422537),
         ('HBB1_XENBO', 'HBB1_PAGBO', 0.43356643356643354),
         ('HBB1_XENBO', 'HBB1_RAT', 0.45833333333333331),
         ('HBB1_XENBO', 'HBB1_SPHPU', 0.48951048951048953),
         ('HBB1_XENBO', 'HBB1_TAPTE', 0.4861111111111111),
         ('HBB1_XENBO', 'HBB1_TORMA', 0.34482758620689657),
         ('HBB1_XENBO', 'HBB1_TRICR', 0.4861111111111111),
         ('HBB1_XENBO', 'HBB1_UROHA', 0.38461538461538464),
         ('HBB1_XENBO', 'HBB1_VAREX', 0.51048951048951052),
         ('HBB1_XENBO', 'HBB1_XENBO', 1.0),
         ('HBB1_XENBO', 'HBB1_XENLA', 0.96551724137931039),
         ('HBB1_XENBO', 'HBB1_XENTR', 0.76388888888888884),
         ('HBB1_XENBO', 'MYG_DIDMA', 0.32075471698113206),
         ('HBB1_XENBO', 'MYG_ELEMA', 0.27358490566037735),
         ('HBB1_XENBO', 'MYG_ERIEU', 0.32075471698113206),
         ('HBB1_XENBO', 'MYG_GALCR', 0.32075471698113206),
         ('HBB1_XENLA', 'HBB0_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_ANAMI', 0.45323741007194246),
         ('HBB1_XENLA', 'HBB1_CYGMA', 0.46715328467153283),
         ('HBB1_XENLA', 'HBB1_IGUIG', 0.48951048951048953),
         ('HBB1_XENLA', 'HBB1_MOUSE', 0.44444444444444442),
         ('HBB1_XENLA', 'HBB1_ONCMY', 0.39436619718309857),
         ('HBB1_XENLA', 'HBB1_PAGBO', 0.44055944055944057),
         ('HBB1_XENLA', 'HBB1_RAT', 0.45833333333333331),
         ('HBB1_XENLA', 'HBB1_SPHPU', 0.4825174825174825),
         ('HBB1_XENLA', 'HBB1_TAPTE', 0.47222222222222221),
         ('HBB1_XENLA', 'HBB1_TORMA', 0.33793103448275863),
         ('HBB1_XENLA', 'HBB1_TRICR', 0.49305555555555558),
         ('HBB1_XENLA', 'HBB1_UROHA', 0.3776223776223776),
         ('HBB1_XENLA', 'HBB1_VAREX', 0.5174825174825175),
         ('HBB1_XENLA', 'HBB1_XENBO', 0.96551724137931039),
         ('HBB1_XENLA', 'HBB1_XENLA', 1.0),
         ('HBB1_XENLA', 'HBB1_XENTR', 0.75),
         ('HBB1_XENLA', 'MYG_DIDMA', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ELEMA', 0.26415094339622641),
         ('HBB1_XENLA', 'MYG_ERIEU', 0.32075471698113206),
         ('HBB1_XENLA', 'MYG_ESCGI', 0.28282828282828282),
         ('HBB1_XENLA', 'MYG_GALCR', 0.32075471698113206),
         ('HBB1_XENTR', 'HBB0_PAGBO', 0.4726027397260274),
         ('HBB1_XENTR', 'HBB1_ANAMI', 0.4689655172413793),
         ('HBB1_XENTR', 'HBB1_CYGMA', 0.47945205479452052),
         ('HBB1_XENTR', 'HBB1_IGUIG', 0.49315068493150682),
         ('HBB1_XENTR', 'HBB1_MOUSE', 0.4589041095890411),
         ('HBB1_XENTR', 'HBB1_ONCMY', 0.39310344827586208),
         ('HBB1_XENTR', 'HBB1_PAGBO', 0.47945205479452052),
         ('HBB1_XENTR', 'HBB1_RAT', 0.45205479452054792),
         ('HBB1_XENTR', 'HBB1_SPHPU', 0.4726027397260274),
         ('HBB1_XENTR', 'HBB1_TAPTE', 0.45205479452054792),
         ('HBB1_XENTR', 'HBB1_TORMA', 0.33561643835616439),
         ('HBB1_XENTR', 'HBB1_TRICR', 0.49305555555555558),
         ('HBB1_XENTR', 'HBB1_UROHA', 0.35616438356164382),
         ('HBB1_XENTR', 'HBB1_VAREX', 0.4726027397260274),
         ('HBB1_XENTR', 'HBB1_XENBO', 0.76388888888888884),
         ('HBB1_XENTR', 'HBB1_XENLA', 0.75),
         ('HBB1_XENTR', 'HBB1_XENTR', 1.0),
         ('HBB1_XENTR', 'MYG_DIDMA', 0.2857142857142857),
         ('HBB1_XENTR', 'MYG_ERIEU', 0.27067669172932329),
         ('HBB1_XENTR', 'MYG_ESCGI', 0.27272727272727271),
         ('HBB1_XENTR', 'MYG_GALCR', 0.2781954887218045),
         ('MYG_DIDMA', 'HBB0_PAGBO', 0.22222222222222221),
         ('MYG_DIDMA', 'HBB1_IGUIG', 0.25179856115107913),
         ('MYG_DIDMA', 'HBB1_MOUSE', 0.29655172413793102),
         ('MYG_DIDMA', 'HBB1_ONCMY', 0.25694444444444442),
         ('MYG_DIDMA', 'HBB1_RAT', 0.29655172413793102),
         ('MYG_DIDMA', 'HBB1_TAPTE', 0.26277372262773724),
         ('MYG_DIDMA', 'HBB1_VAREX', 0.25531914893617019),
         ('MYG_DIDMA', 'HBB1_XENBO', 0.32075471698113206),
         ('MYG_DIDMA', 'HBB1_XENLA', 0.32075471698113206),
         ('MYG_DIDMA', 'HBB1_XENTR', 0.2857142857142857),
         ('MYG_DIDMA', 'MYG_DIDMA', 1.0),
         ('MYG_DIDMA', 'MYG_ELEMA', 0.81045751633986929),
         ('MYG_DIDMA', 'MYG_ERIEU', 0.87581699346405228),
         ('MYG_DIDMA', 'MYG_ESCGI', 0.83552631578947367),
         ('MYG_DIDMA', 'MYG_GALCR', 0.83006535947712423),
         ('MYG_ELEMA', 'HBB0_PAGBO', 0.20833333333333334),
         ('MYG_ELEMA', 'HBB1_MOUSE', 0.27586206896551724),
         ('MYG_ELEMA', 'HBB1_RAT', 0.28275862068965518),
         ('MYG_ELEMA', 'HBB1_XENBO', 0.27358490566037735),
         ('MYG_ELEMA', 'HBB1_XENLA', 0.26415094339622641),
         ('MYG_ELEMA', 'MYG_DIDMA', 0.81045751633986929),
         ('MYG_ELEMA', 'MYG_ELEMA', 1.0),
         ('MYG_ELEMA', 'MYG_ERIEU', 0.82352941176470584),
         ('MYG_ELEMA', 'MYG_ESCGI', 0.83552631578947367),
         ('MYG_ELEMA', 'MYG_GALCR', 0.84313725490196079),
         ('MYG_ERIEU', 'HBB0_PAGBO', 0.21527777777777779),
         ('MYG_ERIEU', 'HBB1_IGUIG', 0.28368794326241137),
         ('MYG_ERIEU', 'HBB1_MOUSE', 0.30344827586206896),
         ('MYG_ERIEU', 'HBB1_ONCMY', 0.2361111111111111),
         ('MYG_ERIEU', 'HBB1_RAT', 0.29655172413793102),
         ('MYG_ERIEU', 'HBB1_TAPTE', 0.27007299270072993),
         ('MYG_ERIEU', 'HBB1_UROHA', 0.27927927927927926),
         ('MYG_ERIEU', 'HBB1_VAREX', 0.25531914893617019),
         ('MYG_ERIEU', 'HBB1_XENBO', 0.32075471698113206),
         ('MYG_ERIEU', 'HBB1_XENLA', 0.32075471698113206),
         ('MYG_ERIEU', 'HBB1_XENTR', 0.27067669172932329),
         ('MYG_ERIEU', 'MYG_DIDMA', 0.87581699346405228),
         ('MYG_ERIEU', 'MYG_ELEMA', 0.82352941176470584),
         ('MYG_ERIEU', 'MYG_ERIEU', 1.0),
         ('MYG_ERIEU', 'MYG_ESCGI', 0.83552631578947367),
         ('MYG_ERIEU', 'MYG_GALCR', 0.85620915032679734),
         ('MYG_ESCGI', 'HBB0_PAGBO', 0.25),
         ('MYG_ESCGI', 'HBB1_CYGMA', 0.2361111111111111),
         ('MYG_ESCGI', 'HBB1_IGUIG', 0.27659574468085107),
         ('MYG_ESCGI', 'HBB1_MOUSE', 0.28965517241379313),
         ('MYG_ESCGI', 'HBB1_ONCMY', 0.25),
         ('MYG_ESCGI', 'HBB1_RAT', 0.28275862068965518),
         ('MYG_ESCGI', 'HBB1_TAPTE', 0.3611111111111111),
         ('MYG_ESCGI', 'HBB1_TORMA', 0.25675675675675674),
         ('MYG_ESCGI', 'HBB1_VAREX', 0.24822695035460993),
         ('MYG_ESCGI', 'HBB1_XENLA', 0.28282828282828282),
         ('MYG_ESCGI', 'HBB1_XENTR', 0.27272727272727271),
         ('MYG_ESCGI', 'MYG_DIDMA', 0.83552631578947367),
         ('MYG_ESCGI', 'MYG_ELEMA', 0.83552631578947367),
         ('MYG_ESCGI', 'MYG_ERIEU', 0.83552631578947367),
         ('MYG_ESCGI', 'MYG_ESCGI', 1.0),
         ('MYG_ESCGI', 'MYG_GALCR', 0.84210526315789469),
         ('MYG_GALCR', 'HBB0_PAGBO', 0.24305555555555555),
         ('MYG_GALCR', 'HBB1_IGUIG', 0.28368794326241137),
         ('MYG_GALCR', 'HBB1_MOUSE', 0.28275862068965518),
         ('MYG_GALCR', 'HBB1_ONCMY', 0.24305555555555555),
         ('MYG_GALCR', 'HBB1_RAT', 0.27586206896551724),
         ('MYG_GALCR', 'HBB1_TAPTE', 0.27007299270072993),
         ('MYG_GALCR', 'HBB1_VAREX', 0.24822695035460993),
         ('MYG_GALCR', 'HBB1_XENBO', 0.32075471698113206),
         ('MYG_GALCR', 'HBB1_XENLA', 0.32075471698113206),
         ('MYG_GALCR', 'HBB1_XENTR', 0.2781954887218045),
         ('MYG_GALCR', 'MYG_DIDMA', 0.83006535947712423),
         ('MYG_GALCR', 'MYG_ELEMA', 0.84313725490196079),
         ('MYG_GALCR', 'MYG_ERIEU', 0.85620915032679734),
         ('MYG_GALCR', 'MYG_ESCGI', 0.84210526315789469),
         ('MYG_GALCR', 'MYG_GALCR', 1.0),
         ('PRCA_ANASP', 'PRCA_ANASP', 1.0),
         ('PRCA_ANASP', 'PRCA_ANAVA', 0.97222222222222221),
         ('PRCA_ANAVA', 'PRCA_ANASP', 0.97222222222222221),
         ('PRCA_ANAVA', 'PRCA_ANAVA', 1.0)]

###

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
