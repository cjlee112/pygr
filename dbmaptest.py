
import MySQLdb
from seqdb import *

sp=BlastDB('sp') # OPEN SWISSPROT BLAST DB
s=NamedSequence(str(sp['CYGB_HUMAN'][40:-40]),'boo')

db=MySQLdb.Connection('localhost','test','hedgehog')
cursor=db.cursor()
t=SQLTableMultiNoCache('test.mytable',cursor)
t._distinct_key='src_id'

m=StoredPathMapping(t,{'boo':s},sp)
for i in m[s].edges(): # SHOW ALL ALIGNMENTS TO s
    print repr(i.srcPath),repr(i.destPath),i.blast_score

myg=sp['MYG_CHICK']
for i in m[s][myg]: # SHOW ALIGNMENT OF s AND myg
    print repr(i.srcPath),repr(i.destPath),i.blast_score
