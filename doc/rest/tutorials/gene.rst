
===========================
Constructing Gene Databases
===========================

Purpose
-------

This tutorial shows you how to build a splice graph representing
a gene's exons and splicing structure,
using simple interval information or a GFF3 formatted file.
You should be familiar with Pygr annotations (see :doc:`annotation2`).


Building a Simple Gene & Exon Database
--------------------------------------

Let's say we want to build a gene database consisting of exons and
splicing structures for all the transcript isoforms.  Our first
step would be to construct a little "database" that annotates some
exons on our genome::

   from pygr import annotation, mapping
   from pygr import worldbase
   hg17 = worldbase.Bio.Seq.Genome.HUMAN.hg17()
   exonSlices = {1:('chr1', 1000, 1300), 2:('chr1', 2000, 2099),
                 3:('chr1', 3000, 3600)}
   exons = annotation.AnnotationDB(exonSlices, hg17, 
                                   sliceAttrDict=dict(id=0, start=1, stop=2))
   exon = exons[1]
   print repr(exon), repr(exon.sequence), exon.sequence

This prints::

   annot1[0:300] cctcagtaatccgaaaagccgggatcgaccgccccttgcttgcagccgggcactacaggacccgcttgctcacggtgctgtgccagggcgccccctgctggcgactagggcaactgcagggctctcttgcttagagtggtggccagcgccccctgctggcgccggggcactgcagggccctcttgcttactgtatagtggtggcacgccgcctgctggcagctagggacattgcagggtcctcttgctcaaggtgtagtggcagcacgcccacctgctggcagctggggacactgccggg


Note that since ``print`` converts its arguments to strings by default,
Pygr's methods for retrieving a slice of the human genome sequence
are automatically invoked on the third argument above.

Next, let's create a splicing graph for the exon-skip and exon-inclusion
isoforms.  This is a *many-to-many mapping*, i.e. each exon can be
spliced *to* multiple downstream exons, and each exon can be spliced
*from* multiple upstream exons.  A standard Python dict can only handle
X-to-one mappings (i.e. each exon maps to a unique exon), not
many-to-many relations, so Pygr adopts the convention of representing
graphs as two-level dictionary interfaces, 
i.e. ``graph[node1][node2]=edge``.  

Let's say we have three exons that produce two isoforms via 
exon-skipping of the central exon.
So here is a basic graph that connects
exon 1 to exons 2 and 3, and exon 2 to exon 3 (with no edge information)::

   spliceGraph = {exons[1]:{exons[2]:None, exons[3]:None}, 
                  exons[2]:{exons[3]:None}}


Next let's write a simple function to generate all possible isoforms
by walking the splice graph, starting from exon 1::

   def walk_graph(graph, node, results, path=()):
      try:
         for node2 in graph[node]:
            walk_graph(graph, node2, results, path + (node,))
      except KeyError: # end node, so save complete path
         results.append(path + (node,))

   isoforms = []
   walk_graph(spliceGraph, exons[1], isoforms) # generate isoforms
   for i,transcript in enumerate(isoforms):
      s = ''.join([str(exon.sequence) for exon in transcript])
      print 'isoform %d: %s' % (i, s)

This yields the output::

   isoform 0: cctcagtaatccgaaaagccgggatcgaccgccccttgcttgcagccgggcactacaggacccgcttgctcacggtgctgtgccagggcgccccctgctggcgactagggcaactgcagggctctcttgcttagagtggtggccagcgccccctgctggcgccggggcactgcagggccctcttgcttactgtatagtggtggcacgccgcctgctggcagctagggacattgcagggtcctcttgctcaaggtgtagtggcagcacgcccacctgctggcagctggggacactgccgggTACCTGAGGCTGAGGAAGGAGAAGGGGATGCACTGTTGGGGAGGCAGCTGTAACTCAAAGCCTTAGCCTCTGTTCCCACGAAGGCAGGGCCATCAGGCACCAAAGGGATTCTGCCAGCATAGTGCTCCTGGACCAGTGATACACCCGGCACCCTGTCCTGGACACGCTGTTGGCCTGGATCTGAGCCCTGGTGGAGGTCAAAGCCACCTTTGGTTCTGCCATTGCTGCTGTGTGGAAGTTCACTCCTGCCTTTTCCTTTCCCTAGAGCCTCCACCACCCCGAGATCACATTTCTCACTGCCTTTTGTCTGCCCAGTTTCACCAGAAGTAGGCCTCTTCCTGACAGGCAGCTGCACCACTGCCTGGCGCTGTGCCCTTCCTTTGCTCTGCCCGCTGGAGACGGTGTTTGTCATGGGCCTGGTCTGCAGGGATCCTGCTACAAAGGTGAAACCCAGGAGAGTGTGGAGTCCAGAGTGTTGCCAGGACCCAGGCACAGGCATTAGTGCCCGTTGGAGAAAACAGGGGAATCCCGAAGAAATGGTGGGTCCTGGCCATCCGTGAGATCTTCCCAGGGCAGCTCCCCTCTGTGGAATCCAATCTG
   isoform 1: cctcagtaatccgaaaagccgggatcgaccgccccttgcttgcagccgggcactacaggacccgcttgctcacggtgctgtgccagggcgccccctgctggcgactagggcaactgcagggctctcttgcttagagtggtggccagcgccccctgctggcgccggggcactgcagggccctcttgcttactgtatagtggtggcacgccgcctgctggcagctagggacattgcagggtcctcttgctcaaggtgtagtggcagcacgcccacctgctggcagctggggacactgccgggCTGCATGTAACTTAATACCACAACCAGGCATAGGGGAAAGATTGGAGGAAAGATGAGTGAGAGCATCAACTTCTCTCACAACCTAGGCCAGTAAGTAGTTACCTGAGGCTGAGGAAGGAGAAGGGGATGCACTGTTGGGGAGGCAGCTGTAACTCAAAGCCTTAGCCTCTGTTCCCACGAAGGCAGGGCCATCAGGCACCAAAGGGATTCTGCCAGCATAGTGCTCCTGGACCAGTGATACACCCGGCACCCTGTCCTGGACACGCTGTTGGCCTGGATCTGAGCCCTGGTGGAGGTCAAAGCCACCTTTGGTTCTGCCATTGCTGCTGTGTGGAAGTTCACTCCTGCCTTTTCCTTTCCCTAGAGCCTCCACCACCCCGAGATCACATTTCTCACTGCCTTTTGTCTGCCCAGTTTCACCAGAAGTAGGCCTCTTCCTGACAGGCAGCTGCACCACTGCCTGGCGCTGTGCCCTTCCTTTGCTCTGCCCGCTGGAGACGGTGTTTGTCATGGGCCTGGTCTGCAGGGATCCTGCTACAAAGGTGAAACCCAGGAGAGTGTGGAGTCCAGAGTGTTGCCAGGACCCAGGCACAGGCATTAGTGCCCGTTGGAGAAAACAGGGGAATCCCGAAGAAATGGTGGGTCCTGGCCATCCGTGAGATCTTCCCAGGGCAGCTCCCCTCTGTGGAATCCAATCTG

Loading Gene Data from GFF3 Files
---------------------------------

Now let's move on from "toy examples" to something a bit more useful:
reading gene annotations in the standard GFF3 format, a tab-separated
format that looks like this::

    ##gff-version   3
    ##sequence-region   ctg123 1 1497228       
    ctg123 . gene            1000  9000  .  +  .  ID=gene00001;Name=EDEN
    ctg123 . TF_binding_site 1000  1012  .  +  .  ID=tfbs00001;Parent=gene00001
    ctg123 . mRNA            1050  9000  .  +  .  ID=mRNA00001;Parent=gene00001;Name=EDEN.1
    ctg123 . mRNA            1050  9000  .  +  .  ID=mRNA00002;Parent=gene00001;Name=EDEN.2
    ctg123 . mRNA            1300  9000  .  +  .  ID=mRNA00003;Parent=gene00001;Name=EDEN.3
    ctg123 . exon            1300  1500  .  +  .  ID=exon00001;Parent=mRNA00003
    ctg123 . exon            1050  1500  .  +  .  ID=exon00002;Parent=mRNA00001,mRNA00002
    ctg123 . exon            3000  3902  .  +  .  ID=exon00003;Parent=mRNA00001,mRNA00003
    ctg123 . exon            5000  5500  .  +  .  ID=exon00004;Parent=mRNA00001,mRNA00002,mRNA00003
    ctg123 . exon            7000  9000  .  +  .  ID=exon00005;Parent=mRNA00001,mRNA00002,mRNA00003
    ctg123 . CDS             1201  1500  .  +  0  ID=cds00001;Parent=mRNA00001;Name=edenprotein.1
    ctg123 . CDS             3000  3902  .  +  0  ID=cds00001;Parent=mRNA00001;Name=edenprotein.1
    ctg123 . CDS             5000  5500  .  +  0  ID=cds00001;Parent=mRNA00001;Name=edenprotein.1
    ctg123 . CDS             7000  7600  .  +  0  ID=cds00001;Parent=mRNA00001;Name=edenprotein.1
    ctg123 . CDS             1201  1500  .  +  0  ID=cds00002;Parent=mRNA00002;Name=edenprotein.2
    ctg123 . CDS             5000  5500  .  +  0  ID=cds00002;Parent=mRNA00002;Name=edenprotein.2
    ctg123 . CDS	     7000  7600	 .  +  0  ID=cds00002;Parent=mRNA00002;Name=edenprotein.2
    ctg123 . CDS             3301  3902  .  +  0  ID=cds00003;Parent=mRNA00003;Name=edenprotein.3
    ctg123 . CDS	     5000  5500	 .  +  1  ID=cds00003;Parent=mRNA00003;Name=edenprotein.3
    ctg123 . CDS	     7000  7600	 .  +  2  ID=cds00003;Parent=mRNA00003;Name=edenprotein.3
    ctg123 . CDS             3391  3902  .  +  0  ID=cds00004;Parent=mRNA00003;Name=edenprotein.4
    ctg123 . CDS	     5000  5500	 .  +  1  ID=cds00004;Parent=mRNA00003;Name=edenprotein.4
    ctg123 . CDS	     7000  7600	 .  +  2  ID=cds00004;Parent=mRNA00003;Name=edenprotein.4

First we need a basic GFF3 row class that Pygr can use as annotation slice
info::

   class GFF3Row(object):
      def __init__(self, line):
         cols = line.split()
         self.type = cols[2]
         self.id = cols[0] # sequence ID
         self.start = int(cols[3]) - 1 # correct for 1-based coords
         self.stop = int(cols[4])
         if cols[6] == '+': # convert to Pygr convention
            self.orientation = 1
         elif cols[6] == '-':
            self.orientation = -1
         else:
            raise ValueError('Bad strand: %s' % cols[6])
         for s in cols[8].split(';'): # parse attributes
            attr,val = s.split('=')
            if ',' in val:
               setattr(self, attr, val.split(','))
            else:
               setattr(self, attr, val)


The key fields this must provide to be used as slice info
are id, start, stop, and orientation.


Next, let's write a reader that will read all the annotations in 
a GFF3 file::

   def read_gff3(filename, genome):
      d = {} # for different types of sliceDBs
      ifile = file(filename)
      for line in ifile: # parse all the GFF3 lines
         if line.startswith('#'): # ignore this line
            continue
         row = GFF3Row(line)
         try:
            d.setdefault(row.type, {})[row.ID] = row
         except AttributeError:
            pass # no type or ID so ignore...
      ifile.close()
      annotations = {}
      for atype,sliceDB in d.items(): # create annotation DBs
         adb = annotation.AnnotationDB(sliceDB, genome)
         annotations[atype] = adb
      return annotations

Now we can read a file and turn it into annotation databases as easily
as::

   annots = read_gff3('eden.gff3', genome)
   print 'annotation types:', len(annots)
   print 'mRNAs:', len(annots['mRNA'])

TO DO
-----

* for each mRNA, make a list of its exons

* create splicegraph

* create NLMSAs that reverse the mapping?

* how to map CDS?

* save to worldbase

