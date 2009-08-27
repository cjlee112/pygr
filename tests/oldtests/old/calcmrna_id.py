import sys
from test import *
(clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
 clusterExons,clusterSplices)=getSpliceGraphFromDB(spliceCalcs['HUMAN_SPLICE'])
db=BlastDB('/usr/tmp/Hs_mrna_mar05',True)


somelist=[splices[int(line)] for line in sys.stdin]
for s in somelist:
    c=clusters[s.cluster_id]
    loadCluster(c,exons,splices,clusterExons,clusterSplices,spliceGraph,alt5Graph,alt3Graph)
    try:
        seq=str(s.exons[0])[-100:]+str(s.exons[1])[:100] # UP TO 100nt FROM EACH EXON
    except KeyError:
        continue
    n=Sequence(seq,'0')
    m=db.blast(n)
    dm=m.seq_dict()
    try:
        it=dm[n].items()
    except KeyError:
        continue
    nlength=len(n)
    for dest,az in it:
        match=az.percent_id(nlength)
        if match>=0.99:
            print '%s\t%d\t%s\t%2.1f' %(s.cluster_id,s.id,dest.id,100*match)

