import UserDict

from pygr import annotation, seqdb, sequence, sqlgraph, worldbase
from pygr.dbfile import ReadOnlyError


gRes = None


class UCSCStrandDescr(object):

    def __get__(self, obj, objtype):
        if obj.strand == '+':
            return 1
        else:
            return -1


class UCSCSeqIntervalRow(sqlgraph.TupleO):
    orientation = UCSCStrandDescr()


class UCSCGeneIntervalRow(sqlgraph.TupleO):
    orientation = UCSCStrandDescr()

    def __init__(self, *args, **kwargs):
        sqlgraph.TupleO.__init__(self, *args, **kwargs)
        self.children = gRes.get_gene_transcript_ids(self.name2)


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
        # Only one instance can be active at a time for now.
        global gRes
        if gRes is not None:
            raise ValueError("A UCSCEnsemblInterface object already exists")
        else:
            gRes = self
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
                                                   allowNonUniqueID=True,
                                                  itemClass=UCSCGeneIntervalRow,
                                                   attrAlias=dict(
                                                     minTxStart='min(txStart)',
                                                     maxTxEnd='max(txEnd)'))
        self.ucsc_ensGtp_gene = sqlgraph.SQLTable('%s.ensGtp' % self.ucsc_db,
                                                  serverInfo=self.ucsc_server,
                                                  primaryKey='gene',
                                                  allowNonUniqueID=True)
        self.ucsc_ensGtp_prot = sqlgraph.SQLTable('%s.ensGtp' % self.ucsc_db,
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
        # Finally, initialise all UCSC-Ensembl databases.
        self.trans_db = annotation.AnnotationDB(self.ucsc_ensGene_trans,
                                                self.genome_seq,
                                                checkFirstID=False,
                                                sliceAttrDict=dict(
                                                    id='chrom',
                                                    start='txStart',
                                                    stop='txEnd'),
                                      itemClass=EnsemblTranscriptAnnotationSeq)
        self.gene_db = annotation.AnnotationDB(self.ucsc_ensGene_gene,
                                               self.genome_seq,
                                               checkFirstID=False,
                                               sliceAttrDict=dict(
                                                   id='chrom',
                                                   start='txStart',
                                                   stop='txEnd'))
        self.prot_db = EnsemblProteinSequenceDB()
        exon_slicedb = EnsemblExonOnDemandSliceDB()
        self.exon_db = annotation.AnnotationDB(exon_slicedb,
                                               self.genome_seq,
                                               checkFirstID=False)
        # Mappings.
        self.protein_transcript_id_map = sqlgraph.MapView(
            self.ucsc_ensGtp_prot, self.trans_db,
            'select transcript from %s.ensGtp \
            where protein=%%s' % self.ucsc_db, inverseSQL='select protein \
            from %s.ensGtp where transcript=%%s' % self.ucsc_db)
        self.transcripts_in_genes_map = sqlgraph.GraphView(
            self.gene_db, self.trans_db,
            "select transcript from %s.ensGtp where gene=%%s" % self.ucsc_db)
        self.ens_transcripts_of_exons_map = sqlgraph.GraphView(
            self.exon_db, self.trans_db, """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id=%%s""" % (self.ens_db, self.ens_db, self.ens_db))
        self.ens_exons_in_transcripts_map = sqlgraph.GraphView(
            self.trans_db, self.exon_db, """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id=%%s order by \
et.rank""" % (self.ens_db, self.ens_db, self.ens_db))

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

    def get_ensembl_exon_ids(self, transcript_id):
        '''Obtain a list of stable IDs of exons associated with the
        specified transcript, ordered by rank.'''
        matching_edges = self.ens_exons_in_transcripts_map[
            self.ens_transcript_stable_id[transcript_id]]
        ids = []
        for exon in matching_edges.keys():
            ids.append(exon.stable_id)
        return ids

    def get_gene_transcript_ids(self, gene_id):
        '''Obtain a list of stable IDs of transcripts associated
        with the specified gene.'''
        matching_edges = self.transcripts_in_genes_map[
            self.ucsc_ensGtp_gene[gene_id]]
        ids = []
        for transcript in matching_edges.keys():
            ids.append(transcript.name)
        return ids

    def transcript_database(self):
        'Return an AnnotationDB of transcript annotations.'
        return self.trans_db

    def gene_database(self):
        'Return an AnnotationDB of gene annotations.'
        return self.gene_db

    def protein_database(self):
        'Return an AnnotationDB of protein annotations.'
        return self.prot_db

    def exon_database(self):
        'Return an AnnotationDB of exon annotations.'
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


class EnsemblTranscriptAnnotationExonDescr(object):

    def __get__(self, obj, objtype):
        'Return a list of exons contained in this transcript.'
        exon_ids = gRes.get_ensembl_exon_ids(obj.name)
        return exon_ids


class EnsemblTranscriptAnnotationSeq(annotation.AnnotationSeq):
    '''An AnnotationSeq class for transcript annotations, implementing
    custom 'sequence' and 'children' properties.'''
    sequence = EnsemblTranscriptAnnotationSeqDescr()
    children = EnsemblTranscriptAnnotationExonDescr()


class EnsemblProteinSequenceDB(object, UserDict.DictMixin):
    'A wrapper around ensPep allowing querying it by protein stable ID.'

    def __getitem__(self, k):
        tid = gRes.protein_transcript_id_map[gRes.ucsc_ensGtp_prot[k]].name
        return gRes.ucsc_ensPep[tid]

    def keys(self):
        prot_keys = []
        trans_keys = gRes.ucsc_ensPep.keys()
        for tid in trans_keys:
            pid = (~gRes.protein_transcript_id_map[
                gRes.ucsc_ensGene[tid]]).name
            prot_keys.append(pid)
        return prot_keys


class EnsemblExonSliceInfo(object):

    def __init__(self, id, start, stop, orientation, parents=None,
                 children=None):
        self.id = id
        self.start = start
        self.stop = stop
        self.orientation = orientation
        self.parents = parents
        self.children = children


class EnsemblExonOnDemandSliceDB(object, UserDict.DictMixin):

    def __init__(self):
        self.data = {}

    def __getitem__(self, k):
        try:
            return self.data[k]
        except KeyError:
            # Not cached yet, extract the exon from transcript data.
            transcripts = gRes.ens_transcripts_of_exons_map[
                gRes.ens_exon_stable_id[k]].keys()
            transcript_exons = self.get_transcript_exons(transcripts[0])
            # Cache all exons from that transcript to save time in the future.
            for exon_id in transcript_exons:
                if exon_id not in self.data:
                    transcript_exons[exon_id].parents = transcripts
                    self.data[exon_id] = transcript_exons[exon_id]
            gRes.genome_seq.cacheHint({transcripts[0].id:
                                           (transcripts[0].txStart,
                                            transcripts[0].txEnd)},
                                          transcripts[0])
            return self.data[k]

    def __setitem__(self, k, v):
        '''Method required by UserDict.DictMixin. Throws an exception
        (read-only sliceDB).'''
        raise ReadOnlyError('EnsemblExonOnDemandSliceDB is read-only')

    def __delitem__(self, k):
        '''Method required by UserDict.DictMixin. Throws an exception
        (read-only sliceDB).'''
        raise ReadOnlyError('EnsemblExonOnDemandSliceDB is read-only')

    def keys(self):
        'Returns keys present in the cache. FIXME: add support for SQL ones?'
        return self.data.keys()

    def get_transcript_exons(self, transcript):
        '''Parse the provided transcript, extract exon data from it
        and return it as a dictionary of slices.'''
        chromosome = transcript.chrom
        exon_count = transcript.exonCount
        exon_starts = transcript.exonStarts.split(',')[:exon_count]
        exon_ends = transcript.exonEnds.split(',')[:exon_count]
        exons = {}
        exon_ids = gRes.get_ensembl_exon_ids(transcript.name)
        for i in range(0, exon_count):
            e = EnsemblExonSliceInfo(chromosome, exon_starts[i], exon_ends[i],
                                     transcript.orientation)
            exons[exon_ids[i]] = e
        return exons
