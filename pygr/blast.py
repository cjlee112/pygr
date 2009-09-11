import glob
import os
import tempfile
import classutil
import logger
from sequtil import *
from parse_blast import BlastHitParser
from seqdb import write_fasta, read_fasta
from nlmsa_utils import CoordsGroupStart, CoordsGroupEnd, CoordsToIntervals,\
     EmptySlice
from annotation import AnnotationDB, TranslationAnnot, TranslationAnnotSlice
import cnestedlist
import translationDB
import UserDict

# NCBI HAS THE NASTY HABIT OF TREATING THE IDENTIFIER AS A BLOB INTO
# WHICH THEY STUFF FIELD AFTER FIELD... E.G. gi|1234567|foobarU|NT_1234567|...
# THIS JUST YANKS OUT THE SECOND ARGUMENT SEPARATED BY |
NCBI_ID_PARSER=lambda id: id.split('|')[1]


def blast_program(query_type, db_type):
    progs = {DNA_SEQTYPE: {DNA_SEQTYPE: 'blastn', PROTEIN_SEQTYPE: 'blastx'},
            PROTEIN_SEQTYPE: {DNA_SEQTYPE: 'tblastn',
                              PROTEIN_SEQTYPE: 'blastp'}}
    if query_type == RNA_SEQTYPE:
        query_type = DNA_SEQTYPE
    if db_type == RNA_SEQTYPE:
        db_type = DNA_SEQTYPE
    return progs[query_type][db_type]


def read_blast_alignment(ofile, srcDB, destDB, al=None, pipeline=None,
                         translateSrc=False, translateDest=False):
    """Apply sequence of transforms to read input from 'ofile'.

    srcDB: database for finding query sequences from the blast input;

    destDB: database for finding subject sequences from the blast input;

    al, if not None, must be a writeable alignment object in which to
    store the alignment intervals;

    translateSrc=True forces creation of a TranslationDB representing
    the possible 6-frames of srcDB (for blastx, tblastx);

    translateDest=True forces creation of a TranslationDB representing
    the possible 6-frames of destDB (for tblastn, tblastx).

    If pipeline is not None, it must be a list of filter functions each
    taking a single argument and returning an iterator or iterable result
    object.
    """
    p = BlastHitParser()
    d = dict(id='src_id', start='src_start', stop='src_end', ori='src_ori',
             idDest='dest_id', startDest='dest_start',
             stopDest='dest_end', oriDest='dest_ori')
    if translateSrc:
        srcDB = translationDB.get_translation_db(srcDB)
    if translateDest:
        destDB = translationDB.get_translation_db(destDB)
    cti = CoordsToIntervals(srcDB, destDB, d)
    alignedIvals = cti(p.parse_file(ofile))
    if pipeline is None:
        result = save_interval_alignment(alignedIvals, al)
    else: # apply all the filters in our pipeline one by one
        result = alignedIvals
        for f in pipeline:
            result = f(result)
    return result


def save_interval_alignment(alignedIvals, al=None):
    """Save alignedIvals to al, or a new in-memory NLMSA"""
    needToBuild = False
    if al is None:
        al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True,
                               bidirectional=False)
        needToBuild = True
    al.add_aligned_intervals(alignedIvals)
    if needToBuild:
        al.build()
    return al


def start_blast(cmd, seq, seqString=None, seqDict=None, **kwargs):
    """Run blast and return results."""
    p = classutil.FilePopen(cmd, stdin=classutil.PIPE, stdout=classutil.PIPE,
                            **kwargs)
    if seqString is None:
        seqString = seq
    if seqDict is not None: # write all seqs to nonblocking ifile
        for seqID, seq in seqDict.iteritems():
            write_fasta(p.stdin, seq)
        seqID = None
    else: # just write one query sequence
        seqID = write_fasta(p.stdin, seqString)
    if p.wait(): # blast returned error code
        raise OSError('command %s failed' % ' '.join(cmd))
    return seqID, p


def process_blast(cmd, seq, blastDB, al=None, seqString=None, queryDB=None,
                  popenArgs={}, **kwargs):
    """Run blast and return an alignment."""
    seqID, p = start_blast(cmd, seq, seqString, seqDict=queryDB, **popenArgs)
    try:
        if not queryDB: # need a query db for translation / parsing results
            try:
                queryDB = seq.db # use this sequence's database
            except AttributeError:
                queryDB = {seqID: seq} # construct a trivial "database"

        al = read_blast_alignment(p.stdout, queryDB, blastDB, al, **kwargs)
    finally:
        p.close() # close our PIPE files
    return al


def repeat_mask(seq, progname='RepeatMasker', opts=()):
    'Run RepeatMasker on a sequence, return lowercase-masked string'
    ## fd, temppath = tempfile.mkstemp()
    ## ofile = os.fdopen(fd, 'w') # text file
    p = classutil.FilePopen([progname] + list(opts), stdin=classutil.PIPE,
                            stdinFlag=None)
    write_fasta(p.stdin, seq, reformatter=lambda x: x.upper()) # save uppercase
    try:
        if p.wait():
            raise OSError('command %s failed' % ' '.join(p.args[0]))
        ifile = file(p._stdin_path + '.masked', 'rU') # text file
        try:
            for id, title, seq_masked in read_fasta(ifile):
                break # JUST READ ONE SEQUENCE
        finally:
            ifile.close()
    finally: # clean up our temp files no matter what happened
        p.close() # close temp stdin file
        for fpath in glob.glob(p._stdin_path + '.*'):
            try:
                os.remove(fpath)
            except OSError:
                pass
    return seq_masked # ONLY THE REPEATS ARE IN LOWERCASE NOW


def warn_if_whitespace(filepath):
    l = filepath.split() # check filepath for whitespace
    if len(l) > 1 or len(l[0]) < len(filepath): # contains whitespace
        logger.warn("""
Your sequence filepath contains whitespace characters:
%s
The NCBI formatdb (and blastall) programs cannot handle file paths
containing whitespace! This is a known NCBI formatdb / blastall bug.
Please use a path containing no whitespace characters!""" % filepath)
        return True # signal caller that a warning was issued


class BlastMapping(object):
    'Graph interface for mapping a sequence to homologs in a seq db via BLAST'

    def __init__(self, seqDB, filepath=None, blastReady=False,
                 blastIndexPath=None, blastIndexDirs=None, verbose=True,
                 showFormatdbMessages=True, **kwargs):
        '''seqDB: sequence database object to search for homologs
        filepath: location of FASTA format file for the sequence database
        blastReady: if True, ensure that BLAST index file ready to use
        blastIndexPath: location of the BLAST index file
        blastIndexDirs: list of directories for trying to build index in
        '''
        self.seqDB = seqDB
        self.idIndex = BlastIDIndex(seqDB)
        self.verbose = verbose
        self.showFormatdbMessages = showFormatdbMessages
        if filepath is not None:
            self.filepath = filepath
        else:
            self.filepath = seqDB.filepath
        if blastIndexPath is not None:
            self.blastIndexPath = blastIndexPath
        if blastIndexDirs is not None:
            self.blastIndexDirs = blastIndexDirs
        self.checkdb() # CHECK WHETHER BLAST INDEX FILE IS PRESENT...
        if not self.blastReady and blastReady: # FORCE CONSTRUCTION OF BLAST DB
            self.formatdb()

    def __repr__(self):
        return "<BlastMapping '%s'>" % (self.filepath)

    def __getitem__(self, k):
        'return NLMSASlice representing BLAST results'
        al = self.__call__(k) # run BLAST & get NLMSA storing results
        return al[k] # return NLMSASlice representing these results

    def test_db_location(self, testpath):
        '''check whether BLAST index files ready for use; return status.'''
        if not os.access(testpath+'.nsd', os.R_OK) \
               and not os.access(testpath+'.psd', os.R_OK) \
               and not os.access(testpath+'.00.nsd', os.R_OK) \
               and not os.access(testpath+'.00.psd', os.R_OK):
            return False
        else: # FOUND INDEX FILES IN THIS LOCATION
            if testpath != self.filepath:
                self.blastIndexPath = testpath
            return True

    def checkdb(self):
        'look for blast index files in blastIndexPath, \
        standard list of locations'
        for testpath in self.blast_index_paths():
            self.blastReady = self.test_db_location(testpath)
            if self.blastReady:
                break
        return self.blastReady

    def run_formatdb(self, testpath):
        'ATTEMPT TO BUILD BLAST DATABASE INDEXES at testpath'
        dirname = classutil.file_dirpath(testpath)
        if not os.access(dirname, os.W_OK): # check if directory is writable
            raise IOError('run_formatdb: directory %s is not writable!'
                          % dirname)
        cmd = ['formatdb', '-i', self.filepath, '-n', testpath, '-o', 'T']
        if self.seqDB._seqtype != PROTEIN_SEQTYPE:
            cmd += ['-p', 'F'] # special flag required for nucleotide seqs
        logger.info('Building index: ' + ' '.join(cmd))
        if self.showFormatdbMessages:
            kwargs = {}
        else: # suppress formatdb messages by redirecting them
            kwargs = dict(stdout=classutil.PIPE, stderr=classutil.PIPE)
        if classutil.call_subprocess(cmd, **kwargs):
            # bad exit code, so command failed
            warn_if_whitespace(self.filepath) \
                 or warn_if_whitespace(testpath) # only issue one warning
            raise OSError('command %s failed' % ' '.join(cmd))
        self.blastReady=True
        if testpath!=self.filepath:
            self.blastIndexPath = testpath

    def get_blast_index_path(self):
        'get path to base name for BLAST index files'
        try:
            return self.blastIndexPath
        except AttributeError:
            return self.filepath
    # DEFAULT: BUILD INDEX FILES IN self.filepath . HOME OR APPROPRIATE
    # USER-/SYSTEM-SPECIFIC TEMPORARY DIRECTORY
    blastIndexDirs = ['FILEPATH', os.getcwd, os.path.expanduser,
                      tempfile.gettempdir()]

    def blast_index_paths(self):
        'iterate over possible blast index directories'
        try: # 1ST TRY ACTUAL SAVED LOCATION IF ANY
            yield self.blastIndexPath
        except AttributeError:
            pass
        for m in self.blastIndexDirs: # NOW TRY STANDARD LOCATIONS
            if m=='FILEPATH':
                yield self.filepath
                continue
            elif m == os.path.expanduser:
                s = m('~') # GET HOME DIRECTORY
            elif callable(m):
                s = m()
            else: # TREAT AS STRING
                s = str(m)
            yield os.path.join(s, os.path.basename(self.filepath))

    def formatdb(self, filepath=None):
        'try to build BLAST index files in an appropriate location'
        if filepath is not None: # JUST USE THE SPECIFIED PATH
            return self.run_formatdb(filepath)
        notFirst = False
        for testpath in self.blast_index_paths():
            if notFirst:
                logger.info('Trying next entry in self.blastIndexDirs...')
            notFirst = True
            try: # BUILD IN TARGET DIRECTORY
                return self.run_formatdb(testpath)
            except (IOError, OSError): # BUILD FAILED
                pass
        raise IOError("cannot build BLAST database for %s" % (self.filepath, ))

    def raw_fasta_stream(self, ifile=None, idFilter=None):
        '''Return a stream of fasta-formatted sequences.

        Optionally, apply an ID filter function if supplied.
        '''
        if ifile is not None: # JUST USE THE STREAM WE ALREADY HAVE OPEN
            return ifile, idFilter
        try: # DEFAULT: JUST READ THE FASTA FILE, IF IT EXISTS
            return file(self.filepath, 'rU'), idFilter
        except IOError: # TRY READING FROM FORMATTED BLAST DATABASE
            cmd='fastacmd -D -d "%s"' % self.get_blast_index_path()
            return os.popen(cmd), NCBI_ID_PARSER #BLAST ADDS lcl| TO id


    _blast_prog_dict = dict(blastx='#BlastxMapping')

    def blast_program(self, seq, blastprog=None):
        'figure out appropriate blast program & remap via _blast_prog_dict'
        if blastprog is None:
            blastprog = blast_program(seq.seqtype(), self.seqDB._seqtype)
        oldprog = blastprog
        try: # apply program transformation if provided
            blastprog = self._blast_prog_dict[blastprog]
            if blastprog.startswith('#'): # not permitted by this class!
                raise ValueError('Use %s for %s' % (blastprog[1:], oldprog))
        except KeyError:
            pass # no program transformation to apply, so nothing to do...
        return blastprog

    def blast_command(self, blastpath, blastprog, expmax, maxseq, opts):
        'generate command string for running blast with desired options'
        filepath = self.get_blast_index_path()
        warn_if_whitespace(filepath)
        cmd = [blastpath, '-d', filepath, '-p', blastprog,
                '-e', '%e' % float(expmax)] + list(opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ['-b', '%d' % maxseq, '-v', '%d' % maxseq]
        return cmd

    def get_seq_from_queryDB(self, queryDB):
        'get one sequence obj from queryDB'
        seqID = iter(queryDB).next() # get 1st seq ID
        return queryDB[seqID]

    def translation_kwargs(self, blastprog):
        'return kwargs for read_blast_alignment() based on blastprog'
        d = dict(tblastn=dict(translateDest=True),
                 blastx=dict(translateSrc=True),
                 tblastx=dict(translateSrc=True, translateDest=True))
        try:
            return d[blastprog]
        except KeyError:
            return {}

    def __call__(self, seq=None, al=None, blastpath='blastall',
                 blastprog=None, expmax=0.001, maxseq=None, verbose=None,
                 opts=(), queryDB=None, **kwargs):
        "Run blast search for seq in database, return alignment object"
        if seq is None and queryDB is None:
            raise ValueError("we need a sequence or db to use as query!")
        if seq and queryDB:
            raise ValueError("both a sequence AND a db provided for query")
        if queryDB is not None:
            seq = self.get_seq_from_queryDB(queryDB)
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        blastprog = self.blast_program(seq, blastprog)
        cmd = self.blast_command(blastpath, blastprog, expmax, maxseq, opts)
        return process_blast(cmd, seq, self.idIndex, al, queryDB=queryDB,
                             ** self.translation_kwargs(blastprog))


class BlastxMapping(BlastMapping):
    """Because blastx changes the query to multiple sequences
    (representing its six possible frames), getitem can no longer
    return a single slice object, but instead an iterator for one
    or more slice objects representing the frames that had
    homology hits."""

    def __repr__(self):
        return "<BlastxMapping '%s'>" % (self.filepath)
    _blast_prog_dict = dict(blastn='tblastx', blastp='#BlastMapping',
                            tblastn='#BlastMapping')

    def __getitem__(self, query):
        """generate slices for all translations of the query """
        # generate NLMSA for this single sequence
        al = self(query)
        # get the translation database for the sequence
        tdb = translationDB.get_translation_db(query.db)

        # run through all of the frames & find alignments.
        slices = []
        for trans_seq in tdb[query.id].iter_frames():
            try:
                slice = al[trans_seq]
            except KeyError:
                continue

            if not isinstance(slice, EmptySlice):
                slices.append(slice)

        return slices


class MegablastMapping(BlastMapping):

    def __repr__(self):
        return "<MegablastMapping '%s'>" % (self.filepath)

    def __call__(self, seq, al=None, blastpath='megablast', expmax=1e-20,
                 maxseq=None, minIdentity=None,
                 maskOpts=['-U', 'T', '-F', 'm'],
                 rmPath='RepeatMasker', rmOpts=['-xsmall'],
                 verbose=None, opts=(), **kwargs):
        "Run megablast search with optional repeat masking."
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()

        # mask repeats to lowercase
        masked_seq = repeat_mask(seq, rmPath, rmOpts)
        filepath = self.get_blast_index_path()
        warn_if_whitespace(filepath)
        cmd = [blastpath] + maskOpts \
              + ['-d', filepath,
                 '-D', '2', '-e', '%e' % float(expmax)] + list(opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ['-b', '%d' % maxseq, '-v', '%d' % maxseq]
        if minIdentity is not None:
            cmd += ['-p', '%f' % float(minIdentity)]
        return process_blast(cmd, seq, self.idIndex, al, seqString=masked_seq,
                             popenArgs=dict(stdinFlag='-i'))


class BlastIDIndex(object):
    """This class acts as a wrapper around a regular seqDB, and handles
    the mangled IDs returned by BLAST to translate them to the correct ID.
    Since NCBI treats FASTA ID as a blob into which they like to stuff
    many fields... and then NCBI BLAST mangles those IDs when it reports
    hits, so they no longer match the true ID... we are forced into
    contortions to rescue the true ID from mangled IDs.

    Our workaround strategy: since NCBI packs the FASTA ID with multiple
    IDs (GI, GB, RefSeq ID etc.), we can use any of these identifiers
    that are found in a mangled ID, by storing a mapping of these
    sub-identifiers to the true FASTA ID."""

    def __init__(self, seqDB):
        self.seqDB = seqDB
        self.seqInfoDict = BlastIDInfoDict(self)
    # FOR UNPACKING NCBI IDENTIFIERS AS WORKAROUND FOR BLAST ID CRAZINESS
    id_delimiter='|'

    def unpack_id(self, id):
        """Return |-packed NCBI identifiers as unpacked list.

        NCBI packs identifier like gi|123456|gb|A12345|other|nonsense.
        Return as list."""
        return id.split(self.id_delimiter)

    def index_unpacked_ids(self, unpack_f=None):
        """Build an index of sub-IDs (unpacked from NCBI nasty habit
        of using the FASTA ID as a blob); you can customize the unpacking
        by overriding the unpack_id function or changing the id_delimiter.
        The index maps each sub-ID to the real ID, so that when BLAST
        hands back a mangled, fragmentary ID, we can unpack that mangled ID
        and look up the true ID in this index.  Any sub-ID that is found
        to map to more than one true ID will be mapped to None (so that
        random NCBI garbage like gnl or NCBI_MITO wont be treated as
        sub-IDs).
        """
        if unpack_f is None:
            unpack_f=self.unpack_id
        t={}
        for id in self.seqDB:
            for s in unpack_f(id):
                if s == id:
                    continue # DON'T STORE TRIVIAL MAPPINGS!!
                s=s.upper() # NCBI FORCES ID TO UPPERCASE?!?!
                try:
                    if t[s]!=id and t[s] is not None:
                        t[s]=None # s NOT UNIQUE, CAN'T BE AN IDENTIFIER!!
                except KeyError:
                    t[s]=id # s UNIQUE, TRY USING s AS AN IDENTIFIER
        for id in t.itervalues():
            if id is not None: # OK THERE ARE REAL MAPPINGS STORED, SO USE THIS
                self._unpacked_dict=t # SAVE THE MAPPING TO REAL IDENTIFIERS
                return
        # NO NON-TRIVIAL MAPPINGS, SO JUST SAVE EMPTY MAPPING
        self._unpacked_dict={}

    def get_real_id(self, bogusID, unpack_f=None):
        "try to translate an id that NCBI has mangled to the real sequence id"
        if unpack_f is None:
            unpack_f = self.unpack_id
        if not hasattr(self, '_unpacked_dict'):
            self.index_unpacked_ids(unpack_f)
        for s in unpack_f(bogusID):
            s = s.upper() # NCBI FORCES ID TO UPPERCASE?!?!
            try:
                id = self._unpacked_dict[s]
                if id is not None:
                    return id # OK, FOUND A MAPPING TO REAL ID
            except KeyError:
                pass # KEEP TRYING...
        # FOUND NO MAPPING, SO RAISE EXCEPTION
        raise KeyError("no key '%s' in database %s" % (bogusID,
                                                        repr(self.seqDB)))

    def __getitem__(self, seqID):
        "If seqID is mangled by BLAST, use our index to get correct ID"
        try: # default: treat as a correct ID
            return self.seqDB[seqID]
        except KeyError: # translate to the correct ID
            return self.seqDB[self.get_real_id(seqID)]

    def __contains__(self, seqID):
        try:
            self.seqInfoDict[seqID]
            return True
        except KeyError:
            return False


class BlastIDInfoDict(object, UserDict.DictMixin):
    """provide seqInfoDict interface for BlastIDIndex """

    def __init__(self, db):
        self.blastDB = db

    def __getitem__(self, seqID):
        try:
            return self.blastDB.seqDB.seqInfoDict[seqID]
        except KeyError:
            seqID = self.blastDB.get_real_id(seqID)
            return self.blastDB.seqDB.seqInfoDict[seqID]

    def __len__(self):
        return len(self.blastDB.seqDB.seqInfoDict)

    def __iter__(self):
        return iter(self.blastDB.seqDB.seqInfoDict)

    def keys(self):
        return self.blastDB.seqDB.seqInfoDict.keys()
