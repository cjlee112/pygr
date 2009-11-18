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
    for i in range(0, exon_count):
        try:
            ens_ex_id = get_ensembl_exon_id(transcript_id, i + 1)
        except:
            print 'Failed to get Ensembl exon ID, using transcript_id:rank'
            ens_ex_id = transcript_id + ':' + str(i + 1)
        e = (
            ens_ex_id,
            chromosome,
            exon_starts[i],
            exon_ends[i],
            trans_tuple.orientation)
        exons.append(e)
    return exons


def get_ensembl_exon_id(transcript_id, rank):
    '''Use Ensembl stable transcript ID and rank extracted from UCSC
    data to obtain Ensembl stable exon ID from their database.'''
    global ens_server, ens_database
    ens_table = ens_database + '.exon_stable_id'
    tbl = sqlgraph.SQLTable(ens_table, serverInfo=ens_server)
    # FIXME: at the moment, the line below throws "No database selected"!
    tbl.cursor.execute('''\
select exon.stable_id from exon_stable_id exon, transcript_stable_id trans,
exon_transcript et where exon.exon_id=et.exon_id and
trans.transcript_id=et.transcript_id and trans.stable_id=%s and et.rank=%s''' \
                       % (transcript_id, rank))
    return tbl.cursor.fetchall()


hg_version = 18
ensembl_postfixes = {54: '54_36p', 55: '55_37'} # FIXME: is there a cleaner way?


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
                                primaryKey='transcript')

# Obtain version mapping from UCSC
ucsc_versions = sqlgraph.SQLTable('hgFixed.trackVersion',
                                  serverInfo=ucsc_server,
                                  primaryKey='db')
ens_version = int(ucsc_versions['hg%d' % hg_version].version)
ens_database = 'homo_sapiens_core_%s' % ensembl_postfixes[ens_version]

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
# FIXME: in order to get protein annotation we need to map protein ID
# to transcript ID using ucsc_ensGtp, then get all the necessary information
# from ucsc_ensGene. This could be done on the server side using a simple
# SQL join - but how to have SQLTable refer to a join rather than a real table?

#
# Exon annotation
#
exon_db = annotation.AnnotationDB({}, human_seq,
                                  sliceAttrDict=dict(id=1, start=2, stop=3,
                                                     orientation=4))
for tr in ucsc_ensGene_trans:
    transcript_exons = get_transcript_exons(ucsc_ensGene_trans[tr])
    for exon in transcript_exons:
        exon_db.new_annotation(exon[0], exon)
    break   # FIXME: temporary - saves time during testing
print '\nExample exon annotation:'
print 'ENST00000000233:4', repr(exon_db['ENST00000000233:4']), \
        repr(exon_db['ENST00000000233:4'].sequence)
