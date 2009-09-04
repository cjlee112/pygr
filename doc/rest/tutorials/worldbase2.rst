
=======================================
Saving Datasets and Schema in Worldbase
=======================================

Purpose
^^^^^^^

This tutorial teaches you how to add your own datasets to worldbase,
using either on-disk indexes or a MySQL database.  You should first
understand how to retrieve data from worldbase (see :doc:`worldbase`).
Setting up an XMLRPC worldbase server is covered in a separate
tutorial (see :doc:`xmlrpc`).


Saving a Dataset into Worldbase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:mod:`worldbase` saves not just a data file but a complete Python interface
to a dataset, i.e. the capability to *use* and mine the data in whatever
ways are possible programmatically.  One way of thinking about worldbase
is that retrieving data from it is like returning to the moment in time
when those data were originally saved to worldbase.  Anything you could
do with the original data, you can do with the retrieved data.

There are only a few requirements:

* you have your dataset loaded in Python as an object.  When retrieved
  from worldbase, this dataset will be usable by the exact same interface
  as the original object.

* your object must be **picklable**.  Worldbase can store any object
  that is compatible with standard Python pickling methods.
  Thus, worldbase is not restricted to Pygr data -- but most Pygr classes
  are of course designed to be stored in worldbase.

* your object must have a docstring, i.e. a ``__doc__`` attribute.  
  This should give a simple
  explanatory description so people can understand what this dataset is.

For example, say we want to add the
hg17 (release 17 of the human genome sequence) as "Bio.Seq.Genome.HUMAN.hg17"
(the choice of name is arbitrary, but it's best to choose a good convention and follow
it consistently)::

   from pygr import seqdb
   from pygr import worldbase # module provides access to our data namespace
   hg17 = seqdb.SequenceFileDB('hg17') # human genome sequence
   hg17.__doc__ = 'human genome sequence draft 17' # required!
   worldbase.Bio.Seq.Genome.HUMAN.hg17 = hg17 # save as this name
   worldbase.commit() # save all pending data to the metabase

Note that you *must* call the function :func:`worldbase.commit()` to
complete the transaction and save all pending data resources
(i.e. all those added since your last :func:`worldbase.commit()` or
:func:`worldbase.rollback()`).  In particular, if you have added
data to worldbase during a given Python interpreter session, you
should always call :func:`worldbase.commit()` or
:func:`worldbase.rollback()` prior to exiting from that session.

In any subsequent Python session, we can now access it directly by its
worldbase name::

   from pygr import worldbase # module provides access to our data namespace
   hg17 = worldbase.Bio.Seq.Genome.HUMAN.hg17() # find the resource

This example illustrates some key points about :mod:`worldbase`:

* The call syntax (``hg17()``) emphasizes that this acts like a Python
  constructor: it constructs a Python object for us (in this case, the
  desired :class:`seqdb.SequenceFileDB` object representing this genome database).

* Note that we did *not* even have to know how to construct the hg17
  object, e.g. what Python class to use 
  (:class:`seqdb.SequenceFileDB`), or even to import
  the necessary modules for constructing it.  

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

* :mod:`worldbase` is designed to work with any back-end database that stores
  **actual data**.  Typical Pygr back-end databases
  for storing data include MySQL, sqlite, Python shelve (using
  :class:`mapping.Collection`), on-disk indexes
  (e.g. for alignments, :class:`cnestedlist.NLMSA`; for sequences,
  :class:`seqdb.SequenceFileDB`), etc., but you can use anything you want --
  you just need to make the database object picklable (using standard
  Python methods).

Saving a Dataset with Dependencies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

What if you wanted to save a dataset that in turn requires many other 
datasets?  For example, a multigenome alignment dataset is only useful if you 
also have the genome datasets that it aligns.  
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
scenes) involves accessing 17 :class:`seqdb.SequenceFileDB` 
sequence databases (one for each
of the genomes in the alignment).  Because the alignment object (NLMSA)
references the 17 :class:`seqdb.SequenceFileDB` databases, 
worldbase automatically saves information
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

Notice that we saved all these resources in a *single* commit.  This
way, we avoid potentially subtle issues about the *order* in which
we saved the resources.  What would happen if we commit the 
NLMSA alignment before adding any of the genomes to worldbase?
This would be exactly like our first case above, in which the genomes
were simply saved as file paths, rather than as worldbase IDs.

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

Saving SQL Server Information to Worldbase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For datasets whose back-end storage is in a SQL server, you need
to supply a mechanism for connecting automatically to that server,
so worldbase can re-establish the database
connection when the object is unpickled.  
For example, say we wanted to save the UCSC ``knownGeneMrna`` 
interface that we created in :doc:`sequence`.
We created these objects in two separate steps: first the
server information; second the mRNA table::

   >>> serverInfo = sqlgraph.DBServerInfo(host='genome-mysql.cse.ucsc.edu',
   ...                                    user='genome')
   >>> mrna = sqlgraph.SQLTable('hg18.knownGeneMrna', serverInfo=serverInfo, 
   ...                          itemClass=UCSCmRNA,
   ...                          itemSliceClass=seqdb.SeqDBSlice)

Now we can save both of these to worldbase::

   >>> serverInfo.__doc__ = 'MySQL server with UCSC genome annotations'
   >>> worldbase.Bio.MSA.UCSC.genome_mysql = serverInfo
   >>> mrna.__doc__ = 'hg18.knownGeneMrna sequence database'
   >>> worldbase.Bio.MSA.UCSC.hg18.knownGeneMrna = mrna
   >>> worldbase.commit()
   
Note that even if we hadn't explicitly saved ``serverInfo`` to worldbase,
it still would have been saved in the second step (as a dependency of ``mrna``).
Retrieving ``Bio.MSA.UCSC.hg18.knownGeneMrna`` would still have worked,
because it would have stored the ``serverInfo`` as part of its dependencies.
In that case, the ``serverInfo`` just wouldn't have been assigned a worldbase ID.


So why is it valuable to assign ``serverInfo`` a worldbase ID?
Assigning it a standard ID creates a layer of dereference between
resources that depend on that ID, and the actual server.  For example,
UCSC provides all of its mysql data for download, so a lab could set up
its own MySQL server containing the same data.  In their local worldbase,
they could save a pointer to their local MySQL server as
``Bio.MSA.UCSC.genome_mysql``, and all worldbase resources that
depend on ``Bio.MSA.UCSC.genome_mysql`` would automatically use their
local server instead of UCSC's.  Furthermore, they could create new resources
that use their local server, and save them to worldbase, yet
those resources would still work for other people who don't have
their own local server -- in their case ``Bio.MSA.UCSC.genome_mysql``
would point back to the standard UCSC MySQL server.

:class:`sqlgraph.DBServerInfo` provides other advantages:

* it will automatically try to obtain authentication information from
  your ~/.my.cnf config file.


Saving Data to a Specific Location
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:mod:`worldbase` is a collection of one or more metabases representing
different zones of access -- typically one metabase belonging to
the user, representing his/her personal data; another metabase
in a system-wide location, representing data stored on this system
and available to all its users; and a remote metabase representing resources
available from the Internet.

Ordinarily, :mod:`worldbase` saves data to the *first writable metabase*
in your ``WORLDBASEPATH``.  What if you want to specify explicitly
where to save your data?  To do this, you can open an interface to a
single metabase directly::

   >>> from pygr import metabase
   >>> mdb = metabase.Metabase('.')

This opens the metabase in your current directory.  Now we can write
to it either using its ``Data`` attribute (which provides a 
worldbase-like interface), or directly use its 
:meth:`metabase.Metabase.add_resource()` method::

   >>> mdb.Data.Bio.MSA.UCSC.hg18.knownGeneMrna = mrna

or::

   >>> mdb.add_resource('Bio.MSA.UCSC.hg18.knownGeneMrna', mrna)

and finally commit in the usual way::

   >>> mdb.commit()

Where Can You Store Metabases?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pygr currently support three types of :class:`metabase.Metabase`:

* a Python shelve file stored on-disk: :class:`metabase.ShelveMetabase`

* a MySQL database table: :class:`metabase.MySQLMetabase`: this is used
  for any metabase path that begins with "mysql:".

* an XMLRPC server: :class:`metabase.MetabaseServer`: this is used
  for any metabase path that begins with "http:".


Pickling: The Fine Print
^^^^^^^^^^^^^^^^^^^^^^^^

Since :mod:`worldbase` 
uses Python pickling to save data, you should understand a few basic aspects
of pickling.

* Pickling an object saves its class information (basically its module name
  and class name, so that the class can be automatically imported to unpickle the
  object).  If ``import`` cannot locate the specified module name, unpickling
  will fail.  Make sure your classes are located in modules that will
  be found under the same consistent name on any machine where you want
  the data to be retrievable.

* Pickling normally saves a dictionary of "attributes" that represent
  the object's *state*.  If an object has dependencies on other data,
  they will normally be included in these "state attributes".  E.g.
  for a multigenome alignment, its state includes a dictionary of its
  genomes.

* Pickling an object simply proceeds recursively to pickle its state
  attributes.  So dependencies are automatically included.

* The best situation is when a dependency itself has a worldbase ID.
  In this case, worldbase simply saves that ID (not the data) in the
  pickle state.  Unpickling this ID will simply request it from worldbase.
  That means when someone else retrieves your data,
  the dependency could be filled by local data on their computer
  (since worldbase generally searches local data first).
