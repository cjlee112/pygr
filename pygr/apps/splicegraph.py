
from sqlgraph import *

class ExonForm(TupleO): # ADD ATTRIBUTES TO THESE ONCE WE HAVE SCHEMA INFO
    pass
class Cluster(TupleO):
    pass
class Splice(TupleO):
    pass

# CREATE OUR GRAPHS
clusterExons=dictGraph()
clusterSplices=dictGraph()
spliceGraph=dictGraph()
alt5Graph=dictGraph()
alt3Graph=dictGraph()

def loadSpliceGraph(jun03,cluster_t,exon_t,splice_t,spliceGraph=spliceGraph,alt5=alt5Graph,
                    alt3=alt3Graph,clusterExons=clusterExons,clusterSplices=clusterSplices):
    """
    Build a splice graph from the specified SQL tables representing gene clusters,
    exon forms, and splices.  Each table must be specified as a DB.TABLENAME string.
    These tables are loaded into memory.
    The splice graph is built based on exact match of exon ends and splice ends.
    In addition, also builds alt5Graph (exons that match at start, but differ at end)
    and alt3Graph (exons that match at end, but differ at start).
    """
    exon_forms=jun03[exon_t]
    ExonForm._attrcol=exon_forms.data # NOW BIND THE SCHEMA INFORMATION
    ExonForm.__class_schema__=SchemaDict(((spliceGraph,'next'),(alt5,'alt5'),(alt3,'alt3')))
    print 'Loading %s...' % exon_forms
    exon_forms.load(ExonForm)

    clusters=jun03[cluster_t]
    Cluster._attrcol=clusters.data
    Cluster.__class_schema__=SchemaDict(((clusterExons,'exons'),(clusterSplices,'splices')))
    print 'Loading %s...' % clusters
    clusters.load(Cluster)

    splices=jun03[splice_t]
    Splice._attrcol=splices.data
    print 'Loading %s...' % splices
    splices.load(Splice)

    print 'Adding clusters to graph...'
    for c in clusters.values(): # ADD CLUSTERS AS NODES TO GRAPH
        clusterExons+=c
        clusterSplices+=c

    print 'Adding exons to graph...'
    for e in exon_forms.values():
        c=clusters[e.cluster_id]
        c.exons+=e
        spliceGraph+=e

    print 'Adding splices to graph...'
    for s in splices.values():
        try:
            c=clusters[s.cluster_id]
        except KeyError: # WIERD, ONE SPLICE WITH BLANK (NOT NULL) VALUE!
            pass
        else:
            c.splices+=s

    print 'Building splice graph...'
    none=[]
    for c in clusters.values():
        start={}
        end={}
        for e in c.exons:
            if e.genomic_start not in start:
                start[e.genomic_start]=[]
            start[e.genomic_start].append(e)
            if e.genomic_end not in end:
                end[e.genomic_end]=[]
            end[e.genomic_end].append(e)
        for s in c.splices:
            try:
                exons1=end[s.ver_gen_start]
            except KeyError:
                exons1=none
            try:
                exons2=start[s.ver_gen_end]
            except KeyError:
                exons2=none
            for e1 in exons1:
                for e2 in exons2:
                    e1.next[e2]=s # SAVE SPLICE AS EDGE INFO...
        for exons in start.values():
            for e1 in exons:
                for e2 in exons:
                    if e1!=e2:
                        alt5+=e1
                        alt5+=e2
                        e1.alt5+=e2
                        e2.alt5+=e1
        for exons in end.values():
            for e1 in exons:
                for e2 in exons:
                    if e1!=e2:
                        alt3+=e1
                        alt3+=e2
                        e1.alt3+=e2
                        e2.alt3+=e1

    return clusters,exons,splices

