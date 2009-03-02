import MySQLdb
import os
from splicegraph_jan06 import *

spliceCalcs={'hg17_JAN06':
             TableGroup(db='SPLICE_JAN06',suffix='hg17',clusters='cluster_hg17',
                        exons='isoform_exon_form_hg17',splices='splice_verification_hg17',
                        genomic='genomic_cluster_hg17',mrna='isoform_mrna_seq_hg17',
                        protein='isoform_protein_seq_hg17'),
             'mm7_JAN06':
             TableGroup(db='SPLICE_JAN06',suffix='mm7',clusters='cluster_mm17',
                        exons='isoform_exon_form_mm7',splices='splice_verification_mm7',
                        genomic='genomic_cluster_mm7',mrna='isoform_mrna_seq_mm7',
                        protein='isoform_protein_seq_mm7')
             }


def getUserCursor(db):
    'get a cursor as the current user'
    db=MySQLdb.connect(db=db,read_default_file=os.environ['HOME']+'/.my.cnf',compress=True)
    return db.cursor()
             
def getSpliceGraphFromDB(dbgroup,loadAll=False):
    """load data from MySQL using the designated database table group.
    If loadAll true, then load the entire splice graph into memory."""
    cursor=getUserCursor(dbgroup.db)
    import sys
    print >>sys.stderr,'Reading database schema...'
    idDict={}
    tables=describeDBTables(dbgroup.db,cursor,idDict)
    if hasattr(dbgroup,'suffix'):
        tables=suffixSubset(tables,dbgroup.suffix) # SET OF TABLES ENDING IN JUN03
        idDict=indexIDs(tables) # CREATE AN INDEX OF THEIR PRIMARY KEYS
    for t in dbgroup.values():
        if t is not None and '.' in t and t not in tables: # THIS TABLE COMES FROM ANOTHER DATABASE...
            tables[t]=SQLTable(t,cursor) # SO GET IT FROM OTHER DATABASE

    # LOAD DATA & BUILD THE SPLICE GRAPH
    return loadSpliceGraph(tables,dbgroup.clusters,dbgroup.exons,dbgroup.splices,
                           dbgroup.genomic,dbgroup.mrna,dbgroup.protein,loadAll)

def localCopy(localFile,cpCommand):
    'if not already present on local file location, run cpCommand'
    if not os.access(localFile,os.R_OK):
        cmd=cpCommand % localFile
        print 'copying data:',cmd
        exit_code=os.system(cmd)
        if exit_code!=0:
            raise OSError((exit_code,'command failed: %s' % cmd))
    return localFile
