:mod:`metabase` --- Easy data sharing and access
=============================================

.. module:: metabase
   :synopsis: Easy data sharing and access
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>

This module provides a simple but powerful interface for creating
a "data namespace" in which users can access complex datasets
by simply requesting the name chosen for a given dataset -- much
like Python's ``import`` mechanism enables users to access
a specified code resource by name, without worrying about where it
should be found or how to assemble its many parts.  For an introduction,
see the pygr.Data tutorial.

What kinds of data can be saved in pygr.Data?
---------------------------------------------
There are a few basic principles you should be aware of:

* The object should be a database (container) or mapping (graph),
  not an individual item of data.  pygr.Data is intended to provide
  a name space for commonly used resources, i.e. an entire database,
  which in turn enable you to access the items they contain.
  
* The object must have a :attr:`__doc__` string that describes
  what its contents are.
  
* The object must be *picklable* using Python's :mod:`pickle`
  module.  pygr.Data uses :mod:`pickle` both to save your object to
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
  
* pygr.Data provides a *namespace* for commonly used data resources.
  Once you import pygr.Data, you can save resources into it just as you would into
  any python namespace.  For example to save an alignment object ``nlmsa``
  as the resource ID "Bio.MSA.UCSC.foo17"::
  
     import pygr.Data # MODULE PROVIDES ACCESS TO OUR DATA NAMESPACE
     pygr.Data.Bio.MSA.UCSC.foo17 = nlmsa # NOW SAVE THE ALIGNMENT
     pygr.Data.save() # SAVE ALL PENDING DATA TO THE RESOURCE DATABASE
  
  The crucial point is that this namespace is *persistent* between
  Python interpreter sessions.  The actual data is not saved in the pygr.Data
  module file, but in *resource databases* either on your disk, in
  a remote XMLRPC server, or in a MySQL database (for details see below).
  
* If an object saved to pygr.Data depends on a given file,
  you should use an absolute path to that file, instead of a relative path,
  when originally constructing that object, prior to adding it to
  pygr.Data.  Relative paths are obviously inadequate for future users of
  pygr.Data to find the file, since they are likely to be working in
  a different "current directory".
  
* For similar obvious reasons, you should ensure that such a
  "dependency file" has security settings that make it readable
  to the set of users that you want to be able to access this pygr.Data
  resource in the future.  Users who lack privileges to be able to
  read that file will be unable to access this specific pygr.Data resource.
  
* To get a named resource from pygr.Data, you again just use this
  namespace, but with a "constructor syntax", i.e. add a call at the end of
  the resource name::
  
     import pygr.Data # MODULE PROVIDES ACCESS TO OUR DATA NAMESPACE
     nlmsa = pygr.Data.Bio.MSA.UCSC.foo17() # SYNTAX EMPHASIZES CONSTRUCTION OF INSTANCE
  
  The actual resource object is not obtained until you call the constructor.
  
* pygr.Data also stores *schema information* for the resources.
  These represent relationships between one resource and another resource
  (or their contents).  For example::
  
     pygr.Data.schema.Bio.Annotation.ASAP2.hg17.splicegraph = \
       pygr.Data.ManyToManyRelation(exons,exons,splices, # ADD ITS SCHEMA RELATIONS
                                    bindAttrs=('next','previous','exons'))
  
  indicates that the pygr.Data resource ``Bio.Annotation.ASAP2.hg17.splicegraph``
  is a many-to-many mapping of the pygr.Data resource *exons* onto itself,
  with additional "edge information" for each exon-to-exon mapping
  provided by the pygr.Data resource *splices*.  Furthermore, this mapping
  is to be bound directly to items of *exons* (i.e. objects returned
  from ``exons.__getitem__``) as their :attr:`next` attribute (giving the
  forward mapping), their :attr:`previous` attribute (giving the reverse
  mapping), and the :attr:`exons` attribute on items of *splices*
  (giving the mapping of the splice object to its pair of (source,target) exons
  as a tuple).
  
* when a user requests a resource that itself depends on other
  resources, pygr.Data automatically loads them.  Thus users do not need
  to know about the complex set of dependencies between data; all they
  have to do ask is ask for the specific data resource they want,
  and pygr.Data will take care of all the details behind the scenes.
  For example, a database of exon annotations is not very useful without
  also loading the genomic sequence database that these annotations
  refer to.  Using pygr.Data, we can simply load the exon annotation
  resource, and it will automatically get the genomic sequence data
  for us.  Thus to get an exon's sequence all we have to do is::
  
     exons = pygr.Data.Bio.Annotation.ASAP2.hg17.exons() # ANNOTATION DATABASE
     str(exons[464].sequence) # GET THE SEQUENCE OF THIS SPECIFIC EXON
  
  
* It should be noted that at the moment there is only one name
  (``Bio``) at the top-level of the pygr.Data module namespace (since currently
  this is only being used for bioinformatics).  However it's
  trivial to add new names as :class:`ResourcePath` objects to the pygr.Data
  module.
  


pygr.Data is transactional
--------------------------

pygr.Data follows a *transactional* model: new resources
added to pygr.Data are not saved to the resource database until you
call ``pygr.Data.save()``.  This has several benefits:


* Because of the transactional model,
  within a single transaction, the *order* in which you
  add resources to pygr.Data does not matter.  This is a crucial data
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
  persistent across Python interpreter sessions, pygr.Data must
  store object references in terms of their unique pygr.Data IDs.
  This is only possible if the object has been assigned a pygr.Data
  ID (by having added it to pygr.Data in the usual way) before
  you complete the transaction by calling ``pygr.Data.save()``.
  
* This also enables pygr.Data to provide a limited form of
  *rollback*, i.e. the ability to cancel an entire set of
  resource additions at any time before they are committed.
  You can do this by calling ``pygr.Data.rollback()``.
  
* You can save a given group of pygr.Data resources as a transaction
  to multiple pygr.Data resource databases, simply by calling
  ``pygr.Data.save``(*layer*) multiple times with different
  pygr.Data *layer* names.
  
* How do you decide what set of data forms a single transaction?
  This follows a very simple rule: if an object *A* that you are adding
  to pygr.Data depends on (i.e. *refers
  to*) some other object *B* that you also
  intend to add to pygr.Data, then *B* must either *already* have a pygr.Data ID,
  or *B* must also be added to pygr.Data in the same transaction.
  
* If you add resources to pygr.Data, you *must* call ``pygr.Data.save()``
  before your Python interpreter session exits.  Otherwise the transaction would
  be left incomplete and would not be saved to the pygr.Data resource database.
  Similarly, if for some reason you need to call ``reload(pygr.Data)``,
  but there are pending pygr.Data additions of data or schema, you must
  first call either ``pygr.Data.save()`` or ``pygr.Data.rollback()``
  to indicate whether you wish to save or dump these pending additions.
  


pygr.Data Namespace Conventions
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
  individual resource names are simply appended to the pygr.Data name, for example,
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

* Bio.Seq: currently, the main category in pygr.Data is sequence databases.
* Bio.MSA: Another major category is multiple sequence alignments (e.g. genome alignments).
  For example: "Bio.MSA.UCSC.hg18_multiz28way".
* Bio.Annotation: category representing annotation information bound
  to sequence intervals.
* Bio.Expression: category representing gene expression analysis,
  including microarray data.

You may obtain a directory of available resources available using
the ``pygr.Data.dir``() function::

   >>> pygr.Data.dir('Bio.Seq.Swiss')
   ['Bio.Seq.Swissprot.sp42']

This returns the list of items beginning with the string
you provided.  Use its ``asDict=True`` argument to make it return a dictionary
of matches with detailed information such as their docstring descriptions.

We suggest that you follow these conventions and extend them as needed.
Please report new category names to us so we can add them to the list.

How does pygr.Data access resource databases?
---------------------------------------------
The list of resource databases is read from the environment variable
PYGRDATAPATH.  If this variable is empty or missing, the default path
for pygr.Data to search is the user's home directory (\$HOME) and
current directory, in that order.  PYGRDATAPATH should be a comma separated list
of "resource path" strings, which must be one of the following:

* A directory path (e.g. /usr/local/pygrdata), in which pygr.Data should
  look for (or, if none present, create) a database file called ".pygr_data".
  You can use the tilde character to indicate your home directory path.
  These are accessed by pygr.Data using its :class:`ResourceDBShelve` class.
  
* a URL for accessing an XMLRPC server that is serving a pygr.Data
  resource database index (previously started by you or someone else).
  The URL must begin with "http://".
  These are accessed by pygr.Data using its :class:`ResourceDBClient` class.
  
* a MySQL server, indicated by a path entry of the form
  "mysql:*DBNAME.TABLENAME* *dbinfo*",
  where *DBNAME* is the name of the database in your MySQL
  server that contains the pygr.Data resource index,
  and *TABLENAME* is the name of the table which contains this index.
  *dbinfo* is optional.  If provided, it must be a whitespace separated
  list of arguments for connecting to the MySQL server, of the form
  *host* *user* *passwd*.  You can provide one, two
  or three of these optional arguments, always beginning with *host*.
  If no *dbinfo* is provided,
  pygr.Data will get the host, user, and password information for connecting
  to the MySQL server as usual from your
  .my.cnf configuration file in your home directory.
  Such resource databases are accessed by pygr.Data using its
  :class:`ResourceDBMySQL` class.


download=True Mode
------------------
When requesting a pygr.Data resource name, you can specify
the optional argument *download=True*, which forces pygr.Data
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
  all resource dependencies are satisfied.  In this way, pygr.Data
  can automatically obtain for you the complete set of local
  resources needed to work with a multi-genome alignment, for example::
  
     nlmsa = pygr.Data.Bio.MSA.UCSC.dm2_multiz9way(download=True)
  
  
* After a resource has been successfully downloaded and
  initialized, it will be automatically saved to your local pygr.Data resource
  database (specifically, the first resource database in your
  PYGRDATAPATH) for future usage.  Future requests for this
  resource do not need to specify download=True, because the
  resource is now recorded in your local pygr.Data resource database
  as being available locally.
  
* To see what downloadable resources are available, pass the
  download=True option to pygr.Data.dir().  Note: currently, this
  also lists resources that you have available locally.
  
* A downloadable resource can be any URL that returns
  a dataset usable in Pygr as a data resource.  Examples:
  a FASTA sequence dataset (accessed in Pygr as a BlastDB);
  an NLMSA textdump file (loaded in Pygr as an NLMSA using the
  textdump_to_binaries() function).  The URL can be anything
  that can be downloaded using the Python :mod:`urllib`
  module.
  
* Pygr.Data searches its resource databases for records
  of downloadable resources matching the requested name.
  Currently, only XMLRPC pygr.Data servers will return
  lists of downloadable resources.  Note that the resource
  database does not store the resource, and the resource will not
  be directly downloaded from the resource database.  Instead,
  the resource database simply stores a record indicating the location
  (URL) for downloading the resource, and how to initialize it
  automatically on your local computer.
  


Adding Downloadable Resources to Pygr.Data
------------------------------------------
Only a few steps are required to add a downloadable resource
to pygr.Data.  The main difference is that instead of saving an
actual resource, you are merely saving a pointer to download /
initialize the resource, which will only be invoked when a user
requests that the resource be downloaded to their local computer.

* First, you need the URL for downloading a data file that
  Pygr could use as a resource.  Obvious examples include a FASTA
  sequence database, or an NLMSA textdump.  Compressed or archived
  data files are supported (for details, see the :mod:`downloader`
  module documentation).
  
* Next, create a :class:`SourceURL` object with the desired URL::
  
     from pygr.downloader import SourceURL
     dfile = SourceURL('http://biodb.bioinformatics.ucla.edu/PYGRDATA/dm2_multiz9way.txt.gz')
  
  Note that this represents just a file, not an actual resource usable
  in Pygr.  This is the difference between a textdump file, and a
  Pygr NLMSA object built from that textdump.
  
* Just save the SourceURL to a local pygr.Data resource
  database (i.e. shelve storage) in the usual way::
  
     dfile.__doc__ = 'DM2 based nine genome alignment from UCSC in textfile  dump format'
     pygr.Data.Bio.MSA.UCSC.dm2_multiz9way.txt = dfile
  
  Note that we added the suffix ".txt" to the usual resource name, because
  this is just a textdump file instead of the actual resource that can be
  used in Pygr.  Strictly speaking there is no need to save the textfile
  directly to pygr.Data, but this improves modularity (e.g. there might
  be multiple URLs from which we could download the same resource text file).
  
* Finally, we create a rule for initializing the actual resource
  object (in this case, NLMSA) from the downloaded text.  As an example,
  the :class:`NLMSABuilder` class saves the appropriate rule for
  initializing an NLMSA from a text file::
  
     from pygr.nlmsa_utils import NLMSABuilder
     nbuilder = NLMSABuilder(dfile)
     nbuilder.__doc__ = 'DM2 based nine genome alignment from UCSC'
     pygr.Data.Bio.MSA.UCSC.dm2_multiz9way = nbuilder
     pygr.Data.save()
  
  Note that we saved this as the actual resource representing the
  dm2_multiz9way alignment, because that is what it will return
  when unpickled by pygr.Data.
  
  Here is another example, for downloading and initializing a
  FASTA sequence database::
  
     src = SourceURL('ftp://hgdownload.cse.ucsc.edu/goldenPath/droVir3/bigZips/droVir3.fa.gz')
     src.__doc__ = 'D. virilis Genome (February 2006) FASTA file'
     pygr.Data.Bio.Seq.Genome.DROVI.droVir3.fasta = src
     from pygr.downloader import GenericBuilder
     rsrc = GenericBuilder('BlastDB', src)
     rsrc.__doc__ = 'D. virilis Genome (February 2006)'
     pygr.Data.Bio.Seq.Genome.DROVI.droVir3 = rsrc
     pygr.Data.save()
  
  Note that we used the :class:`GenericBuilder` class, which acts as proxy
  for the class we want to use for building the resource (:class:`BlastDB`).
  At this moment we do not actually want to make a BlastDB, we simply
  want to save a rule for making a BlastDB when the user actually
  requests that this resource be downloaded.
  Upon unpickling by pygr.Data, :class:`GenericBuilder`
  simply calls its target class with the exact list of arguments /
  keyword arguments it originally received.  When *src* is
  unpickled by pygr.Data, it will be transformed into the local
  filename where the FASTA file was downloaded to (after automatic gunzipping).
  Since :class:`BlastDB` just expects a filename as its first argument,
  we provide *src* as the only additional argument to :class:`GenericBuilder`.
  Note that you specify the target class as a string; GenericBuilder
  matches this against its list of accepted classes, to avoid creating
  a security hole wide enough to drive a truck through!
  
* Setting up an XMLRPC server to serve the downloadable
  resources you saved to your pygr.Data shelve database is easy.
  When you create the server object, just pass the optional
  *downloadDB* argument as follows.  It should give
  the path to your shelve file containing this resource database::
  
     import pygr.Data
     nlmsa = pygr.Data.Bio.MSA.UCSC.hg17_multiz17way() # data to serve: NLMSA AND SEQ DBs
     server = pygr.Data.getResource.newServer('nlmsa_server',
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

.. function:: save(layer=None)

   Saves all pending pygr.Data additions to the resource database.
   If *layer* is not specified, each resource will be saved to the
   layer it was added to, or to the default layer if none was specified
   at the time of addition.  If *layer* is not None, it forces all
   pending data to be saved specifically to that layer.  You can call
   ``pygr.Data.save()`` multiple times with different *layer*
   values to make the same set of data (transaction) be saved to each
   of the specified resource databases.


.. function:: rollback()

   Dumps all pending pygr.Data additions (since the last ``save()``
   or ``rollback()``) without adding them to the resource database.


.. function:: list_pending()

   Returns a pair of two lists ([*data*],[*schema*]), where
   the first list shows newly added pygr.Data IDs that are currently pending,
   and the second list pygr.Data IDs that with newly added schema information
   pending.


.. function:: addResource(id,obj,layer=None)

   Add *obj* to pygr.Data as resource ID *id*, specifically within
   abstract resource *layer* if provided.  Queues *obj* for addition to
   the resource database, and marks it with its :attr:`_persistent_id`
   attribute, whose value is just *id*.  For a resource *id* 'A.Foo.Bar'
   this method is equivalent to the assignment statement::

      pygr.Data.A.Foo.Bar = obj

   This method is provided mainly to enable writing code that automates
   saving of resources, e.g. via code like::

      for id,genome in nlmsa.seqDict.prefixDict.items(): # 1st SAVE THE GENOMES
      genome.__doc__ = 'draft genome sequence '+id
      addResource('Bio.Seq.Genome.'+id,genome)



.. function:: deleteResource(id,layer=None)

   Delete resource *id* from the resource database specified by
   *layer* if provided (or the default resource database otherwise).
   Also delete its associated schema information.


.. function:: addSchema(name,schemaObj,layer=None)

   Add a schema object for the pygr.Data resource indicated by the
   string passed as *name*, to the specified *layer* if provided
   (or the default resource database otherwise).  For example::

      addSchema('Bio.Genomics.ASAP2.hg17.geneExons',
      pygr.Data.OneToManyRelation(genes,exons,bindAttrs=('exons','gene')))
      pygr.Data.save() # SAVE ALL PENDING DATA AND SCHEMA TO RESOURCE DATABASE


Note that schema information, like pending data, is not saved to
the resource database until you call ``pygr.Data.save()``.

The pygr.Data module also provides a directory function for searching
for resource names that begin with a given stem, either in all
databases, or in a specific layer:

.. function:: dir(prefix,layer=None,asDict=False)

   get list or dict of resources beginning with the specified string.
   If the optional *asDict* argument is True, then they are returned
   as a dictionary whose keys are resource names, and whose values are their
   descriptions (taken from the resource object's :attr:`__doc__` string).
   Otherwise they are returned as a list.


.. function:: newServer(name,serverClasses=None,clientHost=None,withIndex=False, host=None, port=5000, excludeClasses=None, downloadDB=None, **kwargs)

   Create and return a new XMLRPC server to serve all pygr.Data resources
   currently loaded in memory that are capable of XMLRPC client-server
   operation.  The server *name* will be used for
   purposes of XMLRPC communication.  The *withIndex=True* option
   will cause the server to also act as a pygr.Data resource database
   accessible via XMLRPC (i.e. add its URL to your PYGRDATAPATH environment
   variable, to make its resources accessible to any Python script).
   In this case, the server will add itself as new pygr.Data layer
   *name*, for any Python script that accesses its resource index.

   Currently, newServer() can serve three types of data as remote
   XMLRPC services: :class:`NLMSA`, :class:`BlastDB`, and :class:`AnnotationDB`.

   *serverClasses* allows you to specify a list of tuples of
   classes that can be served via XMLRPC.  Each tuple should consist of
   three values: *(dbClass,clientClass,serverClass)*, where
   *dbClass* is a normal pygr class, *clientClass* is the
   class to use for the XMLRPC client version of this data, and
   *serverClass* is the class to use for the XMLRPC server of
   this data.  If no value is provided to this option, the current
   default is::

      [(seqdb.SequenceFileDB,seqdb.XMLRPCSequenceDB,seqdb.BlastDBXMLRPC),
      (seqdb.BlastDB,seqdb.XMLRPCSequenceDB,seqdb.BlastDBXMLRPC),
      (AnnotationDB,AnnotationClient,AnnotationServer),
      (cnestedlist.NLMSA,xnestedlist.NLMSAClient,xnestedlist.NLMSAServer)]

   The *clientHost* option allows you to override the hostname
   that clients will be instructed to connect to.  The default is simply
   the fully qualified hostname of your computer.  But if, for example,
   you wished to access your server by port-forwarding localhost port 5000
   to your server port via SSH, you could pass a *clientHost*='localhost'
   setting.

   *excludeClasses*, if not None, should be a list of classes that
   should be excluded from the new server.  If None, the default is
   [pygr.sqlgraph.SQLTableBase,pygr.sqlgraph.SQLGraphClustered], since
   such relational database resources are better accessed directly from
   the relational database server, rather than via the XMLRPC server as
   an intermediate step.

   *downloadDB*, if not None, should be a file path to a pygr.Data
   shelve file in which a set of downloadable resource records have been
   stored.  See the section "download=True Mode" above for more details.

   *host, port* arguments are passed to the :class:`XMLRPCServerBase` constructor.
   For details see that section below.

   Once you create a server using this method, you start it using its
   :meth:`serve_forever()` method.  If the server does not provide its
   own index (i.e. *withIndex=False*), then you should first register
   it to your local resource database server (so that clients of that server
   will know about the new services your new server is providing), by
   calling its :meth:`register()` method.



.. function:: ResourceDBMySQL(tablename,createLayer=LAYERNAME)

   Create a resource database in a MySQL database table.
   *tablename* is the table to use in the database, in the format
   "*DBNAME.TABLENAME* *dbinfo*", where *DBNAME* is the name of the
   database in the MySQL server, and *TABLENAME* is the name of
   the table in that database that you wish to use to store the
   resource database.  *dbinfo* is optional.
   If provided, it must be a whitespace separated
   list of arguments for connecting to the MySQL server, of the form
   *host* *user* *passwd*.  You can provide one, two
   or three of these optional arguments.
   If no *dbinfo* is provided, host, port, user and password info are obtained
   from your .my.cnf config file as usual for the mysql client.

   To create a new table in the MySQL database (automatically initializing its schema),
   instead of assuming that it already exists, you must provide
   the *createLayer* argument, which is saved as the layer name
   of the new resource database.  If pygr.Data finds that it is unable
   to connect to a MySQL database table specified in your PYGRDATAPATH
   it will print a warning message, and ignore the offending database table.
   It will NOT silently create a database table for you in this case.
   The rationale is that whereas a misspelled directory name will result in
   an IOError (thus allowing pygr.Data to detect a bad directory name in PYGRDATAPATH),
   there would be no easy way for pygr.Data to tell whether you simply mistyped the name
   of an existing MySQL table, or whether you actually wanted to create a new MySQL table.

   Example: create a new resource database, give it the layer name "leelab",
   and register it in our list of resource databases::

      rdb = pygr.Data.ResourceDBMySQL('pygrdata.index',createLayer='leelab')

   Note that you must provide the *createLayer* argument, in order to
   create a new resource database table.  :class:`ResourceDBMySQL` will not
   automatically create a new table without this argument, simply because the
   *tablename* you provided does not exist.  In that case, it will
   raise an exception to alert you to the fact that either the correct table name
   was not given, or the table does not exist.


.. function:: dumps(obj)

   Provides a pygr.Data-aware pickling service; that is, if
   during pickling of *obj* any references are encountered
   to objects that pygr.Data IDs, it will simply save the ID.
   Returns a string pickle of *obj*.
   Use pygr.Data.loads() to restore an object pickled using this function.


.. function:: loads(data,cursor=None)

   Unpickles the string pickle contained in *data* in a pygr.Data-aware
   manner.  I.e. any references in the pickle of the form "PYGR_DATA_ID:"
   will be retrieved by pygr.Data in the usual way.

   *data* should have
   been generated by a previous call to pygr.Data.dumps().

   *cursor* if not None, must be a Python DB API 2.0 compliant
   cursor object, that will be used to load any objects that require
   a database connection.



pygr.Data Layers
----------------
To provide an intuitive way to refer to different resource databases,
pygr.Data associates "layer names" with them.  For example, the layer
name for the first resource database whose path is given relative to
your home directory is ``my``, and the first one whose path is given
relative to current directory is ``here``.  Remote resource databases
(XMLRPC; MySQL) each store their own layer name.  For example, within the
Lee lab, we keep a MySQL resource database whose layer name is "leelab".


* You can specify precisely which layer you want to access by prefixing
  your pygr.Data resource name with the desired layer name, e.g.::
  
     nlmsa = pygr.Data.leelab.Bio.MSA.UCSC.hg17_multiz17way()
  
  
* Similarly, you can specify which layer you want to store a resource
  or schema, in the same way::
  
     pygr.Data.leelab.schema.Bio.Annotation.ASAP2.hg17.splicegraph = \
       pygr.Data.ManyToManyRelation(exons,exons,splices, # ADD ITS SCHEMA RELATIONS
                                    bindAttrs=('next','previous','exons'))
  
  
* If you do not specify a layer, pygr.Data uses the first resource
  database in its list that returns the desired resource.
  
* You can delete a resource and its schema rules from a specific resource
  database by specifying its layer name::
  
     del pygr.Data.leelab.Bio.MSA.UCSC.hg17_multiz17way
  
  
* pygr.Data provides a set of default layer names:
  the first resource database whose path is given relative to
  your home directory is ``my``; the first one whose path is given
  relative to current directory is ``here``;the first one whose path is given
  relative to the root directory / is ``system``;
  the first entry that begins with a relative path
  (ie. a local file path that does not fit any of the preceding
  definitions) is ``subdir``;
  the first one whose path begins "http://" is ``remote``;
  the first one whose path begins "mysql:" is ``MySQL``.
  


pygr.Data Schema Concepts
-------------------------
Parallel to the pygr.Data namespace, pygr.Data maintains a schema namespace
that records schema information for pygr.Data resources.  Broadly speaking,
*schema* is any relationship that holds true over a set of data in a given
collection (e.g. in the human genome, "genes have exons", a one-to-many relation).
In traditional (relational) databases, this schema information is usually
represented by *entity-relationship diagrams* showing foreign-key
relationships between tables.  A pygr.Data resource is a collection
of objects (referred to in these docs as a "container" or "database");
thus in pygr, schema is a relation between pygr.Data resources, i.e.
a relationship that holds true between the items of one pygr.Data resource
and the items of another.  For examples, items in a "genes" resource
might each have a mapping to a subset of items in an "exons" resource.
This is achieved in pygr.Data by adding the mapping object itself as a pygr.Data
resource, and then specifying its schema to pygr.Data (in this example,
its schema would be a one-to-many relation between the "genes"
resource and the "exons" resource).  Adding the mapping object
as a pygr.Data resource, and adding its schema information, are
two separate steps::

   pygr.Data.Bio.Genomics.ASAP2.hg17.geneExons = geneToExons # SAVE MAPPING
   pygr.Data.schema.Bio.Genomics.ASAP2.hg17.geneExons = \
     pygr.Data.OneToManyRelation(genes,exons,bindAttrs=('exons','gene'))
   pygr.Data.save() # SAVE ALL PENDING DATA AND SCHEMA TO RESOURCE DATABASE

assuming that ``genes`` and ``exons`` are the pygr.Data resources
that are being mapped.  This would allow a user to obtain the mapping
from pygr.Data and use it just as you'd expect, e.g. assuming that
``gene`` is an item from ``genes``::

   geneToExons = pygr.Data.Bio.Genomics.ASAP2.hg17.geneExons()
   myexons = geneToExons[gene] # GET THE SET OF EXONS FOR THIS GENE

In practice, pygr.Data accomplishes this by automatically setting
``geneToExon``'s ``sourceDB`` and ``targetDB`` attributes
to point to the ``genes`` and ``exons`` resources, respectively.

Since most users find it easier to remember object-oriented behavior
(e.g. "a gene has an exons attribute", rather than "there exists a
mapping between gene objects and exon objects, called geneToExons"),
pygr.Data provides an option to bind attributes of the mapped
resource items.  In the example above, we bound an :attr:`exons` attribute
to each item of ``genes``, which automatically performs this mapping,
e.g. we can iterate over all exons in a given gene as easily as::

   for exon in gene.exons: # gene.exons IS EQUIVALENT TO geneToExons[gene]
     # DO SOMETHING...

Note: in this usage, the user does not even need to know about the
existence of the ``geneToExons`` resource; pygr.Data will load it
automatically when the user attempts to access the ``gene.exons``
attribute.  It can do this because it knows the schema of the pygr.Data
resources!

One additional aspect of pygr.Data schema relations goes a bit beyond
ordinary mapping: a mapping between one object (source) and another
(target) can have *edge information* that describes this specific
relationship.  For example, the connection
between one exon and another in the alternative splicing of an mRNA
isoform, is a *splice*.  For alternative splicing analysis, it is
actually crucial to have detailed information about the splice (e.g.
what experimental evidence exists for that splice; what tissues it was
observed, in what fraction of isoforms etc.) in addition to the exons.
Therefore, pygr.Data allows us to save edge information also as part
of the schema, e.g. for a ``splicegraph`` representing the set of
all splices (edges) between pairs of exons (nodes), we can
store the schema as follows::

   pygr.Data.Bio.Genomics.ASAP2.hg17.splicegraph = splicegraph # ADD A NEW RESOURCE
   pygr.Data.schema.Bio.Genomics.ASAP2.hg17.splicegraph = \
     pygr.Data.ManyToManyRelation(exons,exons,splices, # ADD ITS SCHEMA RELATIONS
                                  bindAttrs=('next','previous','exons'))
   pygr.Data.save() # SAVE ALL PENDING DATA AND SCHEMA TO RESOURCE DATABASE

This type of mapping ("edge" relations between pairs of "nodes")
is referred to in mathematics as a *graph*, and has very general
utility for many applications.  For further information on graphs in
pygr, see the tutorial or the :mod:`mapping` module reference below.

What information does pygr.Data schema actually store?  In practice,
the primary information stored is *attribute* relations:
i.e. for a specified resource ID, a specified attribute name
should be added to the resource object (or to items obtained
from it), which in turn maps to some specified target resource
(or items of that resource).

Although users do not need to know
how this information is saved, I will outline the methodology
as a reference for developers who want to work directly with this
internal data (skip this section otherwise).

* In a given resource database (dictionary), information for constructing a
  given resource ``id`` is stored with its resource ID as the key.
  i.e. if ``rdb`` is a resource database, ``rdb[id]`` gives
  the string to unpickle to construct the resource.  Schema information
  for that resource is stored as ``rdb['SCHEMA.'+id]``.
  
* This schema information (for a given resource) is itself
  a dictionary, whose keys are attribute names to bind to this
  resource, and whose associated values are themselves dictionaries
  specifying the rules for what to bind to this attribute and how.
  See below for further details.
  
* Attributes are added as "shadow attributes" provided by
  descriptors added to the class object for the resource or to
  its :attr:`itemClass` or :attr:`itemSliceClass` object if the
  attribute is to be bound to *items of the resource*.  Descriptors
  (also referred to in the Python documentation as "properties")
  are the major mechanism by which Python new-style classes
  (i.e. subclasses of :class:`object` in Python 2.2 and later)
  can execute code in response to a user attempt to get an
  object attribute, and are definitely preferable over writing
  :meth:`__getattr__` method code if all that's desired
  is an attribute with a specified name.  For more information
  on descriptors, see the Python Reference Manual.
  
* The basic principles of these "shadow attributes" are that
  1. they are bound to the class object, not the instance object;
  2. they are only invoked if the specified attribute name is
  missing from the instance object's :attr:`__dict__`;
  3. once invoked, they save their
  result on the instance object (in its :attr:`__dict__`)
  as the same-named attribute; 4. thus, the descriptor method
  will only be called once; thereafter the attribute will be
  obtained directly from the value cached on the instance object;
  5. the descriptor only loads its target resource(s) when the user
  attempts to read the value of the attribute.  Thus no extra
  resources are loaded until the user actually demands information
  that requires them.
  
* Currently, these shadow attributes are implemented by
  three different descriptor classes in pygr.Data:
  :class:`OneTimeDescriptor`, for binding attributes directly on a resource
  object (container);
   :class:`ItemDescriptor`, for binding attributes on items (or slices of
  items) obtained from a resource object (via its __getitem__ method);
  :class:`SpecialMethodDescriptor`, for binding special Python methods like
  :meth:`__invert__`.
  
* The rule information for a given attribute is itself a dictionary,
  with the following string keys governing the behavior of the shadow attribute.
  *targetID*: the pygr.Data resource ID of the resource that this
  attribute links to.
  *itemRule*: True if the attribute should be bound to *items*
  (and slices of items, if defined) of the source resource, rather than
  directly to the source resource object itself (if itemRule=False).
  *invert*: True if the target resource should first be inverted
  (i.e. query its reverse-mapping rather than its forward-mapping), False otherwise.
  *getEdges*: True if the attribute should query the target resource's
  :attr:`edges` mapping (i.e. the mapping provided by its :attr:`edges` attribute)
  rather than its forward mapping, False otherwise.
  *mapAttr*: if not None, use this named attribute of our source object,
  instead of the source object itself, as the key for search the target resource
  mapping.
  *targetAttr*: if not None, return this named attribute of the result of
  the search, rather than the result of the search itself.


ResourceFinder
--------------
The core functionality of the pygr.Data module is provided by the
:class:`ResourceFinder` class, an instance of which is created at the
top-level of the module as ``pygr.Data.getResource``.  It
provides methods for adding, deleting and controlling pygr.Data
resources and schema.

.. function:: getResource(id, layer=None, debug=None, download=False, *args, **kwargs)

   Look up pygr.Data resource *id*, using the specified abstract
   resource *layer* if provided.  Searches the resouce database(s)
   for *id*, constructs it from the saved resource rule (e.g. from
   a local resource database, by unpickling the object).  Saves the
   object in its cache so that subsequent calls for the same resource
   ID will return the same object.  Applies the stored pygr.Data schema
   rules to it using :meth:`applySchema()`.  Marks the object with
   its :attr:`_persistent_id` attribute, whose value is just *id*.

   The *download=True* option forces pygr.Data to restrict the
   search to downloadable resources.  If a downloadable resource
   matching the requested ID is found, it will be downloaded to a local
   file, uncompressed, and any necessary initialization steps
   performed automatically.  The returned object will be a fully
   initialized local copy of the requested resource.

   Passing the option *debug=True* will cause it to raise any
   exception that occurs during resource loading immediately, rather
   than continuing to search its resource database list.  This is
   helpful for debugging purposes.


.. method:: getResource.addResource(id,obj,layer=None)

   Same as the top-level module function of the same name.


.. method:: getResource.addSchema(name,schemaObj,layer=None)

   Same as the top-level module function of the same name.


.. method:: getResource.dir(prefix,layer=None,asDict=False)

   Same as the top-level module function of the same name.


.. method:: getResource.deleteResource(id,layer=None)

   Same as the top-level module function of the same name.


.. method:: getResource.dumps(obj)

   Same as the top-level module function of the same name.


.. method:: getResource.list_pending()

   Same as the top-level module function of the same name.


.. method:: getResource.loads(data,cursor=None)

   Same as the top-level module function of the same name.


.. method:: getResource.newServer(name,serverClasses=None,clientHost=None,withIndex=False, host=None, port=5000, **kwargs)

   Same as the top-level module function of the same name.


.. method:: getResource.rollback()

   Same as the top-level module function of the same name.


.. method:: getResource.save_pending(layer=None)

   Same as the top-level module function ``pygr.Data.save()``.


The following methods are mainly for internal use, and are unlikely to be
needed by users of pygr.Data.  In general, you should not use them unless
you have a very good reason to be working with the interal pygr.Data
methods, and really know what you are doing!
.. method:: update()

   Update ``getResource``'s list of resource databases, by parsing the environment
   variable PYGRDATAPATH and attempting to connect to the resource databases
   listed there.  Does not return anything.


.. method:: addLayer(layerName,rdb)

   Add the resource database *rdb* to the current resource database list,
   as a named layer given by the string *layerName*.  Over-writing an
   existing layer name is not allowed, for security reasons;
   the previous layer entry must first be deleted.


.. method:: getLayer(layerName)

   Get the specified resource database, by its layer name.  If *layerName*
   is None, returns the default (first) resource database in its list.


.. method:: resourceDBiter()

   Generates all the resource databases currently listed by ``getResource``.


.. method:: registerServer(locationKey,serviceDict)

   Registers the set of resources specified by *serviceDict* to the
   first resource database index in PYGRDATAPATH that will accept them.
   *serviceDict* must be a dictionary whose keys are resource IDs and
   whose associated values are pickled resource objects (encoded as strings).
   *locationKey* should be a string name chosen to represent the "location"
   where the data are stored.  This can be anything you wish, and is mainly used
   to let the user know where the data will come from.  This might be used
   in future versions of pygr.Data to allow preferential screening of where
   to get data from (local disk is better than NFS mounted disk, which in turn
   might be preferable over remote XMLRPC data access).


.. method:: findSchema(id)

   Returns a dictionary for the schema (if any) found for the pygr.Data resource
   specified by *id*.  The dictionary keys are attribute names (representing
   attributes of the specified resource or its contents that should have
   schema relations with other pygr.Data resources), and whose values are
   themselves dictionaries specifying the precise schema rules for constructing
   this specific attribute relation.


.. method:: schemaAttr(id,attr)

   Return the target data linked to by attribute *attr* of pygr.Data
   resource *id*, based on the stored pygr.Data schema.  The target resource
   object will be obtained by pygr.Data.getResource as usual.


.. method:: applySchema(id,obj)

   Apply the pygr.Data schema for resource *id* to the actual data
   object representing it (*obj*), by decorating it (and / or its itemClass
   and itemSliceClass) with properties representing its schema attributes.
   These properties are implemented by adding descriptor attributes to the
   associated class, such as :class:`OneTimeDescriptor` or :class:`ItemDescriptor`.


.. method:: saveResource(resID,obj,layer=None)

   Raw interface to actually save a specific resource to the specified
   (or default) resource database.
   DO NOT use this internal interface unless you know what you are doing!


.. method:: saveSchema(id,attr,bindingDict,layer=None)

   Save a schema attribute relation for attribute *attr* of pygr.Data
   resource *id*, to the specified resource database *layer* (or the default,
   first resource database in the list, if no layer specified).
   *bindingDict* must be a dictionary specifying the rules for
   binding the attribute to a pygr.Data resource target; see below for details.
   DO NOT use this internal interface unless you know what you are doing!


.. method:: delSchema(id,layer=None)

   Delete schema bindings for all attributes of the resource *id*, in
   the specified resource database *layer*, as well as all schema relations
   on other resources that are targeted to resource *id*.


ResourceDBMySQL
---------------
Implements an interface to storage of a resource database in a MySQL
database table.

.. class:: ResourceDBMySQL(tablename,finder=None,createLayer=None)

   *tablename* is the table to use in the database, in the format
   "*DBNAME.TABLENAME* *dbinfo*", where *DBNAME* is the name of the
   database in the MySQL server, and *TABLENAME* is the name of
   the table in that database that you wish to use to store the
   resource database.  *dbinfo* is optional.
   If provided, it must be a whitespace separated
   list of arguments for connecting to the MySQL server, of the form
   *host* *user* *passwd*.  You can provide one, two
   or three of these optional arguments.
   If no *dbinfo* is provided, host, port, user and password info are obtained
   from your .my.cnf config file as usual for the mysql client.

   *finder*, if specified gives the :class:`ResourceFinder` instance
   in which the new resource DB should be registered.  If None provided,
   defaults to pygr.Data.getResource.

   *createLayer*, if specified forces it to create a new table
   in the MySQL database (instead of assuming that it already exists),
   and saves *createLayer* as the layer name of this resource database.

   Example: create a new resource database, give it the layer name "leelab",
   and register it in our list of resource databases::

      rdb = pygr.Data.ResourceDBMySQL('pygrdata.index',createLayer='leelab')

   Note that you must provide the *createLayer* argument, in order to
   create a new resource database table.  :class:`ResourceDBMySQL` will not
   automatically create a new table without this argument, simply because the
   *tablename* you provided does not exist.  In that case, it will
   raise an exception to alert you to the fact that either the correct table name
   was not given, or the table does not exist.


.. method:: __getitem__(id)

   Get resource *id* from this resource database, or :exc:`KeyError`
   if not found.


.. method:: __delitem__(id)

   Delete resource *id* from this resource database, or :exc:`KeyError`
   if not found.


.. method:: __setitem__(id,obj)

   Save resource *id* to this resource database, by pickling it
   with ``self.finder.dumps(obj)``.


.. method:: registerServer(locationKey,serviceDict)

   Saves the set of resources specified by *serviceDict* to the
   database.
   *serviceDict* must be a dictionary whose keys are resource IDs and
   whose associated values are pickled resource objects (encoded as strings).
   *locationKey* should be a string name chosen to represent the "location"
   where the data are stored.  This can be anything you wish, and is mainly used
   to let the user know where the data will come from.  This might be used
   in future versions of pygr.Data to allow preferential screening of where
   to get data from (local disk is better than NFS mounted disk, which in turn
   might be preferable over remote XMLRPC data access).


.. method:: setschema(id,attr,ruleDict)

   Save schema information for attribute *attr* on resource *id*
   by pickling the *ruleDict*.


.. method:: delschema(id,attr)

   Delete schema information for attribute *attr* on resource *id*.


.. method:: getschema(id)

   Get schema information for resource *id*, in the form of a dictionary
   whose keys are attribute names, and whose values are the associated
   schema *ruleDict* for each bound attribute.


ResourceDBShelve
----------------
Implements an interface to storage of a resource database in a Python
:mod:`shelve` (i.e. BerkeleyDB file) stored on local disk.
Provides the same interface as :class:`ResourceDBMySQL`, except for
no :meth:`registerServer` method.  Note: any method call that would
save information to the database temporarily re-opens the database
file in write mode, saves the required information, and immediately
closes and re-opens
the databae in read-only mode.  Thus, unless two clients try
to save information to the same file at exactly the same time,
successive writes by multiple clients will not interfere with each
other.

.. class:: ResourceDBShelve(dbpath,finder,mode='r')

   *dbpath* is the path to the directory in which the shelve
   file is found (or should be created, if none present).


ResourceDBClient
----------------
Implements a client interface to storage of a resource database in an XMLRPC
server.  For security reasons, only provides the :meth:`__getitem__`,
and :meth:`registerServer` methods.

ResourceDBServer
----------------
Implements a server interface for storage of a resource database in
a standard Python dict, served to clients via an XMLRPC
server (use :class:`coordinator.XMLRPCServerBase` as the XMLRPC
server to serve this object).

.. class:: ResourceDBServer(layerName, readOnly=True)

   *layerName* is the layer name that this server will provide
   to pygr.Data clients.  *readOnly* if True, makes the server reject
   any requests to add new database rules received via XMLRPC, i.e.
   only allows :meth:`getName` and :meth:`getResource` calls via XMLRPC.
   If False, also allows calls to :meth:`registerServer` and :meth:`delResource`.


ResourcePath
------------
Used for providing the dynamically extensible pygr.Data namespace
that provides the normal interface for users to access pygr.Data resources.

.. class:: ResourcePath(namepath,layerName=None)

   *namepath* specifies the ID string to use for this resourcePath.
   *layerName* if specified, gives the layer name that should be used
   for finding this resource and any subattributes of it.

   For example, ``Bio`` is added at the top-level of the pygr.Data module
   by the following code::

      Bio = ResourcePath('Bio')



.. method:: __getattr__(attr)

   extends the resource path by one step, returning a
   :class:`ResourcePath` object representing the requested attribute.


.. method:: __setattr__(attr,obj)

   saves *obj* as the specified resource ID, by calling
   :meth:`getResource.addResource`, with our layer name (if any).


.. method:: __delattr__(attr)

   deletes the specified resource ID, by calling
   :meth:`getResource.deleteResource`, with our layer name (if any).


.. method:: __call__(*args,**kwargs)

   Construct the specified resource ID, by calling :meth:`getResource`,
   with our layer name (if any), and the specified arguments (if any).


SchemaPath
----------
Class for top-level object representing a schema namespace.  e.g. in the pygr.Data
module::

   schema = SchemaPath() # CREATE ROOT OF THE schema NAMESPACE


ResourceLayer
-------------
Class for top-level object representing a pygr.Data layer.  e.g. in the pygr.Data
module::

   here = ResourceLayer('here') # CREATE TOP-LEVEL INTERFACE TO here LAYER


ManyToManyRelation, OneToManyRelation, ManyToOneRelation, OneToOneRelation
--------------------------------------------------------------------------
Convenience class for constructing schema relations for
a general graph mapping from a sourceDB to targetDB with edge info.

.. class:: ManyToManyRelation(sourceDB,targetDB,edgeDB=None,bindAttrs=None)

   *sourceDB*,*targetDB*, and *edgeDB* can be either
   a string resource ID, a :class:`ResourcePath` object, or
   an actual pygr.Data resource (automatically marked with its ID
   as the :attr:`_persistent_id` attribute).
   *bindAttrs*, if provided, must give a list of string attribute names to be
   bound, in order, to items of *sourceDB*, *targetDB*,
   and *edgeDB*, in that order.  A None value in this list simply
   means that no attribute binding will be made to the corresponding
   pygr.Data resource.

Note: this class simply records the information necessary for this
schema relation.  The information is not actually saved to the resource
database until its :meth:`saveSchema` method is called by
the :class:`SchemaPath` object.  In addition to saving attribute
bindings given by *bindAttrs*, this will also create bindings
on the mapping resource object itself (i.e. the resource whose
schema is being set; see an example in the tutorial).  Specifically,
it will save bindings for its :attr:`sourceDB`,:attr:`targetDB`,
and :attr:`edgeDB` attributes to the corresponding resources
given by the *sourceDB*,*targetDB*,
and *edgeDB* arguments.

:class:`OneToOneRelation`, :class:`OneToManyRelation`, :class:`ManyToOneRelation`
and :class:`ManyToManyRelation` differ only in the uniqueness vs. multiplicity
of the mapping indicated.
E.g.  \textasciitilde``m1[v] --> k`` vs.
\textasciitilde``mMany[v] --> [k1,k2,...]``

DirectRelation, ItemRelation, InverseRelation
---------------------------------------------
Users are unlikely to have any reason to work directly with these
internal interfaces.  Instead, use :class:`ManyToManyRelation, OneToManyRelation, ManyToOneRelation, OneToOneRelation`
as these cover the normal schema relationships.
You should only use internal interfaces like
:class:`DirectRelation, ItemRelation, InverseRelation` if you
have a real need to do so, and really know what you are doing!
This documentation is only provided for developers directly working
on pygr internals.

:class:`DirectRelation` is a convenience class for constructing
a single schema attribute relation on a pygr.Data resource,
linking it to another pygr.Data resource.

.. class:: DirectRelation(target)

   *target* gives a reference to a pygr.Data resource, which will
   be the target of a bound schema attribute.  *target* can be either
   a string resource ID, a :class:`ResourcePath` object, or
   an actual pygr.Data resource (automatically marked with its ID
   as the :attr:`_persistent_id` attribute).


.. method:: schemaDict()

   returns a basic *ruleDict* dictionary for saving this schema binding.
   Can be over-ridden by subclasses to customize schema binding behavior.


.. method:: saveSchema(source,attr,layer=None,**ruleDict)

   Saves a schema binding for attribute *attr* on pygr.Data resource
   *source* to the specified resource database *layer* (or
   to the default resource database if not specified).  *ruleDict*
   if specified provides additional binding rules (which can add to or
   over-ride those returned by the :meth:`schemaDict` method).
   *source* can be either
   a string resource ID, a :class:`ResourcePath` object, or
   an actual pygr.Data resource (automatically marked with its ID
   as the :attr:`_persistent_id` attribute).


:class:`ItemRelation` provides a subclass of :class:`DirectRelation`
that binds to the *items* of resource *source* rather than to the
*source* object itself.

:class:`InverseRelation` provides a subclass of :class:`DirectRelation`,
that binds *source* and *target* as each other's inverse mappings.
That is, it binds an :attr:`inverseDB` attribute to each resource
that points to the other resource.  When either resource is loaded,
a special :meth:`__invert__` method will be added, that simply
loads and returns the resource pointed to by the :attr:`inverseDB`
binding.

ForeignKeyMap
-------------
Provides a mapping between two containers, assuming that items of the target
container have a foreign key attribute that gives the ID of an item in the source
container.

.. class:: ForeignKeyMap(foreignKey,sourceDB=None,targetDB=None)

   *foreignKey* must be a string attribute name for the foreign key on
   items of the *targetDB*.  Furthermore, *targetDB* must provide
   a :meth:`foreignKey` method that takes two arguments: the *foreignKey* attribute name,
   and an identifier that will be used to search its items for those whose attribute
   matches this identifier.  It must return an iterator or list of the matching items.


.. method:: __getitem__(id)

   get a list of items in *targetDB* whose attribute matches this *id*.


.. method:: __invert__()

   get an interface to the reverse mapping, i.e. mapping object that takes an
   item of *targetDB*, and returns its corresponding item from *sourceDB*,
   based on the input item's foreign key attribute value.


For example, given a container of clusters, and a container of exons (that each
have a :attr:`cluster_id` attribute), we create a mapping between them as follows::

   m = ForeignKeyMap('cluster_id',clusters,exons)
   for exon0 in m[cluster0]: # GET EXONS IN THIS CLUSTER
       do something...
   cluster1 = (~m)[exon1]  # GET CLUSTER OBJECT FOR THIS EXON


nonPortableClasses,SourceFileName
---------------------------------
The variable *pygr.Data.nonPortableClasses* specifies a list of
classes which have local data dependencies (e.g. requires reading a file
that is on your local disk),
and therefore cannot be transferred over XMLRPC to a remote client
by simple pickling / unpickling.  :meth:`pygr.Data.newServer` will
automatically cull any data that has such dependencies from the list
of resources it loads into the XMLRPC server it constructs, so that
the server will not attempt to serve data that actually will not work
on remote clients.  You can add your own classes to this list if
needed.

By default, the *pygr.Data.nonPortableClasses* list consists of simply a single
class, :class:`pygr.Data.SourceFileName`, which is a subclass of str
that marks a string as representing a path to a file.  It behaves
just like a string, but allows pygr.Data to be smart about checking
whether the required file actually exists and is readable before returning
a resource to the user.  If you save filenames on your own objects using
this class, pygr.Data will therefore be able to handle them properly for
many issues such as XMLRPC portability to remote clients.  You do this simply
as follows::

   class Foo(object):
     def __init__(self,filename):
       self.filename = SourceFileName(str(filename)) # MARK THIS A BEING A FILE NAME
       ifile = file(self.filename) # OPEN THIS FILE NOW IF YOU WANT...

