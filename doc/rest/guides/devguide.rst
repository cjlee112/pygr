Pygr Developer's Guide
======================

Working With Pygr
-----------------

Please see our developer tutorial, :doc:`../tutorials/develop`.


Some Pygr Philosophy
--------------------

Pygr attempts to provide a highly Pythonic interface to bioinformatics datatypes
such as sequence, alignments and databases.  This document explains the interfaces
for how different parts of Pygr fit together, for developers seeking to extend
Pygr's capabilities.  Overall, Pygr follows several principles:

* Pygr is Python + Databases: I want to unify the power and generality of
  Python's data models with the scalable principles of schema and data integrity
  that the database field has developed.  I will explain the database part of
  this in a moment; first, let's examine the Python data models that are central
  to Pygr:
  
* dictionary interfaces: Dictionaries (i.e. the Mapping Protocol) are
  the core of the Python language.  In Pygr, we use dictionary interfaces to
  represent database tables, mappings and graphs.  In relational databases
  (and indeed any kind of federated database architecture where data from one
  dataset need to be able to refer to specific items in another dataset),
  each item in a database ordinarily has a "primary key" that has a unique
  value for each item.  Python dictionaries mirror this behavior by associating
  each (unique) key value with a specific object.  Thus dictionaries are a
  natural interface to external databases.  However, the dictionary interface
  is also useful for representing entity-relationships, which can be one-to-one
  (i.e. ``y = m[x]``), many-to-many (i.e. ``for y in m[x]``), etc.  Pygr
  graph interfaces are simply two-level mappings (i.e. ``m[x][y] = edge``).
  
* sequence interfaces: One of the main features of sequences is that they
  are sliceable using integer number ranges (e.g. ``s[5:10]``).  Pygr uses
  sequence interfaces for both bio-sequence objects, intervals (slices) and
  annotations.
  
* pickling: Python included a powerful, elegant and general method for
  object persistence from very early in the language's history.  pygr.Data simply
  leverages this strong foundation to provide convenient data sharing of
  any picklable data.


Dictionary Interfaces
---------------------
Dictionary interfaces play a key role in Pygr modularization, because they
provide a clean, general interface that Python programmers intuitively
understand, hiding the complexities of interacting with a backend database,
so that user code can work transparently with *any* database that
follows this interface.

* identifier: one of the key principles of database
  design is that every item should have a unique identifier ("primary key").
  Identifiers are always basic data types such as integer or string, allowing
  them to act as a portable system of reference for different datasets to keep
  persistent references to each other (e.g. the identifier can be transmitted
  or stored by a relational database server or XMLRPC service)
  The most common usage is ``obj = m[k]`` which returns the object associated
  with key value ``k``.
  
* reverse mapping: one crucial operation is to obtain the identifier for
  a given object from the database.  The database therefore provides an
  inverse operator that returns the inverse mapping, i.e.
  ``k = (``\textasciitilde``m)[obj]``.
  
* Each database should have a :attr:`itemClass` attribute, that
  gives the class to be used for constructing an object to represent a
  database row (e.g. a sequence from a sequence database).
  This is used by pygr.Data to bind schema rules automatically
  to items from a given database.  Similarly, the :attr:`itemSliceClass` attribute
  gives the class to be used for constructing subslices of database row
  objects (e.g. sequence intervals).  Again, this is used for binding automatic
  schema rules.
  
* Caching: Pygr persistent database objects perform local caching of objects
  from the database that have been requested by the user.  This guarantees that
  different requests for the same identifier will return the same object.
  By default, Pygr database classes use a :class:`WeakValueDictionary`
  as the cache, so when a user drops all references to a given item,
  it will automatically be garbage-collected and eliminated from the cache.
  By convention, the cache for a database object is stored as its
  ``_weakValueDict`` attribute.
  
* iteration: Pygr follows a simple logic for allowing users to control
  how data (objects) are loaded into memory.  Iterating over identifiers
  (e.g. using __iter__() or keys()) simply retrieves the list of identifiers,
  but does not load the set of objects from the database.  Thus, the object
  associated with a specific identifier will only be loaded if the user
  explicitly requests it, e.g via ``m[k]``.  By contrast, iterating over
  items or values from the database (e.g. using items() or values()) signals
  to Pygr that the user intends to examine all objects in the database, so
  the entire dataset is automatically retrieved using a single query (to
  maximize performance), and kept in local cache as usual.  In this case
  a subsequent user request ``m[k]`` will simply be returned immediately
  from local cache.  Note that it is possible to customize exactly what
  columns from the database get actually loaded into memory
  by writing row object subclasses.
  
Databases and Schema
--------------------
First, let's define exactly what I mean by the word "database": a
set of data that share a common schema; in other words that each item
in the set participates in the same pattern of relations with other collections
of data.  Example: an *exon* always has the following attributes:

* it is part of a *gene*; this is a many-to-one relation.

* it is part of one or more *transcripts*; this is a many-to-many relation.

* it maps to a specific *interval on a genomic sequence*;
  this is a one-to-one relation.

* it can be connected to other exons by one or more directed edges, called
  *splices* or *introns*.  This is a many-to-many graph relation
  (because it also involves edge-relation objects).

Thus we can think of a database as a set of things that are functionally
equivalent in terms of having the same relations.

Second, let's define what I mean by the word "schema": first, the
list of *mappings* that items in a database participate in; second,
the *bindings* that attach these relations to items in this database.
A mapping is characterized by its *source* database, its *target*
database, and optionally its *edge* database whose items represent the
actual individual relations between a source-target pair of items.  In the example
above, the *splice* objects functioned as such "edge relation" objects.
A binding is typically an attribute name: i.e. for each item in the database,
that attribute name will yield the target that this item maps to according
to the mapping that is bound as this attribute.  For example, an exon object
might have a "gene" attribute that would yield the gene object that this
exon "is part of".

Subclass Binding
^^^^^^^^^^^^^^^^
Python has one "old-style" mechanism for customizing attribute access
(``__getattr__()``), and a "new-style" mechanism, called "descriptors".
Descriptors are modular -- each attribute is handled by a separate object
bound to the class -- whereas __getattr__() is not (a single super-function
handles all custom attribute requests... even worse, __setattr__() intercepts
ALL write requests for the object).  Pygr uses descriptors to implement
schema binding.  This has several pieces

* Subclassing: descriptors are bound to the *class*, not the instance
  object.  So if we want to bind descriptors for a specific object, we need to
  create a subclass.  Pygr.classutil.get_bound_subclass() does this for you.
  The current class is just subclassed, and any desired descriptors are bound
  to the subclass.
  
* :meth:`_init_subclass()`: if provided by the parent class,
  this classmethod will be called when
  the subclass is created, to let it do whatever it needs to initialize itself
  and its relation with its target database.  For example, when
  :class:`FileDBSequence`._init_subclass() is called, it initializes
  the sequence ID/length index that it uses for fast access to sequences
  stored in its packed format.  It also creates the seqInfoDict that its
  parent database object requires as a general interface for looking up
  information about any sequence.
  
* Binding: descriptors for all the relations we want are bound as
  attributes to the subclass.  This makes them appear on all instances of this
  subclass.
  
* Pygr.Data uses this for automatic schema binding.  SQLTable uses this
  for efficient attribute access on TupleO (values stored locally as a tuple)
  and SQLRow (all requests relayed as queries to the back-end database).
  
* The subclass pickles as its parent class, which when unpickled
  will be re-subclassed by get_bound_subclass() as usual.


Persistence
-----------
Python built in a clean, modular system for persistence from very early in its
history: pickling.  Pygr.Data is built on pickling.  To make your classes
picklable, you need to follow some simple guidelines.  Your class will fall
in one of several categories:

* Simple: if the information needed to "resurrect" your object from storage
  is nothing more than its attributes, and those attributes are picklable, you
  don't need to do anything.  Pickling will by default just pickle all the
  attributes, and restore them during unpickling.
  
* State: if your object needs control over what gets saved during pickling,
  it should define a :meth:`__getstate__()` method that returns just the
  data you want saved as the object's "state".  E.g. a database object might have a
  cursor object as an attribute, which can't be pickled.  Your db object must
  save "state information" sufficient for it to re-connect to the database server
  upon unpickling.  Pygr.classutil.standard_getstate() and standard_setstate()
  provide default Pygr behaviors (_pickleAttrs attribute controls list of attributes
  to pickle).
  
* Total control: if your object needs to determine what class it should
  become at the moment of unpickling, you need to provide a :meth:`__reduce__()`
  method.  NB: this is always needed if you subclass a built-in class like :class:`dict`.


Writing New Extensions
----------------------
There are several areas where it should be fairly straightforward
for a developer to extend Pygr functionality.

* Adding new resources to pygr.Data: you can load data using
  pygr's existing classes, then save them to pygr.Data for easy
  access by yourself or sharing with others worldwide.
  
* Creating an interface to existing databases: you can
  use Pygr's sqlgraph classes to model an existing database schema,
  then save it to pygr.Data for easy access from within Python
  or sharing with others.
  
* Writing sequence parsers: by supplying an appropriate parser,
  you can make Pygr sequence databases load from any sequence format you
  want.
  
* Writing alignment parsers: by suppyling an appropriate parser,
  you can make NLMSA alignment databases load from any alignment
  format.
  
* Writing new sequence database storage classes: for special
  applications like Solexa deep-sequencing, you could develop storage
  classes that are especially fast, efficient or scalable for very
  large datasets.  You only to write two capabilities: an index for
  looking up information about a sequence (e.g. its length or other
  info); an index for looking up the actual letter string for all
  or part of a specified sequence.


Writing Sequence Parsers
^^^^^^^^^^^^^^^^^^^^^^^^
By default, the :class:`SequenceFileDB` and related sequence
database classes accept a ``reader`` argument that allows
you to specify a parser function.  It will be called with
two arguments: ``reader(ifile, filename)``; and it should
act like a generator that yields one or more objects that
must each have the following attributes:

* id: the identifier of the sequence
* length: the length of the sequence
* sequence: the actual letter string for this sequence,
  as a single string (with no extraneous characters like carriage
  returns; just the sequence itself)

The ``reader()`` function should read the sequence format
from ``ifile``, but it should not close ``ifile``;
that is done by the function that calls it.

Writing Alignment Parsers
^^^^^^^^^^^^^^^^^^^^^^^^^
Pygr's alignment class, NLMSA, has fast functions in C for reading
multigenome alignment formats like MAF and axtnet.  If you want to
provide your own parser function for reading another format, you can
do so through the following arguments to the NLMSA constructor or
:meth:`add_aligned_intervals()` method.

* alignedIvals: an iterable that yields a series of tuples
  of aligned intervals, or alternatively a series of objects
  that each represent a pair of aligned intervals.
  If tuples are provided, each tuple is interpreted as a set of two
  or more intervals that should be stored as aligned.  Each interval
  must specify a sequence ID, start coordinate and end coordinate
  (following standard Python conventions), and optionally an
  orientation attribute.  Each interval
  can be specified as either a Python object with named attributes
  providing coordinates; or as a tuple.  For details of how to
  control this, see the alignedIvalsAttrs argument below.
  
* alignedIvalsSrc: the sequence database to look up the source
  interval from (the source interval is the first interval in any tuple).
  Each source interval ID will be looked up in the alignedIvalsSrc
  sequence database.
  
* alignedIvalsDest: the sequence database in which to look up destination
  intervals (i.e. the second (or later) intervals in each tuple).
  
* alignedIvalsAttrs: a dictionary specifying how to look up
  id and coordinate attributes from each interval "object".  If
  the object is a tuple, provide mappings to the numerical index
  of each attribute in the tuple, e.g.
  ``alignedIvalsAttrs=dict(id=0, start=1, stop=2, ori=3,
  idDest=0, startDest=1, stopDest=2, oriDest=3)``
  If the object has named attributes, provide mappings to the correct
  attribute names, e.g.
  ``alignedIvalsAttrs=dict(id='src_id', start='src_start',
                                    stop='src_end', ori='src_ori',
                                    idDest='dest_id', startDest='dest_start',
                                    stopDest='dest_end', oriDest='dest_ori')``
  The attribute names used for source vs. destination attributes are
  given different names so that they both be extracted from a single
  object if desired: id, start, stop, ori; idDest, startDest, stopDest, oriDest.

You can write your parser as a generator function, and simply pass its
return value (an iterator) as the ``alignedIvals`` argument.

If you pass these arguments to the NLMSA constructor, the aligned
intervals will be read into the NLMSA, and it will be immediately
initialized (via its build() method), so you can immediately begin
querying it.

If you pass these arguments to the NLMSA.add_aligned_intervals() method,
the intervals will simply be loaded into the NLMSA.  You can call
add_aligned_intervals() repeatedly, if needed.  Finally, you must
call the NLMSA.build() method to construct its indexes and ready it
for querying.

Writing New Sequence Storage Classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Sequence storage functionality is associated with a sequence class;
different sequence classes representing different types of storage
can be used with a generic sequence database class, such as
:class:`SequenceFileDB` (for storage in a local file).  A sequence
class needs to provide just three interfaces for a new kind of storage:

* seqInfoDict: a dictionary-like object that for each valid
  sequence ID returns an object with attributes providing information
  about that sequence.  This allows you, if you wish, to implement an
  efficient mechanism for retrieving information about a sequence
  that does not need to retrieve the sequence string itself.  Alternatively,
  if this doesn't provide any benefit for your specific storage application,
  you could simply use the sequence database itself as the seqInfoDict.
  Since each sequence object has named attributes describing it, the
  sequence object can act as its own "information object".  Regardless,
  this dictionary-like object should be saved as the seqInfoDict
  attribute on the sequence database object.
  
* strslice(seqID, start, stop): this method retrieves a specific
  interval of the sequence string.
  
* __len__(): implement this standard Python method to let users
  request the length of your sequence via ``len(s)``.


To initialize storage for a specific sequence database, write an
_init_subclass classmethod for your sequence class.  This will be
called by the sequence database constructor when it binds your
sequence class (see Subclass Binding, above).  This should either
initialize the storage (if being created for the first time), or
simply open access to the storage (if the storage on disk is already
initialized).  For an example, see seqdb.FileDBSequence.


Examples
--------

Example: SQLTable
^^^^^^^^^^^^^^^^^
A very common usage is to employ a dictionary interface to a relational
database table.  In this case the key value must be a valid identifier
in the database (primary key); a Python object representing that row in the database
will be returned.  The class to be used for constructing the "row object"
is controlled by setting the :attr:`itemClass` attribute.  The default
row class (TupleO) simply provides attributes that mirror the column names
in the database::

   seq_region = sqlgraph.SQLTable('homo_sapiens_core_47_36i.seq_region',
                                  cursor)

We can then request information about a specific sequence region, e.g.::

   sr = seq_region[143909]
   print sr.name, sr.coord_system_id


As a more sophisticated example, we can force rows from a specific table
to be interpreted as sequence objects::

   class EnsemblDNA(seqdb.DNASQLSequence):
       def __len__(self): # just speed optimization
           return self._select('length(sequence)') # SQL SELECT expression
   dna = sqlgraph.SQLTable('homo_sapiens_core_47_36i.dna', cursor,
                           itemClass=EnsemblDNA, attrAlias=dict(seq='sequence'))
   s = dna [143909] # get this sequence object
   print len(s) # 41877
   print str(s[:10]) # CACCCTGCCC

Note the use of the *attrAlias* to provide a dictionary for remapping
the actual column names used in the Ensembl database ("sequence") to the
canonical name expected by seqdb.DNASQLSequence ("seq").  Note also how
we introduce a custom method for calculating the sequence length entirely on
the server side, to avoid Pygr having to retrieve the sequence string just to
calculate its length.


Example: PrefixUnionDict
^^^^^^^^^^^^^^^^^^^^^^^^
Multigenome alignments pose a problem: instead of making references to
a set of sequences from a single database, they combine references to many
different databases each representing one genome.  How can this be handled
within the dictionary interface?  Simple: UCSC adds a prefix (representing the
"name" of the genome database to each sequence identifier, e.g. "hg18.chr1" is
sequence identifier "chr1" in database "hg18".  This can be considered an
identifier in a new "database" that is itself just a union of all the databases
that are included in the alignment.  Its job is to accept strings like "hg18.chr1"
as keys, then request the right identifier ("chr1") from the right database (hg18)
and return the resulting sequence object.
We construct it by supplying a dictionary of string prefixes to associate
with each sequence database as follows::

   db = PrefixUnionDict({'hg18':hg18, 'mm7':mm7})

where ``hg18`` is itself a sequence database that accepts string keys
(like "chr1") and returns the correspond sequence object.  Then we can
do things like::

   s = db['hg18.chr1']

Note that we will get different identifiers for s depending on whether
we ask db or hg18: \textasciitilde db[s] gives "hg18.chr1" whereas
\textasciitilde hg18[s] just gives "chr1", as it should.
\end{itemize}

Example: Ensembl SeqRegion Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Ensembl's annotation schema promulgates a single identifier space
(seq_region_id) that can refer to any database listed in the
coord_systems table.  This is analogous to the UCSC prefix union,
except that it uses an intermediary table seq_region that joins
seq_region_id to coord_system_id.

Once again, Pygr provides a simple interface as a dictionary, which
is itself initialized with a dictionary of {coord_system_id:seqDB}
pairs::

   seq_region = sqlgraph.SQLTable('homo_sapiens_core_47_36i.seq_region',
                                  cursor)
   hg18 = pygr.Data.Bio.Seq.Genome.HUMAN.hg18() # human genome
   srdb = SeqRegion(seq_region, {17:hg18}) # trivial example, only 1 genome

Now we can request seq_region_id values from ``srdb``, e.g.
``chr1 = srdb[226034]`` gets human chromosome 1.
Note that we will get different identifiers for chr1 depending on whether
we ask srdb or hg18: \textasciitilde srdb[chr1] gives 226034 whereas
\textasciitilde hg18[chr1] just gives "chr1", as it should.


Annotation Databases
^^^^^^^^^^^^^^^^^^^^
Pygr treats annotation as an intersection between two types of data:

* Slice database: a dictionary that takes annotation ID as a key,
  and returns an object that provides "slice information" for that annotation,
  consisting of sequenceID, start coordinate, stop coordinate, and orientation.
  
* Sequence database: a dictionary that takes a sequence ID as a key,
  and returns a sliceable sequence object.


It should be emphasized that you can use *any* dictionary-like object
as either the slice database or sequence database.  Examples include

* Python built-in :class:`dict`.
  
* Python persistent dictionary such as :mod:`shelve`, :mod:`anydbm` etc.
  
* Pygr classes that wrap such persistent dictionaries with convenient
  features, e.g. :class:`PicklableShelve` (which, unlike :mod:`shelve` can be
  pickled, allowing it to be stored in pygr.Data), :class:`IntShelve` (can accept
  integer keys, rather than just string keys like :mod:`shelve` etc.).
  
* Pygr sequence database such as :class:`BlastDB`.
  
* "wrapper" or "union" dictionary interfaces like :class:`PrefixUnionDict`
  or :class:`SeqRegion`.
  
* Pygr wrapper for a relational database table such as :class:`SQLTable`.


The AnnotationDB class supports
simple "aliasing" of attribute names from the database to the canonical
names expected by AnnotationDB, by supplying an *attrAliasDict* dictionary
to its constructor.  See the :class:`AnnotationDB` reference documentation for
details.  If more sophisticated transformations need to be performed
on the sliceDB data (e.g. mathematical functions), the best solution is to
use a custom class for the sliceDB.itemClass (i.e. the row object class),
with descriptors (also known as properties) to compute the desired attribute
values.

For example, to convert Ensembl annotations to standard Python zero-offset
coordinates (from the Ensembl coordinate system that starts at 1), we
can define a Python descriptor class, then bind it as the :attr:`start`
attribute for the row class, which is then supplied as the :attr:`itemClass`::

   class SeqRegionStartDescr(object):
       'converts seq_region_start to Python zero-offset coordinate system'
       def __get__(self, obj, objtype):
           return obj.seq_region_start - 1

   from pygr import sqlgraph

   class EnsemblRow(sqlgraph.TupleO): # TupleO is generic tuple with named attrs
       'use this for all Ensembl tables with seq_region_start'
       start = SeqRegionStartDescr()

   exonSliceDB = sqlgraph.SQLTable('homo_sapiens_core_47_36i.exon',
                                   cursor, itemClass=EnsemblRow)


