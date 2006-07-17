from pygr.graphquery import *
from lldb_jan06 import *
import sys, os, string, time

def loadTestJAN06(loadAll=False):
    "Test loading the JUN03 splice graph data"
    return getSpliceGraphFromDB(spliceCalcs['hg17_JAN06'],loadAll)


def forLoopTests(spliceGraph,alt5Graph):
    "run some queries written out as nested for-loops"
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

def graphQueryTests(spliceGraph,alt5Graph):
    "example u11/12 alt5 graph query"
    #queryGraph={0:{2:dict(filter=lambda edge,**kw:edge.type=="U11/U12"),
    #               1:dict(dataGraph=alt5Graph)}, 1:{3:None}, 2:{3:None},3:{}}
    queryGraph={0:{2:{'filter':lambda edge,**kw:edge.type=="U11/U12"},
                   1:{'dataGraph':alt5Graph}}, 1:{3:None}, 2:{3:None},3:{}}

    for d in GraphQuery(spliceGraph, queryGraph):
        print d[0].id,d[0,2].id

def doTests():
    "run all the tests on JAN06 data"
    (clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
     clusterExons,clusterSplices)=loadTestJAN06(True)
    forLoopTests(spliceGraph,alt5Graph)
    graphQueryTests(spliceGraph,alt5Graph)

if __name__ == "__main__":
    doTests()

