
from __future__ import generators
from pygr.leelabdb import *
import pygr.coordinator

def map_clusters(server,**kwargs):
    "map clusters one by one"
    hg17=BlastDB(ifile=server.open_resource('hg17','r')) # CONSTRUCT RESOURCE FOR US IF NEEDED
    # LOAD DB SCHEMA
    (clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
     clusterExons,clusterSplices)=getSpliceGraphFromDB(spliceCalcs['HUMAN_SPLICE'])
    for cluster_id in server:
        g=genomic_seq[cluster_id]
        m=hg17.megablast(g,maxseq=1,minIdentity=98) # MASK, BLAST, READ INTO m
        # SAVE ALIGNMENT m TO DATABASE TABLE test.mytable USING cursor
        createTableFromRepr(m.repr_dict(),
                            'GENOME_ALIGNMENT.hg17_cluster_jan02',
                            clusters.cursor,
                            {'src_id':'varchar(12)','dest_id':'varchar(12)'})
        yield cluster_id # WE MUST FUNCTION AS GENERATOR

def serve_clusters():
    "serve up cluster_id one by one"
    cursor=getUserCursor('HUMAN_SPLICE')
    t=SQLTable('HUMAN_SPLICE.genomic_cluster_jan02',cursor)
    for id in t:
        yield id

if __name__=='__main__':
    coordinator.start_client_or_server(map_clusters,serve_clusters,['hg17'],__file__)
