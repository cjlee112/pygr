from testlib import testutil
import socket, unittest, os, md5, pickle, datetime
import pygr.Data
from pygr import seqdb, cnestedlist
from pygr.downloader import SourceURL, GenericBuilder

# create a temporary directory that can be kept in common for all tests
# in this test run; it needs to be referred to across tests.
#
# @CTB each test should be self-contained!

_tempdir = None
def init_tempdir():
    global _tempdir
    if _tempdir is None:
        _tempdir = testutil.TempDir('pygrdata')

    return _tempdir

class TestBase(unittest.TestCase):
    "A base class to all pygr.Data test classes"

    def setUp(self):
        # overwrite the PYGRDATAPATH environment variable
        self.tempdir = init_tempdir()
        testutil.change_pygrdatapath(self.tempdir.path)
        # handy shortcuts
        self.EQ = self.assertEqual

class Download_Test(TestBase):
    "Save seq db and interval to pygr.Data shelve"

    # tested elsewhere as well, on Linux makes gzip ask for permissions
    # to overwrite
    def Xtest_download(self): 
        "Downloading of gzipped file using pygr.Data"
        
        url = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
        url.__doc__ = 'test download'

        pygr.Data.addResource('Bio.Test.Download1', url)
        pygr.Data.save()

        f = pygr.Data.Bio.Test.Download1(download=True)

        # performs the download            
        reload(pygr.Data)

        fpath = pygr.Data.Bio.Test.Download1()
        data  = file(fpath, 'rb').read()
        
        h = md5.md5(data)
        self.assertEqual(h.hexdigest(), 'f95656496c5182d6cff9a56153c9db73')
        os.remove(fpath)

class GenericBuild_Test(TestBase):

    def test_generic_build(self):
        "GenericBuilder construction of the BlastDB"

        sp_hbb1 = testutil.datafile('sp_hbb1')
        gb = GenericBuilder('BlastDB', sp_hbb1)
        s = pickle.dumps(gb)
        db = pickle.loads(s) # force construction of the BlastDB
        self.EQ(len(db), 24)
        
        found = [x for x in db]
        found.sort()

        expected = ['HBB0_PAGBO', 'HBB1_ANAMI', 'HBB1_CYGMA', 'HBB1_IGUIG',
                   'HBB1_MOUSE', 'HBB1_ONCMY', 'HBB1_PAGBO', 'HBB1_RAT',
                   'HBB1_SPHPU', 'HBB1_TAPTE', 'HBB1_TORMA', 'HBB1_TRICR',
                   'HBB1_UROHA', 'HBB1_VAREX', 'HBB1_XENBO', 'HBB1_XENLA',
                   'HBB1_XENTR', 'MYG_DIDMA', 'MYG_ELEMA', 'MYG_ERIEU',
                   'MYG_ESCGI', 'MYG_GALCR', 'PRCA_ANASP', 'PRCA_ANAVA']
        expected.sort()

        self.EQ(expected, found)

class DNAAnnotation_Test(TestBase):
    
    def setUp(self,**kwargs):
        dnaseq = testutil.datafile('dnaseq.fasta')
        tryannot = testutil.tempdatafile('tryannot')

        db = seqdb.BlastDB(dnaseq)
        db.__doc__ = 'little dna'

        pygr.Data.Bio.Test.dna = db
        annoDB = seqdb.AnnotationDB({1:('seq1',5,10,'fred'),
                                     2:('seq1',-60,-50,'bob'),
                                     3:('seq2',-20,-10,'mary')},
                                    db,
                              sliceAttrDict=dict(id=0, start=1, stop=2,
                                                 name=3))
        annoDB.__doc__ = 'trivial annotation'
        pygr.Data.Bio.Test.annoDB = annoDB
        nlmsa = cnestedlist.NLMSA(tryannot,'w',pairwiseMode=True,
                                  bidirectional=False)
        for annID in annoDB:
            nlmsa.addAnnotation(annoDB[annID])
            
        nlmsa.build(verbose=False)
        nlmsa.__doc__ = 'trivial map'
        pygr.Data.Bio.Test.map = nlmsa
        pygr.Data.schema.Bio.Test.map = pygr.Data.ManyToManyRelation(db,
                                               annoDB,bindAttrs=('exons',))
        pygr.Data.save()
        reload(pygr.Data)
    
    def test_annotation(self):
        "Annotation test"
        db = pygr.Data.Bio.Test.dna()
        s1 = db['seq1']
        l = s1.exons.keys()
        annoDB = pygr.Data.Bio.Test.annoDB()
        assert l == [annoDB[1], -(annoDB[2])]
        assert l[0].sequence == s1[5:10]
        assert l[1].sequence == s1[50:60]
        assert l[0].name == 'fred','test annotation attribute access'
        assert l[1].name == 'bob'
        sneg = -(s1[:55])
        l = sneg.exons.keys()
        assert l == [annoDB[2][5:], -(annoDB[1])]
        assert l[0].sequence == -(s1[50:55])
        assert l[1].sequence == -(s1[5:10])
        assert l[0].name == 'bob'
        assert l[1].name == 'fred'

def populate_swissprot(pygrData):
    "Populate the current pygrData with swissprot data"

    # check for existance and don't populate twice
    # the files are still open and cannot be removed on windows @CTB
    try:
        sp = pygrData.Bio.Seq.Swissprot.sp42()
        return
    except Exception, exc:
        # populate the data
        pass

    # build BlastDB out of the sequences
    sp_hbb1 = testutil.datafile('sp_hbb1')
    sp = seqdb.BlastDB(sp_hbb1)
    sp.__doc__ = 'little swissprot'
    pygrData.Bio.Seq.Swissprot.sp42 = sp

    # also store a fragment
    hbb = sp['HBB1_TORMA']
    ival= hbb[10:35]
    ival.__doc__ = 'fragment'
    pygrData.Bio.Seq.frag = ival

    # build a mapping to itself
    m = pygrData.Mapping(sourceDB=sp,targetDB=sp)
    trypsin = sp['PRCA_ANAVA']
    m[hbb] = trypsin
    m.__doc__ = 'map sp to itself'
    pygrData.Bio.Seq.spmap = m

    # create an annotation database and bind as exons attribute
    pygrData.schema.Bio.Seq.spmap = pygr.Data.OneToManyRelation(sp, sp,
                                                         bindAttrs=('buddy',))
    annoDB = seqdb.AnnotationDB({1:('HBB1_TORMA',10,50)}, sp,
                                sliceAttrDict=dict(id=0, start=1, stop=2)) 
    exon = annoDB[1]
    
    # generate the names where these will be stored
    tempdir = testutil.TempDir('exonAnnot')
    filename = tempdir.subfile('cnested')
    nlmsa = cnestedlist.NLMSA(filename, 'w', pairwiseMode=True,
                              bidirectional=False)
    nlmsa.addAnnotation(exon)
    nlmsa.build(verbose=False)
    annoDB.__doc__ = 'a little annotation db'
    nlmsa.__doc__ = 'a little map'
    pygrData.Bio.Annotation.annoDB = annoDB
    pygrData.Bio.Annotation.map = nlmsa
    pygrData.schema.Bio.Annotation.map = \
         pygrData.ManyToManyRelation(sp, annoDB, bindAttrs=('exons',))
    
    # finally save everything
    pygrData.save()
    reload(pygrData) 

def check_match(self):
    import pygr.Data
    frag = pygr.Data.Bio.Seq.frag()
    correct = pygr.Data.Bio.Seq.Swissprot.sp42()['HBB1_TORMA'][10:35]
    assert frag == correct, 'seq ival should match'
    assert frag.__doc__ == 'fragment', 'docstring should match'
    assert str(frag) == 'IQHIWSNVNVVEITAKALERVFYVY', 'letters should match'
    assert len(frag) == 25, 'length should match'
    assert len(frag.path) == 142, 'length should match'
    
    #store = PygrDataTextFile('results/seqdb1.pickle')
    #saved = store['hbb1 fragment']
    #assert frag == saved, 'seq ival should matched stored result'

def check_dir(self):
    import pygr.Data
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = pygr.Data.dir('Bio')
    found.sort()
    assert found == expected

def check_dir_noargs(self):
    import pygr.Data
    found = pygr.Data.dir()
    found.sort()
    found2 = pygr.Data.dir('')
    found2.sort()
    assert found == found2

def check_dir_re(self):
    import pygr.Data
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = pygr.Data.dir('^Bio', 'r')
    found.sort()
    assert found == expected

    expected = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.spmap']
    expected.sort()
    found = pygr.Data.dir('^Bio\..+\.sp', 'r')
    found.sort()
    assert found == expected

def check_bind(self):
    import pygr.Data
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin =  sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin, 'automatic schema attribute binding'

def check_bind2(self):
    import pygr.Data
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    exons = hbb.exons.keys()
    assert len(exons)==1, 'number of expected annotations'
    annoDB = pygr.Data.Bio.Annotation.annoDB()
    exon = annoDB[1]
    assert exons[0] == exon, 'test annotation comparison'
    assert exons[0].pathForward is exon,'annotation parent match'
    assert exons[0].sequence == hbb[10:50],'annotation to sequence match'
    onc = sp['HBB1_ONCMY']
    try:
        exons = onc.exons.keys()
        raise ValueError('failed to catch query with no annotations')
    except KeyError:
        pass

class Sequence_Test(TestBase):
    def setUp(self):
        TestBase.setUp(self)
        populate_swissprot(pygr.Data)

    def test_match(self):
        "Test matching sequences"
        check_match(self)

    def test_dir(self):
        "Test labels"
        check_dir(self)
        check_dir_noargs(self)
        check_dir_re(self)

    def test_bind(self):
        "Test bind"
        check_bind(self)
        check_bind2(self)

    def test_schema(self):
        "Test schema"
        sp_hbb1 = testutil.datafile('sp_hbb1') 
        sp2 = seqdb.BlastDB(sp_hbb1)
        sp2.__doc__ = 'another sp'
        import pygr.Data
        pygr.Data.Bio.Seq.sp2 = sp2
        sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        m = pygr.Data.Mapping(sourceDB=sp,targetDB=sp2)
        m.__doc__ = 'sp -> sp2'
        pygr.Data.Bio.Seq.testmap = m
        pygr.Data.schema.Bio.Seq.testmap = pygr.Data.OneToManyRelation(sp, sp2)
        pygr.Data.save()

        reload(pygr.Data)

        sp3 = seqdb.BlastDB(sp_hbb1)
        sp3.__doc__ = 'sp number 3'
        pygr.Data.Bio.Seq.sp3 = sp3
        sp2 = pygr.Data.Bio.Seq.sp2()
        m = pygr.Data.Mapping(sourceDB=sp3,targetDB=sp2)
        m.__doc__ = 'sp3 -> sp2'
        pygr.Data.Bio.Seq.testmap2 = m
        pygr.Data.schema.Bio.Seq.testmap2 = pygr.Data.OneToManyRelation(sp3,
                                                                        sp2)
        l = pygr.Data.getResource.d.keys()
        l.sort()
        assert l == ['Bio.Seq.sp2', 'Bio.Seq.sp3', 'Bio.Seq.testmap2']
        pygr.Data.save()
        g = pygr.Data.getResource.db[0].graph
        expected = set(['Bio.Annotation.annoDB',
                     'Bio.Seq.Swissprot.sp42', 'Bio.Seq.sp2', 'Bio.Seq.sp3'])
        found = set(g.keys()) 
        self.EQ(len(expected - found), 0) 
                    
class InvalidPickle_Test(TestBase):
    
    def setUp(self):
        TestBase.setUp(self)
        class MyUnpicklableClass(object):
            pass
        MyUnpicklableClass.__module__ = '__main__'
        self.bad = MyUnpicklableClass()
        
        self.good = datetime.datetime.today()

    def test_invalid_pickle(self):
        "Testing an invalid pickle"
        import pygr.Data
        s = pygr.Data.dumps(self.good) # should pickle with no errors
        try:
            s = pygr.Data.dumps(self.bad) # should raise exception
            msg = 'failed to catch bad attempt to invalid module ref'
            raise ValueError(msg)
        except pygr.Data.PygrDataNoModuleError:
            pass
        
class XMLRPC_Test(TestBase):
    'create an XMLRPC server and access seqdb from it'
    def setUp(self):
        TestBase.setUp(self)

        args = [ 'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap',
                'Bio.Annotation.annoDB', 'Bio.Annotation.map' ]

        kwargs  = dict(PYGRDATAPATH=self.tempdir.path)

        self.server = testutil.TestXMLRPCServer(*args, **kwargs)

    def test_xmlrpc(self):
        "Test one"
        
        # very hackish
        pygr.Data.pygrDataPath = "http://localhost:%s" % self.server.port
        reload(pygr.Data)
        del pygr.Data.pygrDataPath
        
        check_match(self)
        check_dir(self)
        check_bind(self)
        check_bind2(self)
        
        sb_hbb1 = testutil.datafile('sp_hbb1')
        sp2 = seqdb.BlastDB(sb_hbb1)
        sp2.__doc__ = 'another sp'
        try:
            pygr.Data.Bio.Seq.sp2 = sp2
            pygr.Data.save()
            msg = 'failed to catch bad attempt to write to XMLRPC server'
            raise KeyError(msg)
        except ValueError:
            pass
        
        reload(pygr.Data)

    def tearDown(self):
        'halt the test XMLRPC server'
        self.server.close()


def get_suite():
    "Returns the testsuite"
    tests  = [ 
        Download_Test,
        GenericBuild_Test,
        Sequence_Test,
        InvalidPickle_Test, 
        XMLRPC_Test,
        DNAAnnotation_Test, # move this to top to test test framework isolation
    ]
    return testutil.make_suite(tests)

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)
