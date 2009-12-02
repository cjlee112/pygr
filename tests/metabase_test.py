import datetime
import os
import pickle
import socket
import unittest

from testlib import testutil, PygrTestProgram, SkipTest
from pygr import seqdb, cnestedlist, metabase, mapping, logger, sqlgraph
from pygr.downloader import SourceURL, GenericBuilder, uncompress_file, \
     do_unzip, do_gunzip

try:
    set
except NameError:
    from sets import Set as set


class TestBase(unittest.TestCase):
    "A base class to all metabase test classes"

    def setUp(self, worldbasePath=None, **kwargs):
        # overwrite the WORLDBASEPATH environment variable
        self.tempdir = testutil.TempDir('pygrdata')
        if worldbasePath is None:
            worldbasePath = self.tempdir.path
        self.metabase = metabase.MetabaseList(worldbasePath, **kwargs)
        self.pygrData = self.metabase.Data
        self.schema = self.metabase.Schema
        # handy shortcuts
        self.EQ = self.assertEqual


class Download_Test(TestBase):
    "Save seq db and interval to metabase shelve"

    # tested elsewhere as well, on Linux makes gzip ask for permissions
    # to overwrite
    def test_download(self):
        "Downloading of gzipped file using metabase"

        url = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
        url.__doc__ = 'test download'

        self.metabase.add_resource('Bio.Test.Download1', url)
        self.metabase.commit()

        # performs the download
        fpath = self.pygrData.Bio.Test.Download1()
        h = testutil.get_file_md5(fpath)
        self.assertEqual(h.hexdigest(), 'f95656496c5182d6cff9a56153c9db73')
        os.remove(fpath)

    def test_run_unzip(self):
        'test uncompress_file unzip'
        zipfile = testutil.datafile('test.zip')
        outfile = testutil.tempdatafile('test.out')
        uncompress_file(zipfile, newpath=outfile, singleFile=True)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '12ada4c51ccb4c7277c16f1a3c000b90')

    def test_do_unzip(self):
        'test do_unzip'
        zipfile = testutil.datafile('test.zip')
        outfile = testutil.tempdatafile('test2.out')
        do_unzip(zipfile, outfile, singleFile=True)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '12ada4c51ccb4c7277c16f1a3c000b90')

    def test_run_gunzip(self):
        'test uncompress_file gunzip'
        zipfile = testutil.datafile('test.gz')
        outfile = testutil.tempdatafile('test3.out')
        uncompress_file(zipfile, newpath=outfile)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '1db5a21a01ba465fd26c3203d6589b0e')

    def test_do_gunzip(self):
        'test do_gunzip'
        zipfile = testutil.datafile('test.gz')
        outfile = testutil.tempdatafile('test4.out')
        do_gunzip(zipfile, outfile)
        h = testutil.get_file_md5(outfile)
        self.assertEqual(h.hexdigest(), '1db5a21a01ba465fd26c3203d6589b0e')


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

            self.pygrData.Bio.Test.dna = db
            annoDB = seqdb.AnnotationDB({1: ('seq1', 5, 10, 'fred'),
                                         2: ('seq1', -60, -50, 'bob'),
                                         3: ('seq2', -20, -10, 'mary')},
                                        db,
                                  sliceAttrDict=dict(id=0, start=1, stop=2,
                                                     name=3))
            annoDB.__doc__ = 'trivial annotation'
            self.pygrData.Bio.Test.annoDB = annoDB
            nlmsa = cnestedlist.NLMSA(tryannot, 'w', pairwiseMode=True,
                                      bidirectional=False)
            try:
                for annID in annoDB:
                    nlmsa.addAnnotation(annoDB[annID])

                nlmsa.build()
                nlmsa.__doc__ = 'trivial map'
                self.pygrData.Bio.Test.map = nlmsa
                self.schema.Bio.Test.map = metabase.ManyToManyRelation(db,
                                                 annoDB, bindAttrs=('exons', ))
                self.metabase.commit()
                self.metabase.clear_cache()
            finally:
                nlmsa.close()
        finally:
            db.close()

    def test_annotation(self):
        "Annotation test"
        db = self.pygrData.Bio.Test.dna()
        try:
            s1 = db['seq1']
            l = s1.exons.keys()
            annoDB = self.pygrData.Bio.Test.annoDB()
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
            self.pygrData.Bio.Test.map().close() # close NLMSA


def populate_swissprot(pygrData, pygrDataSchema):
    "Populate the current pygrData with swissprot data"
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
    m = mapping.Mapping(sourceDB=sp, targetDB=sp)
    trypsin = sp['PRCA_ANAVA']
    m[hbb] = trypsin
    m.__doc__ = 'map sp to itself'
    pygrData.Bio.Seq.spmap = m

    # create an annotation database and bind as exons attribute
    pygrDataSchema.Bio.Seq.spmap = metabase.OneToManyRelation(sp, sp,
                                                         bindAttrs=('buddy', ))
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
    pygrData.Bio.Annotation.annoDB = annoDB
    pygrData.Bio.Annotation.map = nlmsa
    pygrDataSchema.Bio.Annotation.map = \
         metabase.ManyToManyRelation(sp, annoDB, bindAttrs=('exons', ))


def check_match(self):
    frag = self.pygrData.Bio.Seq.frag()
    correct = self.pygrData.Bio.Seq.Swissprot.sp42()['HBB1_TORMA'][10:35]
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
    found = self.metabase.dir('Bio')
    found.sort()
    assert found == expected


def check_dir_noargs(self):
    found = self.metabase.dir()
    found.sort()
    found2 = self.metabase.dir('')
    found2.sort()
    assert found == found2


def check_dir_download(self):
    found = self.metabase.dir(download=True)
    found.sort()
    found2 = self.metabase.dir('', download=True)
    found2.sort()
    assert len(found) == 0
    assert found == found2


def check_dir_re(self):
    expected=['Bio.Annotation.annoDB', 'Bio.Annotation.map',
                'Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap']
    expected.sort()
    found = self.metabase.dir('^Bio', 'r')
    found.sort()
    assert found == expected

    expected = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.spmap']
    expected.sort()
    found = self.metabase.dir('^Bio\..+\.sp', 'r')
    found.sort()
    assert found == expected


def check_bind(self):
    sp = self.pygrData.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    trypsin = sp['PRCA_ANAVA']
    assert hbb.buddy == trypsin, 'automatic schema attribute binding'


def check_bind2(self):
    sp = self.pygrData.Bio.Seq.Swissprot.sp42()
    hbb = sp['HBB1_TORMA']
    exons = hbb.exons.keys()
    assert len(exons)==1, 'number of expected annotations'
    annoDB = self.pygrData.Bio.Annotation.annoDB()
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
        populate_swissprot(self.pygrData, self.schema)
        self.metabase.commit() # finally save everything
        self.metabase.clear_cache() # force all requests to reload

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
        self.pygrData.Bio.Seq.sp2 = sp2
        sp = self.pygrData.Bio.Seq.Swissprot.sp42()
        m = mapping.Mapping(sourceDB=sp, targetDB=sp2)
        m.__doc__ = 'sp -> sp2'
        self.pygrData.Bio.Seq.testmap = m
        self.schema.Bio.Seq.testmap = metabase.OneToManyRelation(sp, sp2)
        self.metabase.commit()

        self.metabase.clear_cache()

        sp3 = seqdb.BlastDB(sp_hbb1)
        sp3.__doc__ = 'sp number 3'
        self.pygrData.Bio.Seq.sp3 = sp3
        sp2 = self.pygrData.Bio.Seq.sp2()
        m = mapping.Mapping(sourceDB=sp3, targetDB=sp2)
        m.__doc__ = 'sp3 -> sp2'
        self.pygrData.Bio.Seq.testmap2 = m
        self.schema.Bio.Seq.testmap2 = metabase.OneToManyRelation(sp3, sp2)
        l = self.metabase.resourceCache.keys()
        l.sort()
        assert l == ['Bio.Seq.sp2', 'Bio.Seq.sp3', 'Bio.Seq.testmap2']
        self.metabase.commit()
        g = self.metabase.writer.storage.graph
        expected = set(['Bio.Annotation.annoDB',
                     'Bio.Seq.Swissprot.sp42', 'Bio.Seq.sp2', 'Bio.Seq.sp3'])
        found = set(g.keys())
        self.EQ(len(expected - found), 0)


class SQL_Sequence_Test(Sequence_Test):

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest

        self.dbtable = testutil.temp_table_name() # create temp db tables
        Sequence_Test.setUp(self, worldbasePath='mysql:' + self.dbtable,
                            mdbArgs=dict(createLayer='temp'))

    def tearDown(self):
        testutil.drop_tables(self.metabase.writer.storage.cursor, self.dbtable)


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
        s = metabase.dumps(self.good) # should pickle with no errors
        try:
            s = metabase.dumps(self.bad) # should raise exception
            msg = 'failed to catch bad attempt to invalid module ref'
            raise ValueError(msg)
        except metabase.WorldbaseNoModuleError:
            pass


class DBServerInfo_Test(TestBase):

    def setUp(self):
        TestBase.setUp(self)
        logger.debug('accessing ensembldb.ensembl.org')
        conn = sqlgraph.DBServerInfo(host='ensembldb.ensembl.org',
                                     user='anonymous', passwd='')
        try:
            translationDB = sqlgraph.SQLTable(
                'homo_sapiens_core_47_36i.translation', serverInfo=conn)
            exonDB = sqlgraph.SQLTable('homo_sapiens_core_47_36i.exon',
                                       serverInfo=conn)

            sql_statement = '''SELECT t3.exon_id FROM
homo_sapiens_core_47_36i.translation AS tr,
homo_sapiens_core_47_36i.exon_transcript AS t1,
homo_sapiens_core_47_36i.exon_transcript AS t2,
homo_sapiens_core_47_36i.exon_transcript AS t3 WHERE tr.translation_id = %s
AND tr.transcript_id = t1.transcript_id AND t1.transcript_id =
t2.transcript_id AND t2.transcript_id = t3.transcript_id AND t1.exon_id =
tr.start_exon_id AND t2.exon_id = tr.end_exon_id AND t3.rank >= t1.rank AND
t3.rank <= t2.rank ORDER BY t3.rank
'''
            translationExons = sqlgraph.GraphView(translationDB, exonDB,
                                                  sql_statement,
                                                  serverInfo=conn)
        except ImportError:
            raise SkipTest('missing MySQLdb module?')
        translationExons.__doc__ = 'test saving exon graph'
        self.pygrData.Bio.Ensembl.TranslationExons = translationExons
        self.metabase.commit()
        self.metabase.clear_cache()

    def test_orderBy(self):
        """Test saving DBServerInfo to metabase"""
        translationExons = self.pygrData.Bio.Ensembl.TranslationExons()
        translation = translationExons.sourceDB[15121]
        exons = translationExons[translation] # do the query
        result = [e.id for e in exons]
        correct = [95160, 95020, 95035, 95050, 95059, 95069, 95081, 95088,
                   95101, 95110, 95172]
        self.assertEqual(result, correct) # make sure the exact order matches


class XMLRPC_Test(TestBase):
    'create an XMLRPC server and access seqdb from it'

    def setUp(self):
        TestBase.setUp(self)
        populate_swissprot(self.pygrData, self.schema) # save some data
        self.metabase.commit() # finally save everything
        self.metabase.clear_cache() # force all requests to reload

        res = ['Bio.Seq.Swissprot.sp42', 'Bio.Seq.frag', 'Bio.Seq.spmap',
               'Bio.Annotation.annoDB', 'Bio.Annotation.map']
        self.server = testutil.TestXMLRPCServer(res, self.tempdir.path)

    def test_xmlrpc(self):
        "Test XMLRPC"
        self.metabase.clear_cache() # force all requests to reload
        self.metabase.update("http://localhost:%s" % self.server.port)

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
            self.pygrData.Bio.Seq.sp2 = sp2
            self.metabase.commit()
            msg = 'failed to catch bad attempt to write to XMLRPC server'
            raise KeyError(msg)
        except ValueError:
            pass

    def tearDown(self):
        'halt the test XMLRPC server'
        self.server.close()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
