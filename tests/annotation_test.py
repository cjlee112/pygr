import unittest
from testlib import testutil, PygrTestProgram
from pygr import sequence, seqdb, sequtil, annotation
from pygr.sequence import Sequence
from pygr.annotation import AnnotationDB


class AnnotationSeq_Test(unittest.TestCase):

    def setUp(self):

        class Annotation(object):

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        slicedb = dict(X=Annotation(id='seq', start=0, stop=10),
                       Y=Annotation(id='seq', start=0, stop=10),
                       Z=Annotation(id='seq2', start=0, stop=10))

        sequence_dict = dict(seq = Sequence('ATGGGGCCGATTG', 'seq', ),
                             seq2 = Sequence('ATGGGGCCGATTG', 'seq2'))

        self.db = AnnotationDB(slicedb, sequence_dict)

        self.annot = self.db['X']

    def test_orientation_index_error(self):
        db = self.db
        db.sliceAttrDict = dict(id=0, start=1, stop=2, orientation=3)

        # index error should be caught silently, so this should succeed.
        db.new_annotation('some name', ('seq', 5, 8))

    def test_cmp(self):
        assert cmp(self.annot, None) == -1
        assert cmp(self.annot, self.annot) == 0

        a = self.annot
        b = self.annot

        assert cmp(a, b) == 0
        assert a[1:2] == b[1:2]

        # different annotations, even though they point at the same sequence
        assert cmp(self.annot, self.db['Y']) == -1

        # different sequences, even though they point at the same actual seq
        assert cmp(self.annot, self.db['Z']) == -1

    def test_strslice(self):
        try:
            str(self.annot)
            assert 0, "should not get here"
        except ValueError:
            pass

    def test_repr(self):
        annot = self.annot
        assert repr(annot) == 'annotX[0:10]'
        assert repr(-annot) == '-annotX[0:10]'

        annot.annotationType = 'foo'
        assert repr(annot) == 'fooX[0:10]'
        del annot.annotationType

    def test_seq(self):
        assert repr(self.annot.sequence) == 'seq[0:10]'

    def test_slice(self):
        assert repr(self.annot[1:2].sequence) == 'seq[1:2]'


class AnnotationDB_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'AnnotationDB'.
    """

    def setUp(self):

        class Annotation(object):

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        slicedb = dict(annot1=Annotation(id='seq', start=0, stop=10),
                       annot2=Annotation(id='seq', start=5, stop=9))
        sequence_dict = dict(seq = Sequence('ATGGGGCCGATTG', 'seq'))
        self.db = AnnotationDB(slicedb, sequence_dict)

    def test_setitem(self):
        try:
            self.db['foo'] = 'bar'      # use 'add_annotation' instead
            assert 0, "should not reach this point"
        except KeyError:
            pass

    def test_hash(self):
        x = hash(self.db)               # works!
        d = dict(foo=self.db)           # also works!

    def test_keys(self):
        "AnnotationDB keys"
        k = self.db.keys()
        k.sort()
        assert k == ['annot1', 'annot2'], k

    def test_contains(self):
        "AnnotationDB contains"
        assert 'annot1' in self.db, self.db.keys()
        assert 'annot2' in self.db
        assert 'foo' not in self.db

    def test_has_key(self):
        "AnnotationDB has key"
        assert 'annot1' in self.db
        assert 'annot2' in self.db
        assert 'foo' not in self.db

    def test_get(self):
        "AnnotationDB get"
        assert self.db.get('foo') is None
        assert self.db.get('annot1') is not None
        assert str(self.db.get('annot1').sequence).startswith('ATGGGGC')
        assert self.db.get('annot2') is not None
        assert str(self.db.get('annot2').sequence).startswith('GCCG')

    def test_items(self):
        "AnnotationDB items"
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == ['annot1', 'annot2']

    def test_iterkeys(self):
        "AnnotationDB iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "AnnotationDB itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv[0] == iv[0]
        assert kv == iv, (kv, iv)

    def test_iteritems(self):
        "AnnotationDB iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii, (ki, ii)

    def test_readonly(self):
        "AnnotationDB readonly"
        try:
            self.db.copy()              # what should 'copy' do on AD?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'setdefault' do on AD?
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'update' do on AD?
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass

    def test_equality(self):
        "AnnotationDB equality"
        # Check that separately generated annotation objects test equal"
        key = 'annot1'
        db = self.db
        x = db.sliceAnnotation(key, db.sliceDB[key])
        y = db.sliceAnnotation(key, db.sliceDB[key])
        assert x == y

    def test_bad_seqdict(self):
        "AnnotationDB bad seqdict"

        class Annotation(object):

            def __init__(self, **kwargs):
                self.__dict__.update(kwargs)

        slicedb = dict(annot1=Annotation(id='seq', start=0, stop=10),
                       annot2=Annotation(id='seq', start=5, stop=9))
        foo_dict = dict(foo=Sequence('ATGGGGCCGATTG', 'foo'))
        try:
            db = AnnotationDB(slicedb, foo_dict)
            assert 0, "incorrect seqdb; key error should be raised"
        except KeyError:
            pass


class Translation_Test(unittest.TestCase):

    def setUp(self):
        self.M = sequence.Sequence('ATG', 'methionine')
        self.FLIM = sequence.Sequence('TTTCTAATTATG', 'flim')
        self.db = dict(methionine=self.M, flim=self.FLIM)

    def test_simple_translate(self):
        db = self.db

        assert sequtil.translate_orf(str(db['methionine'])) == 'M'
        assert sequtil.translate_orf(str(db['flim'])) == 'FLIM'

    def test_translation_db(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2))

        aa = aa_db.new_annotation('foo', (self.M.id, 0, 3))
        orf = aa_db['foo']
        assert str(orf) == 'M'

        aa2 = aa_db.new_annotation('bar', (self.FLIM.id, 0, 12))
        orf = aa_db['bar']
        assert str(orf) == 'FLIM'

    def test_slice_descr(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2))

        aa = aa_db.new_annotation('bar', (self.FLIM.id, 0, 12))
        assert str(aa) == 'FLIM'
        assert str(aa[1:3].sequence) == 'CTAATT'

    def test_positive_frames(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2))

        f1 = aa_db.new_annotation('f1', (self.FLIM.id, 0, 12))
        assert str(f1) == 'FLIM'
        assert f1.frame == +1

        f2 = aa_db.new_annotation('f2', (self.FLIM.id, 1, 10))
        assert str(f2) == 'F*L'
        assert f2.frame == +2

        f3 = aa_db.new_annotation('f3', (self.FLIM.id, 2, 11))
        assert str(f3) == 'SNY'
        assert f3.frame == +3

    def test_negative_frames(self):
        aa_db = annotation.AnnotationDB({}, self.db,
                          itemClass=annotation.TranslationAnnot,
                          itemSliceClass=annotation.TranslationAnnotSlice,
                          sliceAttrDict=dict(id=0, start=1, stop=2,
                                             orientation=3))

        f1 = aa_db.new_annotation('f1', (self.FLIM.id, 0, 12, -1))
        assert str(f1) == 'HN*K'
        assert f1.frame == -2

        f2 = aa_db.new_annotation('f2', (self.FLIM.id, 1, 10, -1))
        assert str(f2) == '*LE'
        assert f2.frame == -1

        f3 = aa_db.new_annotation('f3', (self.FLIM.id, 2, 11, -1))
        assert str(f3) == 'IIR'
        assert f3.frame == -3

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
