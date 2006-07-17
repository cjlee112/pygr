
from __future__ import generators
from pygr.leelabdb import *
import pygr.coordinator

def map_clusters(server,genome_rsrc='hg17',dbname='HUMAN_SPLICE_03',
                 result_table='GENOME_ALIGNMENT.hg17_cluster_JUN03_all',
                 rmOpts='',**kwargs):
    "map clusters one by one"
    # CONSTRUCT RESOURCE FOR US IF NEEDED
    genome=BlastDB(ifile=server.open_resource(genome_rsrc,'r'))
    # LOAD DB SCHEMA
    (clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
     clusterExons,clusterSplices)=getSpliceGraphFromDB(spliceCalcs[dbname])
    for cluster_id in server:
        g=genomic_seq[cluster_id]
        m=genome.megablast(g,maxseq=1,minIdentity=98,rmOpts=rmOpts) # MASK, BLAST, READ INTO m
        # SAVE ALIGNMENT m TO DATABASE TABLE test.mytable USING cursor
        createTableFromRepr(m.repr_dict(),result_table,clusters.cursor,
                            {'src_id':'varchar(12)','dest_id':'varchar(12)'})
        yield cluster_id # WE MUST FUNCTION AS GENERATOR

def serve_clusters(dbname='HUMAN_SPLICE_03',
                   source_table='HUMAN_SPLICE_03.genomic_cluster_JUN03',**kwargs):
    "serve up cluster_id one by one"
    cursor=getUserCursor(dbname)
    t=SQLTable(source_table,cursor)
    for id in t:
        yield id

if __name__=='__main__':
    coordinator.start_client_or_server(map_clusters,serve_clusters,['hg17'],__file__)
