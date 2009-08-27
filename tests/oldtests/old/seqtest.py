import time
from pygr.apps.leelabdb import *
from pygr.poa import *

cursor=getUserCursor('HUMAN_SPLICE_03')
print 'Reading database schema...'
idDict={}
tables=describeDBTables('HUMAN_SPLICE_03',cursor,idDict)
jun03=suffixSubset(tables,'JUN03') # SET OF TABLES ENDING IN JUN03
idDict=indexIDs(jun03) # CREATE AN INDEX OF THEIR PRIMARY KEYS

g=jun03['HUMAN_SPLICE_03.genomic_cluster_JUN03']
g.objclass(SQLSequence)

mrna=jun03['HUMAN_SPLICE_03.mrna_seqJUN03']
mrna.objclass(SQLSequence) # FORCE mRNA SEQ TABLE TO USE TRANSPARENT ACCESS

protein=jun03['HUMAN_SPLICE_03.protein_seqJUN03']
protein.objclass(SQLSequence) # FORCE PROTEIN SEQ TABLE TO USE TRANSPARENT ACCESS
protein.addAttrAlias(seq='protein_seq') # ALIAS protein_seq TO APPEAR AS seq

c=g['Hs.1162']
c1=c[10:20]
print c,c1

m1=mrna[3]
p1=protein[3]
print m1,p1
