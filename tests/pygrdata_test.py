
from nosebase import *
import nose
import socket

class PygrDownload_Test(object):
    'save seq db and interval to pygr.Data shelve'
    tempDirClass = TempPygrData
    def setup(self,**kwargs):
        self.tempdir = self.tempDirClass(**kwargs)
        from pygr.downloader import SourceURL
        try:
            s = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
        except socket.gaierror:
            raise nose.SkipTest
        s.__doc__ = 'test download'
        import pygr.Data
        pygr.Data.Bio.Test.Download1 = s
        pygr.Data.save()
        self.tempdir.force_reload()
    def download_test(self):
        'test downloading of gzipped file using pygr.Data'
        import pygr.Data
        filepath = pygr.Data.Bio.Test.Download1()
        pygr.Data.save()
        ifile = file(filepath)
        import md5,os
        h = md5.md5(ifile.read())
        ifile.close()
        assert h.hexdigest() == 'f95656496c5182d6cff9a56153c9db73'
        os.remove(filepath)
    def teardown(self):
        self.tempdir.__del__() # FORCE IT TO RELEASE PYGR DATA

class GenericBuild_Test(object):
    def generic_build_test(self):
        'test that GenericBuilder construction of the BlastDB works right'
        from pygr.downloader import GenericBuilder
        import pickle
        gb = GenericBuilder('BlastDB','sp_hbb1')
        s = pickle.dumps(gb)
        db = pickle.loads(s) # force construction of the BlastDB
        assert len(db)==24
        l = [x for x in db]
        l.sort()
        correct = ['HBB0_PAGBO', 'HBB1_ANAMI', 'HBB1_CYGMA', 'HBB1_IGUIG',
                   'HBB1_MOUSE', 'HBB1_ONCMY', 'HBB1_PAGBO', 'HBB1_RAT',
                   'HBB1_SPHPU', 'HBB1_TAPTE', 'HBB1_TORMA', 'HBB1_TRICR',
                   'HBB1_UROHA', 'HBB1_VAREX', 'HBB1_XENBO', 'HBB1_XENLA',
                   'HBB1_XENTR', 'MYG_DIDMA', 'MYG_ELEMA', 'MYG_ERIEU',
                   'MYG_ESCGI', 'MYG_GALCR', 'PRCA_ANASP', 'PRCA_ANAVA']
        correct.sort()
        assert l ==  correct

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
        # CREATE AN ANNOTATION DATABASE AND BIND AS exons ATTRIBUTE
        annoDB = seqdb.AnnotationDB({1:('HBB1_TORMA',10,50)},sp,
                                    sliceAttrDict=dict(id=0,start=1,stop=2))
        exon = annoDB[1]
        from pygr import cnestedlist
        filename = tmp.subfile('exonAnnot')
        nlmsa = cnestedlist.NLMSA(filename,'w',pairwiseMode=True,bidirectional=False)
        nlmsa.addAnnotation(exon)
        nlmsa.build(verbose=False)
        annoDB.__doc__ = 'a little annotation db'
        nlmsa.__doc__ = 'a little map'
        pygr.Data.Bio.Annotation.annoDB = annoDB
        pygr.Data.Bio.Annotation.map = nlmsa
        pygr.Data.schema.Bio.Annotation.map = \
             pygr.Data.ManyToManyRelation(sp,annoDB,bindAttrs=('exons',))
        pygr.Data.save()
        self.tempdir.force_reload()
    def teardown(self):
        self.tempdir.__del__() # FORCE IT TO RELEASE PYGR DATA

class DNAAnnotation_Test(object):
    tempDirClass = TempPygrData
    def setup(self,**kwargs):
        tmp = self.tempDirClass(**kwargs)
        self.tempdir = tmp
        filename = tmp.copyFile('dnaseq')
        from pygr import seqdb
        db = seqdb.BlastDB(filename)
        db.__doc__ = 'little dna'
        import pygr.Data
        pygr.Data.Bio.Test.dna = db
        annoDB = seqdb.AnnotationDB({1:('seq1',5,10,'fred'),2:('seq1',-60,-50,'bob'),
                                     3:('seq2',-20,-10,'mary')},
                                    db,sliceAttrDict=dict(id=0,start=1,stop=2,name=3))
        annoDB.__doc__ = 'trivial annotation'
        pygr.Data.Bio.Test.annoDB = annoDB
        from pygr import cnestedlist
        nlmsa = cnestedlist.NLMSA('tryannot','w',pairwiseMode=True,bidirectional=False)
        for annID in annoDB:
            nlmsa.addAnnotation(annoDB[annID])
        nlmsa.build(verbose=False)
        nlmsa.__doc__ = 'trivial map'
        pygr.Data.Bio.Test.map = nlmsa
        pygr.Data.schema.Bio.Test.map = pygr.Data.ManyToManyRelation(db,annoDB,bindAttrs=('exons',))
        pygr.Data.save()
        self.tempdir.force_reload()
    def annotation_test(self):
        import pygr.Data
        db = pygr.Data.Bio.Test.dna()
        s1 = db['seq1']
        l = s1.exons.keys()
        annoDB = pygr.Data.Bio.Test.annoDB()
        assert l == [annoDB[1],-(annoDB[2])]
        assert l[0].sequence == s1[5:10]
        assert l[1].sequence == s1[50:60]
        assert l[0].name == 'fred','test annotation attribute access'
        assert l[1].name == 'bob'
        sneg = -(s1[:55])
        l = sneg.exons.keys()
        assert l == [annoDB[2][5:],-(annoDB[1])]
        assert l[0].sequence == -(s1[50:55])
        assert l[1].sequence == -(s1[5:10])
        assert l[0].name == 'bob'
        assert l[1].name == 'fred'
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
def check_dir(self,correct=['Bio.Annotation.annoDB','Bio.Annotation.map',
                            'Bio.Seq.Swissprot.sp42','Bio.Seq.frag','Bio.Seq.spmap']):
    import pygr.Data
    l = pygr.Data.dir('Bio')
    print 'dir:',l
    correct.sort()
    assert l == correct
def check_bind(self):
    import pygr.Data
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin =  sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin,'automatic schema attribute binding'

def check_bind2(self):
    import pygr.Data
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    exons = hbb.exons.keys()
    assert len(exons)==1, 'number of expected annotations'
    annoDB = pygr.Data.Bio.Annotation.annoDB()
    exon = annoDB[1]
    assert exons[0]==exon, 'test annotation comparison'
    assert exons[0].pathForward is exon,'annotation parent match'
    assert exons[0].sequence == hbb[10:50],'annotation to sequence match'
    onc = sp['HBB1_ONCMY']
    try:
        exons = onc.exons.keys()
        raise ValueError('failed to catch query with no annotations')
    except KeyError:
        pass
    

class Seq_Test(PygrSwissprotBase):
    def match_test(self):
        check_match(self)
    def dir_test(self):
        check_dir(self)
    def bind_test(self):
        check_bind(self)
        check_bind2(self)
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
        pygr.Data.save()
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
        pygrData.save()
        #pygrData.getResource.newServer('testy',withIndex=True,host='localhost')
        pygrData = self.tempdir.force_reload()
        g = pygrData.getResource.db[0].graph
        l = g.keys()
        l.sort()
        print 'nodes are',l
        assert l == ['Bio.Annotation.annoDB',
                     'Bio.Seq.Swissprot.sp42','Bio.Seq.sp2','Bio.Seq.sp3']
        
        

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
    def bind_test(self):
        check_bind(self)
        check_bind2(self)

class XMLRPC_Test(PygrSwissprotBase):
    'create an XMLRPC server and access seqdb from it'
    def setup(self):
        PygrSwissprotBase.setup(self)
        self.server = TestXMLRPCServer('Bio.Seq.Swissprot.sp42',
                                       'Bio.Seq.frag','Bio.Seq.spmap',
                                       'Bio.Annotation.annoDB',
                                       'Bio.Annotation.map',
                                       PYGRDATAPATH=str(self.tempdir))
    def xmlrpc_test(self):
        pygrData = self.server.access_server()
        check_match(self)
        check_dir(self,correct=['Bio.Seq.Swissprot.sp42','Bio.Seq.frag',
                                'Bio.Seq.spmap','Bio.Annotation.annoDB',
                                'Bio.Annotation.map'])
        check_bind(self)
        check_bind2(self)
        from pygr import seqdb
        sp2 = seqdb.BlastDB(self.filename)
        sp2.__doc__ = 'another sp'
        try:
            pygrData.Bio.Seq.sp2 = sp2
            pygrData.save()
            raise KeyError('failed to catch bad attempt to write to XMLRPC server')
        except ValueError:
            pass
    def teardown(self):
        'halt the test XMLRPC server'
        self.server.close()
        PygrSwissprotBase.teardown(self)

