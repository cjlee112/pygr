import pygrtest_common
from pygr import cnestedlist, nlmsa_utils

class NestedList_Test(object):
    'basic cnestedlist class tests'
    def setup(self):
        self.db = cnestedlist.IntervalDB()
        ivals = [(0,10,1,-110,-100),(-20,-5,2,300,315)]
        self.db.save_tuples(ivals)

    def query_test(self):
        assert self.db.find_overlap_list(0,10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]
    def reverse_test(self):
        assert self.db.find_overlap_list(-11,-7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]
    def filedb_test(self):
        from nosebase import TempDir
        tmp = TempDir()
        filename = tmp.subfile('nlmsa')
        self.db.write_binaries(filename)
        fdb=cnestedlist.IntervalFileDB(filename)
        assert fdb.find_overlap_list(0,10) == \
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)]
        assert fdb.find_overlap_list(-11,-7) == \
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)]
        tmp.__del__() # FORCE IT TO DELETE TEMPORARY DIRECTORY

class NLMSA_Test(object):
    def setup(self):
        pass
    def empty_test(self):
        msa = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True)
        try:
            msa.build()
            raise AssertionError('failed to trap empty alignment!')
        except nlmsa_utils.EmptyAlignmentError:
            pass
    def empty2_test(self):
        msa = cnestedlist.NLMSA('blasthits', 'w', pairwiseMode=True)
        try:
            msa.build()
            raise AssertionError('failed to trap empty alignment!')
        except nlmsa_utils.EmptyAlignmentError:
            pass
