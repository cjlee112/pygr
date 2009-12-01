from seqdb import SequenceDB, BasicSeqInfoDict
from annotation import AnnotationDB, TranslationAnnot, TranslationAnnotSlice
import classutil
import sequence
import UserDict


class SeqTranslator(sequence.SequenceBase):
    """Translator object for positive or minus strand of a sequence.
    Slicing returns TranslationAnnotSlice of the appropriate
    TranslationAnnot representing one of the six possible frames for
    this sequence."""

    def __init__(self, db, id, reversePath=None):
        self.id = id
        sequence.SequenceBase.__init__(self)
        if reversePath: # create top-level object for reverse strand
            self.orientation = -1
            self.start = -len(self)
            self.stop = 0
            self._reverse = reversePath
        if self.id not in self.db.seqDB:
            raise KeyError('sequence %s not in db %s' % (self.id, self.db))

    def __getitem__(self, k):
        """get TranslationAnnotSlice for coordinates given by slice k """
        start = k.start                 # deal with [:stop] slices
        if start is None:
            start = self.start
        stop = k.stop                   # deal with [start:] slices
        if stop is None:
            stop = self.stop

        annoID = self._get_anno_id(start)
        a = self.db.annodb[annoID] # get TranslationAnnot object
        s = a.sequence # corresponding nucleotide region

        return a[(start - s.start) / 3: (stop - s.start) / 3]

    def absolute_slice(self, start, stop):
        """get protein slice in absolute nucleotide coords;
        perform negation before slicing """
        if start<0:
            return (-self)[start:stop]
        else:
            return self[start:stop]

    def __len__(self):
        return self.db.seqInfoDict[self.id].length

    def __neg__(self):
        """get SeqTranslator for the opposite strand """
        try:
            return self._reverse
        except AttributeError:
            self._reverse = self.__class__(self.db, self.id,
                                           reversePath=self)
            return self._reverse

    def _get_anno_id(self, start):
        """get annotation ID for frame starting at start """
        if self.orientation > 0: # positive strand
            return '%s:%d' % (self.id, start % 3)
        else: # negative strand
            return '%s:-%d' % (self.id, (-start) % 3)

    def iter_frames(self):
        'iterate over the 6 possible frames, yielding TranslationAnnot'
        for frame in ('0', '1', '2', '-0', '-1', '-2'):
            yield self.db.annodb['%s:%s' % (self.id, frame)]

    def __repr__(self):
        return 'SeqTranslator(' + sequence.SequenceBase.__repr__(self) + ')'


class TranslationDB(SequenceDB):
    """Provides an automatic translation interface for a nucleotide sequence
    database: slicing of top-level sequence objects will return the
    corresponding TranslationAnnotSlice for that slice, i.e. the
    translated protein sequence, rather than the nucleotide sequence. """
    itemClass = SeqTranslator
    _seqtype = sequence.DNA_SEQTYPE

    def __init__(self, seqDB, **kwargs):
        self.seqDB = seqDB
        try:
            self.seqInfoDict = seqDB.seqInfoDict
        except AttributeError:
            self.seqInfoDict = BasicSeqInfoDict(seqDB)
        self.annodb = AnnotationDB(SixFrameInfo(seqDB), seqDB,
                                   itemClass=TranslationAnnot,
                                   itemSliceClass=TranslationAnnotSlice,
                                   sliceAttrDict=dict(id=0, start=1, stop=2),
                                   checkFirstID=False)
        SequenceDB.__init__(self, **kwargs)


class SixFrameInfo(object, UserDict.DictMixin):
    """Dictionary of slice info for all six frames of each seq in seqDB. """

    def __init__(self, seqDB):
        self.seqDB = seqDB

    def __getitem__(self, k):
        "convert ID of form seqID:frame into slice info tuple"
        i = k.rfind(':')
        if i < 0:
            raise KeyError('invalid TranslationInfo key: %s' % (k, ))
        seqID = k[:i]
        length = len(self.seqDB[seqID]) # sequence length
        frame = int(k[i+1:])
        if k[i+1] == '-': # negative frame -0, -1, or -2
            return (seqID, -(length - ((length + frame) % 3)), frame)
        else: # positive frame 0, 1 or 2
            return (seqID, frame, length - ((length - frame) % 3))

    def __len__(self):
        return 6 * len(self.seqDB)

    def __iter__(self):
        for seqID in self.seqDB:
            for frame in (':0', ':1', ':2', ':-0', ':-1', ':-2'):
                yield seqID + frame

    def keys(self):
        return list(self)

    # these methods should not be implemented for read-only database.
    clear = setdefault = pop = popitem = copy = update = \
            classutil.read_only_error


def get_translation_db(seqDB):
    """Use cached seqDB.translationDB if already present, or create it """
    try:
        return seqDB.translationDB
    except AttributeError: # create a new TranslationAnnot DB
        tdb = TranslationDB(seqDB)
        try:
            seqDB.translationDB = tdb
        except AttributeError:
            pass # won't let us cache? Just hand back the TranslationDB
        return tdb
