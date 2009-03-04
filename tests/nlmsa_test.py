import unittest
from testlib import testutil
from pygr import cnestedlist, nlmsa_utils

class NestedList_Test(unittest.TestCase):
    "Basic cnestedlist class tests"

    def setUp(self):
        self.db = cnestedlist.IntervalDB()
        ivals = [(0,10,1,-110,-100), (-20,-5,2,300,315)]
        self.db.save_tuples(ivals)

    def test_query(self):
        "NestedList query"
        assert self.db.find_overlap_list(0,10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]

    def test_reverse(self):
        "NestedList reverse"
        assert self.db.find_overlap_list(-11,-7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]

    def test_filedb(self):
        "NestedList filedb"
        tempdir  = testutil.TempDir('nlmsa-test')
        filename = tempdir.subfile('nlmsa')
        self.db.write_binaries(filename)
        fdb=cnestedlist.IntervalFileDB(filename)
        assert fdb.find_overlap_list(0,10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]
        assert fdb.find_overlap_list(-11,-7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]
        
        # fails on windows
        #tempdir.remove()  @CTB

class NLMSA_Test(unittest.TestCase):

    def setUp(self):
        pass

    def test_empty(self):
        "NLMSA Empty"
        blasthits  = testutil.tempdatafile('blasthits')

        msa = cnestedlist.NLMSA(blasthits , 'memory', pairwiseMode=True)
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
        msa = cnestedlist.NLMSA(testnlmsa ,mode='w', pairwiseMode=True,
                                bidirectional=False)

def get_suite():
    "Returns the testsuite"
    tests  = [ NestedList_Test, NLMSA_Test ]
    return testutil.make_suite(tests)

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)
