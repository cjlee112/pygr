import time
from MySQLdb import *
from splicegraph import *

db=Connection('lldb','reader','hedgehog')
cursor=db.cursor()
print 'Reading database schema...'
idDict={}
tables=describeDBTables('HUMAN_SPLICE_03',cursor,idDict)
jun03=suffixSubset(tables,'JUN03') # SET OF TABLES ENDING IN JUN03
idDict=indexIDs(jun03) # CREATE AN INDEX OF THEIR PRIMARY KEYS

# LOAD DATA & BUILD THE SPLICE GRAPH
(clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,
 alt3Graph,mrna,protein,mrna_protein)=loadSpliceGraph(jun03,
                                       'HUMAN_SPLICE_03.cluster_JUN03',
                                       'HUMAN_SPLICE_03.exon_formJUN03',
                                       'HUMAN_SPLICE_03.splice_verification_JUN03',
                                       'HUMAN_SPLICE_03.genomic_cluster_JUN03',
                                       'HUMAN_SPLICE_03.mrna_seqJUN03',
                                       'HUMAN_SPLICE_03.protein_seqJUN03')


# OLD STYLE QUERIES
# 'OLD STYLE' MEANS YESTERDAY NIGHT...

print 'Searching for exonskips...'
exonskips=[]
startTime=time.time()
for e1 in spliceGraph:
    for e2 in e1.next:
        for e3 in e2.next:
            if e3 in e1.next:
                exonskips.append((e1,e2,e3))
print 'Found:%d\t%.2f sec\n' % (len(exonskips),time.time()-startTime)


print 'Searching for altskips...'
altskips=[]
startTime=time.time()
for e1 in alt5Graph:
    for e1b in e1.alt5:
        for e2 in e1b.next:
            for e3 in e2.next:
                if e3 in e1.next:
                    altskips.append((e1,e1b,e2,e3))
print 'Found:%d\t%.2f sec\n' % (len(altskips),time.time()-startTime)

print 'Searching for U11/U12 alt5skips...'
u12skips=[]
startTime=time.time()
for e1 in alt5Graph:
    for e1b in e1.alt5:
        for e2,s in e1b.next.items():
            if s.type=='U11/U12':
                for e3 in e2.next:
                    if e3 in e1.next:
                        u12skips.append((e1,e1b,e2,e3))
print 'Found:%d\t%.2f sec\n' % (len(u12skips),time.time()-startTime)


print 'Searching for alt5skips w/ U11/U12 as e2->e3 splice...'
u12bskips=[]
startTime=time.time()
for e1 in alt5Graph:
    for e1b in e1.alt5:
        for e2 in e1b.next:
            for e3,s in e2.next.items():
                if s.type=='U11/U12' and e3 in e1.next:
                    u12bskips.append((e1,e1b,e2,e3))
print 'Found:%d\t%.2f sec\n' % (len(u12bskips),time.time()-startTime)


print 'Searching for U11/U12 alt3skips...'
u12cskips=[]
startTime=time.time()
for e1 in spliceGraph:
    for e2 in e1.next:
        for e3,s in e2.next.items():
            if s.type=='U11/U12' and hasattr(e3,'alt3'):
                for e3b in e3.alt3:
                    if e3b in e1.next:
                        u12cskips.append((e1,e2,e3,e3b))
print 'Found:%d\t%.2f sec\n' % (len(u12cskips),time.time()-startTime)



print 'Searching for U11/U12 nested splices...'
nestedSplices=[]
startTime=time.time()
for e1 in alt5Graph:
    for e1b in e1.alt5:
        for e2b,s in e1b.next.items():
            if s.type=='U11/U12' and hasattr(e2b,'alt3'):
                for e2 in e2b.alt3:
                    if e2 in e1.next:
                        nestedSplices.append((e1,e1b,e2b,e2))
print 'Found:%d\t%.2f sec\n' % (len(nestedSplices),time.time()-startTime)


print 'Searching for U11/U12 intron retentions...'
intronRetentions=[]
startTime=time.time()
for e1 in spliceGraph:
    if hasattr(e1,'alt5') and hasattr(e1,'alt3'):
        for e1b in e1.alt5:
            for e2b in e1.alt3:
                try:
                    s=e1b.next[e2b]
                    if s.consensus_site=='YES': # and s.type=='U11/U12':
                        intronRetentions.append((e1,e1b,e2b))
                except KeyError:
                    pass
print 'Found:%d\t%.2f sec\n' % (len(intronRetentions),time.time()-startTime)



# path query examples: to make this work, let's force spliceGraph to use path query wrapper interface
from pathquery import *
spliceGraph.__class__=PathQueryDictGraph
alt5Graph.__class__=PathQueryDictGraph

# example exon skip query
l=[o for o in spliceGraph.next.next.filter(lambda p:p[2] in p[0].next)]
print len(l)

# same thing, but using graph join syntax
l=[o for o in (spliceGraph>>spliceGraph>>spliceGraph).filter(lambda p:p[2] in spliceGraph[p[0]])]
print len(l)


# example U11/U12 alt5 skip
l=[o for o in alt5Graph.alt5.next.next.filter(lambda p: p[3] in p[0].next
                                         and p.edge[2].type=='U11/U12')]
print len(l)

# example U11/U12 alt3 skip
l=[o for o in spliceGraph.next.next.filter(lambda p: p.edge[2].type=='U11/U12'
                                           and hasattr(p[2],'alt3'))
   .alt3.filter(lambda p:p[4] in p[0].next)]
print len(l)
