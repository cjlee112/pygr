import time
from lldb_jan06 import *
from pygr.poa import *

cursor=getUserCursor('SPLICE_JAN06')
print 'Reading database schema...'
idDict={}
tables=describeDBTables('SPLICE_JAN06',cursor,idDict)
jan06=suffixSubset(tables,'hg17') # SET OF TABLES ENDING IN JUN03
idDict=indexIDs(jan06) # CREATE AN INDEX OF THEIR PRIMARY KEYS

g=jan06['SPLICE_JAN06.genomic_cluster_hg17']
g.objclass(SQLSequence)

mrna=jan06['SPLICE_JAN06.isoform_mrna_seq_hg17']
mrna.objclass(SQLSequence) # FORCE mRNA SEQ TABLE TO USE TRANSPARENT ACCESS

protein=jan06['SPLICE_JAN06.isoform_protein_seq_hg17']
protein.objclass(SQLSequence) # FORCE PROTEIN SEQ TABLE TO USE TRANSPARENT ACCESS
protein.addAttrAlias(seq='protein_seq') # ALIAS protein_seq TO APPEAR AS seq

c=g['Hs.78788']
c1=c[10:20]
print c,c1

m1=mrna[1]
p1=protein[1]
print m1,p1
