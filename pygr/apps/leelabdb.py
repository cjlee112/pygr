import MySQLdb
import os
from splicegraph import *


spliceCalcs={'HUMAN_SPLICE_03':
             TableGroup(db='HUMAN_SPLICE_03', suffix='JUN03',
                        clusters='cluster_JUN03', exons='exon_formJUN03',
                        splices='splice_verification_JUN03',
                        genomic='genomic_cluster_JUN03', mrna='mrna_seqJUN03',
                        protein='protein_seqJUN03'),
             'HUMAN_SPLICE':
             TableGroup(db='HUMAN_SPLICE', suffix='jan02',
                        clusters='cluster_jan02',
                        exons='HUMAN_ISOFORMS.exon_form_4',
                        splices='splice_verification_jan02',
                        genomic='genomic_cluster_jan02',
                        mrna='HUMAN_ISOFORMS.mrna_seq_4',
                        protein='HUMAN_ISOFORMS.protein_seq_4'),
             'MOUSE_SPLICE':
             TableGroup(db='MOUSE_SPLICE', suffix='jan02',
                        clusters='cluster_jan02',
                        exons='MOUSE_ISOFORMS.exon_form_2',
                        splices='splice_verification_jan02',
                        genomic='genomic_cluster_jan02',
                        mrna='MOUSE_ISOFORMS.mrna_seq_2',
                        protein='MOUSE_ISOFORMS.protein_seq_2'),
             'MOUSE_SPLICE_03':
             TableGroup(db='MOUSE_SPLICE_03', suffix='JUN03',
                        clusters='cluster_JUN03', exons='exon_formJUN03',
                        splices='splice_verification_JUN03',
                        genomic='genomic_cluster_JUN03', mrna='mrna_seqJUN03',
                        protein='protein_seqJUN03')}


def getUserCursor(db):
    'get a cursor as the current user'
    db = MySQLdb.connect(db=db, read_default_file=os.environ['HOME']
                         + '/.my.cnf', compress=True)
    return db.cursor()


def getSpliceGraphFromDB(dbgroup, loadAll=False):
    """load data from MySQL using the designated database table group.
    If loadAll true, then load the entire splice graph into memory."""
    cursor = getUserCursor(dbgroup.db)
    import sys
    print >>sys.stderr, 'Reading database schema...'
    idDict = {}
    tables = describeDBTables(dbgroup.db, cursor, idDict)
    if hasattr(dbgroup, 'suffix'):
        # Get a set of tables ending in specified suffix
        # and create an index of their primary keys
        tables = suffixSubset(tables, dbgroup.suffix)
        idDict = indexIDs(tables)
    for t in dbgroup.values():
        # This table comes from another database...
        if t is not None and '.' in t and t not in tables:
            tables[t]=SQLTable(t, cursor) # ...so get it from there

    # LOAD DATA & BUILD THE SPLICE GRAPH
    return loadSpliceGraph(tables, dbgroup.clusters, dbgroup.exons,
                           dbgroup.splices, dbgroup.genomic, dbgroup.mrna,
                           dbgroup.protein, loadAll)


def localCopy(localFile, cpCommand):
    'if not already present on local file location, run cpCommand'
    if not os.access(localFile, os.R_OK):
        cmd=cpCommand % localFile
        print 'copying data:', cmd
        exit_code=os.system(cmd)
        if exit_code!=0:
            raise OSError((exit_code, 'command failed: %s' % cmd))
    return localFile
