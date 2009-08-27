:mod:`cnestedlist` --- Highly scalable sequence alignment database
==================================================================

.. module:: cnestedlist
   :synopsis: Highly scalable sequence alignment database.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>


Pygr provides a general model for interfacing with any kind of sequence alignment,
and also a uniquely scalable storage system for working with huge multiple sequence
alignments such as multigenome alignments.  Specifically, it lets you work with
an alignment both in the traditional Row-Column model (each row is a sequence, each
column is a set of individual letters from different sequences, that are aligned;
we will refer to this as the RC-MSA model), and also
as a graph structure (known as a Partial Order Alignment, which we will refer to as
the PO-MSA model).  This supports "traditional" alignment analysis, as well
as graph-algorithms, and even graph query of alignments.

This model has a few basic classes:

* :class:`NLMSA`: this class represents an entire alignment.  It acts as a graph whose
  nodes are sequences (or sequence intervals) that are aligned, and whose edges
  represent specific alignment relationships between specific pairs of sequences
  (or intervals).  Specifically, it acts as a dictionary whose keys are SeqPath
  objects, and whose values are MSASlice objects (representing an alignment segment
  associated with a specific SeqPath, see below for details).  For example, to find
  out what's aligned to some sequence interval s1::
  
     for s2 in msa[s1]: # GET ALL INTERVALS s2 ALIGNED TO s1 IN msa
         do_something(s1,s2)
  
  
  In addition, its *letters* attribute acts as a graph interface
  to the Partial Order alignment (PO-MSA) representation of the alignment.  I.e.
  it is a graph whose nodes each represent a set of individual letters from
  different sequences, that are aligned to each other, and whose edges connect
  pairs of nodes that are "adjacent" to each other in at least one sequence.
  Specifically, it acts as a dictionary whose keys are MSANode objects (see below),
  and whose edges are LetterEdge objects (see previous section)::
  
     for node in msa.letters: # GET ALL ALIGNMENT "COLUMNS" IN msa
         for l in node: # GET ALL INDIVIDUAL SEQ LETTERS ALIGNED HERE
             say_something(node,l)
  
  
  
* :class:`NLMSASlice`: this class represents a segment of alignment associated with
  a specific sequence interval (s1).  It acts as dictionary whose keys are sequence
  intervals s2 aligned to s1, and whose values are MSASeqEdge objects
  that represent the alignment relationship between s1 $\rightarrow$ s2.  It also
  has a *letters* attribute, that represents the subgraph of nodes
  associated specifically with s1, and the edges that interconnect them::
  
     myslice = msa[s1]: # GET SLICE ALIGNED TO s1 IN msa
         for node in myslice.letters:  # GET ALL ALIGNMENT "COLUMNS" FOR s1
             for l1,l2,e in node.edges(): # GET INDIVIDUAL LETTERS ALIGNED TO l1 OF s1
     	    whatever(l1,l2,e)
  
  
  This class also has a *regions* method that generates all the alignment
  interval relationships in this slice according to "grouping" criteria such
  as maximum permissible gap length, etc.  (i.e. any region of alignment containing
  no gaps larger than a specified size would be returned as a single region,
  whereas any gap larger than the specified size would split it into two separate
  regions).  This provides a general interface for group-by operations in alignment
  query.
  
* :class:`NLMSASeqEdge`: this class represents a relationship between a pair of
  sequence intervals s1 and s2 (SeqPath objects).  It provides a mapping between
  subintervals of s1 $\rightarrow$ s2.  I.e. it acts as a dictionary
  that accepts subintervals of s1 as keys, and maps them to aligned
  subintervals of s2.  It also
  has a *letters* attribute, that represents the subgraph of nodes
  associated specifically with them, and the edges that interconnect the nodes.
  
* :class:`NLMSANode`: this class represents a specific "column" in the alignment
  that aligns a set of individual letters from different sequences.  This
  corresponds to a node in the PO-MSA representation of the alignment.
  It acts as a dictionary whose keys are sequence intervals (typically only
  one letter long) aligned in this column, and whose values are MSASeqEdges
  representing the alignment of that letter to the column (see above).
  


NestedList Storage
------------------
Pygr provides a highly scalable storage mechanism for working with
multi-genome alignments.  One fundamental challenge in working with
very large alignments is the *interval overlap query* problem:
to obtain a portion of an alignment (defined by some interval of
interest) requires finding all interval elements in the "alignment
database" that overlap the query interval.  Since the intervals
can be indexed by start (or end) position, one can typically find the
first overlapping element in $O(\log N)$ time, where $N$ is the total
number of intervals in the database.  The problem is that since
standard index structures cannot index both *start* and *end*,
to obtain *all* intervals that overlap the query interval, one must scan
forwards (or backwards) from that point.  Furthermore, one cannot stop
at the first non-overlapping interval; there might be an extremely long
interval at the very beginning of the index, that extends to overlap
the query interval.  In this case, one would have to scan the entire
database ($O(N)$ time) to guarantee that all overlapping intervals are
found.

The *nested list* data structure solves this problem, by moving
any interval in the database that is *contained* in another interval
out of the top-level interval list, into the *sublist* of the
parent interval.  Based on this, one can prove that one can stop
the scanning operation at the first non-overlapping interval (i.e.
the overlapping intervals in any list form a single contiguous block).
Overall, this reduces the query time to $O(\log N + n)$, where $n$ is
the number of intervals in the database that actually overlap the
query (i.e. results to return).  Moreover, the nested list data structure
can be implemented very well both in computer memory (RAM) or as indexed
disk files.  Pygr's disk-based cnestedlist database can complete
a typical interval query of the 26GB UCSC 8 genome alignment in
about 60 microseconds, compared with 10-30 seconds per query using
MySQL.

Multiple Mappings: a Warning
----------------------------
Multi-genome alignments take traditional models of alignment to an
entirely different scale, and inevitably many of the assumptions of
standard row-column multiple sequence alignment are broken (e.g.
no inversions; no cycles; etc.).  One major issue that users should be
aware of in UCSC multi-genome alignments is the possibility of
*multiple mappings*, in which a given query sequence interval is
mapped to two or more different regions of the alignment (and thus potentially
to two or more different locations in a given target genome).  Currently,
UCSC multi-genome alignment are typically based on a single
*reference genome*, to which all other genomes are aligned.  While
a given region of the reference genome might be guaranteed to have
a unique mapping in the UCSC multi-genome alignment, *other* genomes
do not appear to have any such guarantee: a region in any of those genome
can have multiple mappings.  This is problematic for several reasons:

  
* It introduces ambiguity in the alignment: you don't know which of the
  multiple hits is considered to be the "right" alignment; the UCSC alignment
  file does not tell you.
  
* There is no scoring information to resolve this ambiguity.  In a way,
  this situation is even worse than the common situation we previously faced
  in search for alignment mappings using BLAST, because (unlike BLAST) the
  MAF alignment does not give a score that indicates which mapping is best.
  (We haven't seen such scoring information; if it can be recovered for these
  alignment files, we'd be love to know about that...).
  
* It can cause "buggy" results in calculations based on the alignment.
  For example, Pygr's :meth:`pIdentity()` and :meth:`pAligned()` computations
  can give values larger than one when a query region has multiple hits.  This
  is not, strictly speaking, a Pygr bug: the query region is mapped by the MAF
  file to the same target region *multiple* times, resulting in multiple
  overlaps.
  


If you encounter multiple mappings, you can always iterate over them one
by one, and perform your own computations for each one.  However, to avoid them
altogether, you can restrict your queries to the reference genome for this specific
alignment (UCSC offers different versions of each alignment set, each based on
a different reference genome).

NLMSA
-----
Top-level object representing an entire multiple sequence alignment,
stored using a set of disk-based nested list interval databases.
The alignment is stored as an interval representation of a
*linearized partial order* (LPO), using *nested list*
databases.  This has several elements:


  
* *PO-MSA*: Conceptually, the alignment is represented as a partial order alignment
  (PO-MSA), in which aligned sequence intervals are fused together as a single
  "node" in the alignment graph; two nodes are connected by an edge if and only
  if they are adjacent in at least one of the sequences aligned to them
  (i.e. if residue *i* of that sequence is in the first node, and
  residue *i+1* is in the second node, then there is a directed edge
  from the first PO-MSA node to the second node).
  
* *LPO*: This alignment graph is *partially ordered*.  Let's define an
  ordering relation *"i<j"* to mean "there exists a path
  of directed edges from *i* to *j*".  For two
  letters *i* and *j* in a sequence, *i<j XOR j<i* (i.e. all
  nodes have an ordering relationship).  By contrast, if two nodes in the LPO
  represent insertions in different sequences, then NOT *i<j* AND NOT *j<i*.
  Thus there can be some nodes in the LPO that have no ordering relationship
  with respect to each other.  It is still possible to map the PO-MSA onto
  a linear coordinate system (i.e. to "linearize" the partial order): as long
  as the graph contains no cycles, we can map the nodes *i,j,k,...* of the graph
  onto a linear coordinate system *x,y,z,...* such that for any pair of
  nodes *i,j* mapped to coordinates *x<y*, we assert NOT *j<i*.  This is
  called the *linearized partial order* (LPO). This maps the PO-MSA onto
  a standard Row-Column MSA format, where the LPO coordinate (just an integer
  sequence 0,1,2...) can be considered the index value of each alignment column.
  
* *nested list*: The actual alignment data are stored in the form of
  (*start,stop*) pairs representing aligned intervals.  Since this representation
  uses intervals, not individual letters, it takes no more memory to store
  an alignment of two 100 kb regions than it does to align two individual letters.
  This is important for scalable storage (and query) of large multi-genome
  alignments.  (Each alignment interval takes 24 bytes: five :class:`int` for
  the *(start,stop)* pairs and target sequence ID, plus one :class:`int`
  for the sublist ID).
  These interval databases are stored using nested lists.  Specifically,
  the alignment is stored as 1) a mapping of each aligned sequence interval
  onto an LPO coordinate interval; 2) a reverse mapping of each LPO interval onto
  all the sequence intervals that are aligned there.  To find the alignment of
  a sequence interval onto the other sequences in the alignment, that interval
  is first mapped onto the LPO, and from there mapped back to intervals in the
  other sequences.  A nested list database is stored for *each* of these
  mappings (i.e. for an alignment of *N* sequences, there will be *N+1*
  nested list databases to store the MSA).  Furthermore, if the size of the LPO
  coordinate system (i.e. number of columns in its RC-MSA format)
  grows larger than the range representable by :class:`int` (typically $2^{31}$  = 2 GB),
  the LPO will have to be split into separate nested list databases of a size
  smaller than the maximum range representable by :class:`int`.  This is necessary
  for handling alignments of large genomes (e.g. the human genome is approximately 3 GB).
  Pygr takes care of all this for you automatically.  Note, as an entirely separate
  issue, that Pygr's cnestedlist
  module uses the :class:`long long` data type for file offsets and
  the \function{fseeko()} POSIX interface for large file support (i.e. 64-bit
  file sizes), which is supported by current versions of Linux, Mac OS X, etc;
  otherwise, check if your filesystem supports this.
  


This functionality is encapsulated in the NLMSA class, which has a number of methods
and attributes.

Construction Methods:

.. class:: NLMSA(pathstem=", mode='r', seqDict=None, mafFiles=None, axtFiles=None, maxOpenFiles=1024, maxlen=None, nPad=1000000, maxint=41666666, trypath=None, bidirectional=True, pairwiseMode= -1, bidirectionalRule=nlmsa_utils.prune_self_mappings, maxLPOcoord=None)

   Constructor for the class.  *pathstem* specifies a path and filename prefix for
   the NLMSA files (since multiple files are used to store one NLMSA, it will automatically add a
   number of suffixes automatically to open the necessary set of files for the NLMSA).
   *mode* is either "r" to open an existing NLMSA (from the *pathstem* disk files);
   "w" to create a new one (which will be saved to the *pathstem* disk files);
   or "memory" to create a new in-memory NLMSA (i.e. stored in your computer's RAM
   instead of using files on your hard disk).  Obviously, this limits you to
   the amount of RAM in your computer, but will make the NLMSA much, much faster.

   *seqDict* specifies a dictionary which maps sequence names to actual sequence
   objects representing those sequences.  If *seqDict* is None, the constructor
   will call :meth:`nlmsa_utils.read_seq_dict()` to try to obtain it from files
   associated with the NLMSA.  It first looks for a file *pathstem*``.seqDictP``
   that is simply a pickle of the *seqDict* data.  If this is not found, it
   next looks for a file *pathstem*``.seqDict`` that is a :class:`seqdb.prefixUnionDict`
   header file for opening all the sequence database files for you automatically.
   This header file will itself specify a list of sequence database files; the
   *trypath* option, if provided, specifies a list of directories in which to look for these
   sequence database files.

   The *bidirectional* option indicates whether you wish the NLMSA to
   save each input alignment relationship A:B in *both* possible directions
   (i.e. nlmsa[A] will yield B, and nlmsa[B] will yield A).  In general, the
   *bidirectional=True* mode is most appropriate for true multiple sequence
   alignments, i.e. where it is guaranteed that for a given pair of sequences A,B
   each interval of A maps to a unique interval in B, which in turn maps back
   to the same interval of A (and *only* that interval in A).  There are
   many possible scenarios where you might prefer *bidirectional=False* mode:

   * When you WANT your alignment to have a specific directionality.  For example,
     if ``nlmsa`` is a mapping of the human genome sequence onto the mouse genomic
     sequence, then ``nlmsa[s]`` should only yield a result if ``s`` is a human
     genome sequence interval; a mouse genome sequence interval should raise a :exc:`KeyError`.

   * When the input alignment data themselves give each A:B relationship in
     both directions (i.e. the input data include both an A:B mapping and also a
     B:A mapping).  Since the input data contain both directions of each mapping,
     there is no need for the constructor code to save each input alignment
     bidirectionally.  In this case *bidirectional=True* mode would cause duplicate
     mappings to be saved (i.e. the A:B mapping would be saved twice, and the B:A mapping
     would also be saved twice) and thus alignment queries would yield duplicated results.
     In such a case, *bidirectional=False* prevents this problem.

   * A common example of this issue is when the
     input alignment data may contain multiple, inconsistent alignments of
     a given pair of sequences.  For example, a BLAST all-vs-all will return TWO alignments
     of A,B: one when A is blasted against the database (finding B), and another when
     B is blasted against the database (finding A).  These two alignments could be different!
     In this case, a *bidirectional=True* alignment would return BOTH alignments
     (i.e. ``nlmsa[A]`` will return TWO alignments of B, which might be identical...
     or might be significantly different).  This is undesirable behavior.  Instead,
     use *bidirectional=False* so that ``nlmsa[A]`` will simply return the
     alignments that were found when A was blasted against the database.

   * In general, using *bidirectional=True* can yield multiple, potentially
     inconsistent results when the input data are not a true multiple-sequence alignment
     (e.g. BLAST alignment data is strictly pairwise, not a true multiple-sequence alignment).

   *pairwiseMode=True* indicates a PAIRWISE sequence alignment, in which
   the stored alignment relationships each consist of a pair of sequence intervals
   that are aligned.  Note: this pairwise format can store the alignment of *any*
   number of sequences, but the key point is that the individual alignment relations
   are pairwise, sequence-to-sequence.  The opposite model (*pairwiseMode=False*)
   indicates a true MULTIPLE sequence alignment, in which the stored alignment
   relationships each consist of an integer coordinate interval (the alignment's internal
   coordinate system, for technical reasons called the "LPO") and a sequence
   interval that is aligned to it.  Under normal circumstances, you will not need
   to specify a value for the *pairwiseMode* option; the NLMSA will infer
   the correct setting automatically based on the input data.  Note: the pairwise format
   (*pairwiseMode=True*) and multiple alignment format (*pairwiseMode=False*)
   cannot be mixed in a single NLMSA.  It must be either one format or the other.

   *mafFiles* can be used to specify a list of
   filenames containing a multiple sequence alignment in the UCSC MAF format,
   for saving as a new NLMSA (i.e. ``mode='w'``).
   Note that this automatically sets ``pairwiseMode=False``.  After the MAF
   data are read, it will automatically call the :meth:`NLMSA.build()` method to construct
   the alignment index files.

   *axtFiles* can be used to specify a list of
   filenames containing a set of pairwise alignments in UCSC axtNet format,
   for saving as a new NLMSA (i.e. ``mode='w'``).
   Note that this automatically sets ``pairwiseMode=True``.  After the axtNet
   data are read, it will automatically call the :meth:`NLMSA.build()` method to construct
   the alignment index files.

   *bidirectionalRule* allows the user to provide a function that has
   complete control over the desired *bidirectional* setting to use for
   each possible pair of sequence databases.  Currently, this is only used
   for *axtFiles* reading; the default method (:meth:`nlmsa_utils.prune_self_mappings`)
   filters out duplicate mappings for a sequence database onto itself
   (since these are provided in both forward and reverse directions in the axtNet
   file), but stores mappings for one sequence database to another
   bidirectionally (since the axtNet files give such mappings in only one direction
   normally).  To implement your own bidirectionalRule function, see
   :meth:`nlmsa_utils.prune_self_mappings()` as an example.

   *maxlen* specifies the maximum coordinate
   value for a union or LPO coordinate system.  Its default value is 2GB, to prevent :class:`int` overflow.
   Using a smaller value can be useful, to 1) limit the size of the LPO in memory
   during initial construction, and 2) to limit the size of LPO database files on disk
   (if for example, your file system does not support files above some maximum size).
   During initial construction of the NLMSA (from MAF files or user-specified interval
   alignments), the algorithm performs a one-pass sort of the LPO intervals.  Thus,
   this set of intervals is briefly held in RAM for this sort.  If you have insufficient
   RAM, the construction step may raise a MemoryError.  If so, you can avoid this problem
   by using a smaller *maxlen* value.

   The *maxint* option provides another way of limiting the size of LPO
   databases.  It specifies the maximum number of intervals to store per LPO database.
   Since each interval takes 24 bytes, the default setting limits each LPO to
   a total size of 1 GB.  Note that the current NLMSA construction algorithm
   requires loading each database index into memory as one-time operation
   during construction.  If your NLMSA build fails due to running out of memory,
   simply reduce this value.

   The *nPad* option sets the maximum number of LPO coordinate systems
   (specifically, the offset for the start of real sequence IDs in the NLMSA
   sequence index).  You are unlikely to need to change this default value.

   *maxOpenFiles* limits the open file descriptors the NLMSA will use.
   *This option is no longer of much importance.  In versions prior to pygr 0.5,
   however, it was important because each sequence in the alignment had its
   own index file (in v.0.5 and later this problem is solved by unionization;
   for details see below)*.  Since
   each sequence has a separate nested list database file, a large multi-genome alignment
   (with each genome containing 20 different chromosomes, say) can rapidly open a large
   number of file descriptors.  Note: NLMSA only opens a given sequence's nested list database
   when one of your queries actually requires access to that sequence; it then
   keeps that file descriptor open to make subsequent queries to it fast.  If the number
   of open file descriptors would exceed *maxOpenFiles*, it will close other open
   database files, which may slow down query performance (due to having to open and close
   databases repeatedly to process queries).




.. method:: NLMSA.__iadd__(sequence)

   As part of constructing an alignment, adds *sequence* to the alignment graph,
   so that you can subsequently save specific alignments of intervals of
   *sequence*, using code like ``nlmsa[s]+=s2``, where ``s`` is
   an interval of *sequence* and ``s2`` is some other sequence interval.
   If *sequence* had not been added to the alignment, this later operation
   will raise a :exc:`KeyError`.


.. method:: NLMSA.addAnnotation(annotation)

   adds an alignment relationship to *annotation* from its underlying
   sequence interval.  Note: to use this, the NLMSA must have been created with the
   *pairwiseMode=True* option.


.. method:: NLMSA.__getitem__(seqInterval)

   prepare to store an alignment relationship for the sequence interval *seqInterval*,
   i.e. get a BuildMSASlice object representing *seqInterval*, to which you can
   then add other sequence intervals to align them.  I.e. ``nlmsa[s1]+=s2``
   saves the alignment of intervals s1 and s2.
   You can also use a regular Python *slice* object using integer indices
   ie. ``nlmsa[1:45]``, in which case, it indicates that
   region of the LPO coordinate system.
   If the sequence containing
   interval *s2* is not already in the NLMSA, it will be added for you automatically
   (i.e. creating the necessary indexing, nested list database files, etc.).  In this
   case, the sequence must supply a unique string identifier, which will be used
   on subsequent attempts to open the NLMSA database, to match the individual sequence
   nested-list databases against corresponding sequence objects (using *seqDict*,
   see above).



.. method:: NLMSA.build(buildInPlace=True,saveSeqDict=False,verbose=True)

   to construct the final nested list databases,
   after all the desired alignment intervals have been saved (using the
   :meth:`iadd/getitem` above).  This method
   simply calls the build() method on all the constituent NLMSASequence objects
   in this alignment.  NOTE: you do not need to call :meth:`NLMSA.build()` if
   you provided a *mafFiles* constructor argument, since that automatically
   calls :meth:`NLMSA.build()`.

   *buildInPlace=False* forces it to use an older NLMSA construction method
   (higher memory usage, but more tested).  The new in-place construction method
   (made the default in release 0.7) is described in the Alekseyenko \& Lee 2007
   paper published in *Bioinformatics*.

   *saveSeqDict=True* forces it to write the NLMSA's seqDict (dictionary
   of sequences that are included in the alignment) to disk.  This is unnecessary
   if you intend to store the NLMSA in worldbase, as worldbase will automatically
   save the NLMSA's seqDict as part of that process.  However, if you plan on
   re-opening the NLMSA directly from disk, you should save the seqDict
   to disk by passing this option, or by directly calling the NLMSA's
   save_seq_dict() method.

   *verbose* controls whether the method will print explanatory
   messages to stderr about the saveSeqDict=False mode.
   To suppress printing of these messages, use *verbose=False*.


.. method:: NLMSA.save_seq_dict()

   Forces saving of the NLMSA's seqDict to a disk file named 'FILESTEM.seqDictP'
   (where FILESTEM is the base path to your NLMSA files).  This is unnecessary
   if you intend to store the NLMSA in worldbase, as worldbase will automatically
   save the NLMSA's seqDict as part of that process.  The seqDictP file format
   is a worldbase-aware pickle; that is, references to any worldbase resources
   will simply be saved by their worldbase IDs, and loaded in the usual
   worldbase way.




Alignment Usage Methods:

.. method:: NLMSA.__getitem__(s1)

   get the alignment slice for the sequence interval *s1*,
   i.e. get an NLMSASlice object representing the set of intervals aligned to *s1*.
   You can also use a regular Python *slice* object using integer indices
   ie. ``nlmsa[1:45]``, in which case, it gets the NLMSA slice corresponding to that
   region of the LPO coordinate system.


.. method:: NLMSA.doSlice(s1)

   If you subclass NLMSA and provide a :meth:`doSlice` method, the NLMSA will
   call your :meth:`doSlice(seq)` method to find alignment results for ``seq``,
   instead of querying its stored alignment data.  You can thus use this
   to provide an NLMSA interface around virtually any source of alignment information
   that you have.  To see an example, see the :class:`xnestedlist.NLMSAClient` class.



.. attribute:: NLMSA.seqDict
   
   This attribute provides the dictionary mapping sequence IDs to sequence
   objects contained in this alignment.  You can request its inverse mapping,
   as a convenient way of getting the sequence ID for any sequence object
   in the alignment.  For example::

      d = ~(nlmsa.seqDict) # get the inverse mapping
      print d[myseq]  # get myseq's ID or raise KeyError if not in nlmsa.seqDict

.. attribute:: NLMSA.seqs

   This attribute provides a dictionary of the sequences in
   the NLMSA, whose keys are top-level sequence objects, and whose values are
   the associated NLMSASequence object for each sequence.  Ordinarily you will have
   no need to access the NLMSASequence object directly; only do so if you know what
   you're doing (details below).  This dictionary is of type NLMSASeqDict (see below).
  


dump_textfile, textfile_to_binaries
-----------------------------------
These two functions enable you to dump a constructed NLMSA binary database
to a platform-independent text format, and to restore an NLMSA binary database
from this text format.  This can be useful for

* speeding up the process of installing an NLMSA database on multiple
  machines.  Since the restore operation does not involve a build step, it
  can be substantially faster than building the NLMSA separately on each machine.
  
* moving an NLMSA database from one machine to a machine with a different
  binary architecture.  Since the binary database format depends on platform-specific
  details (e.g. big-endian vs. little-endian integer representation), it is not
  compatible between different architectures.
  
* using an NLMSA database on a machine that has insufficient RAM memory
  to perform the binary database build.  You can build the NLMSA binary database
  on another machine with sufficient RAM, dump it to text, then restore it on
  the desired machine where you wish to be able to use it.
  
* using the text format to "package" an NLMSA database for distribution
  on the Internet.  Users need only to obtain a single file and run a single command
  to restore the NLMSA database.  Users only need sufficient disk space to hold
  the NLMSA; they do not need large amounts of RAM (because they will not have to
  perform a "build" step).
  


.. function:: dump_textfile(pathstem,outfilename=None,verbose=True)

   Dumps a text representation of an existing NLMSA binary database.
   *pathstem* must be the path to the NLMSA.  For
   example if you have an NLMSA database index file ``/loaner/hg17_NLMSA/hg17_msa.idDict``
   (and many other index files with different suffixes),
   then you would supply a *pathstem* value of ``/loaner/hg17_NLMSA/hg17_msa``.

   *outfilename* gives the path for the output text file into which the
   NLMSA database will be dumped.  If None, it will default to *pathstem* with a
   ``.txt`` suffix added.

   Setting *verbose=False* will prevent printing of warning messages
   to stderr (for details about possible warnings, see below).

   Note: :meth:`dump_textfile` attempts to save information about the seqDict
   (or, alternatively, the PrefixUnionDict dictionary of multiple sequence
   databases), using their worldbase IDs if possible.
   Specifically, for a PrefixUnionDict (i.e. multiple sequence databases in
   one NLMSA), it saves a dictionary of the prefixes
   for each sequence database in the NLMSA, with its worldbase ID if it has one.
   Assigning a worldbase ID to each sequence database has the great advantage that
   the reconstruction method :meth:`textfile_to_binaries()` can simply request
   worldbase for these IDs on the destination machine, automatically.  By contrast,
   if a sequence database has no worldbase ID, the user will have to supply that
   sequence database manually on the destination machine.  In this case,
   :meth:`dump_textfile` will print a warning message to stderr explaining
   what the user must do.  This provides yet another reason why it's a good idea
   to assign a worldbase ID to any sequence database that is a well-defined,
   commonly used public resource.



.. function:: textfile_to_binaries(filename,seqDict=None,prefixDict=None)

   Creates an NLMSA binary database from input text file *filename*.
   The NLMSA binary database will be created in the current directory,
   and will be given the same name as it originally had prior to being dumped to text.
   Since no build is required, this function does not require significant amounts
   of RAM memory.

   Handling of sequence databases: :meth:`textfile_to_binaries` will attempt to
   obtain any needed sequence databases using their worldbase ID if assigned.
   If you obtain a :class:`PygrDataNotFoundError`, this simply means that one
   of the worldbase IDs was not found in any of your worldbase resource
   databases.  In this case, you must either add it to one of your resource
   databases, or add a resource database that does contain it to your PYGRDATAPATH,
   then re-run :meth:`textfile_to_binaries`.

   On the other hand, if any of the needed sequence databases were NOT assigned
   a worldbase ID, then you will have to provide that sequence database(s)
   manually to the :meth:`textfile_to_binaries()` function, either via
   its *seqDict* argument (if the NLMSA contains only one sequence database),
   or via its *prefixDict* argument (if the NLMSA contains multiple sequence
   databases).  If you do not
   do so, an appropriate error will be raised, explaining what you need to do.
   The *prefixDict* argument must be a dictionary whose keys match
   individual sequence database prefixes in the original NLMSA PrefixUnionDict,
   and whose associated values are the appropriate sequence database to use
   for each specified prefix.  You only need to provide those sequence databases
   that :meth:`textfile_to_binaries()` is unable to obtain from worldbase.
   When in doubt, just run :meth:`textfile_to_binaries()` without the *prefixDict*
   argument, and it will raise an error message listing the prefixes that you
   need to provide.




xnestedlist.NLMSAServer, xnestedlist.NLMSAClient
------------------------------------------------
These two classes, provided by the separate :mod:`xnestedlist` module,
provide an XMLRPC client-server mechanism for querying NLMSA databases
over a network.

.. class:: NLMSAServer(pathstem=", mode='r', seqDict=None, mafFiles=None, axtFiles=None, maxOpenFiles=1024, maxlen=None, nPad=1000000, maxint=41666666, trypath=None, bidirectional=True, pairwiseMode= -1, bidirectionalRule=nlmsa_utils.prune_self_mappings, maxLPOcoord=None)

   is constructed exactly the same as a normal :class:`NLMSA`;
   it *is* a normal NLMSA with just two methods added for serving XMLRPC client
   requests.  See the :class:`coordinator.XMLRPCServerBase` reference
   documentation below for details about starting an XMLRPC server.

.. class:: NLMSAClient(url=None, name=None, idDictClass=dict, **kwargs)

   provides a read-only client interface for querying
   data in a remote :class:`NLMSAServer`.  It takes two extra arguments for
   its constructor: *url*, the URL for the XMLRPC server; *name*,
   the name of the NLMSAServer server object in the XMLRPC server's dictionary.
   For example, to use an NLMSA stored on a remote XMLRPC server,
   assuming that ``myPrefixUnion`` stores a dictionary of all the
   sequence databases used by that NLMSA alignment, would just be::

      from pygr import xnestedlist
      nlmsa = xnestedlist.NLMSAClient(url='http://leelab.mbi.ucla.edu:5000',
                                      name='ucsc17', seqDict=myPrefixUnion)



NLMSASlice
----------
A temporary object created on-the-fly to represent (an interface to provide
information about) the portion of the alignment associated with a specific
sequence interval.  This is the main class for querying information about
alignments, and provides a number of useful methods for getting
detailed information about alignment relationships.

In addition, the NLMSASlice is the basic unit of *sequence caching*
control, by which you can ensure that pygr alignment analysis accesses
sequence databases in the most efficient way.  Here's how it works:

* When you perform an NLMSA query by creating an NLMSASlice, it assembles
  a list of covering intervals for all sequences in this part of the alignment
  (i.e. for each sequence, the smallest interval that contains all of its
  aligned intervals in this NLMSASlice).
  
* NLMSASlice then attempts to call the ``cacheHint`` method for each
  sequence database object containing the relevant sequences (if this method
  exists; if it doesn't, this step is skipped).  It passes the ``cacheHint`` method
  the covering interval information for the aligned sequence, and a reference to
  itself (the NLMSASlice object) as the *owner* of this cache hint.
  
* If any operation subsequently attempts to access the actual sequence
  for any interval that is contained within this covering interval, the sequence
  database will instead load the entire covering interval, which it stores in
  its cache, associated with the specified *owner*.  It then returns the
  appropriate subinterval of sequence requested, as usual.
  
* Any subsequent requests for sequence strings that fall within this
  covering interval will simply be obtained from this cache, instead of
  retrieving the sequence from disk files.
  
* This cache information is retained until the *owner* (in this case,
  the original NLMSASlice) is deleted (by Python garbage collecting).  Thus, to
  control sequence caching, all you have to do is hold on to the NLMSASlice as
  long as you want to work with its associated sequence intervals.  As soon as
  you drop it, its associated cache information will also be automatically deleted,
  freeing up memory.

.. class:: NLMSASlice(ns, start, stop, id= -1, offset=0, seq=None)

   An NLMSASlice acts like a dictionary whose keys are
   sequence intervals that are aligned to this region, and whose values are
   :class:`sequence.Seq2SeqEdge` objects providing detailed information about the alignment of
   the target interval (key) to the source interval (the sequence interval
   used to create the NLMSASlice in the first place).  You can use this
   dictionary interface in several ways:


.. method:: NLMSASlice.__iter__()

   iterates over all sequence intervals that have
   a 1:1 mapping (i.e. a block of alignment containing no indels) to
   all or part of the source interval.



.. method:: NLMSASlice.keys(maxgap=0, maxinsert=0, mininsert= 0, filterSeqs=None, mergeMost=False, mergeAll=False, maxsize=500000000, minAlignSize=None, maxAlignSize=None, pIdentityMin=None, ivalMethod=None, sourceOnly=False, indelCut=False, seqGroups=None, minAligned=1, pMinAligned=0., seqMethod=None, **kwargs)

   Provides a more general interface than *iter()*, with two types of
   group-by capabilities, "group-by" operations on the alignment intervals
   contained within this slice ("horizontal" grouping),
   and on the sets of sequences aligned
   to this slice ("vertical" grouping).

   1. "group-by" operations on the alignment intervals
   contained within this slice.  It allows the user to supply
   various parameters for controlling when alignment intervals will be
   merged or split in the results that it returns.

   *mergeAll*
   forces it to combine intervals of a given sequence irrespective
   of the size of gaps or inserts separating them.

   *mergeMost*
   forces it to combine intervals of a given sequence, within reason
   (but don't merge a whole chromosome if you get one interval from one end
   and one interval from the other end:
   *maxgap=maxinsert=10000, mininsert=-10, maxsize=50000*).

   *maxgap* sets the
   maximum gap size for merging two adjacent intervals.  If the target sequence
   for the two alignment intervals has a gap longer than *maxgap*
   letters between the two alignment intervals, they will be returned as
   separate intervals; otherwise they will be merged as a single alignment
   region.

   *maxinsert* sets the maximum length of insert in the target
   sequence that allows to adjacent intervals to be merged as a single alignment
   region in the results.

   *mininsert* is specifically for handling
   alignments that may have small "cycles" (due to slight inconsistencies
   in the reported alignment intervals, for example, if a portion of sequence
   can align at both the end of one interval or at the beginning of another, and
   the intervals are actually added to the NLMSA that way, then the *start*
   of the second interval will actually be *before* the *stop* of
   the first interval; this corresponds to a negative insert value).  A
   *mininsert* value of zero (the default), prevents any such interval
   pairs from being merged.  Giving a negative *mininsert* value will allow
   interval pairs whose insert value is greater than or equal to this value,
   to be merged.

   *maxsize*: upper bound on maximum size for interval merging.

   *filterSeqs*, if not None, should be a dict of sequences
   used to filter the group-by analysis; i.e. only alignment intervals
   containing these sequences are considered in the analysis.  More
   specifically, *filterSeqs* can be used to mask the group-by analysis
   to a specific interval of a sequence, by having *filterSeqs*
   return only the intersection between the interval it is passed as a key,
   and the masking interval that it stores.  If there is no overlap, it
   must raise :exc:`KeyError`.  The :class:`sequence.SeqFilterDict` class
   provides exactly this masking capability, i.e.::

      d = sequence.SeqFilterDict(someIntervals)
      overlap = d[ival] # RETURNS INTERSECTION BETWEEN ival AND someIntervals, OR KeyError

   *minAlignSize* if not None, sets a minimum size for filtering the resulting
   alignment regions.  Regions smaller than the specified size will be culled
   from the output.

   *maxAlignSize* if not None, sets a maximum size for filtering the resulting
   alignment regions.  Regions larger than the specified size will be culled
   from the output.

   *pIdentityMin* if not None, sets a minimum fractional sequence identity
   for filtering the resulting alignment regions.  Regions with lower levels
   of identity will be clipped from the output.  Specifically, within each
   region, the largest contiguous segment (possibly including indels, if
   permitted by *maxgap* and *maxinsert*) whose sequence identity is above the
   threshold will be returned (but only if it is larger than *minAlignSize*
   if set).

   *ivalMethod*,
   if not None, allows the user to provide a Python function that performs
   interval grouping.  Specifically it is called as
   ``ivalMethod(l, ns, msaSlice=self, **kwargs)``, where *l* is the
   list of intervals for NLMSASequence *ns* within the current slice
   *msaSlice*; all other args are passed as a dict in *kwargs*.

   2. merge groups of sequences using "vertical" group-by rules.
   *seqGroups*: a list of one or more lists of sequences to group.
   If None, the whole set of sequences will be treated as a single group.
   Each group will be analyzed separately, as follows:

   *sourceOnly*: output intervals will be reported giving only
   the corresponding interval on the source sequence; redundant
   output intervals (mapping to the same source interval) are
   culled.  Has the effect of giving a single interval traversal
   of each group.

   *indelCut*: for *sourceOnly* mode, do not merge separate
   intervals that the groupByIntervals analysis separated due to an indel).

   *minAligned*: the minimum number of sequences that must be aligned to
   the source sequence for masking the output.  Regions below
   this threshold are masked out; no intervals will be reported
   in these regions.

   *pMinAligned*: the minimum fraction of sequences (out of the
   total in the group) that must be aligned to the source
   sequence for masking the output.

   *seqMethod*: you may supply your own function for grouping.
   Called as \function{seqMethod(bounds,seqs,**kwargs)}, where
   *bounds* is a sorted list of
   *(ipos,isStart,i,ns,isIndel,(start,end,targetStart,targetEnd))*
   and *seqs* is a list of sequences in the group.
   Must return a list of *(sourceIval,targetIval)*.  See the docs.




.. method:: NLMSASlice.iteritems(**kwargs)

   same keys as *iter*, but for each provides the source interval
   to target interval mapping (:class:`Seq2SeqEdge`).
   Uses same group-by arguments as :meth:`keys()`.



.. method:: NLMSASlice.edges(**kwargs)

   same interval mappings as *iteritems*, but for
   each provides a tuple of three objects:
   the source interval, the corresponding target interval,
   and the :class:`Seq2SeqEdge` providing detailed
   information about the alignment between the source and target intervals
   (such as percent identity, etc.).
   Uses same group-by arguments as :meth:`keys()`.



.. method:: NLMSASlice.__getitem__(s1)

   treats *s1* as a key (target sequence
   interval), and returns an :class:`Seq2SeqEdge` object providing detailed
   information about the alignment between this target interval
   and the source interval.



.. method:: NLMSASlice.__len__()

   returns the number of distinct sequences that
   are aligned to the source interval.  *Note*: this is NOT necessarily
   equal to the number of items that will be returned by the above iterators,
   since a single target sequence might have multiple 1:1 intervals of
   alignment to the source interval, due to indels.




In addition to these standard dictionary methods, NLMSASlice provides
several additional methods and attributes:



.. attribute:: NLMSASlice.letters

   this attribute provides an interface to
   the individual alignment columns (NLMSANode objects) containing the
   source interval, in order from *start* to *stop*.  This provides
   an easy way to obtain detailed information about the letter-to-letter
   alignment of different sequences within this region of the alignment.
   For details on the kinds of information you can obtain for each
   alignment column, see NLMSANode, below.
  
   It also provides a graph interface to subset of the partial order alignment
   graph corresponding to this slice.  For details, see NLMSASliceLetters, below.


.. method:: NLMSASlice.split(**kwargs)

   this method provides a way to perform group-by operations on the slice;
   the output of split() is one or more NLMSASlice objects; if the
   group-by analysis results in no splitting of the current slice, then
   it is returned unchanged (i.e. the method just returns *self*).
   Uses same group-by arguments as :meth:`keys()`.
   For further details on group-by operations, see :meth:`keys()` above.


.. method:: NLMSASlice.regions(**kwags)

   performs the same group-by analysis as *split()*, but replaces
   the source interval by the corresponding interval in the LPO.  The main
   practical consequence of this is that target sequence *inserts*
   are included in the resulting slice (because they are present in the LPO
   interval corresponding to the original source interval), whereas they
   were NOT included in the original slice (because they are not aligned
   to the source interval).  The main place where this matters is in graph
   traversal of the slice's *letters* attribute: whereas the nodes
   and edges corresponding to these inserts are not considered to be part
   of the *letters* graph for the original slice, they *are* part of the
   LPO slice.  Also, the "source interval" in any subsequent operations
   with the LPO slice will be LPO coordinates instead of subintervals of the
   original source sequence interval.
   Uses same group-by arguments as :meth:`keys()`.


.. method:: NLMSASlice.groupByIntervals(maxgap=0, maxinsert=0, mininsert= 0, filterSeqs=None, mergeMost=False, maxsize=500000000, mergeAll=True, ivalMethod=None, pIdentityMin=None, minAlignSize=None, maxAlignSize=None,**kwargs)

   This method performs the interval grouping analysis for all the iterators
   described above.  Users will not need to call it directly.  Its arguments
   are described above (see :meth:`keys()`).  It returns a dictionary
   whose keys are sequences aligned to this slice (represented by their integer nlmsa_id),
   and whose values are
   the list of intervals produced by the group-by analysis for the corresponding
   sequence.  The values are tuples of the form
   *(source_start, source_stop, target_start, target_stop)*, showing the
   mapping of a source sequence interval onto a target sequence interval.
   This dictionary is the primary input to the :meth:`groupBySequences()`
   method below.


.. method:: NLMSASlice.filterIvalConservation(seqIntervals,pIdentityMin=None,filterFun=None,**kwargs)

   This method is used by :meth:`groupByIntervals()` to filter the results
   using the specified *filterFun* filter function, which should either
   return *None* if the specified alignment region does not pass the filter,
   or return the filtered interval.  For an example
   filter function, see :meth:`conservationFilter`, which is used by default
   in :meth:`filterIvalConservation`.  *seqIntervals* must be passed in
   the same format as expected by :meth:`groupBySequences`; it is modified in
   place by :meth:`filterIvalConservation`, which always returns *None*.


.. method:: NLMSASlice.conservationFilter(seq,m,pIdentityMin=None,minAlignSize=None,maxAlignSize=None,**kwargs)

   Tests an alignment mapping *m* for the specified size and sequence
   identity criteria.  Returns the (possibly clipped) interval *m* if
   the criteria are met, and *None* if the criteria are not met.  *m*
   is expected to be a tuple of integers ``(srcStart,srcEnd,destStart,destEnd)``.
   *seq* must be the destination sequence object (sliceable by the destination
   interval coordinates).  The conservation criteria and clipping are performed
   using :meth:`Seq2SeqEdge.conservedSegment()`.


.. method:: NLMSASlice.groupBySequences(seqIntervals, sourceOnly=False, indelCut=False, seqGroups=None, minAligned=1, pMinAligned=0., seqMethod=None, **kwargs)

   This method performs the sequence grouping analysis for all the iterators
   described above.  *seqIntervals* must be a dictionary of sequences
   and their associated list of intervals (produced by :meth:`groupByIntervals()`
   above).  It returns a list of output sequence intevals, which is either
   a list of source sequence intervals (*sourceOnly* mode), or a list
   of tuples of the form *(source_interval, target_interval)*.



.. method:: NLMSASlice.matchIntervals(seq=None)

   this method returns the set of
   1:1 match intervals for the target sequence *seq* (or all
   aligned sequences, if *seq* is None), as a dictionary
   whose keys are target sequence intervals, and whose values are
   the corresponding source sequence intervals to which they are
   aligned.


.. method:: NLMSASlice.findSeqEnds(seq)

   returns the largest possible interval of
   *seq* that is aligned to this slice, i.e. it merges all
   alignment intervals in this slice containing *seq*, and
   returns the merged sequence interval based on the minimum *start*
   value and maximum *stop* value found.


NLMSASliceLetters
-----------------

represents the *letters* graph of a specific NLMSASlice.  It is
a graph whose nodes are the NLMSANode objects in this slice, and whose
edges are sequence.LetterEdge objects. *Note*: currently the edge objects
are just returned as None -- please implement!

This graph has the following methods:

.. method:: __iter__()

   generates all the nodes in the slice, in order from left to right.


.. method:: items()

   also :meth:`iteritems()`. Generate the same set of nodes as above,
   as keys, but for each also returns a value representing its outgoing
   directed edges (see getitem, below).


.. method:: __getitem__(node)

   gets a dictionary indicating all the outgoing
   directed edges from *node* to subsequence nodes, whose keys are
   the target nodes, and whose edges are the
   :class:`sequence.LetterEdge` objects representing each edge.


NLMSANode
---------
A temporary object (created on-the-fly)
representing a single letter "column" in the alignment.  It acts like
a container of the sequence letters aligned to the source sequence in
this column.  It has the following methods:

.. method:: __iter__()

   generates all the individual sequence letters
   (as SeqPath intervals, presumably of length 1) that are aligned to
   the source sequence, in this column of the alignment.



.. method:: edges()

   generates the same list of of target sequence letters as
   the iterator, but as a tuple of (target letter, source letter, edge).
   Currently, edge is just None.


.. method:: __len__()

   returns the number of distinct sequences aligned to
   the source interval, in this column.


Other, internal methods that regular users are unlikely to need:

.. method:: getSeqPos(seq)

   returns the sequence interval of *seq*
   that is aligned to this column, or raises :exc:`KeyError` if it is not
   aligned here.



.. method:: getEdgeSeqs(node2)

   returns a dictionary of sequences
   that traverse the edge directly from this node to *node2*,
   i.e. if letter *i* of seq is aligned to this node, then
   letter letter *i+1* is aligned to *node2*.  The
   dictionary's keys are top-level sequence objects, and its
   value for each is the letter position index *i* as defined above.


.. method:: nodeEdges()

   returns a dictionary of the outgoing edges
   from this node, whose keys are target nodes, and whose values
   are the corresponding edge objects (of type sequence.LetterEdge).



NLMSASequence
-------------
You are unlikely to need to manipulate NLMSASequence objects directly;
they perform the back-end work for accessing the nested list disk storage
of the alignment of the associated sequence.

However, one thing you should know is that for a sequence to be stored
in a NLMSA, it needs to have a unique string identifier.
NLMSASequence obtains a string identifier for the sequence in one of the following
ways (in decreasing order of precedence): 1) the sequence "object" can itself just
be a Python string, in which case that string is used as the identifier. 2) otherwise,
the object should be a SeqPath instance.  If it has a *name* attribute, that will
be used as the identifier. 3) Otherwise, if it has a *id* attribute (which is present
by default on sequence.Sequence objects), that will be used.

