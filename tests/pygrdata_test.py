
from nosebase import *

class PygrSwissprotBase(object):
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
        pygr.Data.Bio.Seq.Swissprot.sp42 = sp
        ival= hbb[10:35]
        ival.__doc__ = 'fragment'
        pygr.Data.Bio.Seq.frag = ival
        m = pygr.Data.Mapping(sourceDB=sp,targetDB=sp)
        trypsin =  sp['PRCA_ANAVA']
        m[hbb] = trypsin
        m.__doc__ = 'map sp to itself'
        pygr.Data.Bio.Seq.spmap = m
        pygr.Data.schema.Bio.Seq.spmap = pygr.Data.OneToManyRelation(sp,sp,bindAttrs=('buddy',))
        self.tempdir.force_reload()
    def teardown(self):
        self.tempdir.__del__() # FORCE IT TO RELEASE PYGR DATA

def check_match(self):
    import pygr.Data
    frag = pygr.Data.Bio.Seq.frag()
    correct = pygr.Data.Bio.Seq.Swissprot.sp42()['HBB1_TORMA'][10:35]
    assert frag == correct, 'seq ival should match'
    assert frag.__doc__ == 'fragment', 'docstring should match'
    assert str(frag) == 'IQHIWSNVNVVEITAKALERVFYVY', 'letters should match'
    assert len(frag) == 25, 'length should match'
    assert len(frag.path) == 142, 'length should match'
    store = PygrDataTextFile('results/seqdb1.pickle')
    saved = store['hbb1 fragment']
    assert frag == saved, 'seq ival should matched stored result'
def check_dir(self):
    import pygr.Data
    l = pygr.Data.dir('Bio')
    print 'dir:',l
    assert l == ['Bio.Seq.Swissprot.sp42','Bio.Seq.frag','Bio.Seq.spmap']
def check_bind(self):
    import pygr.Data
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin =  sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin,'automatic schema attribute binding'


class Seq_Test(PygrSwissprotBase):
    def match_test(self):
        check_match(self)
    def dir_test(self):
        check_dir(self)
    def bind_test(self):
        check_bind(self)
    def schema_test(self):
        from pygr import seqdb
        sp2 = seqdb.BlastDB(self.filename)
        sp2.__doc__ = 'another sp'
        import pygr.Data
        pygr.Data.Bio.Seq.sp2 = sp2
        sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        m = pygr.Data.Mapping(sourceDB=sp,targetDB=sp2)
        m.__doc__ = 'sp -> sp2'
        pygr.Data.Bio.Seq.testmap = m
        pygr.Data.schema.Bio.Seq.testmap = pygr.Data.OneToManyRelation(sp,sp2)
        pygrData = self.tempdir.force_reload()
        sp3 = seqdb.BlastDB(self.filename)
        sp3.__doc__ = 'sp number 3'
        pygrData.Bio.Seq.sp3 = sp3
        sp2 = pygrData.Bio.Seq.sp2()
        m = pygrData.Mapping(sourceDB=sp3,targetDB=sp2)
        m.__doc__ = 'sp3 -> sp2'
        pygrData.Bio.Seq.testmap2 = m
        pygrData.schema.Bio.Seq.testmap2 = pygr.Data.OneToManyRelation(sp3,sp2)
        l = pygrData.getResource.d.keys()
        l.sort()
        assert l == ['Bio.Seq.sp2','Bio.Seq.sp3','Bio.Seq.testmap2']
        pygrData.getResource.newServer('testy',withIndex=True,host='localhost')
        pygrData = self.tempdir.force_reload()
        g = pygrData.getResource.db[0].graph
        l = g.keys()
        l.sort()
        assert l == ['Bio.Seq.Swissprot.sp42','Bio.Seq.sp2','Bio.Seq.sp3']
        
        

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

class XMLRPC_Test(PygrSwissprotBase):
    'create an XMLRPC server and access seqdb from it'
    def setup(self):
        PygrSwissprotBase.setup(self)
        self.server = TestXMLRPCServer('Bio.Seq.Swissprot.sp42',
                                       'Bio.Seq.frag','Bio.Seq.spmap',
                                       PYGRDATAPATH=str(self.tempdir))
    def xmlrpc_test(self):
        pygrData = self.server.access_server()
        check_match(self)
        check_dir(self)
        check_bind(self)
        from pygr import seqdb
        sp2 = seqdb.BlastDB(self.filename)
        sp2.__doc__ = 'another sp'
        try:
            pygrData.Bio.Seq.sp2 = sp2
            raise KeyError('failed to catch bad attempt to write to XMLRPC server')
        except ValueError:
            pass
    def teardown(self):
        'halt the test XMLRPC server'
        self.server.close()
        PygrSwissprotBase.teardown(self)

