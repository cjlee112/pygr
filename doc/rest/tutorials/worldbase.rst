
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

* :mod:`worldbase` first checked your local resource lists to see
  if this resource was available locally.  Failing that, it obtained
  the resource from the remote server, which basically tells it
  how to download the data.

* :mod:`worldbase` unpickled the ``Bio.Seq.Genome.YEAST.sacCer1``
  :class:`seqdb.SequenceFileDB` object,
  which in turn requested the ``Bio.Seq.Genome.YEAST.sacCer1.fasta``
  text file (again with ``download=True``).

* this is a general principle.  If you request a resource with
  ``download=True``, and it in turn depends on other resources,
  they will also be requested with ``download=True``.  I.e. 
  they will each either be obtained locally, or downloaded
  automatically.  So if you requested the 44 genome alignment
  dataset, this could result in up to 45 downloads (the alignment
  itself plus the 44 genome sequence datasets).

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
for working with data on disk.  

So now when you request this resource 
from worldbase, it will connect you to your local copy stored on disk!


Controlling Where Worldbase Searches and Saves Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the last section, you may have wondered what we meant by 
"your local worldbase indexes".  After all, you didn't do anything
to tell worldbase where you store data.  :mod:`worldbase` checks the
environment variable ``WORLDBASEPATH`` for a list of locations
to search; but if it's not set, worldbase defaults to the following
path::

   ~,.,http://biodb2.bioinformatics.ucla.edu:5000

which specifies three locations to be searched (in order)

* your home directory;

* your current directory;

* the UCLA public XMLRPC server.

In each location, worldbase looks for a "metabase", which is a 
*metadata database* storing information about datasets that it knows
how to access.  This is an important point: worldbase is *not* intended
to be a database in which you actually store data.  Instead it is only
intended to store *metadata* about data that is stored elsewhere
(in disk files; in SQL databases; in network servers, etc.).
Broadly speaking these metadata for each resource include

* what kind of data it is;

* how to access it;

* its relations with other data (schema and dependencies).

You can set your WORLDBASEPATH in your shell environment,
or you can tell worldbase directly what path you want it to use,
by calling its :meth:`worldbase.update()` method.  For example,
to restrict it to searching the metabase in your current directory::

   >>> worldbase.update('.')

Now if we ask for a resource that is not in that metabase, we'll
get an error::

   >>> msa = worldbase.Bio.MSA.UCSC.hg18_multiz44way()
   Traceback (most recent call last):  
     File "<stdin>", line 1, in <module>  
     File "/Users/leec/projects/pygr/pygr/metabase.py", line 1201, in __call__
       return self._mdb(self._path, *args, **kwargs)
     File "/Users/leec/projects/pygr/pygr/metabase.py", line 647, in __call__
       for objdata,docstr in self.find_resource(resID, download):
     File "/Users/leec/projects/pygr/pygr/metabase.py", line 877, in find_resource
       raise WorldbaseNotFoundError('unable to find %s in WORLDBASEPATH' % resID)
   pygr.metabase.WorldbaseNotFoundError: 'unable to find Bio.MSA.UCSC.hg18_multiz44way in WORLDBASEPATH'

In general,
if you place your local metabases before remote resource
servers in your WORLDBASEPATH, ``download=True`` will always default to
any local resource that you already have, rather than downloading
a new copy.

``download=True`` uses two additional environment variables that
specify where you want downloaded data to be saved:

* ``WORLDBASEDOWNLOAD``: the directory that files will be download into;

* ``WORLDBASEBUILDDIR``: that directory in which index files will be
  constructed, when large downloaded datasets are initialized.  Currently,
  this is used by :class:`cnestedlist.NLMSA`.

A Warning about Security
^^^^^^^^^^^^^^^^^^^^^^^^

Worldbase uses Python's standard mechanism for saving and retrieving
data, called **pickling**.  Strictly speaking,
Python pickling is not secure.  In particular, you should not unpickle
data provided by someone else unless you trust the data not to contain
attempted security exploits.  Because Python unpickling has access to ``import``,
it theoretically has the potential to access system calls 
and possibly execute malicious code on your
computer.  Python has made efforts to plug known security holes
in the unpickling process; for example, unpickling will refuse to
call any function that has not been specifically marked as 
safe for unpickling (i.e. that it has no potential for executing
commands supplied by the pickle data).
But it should not be considered secure.

Future versions of Pygr will build in a foundation of digital
signatures and networks-of-trust (based on GPG) so that for every pickle
it is possible to verify who produced it and that no changes have
been introduced since they signed it.

For the moment we advise that you not point your ``WORLDBASEPATH``
at sources that you do not have a good reason to trust.

