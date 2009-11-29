from __future__ import generators
from pygr.sequence import *
#from pathquery import *


class AnonSequence(Sequence):
    """Defines a sequence class with unknown sequence, but
    known length"""

    def __init__(self, length, id):
        s = ''
        self.known = list()
        Sequence.__init__(self, s, id)
        self.stop = length

    def seqsplice(self, s, start, end):
        (begin, stop, step) = slice(start, end).indices(self.stop)

        if (start < end):
            self.known += [(s, start, stop)]
        elif start > end:
            self.known += [(s[::-1], start, stop)]

    def known_int(self):
        for u in self.known:
            yield {'src_id': self.id, 'start': u[1], 'end': u[2], 'seq': u[0]}


class ReferenceSequence(Sequence):
    """Defines a reference sequence class that is subscriptable
    by other sequences. If sequence ids match the resulting sequnce
    will reference this class. This is useful for coordinate
    transforms when an unknown sequence intervals are transformed
    to known sequence"""

    def __init__(self, s, id):
        Sequence.__init__(self, s, id)

    def __getitem__(self, iv):
        if(isinstance(iv, SeqPath)):
            if(iv.id == self.id):
                s = self[iv.start:iv.stop:iv.step]
                s.orientation = iv.orientation
                return s
        else:
            return SeqPath.__getitem__(self, iv)

    def mapCoordinates(self, obj):
        m = PathMapping2()
        for ival in obj:
            m[ival] = self[ival]
        return m


class UnkSequence(SeqPath):
    """Defines a sequence class for pure interval manipulation.
    No sequence information (i.e. length, or seq itself) is needed.
    """

    def __init__(self, id, start=0, end=0, step=1, orientation=1):
        self.id = id
        SeqPath.__init__(self, id)
        self.start = start
        self.stop = end
        self.step = step
        self.orientation = orientation
        if (self.start is not None and self.stop is not None
           and self.start > self.stop):
            t = self.start
            if (self.stop >= 0):
                self.start = self.stop + 1
            else:
                self.start = self.stop
            if (t >= 0):
                self.stop = t + 1
            else:
                self.stop = t
            self.orientation = -self.orientation

    def __getitem__(self, k):
        if isinstance(k, types.SliceType):
            (start, stop, step) = (k.start, k.stop, k.step)
            if k.step == None:
                step = 1
        elif isinstance(k, types.IntType):
            start = k
            stop = k + 1
            if (k == -1):
                stop = None
            step = 1
            return self[start:stop:step]
        else:
            raise KeyError('requires a slice object or integer key')
        if self.step == 1 and stop != None:
            return UnkSequence(self.id, self.start + start * self.step,
                           self.start + stop * self.step,
                           self.step * step, self.orientation)
        else:
            return UnkSequence(self.id, start, stop, step, self.orientation)
