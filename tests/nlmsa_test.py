
import unittest
from pygr import cnestedlist

class NestedListSuite(unittest.TestCase):
    'basic cnestedlist class tests'
    def setUp(self):
        self.db=cnestedlist.IntervalDB()
        ivals=[(0,10,1,-110,-100),(-20,-5,2,300,315)]
        self.db.save_tuples(ivals)

    def testQuery(self):
        self.assertEqual(self.db.find_overlap_list(0,10),
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)])
    def testReverseQuery(self):
        self.assertEqual(self.db.find_overlap_list(-11,-7),
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)])
    def testFileDB(self):
        from nosebase import TempDir
        tmp = TempDir()
        filename = tmp.subfile('nlmsa')
        self.db.write_binaries(filename)
        fdb=cnestedlist.IntervalFileDB(filename)
        self.assertEqual(fdb.find_overlap_list(0,10),
                         [(0, 10, 1, -110, -100), (5, 20, 2, -315, -300)])
        self.assertEqual(fdb.find_overlap_list(-11,-7),
                         [(-10, 0, 1, 100, 110), (-20, -5, 2, 300, 315)])
