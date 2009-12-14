from pygr import annotation, sqlgraph, worldbase


class UCSCStrandDescr(object):

    def __get__(self, obj, objtype):
        if obj.strand == '+':
            return 1
        else:
            return -1


class UCSCSeqIntervalRow(sqlgraph.TupleO):
    orientation = UCSCStrandDescr()


def get_transcript_exons(trans_tuple):
    '''Parse the Ensembl transcript from UCSC provided via trans_tuple,
    extract exon data from it and return it as a list of tuples.'''
    transcript_id = trans_tuple.name
    chromosome = trans_tuple.chrom
    exon_count = trans_tuple.exonCount
    exon_starts = trans_tuple.exonStarts.split(',')[:exon_count]
    exon_ends = trans_tuple.exonEnds.split(',')[:exon_count]
    exons = []
    exon_ids = get_ensembl_exon_ids(transcript_id)
    for i in range(0, exon_count):
        e = (
            exon_ids[i][0],
            chromosome,
            exon_starts[i],
            exon_ends[i],
            trans_tuple.orientation)
        exons.append(e)
    return exons


def get_ensembl_exon_ids(transcript_id):
    '''Obtain a list of stable IDs of exons associated with the
    specified transcript, ordered by rank.'''
    global ens_server, ens_database
    # FIXME: do all this with GraphView instead?
    cursor = ens_server.cursor()
    query = """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id='%s' order by \
et.rank""" % (ens_database, ens_database, ens_database, transcript_id)
    cursor.execute(query)
    return cursor.fetchall()


def get_ensembl_transcript_id(exon_id):
    '''Use Ensembl stable exon ID to obtain Ensembl stable transcript
    ID, which can be used to extract exon information from UCSC data.'''
    global ens_server, ens_database
    # FIXME: do all this with MapView instead?
    cursor = ens_server.cursor()
    query = """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id='%s'""" % (ens_database, ens_database, ens_database, exon_id)
    cursor.execute(query)
    return cursor.fetchall()[0][0]


def get_ensembl_db_name(version, prefix='homo_sapiens_core'):
    global ens_server
    cursor = ens_server.cursor()
    cursor.execute("show databases like '%s_%d_%%'" % (prefix, version))
    return cursor.fetchall()[0][0]


hg_version = 18


human_seq = worldbase('Bio.Seq.Genome.HUMAN.hg%d' % hg_version)

ucsc_server = sqlgraph.DBServerInfo(host='genome-mysql.cse.ucsc.edu',
                                    user='genome')
ens_server = sqlgraph.DBServerInfo(host='ensembldb.ensembl.org', port=5306,
                                   user='anonymous')

ucsc_ensGene_trans = sqlgraph.SQLTable('hg%d.ensGene' % hg_version,
                                       serverInfo=ucsc_server,
                                       primaryKey='name',
                                       itemClass=UCSCSeqIntervalRow)
ucsc_ensGene_gene = sqlgraph.SQLTable('hg%d.ensGene' % hg_version,
                                      serverInfo=ucsc_server,
                                      primaryKey='name2',
                                      itemClass=UCSCSeqIntervalRow)
ucsc_ensGtp = sqlgraph.SQLTable('hg%d.ensGtp' % hg_version,
                                serverInfo=ucsc_server,
                                primaryKey='protein')

# Obtain version mapping from UCSC
ucsc_versions = sqlgraph.SQLTable('hgFixed.trackVersion',
                                  serverInfo=ucsc_server,
                                  primaryKey='db')
ens_version = int(ucsc_versions['hg%d' % hg_version].version)
ens_database = get_ensembl_db_name(ens_version)

#
# Transcript annotations
#
trans_db = annotation.AnnotationDB(ucsc_ensGene_trans, human_seq,
                                   checkFirstID=False,
                                   sliceAttrDict=dict(id='chrom',
                                                      start='txStart',
                                                      stop='txEnd'))
print '\nExample transcript annotation:'
print 'ENST00000000233', repr(trans_db['ENST00000000233']), \
        repr(trans_db['ENST00000000233'].sequence)

#
# Gene annotations
#
gene_db = annotation.AnnotationDB(ucsc_ensGene_gene, human_seq,
                                  checkFirstID=False,
                                  sliceAttrDict=dict(id='chrom',
                                                     start='txStart',
                                                     stop='txEnd'))
print '\nExample gene annotation:'
print 'ENSG00000000003', repr(gene_db['ENSG00000000003']), \
        repr(gene_db['ENSG00000000003'].sequence)
try:
    print 'ENSG00000238261', repr(gene_db['ENSG00000238261'])
except KeyError:
    print 'Querying a multi-transcript gene annotation has failed as expected'

#
# Protein annotation
#
protein_transcripts = sqlgraph.MapView(ucsc_ensGtp, ucsc_ensGene_trans,
                                       'select transcript from hg%d.ensGtp \
                                       where protein=%%s' % hg_version,
                                       inverseSQL='select protein from \
                                       hg%d.ensGtp where transcript=%%s' % \
                                       hg_version)
# FIXME: create a wrapper for trans_db which uses the map
print '\nExample protein annotation:'
prot_id = 'ENSP00000372525'
trans_id = protein_transcripts[ucsc_ensGtp[prot_id]].name
print prot_id, repr(trans_db[trans_id]), \
        repr(trans_db[trans_id].sequence)

#
# Exon annotation
#

# TODO: Clean up exon-related get_ensembl_...() functions:
#  - simplify lookups?
#  - use GraphView or MapView?

class EnsemblOnDemandSliceDB(object):

    def __init__(self, transcript_db):
        self.data = {}
        self.trans_db = transcript_db

    def __getitem__(self, k):
        try:
            return self.data[k]
        except KeyError:
            # Not cached yet, extract the exon from transcript data
            tid = get_ensembl_transcript_id(k)
            transcript_exons = get_transcript_exons(self.trans_db[tid])
            # Cache all exons from that transcript to save time in the future.
            for exon in transcript_exons:
                self.data[exon[0]] = exon
            return self.data[k]


exon_slicedb = EnsemblOnDemandSliceDB(ucsc_ensGene_trans)
exon_db = annotation.AnnotationDB(exon_slicedb, human_seq,
                                  sliceAttrDict=dict(id=1, start=2, stop=3,
                                                     orientation=4))
print '\nExample exon annotation:'
print 'ENSE00000720378', repr(exon_db['ENSE00000720378']), \
        repr(exon_db['ENSE00000720378'].sequence)
