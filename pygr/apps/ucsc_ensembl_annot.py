import UserDict

from pygr import annotation, seqdb, sequence, sqlgraph, worldbase
from pygr.classutil import read_only_error


class UCSCStrandDescr(object):

    def __get__(self, obj, objtype):
        if obj.strand == '+':
            return 1
        else:
            return -1


class UCSCSeqIntervalRow(sqlgraph.TupleO):
    orientation = UCSCStrandDescr()


class UCSCEnsemblInterface(object):
    'package of gene, transcript, exon, protein interfaces to UCSC/Ensembl'

    def __init__(self, ucsc_genome_name, ens_species=None,
                 ucsc_serverInfo=None, ens_serverInfo=None,
                 ens_db=None, trackVersion='hgFixed.trackVersion'):
        '''Construct interfaces to UCSC/Ensembl annotation databases.
        ucsc_genome_name must be a worldbase ID specifying a UCSC genome.
        naming convention.
        ens_species should be the Ensembl database name (generally
        the name of the species).  If not specified, we will try
        to autodetect it based on ucsc_genome_name.
        The interface uses the standard UCSC and Ensembl mysql servers
        by default, unless you provide serverInfo argument(s).
        trackVersion must be the fully qualified MySQL table name
        of the trackVersion table containing information about the
        Ensembl version that each genome dataset connects to.'''
        # Connect to both servers and prepare database names.
        if ucsc_serverInfo is not None:
            if isinstance(ucsc_serverInfo, str): # treat as worldbase ID
                self.ucsc_server = worldbase(ucsc_serverInfo)
            else:
                self.ucsc_server = ucsc_serverInfo
        else:
            self.ucsc_server = sqlgraph.DBServerInfo(
                host='genome-mysql.cse.ucsc.edu', user='genome')
        if ens_serverInfo is not None:
            if isinstance(ens_serverInfo, str): # treat as worldbase ID
                self.ens_server = worldbase(ens_serverInfo)
            else:
                self.ens_server = ens_serverInfo
        else:
            self.ens_server = sqlgraph.DBServerInfo(
                host='ensembldb.ensembl.org', port=5306, user='anonymous')
        self.ucsc_db = ucsc_genome_name.split('.')[-1]
        if ens_db is None: # auto-set ensembl database name
            self.ens_db = self.get_ensembl_db_name(ens_species,
                                                   trackVersion)
        else:
            self.ens_db = ens_db
        # Connect to all the necessary tables.
        self.ucsc_ensGene_trans = sqlgraph.SQLTable('%s.ensGene' %
                   self.ucsc_db, serverInfo=self.ucsc_server,
                   primaryKey='name', itemClass=UCSCSeqIntervalRow)
        self.ucsc_ensGene_gene = sqlgraph.SQLTable('%s.ensGene' %
                   self.ucsc_db, serverInfo=self.ucsc_server,
                   primaryKey='name2', allowNonUniqueID=True,
                   itemClass=UCSCSeqIntervalRow,
                   attrAlias=dict(minTxStart='min(txStart)',
                                  maxTxEnd='max(txEnd)'))
        self.ucsc_ensGtp_gene = sqlgraph.SQLTable('%s.ensGtp' %
                   self.ucsc_db, serverInfo=self.ucsc_server,
                   primaryKey='gene', allowNonUniqueID=True)
        self.prot_db = sqlgraph.SQLTable('%s.ensGtp' % self.ucsc_db,
                                         serverInfo=self.ucsc_server,
                                         primaryKey='protein',
                                         itemClass=EnsemblProteinRow)
        self.prot_db.gRes = self
        self.ucsc_ensPep = sqlgraph.SQLTable('%s.ensPep' % self.ucsc_db,
                   serverInfo=self.ucsc_server,
                   itemClass=sqlgraph.ProteinSQLSequenceCached,
                   itemSliceClass=seqdb.SeqDBSlice)
        self.ens_exon_stable_id = sqlgraph.SQLTable('%s.exon_stable_id' %
                   self.ens_db, serverInfo=self.ens_server,
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
        exon_slicedb = EnsemblExonOnDemandSliceDB(self)
        self.exon_db = annotation.AnnotationDB(exon_slicedb,
                                               self.genome_seq,
                                               checkFirstID=False,
                                               sliceAttrDict=dict(id=0,
                                                 start=1, stop=2,
                                                 orientation=3))
        # Mappings.
        self.protein_transcript_id_map = sqlgraph.MapView(
            self.prot_db, self.trans_db,
            'select transcript from %s.ensGtp \
            where protein=%%s' % self.ucsc_db, inverseSQL='select protein \
            from %s.ensGtp where transcript=%%s' % self.ucsc_db,
            serverInfo=self.ucsc_server)
        self.transcripts_in_genes_map = sqlgraph.GraphView(
            self.gene_db, self.trans_db,
            "select transcript from %s.ensGtp where gene=%%s" % self.ucsc_db,
            inverseSQL="select gene from %s.ensGtp where transcript=%%s" %
            self.ucsc_db, serverInfo=self.ucsc_server)
        self.ens_transcripts_of_exons_map = sqlgraph.GraphView(
            self.exon_db, self.trans_db, """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id=%%s""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.ens_transcripts_of_exons_map2 = sqlgraph.GraphView(
            self.ens_exon_stable_id, self.trans_db, """\
select trans.stable_id from %s.exon_stable_id exon, \
%s.transcript_stable_id trans, %s.exon_transcript et where \
exon.exon_id=et.exon_id and trans.transcript_id=et.transcript_id and \
exon.stable_id=%%s""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.ens_exons_in_transcripts_map = sqlgraph.GraphView(
            self.trans_db, self.exon_db, """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id=%%s order by \
et.rank""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.ens_exons_in_transcripts_map2 = sqlgraph.GraphView(
            self.trans_db, self.ens_exon_stable_id, """\
select exon.stable_id from %s.exon_stable_id exon, %s.transcript_stable_id \
trans, %s.exon_transcript et where exon.exon_id=et.exon_id and \
trans.transcript_id=et.transcript_id and trans.stable_id=%%s order by \
et.rank""" % (self.ens_db, self.ens_db, self.ens_db),
            serverInfo=self.ens_server)
        self.trans_db.exons_map = self.ens_exons_in_transcripts_map2

    def get_ensembl_db_name(self, ens_prefix, trackVersion):
        '''Used by __init__(), obtains Ensembl database name matching
        the specified UCSC genome version'''
        ucsc_versions = sqlgraph.SQLTableMultiNoCache(trackVersion,
                                               serverInfo=self.ucsc_server)
        ucsc_versions._distinct_key = 'db'
        cursor = self.ens_server.cursor()
        for t in ucsc_versions[self.ucsc_db]: # search rows until success
            if ens_prefix is None:
                # Note: this assumes 'source' in hgFixed.trackVersion contains
                # the URI of the Ensembl data set and that the last path component
                # of that URI is the species name of that data set.
                try:
                    ens_prefix1 = t.source.split('/')[-2]
                except IndexError:
                    continue
            else:
                ens_prefix1 = ens_prefix
            cursor.execute("show databases like '%s_core_%s_%%'" 
                           % (ens_prefix1, t.version))
            try:
                return cursor.fetchall()[0][0]
            except IndexError:
                pass
        raise KeyError(
                "Genome %s doesn't exist or has got no Ensembl data at UCSC" %
                self.ucsc_db)

    def get_gene_transcript_ids(self, gene_id):
        '''Obtain a list of stable IDs of transcripts associated
        with the specified gene.'''
        matching_edges = self.transcripts_in_genes_map[
            self.ucsc_ensGtp_gene[gene_id]]
        ids = []
        for transcript in matching_edges.keys():
            ids.append(transcript.name)
        return ids

    def get_annot_db(self, table, primaryKey='name',
                     sliceAttrDict=dict(id='chrom', start='chromStart',
                                        stop='chromEnd')):
        '''generic method to obtain an AnnotationDB for any
        annotation table in UCSC, e.g. snp130.  If your target table
        has non-standard name, start, end columns, specify them in
        the primaryKey and sliceAttrDict args.
        Saves table as named attribute on this package object.'''
        try: # return existing db if already cached here
            return getattr(self, table)
        except AttributeError:
            pass
        sliceDB = sqlgraph.SQLTable(self.ucsc_db + '.' + table,
                                    primaryKey=primaryKey,
                                    serverInfo=self.ucsc_server,
                                    itemClass=UCSCSeqIntervalRow)
        annoDB = annotation.AnnotationDB(sliceDB, self.genome_seq,
                                         checkFirstID=False,
                                         sliceAttrDict=sliceAttrDict)
        setattr(self, table, annoDB) # cache this db on named attribute
        return annoDB


class EnsemblTranscriptAnnotationSeqDescr(object):

    def __init__(self, attr):
        self.attr = attr

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
        seq = sequence.Sequence(trans_seq, obj.name)
        setattr(obj, self.attr, seq) # cache on object
        return seq


class EnsemblTranscriptAnnotationSeq(annotation.AnnotationSeq):
    '''An AnnotationSeq class for transcript annotations, implementing
    custom 'mrna_sequence' property.'''
    mrna_sequence = EnsemblTranscriptAnnotationSeqDescr('mrna_sequence')

    def get_exon_slices(self):
        '''Parse the provided transcript, extract exon data from it
        and return it as a dictionary of slices.'''
        chromosome = self.chrom
        exon_count = self.exonCount
        exon_starts = self.exonStarts.split(',')[:exon_count]
        exon_ends = self.exonEnds.split(',')[:exon_count]
        exons = {}
        exon_ids = self.get_ensembl_exon_ids()
        for i in range(exon_count):
            exons[exon_ids[i]] = (chromosome, exon_starts[i], exon_ends[i],
                                  self.orientation)
        return exons

    def get_ensembl_exon_ids(self):
        '''Obtain a list of stable IDs of exons associated with the
        specified transcript, ordered by rank.'''
        matching_edges = self.db.exons_map[self]
        return [exon.stable_id for exon in matching_edges.keys()]


class EnsemblProteinSeqDescr(object):

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        transcript = obj.db.gRes.protein_transcript_id_map[obj]
        pep = obj.db.gRes.ucsc_ensPep[transcript.name]
        seq = sequence.Sequence(str(pep), obj.id)
        setattr(obj, self.attr, seq) # cache on object
        return seq


class EnsemblProteinRow(sqlgraph.TupleO):
    sequence = EnsemblProteinSeqDescr('sequence')

    def __repr__(self):
        return str(self.id)


class EnsemblExonOnDemandSliceDB(object, UserDict.DictMixin):
    '''Obtains exon info on demand by looking up associated transcript '''

    def __init__(self, gRes):
        self.data = {}
        self.gRes = gRes

    def __getitem__(self, k):
        try:
            return self.data[k]
        except KeyError:
            # Not cached yet, extract the exon from transcript data.
            transcripts = self.gRes.ens_transcripts_of_exons_map2[
                self.gRes.ens_exon_stable_id[k]].keys()
            self.data.update(transcripts[0].get_exon_slices())
            # Cache whole transcript interval to speed sequence access
            self.gRes.genome_seq.cacheHint({transcripts[0].id:
                                           (transcripts[0].txStart,
                                            transcripts[0].txEnd)},
                                           transcripts[0])
            return self.data[k]

    __setitem__ = __delitem__ = read_only_error # Throws an exception

    def keys(self): # mirror iterator methods from exon stable ID table
        return self.gRes.ens_exon_stable_id.keys()

    def __iter__(self):
        return iter(self.gRes.ens_exon_stable_id)

    def __len__(self):
        return len(self.gRes.ens_exon_stable_id)
