import unittest

from testlib import testutil, PygrTestProgram
from pygr import translationDB, seqdb


class TranslationDB_Test(unittest.TestCase):

    def setUp(self):
        hbb1_mouse = testutil.datafile('hbb1_mouse.fa')
        self.dna = seqdb.SequenceFileDB(hbb1_mouse)
        self.tdb = translationDB.get_translation_db(self.dna)

    def test_basic_slice(self):
        id = 'gi|171854975|dbj|AB364477.1|'
        tseq = self.tdb[id][0:99]
        assert str(tseq)[0:10] == 'MVHLTDAEKA'

        tseq = self.tdb[id][1:100]
        assert str(tseq)[0:10] == 'WCT*LMLRRL'

    def test_slice_empty_stop(self):
        id = 'gi|171854975|dbj|AB364477.1|'
        tseq = self.tdb[id][0:]
        assert str(tseq)[0:10] == 'MVHLTDAEKA'

        tseq = self.tdb[id][1:]
        assert str(tseq)[0:10] == 'WCT*LMLRRL'

    def test_slice_empty_start(self):
        id = 'gi|171854975|dbj|AB364477.1|'
        tseq = self.tdb[id][:99]
        assert str(tseq)[0:10] == 'MVHLTDAEKA'

    def test_repr_ne(self):
        """
        Make sure there's some way to distinguish translated seqs from
        regular, visually!
        """
        id = 'gi|171854975|dbj|AB364477.1|'

        seq = self.dna[id]
        tseq = self.tdb[id]

        assert repr(seq) != repr(tseq)

    def test_invalid_annodb_key_str(self):
        """
        The invalid key should be mentioned in the KeyError...
        """
        try:
            self.tdb.annodb['fooBar']
            assert 0, "should not reach this point"
        except KeyError, e:
            assert 'fooBar' in str(e)

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
