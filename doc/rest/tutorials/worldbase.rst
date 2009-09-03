
==========================================
Accessing Complex Datasets Using Worldbase
==========================================

Purpose
^^^^^^^

This tutorial teaches you how to access complex datasets
like whole genomes and multigenome alignments, either from local
files or Internet servers, using :mod:`worldbase`.  
No previous knowledge of Pygr is required, although the end products of
some of the examples (accessing sequences or alignments) may be 
easier to understand if you're familiar with Pygr sequences and
alignments (see :doc:`sequence`; :doc:`alignment`).


worldbase: a Namespace for Transparently Importing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Say you want to work with human genome draft 18.  Start Python and
type the following::

   >>> from pygr import worldbase
   >>> hg18 = worldbase.Bio.Seq.Genome.HUMAN.hg18()

That's it: you now have the human genome dataset, and can start working.
Let's see how many contigs it contains, pull out one chromosome,
print a sequence interval of interest, etc.::

   >>> len(hg18)
   49
   >>> chr1 = hg18['chr1']
   >>> len(chr1)
   247249719
   >>> ival = chr1[20000000:20000500]
   >>> print ival
   cctcggcctcccaaagtgctgggattacaggcgtgagccaccgcgcagccccaactagactttaaaagccctggaggtgggcgggtttaggctgccttgctctccgctgtgtgcccagccccagggactgtgcctagcacttgcaggtgctcaaaagaagcacttaatgaatggatctctttcccctagcaaccctgtgaaatttcatcacacccactctgaaggagaggaaaccgaggctcaggtccagacaatgcagaagccacagagctaatgagtgccagagctagggcatgaatcatcgtggcctcagaagctgttgcccttaCTCCCAGTGAAGACAATCTAGGGTTATGGGAGGAAAAGGTACCGACGGGGGTCAGAGACCAGCATCCCAGCTCAGAGCCTGGGACTCACGCACCTGTGAAATGTTCCTTCCTTCATCTGCTCATCTCCCCACTGGCCAATCAGGACCAAGAAGGGCAGCTCtacccacccat

:mod:`worldbase` establishes a one-step model for accessing data:
*ask for it by name*:

* :mod:`worldbase` is an importable namespace for all the world's
  scientific datasets.  You simply *import* the namespace (in the usual
  Python way), and
  ask it to *construct* an instance of the dataset that you want
  (in the usual Python way).

* Of course, this is a *virtual* namespace -- you don't actually have
  all the world's datasets sitting on your computer in a file called 
  ``worldbase.py``!  :mod:`worldbase` connects to a wide variety of 
  data sources (some of which may be on your computer, and some which
  may be on the Internet) to find out the set of available resources,
  and then serves them to you.

* :mod:`worldbase` takes advantage of Pygr's scalable design.
  Pygr is first and foremost a *a system of representation* not tied to
  any fixed assumptions about storage (i.e. ``chr1`` represents human
  chromosome 1, but does not necessarily mean that the human chromosome
  1 sequence (245 Mb) was loaded into a Python object).
  Thus it can work very naturally with huge datasets, even over
  a network connection where the actual data is stored on a remote
  server.  In this case, :mod:`worldbase` is accessing hg18 from 
  UCLA's data server, which is included by default in :mod:`worldbase`
  searches (of course, you can change that).

* To get a dataset, all you need to know is its *name* in :mod:`worldbase`.
  Note that we did not even have to know what code is required to
  work with that data, let alone explicitly import those modules.
  :mod:`worldbase` takes care of that for you.

Searching Worldbase
^^^^^^^^^^^^^^^^^^^

Python 2.6 introduced a method for customizing the results of the
built-in ``dir()`` function.  Try this out in Python 2.6::

   >>> from pygr import worldbase
   >>> dir(worldbase)
   ['0root', 'Bio', 'Test', '__doc__']
   >>> dir(worldbase.Bio)
   ['MSA', 'Seq']
   >>> dir(worldbase.Bio.Seq)
   ['Genome']
   >>> dir(worldbase.Bio.Seq.Genome)
   ['ANOCA', 'ANOGA', 'APIME', 'BOVIN', 'BRAFL', 'CAEBR', 'CAEEL', 'CAEJA', 'CAEPB', 'CAERE', 'CALJA', 'CANFA', 'CAVPO', 'CHICK', 'CHOHO', 'CIOIN', 'DANRE', 'DASNO', 'DIPOR', 'DROAN', 'DROER', 'DROGR', 'DROME', 'DROMO', 'DROPE', 'DROPS', 'DROSE', 'DROSI', 'DROVI', 'DROWI', 'DROYA', 'ECHTE', 'ERIEU', 'FELCA', 'FUGRU', 'GASAC', 'GORGO', 'HORSE', 'HUMAN', 'LAMPA', 'LOXAF', 'MACMU', 'MICMU', 'MONDO', 'MOUSE', 'MYOLU', 'OCHPR', 'ORNAN', 'ORYLA', 'OTOGA', 'PANTR', 'PETMA', 'PONAB', 'PONPA', 'PRIPA', 'PROCA', 'PTEVA', 'RABIT', 'RAT', 'SORAR', 'SPETR', 'STRPU', 'TAEGU', 'TARSY', 'TETNG', 'TRICA', 'TUPGB', 'TURTR', 'XENTR', 'YEAST']
   >>> dir(worldbase.Bio.Seq.Genome.MOUSE)
   ['mm5', 'mm6', 'mm7', 'mm8', 'mm9']

If we want to get more details, :func:`worldbase.dir()` lets us request
a dictionary of info for each result::

   >>> worldbase.dir('Bio.Seq.Genome.MOUSE', asDict=True)
   {'Bio.Seq.Genome.MOUSE.mm9': {'pickle_size': 186, 'creation_time': <DateTime '20090903T13:07:57' at 7b30f8>, 'user': 'deepreds', '__doc__': 'Mouse Genome (July 2007)'}, 'Bio.Seq.Genome.MOUSE.mm8': {'pickle_size': 186, 'creation_time': <DateTime '20090903T13:07:57' at 7b30d0>, 'user': 'deepreds', '__doc__': 'Mouse Genome (March 2006)'}, 'Bio.Seq.Genome.MOUSE.mm5': {'pickle_size': 186, 'creation_time': <DateTime '20090903T13:07:57' at 7b3120>, 'user': 'deepreds', '__doc__': 'Mouse Genome (May 2004)'}, 'Bio.Seq.Genome.MOUSE.mm7': {'pickle_size': 186, 'creation_time': <DateTime '20090903T13:07:57' at 7b3198>, 'user': 'deepreds', '__doc__': 'Mouse Genome (August 2005)'}, 'Bio.Seq.Genome.MOUSE.mm6': {'pickle_size': 186, 'creation_time': <DateTime '20090903T13:07:57' at 7b3210>, 'user': 'deepreds', '__doc__': 'Mouse Genome (March 2005)'}}

We can also use this to do regular expression searches::

   >>> worldbase.dir('MOUSE', matchType='r')
   ['Bio.Seq.Genome.MOUSE.mm5', 'Bio.Seq.Genome.MOUSE.mm6', 'Bio.Seq.Genome.MOUSE.mm7', 'Bio.Seq.Genome.MOUSE.mm8', 'Bio.Seq.Genome.MOUSE.mm9']
   >>> worldbase.dir('Gor', matchType='r')
   ['Bio.MSA.UCSC.hg19_pairwiseGorGor1', 'Bio.Seq.Genome.GORGO.gorGor1']
   >>> worldbase.dir('[Rr][Aa][Tt]', matchType='r')
   ['Bio.Seq.Genome.RAT.rn3', 'Bio.Seq.Genome.RAT.rn4']
   >>> worldbase.dir('hg[0-9]+', matchType='r')
   ['Bio.MSA.UCSC.hg17ToHg18', 'Bio.MSA.UCSC.hg17_multiz17way', 'Bio.MSA.UCSC.hg18ToHg17', 'Bio.MSA.UCSC.hg18_multiz17way', 'Bio.MSA.UCSC.hg18_multiz28way', 'Bio.MSA.UCSC.hg18_multiz44way', 'Bio.MSA.UCSC.hg18_pairwiseAnoCar1', 'Bio.MSA.UCSC.hg18_pairwiseBosTau2', 'Bio.MSA.UCSC.hg18_pairwiseBosTau3', 'Bio.MSA.UCSC.hg18_pairwiseBosTau4', 'Bio.MSA.UCSC.hg18_pairwiseBraFlo1', 'Bio.MSA.UCSC.hg18_pairwiseCalJac1', 'Bio.MSA.UCSC.hg18_pairwiseCanFam2', 'Bio.MSA.UCSC.hg18_pairwiseCavPor3', 'Bio.MSA.UCSC.hg18_pairwiseDanRer3', 'Bio.MSA.UCSC.hg18_pairwiseDanRer4', 'Bio.MSA.UCSC.hg18_pairwiseDanRer5', 'Bio.MSA.UCSC.hg18_pairwiseEquCab1', 'Bio.MSA.UCSC.hg18_pairwiseFelCat3', 'Bio.MSA.UCSC.hg18_pairwiseFr1', 'Bio.MSA.UCSC.hg18_pairwiseFr2', 'Bio.MSA.UCSC.hg18_pairwiseGalGal2', 'Bio.MSA.UCSC.hg18_pairwiseGalGal3', 'Bio.MSA.UCSC.hg18_pairwiseGasAcu1', 'Bio.MSA.UCSC.hg18_pairwiseMm7', 'Bio.MSA.UCSC.hg18_pairwiseMm8', 'Bio.MSA.UCSC.hg18_pairwiseMm9', 'Bio.MSA.UCSC.hg18_pairwiseMonDom4', 'Bio.MSA.UCSC.hg18_pairwiseOrnAna1', 'Bio.MSA.UCSC.hg18_pairwiseOryCun1', 'Bio.MSA.UCSC.hg18_pairwiseOryLat1', 'Bio.MSA.UCSC.hg18_pairwiseOryLat2', 'Bio.MSA.UCSC.hg18_pairwisePanTro1', 'Bio.MSA.UCSC.hg18_pairwisePanTro2', 'Bio.MSA.UCSC.hg18_pairwisePetMar1', 'Bio.MSA.UCSC.hg18_pairwisePonAbe2', 'Bio.MSA.UCSC.hg18_pairwiseRheMac2', 'Bio.MSA.UCSC.hg18_pairwiseRn4', 'Bio.MSA.UCSC.hg18_pairwiseSelf', 'Bio.MSA.UCSC.hg18_pairwiseSorAra1', 'Bio.MSA.UCSC.hg18_pairwiseStrPur2', 'Bio.MSA.UCSC.hg18_pairwiseTaeGut1', 'Bio.MSA.UCSC.hg18_pairwiseTetNig1', 'Bio.MSA.UCSC.hg18_pairwiseXenTro1', 'Bio.MSA.UCSC.hg18_pairwiseXenTro2', 'Bio.MSA.UCSC.hg19_pairwiseCalJac1', 'Bio.MSA.UCSC.hg19_pairwiseGorGor1', 'Bio.MSA.UCSC.hg19_pairwiseMicMur1', 'Bio.MSA.UCSC.hg19_pairwiseOtoGar1', 'Bio.MSA.UCSC.hg19_pairwisePanTro2', 'Bio.MSA.UCSC.hg19_pairwisePonAbe2', 'Bio.MSA.UCSC.hg19_pairwiseRheMac2', 'Bio.MSA.UCSC.hg19_pairwiseTarSyr1', 'Bio.Seq.Genome.HUMAN.hg17', 'Bio.Seq.Genome.HUMAN.hg18', 'Bio.Seq.Genome.HUMAN.hg19']

Resource Dependencies
^^^^^^^^^^^^^^^^^^^^^

What if the dataset you want to use in turn depends on many other 
datasets?  For example, let's get a multigenome alignment that
maps the human genome to many other genomes::

   >>> worldbase.dir('hg[0-9]+_multi', matchType='r')
   ['Bio.MSA.UCSC.hg17_multiz17way', 'Bio.MSA.UCSC.hg18_multiz17way', 'Bio.MSA.UCSC.hg18_multiz28way', 'Bio.MSA.UCSC.hg18_multiz44way']

Let's get the big alignment of 44 vertebrate genomes::

   >>> msa = worldbase.Bio.MSA.UCSC.hg18_multiz44way()

Not surprisingly, being able to use this dataset depends on also having
the 44 different genome sequence datasets.  A Pygr multiple sequence
alignment object generally stores a dictionary of its sequences as its
``seqDict`` attribute.  Knowing that this dictionary must be a composite
of 44 different genomes, each with a separate prefix in the UCSC alignment,
we can take a peek inside::

   >>> msa.seqDict.prefixDict.keys()
   ['petMar1', 'mm9', 'gorGor1', 'cavPor3', 'eriEur1', 'pteVam1', 'panTro2', 'anoCar1', 'micMur1', 'galGal3', 'proCap1', 'ponAbe2', 'loxAfr2', 'rn4', 'oryLat2', 'vicPac1', 'danRer5', 'canFam2', 'dipOrd1', 'echTel1', 'sorAra1', 'tetNig1', 'equCab2', 'bosTau4', 'ochPri2', 'myoLuc1', 'oryCun1', 'rheMac2', 'turTru1', 'xenTro2', 'speTri1', 'otoGar1', 'dasNov2', 'choHof1', 'taeGut1', 'calJac1', 'tarSyr1', 'ornAna1', 'tupBel1', 'fr2', 'gasAcu1', 'hg18', 'felCat3', 'monDom4']

Yup, there are 44 genomes in there.  We could grab one by its prefix::

   >>> turTru1 = msa.seqDict.prefixDict['turTru1']
   >>> len(turTru1)
   116467

Or we could just access individual sequences using UCSC's prefix notation::

   >>> chr1 = msa.seqDict['mm9.chr1']
   >>> len(chr1)
   197195432
   >>> len(chr1.db)
   35

(Notice that first-draft genomes tend to have huge numbers of contigs,
whereas genomes that have been through many drafts have far fewer).
Let's query the alignment with a piece of mouse chromosome 1::

   >>> ival = chr1[9098000:9099000]

Let's get a mapping that for any sequence will give us its ID
prefixed with the genome name (in the usual UCSC style)::

   >>> idDict = ~(msa.seqDict)

Finally, the actual query, printed in a trivial format::

   >>> for src,dest,e in msa[ival].edges():
   ...    print src, repr(src), '\n', dest, idDict[dest], '\n'
   ...
   CTAAACTA chr1[9098273:9098281] 
   CTGAAATT dasNov2.scaffold_203475 
   
   TCGGAGCTAAACTA chr1[9098267:9098281] 
   AGGAAGCTATTCCT calJac1.Contig7152 
   
   TCGGAGCTAAACTA chr1[9098267:9098281] 
   AGTCAACTAATCTT canFam2.chr29 
   
   TCGGAGCTAAACTA chr1[9098267:9098281] 
   AGGAGGCTATTCTT otoGar1.scaffold_81178.1-424864 
   
   TCGGAGCTAAACTA chr1[9098267:9098281] 
   AAATGGCTATTCGT pteVam1.scaffold_7567 
   (more results truncated)

Hopefully at this point you're convinced that we've got access to 
all of the data from the 44 genomes.  This is a general principle 
in :mod:`worldbase`: asking for one dataset automatically brings along
other data that it requires.  You don't have to do anything special
to make this happen; it just works.


Downloading datasets locally using download=True
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

What if you want to make :mod:`worldbase` download the data locally,
so that you could perform heavy-duty analysis on them?  The examples
above all accessed the data via a client-server (XMLRPC) connection,
without downloading all the data to our computer.  But if you want
the data downloaded to your computer, all you have to do is add
the flag ``download=True``.  First, let's see if the yeast genome
is available for download::

   >>> worldbase.dir('YEAST', matchType='r', download=True)
   ['Bio.Seq.Genome.YEAST.sacCer1', 'Bio.Seq.Genome.YEAST.sacCer1.fasta', '__doc__.Bio.Seq.Genome.YEAST.sacCer1', '__doc__.Bio.Seq.Genome.YEAST.sacCer1.fasta']

The first entry is the one we want -- it represents an interface to
the genome.  It will both invoke downloading of the .fasta file
(the next item in the list), and then install it as a Pygr
:class:`seqdb.SequenceFileDB`.  Let's get it::

   >>> yeast = worldbase.Bio.Seq.Genome.YEAST.sacCer1(download=True)
   INFO downloader.download_unpickler: Beginning download of http://biodb.bioinformatics.ucla.edu/GENOMES/sacCer1/chromFa.zip to /Users/leec/projects/pygr/tests/sacCer1.zip...
   INFO downloader.download_monitor: downloaded 385024 bytes (10.2%)...
   INFO downloader.download_monitor: downloaded 770048 bytes (20.3%)...
   INFO downloader.download_monitor: downloaded 1155072 bytes (30.5%)...
   INFO downloader.download_monitor: downloaded 1540096 bytes (40.7%)...
   INFO downloader.download_monitor: downloaded 1925120 bytes (50.9%)...
   INFO downloader.download_monitor: downloaded 2310144 bytes (61.0%)...
   INFO downloader.download_monitor: downloaded 2695168 bytes (71.2%)...
   INFO downloader.download_monitor: downloaded 3080192 bytes (81.4%)...
   INFO downloader.download_monitor: downloaded 3465216 bytes (91.6%)...
   INFO downloader.download_unpickler: Download done.
   INFO downloader.uncompress_file: unzipping /Users/leec/projects/pygr/tests/sacCer1.zip...
   DEBUG seqdb._create_seqLenDict: Building sequence length index...

We can start using it right away::
   >>> len(yeast)
   17
   >>> yeast.keys()
   ['chr1', 'chr10', 'chr11', 'chr12', 'chr13', 'chr14', 'chr15', 'chr16', 'chr2', 'chr3', 'chr4', 'chr5', 'chr6', 'chr7', 'chr8', 'chr9', 'chrM']
   >>> len(yeast['chr1'])
   230208

What just happened?

* :mod:`worldbase` unpickled the ``Bio.Seq.Genome.YEAST.sacCer1``
  :class:`seqdb.SequenceFileDB` object,
  which in turn requested the ``Bio.Seq.Genome.YEAST.sacCer1.fasta``
  text file (again with ``download=True``).

* the compressed file was downloaded and unzipped.

* the :class:`seqdb.SequenceFileDB` object initialized itself,
  building its indexes on disk.

* :mod:`worldbase` then saved this local resource to your local
  worldbase index (on disk), so that when you request this resource
  in the future, it will simply use the local resource instead
  of either accessing it over a network (the slow client-server model)
  or downloading it over again.

Let's test that claim.  First, we clear all records from our Python interpreter's
worldbase cache.  That will force any new requests to loaded from
scratch (as if we had started a new Python interpreter session).
Then we can request the yeast genome over again and see what happens::

   >>> worldbase.clear_cache()
   >>> yeast = worldbase.Bio.Seq.Genome.YEAST.sacCer1(download=True)
   >>> len(yeast)
   17

Notice that we got the yeast genome instantly, without any downloading.
``download=True`` mode first checks for the resource in your local
worldbase indexes.  If you already have the resource as a local resource
(on your disk), it just uses that, instead of downloading it again.

Let's check that our database is truly a local storage, and not an
XMLRPC client::

   >>> repr(yeast)
   "<BlastDB '/Users/leec/projects/pygr/tests/sacCer1'>"

Yup.  ``BlastDB`` is an older Pygr variant of :class:`seqdb.SequenceFileDB`,
for working with data on disk.  So now when you request this resource 
from worldbase, it will connect you to your local copy stored on disk!

Older material still to be revised
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:mod:`worldbase` provides powerful automation for allowing you to have
both the convenience of obtaining resources automatically from
remote servers, but also the performance of local resources
stored on your computer(s).  If you specify the optional
*download=True* argument, worldbase will try to find a
server that will allow download of the entire dataset, and
will then download and initialize the resource for you --
completely automatically::

   nlmsa = worldbase.Bio.MSA.UCSC.dm2_multiz9way(download=True)

The location in which downloads and constructed index files
will be stored is controlled by environment variables
PYGRDATADOWNLOAD and PYGRDATABUILDDIR.  If these variables are
not set, data files are simply stored in current directory.

If the resource you requested with ``download=True`` has resource
dependencies, they will also be downloaded and built automatically,
if you do not already have a local copy of a given resource.  In general,
if you place your local metabases before remote resource
servers in your WORLDBASEPATH, ``download=True`` will always default to
any local resource that you already have, rather than downloading
a new copy of it.



One challenge in bioinformatics is the complexity of managing many diverse
data resources.  For example, running a large job on a heterogeneous cluster
of computers is complicated by the fact that individual computers often can't
access a given data resource in the same way (i.e. the file path may be different),
and some machines may not have direct access at all to certain resources.

Pygr provides a systematic solution to this problem: creating a consistent
namespace for data.  A given resource is given a unique name that then becomes
its universal handle for accessing it, no matter where you are (just as Python's
``import`` command provides a consistent name for accessing a given code
resource, regardless of where you are).  For example, say we want to add the
hg17 (release 17 of the human genome sequence) as "Bio.Seq.Genome.HUMAN.hg17"
(the choice of name is arbitrary, but it's best to choose a good convention and follow
it consistently)::

   from pygr import seqdb
   from pygr import worldbase # module provides access to our data namespace
   hg17 = seqdb.SequenceFileDB('hg17') # human genome sequence
   hg17.__doc__ = 'human genome sequence draft 17' # required!
   worldbase.Bio.Seq.Genome.HUMAN.hg17 = hg17 # save as this name
   worldbase.commit() # save all pending data to the metabase

Note that you *must* call the function ``worldbase.commit()`` to
complete the transaction and save all pending data resources
(i.e. all those added since your last ``worldbase.commit()`` or
``worldbase.rollback()``).  In particular, if you have added
data to worldbase during a given Python interpreter session, you
should always call ``worldbase.commit()`` or
``worldbase.rollback()`` prior to exiting from that session.

In any subsequent Python session, we can now access it directly by its
worldbase name::

   from pygr import worldbase # module provides access to our data namespace
   hg17 = worldbase.Bio.Seq.Genome.HUMAN.hg17() # find the resource

This example illustrates some key points about :mod:`worldbase`:

* The call syntax (``hg17()``) emphasizes that this acts like a Python
  constructor: it constructs a Python object for us (in this case, the
  desired seqdb.SequenceFileDB object representing this genome database).

* Note that we did *not* even have to know how to construct the hg17
  object, e.g. what Python class to use (seqdb.SequenceFileDB), or even to import
  the necessary modules for constructing it.  

worldbase Sharing Over a Network via XMLRPC
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Sometimes individual compute nodes may not have sufficient disk space to
store all the data resources (for example, just the single UCSC hg17 17-genome alignment and
associated genome databases takes about 200 GB).  Yet it would be useful
to run compute-intensive analyses on those machines accessing such data.
worldbase makes that easy.  The default setting of WORLDBASEPATH (if you
do not set it yourself) is::

   ~,.,http://biodb2.bioinformatics.ucla.edu:5000

respectively your HOME directory, current directory, and the XMLRPC
server provided at UCLA as a service to pygr users.  Thus you can
simply from pygr import worldbase and start accessing data.  Try this::

   >>> from pygr import worldbase
   >>> worldbase.dir('Bio')
   ['Bio.MSA.UCSC.canFam2_multiz4way',...]
   >>> msa = worldbase.Bio.MSA.UCSC.hg17_multiz17way()
   >>> chr1 = msa.seqDict['hg17.chr1']
   >>> ival = chr1[4000:4400]
   >>> myslice = msa[ival]
   >>> for s1,s2,e in myslice.edges():
   ...     print '%s\n%s\n' %(s1,s2)
   ...
   AAGGGCCA
   AAGGGCCA

This provides a convenient way to begin trying out pygr and working
with comparative genomics data, but clearly is not efficient for analysis
of large amounts of data, which must be transmitted to you by the server
via XMLRPC, since potentially many users must share the access to the
biodb2.bioinformatics.ucla.edu server.

Understanding worldbase
^^^^^^^^^^^^^^^^^^^^^^^
How does worldbase work?

* :mod:`worldbase` uses the
  power of Python pickling to figure out automatically what to import.
  Anything that Python can pickle, :mod:`worldbase` can save.

* You should think of :mod:`worldbase` not as a conventional *database*
  (a container for storing a large set of a specific kind of data)
  but rather as a *metadata database*, i.e. a container for storing
  *metadata* describing various datasets (which are typically stored in
  other databases).  By "metadata" we mean information about the *content*
  of a particular dataset (this is what allows :mod:`worldbase` to reload it
  automatically for the user, without the user having to know what classes
  to import or how to construct the object correctly), and about its
  *relations* with other datasets (dependencies, cross-references; for 
  details, see the section on ``worldbase.schema`` below).

* Throughout, we will use the term "metabase" to refer to this concept of
  a "metadata database".
  Whereas a *database* actually stores an entire dataset, a *metabase*
  merely stores a small amount of metadata pointing to that database
  and describing its relations with other datasets.

* :mod:`worldbase` is a collection of one or more metabases representing
  different zones of access -- typically one metabase belonging to
  the user, representing his/her personal data; another metabase
  in a system-wide location, representing data stored on this system
  and available to all its users; and a remote metabase representing resources
  available from the Internet.

* :mod:`worldbase` is designed to work with any back-end database that stores
  actual data, and with a variety of ways of storing metabases.  Typical
  pygr back-end databases include MySQL, sqlite, Python shelve, pygr
  NLMSA, pygr SequenceFileDB, etc., but you can use anything you want --
  you just need to make the database object picklable (using standard
  Python methods).  Currently, metabases can be stored in Python shelve,
  MySQL, or a remote XMLRPC service.

* Where are metabases actually retrieved from?  :mod:`worldbase` looks at
  the environment variable ``WORLDBASEPATH`` to get a list
  of local and remote metabases in which to look up any resource name
  that you try to load.  For example, in the shell you might set::

   setenv WORLDBASEPATH ~,.,/usr/local/pygr,mysql:PYGRDATA.index,http://leelab.mbi.ucla.edu:5000

  This is a comma-separated string (since colon ':' appears inside URLs).
  In this case it tells worldbase to look for metabases (in order):
  ``\$HOME/.pygr_data``; ``./.pygr_data``; ``/usr/local/pygr/.pygr_data``;
  the MySQL table PYGRDATA.index (using your
  MySQL .my.cnf file to determine the MySQL host and authentication);
  and the XMLRPC server running on leelab.mbi.ucla.edu on port 5000.

Saving Data Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^
:mod:`worldbase` is smart about figuring out data resource dependencies.
For example, you could just save a 17-genome alignment in a single step
as follows::

   from pygr import cnestedlist
   from pygr import worldbase # module provides access to our data namespace
   nlmsa = cnestedlist.NLMSA('/loaner/ucsc17')
   nlmsa.__doc__ = 'UCSC 17way multiz alignment, rooted on hg17'
   worldbase.Bio.MSA.UCSC.hg17_multiz17way = nlmsa
   worldbase.commit() # save all pending data to the metabase

This works, even though using this 17-genome alignment (behind the
scenes) involves accessing 17 SequenceFileDB sequence databases (one for each
of the genomes in the alignment).  Because the alignment object (NLMSA)
references the 17 SequenceFileDB databases, worldbase automatically saves information
about how to access them too.

However, it would be a lot smarter to give those databases worldbase resource
names too.  Let's do that::

   from pygr import cnestedlist
   from pygr import worldbase # module provides access to our data namespace
   nlmsa = cnestedlist.NLMSA('/loaner/ucsc17')
   for resID,genome in nlmsa.seqDict.prefixDict.items(): # 1st save the genomes
       genome.__doc__ = 'genome sequence ' + resID
       worldbase.add_resource('Bio.Seq.Genome.' + resID, genome)
   nlmsa.__doc__ = 'UCSC 17way multiz alignment, rooted on hg17'
   worldbase.MSA.Bio.UCSC.hg17_multiz17way = nlmsa # now save the alignment
   worldbase.commit() # save all pending data to the metabase


This has several advantages.  First, we can now access other genome databases
using worldbase too::

   from pygr import worldbase # module provides access to our data namespace
   mm7 = worldbase.Bio.Seq.Genome.mm7() # get the mouse genome

But more importantly, when we try to load the ucsc17 alignment on
another machine, if the genome databases are not in the same directory
as on our original machine, the first method above would fail, whereas in
the second approach worldbase now will automatically scan all its metabases to
figure out how to load each of the genomes on that machine.

NOTE: Python pickling is not secure.  In particular, you should not unpickle
data provided by someone else unless you trust the data not to contain
attempted security exploits.  Because Python unpickling has access to ``import``,
it has the potential to access system calls and execute malicious code on your
computer.

worldbase.schema: a Simple Framework For Managing Database Schemas
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
*Schema* refers to any relationship between two or more collections of
data.  It captures the structure of relationships that define these particular
kinds of data.  For example "a genome has genes, and genes have exons", or
"an exon is connected to another exon by a splice".  In worldbase we can
store such schema information as easily as::

   splicegraph.__doc__ = 'graph of exon:splice:exon relations in human genes'
   worldbase.Bio.Genomics.ASAP2.hg17.splicegraph = splicegraph # add a new resource
   from pygr.metabase import ManyToManyRelation
   worldbase.schema.Bio.Genomics.ASAP2.hg17.splicegraph = \
      ManyToManyRelation(exons, exons, splices, # add its schema relations
                         bindAttrs=('next', 'previous', 'exons'))
   worldbase.commit() # save all pending data to the metabase

This example assumes that

* ``splicegraph`` is a graph whose nodes are exons, and whose
  edges are splices connecting a pair of exons.  Specifically,
  ``splicegraph[exon1][exon2]=splice1`` means ``splice1`` is a
  splice object (from the container ``splices``) that connects
  ``exon1`` and ``exon2`` (both from the container ``exons``).
  
* An exon can have one or more "outgoing" splices connecting it
  to subsequent exons, as well as one or more "incoming" splices from
  previous exons.  Thus this relation of exon to exon is a Many-to-Many
  mapping (e.g. as distinguished from a One-to-One mapping, where each
  exon must have exactly one such relationship with another exon).
  
* Because worldbase now knows the schema for splicegraph, it
  will automatically reconstruct these relationships for any user who
  accesses these data from worldbase.  Specifically, if a user
  retrieves ``worldbase.Bio.Genomics.ASAP2.hg17.splicegraph``,
  the ``sourceDB``, ``targetDB``, ``edgeDB`` attributes on
  the returned object will automatically be set to point to the
  corresponding worldbase resources representing ``exons`` and ``splices``
  respectively.  ``splicegraph`` does not need to do anything to
  remember these relationships; worldbase.schema remembers and applies
  this information for you automatically.  Note that when you access
  ``splicegraph``, neither ``exons`` nor ``splices`` will be
  actually loaded unless you do something that specifically tries to
  read these data (e.g. ``for exon in splicegraph`` will read
  ``exons`` but not ``splices``).
  
* The easiest way for users to work with a schema is to translate
  it into object-oriented behavior.  I.e. instead of remembering that
  when we have ``exons`` we can use ``splicegraph`` to find its
  ``splices`` via code like::
  
     for exon,splice in splicegraph[exon0].items():
        do something...
  
  most people would find it easier to remember that every ``exon``
  has a ``next`` attribute that gives its splices to subsequent exons
  via code like::
  
     for exon,splice in exon0.next.items():
        do something...
  
  Based on the schema statement we gave it,
  worldbase.schema will automatically create the attributes ``next``,
  ``previous`` on any exon item from the container ``exons``,
  according to the schema.  I.e. ``exon.next`` will be equivalent to
  ``splicegraph[exon]``.  Note that as long as the object ``exon0``
  came from the worldbase resource, the user *would not have to do anything*
  to be able to use the ``next`` attribute.  On the basis of the saved
  schema information, worldbase will construct this attribute automatically,
  and will automatically load the resources ``splicegraph`` and ``splices``
  if the user tries to actually use the ``next`` attribute.

Creating your own worldbase XMLRPC server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To setup your own XMLRPC client-server using worldbase,
first create an XMLRPC server on a machine that
has access to the data::

   from pygr import worldbase
   nlmsa = worldbase.Bio.MSA.UCSC.hg17_multiz17way() # get our NLMSA and seq DBs
   from pygr.metabase import ResourceServer
   server = ResourceServer(worldbase._mdb, 'nlmsa_server') # serve all loaded data
   server.register() # tell worldbase index server what resources we're serving
   server.serve_forever() # start the service...


This example code looks for a worldbase XMLRPC server in your WORLDBASEPATH,
and registers our resources to that index.  Now any machine that can access
your servers can access the alignment as easily as::

   from pygr import worldbase
   nlmsa = worldbase.Bio.MSA.UCSC.hg17_multiz17way() # GET THE NLMSA AND SEQ DBs

Alignment queries and sequence strings will be obtained via XMLRPC
queries over the network.  Note that if any of the sequence databases
*are* available locally (on this machine), Pygr will automatically use that
in preference to obtaining it over the network (based on your WORLDBASEPATH
settings).  However, if a particular resource is not available locally,
Pygr will transparently get access to it from the server we created,
using XMLRPC.

