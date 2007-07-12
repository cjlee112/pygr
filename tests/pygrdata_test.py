
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
        assert str(frag) == 'IQHIWSNVNVVEITAKALERVFYVY', 'letters should match'
        store = PygrDataTextFile('results/seqdb1.pickle')
        saved = store['hbb1 fragment']
        assert frag == saved, 'seq ival should matched stored result'
    def dir_test(self):
        pygrData = self.tempdir.force_reload()
        l = pygrData.dir('Bio')
        print 'dir:',l
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

class XMLRPC_Test(object):
    'create an XMLRPC server and access seqdb from it'
    @skip_errors(KeyError)
    def setup(self):
        self.server = TestXMLRPCServer('Bio.Seq.Swissprot.sp42')
    def match_test(self):
        pygrData = self.server.access_server()
        l = pygrData.dir('Bio')
        print 'remote dir:',l
        assert l == ['Bio.Seq.Swissprot.sp42'], 'get resource list by XMLRPC'
        sp = pygrData.Bio.Seq.Swissprot.sp42()
        hbb = sp['HBB1_TORMA']
        assert len(hbb) == 142, 'get length by XMLRPC'
        ival = hbb[10:35]
        assert str(ival) == 'IQHIWSNVNVVEITAKALERVFYVY', 'get seq by XMLRPC'
    def teardown(self):
        'halt the test XMLRPC server'
        self.server.close()

