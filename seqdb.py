import os
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
    if id==None:
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
    "Get one sequence at a time from stream ofile"
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




def fastacmd_seq(filepath,id,start=None,end=None):
    "Get complete sequence or slice from a BLAST formatted database"
    if start!=None: # USE ABILITY TO GRAB A SLICE OF THE SEQUENCE
        cmd='fastacmd -d %s -s %s -L %d,%d' % (filepath,id,start+1,end)
    else:
        cmd='fastacmd -d %s -s %s' % (filepath,id)
    ofile=os.popen(cmd)
    ofile.readline() # SKIP TITLE LINE
    s=''
    for line in ofile:
        for word in line.split(): # GET RID OF WHITESPACE...
            s += word
    if ofile.close()!=None:
        raise OSError('command %s failed' % cmd)
    return s


class BlastSeqDescriptor(object):
    "Get sequence from a blast formatted database for obj.id"
    def __get__(self,obj,objtype):
        return fastacmd_seq(obj.db.filepath,obj.id)

class BlastSequence(NamedSequenceBase):
    "Represents a sequence in a blast database, w/o keeping seq in memory"
    seq=BlastSeqDescriptor()
    def __init__(self,db,id):
        self.db=db
        self.id=id
        NamedSequenceBase.__init__(self)
    def strslice(self,start,end):
        "Efficient access to slice of a sequence, useful for huge contigs"
        return fastacmd_seq(self.db.filepath,self.id,start,end)

def blast_program(query_type,db_type):
    progs= {DNA_SEQTYPE:{DNA_SEQTYPE:'blastn', PROTEIN_SEQTYPE:'blastx'},
            PROTEIN_SEQTYPE:{DNA_SEQTYPE:'tblastn', PROTEIN_SEQTYPE:'blastp'}}
    if query_type==RNA_SEQTYPE:
        query_type=DNA_SEQTYPE
    if db_type==RNA_SEQTYPE:
        db_type=DNA_SEQTYPE
    return progs[query_type][db_type]


class BlastIval(TupleO):
    "Wrap a tuple with sensible attribute names for accessing the data"
    _attrcol={'hit_id':0, 'query_id':1, 'subject_id':2, 'blast_score':3, 'e_value':4,
              'percent_id':5, 'orientation':6, 'query_start':7, 'length':8, 'subject_start':9}
    def __init__(self,t):
        "Convert strings into appropriate types; adjust to zero-based indexes"
        u=(int(t[0]),t[1],t[2],int(t[3]),float(t[4]),
           int(t[5]),int(t[6]),int(t[7])-1,int(t[8]),int(t[9])-1)
        TupleO.__init__(self,u)

class BlastHitInfo(TupleO):
    _attrcol={'blast_score':0,'e_value':1,'percent_id':2}
    def repr_dict(self):
        return {'blast_score':self.data[0],'e_value':self.data[1],
                'percent_id':self.data[2]}

def read_interval_alignment(ofile,container1,container2,al=None):
    "Read tab-delimited interval mapping between seqs from the 2 containers"
    if al==None:
        al=PathMapping()
    hit_id = -1
    for line in ofile:
        t=line.split('\t')
        if t[0]=='MATCH_INTERVAL':
            ival=BlastIval(t[1:]) # WRAP TUPLE WITH SENSIBLE ATTRIBUTE NAMES
            if hit_id!=ival.hit_id:
                hitInfo=BlastHitInfo((ival.blast_score,ival.e_value,ival.percent_id))
                hit_id=ival.hit_id
            query=container1[ival.query_id]
            subject=container2[ival.subject_id]
            q_ival=query[ival.query_start:ival.query_start+ival.length]
            s_ival=subject[ival.subject_start:ival.subject_start+ival.length]
            if ival.orientation<0: # SWITCH IT TO REVERSE ORIENTATION
                s_ival = -s_ival
            al += q_ival # MAKE SURE query IS IN THE TOP LEVEL INDEX
            al[q_ival][s_ival]= hitInfo # SAVE THE ALIGNMENT AND EDGE INFO
    return al

def process_blast(cmd,seq,al=None,seqString=None):
    "run blast, pipe in sequence, pipe out aligned interval lines, return an alignment"
    ifile,ofile=os.popen2(cmd+'|parse_blast.awk -v mode=all')
    if seqString==None:
        seqString=seq
    write_fasta(ifile,seqString,id=seq.id)
    ifile.close()
    al=read_interval_alignment(ofile,{seq.id:seq},self,al)
    if ofile.close()!=None:
        raise OSError('command %s failed' % cmd)
    return al


def repeat_mask(seq,progname='RepeatMasker -xsmall'):
    'Run RepeatMasker on a sequence, return lowercase-masked string'
    temppath=os.tempnam()
    ofile=file(temppath,'w')
    write_fasta(ofile,seq)
    ofile.close()
    cmd=progname+' '+temppath
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
    def __init__(self,filepath):
        "format database and build indexes if needed"
        self.filepath=filepath
        dict.__init__(self)
        ofile=file(filepath) # READ ONE SEQUENCE TO CHECK ITS TYPE
        for id,title,seq in read_fasta(ofile,onlyReadOneLine=True):
            self._seqtype=guess_seqtype(seq) # RECORD PROTEIN VS. DNA...
            break # JUST READ ONE SEQUENCE
        ofile.close()
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
        
    def __getitem__(self,id):
        "Get sequence matching this ID, using dict as local cache"
        try:
            return dict.__getitem__(self,id)
        except KeyError: # NOT FOUND IN DICT, SO CREATE A NEW OBJECT
            s=BlastSequence(self,id)
            dict.__setitem__(self,id,s) # CACHE IT
            return s

    def blast(self,seq,al=None,blastpath='blastall',
              blastprog=None,expmax=0.001,maxseq=None):
        "Run blast search for seq in database, return aligned intervals"
        if blastprog==None:
            blastprog=blast_program(seq.seqtype(),self._seqtype)
        cmd='%s -d %s -p %s -e %e'  %(blastpath,self.filepath,
                                      blastprog,float(expmax))
        return process_blast(cmd,seq,al)

    def megablast(self,seq,al=None,blastpath='megablast',expmax=1e-20,
                  maxseq=None,minIdentity=None,maskOpts='-U T -F m'):
        "Run megablast search with repeat masking."
        masked_seq=repeat_mask(seq)  # MASK REPEATS TO lowercase
        cmd='%s %s -d %s -e %e' % (blastpath,maskOpts,self.filepath,
                                   float(expmax))
        if maxseq!=None:
            cmd+=' -v %d' % maxseq
        if minIdentity!=None:
            cmd+=' -p %f' % float(minIdentity)
        return process_blast(cmd,seq,al,seqString=masked_seq)

class StoredPathMapping(PathMapping):
    _edgeClass=BlastHitInfo
    def __init__(self,table,srcSet,destSet,edgeClass=None):
        PathMapping.__init__(self)
        self.table=table
        self.srcSet=srcSet
        self.destSet=destSet
        if edgeClass!=None:
            self._edgeClass=edgeClass

    def __getitem__(self,p):
        "Get mapping of a path, using stored table if necessary"
        try: # RETURN STORED MAPPING
            return PathMapping.__getitem__(self,p)
        except KeyError: # TRY TO GET IT FROM THE STORED TABLE
            self += p # ADD PathDict FOR THIS SEQUENCE
            edgeAttr=None # DEFAULT: NO EDGE INFORMATION
            if self._edgeClass!=None:
                for edgeAttr in self._edgeClass._attrcol: break
            for ival in self.table[p.id]:
                srcPath=p[ival.src_start:ival.src_end]
                destPath=self.destSet[ival.dest_id][ival.dest_start:ival.dest_end]
                if edgeAttr!=None and hasattr(ival,edgeAttr):
                    ei=len(self._edgeClass._attrcol)*[None] # RIGHT LENGTH LIST
                    for a,i in self._edgeClass._attrcol.items():
                        ei[i]=getattr(ival,a) # CONSTRUCT ATTRS IN RIGHT ORDER
                    self[srcPath][destPath]=self._edgeClass(ei) # SAVE EDGE
                else:
                    self[srcPath]=destPath # SAVE ALIGNMENT W/O EDGE INFO
            return PathMapping.__getitem__(self,p)

    def all_paths(self):
        "Get all source sequences in this mapping"
        for id in self.table:
            p=self.srcSet[id]
            yield p

    # NEED TO ADD APPROPRIATE HOOKS FOR __iter__, items(), ETC.
