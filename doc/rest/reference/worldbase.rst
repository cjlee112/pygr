:mod:`worldbase` --- A virtual namespace for data
=================================================

.. module:: worldbase
   :synopsis: A virtual namespace for data
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>

This module provides a simple but powerful interface for creating
a "data namespace" in which users can access complex datasets
by simply requesting the name chosen for a given dataset -- much
like Python's ``import`` mechanism enables users to access
a specified code resource by name, without worrying about where it
should be found or how to assemble its many parts.  For an introduction,
see the `worldbase tutorial <../tutorials/worldbase.html>`_.

This functionality has two different sides:

* the :mod:`metabase` module contains the classes and code.
  We use the term "metabase" (i.e. "a metadata database") to refer to
  a container for storing
  *metadata* describing various datasets (which are typically stored in
  other databases).  By "metadata" we mean information about the *content*
  of a particular dataset (this is what allows ``worldbase`` to reload it
  automatically for the user, without the user having to know what classes
  to import or how to construct the object correctly), and about its
  *relations* with other datasets (dependencies, cross-references).

* the importable object ``worldbase`` provides the default interface
  for a virtual namespace for scientific data.  ``worldbase`` acts as
  an interface to whatever list of metabases you defined via the
  environment variable ``WORLDBASEPATH``.  "worldbase" connotes the
  idea of using "the whole world as your database", in the form of a virtual
  namespace containing the world's scientific data.

We will use the term "worldbase" to refer to the virtual namespace for
scientific data, and the term "metabase" to refer to the generic concept
of a "metadata database" as defined above.

Note: you import ``worldbase`` like this::
   from pygr import worldbase

You cannot ``import pygr.worldbase`` because it is a Python object,
not a module.


What kinds of data can be saved in worldbase?
---------------------------------------------
There are a few basic principles you should be aware of:

* The object should be a database (container) or mapping (graph),
  not an individual item of data.  worldbase is intended to provide
  a name space for commonly used resources, i.e. an entire database,
  which in turn enable you to access the items they contain.
  
* The object must have a :attr:`__doc__` string that describes
  what its contents are.
  
* The object must be *picklable* using Python's :mod:`pickle`
  module.  worldbase uses :mod:`pickle` both to save your object to
  a persistent storage (either a python :mod:`shelve`, MySQL database,
  or XMLRPC server), and to analyze its *dependencies* on other
  Python objects.  The default pickling procedure (save a dictionary of
  your object's attributes) works fine for simple Python classes.
  However, if your class accesses external data (i.e. data not actually
  stored in its attributes), you will have to define :meth:`__getstate__`
  and :meth:`__setstate__` methods that save and restore just the
  relevant information for it to be able to access the information
  it needs (e.g. if your class reads a file, :meth:`__getstate__` must
  save its filename).  If your class inherits from :class:`dict`, you
  will also have to define a :meth:`__reduce__` method.  See
  the :mod:`pickle` module documentation.
  
* worldbase provides a *namespace* for commonly used data resources.
  Once you import worldbase, you can save resources into it just as you would into
  any python namespace.  For example to save an alignment object ``nlmsa``
  as the resource ID "Bio.MSA.UCSC.foo17"::
  
     from pygr import worldbase # MODULE PROVIDES ACCESS TO OUR DATA NAMESPACE
     worldbase.Bio.MSA.UCSC.foo17 = nlmsa # NOW SAVE THE ALIGNMENT
     worldbase.commit() # SAVE ALL PENDING DATA TO THE METABASE
  
  The crucial point is that this namespace is *persistent* between
  Python interpreter sessions.  The metadata for re-loading objects
  in the namespace are stored in *metabases* either on your disk, in
  a remote XMLRPC server, or in a MySQL database (for details see below).
  
* If an object saved to worldbase depends on a given file,
  you should use an absolute path to that file, instead of a relative path,
  when originally constructing that object, prior to adding it to
  worldbase.  Relative paths are obviously inadequate for future users of
  worldbase to find the file, since they are likely to be working in
  a different "current directory".
  
* For similar obvious reasons, you should ensure that such a
  "dependency file" has security settings that make it readable
  to the set of users that you want to be able to access this worldbase
  resource in the future.  Users who lack privileges to be able to
  read that file will be unable to access this specific worldbase resource.
  
* To get a named resource from worldbase, you again just use this
  namespace, but with a "constructor syntax", i.e. add a call at the end of
  the resource name::
  
     from pygr import worldbase # MODULE PROVIDES ACCESS TO OUR DATA NAMESPACE
     nlmsa = worldbase.Bio.MSA.UCSC.foo17() # SYNTAX EMPHASIZES CONSTRUCTION OF INSTANCE
  
  The actual resource object is not obtained until you call the constructor.
  
* worldbase also stores *schema information* for the resources.
  These represent relationships between one resource and another resource
  (or their contents).  For example::
  
     worldbase.schema.Bio.Annotation.ASAP2.hg17.splicegraph = \
       metabase.ManyToManyRelation(exons,exons,splices, # ADD ITS SCHEMA RELATIONS
                                    bindAttrs=('next','previous','exons'))
  
  indicates that the worldbase resource ``Bio.Annotation.ASAP2.hg17.splicegraph``
  is a many-to-many mapping of the worldbase resource *exons* onto itself,
  with additional "edge information" for each exon-to-exon mapping
  provided by the worldbase resource *splices*.  Furthermore, this mapping
  is to be bound directly to items of *exons* (i.e. objects returned
  from ``exons.__getitem__``) as their :attr:`next` attribute (giving the
  forward mapping), their :attr:`previous` attribute (giving the reverse
  mapping), and the :attr:`exons` attribute on items of *splices*
  (giving the mapping of the splice object to its pair of (source,target) exons
  as a tuple).
  
* when a user requests a resource that itself depends on other
  resources, worldbase automatically loads them.  Thus users do not need
  to know about the complex set of dependencies between data; all they
  have to do ask is ask for the specific data resource they want,
  and worldbase will take care of all the details behind the scenes.
  For example, a database of exon annotations is not very useful without
  also loading the genomic sequence database that these annotations
  refer to.  Using worldbase, we can simply load the exon annotation
  resource, and it will automatically get the genomic sequence data
  for us.  Thus to get an exon's sequence all we have to do is::
  
     exons = worldbase.Bio.Annotation.ASAP2.hg17.exons() # ANNOTATION DATABASE
     str(exons[464].sequence) # GET THE SEQUENCE OF THIS SPECIFIC EXON
  
  


worldbase is transactional
--------------------------

worldbase follows a *transactional* model: new resources
added to worldbase are not saved to the metabase until you
call ``worldbase.commit()``.  This has several benefits:


* Because of the transactional model,
  within a single transaction, the *order* in which you
  add resources to worldbase does not matter.  This is a crucial data
  integrity requirement.  In a non-transactional model (where each
  resource is saved the instant it is added), adding resources in the
  wrong order will break data integrity.  Specifically,
  if object *B* depends on object *A*,
  but you saved *B* before *A*, then
  *B* will not be aware of *A*'s resource ID (i.e. it has no way of
  knowing that you plan on assigning *A* a resource ID some time
  in the future).  This would break a crucial data integrity guarantee,
  namely that if two objects *B* and *C* refer to the same
  object *A* at the time they are saved, it is guaranteed that
  when restored in the future they will still refer to the identical
  Python object.  To provide this guarantee in a way that is
  persistent across Python interpreter sessions, worldbase must
  store object references in terms of their unique worldbase IDs.
  This is only possible if the object has been assigned a worldbase
  ID (by having added it to worldbase in the usual way) before
  you complete the transaction by calling ``worldbase.commit()``.
  
* This also enables worldbase to provide a limited form of
  *rollback*, i.e. the ability to cancel an entire set of
  resource additions at any time before they are committed.
  You can do this by calling ``worldbase.rollback()``.
  
* How do you decide what set of data forms a single transaction?
  This follows a very simple rule: if an object *A* that you are adding
  to worldbase depends on (i.e. *refers
  to*) some other object *B* that you also
  intend to add to worldbase, then *B* must either *already* have a worldbase ID,
  or *B* must also be added to worldbase in the same transaction.
  
* If you add resources to worldbase, you *must* call ``worldbase.commit()``
  before your Python interpreter session exits.  Otherwise the transaction would
  be left incomplete and would not be saved to the worldbase metabase.
  


worldbase Namespace Conventions
-------------------------------
At this point, we're still just making this up as we go along.
However, it is clearly advantageous to adopt some simple conventions
that make it easy for people to use the same name for a given data resource,
and to find what they're looking for.  We are adopting the following conventions:

* The general pattern is *Area.Category.Database.release*.  For example,
  Swissprot release 42 is "Bio.Seq.Swissprot.sp42".  This is a very straightforward
  pattern to follow for well-known databases.
* In other cases, the dataset is not strictly speaking a well-known database,
  but is instead an "instance of a larger class of data".  For example, genome
  sequences.  In this case we follow the general pattern
  *Area.Category.Class.Instance.release*.  For example, the human genome draft
  17 is "Bio.Seq.Genome.HUMAN.hg17".
* To identify specific genomes, we use the Uniprot / Swissprot
  controlled vocabulary for species names, e.g. "HUMAN" for human.  For more
  information, see the Swissprot website
  \url{http://www.expasy.org/cgi-bin/speclist}.
*  Often a database may itself contain many different resources.  These
  individual resource names are simply appended to the worldbase name, for example,
  the ASAP database contains a resource called ``exons``.  This would be
  accessed as "Bio.Genomics.ASAP.asap2.exons".  This pattern can be extended,
  for as many layers are required to specify a unique resource in the database.
* In cases where the original data provider does not assign a release name,
  we use the approximate release date as the release name (chosen appropriately
  for the release frequency of the database).  e.g. "jan06".
* Capitalization: we capitalize Area, Category, Database, Class and Instance
  names.  Release names are chosen to match the name used by the original data
  provider, which are usually not capitalized.

Existing Area categories:

* Bio.Seq: currently, the main category in worldbase is sequence databases.
* Bio.MSA: Another major category is multiple sequence alignments (e.g. genome alignments).
  For example: "Bio.MSA.UCSC.hg18_multiz28way".
* Bio.Annotation: category representing annotation information bound
  to sequence intervals.
* Bio.Expression: category representing gene expression analysis,
  including microarray data.

You may obtain a directory of available resources available using
the ``worldbase.dir``() function::

   >>> worldbase.dir('Bio.Seq.Swiss')
   ['Bio.Seq.Swissprot.sp42']

This returns the list of items beginning with the string
you provided.  Use its ``asDict=True`` argument to make it return a dictionary
of matches with detailed information such as their docstring descriptions.

We suggest that you follow these conventions and extend them as needed.
Please report new category names to us so we can add them to the list.

How does worldbase access metabases?
---------------------------------------------
The list of metabases is read from the environment variable
PYGRDATAPATH.  If this variable is empty or missing, the default path
for worldbase to search is the user's home directory (\$HOME) and
current directory, in that order.  PYGRDATAPATH should be a comma separated list
of "resource path" strings, which must be one of the following:

* A directory path (e.g. /usr/local/pygrdata), in which worldbase should
  look for (or, if none present, create) a database file called ".pygr_data".
  You can use the tilde character to indicate your home directory path.
  These are accessed by worldbase using its :class:`metabase.ShelveMetabase` class.
  
* a URL for accessing an XMLRPC server that is serving a worldbase
  metabase index (previously started by you or someone else).
  The URL must begin with "http://".
  These are accessed by worldbase using its :class:`metabase.XMLRPCMetabase` class.
  
* a MySQL server, indicated by a path entry of the form
  "mysql:*DBNAME.TABLENAME* *dbinfo*",
  where *DBNAME* is the name of the database in your MySQL
  server that contains the worldbase resource index,
  and *TABLENAME* is the name of the table which contains this index.
  *dbinfo* is optional.  If provided, it must be a whitespace separated
  list of arguments for connecting to the MySQL server, of the form
  *host* *user* *passwd*.  You can provide one, two
  or three of these optional arguments, always beginning with *host*.
  If no *dbinfo* is provided,
  worldbase will get the host, user, and password information for connecting
  to the MySQL server as usual from your
  .my.cnf configuration file in your home directory.
  Such metabases are accessed by worldbase using its
  :class:`metabase.MySQLMetabase` class.


download=True Mode
------------------
When requesting a worldbase resource name, you can specify
the optional argument *download=True*, which forces worldbase
to search for a resource that can be downloaded to your local
filesystem (instead of accessed via XMLRPC from a remote server).

* If you already have a local copy of the resource, that will be used.
  
* If no local copy of the resource exists, and a downloadable
  resource is found, it will be automatically downloaded and initialized
  for you.  The result of the resource request will be the fully
  initialized local copy of the resource, ready for use.  Of course,
  downloading a very large dataset may take a long time, but
  the download and processing is completely automatic.
  
* If the downloaded resource itself depends on other
  resources that you do not have local copies of, they will also
  be requested using the download=True mode, and so on, until
  all resource dependencies are satisfied.  In this way, worldbase
  can automatically obtain for you the complete set of local
  resources needed to work with a multi-genome alignment, for example::
  
     nlmsa = worldbase.Bio.MSA.UCSC.dm2_multiz9way(download=True)
  
  
* After a resource has been successfully downloaded and
  initialized, it will be automatically saved to
  the first writeable metabase in your
  WORLDBASEPATH) for future usage.  Future requests for this
  resource do not need to specify download=True, because the
  resource is now recorded in your local metabase
  as being available locally.
  
* To see what downloadable resources are available, pass the
  download=True option to worldbase.dir().  Note: currently, this
  also lists resources that you have available locally.
  
* A downloadable resource can be any URL that returns
  a dataset usable in Pygr as a data resource.  Examples:
  a FASTA sequence dataset (accessed in Pygr as a BlastDB);
  an NLMSA textdump file (loaded in Pygr as an NLMSA using the
  textdump_to_binaries() function).  The URL can be anything
  that can be downloaded using the Python :mod:`urllib`
  module.
  
* worldbase searches its metabases for records
  of downloadable resources matching the requested name.
  Currently, only XMLRPC metabase servers will return
  lists of downloadable resources.  Note that the resource
  database does not store the resource, and the resource will not
  be directly downloaded from the metabase.  Instead,
  the metabase simply stores a record indicating the location
  (URL) for downloading the resource, and how to initialize it
  automatically on your local computer.
  


Adding Downloadable Resources to worldbase
------------------------------------------
Only a few steps are required to add a downloadable resource
to worldbase.  The main difference is that instead of saving an
actual resource, you are merely saving a pointer to download /
initialize the resource, which will only be invoked when a user
requests that the resource be downloaded to their local computer.

* First, you need the URL for downloading a data file that
  Pygr could use as a resource.  Obvious examples include a FASTA
  sequence database, or an NLMSA textdump.  Compressed or archived
  data files are supported (for details, see the :mod:`downloader`
  module documentation).
  
* Next, create a :class:`downloader.SourceURL` object with the desired URL::
  
     from pygr.downloader import SourceURL
     dfile = SourceURL('http://biodb.bioinformatics.ucla.edu/PYGRDATA/dm2_multiz9way.txt.gz')
  
  Note that this represents just a file, not an actual resource usable
  in Pygr.  This is the difference between a textdump file, and a
  Pygr NLMSA object built from that textdump.
  
* Just save the SourceURL to a local metabase
  (i.e. shelve storage) in the usual way::
  
     dfile.__doc__ = 'DM2 based nine genome alignment from UCSC in textfile  dump format'
     worldbase.Bio.MSA.UCSC.dm2_multiz9way.txt = dfile
  
  Note that we added the suffix ".txt" to the usual resource name, because
  this is just a textdump file instead of the actual resource that can be
  used in Pygr.  Strictly speaking there is no need to save the textfile
  directly to worldbase, but this improves modularity (e.g. there might
  be multiple URLs from which we could download the same resource text file).
  
* Finally, we create a rule for initializing the actual resource
  object (in this case, NLMSA) from the downloaded text.  As an example,
  the :class:`nlmsa_utils.NLMSABuilder` class saves the appropriate rule for
  initializing an NLMSA from a text file::
  
     from pygr.nlmsa_utils import NLMSABuilder
     nbuilder = NLMSABuilder(dfile)
     nbuilder.__doc__ = 'DM2 based nine genome alignment from UCSC'
     worldbase.Bio.MSA.UCSC.dm2_multiz9way = nbuilder
     worldbase.commit()
  
  Note that we saved this as the actual resource representing the
  dm2_multiz9way alignment, because that is what it will return
  when unpickled by worldbase.
  
  Here is another example, for downloading and initializing a
  FASTA sequence database::
  
     src = SourceURL('ftp://hgdownload.cse.ucsc.edu/goldenPath/droVir3/bigZips/droVir3.fa.gz')
     src.__doc__ = 'D. virilis Genome (February 2006) FASTA file'
     worldbase.Bio.Seq.Genome.DROVI.droVir3.fasta = src
     from pygr.downloader import GenericBuilder
     rsrc = GenericBuilder('BlastDB', src)
     rsrc.__doc__ = 'D. virilis Genome (February 2006)'
     worldbase.Bio.Seq.Genome.DROVI.droVir3 = rsrc
     worldbase.commit()
  
  Note that we used the :class:`GenericBuilder` class, which acts as proxy
  for the class we want to use for building the resource (:class:`BlastDB`).
  At this moment we do not actually want to make a BlastDB, we simply
  want to save a rule for making a BlastDB when the user actually
  requests that this resource be downloaded.
  Upon unpickling by worldbase, :class:`GenericBuilder`
  simply calls its target class with the exact list of arguments /
  keyword arguments it originally received.  When *src* is
  unpickled by worldbase, it will be transformed into the local
  filename where the FASTA file was downloaded to (after automatic gunzipping).
  Since :class:`BlastDB` just expects a filename as its first argument,
  we provide *src* as the only additional argument to :class:`GenericBuilder`.
  Note that you specify the target class as a string; GenericBuilder
  matches this against its list of accepted classes, to avoid creating
  a security hole wide enough to drive a truck through!
  
* Setting up an XMLRPC server to serve the downloadable
  resources you saved to your worldbase shelve database is easy.
  When you create the server object, just pass the optional
  *downloadDB* argument as follows.  It should give
  the path to your shelve file containing this metabase::
  
     from pygr import worldbase
     nlmsa = worldbase.Bio.MSA.UCSC.hg17_multiz17way() # data to serve: NLMSA AND SEQ DBs
     server = worldbase.getResource.newServer('nlmsa_server',
                       downloadDB='/your/path/to/the/shelve/.pygr_data',
                       withIndex=True)
     server.serve_forever() # START THE SERVICE...
  
  You can also directly call the server method :meth:`read_download_db`(path)
  to read a list of downloadable resources from a shelve specified by
  the *path*.  Resources from the new file will be added to
  the current list of downloadable resources.
  Note however that the server object currently can only store one
  download rule for a given resource name, so a duplicate rule for
  a resource name already in its downloadDB index will overwrite the
  previously existing rule.
  



Convenience functions
---------------------

.. function:: __call__(resID, debug=None, download=None, *args, **kwargs)

   Retrieve the resource specified by *resID*.

   *debug=True* will force it to raise any exception that occurs during
   the search.  By default it ignores exceptions and continues the search
   to subsequent metabases.

   *download=True* will restrict the search to downloadable resources,
   and will download and install the resource (and its dependencies) if
   it / they are not already installed locally.  If a resource is available
   locally, it will simply be used as-is.  If a resource is downloaded, it
   will also be saved to the first writeable (local) metabase for future use.

.. function:: add_resource(resID, obj=None)

   Add *obj* as resource ID *resID* to this metabase or metabase list.

   If *obj* is None, the first argument must be a dictionary of 
   resID:obj pairs, which will all be added to the metabase / list.

   For a resource *id* 'A.Foo.Bar'
   this function is equivalent to the assignment statement::

      worldbase.A.Foo.Bar = obj

   This function is provided mainly to enable writing code that automates
   saving of resources, e.g. via code like::

      for id,genome in nlmsa.seqDict.prefixDict.items(): # 1st SAVE THE GENOMES
      genome.__doc__ = 'draft genome sequence '+id
      worldbase.add_esource('Bio.Seq.Genome.'+id,genome)



.. function:: delete_resource(id,layer=None)

   Delete resource *id* from the metabase specified by
   *layer* if provided (or the default metabase otherwise).
   Also delete its associated schema information.


.. function:: commit(layer=None)

   Saves all pending worldbase additions to the metabase.
   If *layer* is not specified, each resource will be saved to the
   layer it was added to, or to the default layer if none was specified
   at the time of addition.  If *layer* is not None, it forces all
   pending data to be saved specifically to that layer.  You can call
   ``worldbase.commit()`` multiple times with different *layer*
   values to make the same set of data (transaction) be saved to each
   of the specified metabases.


.. function:: rollback()

   Dumps all pending worldbase additions (since the last ``save()``
   or ``rollback()``) without adding them to the metabase.


.. function:: list_pending()

   Returns a pair of two lists ([*data*],[*schema*]), where
   the first list shows newly added worldbase IDs that are currently pending,
   and the second list worldbase IDs that with newly added schema information
   pending.


.. function:: add_schema(name,schemaObj,layer=None)

   Add a schema object for the worldbase resource indicated by the
   string passed as *name*, to the specified *layer* if provided
   (or the default metabase otherwise).  For example::

      addSchema('Bio.Genomics.ASAP2.hg17.geneExons',
      metabase.OneToManyRelation(genes,exons,bindAttrs=('exons','gene')))
      worldbase.commit() # SAVE ALL PENDING DATA AND SCHEMA TO METABASE


Note that schema information, like pending data, is not saved to
the metabase until you call ``worldbase.commit()``.

.. function:: update(newpath)

``worldbase`` also provides a directory function for searching
for resource names that begin with a given stem, either in all
databases, or in a specific layer:

.. function:: dir(prefix,layer=None,asDict=False)

   get list or dict of resources beginning with the specified string.
   If the optional *asDict* argument is True, then they are returned
   as a dictionary whose keys are resource names, and whose values are their
   descriptions (taken from the resource object's :attr:`__doc__` string).
   Otherwise they are returned as a list.


