
from pygr.seqdb import *

db=BlastDB('sp') # OPEN SWISSPROT BLAST DB
s=Sequence(str(db['CYGB_HUMAN'][40:-40]),'boo')
m=db.blast(s) # DO BLAST SEARCH
myg=db['MYG_CHICK']
for i in m[s][myg]:
    print repr(i.srcPath),repr(i.destPath),i.blast_score,i.percent_id
