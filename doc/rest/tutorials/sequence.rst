.. _seq-align:

======================
Working With Sequences
======================


Purpose
^^^^^^^
This tutorial will teach you how to work with sequence data in Pygr,
using different classes that either store the data in memory, on
disk, or accessed from a remote XMLRPC or SQL server.  No previous
knowledge of Pygr is required.

Pygr Sequence Objects
^^^^^^^^^^^^^^^^^^^^^

Python already provides a "sequence protocol" that is familiar to all 
Python programmers as lists, tuples, etc.  
So, naturally, Pygr follows this design pattern for
representing biological sequences.

Let's create a sequence object in memory::

   >>> from pygr.sequence import *
   >>> s = Sequence('attatatgccactat','bobo') #create a sequence named bobo
   >>> s # interpreter will print repr(s)
   bobo[0:15]

Slices of a sequence object (e.g. ``s[1:10]`` or ``s[-8:]``) 
are themselves sequence-like objects.  All of the operations 
that you can do to a :class:`sequence.Sequence` object, you
can also do to a sequence slice object, e.g. slicing, negation etc.::

   >>> t = s[-8:] #python slice gives last 8 nt of s
   >>> t # interpreter will print repr(t)
   bobo[7:15]

Of course, Pygr stores the actual string data only once, in
your original :class:`sequence.Sequence` object.  If you make
slices of the original sequence object, they simply *refer*
to the original data, rather than copying it. In other words,
these objects are a *representation* of the sequence data
rather than themselves *storing* the data.  This is a general
principle in Pygr: Pygr objects are a system of *representation*,
decoupled from fixed assumptions about *storage*.  That is a crucial
requirement for scalability, which makes it as easy in Pygr to work
with the entire human genome as with a 15 nt sequence.

The string value of a sequence object (e.g. ``str(s)``) is just 
the sequence itself (as a string)::

   >>> str(t) #returns the sequence interval as a string
   'gccactat'
   >>> len(t) # get sequence length
   8

Like a regular Python slice object, Pygr sequence slice objects have
``start``, ``stop`` atttributes.  Like Python slice coordinates,
they are zero-based, i.e. ``[0:10]`` means the first ten letters
of a sequence.  (for more details, see :attr:`sequence.start` and
:attr:`sequence.stop`)::

   >>> print t.start, t.stop, t.orientation
   7 15 1

Because nucleotide sequences
can be double-stranded, sequence objects also provide an
:attr:`sequence.orientation` attribute, which will be either 1 (referring
to the same orientation as the original sequence object)
or -1 (the reverse complement of the original sequence object).
  
Where appropriate, Pygr uses Python's math operators for
standard operations on sequences.  For example, Pygr uses negation
to obtain the "reverse strand" for a given sequence slice::

   >>> rc = -s #get the reverse complement
   >>> str(rc[:5]) #its first five letters
   'atagt'

Relations between sequences
^^^^^^^^^^^^^^^^^^^^^^^^^^^

What if you have a sequence slice and want to find out what 
sequence it's a part of, or ask questions about its relationship
with other sequence slices?  Pygr makes this easy::

   >>> t.path
   bobo[0:15]
   >>> t.path is t
   False
   >>> s.path is s
   True

The :attr:`sequence.path` attribute always gives the "whole
sequence" object that your slice is part of.

You can compare sequence slices to test their relative
positions, or whether one contains the other::

   >>> t in s
   True
   >>> s[:3] < t
   True
   >>> s[3:5] + t # get enclosing interval 
   bobo[3:15]

Note that :attr:`sequence.path`
is always on the same strand as your slice, so if your slice
is negative orientation, so is its ``path``::

   >>> u = -t
   >>> u
   -bobo[7:15]
   >>> u.path
   -bobo[0:15]

If you want to get the original sequence (i.e. both whole
and in its original (positive) orientation), use the
:attr:`sequence.pathForward` attribute::

   >>> u.pathForward
   bobo[0:15]

Working with Sequences from a FASTA File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Ordinarily, you'll probably be working with sequences from some external
source, like a FASTA file.  Pygr makes this quite straightforward.
Try the following in the pygr/tests directory::

   >>> from pygr import seqdb
   >>> sp = seqdb.SequenceFileDB('data/sp_hbb1')

Since FASTA files can contain multiple sequences, 
:class:`seqdb.SequenceFileDB` acts like a dictionary whose keys are
the IDs of the sequences in your FASTA file, and whose associated
values are the sequence objects themselves::

   >>> len(sp)
   24
   >>> sp.keys()
   ['HBB0_PAGBO', 'HBB1_ANAMI', 'HBB1_CYGMA', 'HBB1_IGUIG', 'HBB1_MOUSE', 'HBB1_ONCMY', 'HBB1_PAGBO', 'HBB1_RAT', 'HBB1_SPHPU', 'HBB1_TAPTE', 'HBB1_TORMA', 'HBB1_TRICR', 'HBB1_UROHA', 'HBB1_VAREX', 'HBB1_XENBO', 'HBB1_XENLA', 'HBB1_XENTR', 'MYG_DIDMA', 'MYG_ELEMA', 'MYG_ERIEU', 'MYG_ESCGI', 'MYG_GALCR', 'PRCA_ANASP', 'PRCA_ANAVA']

Let's get a sequence::

   >>> pagbo = sp['HBB1_PAGBO']
   >>> len(pagbo)
   146
   >>> print pagbo
   VEWTDKERSIISDIFSHLDYEDIGPKALSRCLIVYPWTQRHFSGFGNLYNAESIIGNANVAAHGIKVLHGLDRGLKNMDNIEATYADLSTLHSEKLHVDPDNFKLLADCITIVLAAKMGQAFTAEIQGAFQKFLAVVVSALGKQYH

Note that even though we obtained this sequence in a completely
different way than our first example (from a file, rather than by
creating it in memory), the interface is *exactly the same*.  Any 
standard sequence operator works equally well with any of Pygr's
various sequence classes.  For example, we can slice, compare, 
look at attributes as usual::

   >>> t = pagbo[20:-30]
   >>> len(t)
   96
   >>> t in s
   False
   >>> t in pagbo
   True
   >>> t.start, t.stop, t.orientation
   (20, 116, 1)

What would happen if we tried to get the "reverse strand" of
this sequence?  Let's find out::

   >>> -t
   Traceback (most recent call last):
     File "<stdin>", line 1, in <module>
     File "/Users/leec/projects/pygr/pygr/sequence.py", line 408, in __neg__
       raise ValueError('protein sequence has no reverse orientation!')
   ValueError: protein sequence has no reverse orientation!

This seems like a good time to introduce a general principle in Pygr:
whenever a Pygr object is part of a "database" (a collection of data that all
obey the same schema), it will have an ``id`` attribute that gives its
unique identifier in that database, and a ``db`` attribute that points
to the database object that contains it::

   >>> t.id
   'HBB1_PAGBO'
   >>> t.db
   <SequenceFileDB 'data/sp_hbb1'>
   >>> t.db is sp
   True

Note that these attributes are automatically mirrored on slices of a
sequence (as in the example above), not just on the original "whole"
sequence objects.

Let's introduce another general principle: for any Pygr mapping, you can
get its reverse mapping using Python's standard invert operator, ~.  
That is, if we have a forward mapping ``forward``, we can get its
reverse mapping via ``reverse = ~forward``.  Then if ``forward[a] == b``
then ``reverse[b] == a``.  Let's see how that applies to our
sequence database::

   >>> idDict = ~sp
   >>> idDict[t]
   'HBB1_PAGBO'

In this case the reverse mapping is pretty trivial -- it returns the
same value as ``t.id``.  But later we will see cases where reverse mappings
are extremely useful.

When you're done using a :class:`seqdb.SequenceFileDB`, 
you should ``close()`` it, just like any other open file resource::

   >>> sp.close()

Closing every file when you are done with it is a good practice,
because some operating systems can behave very strangely if you don't...

Working with Sequences from Worldbase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pygr provides a lot of capabilities for accessing datasets over
remote protocols such as XMLRPC or SQL.  It wraps these up in a convenient
interface called :mod:`worldbase` that lets you ask for datasets
by name, and immediately start working with them::

   >>> from pygr import worldbase
   >>> worldbase.dir('Bio.Seq.Genome.HUMAN')
   ['Bio.Seq.Genome.HUMAN.hg17', 'Bio.Seq.Genome.HUMAN.hg18', 'Bio.Seq.Genome.HUMAN.hg19']

This shows us the set of datasets in this part of the worldbase namespace,
retrieved care of the public worldbase server at UCLA.
Let's get human genome draft 17.  We do this by simply asking it to
construct an instance of this data from the worldbase namespace::

   >>> hg17 = worldbase.Bio.Seq.Genome.HUMAN.hg17()

Notice that connecting to this dataset was more or less instantaneous.
It is setting up a *representation* of the genome for us to use; 
the actual storage of the data (in this case) remains on the server.
Now we can work with the data in all the usual ways::

   >>> len(hg17)
   46
   >>> hg17.keys()
   ['chr6_random', 'chr19_random', 'chr8_random', 'chrY', 'chrX', 'chr13', 'chr12', 'chr11', 'chr15_random', 'chr17', 'chr16', 'chr15', 'chr14', 'chr19', 'chr18', 'chrM', 'chr1_random', 'chr13_random', 'chr3_random', 'chr6_hla_hap2', 'chr9_random', 'chr22_random', 'chr10', 'chr4_random', 'chr18_random', 'chr2_random', 'chr22', 'chr20', 'chr21', 'chr10_random', 'chr6_hla_hap1', 'chr7', 'chr6', 'chr5', 'chr4', 'chr3', 'chr2', 'chr1', 'chr7_random', 'chrX_random', 'chr9', 'chr8', 'chr16_random', 'chr5_random', 'chr17_random', 'chr12_random']
   >>> chr1 = hg17['chr1']
   >>> len(chr1)
   245522847
   >>> s = chr1[100000000:100001000]
   >>> len(s)
   1000
   >>> repr(s)
   'chr1[100000000:100001000]'
   >>> print s
   ATTCAGGCAATGTTGACTTCATTAGTGTTGACAGAAAATAAGCATAAAAATGCAAAACATTGTTGGCTTAACCTGAATATACCTGCATTACCTATTATTAACCAGTTTGTGTTGCCAAAAGACTTATTCCTTGGCATTAAAATGGAGCACTTAAAAATATTTCTAAAAAGCAAATGCCCACACGCTGGTCTTTGCAGCAAATAAGGGTATTTATACTTTTAAAATATTTTAAGTCCATAATTGGATTAATATACACACCTTCTTATGTATAAGGAGTTCAGATCATATAAACACCGTACAATCCAAAAAACCCTACTGAGAATAAAACTAAATAGGCTTATGATAAGAAATACAGATATTCCCATGTATTTACAAATATCATAGACACACAAATTTGGTCAAATACTGTAAAGAAAGAAGAAGtacctgtacctctacctctacctctacctcctctacctcctctacctcctctacctcctctacctcctctacctcctcttcctctacctctacctctacctctacctctacccacggtctccctttccctctctttccacggtctccctctgatgccgagccgaagctggactgtactgctgccatctcggctcactgcaacctccctgcctgattctcctgcctcaacctgccgagtgcctgcgattgcaggcgcgcgccgccacgcctgactggttttcgtatttttttggtggagacggggtttcgctgtgttggccgggctggtctccagctcctaacctcgagtgatccgccagcctcggcctcccgaggtgccgggtttgcagaggagtctcattcactcagtgctcaatggtgcccaggctggagtgcagtggcgtgatctcggctcgctacaacctccacctcccagcagcctgccttggcctcccaaagtgccgagattgcagtctccgcccggctgccaccccatctgggaagtgaggagcatctctgcctggccgcccatcgtctg

Again, note that all of these operations were more or less instantaneous
(even over the network).  These Pygr objects (``chr1``, ``s``) are just
abstract representations of the specified pieces of the human genome,
so creating these objects *does not* require Pygr to download all of human
chromosome 1.  Only when you force it to show a sequence string does Pygr
obtain that data over the network -- and then only the piece that you need.


Pygr is Obsessed with Scalability
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Actually, all of the above statements are equally true for the 
:class:`seqdb.SequenceFileDB` interface we introduced in the previous
section:

* opening the :class:`seqdb.SequenceFileDB` *does not* read all its
  data into memory.  You can open the ``hg17`` human genome database
  using :class:`seqdb.SequenceFileDB`, and it will hardly take up
  any memory.  Equally well, you could open all 44 vertebrate genomes
  in the UCSC 44 vertebrate genome alignment, on a laptop (assuming
  your laptop had enough disk space to store them all) -- and it
  still would hardly take any memory.

* how many genome datasets can you work with simultaneously in practice?
  For a simple example, just take a look at the :mod:`worldbase` server.
  It serves genome sequences and alignments by simply opening all of them
  as Pygr objects (:class:`seqdb.SequenceFileDB` and 
  :class:`cnestedlist.NLMSA`).  With all these objects loaded in Pygr,
  it then serves XMLRPC requests to query its different individual
  datasets.  So how many datasets does that one machine serve 
  simultaneously?  Run the query yourself to see the answer::

     >>> worldbase.dir()
     ['0root', 'Bio.MSA.UCSC.bosTau2ToBostau3', 'Bio.MSA.UCSC.bosTau3ToBostau4', 'Bio.MSA.UCSC.bosTau4_multiz5way', 'Bio.MSA.UCSC.bosTau4_pairwiseCanFam2', 'Bio.MSA.UCSC.bosTau4_pairwiseHg18', 'Bio.MSA.UCSC.bosTau4_pairwiseMm9', 'Bio.MSA.UCSC.bosTau4_pairwiseOrnAna1', 'Bio.MSA.UCSC.braFlo1_multiz5way', 'Bio.MSA.UCSC.braFlo1_pairwiseGalGal3', 'Bio.MSA.UCSC.braFlo1_pairwiseHg18', 'Bio.MSA.UCSC.braFlo1_pairwiseMm9', 'Bio.MSA.UCSC.braFlo1_pairwisePetMar1', 'Bio.MSA.UCSC.calJac1_multiz9way', 'Bio.MSA.UCSC.calJac1_pairwiseCanFam2', 'Bio.MSA.UCSC.calJac1_pairwiseHg18', 'Bio.MSA.UCSC.calJac1_pairwiseHg19', 'Bio.MSA.UCSC.calJac1_pairwiseMm9', 'Bio.MSA.UCSC.calJac1_pairwiseMonDom4', 'Bio.MSA.UCSC.calJac1_pairwiseOrnAna1', 'Bio.MSA.UCSC.calJac1_pairwisePanTro2', 'Bio.MSA.UCSC.calJac1_pairwisePonAbe2', 'Bio.MSA.UCSC.calJac1_pairwiseRheMac2', 'Bio.MSA.UCSC.canFam2_multiz4way', 'Bio.MSA.UCSC.canFam2_pairwiseBosTau4', 'Bio.MSA.UCSC.canFam2_pairwiseCalJac1', 'Bio.MSA.UCSC.canFam2_pairwiseEquCab1', 'Bio.MSA.UCSC.canFam2_pairwiseFelCat3', 'Bio.MSA.UCSC.canFam2_pairwiseHg17', 'Bio.MSA.UCSC.canFam2_pairwiseHg18', 'Bio.MSA.UCSC.canFam2_pairwiseMm6', 'Bio.MSA.UCSC.canFam2_pairwiseMm7', 'Bio.MSA.UCSC.canFam2_pairwiseMm8', 'Bio.MSA.UCSC.canFam2_pairwiseMm9', 'Bio.MSA.UCSC.canFam2_pairwiseRn3', 'Bio.MSA.UCSC.canFam2_pairwiseRn4', 'Bio.MSA.UCSC.cavPor3_pairwiseGalGal3', 'Bio.MSA.UCSC.cavPor3_pairwiseHg18', 'Bio.MSA.UCSC.cavPor3_pairwiseMm9', 'Bio.MSA.UCSC.cavPor3_pairwiseMonDom4', 'Bio.MSA.UCSC.cavPor3_pairwiseOryCun1', 'Bio.MSA.UCSC.cavPor3_pairwiseRn4', 'Bio.MSA.UCSC.ce2ToCe4', 'Bio.MSA.UCSC.ce4_multiz5way', 'Bio.MSA.UCSC.ce6_multiz6way', 'Bio.MSA.UCSC.danRer2ToDanrer3', 'Bio.MSA.UCSC.danRer3ToDanrer2', 'Bio.MSA.UCSC.danRer3ToDanrer4', 'Bio.MSA.UCSC.danRer3_multiz5way', 'Bio.MSA.UCSC.danRer4ToDanrer3', 'Bio.MSA.UCSC.danRer4ToDanrer5', 'Bio.MSA.UCSC.danRer4_multiz7way', 'Bio.MSA.UCSC.danRer4_pairwiseFr1', 'Bio.MSA.UCSC.danRer4_pairwiseFr2', 'Bio.MSA.UCSC.danRer4_pairwiseGalGal3', 'Bio.MSA.UCSC.danRer4_pairwiseGasAcu1', 'Bio.MSA.UCSC.danRer4_pairwiseHg18', 'Bio.MSA.UCSC.danRer4_pairwiseMm8', 'Bio.MSA.UCSC.danRer4_pairwiseMonDom4', 'Bio.MSA.UCSC.danRer4_pairwiseOryLat1', 'Bio.MSA.UCSC.danRer4_pairwiseRn4', 'Bio.MSA.UCSC.danRer4_pairwiseTetNig1', 'Bio.MSA.UCSC.danRer4_pairwiseXenTro2', 'Bio.MSA.UCSC.danRer5ToDanrer4', 'Bio.MSA.UCSC.danRer5_pairwiseFr2', 'Bio.MSA.UCSC.danRer5_pairwiseHg18', 'Bio.MSA.UCSC.danRer5_pairwiseMm9', 'Bio.MSA.UCSC.danRer5_pairwiseOryLat1', 'Bio.MSA.UCSC.danRer5_pairwiseOryLat2', 'Bio.MSA.UCSC.danRer5_pairwiseTetNig1', 'Bio.MSA.UCSC.dm2ToDm3', 'Bio.MSA.UCSC.dm2_multiz15way', 'Bio.MSA.UCSC.dm2_multiz9way', 'Bio.MSA.UCSC.dm3_multiz15way', 'Bio.MSA.UCSC.felCat3_multiz4way', 'Bio.MSA.UCSC.felCat3_pairwiseCanFam2', 'Bio.MSA.UCSC.felCat3_pairwiseHg18', 'Bio.MSA.UCSC.felCat3_pairwiseMm8', 'Bio.MSA.UCSC.fr2_multiz5way', 'Bio.MSA.UCSC.fr2_pairwiseDanRer4', 'Bio.MSA.UCSC.fr2_pairwiseDanRer5', 'Bio.MSA.UCSC.fr2_pairwiseGalGal3', 'Bio.MSA.UCSC.fr2_pairwiseGasAcu1', 'Bio.MSA.UCSC.fr2_pairwiseHg18', 'Bio.MSA.UCSC.fr2_pairwiseMm9', 'Bio.MSA.UCSC.fr2_pairwiseOryLat1', 'Bio.MSA.UCSC.fr2_pairwiseOryLat2', 'Bio.MSA.UCSC.fr2_pairwiseTetNig1', 'Bio.MSA.UCSC.galGal2ToGalgal3', 'Bio.MSA.UCSC.galGal2_multiz7way', 'Bio.MSA.UCSC.galGal3_multiz7way', 'Bio.MSA.UCSC.galGal3_pairwiseAnoCar1', 'Bio.MSA.UCSC.galGal3_pairwiseBraFlo1', 'Bio.MSA.UCSC.galGal3_pairwiseCavPor3', 'Bio.MSA.UCSC.galGal3_pairwiseDanRer4', 'Bio.MSA.UCSC.galGal3_pairwiseEquCab1', 'Bio.MSA.UCSC.galGal3_pairwiseFr2', 'Bio.MSA.UCSC.galGal3_pairwiseGasAcu1', 'Bio.MSA.UCSC.galGal3_pairwiseHg18', 'Bio.MSA.UCSC.galGal3_pairwiseMm8', 'Bio.MSA.UCSC.galGal3_pairwiseMm9', 'Bio.MSA.UCSC.galGal3_pairwiseMonDom4', 'Bio.MSA.UCSC.galGal3_pairwiseOrnAna1', 'Bio.MSA.UCSC.galGal3_pairwisePetMar1', 'Bio.MSA.UCSC.galGal3_pairwisePonAbe2', 'Bio.MSA.UCSC.galGal3_pairwiseRn4', 'Bio.MSA.UCSC.galGal3_pairwiseTaeGut1', 'Bio.MSA.UCSC.galGal3_pairwiseXenTro2', 'Bio.MSA.UCSC.gasAcu1_multiz8way', 'Bio.MSA.UCSC.gasAcu1_pairwiseAnoCar1', 'Bio.MSA.UCSC.gasAcu1_pairwiseDanRer4', 'Bio.MSA.UCSC.gasAcu1_pairwiseFr1', 'Bio.MSA.UCSC.gasAcu1_pairwiseFr2', 'Bio.MSA.UCSC.gasAcu1_pairwiseGalGal3', 'Bio.MSA.UCSC.gasAcu1_pairwiseHg18', 'Bio.MSA.UCSC.gasAcu1_pairwiseMm8', 'Bio.MSA.UCSC.gasAcu1_pairwiseMm9', 'Bio.MSA.UCSC.gasAcu1_pairwiseOryLat1', 'Bio.MSA.UCSC.gasAcu1_pairwiseOryLat2', 'Bio.MSA.UCSC.gasAcu1_pairwiseTetNig1', 'Bio.MSA.UCSC.hg17ToHg18', 'Bio.MSA.UCSC.hg17_multiz17way', 'Bio.MSA.UCSC.hg18ToHg17', 'Bio.MSA.UCSC.hg18_multiz17way', 'Bio.MSA.UCSC.hg18_multiz28way', 'Bio.MSA.UCSC.hg18_multiz44way', 'Bio.MSA.UCSC.hg18_pairwiseAnoCar1', 'Bio.MSA.UCSC.hg18_pairwiseBosTau2', 'Bio.MSA.UCSC.hg18_pairwiseBosTau3', 'Bio.MSA.UCSC.hg18_pairwiseBosTau4', 'Bio.MSA.UCSC.hg18_pairwiseBraFlo1', 'Bio.MSA.UCSC.hg18_pairwiseCalJac1', 'Bio.MSA.UCSC.hg18_pairwiseCanFam2', 'Bio.MSA.UCSC.hg18_pairwiseCavPor3', 'Bio.MSA.UCSC.hg18_pairwiseDanRer3', 'Bio.MSA.UCSC.hg18_pairwiseDanRer4', 'Bio.MSA.UCSC.hg18_pairwiseDanRer5', 'Bio.MSA.UCSC.hg18_pairwiseEquCab1', 'Bio.MSA.UCSC.hg18_pairwiseFelCat3', 'Bio.MSA.UCSC.hg18_pairwiseFr1', 'Bio.MSA.UCSC.hg18_pairwiseFr2', 'Bio.MSA.UCSC.hg18_pairwiseGalGal2', 'Bio.MSA.UCSC.hg18_pairwiseGalGal3', 'Bio.MSA.UCSC.hg18_pairwiseGasAcu1', 'Bio.MSA.UCSC.hg18_pairwiseMm7', 'Bio.MSA.UCSC.hg18_pairwiseMm8', 'Bio.MSA.UCSC.hg18_pairwiseMm9', 'Bio.MSA.UCSC.hg18_pairwiseMonDom4', 'Bio.MSA.UCSC.hg18_pairwiseOrnAna1', 'Bio.MSA.UCSC.hg18_pairwiseOryCun1', 'Bio.MSA.UCSC.hg18_pairwiseOryLat1', 'Bio.MSA.UCSC.hg18_pairwiseOryLat2', 'Bio.MSA.UCSC.hg18_pairwisePanTro1', 'Bio.MSA.UCSC.hg18_pairwisePanTro2', 'Bio.MSA.UCSC.hg18_pairwisePetMar1', 'Bio.MSA.UCSC.hg18_pairwisePonAbe2', 'Bio.MSA.UCSC.hg18_pairwiseRheMac2', 'Bio.MSA.UCSC.hg18_pairwiseRn4', 'Bio.MSA.UCSC.hg18_pairwiseSelf', 'Bio.MSA.UCSC.hg18_pairwiseSorAra1', 'Bio.MSA.UCSC.hg18_pairwiseStrPur2', 'Bio.MSA.UCSC.hg18_pairwiseTaeGut1', 'Bio.MSA.UCSC.hg18_pairwiseTetNig1', 'Bio.MSA.UCSC.hg18_pairwiseXenTro1', 'Bio.MSA.UCSC.hg18_pairwiseXenTro2', 'Bio.MSA.UCSC.hg19_pairwiseCalJac1', 'Bio.MSA.UCSC.hg19_pairwiseGorGor1', 'Bio.MSA.UCSC.hg19_pairwiseMicMur1', 'Bio.MSA.UCSC.hg19_pairwiseOtoGar1', 'Bio.MSA.UCSC.hg19_pairwisePanTro2', 'Bio.MSA.UCSC.hg19_pairwisePonAbe2', 'Bio.MSA.UCSC.hg19_pairwiseRheMac2', 'Bio.MSA.UCSC.hg19_pairwiseTarSyr1', 'Bio.MSA.UCSC.mm5ToMm6', 'Bio.MSA.UCSC.mm5ToMm7', 'Bio.MSA.UCSC.mm5ToMm8', 'Bio.MSA.UCSC.mm7ToMm5', 'Bio.MSA.UCSC.mm7ToMm6', 'Bio.MSA.UCSC.mm7ToMm8', 'Bio.MSA.UCSC.mm7_multiz17way', 'Bio.MSA.UCSC.mm8ToMm7', 'Bio.MSA.UCSC.mm8ToMm9', 'Bio.MSA.UCSC.mm8_multiz17way', 'Bio.MSA.UCSC.mm8_pairwiseAnoCar1', 'Bio.MSA.UCSC.mm8_pairwiseBosTau2', 'Bio.MSA.UCSC.mm8_pairwiseBosTau3', 'Bio.MSA.UCSC.mm8_pairwiseCanFam2', 'Bio.MSA.UCSC.mm8_pairwiseDanRer3', 'Bio.MSA.UCSC.mm8_pairwiseDanRer4', 'Bio.MSA.UCSC.mm8_pairwiseEquCab1', 'Bio.MSA.UCSC.mm8_pairwiseFelCat3', 'Bio.MSA.UCSC.mm8_pairwiseFr1', 'Bio.MSA.UCSC.mm8_pairwiseGalGal2', 'Bio.MSA.UCSC.mm8_pairwiseGalGal3', 'Bio.MSA.UCSC.mm8_pairwiseGasAcu1', 'Bio.MSA.UCSC.mm8_pairwiseHg17', 'Bio.MSA.UCSC.mm8_pairwiseHg18', 'Bio.MSA.UCSC.mm8_pairwiseMonDom4', 'Bio.MSA.UCSC.mm8_pairwiseOrnAna1', 'Bio.MSA.UCSC.mm8_pairwisePanTro1', 'Bio.MSA.UCSC.mm8_pairwisePanTro2', 'Bio.MSA.UCSC.mm8_pairwiseRheMac2', 'Bio.MSA.UCSC.mm8_pairwiseRn4', 'Bio.MSA.UCSC.mm8_pairwiseTetNig1', 'Bio.MSA.UCSC.mm8_pairwiseXenTro1', 'Bio.MSA.UCSC.mm8_pairwiseXenTro2', 'Bio.MSA.UCSC.mm9ToMm8', 'Bio.MSA.UCSC.mm9_multiz30way', 'Bio.MSA.UCSC.mm9_pairwiseAnoCar1', 'Bio.MSA.UCSC.mm9_pairwiseBosTau3', 'Bio.MSA.UCSC.mm9_pairwiseBosTau4', 'Bio.MSA.UCSC.mm9_pairwiseBraFlo1', 'Bio.MSA.UCSC.mm9_pairwiseCalJac1', 'Bio.MSA.UCSC.mm9_pairwiseCanFam2', 'Bio.MSA.UCSC.mm9_pairwiseCavPor3', 'Bio.MSA.UCSC.mm9_pairwiseDanRer5', 'Bio.MSA.UCSC.mm9_pairwiseEquCab1', 'Bio.MSA.UCSC.mm9_pairwiseFr2', 'Bio.MSA.UCSC.mm9_pairwiseGalGal3', 'Bio.MSA.UCSC.mm9_pairwiseGasAcu1', 'Bio.MSA.UCSC.mm9_pairwiseHg18', 'Bio.MSA.UCSC.mm9_pairwiseMonDom4', 'Bio.MSA.UCSC.mm9_pairwiseOrnAna1', 'Bio.MSA.UCSC.mm9_pairwiseOryLat1', 'Bio.MSA.UCSC.mm9_pairwiseOryLat2', 'Bio.MSA.UCSC.mm9_pairwisePanTro2', 'Bio.MSA.UCSC.mm9_pairwisePetMar1', 'Bio.MSA.UCSC.mm9_pairwisePonAbe2', 'Bio.MSA.UCSC.mm9_pairwiseRheMac2', 'Bio.MSA.UCSC.mm9_pairwiseRn4', 'Bio.MSA.UCSC.mm9_pairwiseTetNig1', 'Bio.MSA.UCSC.mm9_pairwiseXenTro2', 'Bio.MSA.UCSC.monDom4_multiz7way', 'Bio.MSA.UCSC.monDom4_pairwiseCalJac1', 'Bio.MSA.UCSC.monDom4_pairwiseCavPor3', 'Bio.MSA.UCSC.monDom4_pairwiseDanRer3', 'Bio.MSA.UCSC.monDom4_pairwiseDanRer4', 'Bio.MSA.UCSC.monDom4_pairwiseGalGal2', 'Bio.MSA.UCSC.monDom4_pairwiseGalGal3', 'Bio.MSA.UCSC.monDom4_pairwiseHg18', 'Bio.MSA.UCSC.monDom4_pairwiseMm8', 'Bio.MSA.UCSC.monDom4_pairwiseMm9', 'Bio.MSA.UCSC.monDom4_pairwiseOrnAna1', 'Bio.MSA.UCSC.monDom4_pairwisePanTro2', 'Bio.MSA.UCSC.monDom4_pairwisePonAbe2', 'Bio.MSA.UCSC.monDom4_pairwiseRn4', 'Bio.MSA.UCSC.monDom4_pairwiseXenTro2', 'Bio.MSA.UCSC.ornAna1_multiz6way', 'Bio.MSA.UCSC.ornAna1_pairwiseAnoCar1', 'Bio.MSA.UCSC.ornAna1_pairwiseBosTau4', 'Bio.MSA.UCSC.ornAna1_pairwiseCalJac1', 'Bio.MSA.UCSC.ornAna1_pairwiseGalGal3', 'Bio.MSA.UCSC.ornAna1_pairwiseHg18', 'Bio.MSA.UCSC.ornAna1_pairwiseMm8', 'Bio.MSA.UCSC.ornAna1_pairwiseMm9', 'Bio.MSA.UCSC.ornAna1_pairwiseMonDom4', 'Bio.MSA.UCSC.ornAna1_pairwisePonAbe2', 'Bio.MSA.UCSC.oryLat1_multiz5way', 'Bio.MSA.UCSC.oryLat2_multiz5way', 'Bio.MSA.UCSC.oryLat2_pairwiseDanRer5', 'Bio.MSA.UCSC.oryLat2_pairwiseFr2', 'Bio.MSA.UCSC.oryLat2_pairwiseGasAcu1', 'Bio.MSA.UCSC.oryLat2_pairwiseHg18', 'Bio.MSA.UCSC.oryLat2_pairwiseMm9', 'Bio.MSA.UCSC.oryLat2_pairwisePetMar1', 'Bio.MSA.UCSC.oryLat2_pairwiseTetNig1', 'Bio.MSA.UCSC.panTro1ToPantro2', 'Bio.MSA.UCSC.panTro2ToPantro1', 'Bio.MSA.UCSC.panTro2_pairwiseCalJac1', 'Bio.MSA.UCSC.panTro2_pairwiseCanFam2', 'Bio.MSA.UCSC.panTro2_pairwiseDanRer4', 'Bio.MSA.UCSC.panTro2_pairwiseEquCab1', 'Bio.MSA.UCSC.panTro2_pairwiseGalGal2', 'Bio.MSA.UCSC.panTro2_pairwiseHg17', 'Bio.MSA.UCSC.panTro2_pairwiseHg18', 'Bio.MSA.UCSC.panTro2_pairwiseHg19', 'Bio.MSA.UCSC.panTro2_pairwiseMm8', 'Bio.MSA.UCSC.panTro2_pairwiseMm9', 'Bio.MSA.UCSC.panTro2_pairwiseMonDom4', 'Bio.MSA.UCSC.panTro2_pairwisePonAbe2', 'Bio.MSA.UCSC.panTro2_pairwiseRheMac2', 'Bio.MSA.UCSC.panTro2_pairwiseRn4', 'Bio.MSA.UCSC.petMar1_multiz6way', 'Bio.MSA.UCSC.petMar1_pairwiseBraFlo1', 'Bio.MSA.UCSC.petMar1_pairwiseGalGal3', 'Bio.MSA.UCSC.petMar1_pairwiseHg18', 'Bio.MSA.UCSC.petMar1_pairwiseMm9', 'Bio.MSA.UCSC.petMar1_pairwiseOryLat1', 'Bio.MSA.UCSC.petMar1_pairwiseOryLat2', 'Bio.MSA.UCSC.ponAbe2_multiz8way', 'Bio.MSA.UCSC.ponAbe2_pairwiseCalJac1', 'Bio.MSA.UCSC.ponAbe2_pairwiseGalGal3', 'Bio.MSA.UCSC.ponAbe2_pairwiseHg18', 'Bio.MSA.UCSC.ponAbe2_pairwiseHg19', 'Bio.MSA.UCSC.ponAbe2_pairwiseMm9', 'Bio.MSA.UCSC.ponAbe2_pairwiseMonDom4', 'Bio.MSA.UCSC.ponAbe2_pairwiseOrnAna1', 'Bio.MSA.UCSC.ponAbe2_pairwisePanTro2', 'Bio.MSA.UCSC.ponAbe2_pairwiseRheMac2', 'Bio.MSA.UCSC.rheMac2_pairwiseCalJac1', 'Bio.MSA.UCSC.rheMac2_pairwiseHg18', 'Bio.MSA.UCSC.rheMac2_pairwiseHg19', 'Bio.MSA.UCSC.rheMac2_pairwiseMm8', 'Bio.MSA.UCSC.rheMac2_pairwiseMm9', 'Bio.MSA.UCSC.rheMac2_pairwisePanTro2', 'Bio.MSA.UCSC.rheMac2_pairwisePonAbe2', 'Bio.MSA.UCSC.rheMac2_pairwiseRn4', 'Bio.MSA.UCSC.rn3ToRn4', 'Bio.MSA.UCSC.rn4ToRn3', 'Bio.MSA.UCSC.rn4_multiz9way', 'Bio.MSA.UCSC.rn4_pairwiseBosTau2', 'Bio.MSA.UCSC.rn4_pairwiseBosTau3', 'Bio.MSA.UCSC.rn4_pairwiseCanFam2', 'Bio.MSA.UCSC.rn4_pairwiseCavPor3', 'Bio.MSA.UCSC.rn4_pairwiseDanRer3', 'Bio.MSA.UCSC.rn4_pairwiseDanRer4', 'Bio.MSA.UCSC.rn4_pairwiseEquCab1', 'Bio.MSA.UCSC.rn4_pairwiseGalGal2', 'Bio.MSA.UCSC.rn4_pairwiseGalGal3', 'Bio.MSA.UCSC.rn4_pairwiseHg18', 'Bio.MSA.UCSC.rn4_pairwiseMm8', 'Bio.MSA.UCSC.rn4_pairwiseMm9', 'Bio.MSA.UCSC.rn4_pairwiseMonDom4', 'Bio.MSA.UCSC.rn4_pairwisePanTro2', 'Bio.MSA.UCSC.rn4_pairwiseRheMac2', 'Bio.MSA.UCSC.rn4_pairwiseXenTro1', 'Bio.MSA.UCSC.rn4_pairwiseXenTro2', 'Bio.MSA.UCSC.tetNig1_pairwiseDanRer3', 'Bio.MSA.UCSC.tetNig1_pairwiseDanRer4', 'Bio.MSA.UCSC.tetNig1_pairwiseDanRer5', 'Bio.MSA.UCSC.tetNig1_pairwiseFr2', 'Bio.MSA.UCSC.tetNig1_pairwiseGasAcu1', 'Bio.MSA.UCSC.tetNig1_pairwiseHg18', 'Bio.MSA.UCSC.tetNig1_pairwiseMm6', 'Bio.MSA.UCSC.tetNig1_pairwiseMm7', 'Bio.MSA.UCSC.tetNig1_pairwiseMm8', 'Bio.MSA.UCSC.tetNig1_pairwiseMm9', 'Bio.MSA.UCSC.tetNig1_pairwiseOryLat1', 'Bio.MSA.UCSC.tetNig1_pairwiseOryLat2', 'Bio.MSA.UCSC.xenTro1ToXentro2', 'Bio.MSA.UCSC.xenTro1_multiz5way', 'Bio.MSA.UCSC.xenTro2_multiz7way', 'Bio.MSA.UCSC.xenTro2_pairwiseAnoCar1', 'Bio.MSA.UCSC.xenTro2_pairwiseDanRer4', 'Bio.MSA.UCSC.xenTro2_pairwiseGalGal2', 'Bio.MSA.UCSC.xenTro2_pairwiseGalGal3', 'Bio.MSA.UCSC.xenTro2_pairwiseHg18', 'Bio.MSA.UCSC.xenTro2_pairwiseMm8', 'Bio.MSA.UCSC.xenTro2_pairwiseMm9', 'Bio.MSA.UCSC.xenTro2_pairwiseMonDom4', 'Bio.MSA.UCSC.xenTro2_pairwiseRn4', 'Bio.Seq.Genome.ANOCA.anoCar1', 'Bio.Seq.Genome.ANOGA.anoGam1', 'Bio.Seq.Genome.APIME.apiMel2', 'Bio.Seq.Genome.APIME.apiMel3', 'Bio.Seq.Genome.BOVIN.bosTau2', 'Bio.Seq.Genome.BOVIN.bosTau3', 'Bio.Seq.Genome.BOVIN.bosTau4', 'Bio.Seq.Genome.BRAFL.braFlo1', 'Bio.Seq.Genome.CAEBR.cb3', 'Bio.Seq.Genome.CAEEL.ce2', 'Bio.Seq.Genome.CAEEL.ce4', 'Bio.Seq.Genome.CAEEL.ce6', 'Bio.Seq.Genome.CAEJA.caeJap1', 'Bio.Seq.Genome.CAEPB.caePb1', 'Bio.Seq.Genome.CAEPB.caePb2', 'Bio.Seq.Genome.CAERE.caeRem2', 'Bio.Seq.Genome.CAERE.caeRem3', 'Bio.Seq.Genome.CALJA.calJac1', 'Bio.Seq.Genome.CANFA.canFam2', 'Bio.Seq.Genome.CAVPO.cavPor2', 'Bio.Seq.Genome.CAVPO.cavPor3', 'Bio.Seq.Genome.CHICK.galGal2', 'Bio.Seq.Genome.CHICK.galGal3', 'Bio.Seq.Genome.CHOHO.choHof1', 'Bio.Seq.Genome.CIOIN.ci2', 'Bio.Seq.Genome.DANRE.danRer1', 'Bio.Seq.Genome.DANRE.danRer2', 'Bio.Seq.Genome.DANRE.danRer3', 'Bio.Seq.Genome.DANRE.danRer4', 'Bio.Seq.Genome.DANRE.danRer5', 'Bio.Seq.Genome.DASNO.dasNov1', 'Bio.Seq.Genome.DASNO.dasNov2', 'Bio.Seq.Genome.DIPOR.dipOrd1', 'Bio.Seq.Genome.DROAN.droAna1', 'Bio.Seq.Genome.DROAN.droAna2', 'Bio.Seq.Genome.DROAN.droAna3', 'Bio.Seq.Genome.DROER.droEre1', 'Bio.Seq.Genome.DROER.droEre2', 'Bio.Seq.Genome.DROGR.droGri1', 'Bio.Seq.Genome.DROGR.droGri2', 'Bio.Seq.Genome.DROME.dm2', 'Bio.Seq.Genome.DROME.dm3', 'Bio.Seq.Genome.DROMO.droMoj1', 'Bio.Seq.Genome.DROMO.droMoj2', 'Bio.Seq.Genome.DROMO.droMoj3', 'Bio.Seq.Genome.DROPE.droPer1', 'Bio.Seq.Genome.DROPS.dp3', 'Bio.Seq.Genome.DROPS.dp4', 'Bio.Seq.Genome.DROSE.droSec1', 'Bio.Seq.Genome.DROSI.droSim1', 'Bio.Seq.Genome.DROVI.droVir1', 'Bio.Seq.Genome.DROVI.droVir2', 'Bio.Seq.Genome.DROVI.droVir3', 'Bio.Seq.Genome.DROWI.droWil1', 'Bio.Seq.Genome.DROYA.droYak1', 'Bio.Seq.Genome.DROYA.droYak2', 'Bio.Seq.Genome.ECHTE.echTel1', 'Bio.Seq.Genome.ERIEU.eriEur1', 'Bio.Seq.Genome.FELCA.felCat3', 'Bio.Seq.Genome.FUGRU.fr1', 'Bio.Seq.Genome.FUGRU.fr2', 'Bio.Seq.Genome.GASAC.gasAcu1', 'Bio.Seq.Genome.GORGO.gorGor1', 'Bio.Seq.Genome.HORSE.equCab1', 'Bio.Seq.Genome.HORSE.equCab2', 'Bio.Seq.Genome.HUMAN.hg17', 'Bio.Seq.Genome.HUMAN.hg18', 'Bio.Seq.Genome.HUMAN.hg19', 'Bio.Seq.Genome.LAMPA.vicPac1', 'Bio.Seq.Genome.LOXAF.loxAfr1', 'Bio.Seq.Genome.LOXAF.loxAfr2', 'Bio.Seq.Genome.MACMU.rheMac1', 'Bio.Seq.Genome.MACMU.rheMac2', 'Bio.Seq.Genome.MICMU.micMur1', 'Bio.Seq.Genome.MONDO.monDom1', 'Bio.Seq.Genome.MONDO.monDom2', 'Bio.Seq.Genome.MONDO.monDom4', 'Bio.Seq.Genome.MOUSE.mm5', 'Bio.Seq.Genome.MOUSE.mm6', 'Bio.Seq.Genome.MOUSE.mm7', 'Bio.Seq.Genome.MOUSE.mm8', 'Bio.Seq.Genome.MOUSE.mm9', 'Bio.Seq.Genome.MYOLU.myoLuc1', 'Bio.Seq.Genome.OCHPR.ochPri2', 'Bio.Seq.Genome.ORNAN.ornAna1', 'Bio.Seq.Genome.ORYLA.oryLat1', 'Bio.Seq.Genome.ORYLA.oryLat2', 'Bio.Seq.Genome.OTOGA.otoGar1', 'Bio.Seq.Genome.PANTR.panTro1', 'Bio.Seq.Genome.PANTR.panTro2', 'Bio.Seq.Genome.PETMA.petMar1', 'Bio.Seq.Genome.PONAB.ponAbe2', 'Bio.Seq.Genome.PONPA.ponAbe2', 'Bio.Seq.Genome.PRIPA.priPac1', 'Bio.Seq.Genome.PROCA.proCap1', 'Bio.Seq.Genome.PTEVA.pteVam1', 'Bio.Seq.Genome.RABIT.oryCun1', 'Bio.Seq.Genome.RAT.rn3', 'Bio.Seq.Genome.RAT.rn4', 'Bio.Seq.Genome.SORAR.sorAra1', 'Bio.Seq.Genome.SPETR.speTri1', 'Bio.Seq.Genome.STRPU.strPur1', 'Bio.Seq.Genome.STRPU.strPur2', 'Bio.Seq.Genome.TAEGU.taeGut1', 'Bio.Seq.Genome.TARSY.tarSyr1', 'Bio.Seq.Genome.TETNG.tetNig1', 'Bio.Seq.Genome.TRICA.triCas2', 'Bio.Seq.Genome.TUPGB.tupBel1', 'Bio.Seq.Genome.TURTR.turTru1', 'Bio.Seq.Genome.XENTR.xenTro1', 'Bio.Seq.Genome.XENTR.xenTro2', 'Bio.Seq.Genome.YEAST.sacCer1', 'Test.Temp', '__doc__.Test.Temp']
     >>> len(worldbase.dir())
     465

  That is 465 whole vertebrate / animal genomes and whole genome alignments
  loaded simultaneously on one vanilla server, constantly serving requests from
  people around the world.

* when you get a specific sequence object (e.g. ``chr1``), that still
  doesn't read all its data into memory.  The object is just a representation
  of that piece of the genome, decoupled from the problem of where to
  actually store all that data.  In the case of :class:`seqdb.SequenceFileDB`,
  the data are stored on disk, and accessed via fast on-disk indexes
  and the standard ``fseek()`` interface.

* just because data may not be stored in memory doesn't mean performance
  must go down the drain.  Pygr uses ``weakref`` based caching techniques
  to keep a cache of data that you are likely to access, until you don't
  want them anymore.  (for details see :class:`seqdb.SequenceDB`).

Accessing a Sequence Database over SQL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's say you wanted to access the transcript sequences from UCSC's
"known genes" annotation, from UCSC's MySQL server.  Pygr provides
standard sequence types that work over SQL.  That is, they

* implement fast sequence slice retrieval using SQL queries to get
  a given piece of sequence that you want.

* provide transparent attribute access to columns in the SQL table
  (using SQL queries).

* by default, they assume that two standard column names will be present
  in the database table: ``seq``, containing the actual sequence string;
  ``length``, containing the sequence length as an integer.

* :mod:`sqlgraph` defines three sequence classes: ``DNASQLSequence``,
  ``RNASQLSequence``, and ``ProteinSQLSequence``.  The only difference
  between them is their ``_seqtype`` attribute, which informs Pygr what
  kind of sequences it contains.

In the case of the UCSC ``knownGenesMrna`` table, it does in fact 
store the sequence as its ``seq`` column, but it lacks a ``length``
column.  So we'll just write a custom ``__len__()`` method that will
execute the right SQL query::

   >>> from pygr import sqlgraph
   >>> class UCSCmRNA(sqlgraph.RNASQLSequence):
   ...    'interpret row objects as sequence object a la knownGeneMrna'
   ...    def __len__(self): # get length by running SQL query
   ...        return self._select('length(seq)') # SQL SELECT expression
   ...

Now all we have to do is connect to the UCSC MySQL server, and access
our desired table.  First we create an object representing the server,
with the basic authentication information::

   >>> serverInfo = sqlgraph.DBServerInfo(host='genome-mysql.cse.ucsc.edu',
                                          user='genome')

Finally, we connect to the ``hg18.knownGeneMrna`` table, which stores
the transcript sequences for all of UCSC's known gene annotations on 
human genome draft 18::

   >>> mrna = sqlgraph.SQLTable('hg18.knownGeneMrna', serverInfo=serverInfo, 
                                itemClass=UCSCmRNA,
                                itemSliceClass=seqdb.SeqDBSlice)

Notice the only thing "special" here is that we have told 
:class:`sqlgraph.SQLTable` to use custom classes for the row objects
that it creates:

* Pygr database classes accept the ``itemClass`` argument as the class
  to use for its "row objects".

* Similarly, the ``itemSliceClass`` tells it the class that will be used
  for creating *slices* of the itemClass.  In this case, it's just Pygr's
  standard slice class for sequences that are part of a sequence database.
  (The main effect of this is to mirror the ``id`` and ``db`` attributes
  from the sequence object).

Now we can use this to access some UCSC mRNA sequences::

   >>> len(mrna)
   37428

This database contains a lot of mRNAs!  Rather than display a list
of them, let's just start playing with one sequence, in the usual ways::

   >>> s = ucsc_mrna.mrna['uc009vjh.1']
   >>> len(s)
   888
   >>> s
   uc009vjh.1[0:888]
   >>> print s
   gttatgaagaaggtccggtgttttcttacccacctccttccctcctttttataataccagtgaaacttggtttggagcatttctttcacataaaggtaactgcagaggctatttcctggaatgaatcaacgagtgaaacgaataactctatggtgactgaattcatttttctgggtctctctgattctcaggaactccagaccttcctatttatgttgttttttgtattctatggaggaatcgtgtttggaaaccttcttattgtcataacagtggtatctgactcccaccttcactctcccatgtacttcctgctagccaacctctcactcattgatctgtctctgtcttcagtcacagcccccaagatgattactgactttttcagccagcgcaaagtcatctctttcaagggctgccttgttcagatatttctccttcacttctttggtgggagtgagatggtgatcctcatagccatgggctttgacagatatatagcaatatgcaagcccctacactacactacaattatgtgtggcaacgcatgtgtcggcattatggctgtcacatggggaattggctttctccattcggtgagccagttggcgtttgccgtgcacttactcttctgtggtcccaatgaggtcgatagtttttattgtgaccttcctagggtaatcaaacttgcctgtacagatacctacaggctagatattatggtcattgctaacagtggtgtgctcactgtgtgttcttttgttcttctaatcatctcatacactatcatcctaatgaccatccagcatcgccctttagataagtcgtccaaagctctgtccactttgactgctcacattacagtagttcttttgttctttggaccat
   >>> t = s[100:210]
   >>> print t
   tgcagaggctatttcctggaatgaatcaacgagtgaaacgaataactctatggtgactgaattcatttttctgggtctctctgattctcaggaactccagaccttcctat
   >>> print -t
   ataggaaggtctggagttcctgagaatcagagagacccagaaaaatgaattcagtcaccatagagttattcgtttcactcgttgattcattccaggaaatagcctctgca

As you can see, we can use these sequence objects exactly the same way
we used any other Pygr sequence objects.

Once again, it's a good idea to ``close()`` any open resource
when you're done with it.  In this case, you should close the 
:class:`sqlgraph.DBServerInfo` object when you are done using its
database connection::

   >>> serverInfo.close()


Comparative Genomics Query of Multigenome Alignments
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Many groups (e.g. David Haussler's group at UC Santa Cruz) have constructed alignments of multiple genomes.  These alignments are extremely useful and interesting, but so large that it is cumbersome to work with the dataset using conventional methods.  For example, for the 17-genome alignment you have to work simultaneously with the individual genome datasets for human, chimp, mouse, rat, dog, chicken, fugu and zebrafish etc., as well as the huge alignment itself.  Pygr makes this quite easy.  Here we illustrate an example of mapping a set of human exons, which has two splice sites
(``ss1`` and ``ss2``) bracketing a single exon (``exon``).
We use the alignment database to map each of these splice sites onto all the aligned
genomes, and to print the percent-identity and percent-aligned for each genome,
as well as the two nucleotides consituting the splice site itself.
It also prints the conservation of the two exonic region (between ``ss1``
and ``ss2``::

   from pygr import worldbase # FINDS DATA WHEREVER IT'S REGISTERED
   msa = worldbase.Bio.MSA.UCSC.hg17_multiz17way() # SANTA CRUZ 17-GENOME ALIGNMENT
   exons = worldbase.Leelab.ASAP2.hg17.exons() # ASAP2 HUMAN EXONS
   idDict = ~(msa.seqDict) # INVERSE: MAPS SEQ --> STRING IDENTIFIER
   def printConservation(id,label,site):
       for src,dest,edge in msa[site].edges(mergeMost=True):
           print '%d\t%s\t%s\t%s\t%s\t%s\t%2.1f\t%2.1f' \
                 %(id,label,repr(src),src,idDict[dest],dest,
                   100*edge.pIdentity(),100*edge.pAligned())
   for id,exon in exons.iteritems():
       ival = exon.sequence # GET THE SEQUENCE INTERVAL FOR THIS EXON
       ss1 = ival.before()[-2:] # GET THE 2 NT SPLICE SITES
       ss2 = ival.after()[:2]
       cacheHint = msa[ss1+ss2] #CACHE THE COVERING INTERVALS FROM ss1 TO ss2
       printConservation(id,'ss1',ss1)
       printConservation(id,'ss2',ss2)
       printConservation(id,'exon',ival)


A few notes:


  
* Querying a large multi-genome alignment requires special interval indexing
  algorithms (R-Tree or nested-list used in Pygr).  Pygr provides a high-performance
  C implementation of a disk-based nested-list database that provides both
  very fast interval overlap query times (sub-millisecond per query, compared with
  10-30 seconds per query using MySQL multi-column indexing, and much faster
  than Postgres R-Tree indexing), and a very small memory footprint
  (e.g. 2.5 MB RSS in-memory, 8 MB VSZ virtual size,
  for working with the UCSC 17 vertebrate
  genome alignment and sequence databases).  For more information on the
  nested-list algorithm and performance comparisons, see the published paper,
  Alekseyenko and Lee, Bioinformatics 2007.
  
* The alignment database query is in the first line of ``printConservation()``.
  ``msa`` is the database; ``site`` is the interval query; and the
  :meth:`edges()` methods iterates over the results, returning a tuple for
  each, consisting of a *source sequence* interval (i.e. an interval of
  ``site``), a *destination sequence* interval (i.e. an interval in
  an aligned genome), and an *edge object* describing that alignment.
  We are taking advantage of Pygr's group-by operator ``mergeMost``,
  which will cause multiple intervals in a given sequence to be merged
  into a single interval that constitutes their "union".  Thus,
  for each aligned genome, the ``edges`` iterator will return a single
  aligned interval.  The alignment edge object provides some useful
  conveniences, such as calculating the percent-identity between ``src``
  and ``dest`` automatically for you.  :meth:`pIdentity()` computes
  the fraction of identical residues; :meth:`pAligned` computes the
  fraction of *aligned* residues (allowing you to see if there are
  big gaps or insertions in the alignment of this interval).  If we
  had wanted to inspect the detailed alignment letter by letter, we
  would just iterate over the :attr:`letters` attribute instead of
  the :meth:`edges` method. (See the :class:`NLMSASlice` documentation for
  further information).
  
* Pygr provides convenient query options for specifying precisely how regions
  of alignment should be "grouped" together (e.g. treat alignment intervals
  separated by indels up to a certain size as being a *single* alignment
  region) or filtered (e.g. require a certain level of conservation over some
  minimum size of alignment region).  Here's an example::
  
     results = msa[site].edges(maxgap=1,maxinsert=1,
                             minAlignSize=14,pIdentityMin=0.9)
  
  This example groups together any number of alignment intervals separated by indels
  of at most one in length, and then filters these alignment regions to
  just those (sub)regions that have at least 90\% sequence identity over
  a region of at least 14 residues in length.
  
  We can use this same idea to search for regions of "deep conservation".  Here
  we search the UCSC alignment of 17 vertebrate genomes for regions of 90\% identity
  or better that are at least 40 nt long, and then screen for a zone in which at
  least nine different genomes all share this level of alignment with the human
  query::
  
     >>> ival = nlmsa.seqDict['hg17.chr1'][7000:8000] # 1 kb REGION OF HUMAN CHROMOSOME 1
     >>> for x,y,e in nlmsa[ival].edges(minAligned=9,minAlignSize=40,pIdentityMin=0.9):
     ...   print "%s\t%s\n%s\t%s\n" % (x,repr(x),y,(~(nlmsa.seqDict))[y])
     ...
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAACAGCAGTAAAGAGCTGAC      danRer3.chr18
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAAGAGCAGCAAGGAGCTGAC      dasNov1.scaffold_107966
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAAAAGGAGCAAGGAGCTGAC      xenTro1.scaffold_1073
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAAGAGCAGCAGGGAGCTGAG      galGal2.chr1
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAAGAGCAGCAAGGAGCTGAC      panTro1.chr1
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAAGAGCAGCAGGGAGCTGAC      bosTau2.chr5
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAATAGCAGCAACGAGCTGAC      canFam2.chr27
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAAGAGCAGCAAGGAGCTGAG      monDom2.scaffold_31
  
     GTGTTGAAGAGCAGCAAGGAGCTGAC      chr1[7480:7506]
     GTGTTGAAGAGCAGCAAGGAGCTGAC      loxAfr1.scaffold_5603
  
  Each region of alignment was contained in a block of >=90\% identity and
  over 40 nt long.  The region has been masked by the minAligned option to just
  the portion in which at least nine different genomes are aligned to the human query.
  
* ``src`` and ``dest`` print the first two nucleotides
  of the site in human and in the aligned genome.
  
* it's worth noting that the actual sequence string comparisons are being
  done using a completely different database mechanism 
  (Pygr's simple ``pureseq`` text format),
  not the ``cnestedlist`` database.  Basically, each genome is being queried
  as a separate sequence database, represented in Pygr by the
  :class:`SequenceFileDB` class.  Pygr makes this complex set of multi-database
  operations more or less transparent to the user.
  For further information, see the :class:`SequenceFileDB` documentation.
  
* ASAP2.hg17.exons is an annotation database; each object it
  contains (``exon``) is an annotation object.  To get the actual
  sequence interval corresponding to this annotation, we simply request
  the annotation object's :attr:`sequence` attribute.
  
* Note: ``exon.sequence`` must itself be a slice of a sequence in our alignment,
  or the alignment query ``msa[site]`` will raise an :exc:`KeyError` informing
  the user that the sequence ``site`` is not in the alignment.
  
* One interesting operation here is the use of interval
  addition to obtain the "union" of two intervals, e.g. ``ss1+ss2``.
  This obtains a single interval that covers both of the input intervals.
  
* When the print statement requests str() representations of these sequence objects, Pygr uses fseek() to extract just the right piece of the corresponding chromosomes from the 17 BLAST databases representing all the different genomes.
  
* Given the high speed of the NLMSA alignment query, it turns out that the
  operation of reading sequence strings from the sequence databases (in this
  case, for printing them in ``printConservation()`` and calculating the percent identity
  in ``pIdentity()``) is the rate-limiting step for this analysis.  I.e. this analysis
  spends far more time waiting for disk I/O to read a particular piece of sequence
  than it does running the NLMSA alignment queries.  To solve this problem, Pygr
  provides a mechanism for intelligent caching of sequence data.  Whenever you
  perform a query (e.g. ``msa[site]``), it infers that you are likely to look
  at the sequence intervals that are contained within this slice of the alignment
  (i.e. within the region aligned to ``site``).  It sets "caching hints" on the
  associated sequence databases, recording for each aligned sequence
  the covering interval coordinates (i.e. the smallest interval that fully contains
  all portions of the sequence that are aligned to ``site``).  These caching hints
  do not themselves trigger reading of sequence string data from the databases.  Only
  when user code actually requests sequence strings that fall within these covering
  intervals, the sequence database object will load not the requested interval, but
  the entire covering interval, which is then cached.  Thereafter, all sequence
  string requests that fall within the covering interval are simply immediately sliced
  from the cached sequence string, completely avoiding any need to read from disk.
  This greatly accelerates sequence analysis with very large multigenome alignments
  and sequence databases.
  
  In this case, to enforce the most efficient caching possible, we simply performed
  a query that contains all three sites of interest (ss1, ss2, and exon).  By performing
  this query first, and holding onto the query result, we ensure that Pygr will
  use the same cache for all three subsequent queries contained in it.  As soon
  as we release the reference to this query result (i.e. in the example above,
  whenever the variable ``cacheHint`` is deleted or over-written with a new value,
  freeing Python to garbage-collect the original query result), the associated
  cache hint information will also be cleared.
  


(Actually, because of Pygr's caching / optimizations, considerably more is going on than indicated in this simplified sketch.  But you get the idea: Pygr makes it relatively effortless to work with a variety of disparate (and large) resources in an integrated way.)

Here is some example output::

   NEED TO UPDATE THESE RESULTS
   1       Mm.99996        ss1     hg17    50.0    100.0   AG      GG
   1       Mm.99996        ss1     canFam1 50.0    100.0   AG      GG
   1       Mm.99996        ss1     panTro1 50.0    100.0   AG      GG
   1       Mm.99996        ss1     rn3     100.0   100.0   AG      AG
   1       Mm.99996        ss2     hg17    100.0   100.0   AG      AG
   1       Mm.99996        ss2     canFam1 100.0   100.0   AG      AG
   1       Mm.99996        ss2     panTro1 100.0   100.0   AG      AG
   1       Mm.99996        ss2     rn3     100.0   100.0   AG      AG
   1       Mm.99996        ss3     hg17    100.0   100.0   GT      GT
   1       Mm.99996        ss3     canFam1 100.0   100.0   GT      GT
   1       Mm.99996        ss3     panTro1 100.0   100.0   GT      GT
   1       Mm.99996        ss3     rn3     100.0   100.0   GT      GT
   1       Mm.99996        e1      hg17    78.9    100.0   AG      GG
   1       Mm.99996        e1      canFam1 84.2    100.0   AG      GG
   1       Mm.99996        e1      panTro1 77.6    100.0   AG      GG
   1       Mm.99996        e1      rn3     97.4    98.7    AG      AG
   1       Mm.99996        e2      hg17    91.6    99.1    CC      CC
   1       Mm.99996        e2      canFam1 88.8    99.1    CC      CC
   1       Mm.99996        e2      panTro1 91.6    99.1    CC      CC
   1       Mm.99996        e2      rn3     97.2    100.0   CC      CC


Working with Sequences from Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pygr provides a variety of "back-end" implementations of sequence objects, ranging from sequences stored in a relational database table, or a BLAST database, to sequences created by the user in Python (as above).  All of these provide the same consistent interface, and in general try to be efficient.  For example, Pygr sequence objects are just "placeholders" that record what sequence interval you're working with, but if the back-end is an external database, the sequence object itself does not store the sequence, and creating new sequence objects (e.g. taking slices of the object as above) will not require anything to be done on the actual sequence itself (such as copying a portion of it).  Pygr only obtains sequence information when you actually ask for it (e.g. by taking the string value str(s) of a sequence object), and normally only obtains just the portion that you ask for (i.e. str(s[1000000:1000100]) only obtains 100nt of sequence, even if s is a 100 megabase sequence.  By contrast str(s)[1000000:1000100] would force it to obtain the whole sequence from the database, then slice out just the 100 nt you selected).

Here's an example of working with sequences from a sequence database and
running a BLAST search::

   NEED TO UPDATE THESE RESULTS
   >>> from pygr.seqdb import *
   >>> db = SequenceFileDB('sp') # open sequence database from FASTA file 'sp'
   >>> s = db['CYGB_HUMAN'][90:150] # get a sequence by ID, and take a slice
   >>> str(s)
   'TVVENLHDPDKVSSVLALVGKAHALKHKVEPVYFKILSGVILEVVAEEFASDFPPETQRA'
   >>> from blast import BlastMapping
   >>> blastmap = BlastMapping(db) # create homology mapping to our seq db
   >>> al = blastmap[s] # get alignment to all BLAST hits in db
   >>> for src,dest,edge in al.edges(): # print out the alignment edges
   ...     print src,repr(src),'\n',dest,repr(dest),edge.pIdentity(),'\n'
   ...
   TVVENLHDPDKVSSVLALVGKAHALKHKVEPVYFKILSGVILEVVAEEFASDFPP CYGB_HUMAN[90:145]
   TLVENLRDADKLNTIFNQMGKSHALRHKVDPVYFKILAGVILEVLVEAFPQCFSP CYGB_BRARE[87:142] 72

   TVVENLHDPDKVSSVLALVGKAHALKHKVEPVYFKILSGVILEVVAEEFASDFPPETQRA CYGB_HUMAN[90:150]
   TVVENLHDPDKVSSVLALVGKAHALKHKVEPVYFKILSGVILEVVAEEFASDFPPETQRA CYGB_HUMAN[90:150] 120

   TVVENLHDPDKVSSVLALVGKAHALKHKVEPVYFKILSGVILEVVAEEFASDFPPETQRA CYGB_HUMAN[90:150]
   TVVENLHDPDKVSSVLALVGKAHALKHKVEPMYFKILSGVILEVIAEEFANDFPVETQKA CYGB_MOUSE[90:150] 112
   ...


This example introduces the use of a Pygr alignment object to store the mapping of s onto homologous sequences in db, obtained from BLAST.  Here's what Pygr actually does:


  
* We can construct a :class:`SequenceFileDB` object
  from any FASTA formatted sequence file.
  It acts as a Python dictionary mapping sequence IDs to the associated
  sequence objects (i.e. if 'CYGB_HUMAN' is a sequence ID in sp,
  then db['CYGB_HUMAN'] is the sequence object for that sequence.
  
* When you work with such sequence objects, slicing etc. happens in the usual
  way, creating new sequence objects.
  
* Only when you ask for actual sequence (by taking ``str(s)``) does it obtain
  a sequence string from the database.  This is done using ``fseek()`` system
  call to obtain just the selected slice.  So you can efficiently obtain a
  substring of a sequence, even if that sequence is an entire chromosome.
  
* Any sequence database object can be used as a "target" for a homology
  search such as BLAST.  In Pygr, BLAST searches are just another kind
  of mapping, that maps a sequence object to similar sequences in the
  target database.  You instantiate a :class:`BlastMapping` object to do this by
  simply passing the target database as an argument to the
  :class:`BlastMapping` constructor.
  
* When you first create the :class:`BlastMapping` object, it looks for existing BLAST database files associated with the FASTA file 'sp'.  If present, it uses them.  If not, it will create them automatically if the user actually tries to run a BLAST query.  Pygr builds BLAST database files using the NCBI program formatdb (Pygr figures out whether the sequences are nucleotide or protein, and gives formatdb the appropriate command line options).
  
* When you search the :class:`BlastMapping` object with a given query (sequence) object, it obtains the actual string of the object, and uses it to run a BLAST search.  It determines the type (nucleotide or protein) of the sequence object, and uses the appropriate search method (in this case blastp).  You can pass optional arguments for controlling BLAST.  It then reads the results into a Pygr multiple sequence alignment object, which stores the alignments as sets of matched intervals.  Specifically, it is a graph, whose nodes are sequence intervals (i.e. sequence objects that typically represent only part of a sequence), and whose edges represent an alignment between a pair of intervals.  To illustrate this, we ran a for-loop over all the "edge relations" in this graph, and printed them out.  This is a tuple of 3 values: ``src`` and ``dest`` are the two aligned sequence intervals, and ``edge`` provides a convenient interface to information about their relationship (e.g. \%identity, etc.).
  
* If we wanted to pass parameters for controlling the BLAST search, we
  can use ``blastmap`` as a function that accepts additional parameters::
  
     >>> al = blastmap(s, expmax=1e-10, maxseq=5) # expectation score cutoff, etc.
  
  
* Note: print converts its arguments to strings (i.e. calls ``str()`` on them), so we used ``repr(src)`` to get a "string representation" of each sequence interval.  When print calls str() on individual sequence interval objects returned by the BLAST search, the sequence database will efficiently obtain the specific sequence slice representing that interval (typically, using fseek() and caching).


