import UserDict

from pygr import annotation, seqdb, sequence, sqlgraph, worldbase
from pygr.dbfile import ReadOnlyError


class UCSCStrandDescr(object):

    def __get__(self, obj, objtype):
        if obj.strand == '+':
            return 1
        else:
            return -1


class UCSCSeqIntervalRow(sqlgraph.TupleO):
    orientation = UCSCStrandDescr()


class UCSCProteinSeq(sqlgraph.ProteinSQLSequence):
    '''Representation of UCSC protein-sequence tables such as ensGene,
    which lack the length column.'''

    def __len__(self):
        return self._select('length(seq)')


class UCSCEnsemblInterface(object):

    def __init__(self, ucsc_genome_name, ens_species=None,
                 ucsc_serverInfo=None, ens_serverInfo=None):
        '''Set up everything needed to produce UCSC/Ensembl
        annotation databases. ucsc_genome_name should follow the worldbase
        naming convention. If ens_species is not specified, we will try
        to autodetect it.'''
        # Connect to both servers and prepare database names.
        if ucsc_serverInfo is not None:
            self.ucsc_server = ucsc_serverInfo
        else:
            self.ucsc_server = sqlgraph.DBServerInfo(
                host='genome-mysql.cse.ucsc.edu', user='genome')
        if ens_serverInfo is not None:
            self.ens_server = ens_serverInfo
        else:
            self.ens_server = sqlgraph.DBServerInfo(
                host='ensembldb.ensembl.org', port=5306, user='anonymous')
        self.ucsc_db = ucsc_genome_name.split('.')[-1]
        self.ens_db = self.get_ensembl_db_name(ens_species)
        # Connect to all the necessary tables.
        self.ucsc_ensGene_trans = sqlgraph.SQLTable('%s.ensGene' %
                                                    self.ucsc_db,
                                                   serverInfo=self.ucsc_server,
                                                    primaryKey='name',
                                                  itemClass=UCSCSeqIntervalRow)
        self.ucsc_ensGene_gene = sqlgraph.SQLTable('%s.ensGene' % self.ucsc_db,
                                                   serverInfo=self.ucsc_server,
                                                   primaryKey='name2',
                                                  itemClass=UCSCSeqIntervalRow)
        self.ucsc_ensGtp = sqlgraph.SQLTable('%s.ensGtp' % self.ucsc_db,
                                             serverInfo=self.ucsc_server,
                                             primaryKey='protein')
        self.ucsc_ensPep = sqlgraph.SQLTable('%s.ensPep' % self.ucsc_db,
                                             serverInfo=self.ucsc_server,
                                             itemClass=UCSCProteinSeq,
                                             itemSliceClass=seqdb.SeqDBSlice)
        self.ens_exon_stable_id = sqlgraph.SQLTable('%s.exon_stable_id'
                                                    % self.ens_db,
                                                    serverInfo=self.ens_server,
                                                    primaryKey='stable_id')
        self.ens_transcript_stable_id = sqlgraph.SQLTable(
            '%s.transcript_stable_id' % self.ens_db,
            serverInfo=self.ens_server, primaryKey='stable_id')
        # We will need this too.
        self.genome_seq = worldbase(ucsc_genome_name)
        # Initialise all cache variables.
        self.trans_db = None
        self.gene_db = None
        self.prot_db = None
        self.exon_db = None

    def get_ensembl_db_name(self, ens_prefix):
        '''Used by __init__(), obtains Ensembl database name matching
        the specified UCSC genome version'''
        ucsc_versions = sqlgraph.SQLTable('hgFixed.trackVersion',
                                          serverInfo=self.ucsc_server,
                                          primaryKey='db')
        ens_version = ucsc_versions[self.ucsc_db].version
        if ens_prefix is None:
            # Note: this assumes 'source' in hgFixed.trackVersion contains
            # the URI of the Ensembl data set and that the last path component
            # of that URI is the species name of that data set.
            ens_prefix = ucsc_versions[self.ucsc_db].source.split('/')[-2]
        cursor = self.ens_server.cursor()
        cursor.execute("show databases like '%s_core_%s_%%'" % (ens_prefix,
                                                                ens_version))
        return cursor.fetchall()[0][0]

    def transcript_database(self):
        'Return an AnnotationDB of transcript annotations.'
        if self.trans_db is None:
            self.trans_db = annotation.AnnotationDB(self.ucsc_ensGene_trans,
                                                    self.genome_seq,
                                                    checkFirstID=False,
                                                    sliceAttrDict=dict(
                                                        id='chrom',
                                                        start='txStart',
                                                        stop='txEnd'),
                                      itemClass=EnsemblTranscriptAnnotationSeq)
        return self.trans_db

    def gene_database(self):
        'Return an AnnotationDB of gene annotations.'
        if self.gene_db is None:
            self.gene_db = annotation.AnnotationDB(self.ucsc_ensGene_gene,
                                                   self.genome_seq,
                                                   checkFirstID=False,
                                                   sliceAttrDict=dict(
                                                       id='chrom',
                                                       start='txStart',
                                                       stop='txEnd'))
        return self.gene_db

    def protein_database(self):
        'Return an AnnotationDB of protein annotations.'
        if self.prot_db is None:
            self.protein_transcript_id_map = sqlgraph.MapView(self.ucsc_ensGtp,
                self.ucsc_ensGene_trans, 'select transcript from %s.ensGtp \
                where protein=%%s' % self.ucsc_db, inverseSQL='select protein \
                from %s.ensGtp where transcript=%%s' % self.ucsc_db)
            protein_slicedb = EnsemblProteinSliceDB(self, '%s.ensGene' %
                                                    self.ucsc_db,
                                                   serverInfo=self.ucsc_server,
                                                    primaryKey='name',
                                                  itemClass=UCSCSeqIntervalRow)
            self.prot_db = annotation.AnnotationDB(protein_slicedb,
                                                   self.genome_seq,
                                                   checkFirstID=False,
                                                   sliceAttrDict=dict(
                                                       id='chrom',
                                                       start='txStart',
                                                       stop='txEnd'))
            return self.prot_db

    def exon_database(self):
        'Return an AnnotationDB of exon annotations.'
        if self.exon_db is None:
            self.ens_transcripts_of_exons_map = sqlgraph.GraphView(
                self.ens_exon_stable_id, self.ucsc_ensGene_trans, """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id=%%s""" % (self.ens_db, self.ens_db, self.ens_db))
            self.ens_exons_in_transcripts_map = sqlgraph.GraphView(
                self.ens_transcript_stable_id, self.ens_exon_stable_id, """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id=%%s order by \
et.rank""" % (self.ens_db, self.ens_db, self.ens_db))
            exon_slicedb = EnsemblOnDemandSliceDB(self)
            self.exon_db = annotation.AnnotationDB(exon_slicedb,
                                                   self.genome_seq,
                                                   checkFirstID=False,
                                                   sliceAttrDict=dict(id=1,
                                                                      start=2,
                                                                      stop=3,
                                                                orientation=4))
        return self.exon_db


class EnsemblTranscriptAnnotationSeqDescr(object):

    def __get__(self, obj, objtype):
        '''Concatenate exon sequences of a transcript to obtain
        its sequence.'''
        exon_count = obj.exonCount
        exon_starts = obj.exonStarts.split(',')[:exon_count]
        exon_ends = obj.exonEnds.split(',')[:exon_count]
        trans_seq = ''
        for i in range(0, exon_count):
            trans_seq += str(sequence.absoluteSlice(obj._anno_seq,
                                                    int(exon_starts[i]),
                                                    int(exon_ends[i])))
        return sequence.Sequence(trans_seq, obj.name)   # FIXME: cache this?


class EnsemblTranscriptAnnotationSeq(annotation.AnnotationSeq):
    '''An AnnotationSeq class for transcript annotations, implementing
    a custom 'sequence' property.'''
    sequence = EnsemblTranscriptAnnotationSeqDescr()


class EnsemblProteinSliceDB(sqlgraph.SQLTable):
    '''A sliceDB class for protein annotations. Basically, an SQLTable
    pointing to transcript data along with transparent mapping of keys.'''

    def __init__(self, res, *args, **kwargs):
        self.res = res
        sqlgraph.SQLTable.__init__(self, *args, **kwargs)

    def __getitem__(self, k):
        tid = self.res.protein_transcript_id_map[self.res.ucsc_ensGtp[k]].name
        return sqlgraph.SQLTable.__getitem__(self, tid)

    def keys(self):
        prot_keys = []
        trans_keys = SQLTable.keys(self)
        for tid in trans_keys:
            pid = (~self.res.protein_transcript_id_map[
                self.res.ucsc_ensGene[tid]]).name
            prot_keys.append(pid)
        return prot_keys


class EnsemblOnDemandSliceDB(object, UserDict.DictMixin):

    def __init__(self, res):
        self.data = {}
        self.res = res

    def __getitem__(self, k):
        try:
            return self.data[k]
        except KeyError:
            # Not cached yet, extract the exon from transcript data.
            transcripts = self.res.ens_transcripts_of_exons_map[
                self.res.ens_exon_stable_id[k]].keys()
            transcript_exons = self.get_transcript_exons(transcripts[0])
            # Cache all exons from that transcript to save time in the future.
            for exon in transcript_exons:
                if exon[0] not in self.data:
                    self.data[exon[0]] = exon
            self.res.genome_seq.cacheHint({transcripts[0].id:
                                           (transcripts[0].txStart,
                                            transcripts[0].txEnd)},
                                          self)
            return self.data[k]

    def __setitem__(self, k, v):
        '''Method required by UserDict.DictMixin. Throws an exception
        (read-only sliceDB).'''
        raise ReadOnlyError('EnsemblOnDemandSliceDB is read-only')

    def __delitem__(self, k):
        '''Method required by UserDict.DictMixin. Throws an exception
        (read-only sliceDB).'''
        raise ReadOnlyError('EnsemblOnDemandSliceDB is read-only')

    def keys(self):
        'Returns keys present in the cache. FIXME: add support for SQL ones?'
        return self.data.keys()

    def get_ensembl_exon_ids(self, transcript_id):
        '''Obtain a list of stable IDs of exons associated with the
        specified transcript, ordered by rank.'''
        matching_edges = self.res.ens_exons_in_transcripts_map[
            self.res.ens_transcript_stable_id[transcript_id]]
        ids = []
        for exon in matching_edges.keys():
            ids.append(exon.stable_id)
        return ids

    def get_transcript_exons(self, trans_tuple):
        '''Parse the Ensembl transcript from UCSC provided via
        trans_tuple, extract exon data from it and return it
        as a list of tuples.'''
        transcript_id = trans_tuple.name
        chromosome = trans_tuple.chrom
        exon_count = trans_tuple.exonCount
        exon_starts = trans_tuple.exonStarts.split(',')[:exon_count]
        exon_ends = trans_tuple.exonEnds.split(',')[:exon_count]
        exons = []
        exon_ids = self.get_ensembl_exon_ids(transcript_id)
        for i in range(0, exon_count):
            e = (
                exon_ids[i],
                chromosome,
                exon_starts[i],
                exon_ends[i],
                trans_tuple.orientation)
            exons.append(e)
        return exons
