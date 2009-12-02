
from __future__ import generators
import types
from sequtil import *


NOT_ON_SAME_PATH = -2


class ReadOnlyAttribute(object):

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, klass):
        return getattr(obj, self.attr)


###################################################################
#
# INTERVAL - INTERVAL MAPPING
# CORRECTLY HANDLES SCALING AND ORIENTATION TRANSFORMATIONS
# ASSUMES A SIMPLE SCALAR TRANSFORMATION FROM ONE COORD SYSTEM
# TO THE OTHER.  DOES NOT HANDLE INDELS WITHIN THE MAPPING!

class IntervalTransform(object):
    "Represents coordinate transformation from one interval to another"
    srcPath=ReadOnlyAttribute('_srcPath') # PREVENT USER FROM MODIFYING THESE!
    destPath=ReadOnlyAttribute('_destPath')

    def __init__(self, srcPath, destPath, edgeInfo=None,
                 edgeAttr=None, edgeIndex=None):
        "MAP FROM srcPath -> destPath"
        self.scale = len(destPath) / float(len(srcPath))
        self._srcPath = srcPath
        self._destPath = destPath
        if edgeInfo != None and edgeAttr != None:
            try: # GET EDGE INFO IF PRESENT
                edgeInfo = getattr(edgeInfo, edgeAttr)
            except AttributeError:
                edgeInfo = None
        if edgeInfo != None:
            if edgeIndex != None:
                edgeInfo = edgeInfo[edgeIndex]
            self.edgeInfo = edgeInfo

    def xform(self, i):
        'transform int srcPath local coord to destPath local coord'
        return int(i * self.scale)

    def xformBack(self, i):
        'transform int destPath local coord to srcPath local coord'
        return int(i / self.scale)

    def getStartStop(self, srcPath, ourPath):
        'compute srcPath start,stop in ourPath local coords'
        if srcPath.path is ourPath.path:
            return srcPath.start - ourPath.start, srcPath.stop - ourPath.start
        try:
            if srcPath.path._reverse is ourPath.path:
                return -(srcPath.start) - ourPath.start,\
                       -(srcPath.stop) - ourPath.start
        except AttributeError:
            pass
        raise ValueError('sequence mismatch: argument not from this seq')

    def __call__(self, srcPath):
        """Apply this transformation to an interval
           NB: it is not restricted to the domain of this transform,
           and thus can extend BEYOND the boundaries of this transform.
           If you want it clipped use [] interface instead of ()."""
        start, stop = self.getStartStop(srcPath, self.srcPath)
        return SeqPath(self.destPath, self.xform(start), self.xform(stop),
                       relativeToStart=True)

    def reverse(self, destPath):
        "reverse transform an interval"
        start, stop = self.getStartStop(destPath, self.destPath)
        return SeqPath(self.srcPath, self.xformBack(start),
                       self.xformBack(stop), relativeToStart=True)

    def __getitem__(self, srcPath): # PROVIDE DICT-LIKE INTERFACE
        """intersect srcPath with domain of this transform, then return
        transform to target domain coordinates"""
        return self(srcPath * self.srcPath)

    def __iter__(self):
        yield self.srcPath

    def items(self):
        yield self.srcPath, self.destPath

    def __getattr__(self, attr):
        "provide transparent wrapper for edgeInfo attributes"
        try:
            return getattr(self.__dict__['edgeInfo'], attr)
        except (KeyError, AttributeError): # RAISE EXCEPTION IF NOT FOUND!
            raise AttributeError('neither IntervalTransform nor edgeinfo \
                                 has attr ' + attr)

    def repr_dict(self):
        "Return compact dictionary representing this interval mapping"
        s = self.srcPath.repr_dict() # GET REPR OF BOTH INTERVALS
        d = self.destPath.repr_dict()
        out= {}
        for k, val in s.items(): # ADD PREFIX TO EACH ATTR
            out['src_' + k] = val
            out['dest_' + k] = d[k]
        try:
            e = self.edgeInfo.repr_dict() # GET EDGE INFO IF PRESENT
        except AttributeError:
            pass
        else:
            out.update(e) # SAVE EDGE INFO DATA
        return out

    def nidentity(self):
        "calculate total #identity matches between srcPath and destPath"
        nid = 0
        src = str(self.srcPath).upper()
        dest = str(self.destPath).upper()
        slen = len(src)
        i = 0
        while i < slen:
            if src[i] == dest[i]:
                nid += 1
            i += 1
        return nid

    def percent_id(self):
        "calculate fractional identity for this pairwise alignment"
        return self.nidentity / float(len(self.srcPath))


###################################################################
#
# SINGLE LETTER GRAPH INTERFACE CLASSES
# INSTANTIATED ON THE FLY TO PROVIDE LETTER GRAPH INTERFACE

class LetterEdgeDescriptor(object):
    "cached dict of sequences traversing this edge"

    def __get__(self, edge, objtype):
        try:
            return edge._seqs
        except AttributeError:
            edge._seqs = edge.origin.getEdgeSeqs(edge.target)
            return edge._seqs


class LetterEdge(object):
    "represents an edge from origin -> target. seqs returns its sequences"
    seqs = LetterEdgeDescriptor()

    def __init__(self, origin, target):
        self.origin = origin
        self.target = target

    def __iter__(self):
        'generate origin seqpos for sequences that traverse this edge'
        for seq in self.seqs:
            # Reduce 1:many schema to 1:1, discard edge information.
            yield self.origin.getSeqPos(seq)

    def iteritems(self):
        'generate origin,target seqpos for sequences that traverse this edge'
        for seq in self.seqs: # REDUCE 1:MANY SCHEMA TO 1:1, DISCARD EDGE INFO
            yield self.origin.getSeqPos(seq), self.target.getSeqPos(seq)

    def __getitem__(self, k):
        '''return origin,target seqpos for sequence k; raise KeyError if
        not in this edge'''
        try:
            k = k.path
        except AttributeError:
            raise TypeError('k not a valid sequence: it has no path attribute')
        return (self.origin.getSeqPos(k.path), self.target.getSeqPos(k.path))

    def __cmp__(self, other):
        'two edge objects match if they link identical nodes'
        try:
            if self.origin == other.origin and self.target == other.target:
                return 0 # REPORT A MATCH
        except AttributeError: # other MUST BE A DIFFERENT TYPE, SO NO MATCH
            pass
        return cmp(id(self), id(other))


def absoluteSlice(seq, start, stop):
    '''get slice of top-level sequence object, in absolute coordinates.
    This method calls getitem on the top-level sequence object
    i.e. seq.pathForward'''
    try:
        if start < 0: # REVERSE ORIENTATION
            return -(seq.pathForward[-stop:-start])
        else: # FORWARD ORIENTATION
            return seq.pathForward[start:stop]
    except AttributeError:
        if seq is None:
            return slice(start, stop)


def relativeSlice(seq, start, stop):
    '''get slice of this sequence object, in relative coordinates.
    This method calls getitem on the top-level sequence object
    i.e. seq.pathForward'''
    if start < 0: # REVERSE ORIENTATION
        return -(seq[-stop: -start])
    else: # FORWARD ORIENTATION
        return seq[start: stop]


def sumSliceIndex(i, myslice, relativeToStart):
    '''Adjust index value either relative to myslice.start (positive indexes)
    or relative to myslice.stop (negative indexes).  Handle the case where
    i is None or myslice is None appropriately.
    '''
    if myslice is None: # NO OBJECT, SO NOTHING TO DO...
        return i
    if i is None:
        i = 0
    i *= myslice.step
    if relativeToStart:
        return i + myslice.start
    else:
        return i + myslice.stop


class SeqOriDescriptor(object):
    "Get orientation of sequence interval"

    def __get__(self, seq, objtype):
        if seq.start >= 0:
            return 1 # FORWARD ORIENTATION
        else:
            return -1 # REVERSE ORIENTATION


class PathForwardDescr(object):
    'get the top-level forward sequence object'

    def __get__(self, seq, objtype):
        if seq.orientation > 0:
            return seq.path
        else:
            return seq.path._reverse


class AbsIntervalDescr(object):
    'get the top-level forward sequence object'

    def __get__(self, seq, objtype):
        if seq.orientation > 0:
            return seq.start, seq.stop
        else:
            return -(seq.stop), -(seq.start)


class SeqPath(object):
    '''Base class for specifying a path, ie. sequence interval.
    This implementation takes a sequence object as initializer
    and simply represents the interval as a slice of the sequence.'''
    orientation=SeqOriDescriptor()  # COMPUTE ORIENTATION AUTOMATICALLY
    pathForward=PathForwardDescr()  # GET THE TOP-LEVEL FORWARD SEQUENCE OBJ
    _abs_interval=AbsIntervalDescr()

    def __init__(self, path, start=0, stop=None, step=None, reversePath=False,
                 relativeToStart=False, absoluteCoords=False):
        '''Return slice of path[start:stop:step].
        NB: start>stop means reverse orientation, i.e. (-path)[-stop:-start]
        start/stop are LOCAL coordinates relative to the specified path
        By default, start/stop are interpreted in the usual Python slicing way,
        i.e. a negative start value is interpreted as len(path)-start.
        The relativeToStart option turns off this behavior, so that negative
        values are interpreted as negative coordinates in the local coordinate
        system of path.

        absoluteCoords option allows intervals to be created using
        Pygr's internal coordinate convention i.e.
        -20,-10 --> -(path.pathForward[10:20])
        '''
        if reversePath: # create top-level negative orientation path
            start = -(path.stop)
            stop = 0
            self._reverse = path
            path = None # make this a top-level path object
        if absoluteCoords: # THIS OPTION PROVIDES TRANSPARENT WAY TO CREATE
            if start >= 0:   # INTERVALS USING start,stop PAIRS THAT FOLLOW
                path = path.pathForward # OUR INTERNAL SIGN CONVENTION
            else: # i.e. start<0 MEANS REVERSE ORIENTATION!
                path = - (path.pathForward)
        else: # ADJUST start,stop ACCORDING TO path.start / path.stop
            start = sumSliceIndex(start, path, relativeToStart or start is None
                                  or start>=0)
            stop = sumSliceIndex(stop, path, relativeToStart or
                                 (stop is not None and stop>=0))
        if start is not None and stop is not None and start>stop:
            start = -start # start>stop MEANS REVERSE ORIENTATION!
            stop = -stop
            if path is not None:
                path = -path
        if path is not None: # perform bounds checking
            if start < path.path.start:
                start = path.path.start
            if stop > path.path.stop:
                stop = path.path.stop
        if start is None or stop is None or start>=stop:
            raise IndexError('cannot create empty sequence interval!')
        self.start = start
        self.stop = stop
        if step is None:
            step = 1
        if path is None:
            self.path = self
            self.step = step
        else: # STORE TOP-LEVEL SEQUENCE PATH...
            self.path = path.path
            self.step = step * path.step

    def classySlice(self, path, *l, **kwargs):
        'create a subslice using appropriate class based on container'
        try: # if db provides a class to use for slices, use it.
            klass = path.pathForward.db.itemSliceClass
        except AttributeError:
            klass = SeqPath # default: just use generic slice class
        return klass(path, *l, **kwargs) # construct the slice

    def absolute_slice(self, start, stop):
        'get slice of top-level sequence, using absolute coords'
        return self.classySlice(self, start, stop, absoluteCoords=True)

    def __getitem__(self, k):
        if isinstance(k, types.IntType):
            if k == -1: # HAVE TO HANDLE THIS CASE SPECIALLY
                k = slice(k, None, 1) # -1 IS LAST LETTER, SO [-1:None] slice
            else: # REGULAR CASE, JUST [k:k+1] slice
                k = slice(k, k + 1, 1)
        if isinstance(k, types.SliceType): # GET AN INTERVAL USING slice
            return self.classySlice(self, k.start, k.stop, k.step)
        elif isinstance(k, SeqPath): # MODEL SEQ AS GRAPH
            if k.path is not self.path:
                raise KeyError('node is not in this sequence!')
            try:
                target = self.classySlice(self.path, k.stop,
                                          k.stop + len(k) * k.step, k.step)
                return {target: LetterEdge(k, target)}
            except IndexError: # OUT OF BOUNDS, SO NO NEXT NODE
                return {}
        raise KeyError('requires a slice object or integer key')

    def __len__(self):
        if self.path is self and self.orientation < 0:
            return len(self._reverse) # GET LENGTH FROM FORWARD SEQUENCE
        # Get the number of results from iter(self).
        d = (self.stop - self.start) / self.step
        if d > 0: # IF stop - start < step, d WILL BE ZERO -- PREVENT THAT!
            return d
        else:
            # Never return 0 length... Bounds checking ensures non-empty ival.
            return 1

    ################################ LETTER GRAPH METHODS: JUST A LINEAR GRAPH
    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def iteritems(self):
        'letter graph iterator over (node1, {node2: edge}) tuples'
        src = self[0] # GET 1ST LETTER
        for i in range(1, len(self)): # ITERATE OVER ALL ADJACENT PAIRS
            target = self[i]
            yield src, {target: LetterEdge(src, target)}
            src = target
        yield src, {} # LAST LETTER HAS NO EDGES

    def getEdgeSeqs(self, other):
        'return dict of sequences that traverse edge from self -> other'
        if self.path is other.path and self.stop == other.start:
            return {self.path: self.stop - self.step}
        else:
            return {}

    def getSeqPos(self, seq):
        'get seq interval corresponding to this node in sequence graph'
        if seq.path is self.path:
            return self
        raise KeyError('seq not on this path!')

    ################################ INTERVAL COMPOSITION OPERATORS
    def __hash__(self):
        'ensure that same seq intervals match in dict'
        return id(self.path)^hash(self.start)^hash(self.stop)

    def __cmp__(self, other):
        'ensure that same seq intervals match in cmp()'
        if not isinstance(other, SeqPath):
            return -1
        if self.path is other.path:
            return cmp((self.start, self.stop), (other.start, other.stop))
        else:
            return NOT_ON_SAME_PATH
            #raise TypeError('SeqPath not comparable, not on same path: %s, %s'
            #                % (self.path, other.path))

    def __contains__(self, k):
        # PUT OTHER LOGIC HERE FOR CHECKING WHETHER INTERVAL IS CONTAINED...
        if isinstance(k, SeqPath):
            if k.path == self.path and self.start <= k.start and \
               k.stop <= self.stop:
                return True
            else:
                return False
        elif isinstance(k, types.IntType):
            return self.start <= k and k < self.stop

    def overlaps(self, p):
        "check whether two paths on same seq overlap"
        if self.path is not p.path:
            return False
        if (self.start <= p.start and p.start < self.stop) or \
               (p.start <= self.start and self.start < p.stop):
            return True
        else:
            return False

    def __mul__(self, other):
        "find intersection of two intervals"
        if isinstance(other, SeqPath):
            if self.path is not other.path:
                return None
            start=max(self.start, other.start)
            stop=min(self.stop, other.stop)
            if start < stop:
                if stop == 0:
                    # Have to handle the boundary case specially because of
                    # Python conventions.
                    stop = None
                return self.classySlice(self.path, start, stop)
            else:
                return None
        else:
            raise TypeError('SeqPath can only intersect SeqPath')

    def __div__(self, other):
        "return transform from other -> self coordinate systems"
        return IntervalTransform(other, self)

    def __neg__(self):
        "return same interval in reverse orientation"
        try:
            if self.seqtype() == PROTEIN_SEQTYPE:
                raise ValueError('protein sequence has no reverse \
                                 orientation!')
        except AttributeError:
            pass # ALLOW UNTYPED SEQ OBJECTS TO BE REV-COMPD
        if self is self.path: # TOP-LEVEL SEQUENCE OBJECT
            try:
                return self._reverse # USE EXISTING RC OBJECT FOR THIS SEQ
            except AttributeError: #  CREATE ONLY ONE RC FOR THIS SEQUENCE
                self._reverse = self.classySlice(self, reversePath=True)
                return self._reverse
        elif self.orientation > 0: # FORWARD ORI: JUST REVERSE INDICES
            return self.classySlice(self.path, self.stop, self.start,
                                    self.step) #SWAP ==> RC
        else: # REVERSE ORI: BECAUSE OF stop=0 POSSIBILITY, USE POSITIVE COORDS
            return self.classySlice(self.path._reverse, -(self.stop),
                                    -(self.start), self.step)

    def __add__(self, other):
        "return merged interval spanning both self and other intervals"
        if self.path is not other.path:
            raise ValueError('incompatible intervals cannot be merged.')
        if self.start < other.start:
            start = self.start
        else:
            start = other.start
        if self.stop > other.stop:
            stop = self.stop
        else:
            stop = other.stop
        if stop == 0:
            # Have to handle the boundary case specially because of Python
            # conventions.
            stop = None
        return self.classySlice(self.path, start, stop, self.step)

    def __iadd__(self, other):
        "return merged interval spanning both self and other intervals"
        if self.path is not other.path:
            raise ValueError('incompatible intervals cannot be merged.')
        if other.start < self.start:
            self.start = other.start
        if other.stop > self.stop:
            self.stop = other.stop
        return self # iadd MUST ALWAYS RETURN self!!

    def before(self):
        'get the sequence interval before this interval'
        return self.classySlice(self.path, None, self.start)

    def after(self):
        'get the sequence interval after this interval'
        if self.stop == 0:
            raise IndexError('cannot create empty sequence interval')
        return self.classySlice(self.path, self.stop, None)

    def is_full_length(self):
        '''test whether this constitutes the whole sequence (in either
        orientation)'''
        return self == self.path

    ############################################ STRING SEQUENCE METHODS
    _complement = {'a': 't', 'c': 'g', 'g': 'c', 't': 'a', 'u': 'a', 'n': 'n',
                   'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'U': 'A', 'N': 'N'}

    def reverse_complement(self, s):
        'get reverse complement of a string s'
        #return ''.join([self._complement.get(c, c) for c in s[::-1]])
        return ''.join([self._complement.get(s[i], s[i]) for i in
                        range(len(s) -1, -1, -1)])

    def seqtype(self):
        "Get the sequence type for this sequence"
        path = self.pathForward
        try: # TRY GETTING IT FROM TOP-LEVEL SEQUENCE OBJECT?
            return path._seqtype
        except AttributeError:
            try: # TRY TO GET IT FROM DB THIS SEQ IS ASSOCIATED WITH, IF ANY
                return path.db._seqtype
            except AttributeError:# GUESS IT FROM 1ST 40 LETTERS OF SEQUENCE
                path._seqtype = guess_seqtype(str(self[0:40]))
                return path._seqtype

    def __str__(self):
        '''string for this sequence interval; use reverse complement
        if necessary...'''
        if self.orientation > 0:
            return self.path.strslice(self.start, self.stop)
        else:
            s = self.path._reverse.strslice(-(self.stop), -(self.start))
            return self.reverse_complement(s)

    def __repr__(self):
        try: # USE id CONVENTION TO GET A NAME FOR THIS SEQUENCE
            id = self.pathForward.id
        except AttributeError: # OTHERWISE USE A DEFAULT, SHOWING THERE'S NO id
            id = '@NONAME'
        if self.orientation < 0: # INDICATE NEGATIVE ORIENTATION
            return '-%s[%d:%d]' % (id, -self.stop, -self.start)
        else:
            return '%s[%d:%d]' % (id, self.start, self.stop)

    def repr_dict(self):
        "Return compact dictionary representing this interval"
        try:
            id = self.path.id
        except AttributeError:
            id = self.id
        return {'id': id, 'start': self.start, 'end': self.stop,
                'ori': self.orientation}


class LengthDescriptor(object):
    'property that just returns length of object'

    def __get__(self, seq, klass):
        return len(seq)


# BASIC WRAPPER FOR A SEQUENCE.  LETS US ATTACH A NAME TO IT...
class SequenceBase(SeqPath):
    '''base sequence type assumes there will be a seq attribute
    providing sequence'''
    start = 0
    stop = LengthDescriptor()
    step = 1
    orientation = 1

    def __init__(self):
        self.path = self

    def update(self, seq):
        'change this sequence to the string <seq>'
        self.seq = seq

    def __len__(self):
        'default: get the whole self.seq and compute its length'
        return len(self.seq) # COMPUTE IT FROM THE SEQUENCE

    def strslice(self, start, stop):
        'default method assumes self.seq is a sliceable string'
        return self.seq[start:stop]


class Sequence(SequenceBase):
    'default sequence class initialized with a sequence string and ID'

    def __init__(self, s, id):
        SequenceBase.__init__(self)
        self.id = id
        self.seq = s


class SeqFilterDict(dict):
    '''stores a set of intervals, either on init or via self[ival]=junk;
    self[ival] returns intersection of ival and the overlapping
    interval in self if any; otherwise raise KeyError'''

    def __init__(self, l=[]):
        'accepts optional arg giving list of intervals'
        dict.__init__(self)
        for ival in l:
            self[ival] = None

    def __getitem__(self, k):
        try:
            ival = dict.__getitem__(self, k.path)
        except KeyError:
            raise KeyError('seq not in dict')
        result = k * ival # RETURN INTERSECTION OF IVALS
        if result is None:
            raise KeyError # PROPER WAY TO SIGNAL KEY MAPS TO NO VALUE
        return result

    def __setitem__(self, ival, junk):
        dict.__setitem__(self, ival.path, ival)

    def __iter__(self):
        return dict.itervalues(self)
##
##
## class S2SEEdgesDescriptor(object):
##     "list of interval matches as list of tuples (ival1, ival2, xform)"
##     def __get__(self, s2se, objtype):
##         return [(t.srcPath, t.destPath, t) for t in s2se.matches]


class Seq2SeqEdge(object):
    '''Maps two sequence regions onto each other, using a list
    of scalar transformations.  Can handle indels within the
    mapping.'''
    #edges = S2SEEdgesDescriptor()

    def __init__(self, msaSlice, targetPath, sourcePath=None,
                 matchIntervals=False):
        self.msaSlice = msaSlice
        self.targetPath = targetPath
        if sourcePath is not None:
            self.sourcePath = sourcePath
            self.matchIntervals = matchIntervals
        else: # NEED TO REVERSE-MAP targetPath TO FIND sourcePath
            # Mask to targetPath.
            si = msaSlice.groupByIntervals(filterList = [targetPath],
                                           mergeAll=True)
            l = msaSlice.groupBySequences(si)
            try:
                self.sourcePath = l[0][0]
            except IndexError:
                raise KeyError('target interval not in msaSlice!')
            self.matchIntervals = l[0][2]

    def items(self, mergeAll=False, **kwargs):
        'get list of (srcPath, destPath) 1:1 matches'
        if self.matchIntervals is None: # THIS IS ALREADY A 1:1 INTERVAL!
            return [(self.sourcePath, self.targetPath)]
        elif self.matchIntervals is False:
            raise ValueError('no matchIntervals information!')
        l = [] # USE STORED LIST OF 1:1 INTERVALS
        for srcStart, srcEnd, destStart, destEnd in self.matchIntervals:
            l.append((absoluteSlice(self.sourcePath, srcStart, srcEnd),
                      absoluteSlice(self.targetPath, destStart, destEnd)))
        return l

    def get_gaps(self):
        'return list of (srcIval,destIval) representing gaps / insertions'
        if self.matchIntervals is False:
            raise ValueError('no matchIntervals information!')
        elif self.matchIntervals is None or len(self.matchIntervals) < 2:
            return [] # no gaps here...
        srcLast = self.matchIntervals[0][1] # ends of 1st aligned intervals
        destLast = self.matchIntervals[0][3]
        l = []
        for t in self.matchIntervals[1:]:
            if t[0] > srcLast: # gap region
                srcIval = absoluteSlice(self.sourcePath, srcLast, t[0])
            else:
                srcIval = None
            if t[2] > destLast: # insertion region
                destIval = absoluteSlice(self.targetPath, destLast, t[2])
            else:
                destIval = None
            if srcIval is not None or destIval is not None:
                l.append((srcIval, destIval))
            srcLast = t[1] # ends of these aligned intervals
            destLast = t[3]
        return l

    def __iter__(self, sourceOnly=True, **kwargs):
        return iter([t[0] for t in self.items(sourceOnly=sourceOnly,
                                              **kwargs)])

    def length(self, mode=max):
        'get length of source vs. target interval according to mode'
        return mode(len(self.sourcePath), len(self.targetPath))

    def pIdentity(self, mode=max, trapOverflow=True):
        "calculate fractional identity for this pairwise alignment"
        nid = 0
        start1 = self.sourcePath.start
        s1 = str(self.sourcePath).upper()
        start2 = self.targetPath.start
        s2 = str(self.targetPath).upper()
        for srcPath, destPath in self.items():
            isrc = srcPath.start - start1
            idest = destPath.start - start2
            for i in xrange(len(srcPath)):
                if s1[isrc + i] == s2[idest + i]:
                    nid += 1
        x = nid / float(self.length(mode))
        if trapOverflow and x > 1.:
            raise ValueError('''pIdentity overflow due to multiple hits
                             (see docs)? To avoid this error message,
                             use trapOverflow=False option.''')
        return x

    def longestSegment(self, segment, pIdentityMin=.9, minAlignSize=1,
                       mode=max, **kwargs):
        besthit = None
        for i in xrange(len(segment)):
            ni = 0 # IDENTITY COUNT
            nm = 0 # MISMATCH COUNT
            for j in xrange(i, -1, -1):
                ni += segment[j][2]
                l = mode(segment[i][0] + segment[i][2] - segment[j][0],
                       segment[i][1] + segment[i][2] - segment[j][1])
                pIdentity = float(ni) / l
                if pIdentity >= pIdentityMin and (besthit is None or
                                                  ni + nm > besthit[4]):
                    besthit = (segment[j][0], segment[i][0] + segment[i][2],
                               segment[j][1], segment[i][1] + segment[i][2],
                               ni + nm)
                nm += segment[j][3]
        if besthit is None:
            return None
        elif besthit[4] >= minAlignSize:
            return besthit[:4]
        else:
            return None

    def conservedSegment(self, **kwargs):
        "calculate fractional identity for this pairwise alignment"
        start1 = self.sourcePath.start
        s1 = str(self.sourcePath).upper()
        start2 = self.targetPath.start
        s2 = str(self.targetPath).upper()
        i1 = None
        segment = []
        n = 0
        # Find unbroken identity segments.
        for srcPath, destPath in self.items():
            isrc = srcPath.start - start1
            idest = destPath.start - start2
            for i in xrange(len(srcPath)):
                if s1[isrc + i] == s2[idest + i]: # EXACT MATCH
                    if i1 is None: # START NEW IDENTITY-SEGMENT
                        seg1, i1 = isrc + i, isrc + i
                        seg2, i2 = idest + i, idest + i
                    elif i1 + 1 != isrc + i or i2 + 1 != idest + i:
                        # Not contiguous, break.
                        segment.append((seg1 + start1, seg2 + start2,
                                        i1 + 1 - seg1, n))
                        n = 0 # RESET MISMATCH COUNT
                        seg1, i1 = isrc + i, isrc + i
                        seg2, i2 = idest + i, idest + i
                    else:
                        i1 = isrc + i
                        i2 = idest + i
                else: # MISMATCH
                    if i1 is not None: # BREAK PREVIOUS SEGMENT
                        segment.append((seg1 + start1, seg2 + start2,
                                        i1 + 1 - seg1, n))
                        i1 = None
                        n = 0 # RESET MISMATCH COUNT
                    n += 1 # COUNT MISMATCH
        if i1 is not None:
            segment.append((seg1 + start1, seg2 + start2, i1 + 1 - seg1, n))
        return self.longestSegment(segment, **kwargs)

    def pAligned(self, mode=max, trapOverflow=True):
        'get fraction of aligned letters for this pairwise alignment'
        nid = 0
        for srcPath, destPath in self.items():
            nid += len(destPath)
        x = nid / float(self.length(mode))
        if trapOverflow and x > 1.:
            raise ValueError('''pAligned overflow due to multiple hits
                             (see docs)? To avoid this error message,
                             use trapOverflow=False option.''')
        return x


class SeqDBDescriptor(object):
    'forwards attribute requests to self.pathForward'

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        # Raises an AttributeError if None.
        return getattr(obj.pathForward, self.attr)


class SeqDBSlice(SeqPath):
    'JUST A WRAPPER FOR SCHEMA TO HANG SHADOW ATTRIBUTES ON...'
    id = SeqDBDescriptor('id')
    db = SeqDBDescriptor('db')



# CURRENTLY UNUSED

## class PathEdgeDict(dict):
##
##     def __init__(self, p):
##         self.path = p.path
##         self.pos = p.end - 1
##         if p.end < len(p.path):
##             dict.__setitem__(self, p.path[p.end], 1)
##         if hasattr(p.path, '_next') and self.pos in p.path._next:
##             dict.update(self, p.path._next[self.pos])
##
##     def __setitem__(self, k, val):
##         print 'entered PathEdgeDict.setitem'
##         if not hasattr(self.path, '_next'):
##             self.path._next = {}
##         if self.pos not in self.path._next:
##             self.path._next[self.pos] = {}
##         self.path._next[self.pos][k] = val
##         dict.__setitem__(self, k, val)


## class PathNextDescr(object):
##
##     def __init__(self, attrName='next'):
##         self.attrName = attrName
##
##     def __get__(self, obj, objtype):
##         return PathEdgeDict(obj)
##
##     def __set__(self, obj, val):
##         raise AttributeError(self.attrName + ' is read-only!')


## class LengthDescriptor(object):
##
##     def __init__(self, attr):
##         self.attr = attr
##
##     def __get__(self, obj, objtype):
##         return len(getattr(obj, self.attr))
##
##     def __set__(self, obj, val):
##         raise AttributeError(self.attr + ' is read-only!')


## def firstItem(aList):
##     if hasattr(aList, '__iter__'):
##         for i in aList:
##             return i
##     else:
##         return aList
