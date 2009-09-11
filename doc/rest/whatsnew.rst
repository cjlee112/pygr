What's New in Pygr 0.8
----------------------

This list attempts to summarize the main things that have changed
from Pygr 0.7.

Windows Platform
^^^^^^^^^^^^^^^^

We have extended Pygr to support the Windows platform, and have tested
extensively on Windows.  This involved a variety of changes:

* The setup.py build script was completely refactored, to build
  in a platform-independent way.  We test building Pygr on
  native Windows (using Python 2.5 and Visual Studio 2003) and
  Windows/Cygwin on a daily basis.

* Pygr now uses binary file mode when opening non-text files, as is 
  required on Windows.

* platform independent path manipulation functions are used throughout.

* We added :meth:`close()` methods to objects that keep a file open
  during the object's lifetime.
  Previously, Pygr relied on these files to be closed automatically
  by Python garbage collection (i.e. when the object's refcount goes to zero).
  However, an open file can cause wierd problems on Windows, e.g. if one
  process tries to delete a file while another file still has the file
  open.  Our tests suggested that relying on Python garbage collection
  to close the file automatically was not adequate on Windows.
  We added :meth:`close()` methods to :class:`cnestedlist.NLMSA`,
  :class:`seqdb.SequenceFileDB`,
  :class:`annotation.AnnotationDB`, :class:`mapping.Graph`,
  and :class:`sqlgraph.DBServerInfo`.



worldbase and metabase
^^^^^^^^^^^^^^^^^^^^^^

The module formerly known as ``pygr.Data`` has been split into two
quite different pieces: 

* the :mod:`metabase` module is a thorough refactoring of the classes and code.
  We now use the term "metabase" (i.e. "a metadata database") instead of
  "resource database".

* the importable object :mod:`worldbase` provides the default interface
  for a virtual namespace for scientific data.  :mod:`worldbase` acts as
  an interface to whatever list of metabases you defined via the
  environment variable ``WORLDBASEPATH``.

Functionality changes:

* ``download=True``: passing this argument to worldbase requests makes
  worldbase get the resource installed locally; if it is not available
  locally, it will attempt to download it from a remote service and install
  it locally.  Similarly, if this resource has additional resource dependencies,
  worldbase will also try to ensure that they are installed locally, via
  the same mechanism.

* the new :mod:`downloader` module can automatically uncompress / extract several
  common formats, including zip, gzip, and tar.

* a variety of classes for downloadable resources are now provided:

  * :class:`dowloader.SourceURL`: a URL for a downloadable resource file.  When
    unpickled on a client machine, the object will download the resource
    file, and uncompress / extract it automatically.

  * :class:`downloader.GenericBuilder`: for constructing any class that can be built
    directly from a downloaded file.  Currently this is used mainly for 
    :class:`seqdb.SequenceFileDB`.

  * :class:`nlmsa_utils.NLMSABuilder`: for constructing NLMSA from downloaded textfile.

* metabases are no longer automatically opened on import of the module.
  Importing :mod:`metabase` does nothing but import the classes.

* At any time you can change the effective WORLDBASEPATH by simply calling
  the :meth:`update()` method with a new path string.

* You can clear the cache of loaded objects at any time by calling the
  :meth:`clear_cache()` method.  This forces any future worldbase requests
  to re-load the specified resource (even if it was previously loaded).

* The :meth:`dir()` method on any metabase now accepts regular expression
  queries.

* Metabase resource paths now take advantage of Python 2.6+'s support
  of __dir__ to customize the results of Python's builtin function dir().
  i.e. In Python 2.6+, you can simply use the builtin dir() to query
  any metabase resource path.

* To add equivalent support on earlier versions of Python (whose builtin
  dir() does not support __dir__), Pygr supplies a dir() function that
  acts like Python 2.6's.


XMLRPC Service enhancements
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Several improvements:

* creating a new XMLRPC server now merely requires instantiating the
  new class :class:`metabase.ResourceServer` from the :mod:`metabase` module.
  It takes the same arguments as the old ``newServer()`` function.

* :class:`annotation.AnnotationDB` can now be served via XMLRPC.  This completes the
  triad of sequence databases, alignment databases and annotation database;
  all can be served / accessed remotely transparently via worldbase XMLRPC. 

* The recommended method for running an XMLRPC server is to run it
  from an interactive Python interpreter session in a separate thread.
  You can then run this session within the UNIX ``screen`` utility and
  disconnect / reconnect to it in subsequence ``ssh`` sessions.
  We added convenience methods to support this recommended usage pattern.

* 0.8 XMLPRC servers are backwards compatible to use by 0.7 clients.

seqdb
^^^^^

This module was been extensively refactored, to simplify the code and
improve documentation.

* :class:`BlastDB` is deprecated.  We have separated BLAST functionality
  from sequence database functionality; see the section on the new
  :mod:`blast` module below.

* :class:`seqdb.SequenceDB` provides a base class for implementing new sequence
  database storage back-ends.  It provides a standard dictionary-like
  interface to sequence objects, with caching of sequence objects,
  smart caching of sequence string retrieval, etc.

* established a general interface for obtaining information about a 
  sequence without actually instantiating a sequence object: the
  :attr:`seqdb.SequenceDB.seqInfoDict` attribute.  This is any dictionary-like
  object whose keys are sequence IDs and values are objects with
  at least the attribute ``length``, which must be the sequence's length.

* :class:`seqdb.SequenceFileDB` is the new standard sequence database storage
  subclass.  It stores sequences in a text file indexed by a Python shelve,
  and uses :func:`fseek()` to retrieve sequence substrings efficiently.
  Use this instead of :class:`BlastDB`.

* :class:`seqdb.SequenceDB` now provides a complete and consistent dict-like
  interface, using UserDict.DictMixin.

* :class:`seqdb.SequenceDB` caching has been improved in several ways.  First,
  by default, it uses a :class:`classutil.RecentValueDictionary` as its object cache.
  Thus, when the user drops all references to a given row object, it
  will be automatically flushed from the cache.  Second, as a general
  Pygr standard, the method :meth:`clear_cache()` will clear all entries
  from the cache.

* :class:`seqdb.SequenceDB` was extensively refactored to
  use the new :func:`classutil.get_bound_subclass()` mechanism
  to subclass the :attr:`itemClass` and :attr:`itemSliceClass` automatically.
  This eliminates the use of :meth:`__getattr__` on item classes, replacing
  them with standard Python descriptors.  This greatly improves the modularity
  of the code.

annotation
^^^^^^^^^^

We created a new :mod:`annotation` module and moved existing 
:class:`AnnotationDB` functionality here.

* we created the new :class:`annotation.TranslationAnnot` and
  :class:`annotation.TranslationAnnotSlice` classes to represent
  open reading frame (ORF) annotations.  Such an ORF annotation
  differs from a normal annotation in a couple respects:

  * it represents a *translation* of the sequence interval it
    annotates.  Therefore its length is 1/3 that of the sequence
    interval it annotates.

  * Unlike a regular annotation, you *can* request its string value
    (using ``str()``).  The result will be the amino acid translation
    of the selected ORF interval.  Thus an ORF annotation object
    can be treated like a sequence object in all respects -- you
    can align it, measure its sequence similarity to another sequence etc.

* :class:`annotation.AnnotationDB` caching has been improved in several ways.  First,
  by default, it uses a :class:`classutil.RecentValueDictionary` as its object cache.
  Thus, when the user drops all references to a given row object, it
  will be automatically flushed from the cache.  Second, as a general
  Pygr standard, the method :meth:`clear_cache()` will clear all entries
  from the cache.  Third, the *maxCache* constructor argument allows
  you to set the maximum size of the cache.

* :class:`annotation.AnnotationDB`
  now provides a complete and consistent dict-like
  interface, using UserDict.DictMixin.

* :class:`annotation.AnnotationDB` can now be served via XMLRPC.


blast
^^^^^

We created a new :mod:`blast` module and moved existing BLAST functionality
here, thoroughly refactoring it in the process.

* :class:`BlastDB` is deprecated.  Instead of combining sequence database
  functionality and blast functionality as this class did, the new module
  only contains blast functionality; sequence database functionality is
  kept in the :mod:`seqdb` module.

* BLAST is now treated as a many-to-many mapping, just like any other
  Pygr graph object.  That is, a :class:`blast.BlastMapping` object 
  acts like a graph whose nodes are sequence interval objects, and
  whose edges are alignment edge objects. 

* Thus to perform a query, you can simply use a sequence object
  as a key for querying the :class:`blast.BlastMapping`.  The
  result will simply be a :class:`cnestedlist.NLMSASlice` as 
  usual for an alignment query.

* To pass additional parameters for controlling the BLAST search,
  use the :class:`blast.BlastMapping` as a callable (function) object
  to which you pass these parameters as arguments.  The result will
  be an :class:`cnestedlist.NLMSA` alignment object.

* You can also use this to pass a dictionary containing multiple
  sequences to be used as queries.  Since the blastall program
  will only be invoked once for all the queries (instead of
  once for each sequence), this can be more efficient.  Pass
  the optional argument *queryDB* to the callable; its values
  must be sequence (interval) objects to be used as queries.

* To construct a :class:`blast.BlastMapping` instance, you simply
  pass it the sequence database to be searched.

* We added support for blastx, tblastn and tblastx.  This makes use 
  of the new :class:`annotation.TranslationAnnot` "translation annotation"
  objects.

* Use :class:`blast.BlastMapping` for the following BLAST modes:

  * blastn: automatically selected by Pygr
    when the query and database sequences are both nucleotide;

  * blastp: when the query and database sequences are both protein;

  * tblastn: when the query is protein and the database sequences are 
    nucleotide.

* Use :class:`blast.BlastxMapping` for the following BLAST modes:

  * tblastx: automatically selected by Pygr
    when the query and database sequences are both nucleotide;

  * blastx: when the query is nucleotide and the database sequences are 
    protein.

* Use :class:`blast.MegablastMapping` for megablast (nucleotide vs. nucleotide
  with repeat masking).

* The blast parser now returns alignment group information, i.e. it indicates
  the beginning and end of each BLAST alignment block, which is required
  for reporting blastx results correctly.

NLMSA
^^^^^

* added a general method for loading interval alignments from 
  user-supplied alignment parsers:
  :meth:`cnestedlist.NLMSA.add_aligned_intervals()`

* :func:`cnestedlist.textfile_to_binaries()` now accepts an optional *buildpath* argument
  specifying where the NLMSA indexes should be constructed (instead of
  in the current directory).

sqlgraph
^^^^^^^^

* :class:`sqlgraph.SQLTable` has been generalized to work with other databases
  besides MySQL.  Currently it also works with sqlite.  Adding other
  database back-ends requires a function for analyzing the schema of
  that database and macros for handling non-standard SQL usages.

* :class:`sqlgraph.SQLTable` has added *write* support, via the *writeable=True*
  option, :meth:`insert()` and :meth:`new()` methods.  Use the 
  :meth:`new()` method to create a new instance in the database,
  passing it keyword arguments for all the column values.  To
  update an existing instance (row) in the database, simply change
  its attribute value(s) in the usual Python way.

* :class:`sqlgraph.SQLTable` caching has been improved in several ways.  First,
  by default, it uses a :class:`classutil.RecentValueDictionary` as its object cache.
  Thus, when the user drops all references to a given row object, it
  will be automatically flushed from the cache.  Second, as a general
  Pygr standard, the method :meth:`clear_cache()` will clear all entries
  from the cache.

* :class:`sqlgraph.SQLTable` was extensively refactored to
  use the new :func:`classutil.get_bound_subclass()` mechanism
  to subclass the :attr:`itemClass` and :attr:`itemSliceClass` automatically.
  This eliminates the use of :meth:`__getattr__` on item classes, replacing
  them with standard Python descriptors.  This greatly improves the modularity
  of the code.

* :class:`sqlgraph.SQLTable` now provides a complete and consistent dict-like
  interface, using UserDict.DictMixin.

* added optional *orderBy* argument to :class:`sqlgraph.SQLTable` constructor.
  Allows you to control the iteration order of the database objects.

* :class:`sqlgraph.SQLTable` row objects now support Python 2.6 style dir()
  introspection (i.e. they supply a __dir__ method).

* We have created a new recommended mechanism for persistent connections
  to relational databases: :class:`sqlgraph.DBServerInfo`. Unlike a relational
  database cursor or connection object, :class:`sqlgraph.DBServerInfo` objects
  are picklable, and can therefore be saved to ``worldbase``.

* The subclass 
  :class:`sqlgraph.SQLiteServerInfo` customizes this for persistent access to a
  sqlite database stored as a file.  

* added new classes :class:`sqlgraph.MapView` and :class:`GraphView`, to
  provide one-to-one mapping (dictionary interface) and many-to-many
  mapping (graph interface) objects that use a back-end SQL storage.

* :class:`sqlgraph.SQLTable` now by default provides a workaround for
  serious performance problems that our testing revealed in
  the ``MySQLdb`` Python DB API 2.0 module for accessing MySQL.
  Specifically, when using ``MySQLdb``, iteration over very
  large numbers of rows uses huge amounts of memory and
  can be very slow.  :class:`sqlgraph.SQLTable`
  uses a workaround that enables iteration over very large
  table sizes with little memory usage and good performance.


classutil
^^^^^^^^^

* established the renamed :func:`classutil.get_bound_subclass()`
  function as the standard mechanism for automatic subclassing of
  itemClass etc.

* We created a new class :class:`classutil.FilePopen`, as a variation on
  Python's standard subprocess.Popen class.  subprocess.Popen has problems
  with large data transfers and can hang (permanently blocked waiting for
  I/O with its subprocess).  To avoid these problems without requiring the
  use of threading (which creates its own problems), :class:`classutil.FilePopen`
  simply uses files instead of pipes for communicating with the subprocess.
  This code works not only on Python 2.4+ (which have the subprocess module),
  but in Python 2.3 (by supplying subprocess-like functionality).

* :class:`classutil.FilePopen` is now used throughout Pygr, to invoke 
  subprocesses in a safe, platform-independent manner. 

dbfile
^^^^^^

* subclassed shelve to provide a good __iter__ method.  The default
  Python shelve behavior was to load the *entire* index into memory
  as the first step for creating an iterator!

* ensured that attempting to access a closed shelve reports a clear error
  message even prior to Python 2.6.

General
^^^^^^^

* We now use the standard warnings and logger modules instead of printing
  error messages to stderr.

* Many, many bug fixes.  See the issue tracker for the most prominent...


Building Pygr
^^^^^^^^^^^^^

* The setup.py build script was completely refactored, to build
  in a platform-independent way.

* setup.py now works with either setuptools (if it is available) or distutils.
 
* It can thus automatically build eggs and rpm binary packages on UNIX
  platforms, and Windows binary installer packages.


Testing Pygr
^^^^^^^^^^^^

* The test system was completely refactored.

* The tests can be run either with unittest or nose.

* The customized testing framework protest.py is no longer used.

* Enormously increased the number of tests and test coverage of Pygr.
  New tests for all the new functionality.

* generalized the megatest scripts to be run anywhere.

Documentation
^^^^^^^^^^^^^

* converted the Pygr docs to Restructured Text and construction of
  multiple target formats using Sphinx.  In this regard, we are
  just following the lead of Python itself...

* many new tutorials!

