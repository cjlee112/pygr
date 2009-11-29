import datetime
import md5
import os
import pickle
import socket
import unittest
import warnings

import testlib
from testlib import testutil, SkipTest, PygrTestProgram
from pygr import seqdb, cnestedlist, mapping
from pygr.downloader import SourceURL, GenericBuilder


warnings.simplefilter("ignore")
import pygr.Data
warnings.simplefilter("default")

try:
    set
except NameError:
    from sets import Set as set


class TestBase(unittest.TestCase):
    "A base class to all pygr.Data test classes"

    def setUp(self, pygrDataPath=None, **kwargs):
        # overwrite the WORLDBASEPATH environment variable
        self.tempdir = testutil.TempDir('pygrdata')
        if pygrDataPath is None:
            pygrDataPath = self.tempdir.path
        pygr.Data.clear_cache() # make sure no old data loaded
        pygr.Data.update(pygrDataPath, **kwargs) # use this path
        # handy shortcuts
        self.EQ = self.assertEqual


class Download_Test(TestBase):
    "Save seq db and interval to pygr.Data shelve"

    # tested elsewhere as well, on Linux makes gzip ask for permissions
    # to overwrite
    def test_download(self):
        "Downloading of gzipped file using pygr.Data"

        url = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
        url.__doc__ = 'test download'

        pygr.Data.addResource('Bio.Test.Download1', url)
        pygr.Data.save()

        # performs the download
        fpath = pygr.Data.Bio.Test.Download1()
        h = testutil.get_file_md5(fpath)
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

    def setUp(self, **kwargs):
        TestBase.setUp(self)
        dnaseq = testutil.datafile('dnaseq.fasta')
        tryannot = testutil.tempdatafile('tryannot')

        db = seqdb.BlastDB(dnaseq)
        try:
            db.__doc__ = 'little dna'

            pygr.Data.Bio.Test.dna = db
            annoDB = seqdb.AnnotationDB({1: ('seq1', 5, 10, 'fred'),
                                         2: ('seq1', -60, -50, 'bob'),
                                         3: ('seq2', -20, -10, 'mary')},
                                        db,
                                  sliceAttrDict=dict(id=0, start=1, stop=2,
                                                     name=3))
            annoDB.__doc__ = 'trivial annotation'
            pygr.Data.Bio.Test.annoDB = annoDB
            nlmsa = cnestedlist.NLMSA(tryannot, 'w', pairwiseMode=True,
                                      bidirectional=False)
            try:
                for annID in annoDB:
                    nlmsa.addAnnotation(annoDB[annID])

                nlmsa.build()
                nlmsa.__doc__ = 'trivial map'
                pygr.Data.Bio.Test.map = nlmsa
                pygr.Data.schema.Bio.Test.map = \
                       pygr.Data.ManyToManyRelation(db, annoDB,
                                                    bindAttrs=('exons', ))
                pygr.Data.save()
                pygr.Data.clear_cache()
            finally:
                nlmsa.close()
        finally:
            db.close()

    def test_annotation(self):
        "Annotation test"
        db = pygr.Data.Bio.Test.dna()
        try:
            s1 = db['seq1']
            l = s1.exons.keys()
            annoDB = pygr.Data.Bio.Test.annoDB()
            assert l == [annoDB[1], -(annoDB[2])]
            assert l[0].sequence == s1[5:10]
            assert l[1].sequence == s1[50:60]
            assert l[0].name == 'fred', 'test annotation attribute access'
            assert l[1].name == 'bob'
            sneg = -(s1[:55])
            l = sneg.exons.keys()
            assert l == [annoDB[2][5:], -(annoDB[1])]
            assert l[0].sequence == -(s1[50:55])
            assert l[1].sequence == -(s1[5:10])
            assert l[0].name == 'bob'
            assert l[1].name == 'fred'
        finally:
            db.close() # close SequenceFileDB
            pygr.Data.Bio.Test.map().close() # close NLMSA


def populate_swissprot():
    "Populate the current pygrData with swissprot data"
    # build BlastDB out of the sequences
    sp_hbb1 = testutil.datafile('sp_hbb1')
    sp = seqdb.BlastDB(sp_hbb1)
    sp.__doc__ = 'little swissprot'
    pygr.Data.Bio.Seq.Swissprot.sp42 = sp

    # also store a fragment
    hbb = sp['HBB1_TORMA']
    ival= hbb[10:35]
    ival.__doc__ = 'fragment'
    pygr.Data.Bio.Seq.frag = ival

    # build a mapping to itself
    m = mapping.Mapping(sourceDB=sp, targetDB=sp)
    trypsin = sp['PRCA_ANAVA']
    m[hbb] = trypsin
    m.__doc__ = 'map sp to itself'
    pygr.Data.Bio.Seq.spmap = m

    # create an annotation database and bind as exons attribute
    pygr.Data.schema.Bio.Seq.spmap = \
           pygr.Data.OneToManyRelation(sp, sp, bindAttrs=('buddy', ))
    annoDB = seqdb.AnnotationDB({1: ('HBB1_TORMA', 10, 50)}, sp,
                                sliceAttrDict=dict(id=0, start=1, stop=2))
    exon = annoDB[1]

    # generate the names where these will be stored
    tempdir = testutil.TempDir('exonAnnot')
    filename = tempdir.subfile('cnested')
    nlmsa = cnestedlist.NLMSA(filename, 'w', pairwiseMode=True,
                              bidirectional=False)
    nlmsa.addAnnotation(exon)
    nlmsa.build()
    annoDB.__doc__ = 'a little annotation db'
    nlmsa.__doc__ = 'a little map'
    pygr.Data.Bio.Annotation.annoDB = annoDB
    pygr.Data.Bio.Annotation.map = nlmsa
    pygr.Data.schema.Bio.Annotation.map = \
         pygr.Data.ManyToManyRelation(sp, annoDB, bindAttrs=('exons', ))


def check_match(self):
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
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = pygr.Data.dir('Bio')
    found.sort()
    assert found == expected


def check_dir_noargs(self):
    found = pygr.Data.dir()
    found.sort()
    found2 = pygr.Data.dir('')
    found2.sort()
    assert found == found2


def check_dir_download(self):
    found = pygr.Data.dir(download=True)
    found.sort()
    found2 = pygr.Data.dir('', download=True)
    found2.sort()
    assert len(found) == 0
    assert found == found2


def check_dir_re(self):
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
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin = sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin, 'automatic schema attribute binding'


def check_bind2(self):
    sp = pygr.Data.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    exons = hbb.exons.keys()
    assert len(exons) == 1, 'number of expected annotations'
    annoDB = pygr.Data.Bio.Annotation.annoDB()
    exon = annoDB[1]
    assert exons[0] == exon, 'test annotation comparison'
    assert exons[0].pathForward is exon, 'annotation parent match'
    assert exons[0].sequence == hbb[10:50], 'annotation to sequence match'
    onc = sp['HBB1_ONCMY']
    try:
        exons = onc.exons.keys()
        raise ValueError('failed to catch query with no annotations')
    except KeyError:
        pass


class Sequence_Test(TestBase):

    def setUp(self, *args, **kwargs):
        TestBase.setUp(self, *args, **kwargs)
        populate_swissprot()
        pygr.Data.save() # finally save everything
        pygr.Data.clear_cache() # force all requests to reload

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
        pygr.Data.Bio.Seq.sp2 = sp2
        sp = pygr.Data.Bio.Seq.Swissprot.sp42()
        m = mapping.Mapping(sourceDB=sp, targetDB=sp2)
        m.__doc__ = 'sp -> sp2'
        pygr.Data.Bio.Seq.testmap = m
        pygr.Data.schema.Bio.Seq.testmap = pygr.Data.OneToManyRelation(sp, sp2)
        pygr.Data.save()

        pygr.Data.clear_cache()

        sp3 = seqdb.BlastDB(sp_hbb1)
        sp3.__doc__ = 'sp number 3'
        pygr.Data.Bio.Seq.sp3 = sp3
        sp2 = pygr.Data.Bio.Seq.sp2()
        m = mapping.Mapping(sourceDB=sp3, targetDB=sp2)
        m.__doc__ = 'sp3 -> sp2'
        pygr.Data.Bio.Seq.testmap2 = m
        pygr.Data.schema.Bio.Seq.testmap2 = pygr.Data.OneToManyRelation(sp3,
                                                                        sp2)
        # List all cached resources.
        l = pygr.Data.getResource.resourceCache.keys()
        l.sort()
        assert l == ['Bio.Seq.sp2', 'Bio.Seq.sp3', 'Bio.Seq.testmap2']
        pygr.Data.save()
        g = pygr.Data.getResource.writer.storage.graph
        expected = set(['Bio.Annotation.annoDB',
                     'Bio.Seq.Swissprot.sp42', 'Bio.Seq.sp2', 'Bio.Seq.sp3'])
        found = set(g.keys())
        self.EQ(len(expected - found), 0)


class SQL_Sequence_Test(Sequence_Test):

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL installed")

        self.dbtable = testutil.temp_table_name() # create temp db tables
        Sequence_Test.setUp(self, pygrDataPath='mysql:' + self.dbtable,
                            mdbArgs=dict(createLayer='temp'))

    def tearDown(self):
        testutil.drop_tables(pygr.Data.getResource.writer.storage.cursor,
                             self.dbtable)


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
        s = pygr.Data.dumps(self.good) # should pickle with no errors
        try:
            s = pygr.Data.dumps(self.bad) # should raise exception
            msg = 'failed to catch bad attempt to invalid module ref'
            raise ValueError(msg)
        except pygr.Data.WorldbaseNoModuleError:
            pass


class XMLRPC_Test(TestBase):
    'create an XMLRPC server and access seqdb from it'

    def setUp(self):
        TestBase.setUp(self)
        populate_swissprot() # save some data
        pygr.Data.save() # finally save everything
        pygr.Data.clear_cache() # force all requests to reload

        res = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap',
               'Bio.Annotation.annoDB', 'Bio.Annotation.map']
        self.server = testutil.TestXMLRPCServer(res, self.tempdir.path)

    def test_xmlrpc(self):
        "Test XMLRPC"
        pygr.Data.clear_cache() # force all requests to reload
        pygr.Data.update("http://localhost:%s" % self.server.port)

        check_match(self)
        check_dir(self)
        check_dir_noargs(self)
        check_dir_download(self)
        check_dir_re(self)
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

    def tearDown(self):
        'halt the test XMLRPC server'
        self.server.close()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
