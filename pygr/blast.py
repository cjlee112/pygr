import os, tempfile, glob
import classutil, logger
from sequtil import *
from parse_blast import BlastHitParser
from seqdb import write_fasta, read_fasta
from nlmsa_utils import CoordsGroupStart, CoordsGroupEnd, CoordsToIntervals
from annotation import AnnotationDB, TranslationAnnot, TranslationAnnotSlice
import cnestedlist

# NCBI HAS THE NASTY HABIT OF TREATING THE IDENTIFIER AS A BLOB INTO
# WHICH THEY STUFF FIELD AFTER FIELD... E.G. gi|1234567|foobarU|NT_1234567|...
# THIS JUST YANKS OUT THE SECOND ARGUMENT SEPARATED BY |
NCBI_ID_PARSER=lambda id:id.split('|')[1]



def blast_program(query_type,db_type):
    progs= {DNA_SEQTYPE:{DNA_SEQTYPE:'blastn', PROTEIN_SEQTYPE:'blastx'},
            PROTEIN_SEQTYPE:{DNA_SEQTYPE:'tblastn', PROTEIN_SEQTYPE:'blastp'}}
    if query_type == RNA_SEQTYPE:
        query_type = DNA_SEQTYPE
    if db_type == RNA_SEQTYPE:
        db_type = DNA_SEQTYPE
    return progs[query_type][db_type]


def read_blast_alignment(ofile, srcDB, destDB, al=None, pipeline=None):
    """Apply sequence of transforms to read input from 'ofile'.
    
    BlastHitParser; CoordsToIntervals; save_interval_alignment OR [pipeline]
    If pipeline is not None, it must be a list of filter functions each
    taking a single argument and returning an iterator or iterable result
    object.
    """
    p = BlastHitParser()
    d = dict(id='src_id', start='src_start', stop='src_end', ori='src_ori',
             idDest='dest_id', startDest='dest_start',
             stopDest='dest_end', oriDest='dest_ori')
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

def process_blast(cmd, seq, seqDB, al=None, seqString=None, queryDB=None,
                  popenArgs={}, **kwargs):
    """Run blast and return an alignment."""
    seqID,p = start_blast(cmd, seq, seqString, seqDict=queryDB, **popenArgs)
    try:
        if queryDB is not None:
            al = read_blast_alignment(p.stdout, queryDB, seqDB, al, **kwargs)
        else:
            al = read_blast_alignment(p.stdout, {seqID:seq}, seqDB, al,
                                         **kwargs)
    finally:
        p.close() # close our PIPE files
    return al


def repeat_mask(seq, progname='RepeatMasker', opts=()):
    'Run RepeatMasker on a sequence, return lowercase-masked string'
    ## fd, temppath = tempfile.mkstemp()
    ## ofile = os.fdopen(fd, 'w') # text file
    p = classutil.FilePopen([progname] + list(opts), stdin=classutil.PIPE,
                            stdinFlag=None)
    write_fasta(p.stdin, seq, reformatter=lambda x:x.upper()) # save uppercase!
    try:
        if p.wait():
            raise OSError('command %s failed' % ' '.join(p.args[0]))
        ifile = file(p._stdin_path + '.masked', 'rU') # text file
        try:
            for id,title,seq_masked in read_fasta(ifile):
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


class BlastMapping(object):
    'Graph interface for mapping a sequence to homologs in a seq db via BLAST'
    def __init__(self, seqDB, filepath=None, blastReady=False,
                 blastIndexPath=None, blastIndexDirs=None, verbose=True,
                 **kwargs):
        '''seqDB: sequence database object to search for homologs
        filepath: location of FASTA format file for the sequence database
        blastReady: if True, ensure that BLAST index file ready to use
        blastIndexPath: location of the BLAST index file
        blastIndexDirs: list of directories for trying to build index in
        '''
        self.seqDB = seqDB
        self.idIndex = BlastIDIndex(seqDB)
        self.verbose = verbose
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
    def test_db_location(self, filepath):
        '''check whether BLAST index files ready for use; return status.'''
        if not os.access(filepath+'.nsd',os.R_OK) \
               and not os.access(filepath+'.psd',os.R_OK) \
               and not os.access(filepath+'.00.nsd',os.R_OK) \
               and not os.access(filepath+'.00.psd',os.R_OK):
            return False
        else: # FOUND INDEX FILES IN THIS LOCATION
            if filepath != self.filepath:
                self.blastIndexPath = filepath
            return True
    def checkdb(self):
        'look for blast index files in blastIndexPath, standard list of locations'
        for filepath in self.blast_index_paths():
            self.blastReady = self.test_db_location(filepath)
            if self.blastReady:
                break
        return self.blastReady
    def run_formatdb(self, filepath):
        'ATTEMPT TO BUILD BLAST DATABASE INDEXES at filepath'
        dirname = classutil.file_dirpath(filepath)
        if not os.access(dirname, os.W_OK): # check if directory is writable
            raise IOError('run_formatdb: directory %s is not writable!'
                          % dirname)
        cmd = ['formatdb', '-i', self.filepath, '-n', filepath, '-o', 'T']
        if self.seqDB._seqtype != PROTEIN_SEQTYPE:
            cmd += ['-p', 'F'] # special flag required for nucleotide seqs
        logger.info('Building index: ' + ' '.join(cmd))
        if classutil.call_subprocess(cmd): # bad exit code, so command failed
            raise OSError('command %s failed' % ' '.join(cmd))
        self.blastReady=True
        if filepath!=self.filepath:
            self.blastIndexPath = filepath
    def get_blast_index_path(self):
        'get path to base name for BLAST index files'
        try:
            return self.blastIndexPath
        except AttributeError:
            return self.filepath
    # DEFAULT: BUILD INDEX FILES IN self.filepath . HOME OR APPROPRIATE
    # USER-/SYSTEM-SPECIFIC TEMPORARY DIRECTORY
    blastIndexDirs = ['FILEPATH',os.getcwd,os.path.expanduser,
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
            yield os.path.join(s,os.path.basename(self.filepath))
    def formatdb(self, filepath=None):
        'try to build BLAST index files in an appropriate location'
        if filepath is not None: # JUST USE THE SPECIFIED PATH
            return self.run_formatdb(filepath)
        notFirst = False
        for filepath in self.blast_index_paths():
            if notFirst:
                logger.info('Trying next entry in self.blastIndexDirs...')
            notFirst = True
            try: # BUILD IN TARGET DIRECTORY
                return self.run_formatdb(filepath)
            except (IOError,OSError): # BUILD FAILED 
                classutil.report_exception() # REPORT IT AND CONTINUE
        # @CTB shouldn't we check to make sure that at least one formatdb
        # succeeded?  Of course, it may be that we don't need to run
        # formatdb because the database exists... so, what, just report
        # the blastall error?
            
    def raw_fasta_stream(self, ifile=None, idFilter=None):
        '''Return a stream of fasta-formatted sequences.

        Optionally, apply an ID filter function if supplied.
        '''
        if ifile is not None: # JUST USE THE STREAM WE ALREADY HAVE OPEN
            return ifile,idFilter
        try: # DEFAULT: JUST READ THE FASTA FILE, IF IT EXISTS
            return file(self.filepath, 'rU'),idFilter
        except IOError: # TRY READING FROM FORMATTED BLAST DATABASE
            cmd='fastacmd -D -d "%s"' % self.get_blast_index_path()
            return os.popen(cmd),NCBI_ID_PARSER #BLAST ADDS lcl| TO id

    def warn_about_self_masking(self, seq, verbose, methodname='blast'):
        if verbose is None:
            verbose = self.verbose
        if not verbose: # don't print out annoying warning messages
            return
        try:
            if seq.db is self.seqDB:
                logger.warning('''
WARNING: your query sequence is part of this database.  Pygr alignments
normally do not report self-matches, i.e. the alignment of a sequence interval
to itself, so only homologies to OTHER sequences in the database
(or other intervals of the query sequence, if they are homologous) will be
reported (or an empty query result if no such homologies are found).
To report ALL homologies, including the self-match, simply create a new
sequence object and use that as your query, e.g.
query = sequence.Sequence(str(seq),"myquery")
results = db.%s(query)

To turn off this message, use the verbose=False option''' % methodname)
        except AttributeError:
            pass
    def blast_program(self, seq, blastprog):
        'figure out appropriate blast program if needed'
        if blastprog is None:
            return blast_program(seq.seqtype(), self.seqDB._seqtype)
        return blastprog
    def blast_command(self, blastpath, blastprog, expmax, maxseq, opts):
        'generate command string for running blast with desired options'
        cmd = [blastpath, '-d', self.get_blast_index_path(), '-p', blastprog,
                '-e', '%e' % float(expmax)] + list(opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ['-b', '%d' % maxseq, '-v', '%d' % maxseq]
        return cmd
    def get_seq_from_queryDB(self, queryDB):
        'get one sequence obj from queryDB'
        seqID = iter(queryDB).next() # get 1st seq ID
        return queryDB[seqID]
    def __call__(self, seq=None, al=None, blastpath='blastall',
                 blastprog=None, expmax=0.001, maxseq=None, verbose=None,
                 opts=(), queryDB=None, **kwargs):
        "Run blast search for seq in database, return aligned intervals"
        if seq is None and queryDB is None:
            raise ValueError("we need a sequence or db to use as query!")
        if seq and queryDB:
            raise ValueError("both a sequence AND a db provided for query")
        if queryDB is not None:
            seq = self.get_seq_from_queryDB(queryDB)
        self.warn_about_self_masking(seq, verbose)
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        blastprog = self.blast_program(seq, blastprog)
        cmd = self.blast_command(blastpath, blastprog, expmax, maxseq, opts)
        if blastprog=='tblastn': # apply ORF transformation to results
            pipeline = (TblastnTransform(), save_interval_alignment)
        elif blastprog=='blastx':
            raise ValueError("Use BlastxMapping for " + blastprog)
        else:
            pipeline = None
        return process_blast(cmd, seq, self.idIndex, al, queryDB=queryDB,
                             pipeline=pipeline)

class MegablastMapping(BlastMapping):
    def __repr__(self):
        return "<MegablastMapping '%s'>" % (self.filepath)
    def __call__(self, seq, al=None, blastpath='megablast', expmax=1e-20,
                 maxseq=None, minIdentity=None,
                 maskOpts=['-U', 'T', '-F', 'm'],
                 rmPath='RepeatMasker', rmOpts=['-xsmall'],
                 verbose=None, opts=(), **kwargs):
        "Run megablast search with optional repeat masking."
        self.warn_about_self_masking(seq, verbose, 'megablast')
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()

        # mask repeats to lowercase
        masked_seq = repeat_mask(seq,rmPath,rmOpts)
        cmd = [blastpath] + maskOpts \
              + ['-d', self.get_blast_index_path(),
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
    # FOR UNPACKING NCBI IDENTIFIERS AS WORKAROUND FOR BLAST ID CRAZINESS
    id_delimiter='|'
    def unpack_id(self,id):
        """Return |-packed NCBI identifiers as unpacked list.

        NCBI packs identifier like gi|123456|gb|A12345|other|nonsense.
        Return as list."""
        return id.split(self.id_delimiter)

    def index_unpacked_ids(self,unpack_f=None):
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
                if s==id: continue # DON'T STORE TRIVIAL MAPPINGS!!
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

    def get_real_id(self,bogusID,unpack_f=None):
        "try to translate an id that NCBI has mangled to the real sequence id"
        if unpack_f is None:
            unpack_f=self.unpack_id
        if not hasattr(self,'_unpacked_dict'):
            self.index_unpacked_ids(unpack_f)
        for s in unpack_f(bogusID):
            s=s.upper() # NCBI FORCES ID TO UPPERCASE?!?!
            try:
                id=self._unpacked_dict[s]
                if id is not None:
                    return id # OK, FOUND A MAPPING TO REAL ID
            except KeyError:
                pass # KEEP TRYING...
        # FOUND NO MAPPING, SO RAISE EXCEPTION            
        raise KeyError, "no key '%s' in database %s" % (bogusID,
                                                        repr(self.seqDB))

    def __getitem__(self, seqID):
        "If seqID is mangled by BLAST, use our index to get correct ID"
        try: # default: treat as a correct ID
            return self.seqDB[seqID]
        except KeyError: # translate to the correct ID
            return self.seqDB[self.get_real_id(seqID)]

def get_orf_slices(ivals):
    'create list of TranslationAnnotation slices from union of seq ivals'
    it = iter(ivals)
    try:
        region = it.next()
    except StopIteration:
        raise ValueError('empty ivals list!')
    seqDB = region.db

    # construct a covering ival by taking the union of all ivals
    for ival in it:
        region = region + ival

    # retrieve or create a translation db that will automatically 
    try:
        translationDB = seqDB.translationDB
    except AttributeError: # create a new TranslationAnnot DB
        translationDB = AnnotationDB({}, seqDB, itemClass=TranslationAnnot,
                                     itemSliceClass=TranslationAnnotSlice,
                                     sliceAttrDict=dict(id=0,start=1,stop=2))
        seqDB.translationDB = translationDB

    # create an annotation representing the entire translated ORF, named
    # uniquely by taking the length of the database.
    a = translationDB.new_annotation(str(len(translationDB)),
                                     (region.id, region.start, region.stop))

    # now, for each of the ORF intervals, construct a new annotation ival
    # and keep.
    l = []
    for ival in ivals: # transform to slices of our ORF annotation
        aval = a[(ival.start - region.start)/3 :
                   (ival.stop - region.start)/3]
        l.append(aval)
    return l

class TblastnTransform(object):
    def __init__(self, xformSrc=False, xformDest=True):
        self.xformSrc = xformSrc
        self.xformDest = xformDest

    def __call__(self, alignedIvals):
        'process target nucleotide ivals into TranslationAnnot slices'
        for t in alignedIvals: # read aligned protein:nucleotide ival pairs
            if isinstance(t, CoordsGroupStart):
                yield t # pass through grouping marker in case anyone cares
                srcIvals = []
                destIvals = []
            elif isinstance(t, CoordsGroupEnd): # process all ivals in this hit
                if self.xformSrc: # transform to TranslationAnnot
                    srcIvals = get_orf_slices(srcIvals)
                if self.xformDest: # transform to TranslationAnnot
                    destIvals = get_orf_slices(destIvals)
                it = iter(srcIvals)
                for dest in destIvals: # recombine src,dest pairs
                    yield (it.next(), dest)  # no edge info
                yield t # pass through grouping marker in case anyone cares
            else: # just keep accumulating all the ivals for this hit
                srcIvals.append(t[0])
                destIvals.append(t[1])


def blastx_results(alignedIvals):
    '''store blastx or tblastx results as a list of individual hits.
    Each hit is stored as the usual NLMSASlice interface (e.g.
    use its edges() method to get src,dest,edgeInfo tuples'''
    l = []
    for t in alignedIvals:
        if isinstance(t, CoordsGroupStart):
            for slice in l:
                yield slice
                
            l = []
            al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True)
        elif isinstance(t, CoordsGroupEnd): # process all ivals in this hit
            al.build()
            l.append(al[queryORF]) # save NLMSASlice view of this hit
        else: # just keep accumulating all the ivals for this hit
            al += t[0]
            al[t[0]][t[1]] = None # save their alignment
            queryORF = t[0].path

    for slice in l:
        yield slice

class BlastxMapping(BlastMapping):
    '''use this mapping class for blastx or tblastx queries.
    Note that its interface is a little different than BlastMapping
    in that it returns a list of hits, one for each hit returned by
    blastx, in the same order as returned by blastx (whereas BlastMapping
    consolidates all the hits into a single alignment object).
    BlastxMapping does this because blastx may find multiple ORFs
    in the query sequence; due to this complication it is simplest
    to simply return the hits one at a time exactly as blastx reports them.'''
    def __repr__(self):
        return "<BlastxMapping '%s'>" % (self.filepath)
    def __call__(self, seq=None, blastpath='blastall',
                 blastprog=None, expmax=0.001, maxseq=None, verbose=None,
                 opts='', queryDB=None, xformSrc=True, xformDest=False,
                 **kwargs):
        'perform blastx or tblastx query'
        if seq is None and queryDB is None:
            raise ValueError("we need a sequence or db to use as query!")
        if seq and queryDB:
            raise ValueError("both a sequence AND a db provided for query")
        if queryDB is not None:
            seq = self.get_seq_from_queryDB(queryDB)
            
        self.warn_about_self_masking(seq, verbose)
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        blastprog = self.blast_program(seq, blastprog)
        if blastprog=='blastn':
            blastprog = 'tblastx'
            xformDest = True # must also transform the destDB sequence to ORF
        elif blastprog != 'blastx':
            raise ValueError('Use BlastMapping for ' + blastprog)
        cmd = self.blast_command(blastpath, blastprog, expmax, maxseq, opts)
        seqID,p = start_blast(cmd, seq, seqDict=queryDB) # run the command
        try:
            if queryDB is None:
                srcDB = { seqID: seq }
            else:
                srcDB = queryDB
            pipeline = (TblastnTransform(xformSrc, xformDest), blastx_results,
                        list) # load results to list before p.close()!!
            # save the results            
            results = read_blast_alignment(p.stdout, srcDB, self.idIndex,
                                           pipeline=pipeline)
        finally:
            p.close() # close our PIPE files
        return results

    def __getitem__(self, k):
        return self.__call__(k)
