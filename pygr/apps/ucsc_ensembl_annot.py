import UserDict

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
            exon_ids[i],
            chromosome,
            exon_starts[i],
            exon_ends[i],
            trans_tuple.orientation)
        exons.append(e)
    return exons


def get_ensembl_exon_ids(transcript_id):
    '''Obtain a list of stable IDs of exons associated with the
    specified transcript, ordered by rank.'''
    global ens_server, ens_database, ens_transcript_stable_id, \
            ensembl_transcript_exons
    matching_edges = \
            ensembl_transcript_exons[ens_transcript_stable_id[transcript_id]]
    ids = []
    for exon in matching_edges.keys():  # FIXME: is the order always correct?
        ids.append(exon.stable_id)
    return ids


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

# Obtain version mapping from UCSC
ucsc_versions = sqlgraph.SQLTable('hgFixed.trackVersion',
                                  serverInfo=ucsc_server,
                                  primaryKey='db')
ens_version = int(ucsc_versions['hg%d' % hg_version].version)
ens_database = get_ensembl_db_name(ens_version)

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

ens_exon_stable_id = sqlgraph.SQLTable('%s.exon_stable_id' % ens_database,
                                       serverInfo=ens_server,
                                       primaryKey='stable_id')

ens_transcript_stable_id = sqlgraph.SQLTable('%s.transcript_stable_id' %
                                             ens_database,
                                             serverInfo=ens_server,
                                             primaryKey='stable_id')

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
ensembl_exon_transcripts = sqlgraph.MapView(ens_exon_stable_id,
                                            ucsc_ensGene_trans, """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id=%%s""" % (ens_database, ens_database, ens_database))

ensembl_transcript_exons = sqlgraph.GraphView(ens_transcript_stable_id,
                                              ens_exon_stable_id, """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id=%%s order by \
et.rank""" % (ens_database, ens_database, ens_database))


class EnsemblOnDemandSliceDB(object, UserDict.DictMixin):

    def __init__(self, transcript_db):
        self.data = {}
        self.trans_db = transcript_db

    def __getitem__(self, k):
        try:
            return self.data[k]
        except KeyError:
            # Not cached yet, extract the exon from transcript data
            transcript = ensembl_exon_transcripts[ens_exon_stable_id[k]]
            transcript_exons = get_transcript_exons(transcript)
            # Cache all exons from that transcript to save time in the future.
            for exon in transcript_exons:
                self.data[exon[0]] = exon
            return self.data[k]

    def __setitem__(self, k, v):
        '''Method required by UserDict.DictMixin. Does nothing
        (read-only sliceDB).'''
        pass

    def __delitem__(self, k):
        '''Method required by UserDict.DictMixin. Does nothing
        (read-only sliceDB).'''
        pass

    def keys(self):
        'Returns keys present in the cache. FIXME: add support for SQL ones?'
        return self.data.keys()


exon_slicedb = EnsemblOnDemandSliceDB(ucsc_ensGene_trans)
exon_db = annotation.AnnotationDB(exon_slicedb, human_seq, checkFirstID=False,
                                  sliceAttrDict=dict(id=1, start=2, stop=3,
                                                     orientation=4))
print '\nExample exon annotation:'
print 'ENSE00000720378', repr(exon_db['ENSE00000720378']), \
        repr(exon_db['ENSE00000720378'].sequence)
