import os
import shelve
from sqlgraph import *
from poa import *


class SQLSequence(SQLRow,NamedSequenceBase):
    "Transparent access to a DB row representing a sequence; no caching."
    def __init__(self,table,id):
        SQLRow.__init__(self,table,id)
        NamedSequenceBase.__init__(self)
    def strslice(self,start,end):
        "Efficient access to slice of a sequence, useful for huge contigs"
        return self._select('substring(%s FROM %d FOR %d)'
                            %(self._attrSQL('seq'),start+1,end-start))

class DNASQLSequence(SQLSequence):
    _seqtype=DNA_SEQTYPE

class RNASQLSequence(SQLSequence):
    _seqtype=RNA_SEQTYPE

class ProteinSQLSequence(SQLSequence):
    _seqtype=PROTEIN_SEQTYPE


seq_id_counter=0
def new_seq_id():
    global seq_id_counter
    seq_id_counter += 1
    return seq_id_counter-1


def write_fasta(ofile,s,chunk=60,id=None):
    "Trivial FASTA output"
    if id is None:
        try:
            id=s.id
        except AttributeError:
            id=new_seq_id()

    ofile.write('>'+str(id)+'\n')
    seq=str(s)
    end=len(seq)
    pos=0
    while 1:
        ofile.write(seq[pos:pos+chunk]+'\n')
        pos += chunk
        if pos>=end:
            break
    return id # IN CASE CALLER WANTS TEMP ID WE MAY HAVE ASSIGNED

def read_fasta(ifile,onlyReadOneLine=False):
    "Get one sequence at a time from stream ifile"
    id=None
    title=''
    seq=''
    for line in ifile:
        if '>'==line[0]:
            if id!=None and len(seq)>0:
                yield id,title,seq
            id=line[1:].split()[0]
            title=line[len(id)+2:]
        elif id!=None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seq += word
            if onlyReadOneLine and len(seq)>0:
                yield id,title,seq
    if id!=None and len(seq)>0:
        yield id,title,seq

def read_fasta_lengths(ifile):
    "Generate sequence ID,length from stream ifile"
    id=None
    seqLength=0
    for line in ifile:
        if '>'==line[0]:
            if id is not None and seqLength>0:
                yield id,seqLength
            id=line[1:].split()[0]
            seqLength=0
        elif id is not None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seqLength += len(word)
    if id is not None and seqLength>0:
        yield id,seqLength


def store_seqlen_dict(d,ifile,idFilter=None):
    "store sequence lengths in a dictionary"
    if idFilter is not None: # HAVE TO CLEAN UP BLAST'S MESSY IDs
        for id,seqLength in read_fasta_lengths(ifile):
            d[idFilter(id)]=seqLength # SAVE TO DICTIONARY
    else: # JUST USE id AS-IS
        for id,seqLength in read_fasta_lengths(ifile):
            d[id]=seqLength # SAVE TO DICTIONARY
        

def fastacmd_seq(filepath,id,start=None,end=None):
    "Get complete sequence or slice from a BLAST formatted database"
    if start is not None: # USE ABILITY TO GRAB A SLICE OF THE SEQUENCE
        cmd='fastacmd -d %s -s "%s" -L %d,%d' % (filepath,id,start+1,end)
    else:
        cmd='fastacmd -d %s -s "%s"' % (filepath,id)
    ofile=os.popen(cmd)
    ofile.readline() # SKIP TITLE LINE
    s=''
    for line in ofile:
        for word in line.split(): # GET RID OF WHITESPACE...
            s += word
    if ofile.close() is not None:
        raise OSError('command %s failed' % cmd)
    return s


class FastacmdIntervalCache(object):
    def __init__(self,start,end):
        self.start=start
        self.end=end

    def __getitem__(self,k):
        pass # THIS NEEDS MORE WORK...


class BlastSeqDescriptor(object):
    "Get sequence from a blast formatted database for obj.id"
    def __get__(self,obj,objtype):
        return fastacmd_seq(obj.db.filepath,obj.id)

class BlastSequenceBase(NamedSequenceBase):
    "Represents a sequence in a blast database, w/o keeping seq in memory"
    seq=BlastSeqDescriptor()
    def __init__(self,db,id):
        self.db=db
        self.id=id
        NamedSequenceBase.__init__(self)
    def strslice(self,start,end):
        "Efficient access to slice of a sequence, useful for huge contigs"
        return fastacmd_seq(self.db.filepath,self.id,start,end)

class BlastSequence(BlastSequenceBase):
    "Rely on seqLenDict to give fast access to sequence lengths"
    def __len__(self):
        "Use persistent storage of sequence lengths to avoid reading whole sequence"
        return self.db.seqLenDict[self.id]

def blast_program(query_type,db_type):
    progs= {DNA_SEQTYPE:{DNA_SEQTYPE:'blastn', PROTEIN_SEQTYPE:'blastx'},
            PROTEIN_SEQTYPE:{DNA_SEQTYPE:'tblastn', PROTEIN_SEQTYPE:'blastp'}}
    if query_type==RNA_SEQTYPE:
        query_type=DNA_SEQTYPE
    if db_type==RNA_SEQTYPE:
        db_type=DNA_SEQTYPE
    return progs[query_type][db_type]


class BlastIval(TupleO):
    "Wrap a tuple with same attribute names as poa.IntervalTransform.repr_dict"
    _attrcol={'hit_id':0, 'src_id':1, 'dest_id':2, 'blast_score':3, 'e_value':4,
              'percent_id':5, 'dest_ori':6, 'src_start':7, 'length':8, 'dest_start':9}
    def __init__(self,t):
        "Convert strings into appropriate types; adjust to zero-based indexes"
        u=(int(t[0]),t[1],t[2],int(t[3]),float(t[4]),
           int(t[5]),int(t[6]),int(t[7])-1,int(t[8]),int(t[9])-1)
        TupleO.__init__(self,u)
    def __getattr__(self,k):
        'provide a few attributes to give same interface as poa.IntervalTransform.repr_dict'
        if k=='src_ori': return 1
        if k=='src_end': return self.src_start+self.length
        if k=='dest_end': return self.dest_start+self.length
        else: return TupleO.__getattr__(self,k)

class BlastHitInfo(TupleO):
    _attrcol={'blast_score':0,'e_value':1,'percent_id':2}
    def __init__(self,ival):
        "save edge info from ival onto our TupleO"
        ei=len(self._attrcol)*[None] # RIGHT LENGTH LIST
        for a,i in self._attrcol.items():
            try:
                ei[i]=getattr(ival,a) # CONSTRUCT ATTRS IN RIGHT ORDER
            except AttributeError:
                pass # OK FOR ival TO LACK SOME ATTRIBUTES...
        TupleO.__init__(self,ei)
        
    def repr_dict(self):
        return {'blast_score':self.data[0],'e_value':self.data[1],
                'percent_id':self.data[2]}

def get_interval(seq,start,end,ori):
    "trivial function to get the interval seq[start:end] with requested ori"
    ival=seq[start:end]
    if ori== -1:
        ival= -ival
    return ival

def save_interval_alignment(m,ival,srcSet,destSet=None,edgeClass=BlastHitInfo,
                            ivalXform=get_interval):
    "Add ival to alignment m, with edge info if requested"
    if destSet is None:
        destSet=srcSet
    srcSeq=srcSet[ival.src_id]
    srcPath=ivalXform(srcSeq,ival.src_start,ival.src_end,ival.src_ori)
    destPath=ivalXform(destSet[ival.dest_id],ival.dest_start,ival.dest_end,ival.dest_ori)
    if edgeClass is not None:
        m+=srcSeq # MAKE SURE THIS SEQUENCE IS IN THE MAPPING TOP-LEVEL INDEX
        m[srcPath][destPath]=edgeClass(ival) # SAVE ALIGNMENT WITH EDGE INFO
    else:
        m[srcPath]=destPath # JUST SAVE ALIGNMENT, NO EDGE INFO
    return srcPath,destPath # HAND BACK IN CASE CALLER WANTS TO KNOW THE INTERVALS


def read_interval_alignment(ofile,srcSet,destSet,al=None):
    "Read tab-delimited interval mapping between seqs from the 2 sets of seqs"
    if al is None:
        al=PathMapping()
    for line in ofile:
        t=line.split('\t')
        if t[0]=='MATCH_INTERVAL':
            save_interval_alignment(al,BlastIval(t[1:]),srcSet,destSet)
    return al

def process_blast(cmd,seq,seqDB,al=None,seqString=None):
    "run blast, pipe in sequence, pipe out aligned interval lines, return an alignment"
    ifile,ofile=os.popen2(cmd+'|parse_blast.awk -v mode=all')
    if seqString is None:
        seqString=seq
    write_fasta(ifile,seqString,id=seq.id)
    ifile.close()
    al=read_interval_alignment(ofile,{seq.id:seq},seqDB,al)
    print ofile.readline()
    if ofile.close() is not None:
        raise OSError('command %s failed' % cmd)
    return al


def repeat_mask(seq,progname='RepeatMasker -xsmall',opts=''):
    'Run RepeatMasker on a sequence, return lowercase-masked string'
    temppath=os.tempnam()
    ofile=file(temppath,'w')
    write_fasta(ofile,seq)
    ofile.close()
    cmd=progname+' '+opts+' '+temppath
    if os.system(cmd)!=0:
        raise OSError('command %s failed' % cmd)
    ofile=file(temppath+'.masked')
    for id,title,seq_masked in read_fasta(ofile):
        break # JUST READ ONE SEQUENCE
    ofile.close()
    cmd='rm -f %s %s.*' % (temppath,temppath)
    if os.system(cmd)!=0:
        raise OSError('command '+cmd+' failed')
    return seq_masked


class BlastDB(dict):
    "Container representing Blast database"
    seqClass=BlastSequence # CLASS TO USE FOR SAVING EACH SEQUENCE
    def __init__(self,filepath,skipSeqLenDict=False):
        "format database and build indexes if needed"
        self.filepath=filepath
        dict.__init__(self)
        self.set_seqtype()
        if skipSeqLenDict:
            self.seqClass=BlastSequenceBase # DON'T USE seqLenDict
        else:
            import anydbm
            try: # THIS WILL FAIL IF SHELVE NOT ALREADY PRESENT...
                self.seqLenDict=shelve.open(filepath+'.seqlen','r')
            except anydbm.error: # READ ALL SEQ LENGTHS, STORE IN PERSIST DICT
                self.seqLenDict=shelve.open(filepath+'.seqlen') # OPEN IN DEFAULT "CREATE" MODE
                ifile,idFilter=self.raw_fasta_stream()
                print 'Building sequence length index...'
                store_seqlen_dict(self.seqLenDict,ifile,idFilter)
                ifile.close()
                self.seqLenDict.close() # FORCE IT TO WRITE DATA TO DISK
                self.seqLenDict=shelve.open(filepath+'.seqlen','r') # REOPEN IT READ-ONLY
        # CHECK WHETHER BLAST INDEX FILE IS PRESENT...
        if not os.access(filepath+'.nsd',os.R_OK) \
               and not os.access(filepath+'.psd',os.R_OK):
            # ATTEMPT TO BUILD BLAST DATABASE & INDEXES
            cmd='formatdb -i %s -o T' % filepath
            if self._seqtype!=PROTEIN_SEQTYPE:
                cmd += ' -p F' # SPECIAL FLAG REQUIRED FOR NUCLEOTIDE SEQS
            print 'Building index:',cmd
            if os.system(cmd)!=0: # BAD EXIT CODE, SO COMMAND FAILED
                raise OSError('command %s failed' % cmd)

    def set_seqtype(self):
        "Determine whether this database is DNA or protein"
        if os.path.isfile(self.filepath+'.psd'):
            self._seqtype=PROTEIN_SEQTYPE
        elif os.path.isfile(self.filepath+'.nsd'):
            self._seqtype=DNA_SEQTYPE
        else:
            ofile=file(self.filepath) # READ ONE SEQUENCE TO CHECK ITS TYPE
            for id,title,seq in read_fasta(ofile,onlyReadOneLine=True):
                self._seqtype=guess_seqtype(seq) # RECORD PROTEIN VS. DNA...
                break # JUST READ ONE SEQUENCE
            ofile.close()

    def raw_fasta_stream(self):
        'return a stream of fasta-formatted sequences, and ID filter function if needed'
        try: # DEFAULT: JUST READ THE FASTA FILE, IF IT EXISTS
            return file(self.filepath),None
        except IOError: # TRY READING FROM FORMATTED BLAST DATABASE
            cmd='fastacmd -D -d '+self.filepath
            return os.popen(cmd),lambda id:id.split('|')[1] #BLAST ADDS lcl| TO id

    def __iter__(self):
        'generate all IDs in this database'
        for id in self.seqLenDict:
            yield id

    def __len__(self):
        "number of total entries in this database"
        return len(self.seqLenDict)

    def __hash__(self): # TO ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...
        return id(self)

    def __getitem__(self,id):
        "Get sequence matching this ID, using dict as local cache"
        try:
            return dict.__getitem__(self,id)
        except KeyError: # NOT FOUND IN DICT, SO CREATE A NEW OBJECT
            s=self.seqClass(self,id)
            s.db=self # LET IT KNOW WHAT DATABASE IT'S FROM...
            dict.__setitem__(self,id,s) # CACHE IT
            return s

    def blast(self,seq,al=None,blastpath='blastall',
              blastprog=None,expmax=0.001,maxseq=None):
        "Run blast search for seq in database, return aligned intervals"
        if blastprog is None:
            blastprog=blast_program(seq.seqtype(),self._seqtype)
        cmd='%s -d %s -p %s -e %e'  %(blastpath,self.filepath,
                                      blastprog,float(expmax))
        return process_blast(cmd,seq,self,al)

    def megablast(self,seq,al=None,blastpath='megablast',expmax=1e-20,
                  maxseq=None,minIdentity=None,maskOpts='-U T -F m',rmOpts=''):
        "Run megablast search with repeat masking."
        masked_seq=repeat_mask(seq,opts=rmOpts)  # MASK REPEATS TO lowercase
        cmd='%s %s -d %s -D 2 -e %e -i stdin' % (blastpath,maskOpts,self.filepath,float(expmax))
        if maxseq is not None:
            cmd+=' -v %d' % maxseq
        if minIdentity is not None:
            cmd+=' -p %f' % float(minIdentity)
        return process_blast(cmd,seq,self,al,seqString=masked_seq)

class StoredPathMapping(PathMapping):
    _edgeClass=BlastHitInfo
    def __init__(self,table,srcSet,destSet,edgeClass=None):
        PathMapping.__init__(self)
        self.table=table
        self.srcSet=srcSet
        self.destSet=destSet
        if edgeClass is not None:
            self._edgeClass=edgeClass

    def __getitem__(self,p):
        "Get mapping of a path, using stored table if necessary"
        try: # RETURN STORED MAPPING
            return PathMapping.__getitem__(self,p)
        except KeyError: # TRY TO GET IT FROM THE STORED TABLE
            for ival in self.table[p.path.id]: # READ INTERVAL MAPPINGS ONE BY ONE
                save_interval_alignment(self,ival,self.srcSet,self.destSet,
                                        self._edgeClass) # SAVE IT
            return PathMapping.__getitem__(self,p) # RETURN TOTAL RESULT

    def all_paths(self):
        "Get all source sequences in this mapping"
        for id in self.table:
            p=self.srcSet[id]
            yield p

    # NEED TO ADD APPROPRIATE HOOKS FOR __iter__, items(), ETC.



class VirtualSeq(SeqPath):
    """Empty sequence object acts purely as a reference system.
    Automatically elongates if slice extends beyond current end."""
    def __init__(self,id,length=1):
        SeqPath.__init__(self,self,0,length)
        self.id=id
    def __getitem__(self,k):
        "Elongate if slice extends beyond current self.end"
        if isinstance(k,types.SliceType):
            if k.stop>self.end:
                self.end=k.stop
        return SeqPath.__getitem__(self,k)
    def strslice(self,start,end):
        "NO sequence access!  Raise an exception."
        raise ValueError('VirtualSeq has no actual sequence')

class VirtualSeqDB(dict):
    "return a VirtualSeq for any ID requested"
    def __getitem__(self,k):
        try: # IF WE ALREADY CREATED A SEQUENCE FOR THIS ID, RETURN IT
            return dict.__getitem__(self,k)
        except KeyError: # CREATE A VirtualSeq FOR THIS NEW ID
            s=VirtualSeq(k)
            self[k]=s
            return s


class TempMAFIntervalDict(object):
    "placeholder for generating edges that map a given interval to its targets"
    def __init__(self,map,ival):
        self.map=map
        self.ival=ival
    def edges(self):
        "get all mappings of this interval"
        return self.map.edges(self.ival)

def MAF_get_interval(seq,start,end,ori):
    "Alex's reverse intervals are shifted by one, so correct them..."
    if ori== -1:
        return get_interval(seq,start-1,end-1,ori)
    else:
        return get_interval(seq,start,end,ori)

class MAFStoredPathMapping(PathMapping):
    def __init__(self,ival,table,dbset,vdbset=None):
        """Load all alignments that overlap ival, from the database table,
        using dbset as the interface to all of the sequences.
        """
        if vdbset is None: # CREATE A VIRTUAL SEQ DB FOR REFERENCE SEQUENCES
            vdbset=VirtualSeqDB()
        PathMapping.__init__(self)
        self.ival=ival
        self.table=table
        self.dbset=dbset
        vseqs={}
        self.vseqs=vseqs
        id=dbset.getName(ival.path)
        for i in table.select('where src_id=%s and src_start<%s and src_end>%s',
                              (id,ival.end,ival.start)):  # SAVE MAPPING TO vdbset
            save_interval_alignment(self,i,dbset,vdbset,None,MAF_get_interval)
            vseqs[i.dest_id]=None # KEEP TRACK OF ALL OUR VIRTUAL SEQUENCES...
        for vseqID in vseqs: # GET EVERYTHING THAT OUR vseqs MAP TO...
            for i in table.select('where src_id=%s',(vseqID,)): # SAVE MAPPING TO dbset
                if i.src_id==vseqID: # FILTER OUT MYSQL'S CASE-INSENSITIVE MATCHES!!!
                    save_interval_alignment(self,i,vdbset,dbset,None,MAF_get_interval)

    def __getitem__(self,k):
        return TempMAFIntervalDict(self,k)

    def edges(self,ival=None):
        "get all mappings of self.ival, as edges"
        if ival is None:
            ival=self.ival
        for e in PathMapping.__getitem__(self,ival).edges():
            for e2 in PathMapping.__getitem__(self,e.destPath).edges():
                if ival!=e2.destPath: # IGNORE SELF-MATCH
                    yield IntervalTransform(e.reverse(e2.srcPath),e2.destPath)


class PrefixUnionDict(object):
    """union interface to a series of dicts, each assigned a unique prefix
       ID 'foo.bar' --> ID 'bar' in dict f asociated with prefix 'foo'."""
    def __init__(self,prefixDict,separator='.'):
        self.separator=separator
        self.prefixDict=prefixDict
        d={}
        for k,v in prefixDict.items():
            d[v]=k # CREATE A REVERSE MAPPING
        self.dicts=d

    def __getitem__(self,k):
        "for ID 'foo.bar', return item 'bar' in dict f associated with prefix 'foo'"
        (prefix,id) =k.split(self.separator)
        return self.prefixDict[prefix][id]

    def __iter__(self):
        "generate union of all dicts items, each with appropriate prefix."
        for p,d in self.prefixDict.items():
            for id in d:
                yield p+self.separator+id

    def getName(self,path):
        "return fully qualified ID i.e. 'foo.bar'"
        return self.dicts[path.db]+self.separator+path.id
