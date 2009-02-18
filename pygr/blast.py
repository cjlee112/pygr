import os
import classutil
from sequtil import *
from parse_blast import BlastHitParser
from seqdb import write_fasta, read_fasta
from nlmsa_utils import CoordsGroupStart, CoordsGroupEnd, read_aligned_coords
from annotation import AnnotationDB, TranslationAnnot, TranslationAnnotSlice

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


def read_interval_alignment(ofile, srcDB, destDB, al=None, **kwargs):
    "Read tab-delimited interval mapping between seqs from the 2 sets of seqs"
    needToBuild = False
    if al is None:
        import cnestedlist
        al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True)
        needToBuild = True
    p = BlastHitParser()
    al.add_aligned_intervals(p.parse_file(ofile), srcDB, destDB,
                             alignedIvalsAttrs=
                             dict(id='src_id', start='src_start',
                                  stop='src_end', ori='src_ori',
                                  idDest='dest_id', startDest='dest_start',
                                  stopDest='dest_end', oriDest='dest_ori'),
                             **kwargs)
    if p.nline == 0: # NO BLAST OUTPUT??
        raise IOError('no BLAST output.  Check that blastall is in your PATH')
    if needToBuild:
        al.build()
    return al

def start_blast(cmd, seq, seqString=None):
    "run blast, pipe in sequence, pipe out aligned interval lines, return an alignment"
    ifile,ofile = os.popen2(cmd)
    if seqString is None:
        seqString = seq
    seqID = write_fasta(ifile, seqString)
    ifile.close()
    return seqID,ofile

def process_blast(cmd, seq, seqDB, al=None, seqString=None, **kwargs):
    "run blast, pipe in sequence, pipe out aligned interval lines, return an alignment"
    seqID,ofile = start_blast(cmd, seq, seqString)
    al = read_interval_alignment(ofile, {seqID:seq}, seqDB, al, **kwargs)
    if ofile.close() is not None:
        raise OSError('command %s failed' % cmd)
    return al


def repeat_mask(seq, progname='RepeatMasker', opts=''):
    'Run RepeatMasker on a sequence, return lowercase-masked string'
    temppath = os.tempnam()
    ofile = file(temppath,'w') # text file
    write_fasta(ofile, seq, reformatter=lambda x:x.upper()) # SAVE IN UPPERCASE!
    ofile.close()
    cmd = progname + ' ' + opts + ' ' + temppath
    if os.system(cmd) != 0:
        raise OSError('command %s failed' % cmd)
    ifile = file(temppath+'.masked', 'rU') # text file
    for id,title,seq_masked in read_fasta(ifile):
        break # JUST READ ONE SEQUENCE
    ifile.close()
    cmd = 'rm -f %s %s.*' % (temppath,temppath)
    if os.system(cmd) != 0:
        raise OSError('command ' + cmd + ' failed')
    return seq_masked # ONLY THE REPEATS ARE IN LOWERCASE NOW


class BlastMapping(object):
    'Graph interface for mapping a sequence to homologs in a seq db via BLAST'
    def __init__(self, seqDB, filepath=None, blastReady=False,
                 blastIndexPath=None, blastIndexDirs=None, **kwargs):
        '''seqDB: sequence database object to search for homologs
        filepath: location of FASTA format file for the sequence database
        blastReady: if True, ensure that BLAST index file ready to use
        blastIndexPath: location of the BLAST index file
        blastIndexDirs: list of directories for trying to build index in
        '''
        self.seqDB = seqDB
        self.idIndex = BlastIDIndex(seqDB)
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
    def __getitem__(self, k, **kwargs):
        'return NLMSASlice representing BLAST results'
        al = self(k, **kwargs) # run BLAST & get NLMSA storing results
        return al[k] # return NLMSASlice representing these results
    def test_db_location(self, filepath):
        'check whether BLAST index files ready for use; return self.blastReady status'
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
        cmd = 'formatdb -i "%s" -n "%s" -o T' % (self.filepath,filepath)
        if self.seqDB._seqtype != PROTEIN_SEQTYPE:
            cmd += ' -p F' # SPECIAL FLAG REQUIRED FOR NUCLEOTIDE SEQS
        import sys
        print >>sys.stderr,'Building index:',cmd
        if os.system(cmd)!=0: # BAD EXIT CODE, SO COMMAND FAILED
            raise OSError('command %s failed' % cmd)
        self.blastReady=True
        if filepath!=self.filepath:
            self.blastIndexPath = filepath
    def get_blast_index_path(self):
        'get path to base name for BLAST index files'
        try:
            return self.blastIndexPath
        except AttributeError:
            return self.filepath
    # DEFAULT: BUILD INDEX FILES IN self.filepath . HOME OR /tmp 
    blastIndexDirs = ['FILEPATH',os.getcwd,os.path.expanduser,
                      classutil.default_tmp_path]
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
                import sys
                print >>sys.stderr,'Trying next entry in self.blastIndexDirs...'
            notFirst = True
            try: # BUILD IN TARGET DIRECTORY
                return self.run_formatdb(filepath)
            except (IOError,OSError): # BUILD FAILED 
                classutil.report_exception() # REPORT IT AND CONTINUE
            
    def raw_fasta_stream(self, ifile=None, idFilter=None):
        'return a stream of fasta-formatted sequences, and ID filter function if needed'
        if ifile is not None: # JUST USE THE STREAM WE ALREADY HAVE OPEN
            return ifile,idFilter
        try: # DEFAULT: JUST READ THE FASTA FILE, IF IT EXISTS
            return file(self.filepath, 'rU'),idFilter
        except IOError: # TRY READING FROM FORMATTED BLAST DATABASE
            cmd='fastacmd -D -d "%s"' % self.get_blast_index_path()
            return os.popen(cmd),NCBI_ID_PARSER #BLAST ADDS lcl| TO id

    def warn_about_self_masking(self, seq, methodname='blast'):
        try:
            if seq.db is self.seqDB:
                import sys
                print >>sys.stderr,'''
WARNING: your query sequence is part of this database.  Pygr alignments
normally do not report self-matches, i.e. the alignment of a sequence interval
to itself, so only homologies to OTHER sequences in the database
(or other intervals of the query sequence, if they are homologous) will be
reported (or an empty query result if no such homologies are found).
To report ALL homologies, including the self-match, simply create a new
sequence object and use that as your query, e.g.
query = sequence.Sequence(str(seq),"myquery")
results = db.%s(query)

To turn off this message, use the verbose=False option''' % methodname
        except AttributeError:
            pass
    def blast_program(self, seq, blastprog):
        'figure out appropriate blast program if needed'
        if blastprog is None:
            return blast_program(seq.seqtype(), self.seqDB._seqtype)
        return blastprog
    def blast_command(self, blastpath, blastprog, expmax, maxseq, opts):
        'generate command string for running blast with desired options'
        cmd = '%s -d "%s" -p %s -e %e %s'  \
              %(blastpath, self.get_blast_index_path(), blastprog,
                float(expmax), opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ' -b %d -v %d' % (maxseq,maxseq)
        return cmd
    def __call__(self, seq, al=None, blastpath='blastall',
                 blastprog=None, expmax=0.001, maxseq=None, verbose=True,
                 opts='', **kwargs):
        "Run blast search for seq in database, return aligned intervals"
        if verbose:
            self.warn_about_self_masking(seq)
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        blastprog = self.blast_program(seq, blastprog)
        cmd = self.blast_command(blastpath, blastprog, expmax, maxseq, opts)
        if blastprog=='tblastn': # apply ORF transformation to results
            return process_blast(cmd, seq, self.idIndex, al,
                                 groupIntervals=generate_tblastn_ivals)
        elif blastprog=='blastx':
            raise ValueError("Use BlastxMapping for " + blastprog)
        else:
            return process_blast(cmd, seq, self.idIndex, al)

class MegablastMapping(BlastMapping):
    def __call__(self, seq, al=None, blastpath='megablast', expmax=1e-20,
                 maxseq=None, minIdentity=None, maskOpts='-U T -F m',
                 rmPath='RepeatMasker', rmOpts='-xsmall',
                 verbose=True, opts='', **kwargs):
        "Run megablast search with optional repeat masking."
        if verbose:
            self.warn_about_self_masking(seq, 'megablast')
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        masked_seq = repeat_mask(seq,rmPath,rmOpts)  # MASK REPEATS TO lowercase
        cmd = '%s %s -d "%s" -D 2 -e %e -i stdin %s' \
             % (blastpath, maskOpts, self.get_blast_index_path(),
                float(expmax), opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ' -b %d -v %d' % (maxseq,maxseq)
        if minIdentity is not None:
            cmd += ' -p %f' % float(minIdentity)
        return process_blast(cmd, seq, self.idIndex, al, seqString=masked_seq)


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
    id_delimiter='|' # FOR UNPACKING NCBI IDENTIFIERS AS WORKAROUND FOR BLAST ID CRAZINESS
    def unpack_id(self,id):
        "NCBI packs identifier like gi|123456|gb|A12345|other|nonsense. Return as list"
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
        self._unpacked_dict={} # NO NON-TRIVIAL MAPPINGS, SO JUST SAVE EMPTY MAPPING

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

def get_orf_slices(ivals, **kwargs):
    'create list of TranslationAnnotation slices from union of seq ivals'
    it = iter(ivals)
    try:
        region = it.next()
    except StopIteration:
        raise ValueError('empty ivals list!')
    seqDB = region.db
    for ival in it:
        region = region + ival # get total union of all intervals
    try:
        translationDB = seqDB.translationDB
    except AttributeError: # create a new TranslationAnnot DB
        translationDB = AnnotationDB({}, seqDB, itemClass=TranslationAnnot,
                                     itemSliceClass=TranslationAnnotSlice,
                                     sliceAttrDict=dict(id=0,start=1,stop=2))
        seqDB.translationDB = translationDB
    a = translationDB.new_annotation(str(len(translationDB)),
                                     (region.id, region.start, region.stop))
    l = []
    for ival in ivals: # transform to slices of our ORF annotation
        aval = a[(ival.start - region.start)/3 :
                   (ival.stop - region.start)/3]
        l.append(aval)
    return l

def generate_tblastn_ivals(alignedIvals, xformSrc=False, xformDest=True,
                           **kwargs):
    'process target nucleotide ivals into TranslationAnnot slices'
    for t in alignedIvals: # read aligned protein:nucleotide ival pairs
        if isinstance(t, CoordsGroupStart):
            yield t # pass through grouping marker in case anyone cares
            srcIvals = []
            destIvals = []
        elif isinstance(t, CoordsGroupEnd): # process all ivals in this hit
            if xformSrc: # transform to TranslationAnnot
                srcIvals = get_orf_slices(srcIvals, **kwargs)
            if xformDest: # transform to TranslationAnnot
                destIvals = get_orf_slices(destIvals, **kwargs)
            it = iter(srcIvals)
            for dest in destIvals: # recombine src,dest pairs
                yield (it.next(),dest,None)  # no edge info
            yield t # pass through grouping marker in case anyone cares
        else: # just keep accumulating all the ivals for this hit
            srcIvals.append(t[0])
            destIvals.append(t[1])


class BlastxResults(object):
    '''holds blastx or tblastx results.  Iterate over it to get hits one by one
    Each hit is returned as the usual NLMSASlice interface (e.g.
    use its edges() method to get src,dest,edgeInfo tuples'''
    def __init__(self, ofile, srcDB, destDB, xformSrc=True, xformDest=False,
                 **kwargs):
        import cnestedlist
        p = BlastHitParser()
        alignedIvals = read_aligned_coords(p.parse_file(ofile), srcDB, destDB,
                                           dict(id='src_id', start='src_start',
                                                stop='src_end', ori='src_ori',
                                                idDest='dest_id',
                                                startDest='dest_start',
                                                stopDest='dest_end',
                                                oriDest='dest_ori'))
        l = []
        for t in generate_tblastn_ivals(alignedIvals, xformSrc, xformDest):
            if isinstance(t, CoordsGroupStart):
                al = cnestedlist.NLMSA('blasthits', 'memory', pairwiseMode=True)
            elif isinstance(t, CoordsGroupEnd): # process all ivals in this hit
                al.build()
                l.append(al[queryORF]) # save NLMSASlice view of this hit
            else: # just keep accumulating all the ivals for this hit
                al += t[0]
                al[t[0]][t[1]] = None # save their alignment
                queryORF = t[0].path
        self.hits = l
    def __iter__(self):
        return iter(self.hits)
    def __len__(self):
        return len(self.hits)

class BlastxMapping(BlastMapping):
    '''use this mapping class for blastx or tblastx queries.
    Note that its interface is a little different than BlastMapping
    in that it returns a list of hits, one for each hit returned by
    blastx, in the same order as returned by blastx (whereas BlastMapping
    consolidates all the hits into a single alignment object).
    BlastxMapping does this because blastx may find multiple ORFs
    in the query sequence; due to this complication it is simplest
    to simply return the hits one at a time exactly as blastx reports them.
    Running a query on this class returns a BlastxResults object
    which provides an interface to iterate through the hits one by one.'''
    def __call__(self, seq, blastpath='blastall',
                 blastprog=None, expmax=0.001, maxseq=None, verbose=True,
                 opts='', xformSrc=True, xformDest=False, **kwargs):
        'perform blastx or tblastx query'
        if verbose:
            self.warn_about_self_masking(seq)
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        blastprog = self.blast_program(seq, blastprog)
        if blastprog=='blastn':
            blastprog = 'tblastx'
            xformDest = True # must also transform the destDB sequence to ORF
        elif blastprog != 'blastx':
            raise ValueError('Use BlastMapping for ' + blastprog)
        cmd = self.blast_command(blastpath, blastprog, expmax, maxseq, opts)
        seqID,ofile = start_blast(cmd, seq) # run the command
        results = BlastxResults(ofile, {seqID:seq}, self.idIndex, xformSrc,
                                xformDest, **kwargs) # save the results
        if ofile.close() is not None:
            raise OSError('command %s failed' % cmd)
        return results
    def __getitem__(self, k):
        return self(k)
