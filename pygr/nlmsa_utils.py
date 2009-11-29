import os
import types
import classutil
import logger
from UserDict import DictMixin


class NLMSASeqList(list):

    def __init__(self, nlmsaSeqDict):
        list.__init__(self)
        self.nlmsaSeqDict = nlmsaSeqDict

    def __getitem__(self, nlmsaID):
        'return NLMSASequence for a given nlmsa_id'
        try:
            return list.__getitem__(self, nlmsaID)
        except IndexError:
            seqID, nsID = self.nlmsaSeqDict.IDdict[str(nlmsaID)]
            return list.__getitem__(self, nsID)

    def getSeq(self, nlmsaID):
        'return seq for a given nlmsa_id'
        seqID, nsID = self.nlmsaSeqDict.IDdict[str(nlmsaID)]
        return self.nlmsaSeqDict.nlmsa.seqDict[seqID]

    def getSeqID(self, nlmsaID):
        'return seqID for a given nlmsa_id'
        seqID, nsID = self.nlmsaSeqDict.IDdict[str(nlmsaID)]
        return seqID

    def is_lpo(self, id):
        if id >= len(self):
            return False
        ns = self[id]
        if ns.is_lpo:
            return True
        else:
            return False

    def nextID(self):
        return len(self)


class EmptySliceError(KeyError):
    pass


class EmptyAlignmentError(ValueError):
    pass


class EmptySlice:
    'Empty slice for use by NLMSASlice'

    def __init__(self, seq):
        self.seq = seq

    def edges(self, *args, **kwargs):
        return []

    def items(self, **kwargs):
        return []

    def iteritems(self, **kwargs):
        return iter([])

    def keys(self, **kwargs):
        return []

    def __iter__(self):
        return iter([])

    def __getitem__(self, k):
        raise KeyError

    def __len__(self):
        return 0

    def matchIntervals(self, seq=None):
        return []

    def findSeqEnds(self, seq):
        raise KeyError('seq not aligned in this interval')

    def generateSeqEnds(self):
        return []

    def groupByIntervals(self, **kwargs):
        return {}

    def groupBySequences(self, **kwargs):
        return []

    def split(self, **kwargs):
        return []

    def regions(self, **kwargs):
        return []

    def __cmp__(self, other):
        return cmp(self.seq, other.seq)

    def rawIvals(self):
        return []


class _NLMSASeqDict_ValueWrapper(object):
    """A wrapper class for NLMSASeqDict to use to store 3-tuples in its cache.

    NLMSASeqDict has a most-recent-values cache containing (id,
    seqlist, offset) tuples for each referenced pathForward.  However,
    tuples cannot be stored in a weakref dictionary.  This class provides
    a tuple-like wrapper object that *can* be stored in a weakref dict.
    
    """
    def __init__(self, nlmsaID, seqlist, offset):
        self.v = (nlmsaID, seqlist, offset)

    def __hash__(self):
        return hash(self.v)

    def __len__(self):
        return 3

    def __getitem__(self, n):
        return self.v[n]

_DEFAULT_SEQUENCE_CACHE_SIZE=100
class NLMSASeqDict(object, DictMixin):
    """Index sequences by pathForward, and use list to keep reverse mapping.

    Keeps a cache of n most recently accessed sequences, up to
    maxSequenceCacheSize (defaults to 100).
    
    """

    def __init__(self, nlmsa, filename, mode, idDictClass=None,
                 maxSequenceCacheSize=_DEFAULT_SEQUENCE_CACHE_SIZE):
        self._cache = classutil.RecentValueDictionary(maxSequenceCacheSize)
        self.seqlist = NLMSASeqList(self)
        self.nlmsa = nlmsa
        self.filename = filename
        if mode == 'memory': # just use python dictionary
            idDictClass = dict
        elif mode == 'w': # new database
            mode = 'n'
        if idDictClass is None: # use persistent id dictionary storage
            self.seqIDdict = classutil.open_shelve(filename + '.seqIDdict',
                                                   mode)
            self.IDdict = classutil.open_shelve(filename + '.idDict', mode)
        else: # user supplied class for id dictionary storage
            self.seqIDdict = idDictClass()
            self.IDdict = idDictClass()

    def saveSeq(self, seq, nsID= -1, offset=0, nlmsaID=None):
        'save mapping of seq to specified (nlmsaID,ns,offset)'
        if nsID < 0: # let the union figure it out
            self.nlmsa.currentUnion.__iadd__(seq)
            return # the union added it for us, no need to do anything
        if isinstance(seq, types.StringType):
            id = seq # treat this as fully qualified identifier
        else: # get the identfier from the seq / database
            id = self.getSeqID(seq)
        if nlmsaID is None: # allocate a new unique id
            nlmsaID = self.nlmsa.nextID()
        self.seqIDdict[id] = nlmsaID, nsID, offset
        self.IDdict[str(nlmsaID)] = id, nsID

    def getIDcoords(self, seq):
        'return nlmsaID,start,stop for a given seq ival.'
        nlmsaID = self.getID(seq)
        return nlmsaID, seq.start, seq.stop # standard coords

    def getID(self, seq):
        'return nlmsa_id for a given seq'
        return self[seq][0]

    def __getitem__(self, seq):
        'return nlmsaID,NLMSASequence,offset for a given seq'
        if not hasattr(seq, 'annotationType'): # don't cache annotations
            try: # look in our sequence cache
                return self._cache[seq.pathForward]
            except AttributeError:
                raise KeyError('key must be a sequence interval!')
            except KeyError:
                pass
        seqID = self.getSeqID(seq) # use seq id to look up...
        try:
            nlmsaID, nsID, offset = self.seqIDdict[seqID]
        except KeyError:
            raise KeyError('seq not found in this alignment')
        v = nlmsaID, self.seqlist[nsID], offset
        if not hasattr(seq, 'annotationType'): # don't cache annotations
            self._cache[seq.pathForward] = _NLMSASeqDict_ValueWrapper(*v)
        return v

    def __iter__(self):
        'iterate over sequences in this alignment'
        for seqID in self.seqIDdict:
            yield self.nlmsa.seqDict[seqID]

    def getSeqID(self, seq):
        'return fully qualified sequence ID for this seq'
        return (~(self.nlmsa.seqDict))[seq]

    def __setitem__(self, k, ns):
        'save mapping of seq to the specified NLMSASequence'
        self.seqlist.append(ns)
        if isinstance(k, types.StringType):
            # Allow build with a string object.
            self._cache[k] = (ns.id, ns, 0)
        elif k is not None:
            self._cache[k.pathForward] = (ns.id, ns, 0)

    def __iadd__(self, ns):
        'add coord system ns to the alignment'
        self[None] = ns
        return self # iadd must return self!!!

    def close(self):
        'finalize and close shelve indexes'
        try:
            do_close = self.seqIDdict.close
        except AttributeError:
            return # our storage doesn't support close(), so nothing to do
        do_close() # close both shelve objects
        self.IDdict.close()

    def reopenReadOnly(self, mode='r'):
        'save existing data and reopen in read-only mode'
        self.close()
        self.seqIDdict = classutil.open_shelve(self.filename + '.seqIDdict',
                                               mode)
        self.IDdict = classutil.open_shelve(self.filename + '.idDict', mode)

    def getUnionSlice(self, seq):
        'get union coords for this seq interval, adding seq to index if needed'
        try:
            id, ns, offset = self[seq] # look up in index
        except KeyError:
            self.saveSeq(seq) # add this new sequence to our current union
            id, ns, offset = self[seq] # look up in index
        # Make sure to handle annotations right
        i, start, stop = self.getIDcoords(seq)
        if start < 0: # reverse orientation
            return ns, slice(start - offset, stop - offset) # use union coords
        else: # forward orientation
            return ns, slice(start + offset, stop + offset) # use union coords

    def clear_cache(self):
        'Clear the cache of saved sequences.'
        self._cache.clear()


def splitLPOintervals(lpoList, ival, targetIval=None):
    'return list of intervals split to different LPOs'
    if ival.start < 0: # reverse orientation: force into forward ori
        start= -(ival.stop)
        stop= -(ival.start)
    else: # forward orientation
        start=ival.start
        stop=ival.stop
    l = []
    i = len(lpoList) - 1
    while i >= 0:
        offset = lpoList[i].offset
        if offset < stop: # appears to be in this
            if offset <= start: # fits completely in this LPO
                if ival.start < 0: # reverse ori
                    myslice = slice(offset - stop, offset - start)
                else: # forward ori
                    myslice = slice(start - offset, stop - offset)
                if targetIval is not None:
                    l.append((lpoList[i], myslice, targetIval))
                else:
                    l.append((lpoList[i], myslice))
                return l # done
            else: # continues past start of this LPO
                if ival.start < 0: # reverse ori
                    myslice = slice(offset - stop, 0)
                else: # forward ori
                    myslice = slice(0, stop - offset)
                if targetIval is not None:
                    l.append((lpoList[i], myslice, targetIval[offset
                                                              - start:]))
                    # Remove the already-appended part
                    targetIval = targetIval[:offset - start]
                else:
                    l.append((lpoList[i], myslice))
                stop = offset
        i -= 1 # continue to previous LPO
    raise ValueError('empty lpoList or offset not starting at 0?  Debug!')


class BuildMSASlice(object):

    def __init__(self, ns, start, stop, id, offset, is_lpo=0, seq=None):
        self.ns = ns
        self.start = start
        self.stop = stop
        self.id = id
        self.offset = offset
        self.is_lpo = is_lpo
        self.seq = seq

    def offsetSlice(self, ival):
        if ival.orientation < 0:
            return slice(ival.start - self.offset, ival.stop - self.offset)
        else:
            return slice(ival.start + self.offset, ival.stop + self.offset)

    def __iadd__(self, targetIval):
        'save an alignment edge between self and targetIval'
        if self.is_lpo: # assign to correct LPO(s)
            if isinstance(targetIval, types.SliceType):
                raise ValueError('you attempted to map LPO --> LPO?!?')
            self.ns.nlmsaLetters.__iadd__(targetIval)
            splitList = splitLPOintervals(self.ns.nlmsaLetters.lpoList,
                                          slice(self.start, self.stop),
                                          targetIval)
            for ns, src, target in splitList:
                # Save intervals to respective LPOs; LPO --> target
                ns[src] = self.ns.nlmsaLetters.seqs.getIDcoords(target)
                if self.ns.nlmsaLetters.is_bidirectional:
                    nsu, myslice = self.ns.nlmsaLetters.seqs \
                            .getUnionSlice(target)
                    # Save target --> LPO
                    nsu[myslice] = (ns.id, src.start, src.stop)
        else:
            if isinstance(targetIval, types.SliceType): # target is LPO
                splitList = splitLPOintervals(self.ns.nlmsaLetters.lpoList,
                                            targetIval, self.seq)
                for ns, target, src in splitList:
                    self.ns[self.offsetSlice(src)] = (ns.id, target.start,
                                                      target.stop)
                    if self.ns.nlmsaLetters.is_bidirectional:
                        # Save LPO --> SRC
                        ns[target]=(self.id, src.start, src.stop)
            else: # both src and target are normal seqs.  use_virtual_lpo!!
                self.ns.nlmsaLetters.__iadd__(targetIval)
                self.ns.nlmsaLetters.init_pairwise_mode()
                # Our virtual LPO
                ns_lpo = self.ns.nlmsaLetters.seqlist[self.ns.id - 1]
                # Save src --> target
                ns_lpo[self.offsetSlice(self.seq)] = self.ns.nlmsaLetters \
                        .seqs.getIDcoords(targetIval)
                if self.ns.nlmsaLetters.is_bidirectional:
                    nsu, myslice = self.ns.nlmsaLetters.seqs \
                            .getUnionSlice(targetIval)
                    # Our virtual LPO
                    ns_lpo = self.ns.nlmsaLetters.seqlist[nsu.id - 1]
                    # Save target --> src
                    ns_lpo[myslice] = (self.id, self.start, self.stop)
        return self # iadd must always return self

    def __setitem__(self, k, v):
        if v is not None:
            raise ValueError('NLMSA cannot save edge-info. Only \
                             nlmsa[s1][s2]=None allowed')
        self += k


def read_seq_dict(pathstem, trypath=None):
    'read seqDict for NLMSA'
    if os.access(pathstem + '.seqDictP', os.R_OK):
        from pygr import worldbase
        ifile = file(pathstem+'.seqDictP', 'rb') # pickle is binary file!
        try: # load from worldbase-aware pickle file
            seqDict = worldbase._mdb.loads(ifile.read())
        finally:
            ifile.close()
    elif os.access(pathstem + '.seqDict', os.R_OK): # old-style union header
        import seqdb
        seqDict = seqdb.PrefixUnionDict(filename=pathstem+'.seqDict',
                                        trypath=trypath)
    else:
        raise ValueError('''Unable to find seqDict file
%s.seqDictP or %s.seqDict
and no seqDict provided as an argument''' % (pathstem, pathstem))
    return seqDict


def save_seq_dict(pathstem, seqDict):
    'save seqDict to a worldbase-aware pickle file'
    from metabase import dumps
    ofile = file(pathstem + '.seqDictP', 'wb') # pickle is binary file!
    try:
        ofile.write(dumps(seqDict))
    finally:
        ofile.close()


def prune_self_mappings(src_prefix, dest_prefix, is_bidirectional):
    '''return is_bidirectional flag according to whether source and
    target are the same genome.  This handles axtNet reading, in which
    mappings between genomes are given in only one direction, whereas
    mappings between the same genome are given in both directions.'''
    if src_prefix == dest_prefix:
        return 0
    else:
        return 1


def nlmsa_textdump_unpickler(filepath, kwargs):
    from cnestedlist import textfile_to_binaries, NLMSA
    logger.info('Saving NLMSA indexes from textdump: %s' % filepath)
    try:
        buildpath = os.environ['WORLDBASEBUILDDIR']
    except KeyError:
        buildpath = classutil.get_env_or_cwd('PYGRDATABUILDDIR')
    path = textfile_to_binaries(filepath, buildpath=buildpath, **kwargs)
    o = NLMSA(path) # now open in read mode from the saved index fileset
    o._saveLocalBuild = True # mark this for saving in local metabase
    return o


nlmsa_textdump_unpickler.__safe_for_unpickling__ = 1


class NLMSABuilder(object):
    'when unpickled triggers construction of NLMSA from textdump'
    _worldbase_no_cache = True # force worldbase to reload this fresh

    def __init__(self, filepath, **kwargs):
        self.filepath = filepath
        self.kwargs = kwargs

    def __reduce__(self):
        return (nlmsa_textdump_unpickler, (self.filepath, self.kwargs))


class SeqCacheOwner(object):
    'weak referenceable object: workaround for pyrex extension classes'

    def __init__(self):
        self.cachedSeqs = {}

    def cache_reference(self, seq):
        'keep a ref to seqs cached on our behalf'
        self.cachedSeqs[seq.id] = seq


def generate_nlmsa_edges(self, *args, **kwargs):
    """iterate over all edges for all sequences in the alignment.
    Very slow for a big alignment!"""
    for seq in self.seqs:
        myslice = self[seq]
        for results in myslice.edges(*args, **kwargs):
            yield results


def get_interval(seq, start, end, ori):
    "trivial function to get the interval seq[start:end] with requested ori"
    if ori < 0:
        return seq.absolute_slice(-end, -start)
    else:
        return seq.absolute_slice(start, end)


_default_ivals_attrs = dict(idDest='id', startDest='start',
                            stopDest='stop', oriDest='ori')


class CoordsToIntervals(object):
    '''Transforms coord objects to (ival1,ival2) aligned interval pairs.

    The intervals can come in in two forms:
    First, as a list, with [src, dest1, dest2, dest3] information;
    or second, as an object, with attributes specifying src/dest info.
    '''

    def __init__(self, srcDB, destDB=None,
                 alignedIvalsAttrs=_default_ivals_attrs):
        self.srcDB = srcDB
        if destDB:
            self.destDB = destDB
        else:
            self.destDB = srcDB
        self.getAttr = classutil.make_attribute_interface(alignedIvalsAttrs)

    def __call__(self, alignedCoords):
        '''Read interval info from alignedCoords and generate actual intervals.

        Information read is id, start, stop, and orientation (ori).
        '''
        for c in alignedCoords:
            if isinstance(c, (CoordsGroupStart, CoordsGroupEnd)):
                yield c # just pass grouping-info through
                continue

            try:
                srcData = c[0] # align everything to the first interval
                destSet = c[1:]
            except TypeError:
                srcData = c # extract both src and dest from ivals object
                destSet = [c]

            id = self.getAttr(srcData, 'id')
            start = self.getAttr(srcData, 'start')
            stop = self.getAttr(srcData, 'stop')
            ori = self.getAttr(srcData, 'ori', 1)    # default orientation: +

            srcIval = get_interval(self.srcDB[id], start, stop, ori)

            # get the dest interval(s) and yield w/src.
            for destData in destSet:
                idDest = self.getAttr(destData, 'idDest')
                startDest = self.getAttr(destData, 'startDest')
                stopDest = self.getAttr(destData, 'stopDest')
                oriDest = self.getAttr(destData, 'oriDest', 1) # default ori: +

                destIval = get_interval(self.destDB[idDest], startDest,
                                        stopDest, oriDest)

                yield srcIval, destIval # generate aligned intervals


def add_aligned_intervals(al, alignedIvals):
    '''Save a set of aligned intervals to alignment.
    '''
    # for each pair of aligned intervals, save them into the alignment.
    for t in alignedIvals:
        # is 't' a marker object for start or end of a group of coordinates?
        if isinstance(t, (CoordsGroupStart, CoordsGroupEnd)):
            continue # ignore grouping markers

        (src, dest) = t
        al += src
        al[src][dest] = None                # save their alignment


class CoordsGroupStart(object):
    '''Marker object indicating start of a coordinates group.

    See BlastHitParser for an example.'''
    pass


class CoordsGroupEnd(object):
    '''Marker object indicating end of a group of coordinates.

    See BlastHitParser for an example.'''
    pass
