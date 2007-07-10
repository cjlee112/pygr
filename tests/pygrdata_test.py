
from nosebase import *

class Seq_Test(object):
    'save seq db and interval to pygr.Data shelve'
    tempDirClass = TempPygrData
    def setup(self,**kwargs):
        tmp = self.tempDirClass(**kwargs)
        self.tempdir = tmp
        self.filename = tmp.copyFile('sp_hbb1')
        from pygr import seqdb
        sp = seqdb.BlastDB(self.filename)
        sp.__doc__ = 'little swissprot'
        hbb = sp['HBB1_TORMA']
        import pygr.Data
        pygr.Data.Bio.Seq.sp = sp
        ival= hbb[10:35]
        ival.__doc__ = 'fragment'
        pygr.Data.Bio.Seq.frag = ival
    def match_test(self):
        pygrData = self.tempdir.force_reload()
        frag = pygrData.Bio.Seq.frag()
        correct = pygrData.Bio.Seq.sp()['HBB1_TORMA'][10:35]
        assert frag == correct, 'seq ival should match'
        assert frag.__doc__ == 'fragment', 'docstring should match'
    def dir_test(self):
        pygrData = self.tempdir.force_reload()
        l = pygrData.dir('Bio')
        assert l == ['Bio.Seq.frag','Bio.Seq.sp']
        

class Seq_SQL_Test(Seq_Test):
    'save same data to MySQL server'
    tempDirClass = TempPygrDataMySQL
    mysqlArgs = {}
    @skip_errors(ImportError)
    def setup(self):
        import MySQLdb
        try:
            Seq_Test.setup(self,**self.mysqlArgs)
        except MySQLdb.MySQLError:
            raise ImportError

class Seq_SQL2_Test(Seq_SQL_Test):
    'test arg passing mechanism to save to a specific database'
    mysqlArgs = dict(args=' lldb.mbi.ucla.edu')
