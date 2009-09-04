
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

