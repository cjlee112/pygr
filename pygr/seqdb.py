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


class BlastIval(TupleO):
    "Wrap a tuple with sensible attribute names for accessing the data"
    _attrcol={'hit_id':0, 'query_id':1, 'subject_id':2, 'blast_score':3, 'e_value':4,
              'percent_id':5, 'orientation':6, 'query_start':7, 'length':8, 'subject_start':9}
    def __init__(self,t):
        "Convert strings into appropriate types; adjust to zero-based indexes"
        u=(int(t[0]),t[1],t[2],int(t[3]),float(t[4]),
           int(t[5]),int(t[6]),int(t[7])-1,int(t[8]),int(t[9])-1)
        TupleO.__init__(self,u)




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

class BlastDB(dict):
    "Container representing Blast database"
    def __init__(self,filepath):
        self.filepath=filepath
        dict.__init__(self)

    def __getitem__(self,id):
        "Get sequence matching this ID, using dict as local cache"
        try:
            return dict.__getitem__(self,id)
        except KeyError: # NOT FOUND IN DICT, SO CREATE A NEW OBJECT
            s=BlastSequence(self,id)
            dict.__setitem__(self,id,s) # CACHE IT
            return s

    def __mul__(self,seq):
        "Run blast search for seq in database, return aligned intervals"
        blastpath='blastall'
        blastprog='blastp'
        expmax=0.001
        cmd='%s -d %s -p %s -e %f|parse_blast.awk -v mode=all' \
                              %(blastpath,self.filepath,blastprog,expmax)
        ifile,ofile=os.popen2(cmd)
        write_fasta(ifile,seq)
        ifile.close()
        m=PathMapping()
        for line in ofile:
            t=line.split('\t')
            if t[0]=='MATCH_INTERVAL':
                ival=BlastIval(t[1:]) # WRAP TUPLE WITH SENSIBLE ATTRIBUTE NAMES
                subject=self[ival.subject_id]
                q_ival=seq[ival.query_start:ival.query_start+ival.length]
                s_ival=subject[ival.subject_start:ival.subject_start+ival.length]
                if ival.orientation<0: # SWITCH IT TO REVERSE ORIENTATION
                    s_ival = -s_ival
                m[q_ival]=s_ival # SAVE THE ALIGNMENT
        if ofile.close()!=None:
            raise OSError('command %s failed' % cmd)
        return m
