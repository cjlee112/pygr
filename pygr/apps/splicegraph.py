from pygr.sqlgraph import *
from pygr.sequence import *
from pygr.seqdb import *


def buildClusterSpliceGraph(c, alt5, alt3):
    """use exon/splice start and end positions to build splice graph
    for a cluster c. Also finds exons that share same start (but differ
    at end: alt5), or share the same end (but differ at start: alt3)."""
    start = {}
    end = {}
    none = []
    for e in c.exons:
        if e.genomic_start not in start:
            start[e.genomic_start] = []
        start[e.genomic_start].append(e)
        if e.genomic_end not in end:
            end[e.genomic_end] = []
        end[e.genomic_end].append(e)
    for s in c.splices:
        try:
            exons1 = end[s.ver_gen_start]
        except KeyError:
            exons1 = none
        try:
            exons2 = start[s.ver_gen_end]
        except KeyError:
            exons2 = none
        for e1 in exons1:
            for e2 in exons2:
                e1.next[e2] = s # SAVE SPLICE AS EDGE INFO...
                s.exons = (e1, e2) # SAVE EXONS DIRECTLY ON THE SPLICE OBJECT
    for exons in start.values():
        for e1 in exons:
            for e2 in exons:
                if e1 != e2:
                    alt5 += e1
                    alt5 += e2
                    e1.alt5 += e2
                    e2.alt5 += e1
    for exons in end.values():
        for e1 in exons:
            for e2 in exons:
                if e1 != e2:
                    alt3 += e1
                    alt3 += e2
                    e1.alt3 += e2
                    e2.alt3 += e1


def loadCluster(c, exon_forms, splices, clusterExons, clusterSplices,
                spliceGraph, alt5, alt3):
    """Loads data for a single cluster, and builds it into a splice graph."""
    clusterExons += c
    clusterSplices += c
    for e in exon_forms.select('where cluster_id=%s', (c.id, )):
        c.exons += e
        spliceGraph += e
    for s in splices.select('where cluster_id=%s', (c.id, )):
        c.splices += s
    buildClusterSpliceGraph(c, alt5, alt3)


class ExonForm(TupleO, SeqPath): # ADD ATTRIBUTES STORING SCHEMA INFO

    def __init__(self, t):
        TupleO.__init__(self, t) # 1ST INITIALIZE ATTRIBUTE ACCESS
        SeqPath.__init__(self, g[self.cluster_id], # INITIALIZE AS SEQ INTERVAL
                         self.genomic_start - 1, self.genomic_end)

    def __getattr__(self, attr):
        'both parent classes have getattr, so have to call them both...'
        try:
            return TupleO.__getattr__(self, attr)
        except AttributeError:
            return SeqPath.__getattr__(self, attr)


class Splice(TupleO):
    pass


def loadSpliceGraph(jun03, cluster_t, exon_t, splice_t, genomic_seq_t,
                    mrna_seq_t=None, protein_seq_t=None, loadAll=True):
    """
    Build a splice graph from the specified SQL tables representing gene
    clusters, exon forms, and splices. Each table must be specified
    as a DB.TABLENAME string.
    These tables are loaded into memory.
    The splice graph is built based on exact match of exon and splice ends.
    In addition, also builds alt5Graph (exons that match at start but differ
    at end) and alt3Graph (exons that match at end but differ at start).

    Loads all cluster, exon and splice data if loadAll is True.

    Returns tuple: clusters, exons, splices, spliceGraph, alt5Graph, alt3Graph
    """

    # CREATE OUR GRAPHS
    clusterExons = dictGraph()
    clusterSplices = dictGraph()
    spliceGraph = dictGraph()
    alt5 = dictGraph()
    alt3 = dictGraph()

    class YiGenomicSequence(DNASQLSequence):

        def __len__(self):
            return self._select('length(seq)')  # USE SEQ LENGTH FROM DATABASE

    g = jun03[genomic_seq_t]
    # Force genomic seq table to use transparent access
    g.objclass(YiGenomicSequence)

    # Only process this if provided an mRNA table by the user.
    if mrna_seq_t is not None:
        mrna = jun03[mrna_seq_t]
        # Force mRNA seq table to use transparent access.
        mrna.objclass(SQLSequence)
    else:
        mrna = None

    # Only process this if provided a protein table by the user.
    if protein_seq_t is not None:

        class YiProteinSQLSequence(ProteinSQLSequence):

            def __len__(self):
                return self.protein_length # USE SEQ LENGTH FROM DATABASE

        protein = jun03[protein_seq_t]
        # Force protein seq table to use transparent access
        protein.objclass(YiProteinSQLSequence)
        # Alias 'protein_seq' to appear as 'seq'
        protein.addAttrAlias(seq='protein_seq')
    else:
        protein = None

    exon_forms = jun03[exon_t]
    ExonForm.__class_schema__ = SchemaDict(((spliceGraph, 'next'),
                                            (alt5, 'alt5'), (alt3, 'alt3')))
    # Bind this class to container as the one to use as "row objects".
    exon_forms.objclass(ExonForm)

    if loadAll:
        print 'Loading %s...' % exon_forms
        exon_forms.load(ExonForm)

    clusters = jun03[cluster_t]

    class Cluster(TupleO):
        __class_schema__ = SchemaDict(((clusterExons, 'exons'),
                                       (clusterSplices, 'splices')))
    # Bind this class to container as the one to use as "row objects".
    clusters.objclass(Cluster)
    if loadAll:
        print 'Loading %s...' % clusters
        clusters.load(Cluster)

    splices = jun03[splice_t]
    # Bind this class to container as the one to use as "row objects".
    splices.objclass(Splice)
    if loadAll:
        print 'Loading %s...' % splices
        splices.load(Splice)

##     print 'Saving alignment of protein to mrna isoforms...'
##     mrna_protein=PathMapping2()
##     for form_id in protein:
##         p=protein[form_id]
##         m=mrna[form_id]
##         start=3*(p.mRNA_start-1)+int(p.reading_frame)
##         end=start+3*p.protein_length
##         mrna_protein[p]=m[start:end]

        print 'Adding clusters to graph...'
        for c in clusters.values(): # ADD CLUSTERS AS NODES TO GRAPH
            clusterExons+=c
            clusterSplices+=c

        print 'Adding exons to graph...'
        for e in exon_forms.values():
            c=clusters[e.cluster_id]
            try:
                c.exons+=e
                spliceGraph+=e
            except IndexError:
                pass # BAD EXON: EMPTY SEQUENCE INTERVAL... IGNORE IT

        print 'Adding splices to graph...'
        for s in splices.values():
            try:
                c=clusters[s.cluster_id]
            except KeyError: # WIERD, ONE SPLICE WITH BLANK (NOT NULL) VALUE!
                pass
            else:
                c.splices+=s

        print 'Building splice graph...'
        for c in clusters.values():
            buildClusterSpliceGraph(c, alt5, alt3)

    return clusters, exon_forms, splices, g, spliceGraph, alt5, alt3, mrna,\
            protein, clusterExons, clusterSplices
