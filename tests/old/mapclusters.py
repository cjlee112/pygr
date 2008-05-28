
from test import *
import idservice

hg17=BlastDB(localCopy('/usr/tmp/ucsc_msa/hg17','gunzip -c /data/yxing/databases/ucsc_msa/human_assembly_HG17/*.fa.gz >%s')) # OPEN OUR BLAST DATABASE
(clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
 clusterExons,clusterSplices)=loadTestJUN03() # LOAD DB SCHEMA

server=idservice.IDClient('http://leelab.mbi.ucla.edu:8888')
for cluster_id in server:
    print cluster_id
    try:
        g=genomic_seq[cluster_id]
        m=hg17.megablast(g,maxseq=1,minIdentity=98) # MASK, BLAST, READ INTO m
        # SAVE ALIGNMENT m TO DATABASE TABLE test.mytable USING cursor
        createTableFromRepr(m.repr_dict(),
                            'GENOME_ALIGNMENT.hg17_cluster_JUN03',
                            clusters.cursor,
                            {'src_id':'varchar(12)','dest_id':'varchar(12)'})
    except: # TRAP ALL EXCEPTIONS AND KEEP GOING
        pass
