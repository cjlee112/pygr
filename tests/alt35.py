
## from maftest import *
from pygr.apps.leelabdb import *

def printResults(prefix,msa,site,altID=None,cluster_id=None,dbUnion=None):
    edges=msa[site].edges(mergeMost=True)
    for src,dest,e in edges:
        print '%s\t%s\t%s\t%s\t%2.1f\t%2.1f\t%s\t%s' \
              %(altID,cluster_id,prefix,dbUnion.dicts[dest.pathForward.db],
                100.*e.pIdentity(),100.*e.pAligned(),src[:2],dest[:2])

def getSSMap(msa,ss1,ss2,ss3,e1,e2,**kwargs):
    zone=e1+ss3 # LET CACHE KNOW WE NEED ALL ALIGNMENTS OF zone
    cache=msa[zone].keys(mergeMost=True)
    printResults('ss1',msa,ss1,**kwargs)
    printResults('ss2',msa,ss2,**kwargs)
    printResults('ss3',msa,ss3,**kwargs)
    printResults('e1',msa,e1,**kwargs)
    printResults('e2',msa,e2,**kwargs)

# USE THIS FOR HUMAN_SPLICE_03 DATA
(clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
 clusterExons,clusterSplices)=getSpliceGraphFromDB(spliceCalcs['HUMAN_SPLICE_03'], loadAll=False) # GET OUR USUAL SPLICE GRAPH
def getClusterMappingJUN03(hg17):
    ct=SQLTableMultiNoCache('GENOME_ALIGNMENT.hg17_cluster_JUN03',clusters.cursor)
    ct._distinct_key='src_id'
    cm=StoredPathMapping(ct,genomic_seq,hg17) # MAPPING OF OUR CLUSTER GENOMIC ONTO hg17
    return cm

from pygr.mapping import listUnion
def getAlt5Conservation(msa,cm,cluster_id,start1,start2,stop,**kwargs):
    gene=genomic_seq[cluster_id] # BARMAK'S GENOMIC FRAGMENT
    ss1=listUnion(cm[gene[start1-2:start1]]) # SPLICE SITES ON hg17
    ss2=listUnion(cm[gene[start2-2:start2]])
    ss3=listUnion(cm[gene[stop:stop+2]])
    e1=ss1+ss2 # GET INTERVAL BETWEEN PAIR OF SPLICE SITES
    e2=listUnion(cm[gene[max(start1,start2):stop]])
    getSSMap(msa,ss1,ss2,ss3,e1,e2,cluster_id=cluster_id,**kwargs)

def getAlt3Conservation(msa,cm,cluster_id,start,stop1,stop2,**kwargs):
    gene=genomic_seq[cluster_id] # BARMAK'S GENOMIC FRAGMENT
    ss1=listUnion(cm[gene[stop1:stop1+2]]) # SPLICE SITES ON hg17
    ss2=listUnion(cm[gene[stop2:stop2+2]])
    ss3=listUnion(cm[gene[start-2:start]])
    e1=ss1+ss2 # GET INTERVAL BETWEEN PAIR OF SPLICE SITES
    e2=listUnion(cm[gene[start:min(stop1,stop2)]])
    getSSMap(msa,ss1,ss2,ss3,e1,e2,cluster_id=cluster_id,**kwargs)


def getAlt5Conservation2(msa,gene,start1,start2,stop,**kwargs):
    ss1=gene[start1-2:start1] # SPLICE SITES ON hg17
    ss2=gene[start2-2:start2]
    ss3=gene[stop:stop+2]
    e1=ss1+ss2 # GET INTERVAL BETWEEN PAIR OF SPLICE SITES
    e2=gene[max(start1,start2):stop]
    getSSMap(msa,ss1,ss2,ss3,e1,e2,**kwargs)

def getAlt3Conservation2(msa,gene,start,stop1,stop2,**kwargs):
    ss1=gene[stop1:stop1+2] # SPLICE SITES ON mm5
    ss2=gene[stop2:stop2+2]
    ss3=gene[start-2:start]
    e1=ss1+ss2 # GET INTERVAL BETWEEN PAIR OF SPLICE SITES
    e2=gene[start:min(stop1,stop2)]
    getSSMap(msa,ss1,ss2,ss3,e1,e2,**kwargs)

def splice_genomic_may05(mm5):
    cursor=getUserCursor('MOUSE_SPLICE_03')
    t=SQLTable('splice_genomic_may05',cursor)
    return SliceDB(t,mm5) # APPLY SLICES OF t TO SEQUENCES OF mm5


if __name__=='__main__':
    from pygr import cnestedlist
    CHRDB=cnestedlist.NLMSA('/usr/tmp/ucscDB/mafdb','r')
    genomeUnion=CHRDB.seqDict
    #genomic_seq=splice_genomic_may05(genomeUnion.prefixDict['mm5'])
    cluster_map=getClusterMappingJUN03(genomeUnion.prefixDict['hg17'])
    import sys
    for line in sys.stdin:
        args=line.split()
        cluster_id=args[1]
        #gene=genomic_seq[cluster_id] # BARMAK'S GENOMIC FRAGMENT
        try:
##             getAlt5Conservation2(CHRDB,gene,int(args[3])-1,
##                                  int(args[5])-1,int(args[6]),
##                                  cluster_id=cluster_id,
##                                  altID=args[0],dbUnion=genomeUnion)
##             getAlt3Conservation2(CHRDB,genomic_seq,args[1],int(args[2])-1,
##                                  int(args[4]),int(args[6]),args[0])
##             getAlt3Conservation(CHRDB,cluster_map,cluster_id,
##                                 int(args[2])-1,int(args[4]),
##                                 int(args[6]),altID=args[0],dbUnion=genomeUnion)
            getAlt5Conservation(CHRDB,cluster_map,cluster_id,
                                int(args[3])-1,int(args[5])-1,
                                int(args[6]),altID=args[0],dbUnion=genomeUnion)
        except:
            print 'ERROR: SKIPPED',args[0],args[1]
    #getExonConservation(CHRDB,'Hs.99736',10426,9234,10546)
