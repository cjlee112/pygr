from test import *
from pygr.apps.leelabdb import *
from pygr import cnestedlist
from lldb_jan06 import *

# GET CONNECTIONS TO ALL OUR GENOMES

from pygr import seqdb

hg17 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/hg17')
mm7 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/mm7')
rn3 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/rn3')
dr3 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/dr3')
bt2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/bt2')
cf2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/cf2')
gg2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/gg2')
fr1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/fr1')
xt1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/xt1')
oc1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/oc1')
pt1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/pt1')
rm1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/rm1')
rm2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/rm2')
dn1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/dn1')
la1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/la1')
et1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/et1')
tn1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/tn1')
md2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/md2')

genomes={'hg17':hg17,'mm7':mm7, 'rn3':rn3, 'canFam2':cf2, 'danRer3':dr3, 'fr1':fr1,'galGal2':gg2, \
         'panTro1':pt1, 'bosTau2':bt2, 'xenTro1':xt1, 'oryCun1':oc1, 'rheMac2':rm2, 'dasNov1':dn1, \
         'loxAfr1':la1, 'echTel1':et1, 'monDom2':md2, 'tetNig1':tn1, 'rheMac1':rm1}
genomeUnion=seqdb.PrefixUnionDict(genomes)

for db in genomes.values(): # FORCE ALL OUR DATABASES TO USE INTERVAL CACHING
    db.seqClass=BlastSequenceCache

(clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,protein,
 clusterExons,clusterSplices)=getSpliceGraphFromDB(spliceCalcs['hg17_JAN06'], loadAll=False) # GET OUR USUAL SPLICE GRAPH
ct=SQLTableMultiNoCache('SPLICE_JAN06.splice_genomic_hg17',clusters.cursor)
ct._distinct_key='src_id'
cm=StoredPathMapping(ct,genomic_seq,hg17) # MAPPING OF OUR CLUSTER GENOMIC ONTO hg17

def getAlTable(tableName='GENOME_ALIGNMENT.haussler_align_sorted',cursor=None):
    if cursor is None:
        cursor=clusters.cursor
    alTable=SQLTable(tableName,cursor) # THE MAF ALIGNMENT TABLE
    alTable.objclass() # USE STANDARD TupleO OBJECT FOR EACH ROW
    return alTable

def getNLMSA(filename='/Volumes/LaCie2/deepreds/hg17_msa'):
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
    getClusterAlignment('Hs.88630')
