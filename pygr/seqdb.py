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
    seq_id_counter += 1
    return seq_id_counter-1


def write_fasta(ofile,s,chunk=60):
    "Trivial FASTA output"
    try:
        id=s.id
    except AttributeError:
        id=new_seq_id()
        s.id=id
    ofile.write('>'+str(id)+'\n')
    seq=str(s)
    end=len(seq)
    pos=0
    while 1:
        ofile.write(seq[pos:pos+chunk]+'\n')
        pos += chunk
        if pos>=end:
            break

def read_fasta(ifile):
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


class BlastDB(dict):
    "Container representing Blast database"
    def __init__(self,filepath):
        "format database and build indexes if needed"
        self.filepath=filepath
        dict.__init__(self)
        ofile=file(filepath) # READ ONE SEQUENCE TO CHECK ITS TYPE
        for id,title,seq in read_fasta(ofile):
            self._seqtype=guess_seqtype(seq) # RECORD PROTEIN VS. DNA...
            break # JUST READ ONE SEQUENCE
        ofile.close()
        try: # CHECK WHETHER BLAST INDEX FILE IS PRESENT...
            fp=file(filepath+'.psd')
        except IOError: # ATTEMPT TO BUILD BLAST DATABASE & INDEXES
            cmd='formatdb -i %s -o' % filepath
            if self._seqtype!=PROTEIN_SEQTYPE:
                cmd += ' -p F' # SPECIAL FLAG REQUIRED FOR NUCLEOTIDE SEQS
            print 'Building index:',cmd
            if os.system(cmd)!=0: # BAD EXIT CODE, SO COMMAND FAILED
                raise OSError('command %s failed' % cmd)
        else:
            fp.close()
        
    def __getitem__(self,id):
        "Get sequence matching this ID, using dict as local cache"
        try:
            return dict.__getitem__(self,id)
        except KeyError: # NOT FOUND IN DICT, SO CREATE A NEW OBJECT
            s=BlastSequence(self,id)
            dict.__setitem__(self,id,s) # CACHE IT
            return s

    def blast(self,seq,al=None,blastpath='blastall',
              blastprog=None,expmax=0.001):
        "Run blast search for seq in database, return aligned intervals"
        if blastprog==None:
            blastprog=blast_program(seq.seqtype(),self._seqtype)
        cmd='%s -d %s -p %s -e %f|parse_blast.awk -v mode=all' \
                              %(blastpath,self.filepath,blastprog,expmax)
        ifile,ofile=os.popen2(cmd)
        write_fasta(ifile,seq)
        ifile.close()
        al=read_interval_alignment(ofile,{seq.id:seq},self,al)
        if ofile.close()!=None:
            raise OSError('command %s failed' % cmd)
        return al
