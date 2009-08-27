
import MySQLdb
from pygr.seqdb import *

sp=BlastDB('sp') # OPEN SWISSPROT BLAST DB
s=Sequence(str(sp['CYGB_HUMAN'][40:-40]),'boo')

db=MySQLdb.Connection(db='test',read_default_file=os.environ['HOME']+'/.my.cnf')
cursor=db.cursor()
t=SQLTableMultiNoCache('test.mytable',cursor)
t._distinct_key='src_id'

m=StoredPathMapping(t,{'boo':s},sp)
for i in m[s].edges(): # SHOW ALL ALIGNMENTS TO s
    print repr(i.srcPath),repr(i.destPath),i.blast_score

myg=sp['MYG_CHICK']
for i in m[s][myg]: # SHOW ALIGNMENT OF s AND myg
    print repr(i.srcPath),repr(i.destPath),i.blast_score
