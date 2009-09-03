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

Plugging in Your Own Sequence Parser
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

What if you want to open a sequence database stored in a non-FASTA
format?  This is very simple in Pygr.  All you have to do is pass a
``reader()`` function to :class:`seqdb.SequenceFileDB`, and it will
use your reader instead of its own FASTA parser.

* Your ``reader()``
  must act like a Python generator function (i.e. it can be used as
  an iterator), yielding one object per sequence in the file.

* each object should have three attributes: ``id``, giving the 
  sequence's ID; ``length``, giving the sequence's length, and
  ``sequence``, giving the actual string sequence.

* the first time you open the :class:`seqdb.SequenceFileDB`, it
  will use your ``reader()`` to build an on-disk index of all
  the sequences, reading the sequences one at a time to do so.

* once this is complete, it will be used exactly the same as a
  FASTA-based :class:`seqdb.SequenceFileDB`.  That is, the
  sequences will *not* be kept in memory, but accessed from the
  on-disk index, using its fast ``fseek()`` method.

* once the index files have been created, you can later open the
  sequence database without even passing a ``reader()`` method.
  The ``reader()`` method is only needed for the initial indexing
  operation.

Let's try this out with a simple CSV based ``reader()``.  First,
let's write our parsing function, which must take two arguments:
``ifile``, a file object to read the data from; ``filename``, the
path to the file, in case that is helpful (for example, the function
might use its file suffix to guess the file's format).  Here is 
a simple example::

   import csv
   def read_csv(ifile, filename):
      'assume 1st col is id, 2nd is sequence'
      class seqholder(object):
         def __init__(self, id, sequence):
            (self.id, self.sequence, self.length) = (id, sequence, 
                                                     len(sequence))
      for row in csv.reader(ifile):
         yield seqholder(row[0],row[1])
         
Now all we have to do is pass this reader function to create a new
:class:`seqdb.SequenceFileDB`::

   >>> myseqs = seqdb.SequenceFileDB('someseqs.csv', reader=read_csv)
   DEBUG seqdb._create_seqLenDict: Building sequence length index...

This message signals that it created our sequence index files.
Now we can use the sequence database in all the usual ways::

   >>> len(myseqs)
   2
   >>> myseqs.keys()
   ['bar', 'foo']
   >>> foo = myseqs['foo']
   >>> len(foo)
   17
   >>> print foo
   attgtatacgtgcgtag

Finally, let's close our database::

   >>> myseqs.close()

Combining Sequence Databases Using PrefixUnionDict
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

What if you wanted to make a "super-database" of sequences, by combining
several different sequence databases?  For example, the UCSC
multigenome alignments do exactly that, because each alignment must
refer to sequences from several different genome databases.
UCSC adopted the convention of pre-pending a prefix for each
genome, e.g. "hg17", separated by a dot from the sequence ID within
that genome, e.g. "hg17.chr1".  

Pygr provides a simple way of combining multiple sequence databases,
called :class:`seqdb.PrefixUnionDict`.

Let's get a couple more sequence databases from worldbase, then
combine them::

   >>> mm8 = worldbase.Bio.Seq.Genome.MOUSE.mm8()
   >>> rn4 = worldbase.Bio.Seq.Genome.RAT.rn4()
   >>> pud = seqdb.PrefixUnionDict(dict(hg17=hg17,mm8=mm8,rn4=rn4))

We have to initialize the :class:`seqdb.PrefixUnionDict` with a dictionary
of the prefix:sequence_db pairs we want it to combine.  Now we can use
it as a sequence database that seems to contain all the sequences
within any of its member databases::

   >>> len(pud)
   125
   >>> len(hg17) + len(rn4) + len(mm8)
   125
   >>> pud.keys()
   ['rn4.chr6_random', 'rn4.chr19_random', 'rn4.chr8_random', 'rn4.chrX', 'rn4.chr13', 'rn4.chr12', 'rn4.chr11', 'rn4.chr15_random', 'rn4.chr17', 'rn4.chr16', 'rn4.chr15', 'rn4.chr14', 'rn4.chr19', 'rn4.chr18', 'rn4.chrM', 'rn4.chr1_random', 'rn4.chr13_random', 'rn4.chr3_random', 'rn4.chr9_random', 'rn4.chr14_random', 'rn4.chr10', 'rn4.chrUn_random', 'rn4.chr4_random', 'rn4.chr18_random', 'rn4.chr2_random', 'rn4.chr20_random', 'rn4.chr20', 'rn4.chr10_random', 'rn4.chr11_random', 'rn4.chr7', 'rn4.chr6', 'rn4.chr5', 'rn4.chr4', 'rn4.chr3', 'rn4.chr2', 'rn4.chr1', 'rn4.chr7_random', 'rn4.chrX_random', 'rn4.chr9', 'rn4.chr8', 'rn4.chr16_random', 'rn4.chr5_random', 'rn4.chr17_random', 'rn4.chrUn', 'rn4.chr12_random', 'mm8.chrY_random', 'mm8.chr8_random', 'mm8.chrY', 'mm8.chrX', 'mm8.chr13', 'mm8.chr12', 'mm8.chr11', 'mm8.chr10', 'mm8.chr17', 'mm8.chr16', 'mm8.chr15', 'mm8.chr14', 'mm8.chr5_random', 'mm8.chr19', 'mm8.chr18', 'mm8.chrM', 'mm8.chr1_random', 'mm8.chr13_random', 'mm8.chr9_random', 'mm8.chrUn_random', 'mm8.chr10_random', 'mm8.chr7', 'mm8.chr6', 'mm8.chr5', 'mm8.chr4', 'mm8.chr3', 'mm8.chr2', 'mm8.chr1', 'mm8.chr7_random', 'mm8.chrX_random', 'mm8.chr9', 'mm8.chr8', 'mm8.chr15_random', 'mm8.chr17_random', 'hg17.chr6_random', 'hg17.chr19_random', 'hg17.chr8_random', 'hg17.chrY', 'hg17.chrX', 'hg17.chr13', 'hg17.chr12', 'hg17.chr11', 'hg17.chr15_random', 'hg17.chr17', 'hg17.chr16', 'hg17.chr15', 'hg17.chr14', 'hg17.chr19', 'hg17.chr18', 'hg17.chrM', 'hg17.chr1_random', 'hg17.chr13_random', 'hg17.chr3_random', 'hg17.chr6_hla_hap2', 'hg17.chr9_random', 'hg17.chr22_random', 'hg17.chr10', 'hg17.chr4_random', 'hg17.chr18_random', 'hg17.chr2_random', 'hg17.chr22', 'hg17.chr20', 'hg17.chr21', 'hg17.chr10_random', 'hg17.chr6_hla_hap1', 'hg17.chr7', 'hg17.chr6', 'hg17.chr5', 'hg17.chr4', 'hg17.chr3', 'hg17.chr2', 'hg17.chr1', 'hg17.chr7_random', 'hg17.chrX_random', 'hg17.chr9', 'hg17.chr8', 'hg17.chr16_random', 'hg17.chr5_random', 'hg17.chr17_random', 'hg17.chr12_random']

As with any Pygr database, we can ask for its reverse mapping.  Since
the database maps a sequence ID to a sequence object, the reverse
mapping takes a sequence object and returns its ID.  But note that
:class:`seqdb.PrefixUnionDict` returns the correct ID for looking
up that sequence object in the prefix union, which in this case
is *not* the same as the sequence object's ``id`` attribute::

   >>> idDict = ~pud
   >>> idDict[chr1]
   'hg17.chr1'
   >>> chr1.id
   'chr1'
   >>> mouse_chr5 = pud['mm8.chr5']
   >>> idDict[mouse_chr5]
   'mm8.chr5'

:class:`seqdb.PrefixUnionDict` is commonly used by :class:`cnestedlist.NLMSA`
multiple genome alignments to access many genome databases as a single
database.  This simply follows UCSC's practice of indexing their
multigenome alignments using this "prefix.ID" notation.



