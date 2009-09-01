Simplifying the Challenges of Working with Complex Datasets
-----------------------------------------------------------

worldbase: a Namespace for Transparently Importing Data
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
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

download=True Mode
^^^^^^^^^^^^^^^^^^
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

