import unittest
from testlib import testutil, PygrTestProgram
from pygr import cnestedlist, nlmsa_utils, seqdb, sequence


class NestedList_Test(unittest.TestCase):
    "Basic cnestedlist class tests"

    def setUp(self):
        self.db = cnestedlist.IntervalDB()
        ivals = [(0, 10, 1, -110, -100), (-20, -5, 2, 300, 315)]
        self.db.save_tuples(ivals)

    def test_query(self):
        "NestedList query"
        assert self.db.find_overlap_list(0, 10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]

    def test_reverse(self):
        "NestedList reverse"
        assert self.db.find_overlap_list(-11, -7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]

    def test_filedb(self):
        "NestedList filedb"
        tempdir = testutil.TempDir('nlmsa-test')
        filename = tempdir.subfile('nlmsa')
        self.db.write_binaries(filename)
        fdb = cnestedlist.IntervalFileDB(filename)
        assert fdb.find_overlap_list(0, 10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]
        assert fdb.find_overlap_list(-11, -7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]

        # fails on windows
        #tempdir.remove()  @CTB


class NLMSA_SimpleTests(unittest.TestCase):

    def setUp(self):
        pass

    def test_empty(self):
        "NLMSA Empty"
        blasthits = testutil.tempdatafile('blasthits')

        msa = cnestedlist.NLMSA(blasthits, 'memory', pairwiseMode=True)
        try:
            msa.build()
            raise AssertionError('failed to trap empty alignment!')
        except nlmsa_utils.EmptyAlignmentError:
            pass

    def test_empty2(self):
        "NLMSA Empty 2"
        blasthits = testutil.tempdatafile('blasthits2')
        msa = cnestedlist.NLMSA(blasthits, mode='w', pairwiseMode=True)
        try:
            msa.build()
            raise AssertionError('failed to trap empty alignment!')
        except nlmsa_utils.EmptyAlignmentError:
            pass

    def test_build(self):
        "NLMSA build"

        testnlmsa = testutil.tempdatafile('testnlmsa')
        msa = cnestedlist.NLMSA(testnlmsa, mode='w', pairwiseMode=True,
                                bidirectional=False)
        # @CTB should there be something else here?  What is this testing?

    def test_lpo_query(self):
        s1=sequence.Sequence('aaaa', 's1')
        s2=sequence.Sequence('bbbb', 's2')
        msa = cnestedlist.NLMSA(mode='memory')
        msa[0:4] += s1
        msa[0:4] += s2
        msa.build()
        msaSlice = msa[0:4]
        assert len(msaSlice) == 2
        l = [t[0:2] for t in msaSlice.edges()]
        l.sort()
        correct = [(slice(0, 4), s1), (slice(0, 4), s2)]
        correct.sort()
        assert l == correct


class NLMSA_Test(unittest.TestCase):

    def setUp(self):
        s = sequence.Sequence('ATGGACAGAGATGACAGATGAC', 'a')
        s2 = sequence.Sequence('ATGGGAGCAGCATGACAGATGAC', 'b')

        # make a non-empty NLMSA
        nlmsa = cnestedlist.NLMSA('foo', mode='memory', pairwiseMode=True)
        nlmsa += s
        nlmsa[s] += s2
        nlmsa.build()

        self.s = s
        self.s2 = s2
        self.nlmsa = nlmsa

    def test_iter(self):
        "Iteration of NLMSA objects should return reasonable error."

        # try iterating over it
        try:
            for x in self.nlmsa:
                break                   # should fail before this

            assert 0, "should not be able to iterate over NLMSA"
        except NotImplementedError:
            pass

    def test_slice_repr(self):
        "Ask for an informative __repr__ on NLMSASlice objects"

        slice = self.nlmsa[self.s]
        r = repr(slice)
        assert 'seq=a' in r

        slice = self.nlmsa[self.s2]
        r = repr(slice)
        assert 'seq=b' in r


class NLMSA_BuildWithAlignedIntervals_Test(unittest.TestCase):

    def setUp(self):
        seqdb_name = testutil.datafile('alignments.fa')
        self.db = seqdb.SequenceFileDB(seqdb_name)

    def _check_results(self, n):
        db = self.db

        a, b, c = db['a'], db['b'], db['c']

        ival = a[0:8]
        (result, ) = n[ival].keys()
        assert result == b[0:8]

        ival = a[12:20]
        (result, ) = n[ival].keys()
        assert result == c[0:8]

        l = list(n[a].keys())
        l.sort()
        assert b[0:8] in l
        assert c[0:8] in l

    def test_simple(self):
        # first set of intervals
        ivals = [(('a', 0, 8, 1), ('b', 0, 8, 1), ),
                 (('a', 12, 20, 1), ('c', 0, 8, 1)), ]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        alignedIvalsAttrs = dict(id=0, start=1, stop=2, idDest=0, startDest=1,
                                 stopDest=2, ori=3, oriDest=3)
        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db,
                                            alignedIvalsAttrs)
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_simple_no_ori(self):
        # first set of intervals
        ivals = [(('a', 0, 8, ), ('b', 0, 8, ), ),
                 (('a', 12, 20, ), ('c', 0, 8, )), ]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        alignedIvalsAttrs = dict(id=0, start=1, stop=2, idDest=0, startDest=1,
                                 stopDest=2)
        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db,
                                            alignedIvalsAttrs)
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_attr(self):

        class Bag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first set of intervals
        db = self.db
        a, b, c = db['a'], db['b'], db['c']

        src_ival1 = Bag(id='a', start=0, stop=8, ori=1)
        dst_ival1 = Bag(id='b', start=0, stop=8, ori=1)

        src_ival2 = Bag(id='a', start=12, stop=20, ori=1)
        dst_ival2 = Bag(id='c', start=0, stop=8, ori=1)

        ivals = [(src_ival1, dst_ival1), (src_ival2, dst_ival2)]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db)
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_single_ival_attr(self):

        class Bag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first set of intervals
        db = self.db
        a, b, c = db['a'], db['b'], db['c']

        ival1 = Bag(id='a', start=0, stop=8, ori=1,
                    idDest='b', startDest=0, stopDest=8, stopOri=1)
        ival2 = Bag(id='a', start=12, stop=20, ori=1,
                    idDest='c', startDest=0, stopDest=8, oriDest=1)

        ivals = [ival1, ival2]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True)

        cti = nlmsa_utils.CoordsToIntervals(self.db, self.db, {})
        n.add_aligned_intervals(cti(ivals))
        n.build()

        self._check_results(n)

    def test_no_seqDict_args(self):

        class Bag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first set of intervals
        db = self.db

        src_ival1 = Bag(id='a', start=0, stop=8, ori=1)
        dst_ival1 = Bag(id='b', start=0, stop=8, ori=1)

        src_ival2 = Bag(id='a', start=12, stop=20, ori=1)
        dst_ival2 = Bag(id='c', start=0, stop=8, ori=1)

        ivals = [(src_ival1, dst_ival1), (src_ival2, dst_ival2)]

        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              seqDict=db)

        cti = nlmsa_utils.CoordsToIntervals(self.db)
        n.add_aligned_intervals(cti(ivals))
        n.build()

class NLMSASeqDict_Test(unittest.TestCase):

    def setUp(self):
        seqdb_name = testutil.datafile('alignments.fa')
        self.db = seqdb.SequenceFileDB(seqdb_name)

    def _add_seqs(self, n):
        # CTB: note, force hard references for weakref checking behavior
        self.a = a = self.db['a']
        self.b = b = self.db['b']
        self.c = c = self.db['c']

        pairs = ((a[0:8], b[0:8]),
                 (a[12:20], c[0:8]))
        
        n += a
        for src, dest in pairs:
            n[src] += dest

    def test_cache_size0(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=0)
        self._add_seqs(n)

        # should be zero elements: cachesize of 0
        assert len(n.seqs._cache) == 0
        
    def test_cache_size1(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=1)
        self._add_seqs(n)

        # should be 1 elements: cachesize of 1
        assert len(n.seqs._cache) == 1

    def test_cache_size1(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=1)
        self._add_seqs(n)

        # should be 1 element: cachesize of 1
        assert len(n.seqs._cache) == 1

    def test_cache_size2(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=2)
        self._add_seqs(n)

        # should be 2 elements: cachesize of 2
        assert len(n.seqs._cache) == 2

    def test_cache_size4(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=4)
        self._add_seqs(n)

        # should be 3 elements: cachesize of 4, but only three sequences
        assert len(n.seqs._cache) == 3, len(n.seqs._cache)
        
    def test_clear_cache(self):
        n = cnestedlist.NLMSA('test', mode='memory', pairwiseMode=True,
                              maxSequenceCacheSize=4)
        self._add_seqs(n)

        # should be 3 elements: cachesize of 4, but only three sequences
        assert len(n.seqs._cache) == 3, len(n.seqs._cache)

        # now clear the cache
        n.seqs.clear_cache()
        assert len(n.seqs._cache) == 0, len(n.seqs._cache)

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
