Storing Alignments
------------------

Alignment Basics
^^^^^^^^^^^^^^^^

Pygr multiple alignment objects can be treated as mappings of sequence 
intervals onto sequence intervals.  Here is a very simple example, 
showing basic operations for constructing an alignment::

   >>> from pygr import cnestedlist
   >>>
   >>> # build an empty alignment, in-memory
   >>> m2 = cnestedlist.NLMSA('myo',mode='memory') 
   >>>
   >>> # add sequence s to the alignment
   >>> m2 += s 
   >>> ival = s[100:160] # AN INTERVAL OF s
   >>>
   >>> # add an edge mapping interval s -> an interval of MYG_CHICK
   >>> m2[ival] += db['MYG_CHICK'][83:143] 
   >>> m2[ival] += db['MYG_CANFA'][45:105] 
   >>>
   >>> # done constructing the alignment.  Initialize for query.
   >>> m2.build() 
   >>>
   >>> # get aligned seqs for the first 10 letters of ival...
   >>> for s2 in m2[ival[:10]]: 
   ...     print repr(s2)
   ...
   MYG_CHICK[83:93]
   MYG_CANFA[45:55]

In this case we used in-memory storage of the alignment.

Storing an All-vs-All BLAST Alignment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
However, for really large
alignments (e.g. an all vs. all BLAST analysis) we may prefer to store the alignment
on-disk.  In pygr, all we have to do is change the mode flag to 'w' (implying *write*
a file)::

   from pygr import cnestedlist,seqdb
   msa = cnestedlist.NLMSA('all_vs_all', mode='w', bidirectional=False) # on-disk
   sp = seqdb.SequenceFileDB('sp') # open swissprot database
   blastmap = blast.BlastMapping(sp) # create blast mapping object
   blastmap(None, msa, queryDB=sp, expmax=1e-10) # query with each seq in queryDB
   msa.build(saveSeqDict=True) # build & save alignment indexes
   # msa ready to query now...

Again you can see how pygr makes it quite simple to do a large analysis
and create a powerful resource (an all-vs-all alignment database).
A couple of points deserve comment:


  
* The in-memory and on-disk NLMSA alignment storages have exactly the same
  interface.  You can work with alignments from small to large to gimungous
  using the same consistent set of tools.  Moreover the performance will be
  fast across the whole range of scales, because the NLMSA storage and query
  algorithms scale very well (O(logN)).
  
* Because of the ``mode='w'`` flag, NLMSA will create a set of alignment
  index files called 'all_vs_all'.
  
* ``bidirectional=False``: whenever you store an alignment relationship
  ``S`` --> ``T``, this can either be *unidirectional* or *bidirectional*.
  Unidirectional means only the ``S`` to ``T`` mapping is stored; bidirectional means
  both ``S`` to ``T`` and ``T`` to ``S`` are stored (i.e. you can both query
  with ``S`` (and get ``T``), and query with ``T`` (and get ``S``).  In general, you want
  a unidirectional alignment storage when *directionality matters*.  For
  example, in a BLAST all vs. all search the alignment of ``S`` and ``T`` that you get
  when you blast ``S`` against the database (finding ``T``, among others) may well be
  different from the alignment of ``S`` and ``T`` that you get when you blast ``T`` against
  the database (finding ``S``, among others).  If you stored the all-vs-all alignment
  using bidirectional storage, querying ``msa`` with ``S`` would get *two* alignments
  to ``T``: one from the ``S`` to ``T`` BLAST search results, and one from the
  ``T`` to ``S`` BLAST search results.  This simply reflects the fact that
  the all vs all BLAST stored two alignments of ``S`` and ``T`` into ``msa``.
  What this highlights is that BLAST is not a true multiple sequence alignment
  algorithm (among other things, it is not symmetric: you can get different
  mappings in one direction vs. the other).
  
  In general, bidirectional storage
  mainly makes sense for true multiple sequence alignments (which are guaranteed
  to be symmetric).
  
* Supplying the :class:`BlastMapping` with an alignment object makes it store
  its results into that alignment, rather than creating its own alignment holder
  for us.  In this way we can make it store many different BLAST searches into
  a single alignment database.

* Supplying the ``queryDB`` argument allows you to run multiple queries at
  once; ``queryDB`` is expected to be a dictionary whose values are the 
  sequence objects you wish to use as queries to the :class:`BlastMapping`.
  
* To make the NLMSA algorithm scalable, pygr defers construction of the alignment
  indexes until the alignment is complete.  We trigger this by calling its build()
  method.  At this point we now have an alignment database stored on disk, which
  we can open at any time later and query with the high-speed nested list algorithm
  as illustrated in the examples in previous sections.
  



Building an Alignment Database from MAF files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
It may be helpful to see how a large multi-genome alignment database
is created in Pygr.  It is quite straightforward.
UCSC has defined a new file format for large multigenome alignment,
called MAF.  Pygr provides high-performance utilities for reading
MAF alignment files and building a disk-based NLMSA alignment database.
(These utilities are written in C for performance).  Here's an
example of building an alignment database from scratch using a
set of MAF files stored in a directory called ``maf/``::

   import os
   from pygr import cnestedlist,seqdb

   genomes = {'hg17':'hg17','mm5':'mm5', 'rn3':'rn3', 'canFam1':'cf1',
              'danRer1':'dr1', 'fr1':'fr1','galGal2':'gg2', 'panTro1':'pt1'}
   for k,v in genomes.items(): # PREFIX DICTIONARY FOR UNION OF GENOMES
       genomes[k] = seqdb.SequenceFileDB(v) # USE v AS FILENAME FOR FASTA FILE
   genomeUnion=seqdb.PrefixUnionDict(genomes) # CREATE UNION OF THESE DBs
   # CREATE NLMSA DATABASE ucsc8 ON DISK, FROM MAF FILES IN maf/
   msa = cnestedlist.NLMSA('ucsc8','w',genomeUnion,os.listdir('maf'))
   msa.build(saveSeqDict=True) # BUILD & SAVE ALIGNMENT + SEQUENCE INDEXES


The only real work here is due to the fact that UCSC's MAF files
use a *prefix.suffix* notation for identifying specific sequences,
where *prefix* gives the name of the genome, and *suffix*
gives the identifier of the sequence in that genome database.
Here we use Pygr's :class:`PrefixUnionDict` class to wrap the
set of genome databases in a dict-like interface that accepts
string keys of the form *prefix.suffix* and returns the
right sequence object from the right genome database.  As an
added twist, the genome names in the MAF files match the
filenames of the associated genome databases in most cases, but
not all, so we have to create an initial dictionary giving the
correct mapping.  Actually building the NLMSA requires just one
line, but actually a number of steps are happening behind the
scenes:

* If you have never opened :class:`SequenceFileDB` objects for these genome
  databases before, :class:`SequenceFileDB` will initialize each one.  This means
  two things.  First, it builds an index of all the sequences and their
  lengths.  This is essential for combining the
  large numbers of sequences in these databases into
  "unified" coordinate systems in the NLMSA (otherwise there would
  have to be a separate database file for each individual sequence).
  Second, it saves the sequences to a simple indexed file format that
  allows Pygr to retrieve individual sequence fragments quickly and
  efficiently.  We got tired of NCBI ``fastacmd``'s horrible
  memory requirements and slow speed, so we implemented fast sequence
  indexing.
  
* :class:`NLMSA` reads each MAF file and divides the interval
  alignment data into one or more coordinate systems created
  on-the-fly (for efficient memory usage, NLMSA uses :class:`int`
  coordinates (32-bit), which has a maximum size of approximately
  2 billion.  This is too small even for a single genome like human;
  :class:`NLMSA` automatically splits the database into as many
  coordinate systems are needed to represent the alignment.
  Each coordinate system has its own database file on disk.
  
* After it has finished reading the MAF data, :class:`NLMSA`
  begins to build the database indexes for each coordinate
  system.  Computationally, this operation is equivalent to
  a *sort* (N log N complexity).  Once the indexes are built, the database is
  ready for use.


Example: Mapping an entire gene set onto a new genome version
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To illustrate how Pygr can perform a big task with a little code, here is an example that maps a set of gene sequences onto a new version of the genome, using megablast to do the mapping, and a relational database to store the results.  Moreover, since mapping 80,000 gene clusters takes a fair amount of time, the calculation is parallelized to run over a large number of compute nodes simultaneously::

   from pygr import worldbase
   from pygr.apps.leelabdb import * # this accesses our databases
   from pygr import coordinator     # this provides parallelization support

   def map_clusters(server,dbname='HUMAN_SPLICE_03',
                    result_table='GENOME_ALIGNMENT.hg17_cluster_JUN03_all',
                    rmOpts=",**kwargs):
       "CLIENT FUNCTION: map clusters one by one"
       # construct resource for us if needed
       genome = worldbase.Bio.Seq.Genome.HUMAN.hg17()
       # load db schema
       (clusters,exons,splices,genomic_seq,spliceGraph,alt5Graph,alt3Graph,mrna,
       protein, clusterExons,clusterSplices) = getSpliceGraphFromDB(spliceCalcs[dbname])
       # now map cluster sequences one by one to our new genome
       for cluster_id in server:
           g = genomic_seq[cluster_id] # get the old genomic sequence for this cluster
           m = genome.megablast(g,maxseq=1,minIdentity=98,rmOpts=rmOpts) # mask, blast, read into m
           # save alignment m to database table result_table using cursor
           createTableFromRepr(m.repr_dict(),result_table,clusters.cursor,
                               {'src_id':'varchar(12)','dest_id':'varchar(12)'})
           yield cluster_id # we must function as generator to keep error trapping
   		         # HAPPY

   def serve_clusters(dbname='HUMAN_SPLICE_03',
                      source_table='HUMAN_SPLICE_03.genomic_cluster_JUN03',**kwargs):
       "SERVER FUNCTION: serve up cluster_id one by one to as many clients as you want"
       cursor = getUserCursor(dbname)
       t = SQLTable(source_table,cursor)
       for id in t:
           yield id # HAND OUT ONE CLUSTER ID TO A CLIENT

   if __name__=='__main__': # AUTOMATICALLY RUN EITHER THE CLIENT OR SERVER FUNCTION
       coordinator.start_client_or_server(map_clusters,serve_clusters,[],__file__)


First, let's just focus on the map_clusters() function, which illustrates how the mapping of each gene is generated and saved.  Let's examine the data piece by piece:

  
* genome: a BLAST database storing our hg17 genome sequence
  
* genomic_seq: another sequence database (which in this case happens to be stored in a relational database), mapping each cluster ID to a piece of the old genomic sequence version containing that specific gene.
  
* cluster_id: a cluster ID for us to process.
  
* g: the actual sequence object associated with this cluster_id
  
* m: the mapping of g onto genome, as generated by megablast after first running RepeatMasker on g, using the RepeatMasker options passed as rmOpts.  Note that only the top hit will be saved (maximum number of hits to save maxseq=1), and only if it has at least 98\% identity.  This alignment is then saved to a relational database table using createTableFromRepr().
  

This code will run in parallel over as many compute nodes as you have free, using Pygr's coordinator module.  The parallelization model for this particular task is simple: a single iterator (server) dispensing task IDs to many clients.


  
* server: the serve_clusters() function is trivial: all it does is connect to a specific database table (source_table) and iterate over all its primary keys, yielding them one by one.
  
* client: the map_clusters() function expects an iterator as its first argument, which must give it a sequence of task IDs (cluster_id in this script).  This iterator is actually using an XMLRPC request to the server to get the next task ID, but that is done transparently by the coordinator.Processor() class.  The map_clusters() function is modeled as a generator: that is, it first does some initial setup (loading the database schema for example), then it runs its actual task loop, yielding each completed task ID. This enables coordinator.Processor to run map_clusters() within an error-trapping try: except: clause that catches and reports all errors to the central coordinator.Coordinator instance, and also to implement some intelligent error handling policies (like robustly preventing rare individual errors from causing an entire Processor() to crash, but detecting when consistent patterns of errors occur on a particular Processor, and automatically shutting down that Processor.
  
* start_client_or_server(): this line automatically starts up the correct function (depending on whether this process is running as client or server).  To make a long story short, all you have to do is run the script once (as a server), and it will automatically start clients for you on free compute nodes (using ssh-agent), with reasonable load-balancing and queuing policies.  For details, see the coordinator module docs.


