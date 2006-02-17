
from test import *
from pygr.apps.leelabdb import *
from pygr import cnestedlist

# GET CONNECTIONS TO ALL OUR GENOMES
hg17=BlastDB(localCopy('/usr/tmp/ucsc_msa/hg17','gunzip -c /data/yxing/databases/ucsc_msa/human_assembly_HG17/*.fa.gz >%s'))
mm5=BlastDB(localCopy('/usr/tmp/ucsc_msa/mm5','unzip -p /data/yxing/databases/ucsc_msa/MouseMM5/chromFa.zip >%s'))
rn3=BlastDB(localCopy('/usr/tmp/ucsc_msa/rn3','unzip -p /data/yxing/databases/ucsc_msa/RatRn3/chromFa.zip >%s'))
cf1=BlastDB(localCopy('/usr/tmp/ucsc_msa/cf1','unzip -p /data/genome/ucsc_msa/canFam1/chromFa.zip >%s'))
dr1=BlastDB(localCopy('/usr/tmp/ucsc_msa/dr1','unzip -p /data/genome/ucsc_msa/danRer1/chromFa.zip >%s'))
fr1=BlastDB(localCopy('/usr/tmp/ucsc_msa/fr1','unzip -p /data/genome/ucsc_msa/fr1/chromFa.zip >%s'))
gg2=BlastDB(localCopy('/usr/tmp/ucsc_msa/gg2','unzip -p /data/yxing/databases/ucsc_msa/galGal2/chromFa.zip >%s'))
pt1=BlastDB(localCopy('/usr/tmp/ucsc_msa/pt1','unzip -p /data/yxing/databases/ucsc_msa/chimp_pantro1/chromFa.zip >%s'))

genomes={'hg17':hg17,'mm5':mm5, 'rn3':rn3, 'canFam1':cf1, 'danRer1':dr1, 'fr1':fr1,
         'galGal2':gg2, 'panTro1':pt1} # PREFIX DICTIONARY FOR THE UNION OF ALL OUR GENOMES
genomeUnion=PrefixUnionDict(genomes) # GIVES ACCESS TO ID FORMAT 'panTro1.chr7'
for db in genomes.values(): # FORCE ALL OUR DATABASES TO USE INTERVAL CACHING
    db.seqClass=BlastSequenceCache

(clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
 clusterExons,clusterSplices)=getSpliceGraphFromDB(spliceCalcs['HUMAN_SPLICE_03'], loadAll=False) # GET OUR USUAL SPLICE GRAPH
ct=SQLTableMultiNoCache('GENOME_ALIGNMENT.hg17_cluster_JUN03',clusters.cursor)
ct._distinct_key='src_id'
cm=StoredPathMapping(ct,genomic_seq,hg17) # MAPPING OF OUR CLUSTER GENOMIC ONTO hg17

def getAlTable(tableName='GENOME_ALIGNMENT.haussler_align_sorted',cursor=None):
    if cursor is None:
        cursor=clusters.cursor
    alTable=SQLTable(tableName,cursor) # THE MAF ALIGNMENT TABLE
    alTable.objclass() # USE STANDARD TupleO OBJECT FOR EACH ROW
    return alTable

def getNLMSA(filename='/home/alex/localdata/ucscDB/mafdb'):
    return cnestedlist.NLMSA(filename,'r',genomeUnion)
    
def getClusterAlignment(cluster_id):
    c=clusters[cluster_id] # GET DATA FOR THIS CLUSTER ON chr22
    loadCluster(c,exons,splices,clusterExons,clusterSplices,spliceGraph,alt5Graph,alt3Graph)
    for e in c.exons:
        for g in cm[e]: # GET A GENOMIC INTERVAL ALIGNED TO OUR EXON
            print 'exon interval:',repr(g)
            maf=MAFStoredPathMapping(g,alTable,genomeUnion) # LOAD ALIGNMENT FROM THE DATABASE
            for ed in maf.edges(): # PRINT THE ALIGNED SEQUENCES
                print '%s (%s)\n%s (%s)\n' % (ed.srcPath,genomeUnion.getName(ed.srcPath.path),
                                              ed.destPath,genomeUnion.getName(ed.destPath.path))


# THE FOLLOWING CODE IS A TEST OF LOADING ALIGNMENT OF WHOLE GENOMIC CLUSTER...
# MAKES THE BlastSequenceCache MUCH FASTER, BECAUSE IT KNOWS THE WHOLE REGION TO PRE-LOAD...
#for as in cm[genomic_seq[c.cluster_id]].seq_dict().values():
#    g=as.destPath[as.destMin:as.destMax] # GET MERGED INTERVAL
#    maf=MAFStoredPathMapping(g,alTable,genomeUnion) # LOAD ALIGNMENT FROM THE DATABASE
#    break
#maf=MAFStoredPathMapping(cm[cg],alTable,genomeUnion) # LOAD ALIGNMENT FROM THE DATABASE

if __name__=='__main__':
    getClusterAlignment('Hs.10267')
