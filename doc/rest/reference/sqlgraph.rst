:mod:`sqlgraph` --- Relational database interfaces
==================================================

.. module:: sqlgraph
   :synopsis: Relational database interfaces.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>

This module provides back-end database access.

DBServerInfo
------------

This class provides a general, picklable object for connecting to 
a database server.  You instantiate it with the necessary arguments
for accessing a database server, then pass it as the *serverInfo* 
argument to any datbase table class.  You can then save these
database table classes to :mod:`worldbase`, and when retrieved
they will automatically reconnect to the database server.  Indeed,
you can save the :class:`DBServerInfo` object itself to :mod:`worldbase`
as a standard name (e.g. referring to UCSC's MySQL server).
Then any database table refering to this standard name could
automatically re-connect to a *local* copy of that server
when retrieved from :mod:`worldbase`.

A second advantage of :class:`DBServerInfo` over regular cursor
objects, is that it can create temporary cursor objects automatically when
needed.  This is crucial for guaranteeing query isolation for
long-lived iterator objects; otherwise Pygr is forced to 
load the entire set of keys into memory to protect against the possibility
that the user would issue another query during the lifetime of 
that iterator.

.. class:: DBServerInfo(moduleName='MySQLdb', serverSideCursors=False, blockIterators=True, *args, **kwargs)

   Base class for accessing different types of database servers.

   *moduleName* must be the name of a Python DB API 2.0 module.
   Currently only ``"MySQLdb"`` and ``"sqlite3"`` are supported.

   *args* and *kwargs* are simply passed to the module's ``connect()``
   function.

   *serverSideCursors*, *blockIterators*: for details, see
   `MySQLdb Large Table Performance`_.

.. class:: MySQLServerInfo(moduleName='MySQLdb', serverSideCursors=True, blockIterators=True, *args, **kwargs)

   Subclass of :class:`DBServerInfo` for accessing MySQL.

.. class:: SQLiteServerInfo(moduleName='MySQLdb', serverSideCursors=True, blockIterators=True, *args, **kwargs)

   Subclass of :class:`DBServerInfo` for accessing sqlite.
   This will work with the Python standard library module ``sqlite3``
   or external package ``pysqlite2``.


SQLTableBase
------------
The base class for :class:`SQLTable` and other variants below.
This class is derived from
the Python :class:`UserDict.DictMixin` class, so all standard methods of 
the Mapping protocol (i.e. dictionary) can be used.

SQLTable
--------
Provides a :class:`dict`-like interface to an SQL table.  It accepts
an identifier as a key, and returns a Python object representing
the corresponding row in the database.  Typically, these "row"
objects have an :attr:`id` attribute that represents the
primary key, and all column names in the SQL table can be
used as attribute names on the row object.

This class assumes that the database table has a primary key,
which is used as the key value for the dictionary.  For tables
with no primary key see other variants below.

.. class:: SQLTable(name, cursor=None, itemClass=None, attrAlias=None, clusterKey=None, createTable=None, graph=None, maxCache=None, arraysize=1024, itemSliceClass=None, dropIfExists=False, serverInfo=None, autoGC=True, orderBy=None, writeable=False, iterSQL=None, iterColumns=None, primaryKey=None, **kwargs)

   Open a connection to an SQL table specified by *name*.

   You should provide a *serverInfo* argument that provides a connection
   to the server.  See :class:`DBServerInfo` for details.

   DEPRECATED: You can supply a Python DB API *cursor* providing a connection
   to the database server.  If *cursor* is None, it will attempt
   to connect to a MySQL server using authentication information either
   from your the *name* string (treated as a whitespace separated
   list in the form *tablename* *host* *user* *passwd*;
   at least *tablename* and *host* must be present), or from your
   .my.cnf configuration file in the usual MySQL way (in which case only
   *tablename* needs to be specified).

   *itemClass* indicates
   the class that should be used for constructing item objects (representing
   individual rows in the database). *itemSliceClass* indicates the class
   used for instantiation slices of items (if appropriate).

   *createTable* if not None, must be an SQL statement for creating
   the desired table structure.

   *dropIfExists* if True, forces it to delete any existing table 
   of the same name prior to creating a new table.

   *attrAlias*, if provided, must be a dictionary whose keys are
   attribute names that should be bound to items from your database,
   and whose values are an SQL column name or SQL expression that should
   be used to obtain the value of the bound attribute.

   *clusterKey*, if provided, is a caching hint for speeding up
   database access by "clustering" queries to load an entire block
   of rows that share the same value of the specified *clusterKey* column.
   This caching hint is only used by the :class:`Clustered` SQLTable variants
   described in detail below.

   *autoGC* if True, makes it use a :class:`classutil.RecentValueDictionary`
   to implement a weakref-based cache, in which items are automatically
   flushed from the cache when no longer referenced by the user.

   *orderBy* if not None, must be an SQL ``ORDER BY`` clause to be used
   for determining the iteration order of keys from the database.  
   For example ``orderBy="ORDER BY seq_id"``.  You can also include
   ``GROUP BY`` clauses if you want iteration to eliminate redundant
   rows from the iteration, e.g. ``orderBy="GROUP BY source_id"``.

   For use with MySQL, if you provide *orderBy*, you must also
   provide *iterSQL* and *iterColumns*.  These parameters are required
   for a workaround that solves serious performance problems in
   the ``MySQLdb`` Python DB API 2.0 module for accessing MySQL.
   For details, see `MySQLdb Large Table Performance`_.

   *iterSQL* must provide the ``WHERE`` clause for the above algorithm.
   For example, if you were iterating on ``orderBy="ORDER BY seq_id"``,
   you would specify ``iterSQL="WHERE seq_id>%s"`` since ``seq_id``
   is the column on which the iteration results will be ordered.

   *iterColumns* must be a list of the column names to be filled into
   your *iterSQL* ``WHERE`` clause as its ``%s`` fields.  For the 
   example above, ``iterColumns=["seq_id"]``.

   *primaryKey*, if not None, specifies the column to use as a 
   primary key for looking up key values passed to this dictionary
   interface.  This is only needed either if the SQL table lacks
   a primary key (if it has a primary key, :class:`SQLTable` will
   discover that automatically), or if you wish to *override* the
   actual primary key provided by the SQL table.

   *maxCache*, if not None, specifies the maximum number of database
   objects to keep in the cache.  For large databases, this is an important
   parameter for ensuring that :class:`SQLTable` will not consume too much
   memory (e.g. if you iterate over all or a large fraction of the items
   in the database).

   *arraysize*: specifies the number of rows to be transfered from the
   database server in each ``cursor.fetchmany()`` operation.
   This can be important
   for speeding up data transfer from the database server.

   Additional *kwargs* are passed to :func:`get_name_cursor()` for
   obtaining a *serverInfo* if neither *serverInfo* or *cursor* are
   provided.


Memory-efficient Iteration
^^^^^^^^^^^^^^^^^^^^^^^^^^

:class:`SQLTable` and its variants follow a simple rule for controlling
how data is loaded into memory:

* :meth:`SQLTable.iteritems()` and :meth:`SQLTable.itervalues()`
  iterate over the row objects while keeping only a small number of them
  in memory at any time (controlled by *maxCache* and *arraysize*)

* :meth:`SQLTable.items()` and :meth:`SQLTable.values()`
  iterate over the row objects by first loading the entire table into 
  memory, in a single operation.

* :meth:`SQLTable.__iter__()` and :meth:`SQLTable.keys()` do not
  load any rows into memory.

For the most common usage,
iterating over the objects in the database, you should use the
iterator methods :meth:`SQLTable.iteritems()` 
(which yields tuples of (*id,obj*)), or :meth:`SQLTable.itervalues()` 
(which just yields each object).  These methods
use the parameters *maxCache* and *arraysize* to control the
size of caching and data transfer from the database server (see details above).
This allows you to keep tight control over the total memory usage of :class:`SQLTable`
when iterating over all the items in a very large database, and also to ensure
efficient data transfer using the Python DB API 2.0 :meth:`fetchmany()` method.

.. method:: SQLTable.iteritems()


.. method:: SQLTable.itervalues()

Iteration over Keys
^^^^^^^^^^^^^^^^^^^

If you iterate over IDs using :meth:`__iter__()` or :meth:`keys()`
(i.e. ``for id in mytable``), row objects are not pre-loaded into memory;
each object will be fetched individually when you try to access it
(e.g. ``obj=mytable[id]``).

.. method:: SQLTable.__iter__()

   Iterate over all IDs (primary key values) in the table,
   without loading the entire table into memory.

.. method:: SQLTable.keys()

   Obtain a list of all keys for the table (in a single query),
   without loading the entire table of row objects into memory.



Single-Pass Iteration
^^^^^^^^^^^^^^^^^^^^^

By contrast, if you call the table's
:meth:`SQLTable.items()` or :meth:`SQLTable.values()` method, it will load data for the entire table into
memory, since these methods actually require creating a list object
containing every object in the database.
These methods ensure very efficient data transfer from the database server
(using the :meth:`fetchall()` method), but can consume large amounts of
memory limited only by the size of your database!

.. method:: SQLTable.items()

   return a list of all (id,obj) pairs representing all data in the table,
   after first loading the entire table into memory.

.. method:: SQLTable.values()

   return a list of all obj representing each row in the table,
   after first loading the entire table into memory.

You can also force loading of the entire database directly:

.. method:: SQLTable.load(oclass=None)

   Load all data from the table, using *oclass* as the row object
   class if specified (otherwise use the oclass for this table).
   All rows are loaded from the database and saved as row objects
   in the Python dictionary of this class.



Obtaining or Creating Row Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Accessing individual objects by *id* also obeys the *maxCache*
caching limits:

.. method:: SQLTable.__getitem__(id)

   get the object whose primary key is *id*, and cache it in
   our local dictionary (so that subsequent requests will return the
   same Python object, immediately, with no need to re-run an SQL query).
   For non-caching versions of :class:`SQLTable`, see below.


.. method:: SQLTable.new(**columnSettings)

   creates a new row in the database, using the keyword arguments as column
   name-value pairs to save to that row.  Returns the new row object.

.. method:: SQLTable.objclass(itemClass)

   Specify a object class to use for creating new "row" objects.
   *itemClass* must accept a single argument, a tuple object representing
   a row in the database.

   Otherwise, the default *oclass* for SQLTable is
   the :class:`TupleO` class, which provides a named attribute interface
   to the tuple values representing the row.


.. method:: SQLTable.select(whereClause,params=None,oclass=None,selectCols='t1.*')

   Generate the list of objects that satisfy the *whereClause*
   via a SQL SELECT query.  This function is a generator, so you
   use it as an iterator.  *params* is passed to the
   cursor execute statement to allow additional control over
   the query.  *selectCols* allows you to control what subset of
   columns should actually be retrieved.


.. method:: SQLTable._attrSQL(attr)

   Get a string expression for accessing attribute *attr* in SQL.
   This might either simply be an alias to the corresponding column
   name in the SQL table, or possibly an SQL expression that computes
   the desired value, executed on the database server.




There are several variants of this class:

SQLTableClustered
-----------------
A subclass of :class:`SQLTable` that groups its retrieval
of data from the table (into its local dictionary, where it
is cached), into "clusters" of rows that share the same value of
a column specified by the *clusterKey* argument to the :class:`SQLTableBase`
constructor.  For data that naturally subdivide into large clusters,
this can speed up performance considerably.  If the clustering
closely mirrors how users are likely to access the data, this
performance gain will have relatively little cost in terms
of memory wasted on loading rows that the user will not need.

Note that iteration will by default be ordered by *clusterKey*.
You may override this by specifying your own *orderBy* argument.

Also provides a few convenience methods:

.. method:: clusterkeys()

   Return list of all cluster IDs (distinct values in the *clusterKey*
   field of the database).

.. method:: itercluster(cluster_id)

   Return list of all objects in the database that have a *clusterKey*
   value equal to *cluster_id*.



SQLTableNoCache
---------------
Provide on-the-fly access to rows in the database,
but never cache results.  Use this when memory constraints or other
considerations (for example, if the data in the database may change
during program execution, and you want to make sure your program
is always working with the latest version of the data)
make it undesirable to cache recently used row objects, as the
standard :class:`SQLTable` does.  Instead it returns (by default)
:class:`SQLRow` objects that simply provide an interface
to obtain desired data attributes via database SQL queries.
Of course this reduces performance; every attribute access
requires an SQL query.  You can customize the class used for
providing this interface by specifying a different *itemClass*
to the constructor.

SQLTableMultiNoCache
--------------------
Drops the assumption of a one-to-one
mapping between each key and a row object (i.e. removes the
assertion that the key is unique, a "primary key"), allowing
multiple row objects to be returned for a given key.  Therefore,
the standard :meth:`__getitem__` must act as a generator, returning
an iterator for one or more row object.  You must set a
:attr:`_distinct_key` attribute to inform it of which
column to use as the key for searching the database;
this defaults to "id".

MapView
-------

Provides a one-to-one mapping based on any SQL query that you provide.

.. class:: MapView(sourceDB, targetDB, viewSQL, cursor=None, serverInfo=None, inverseSQL=None)

   *sourceDB* must be the database whose objects will be used as keys
   to this mapping.

   *targetDB* must be the database whose objects will be targets of this
   mapping.

   *viewSQL* must be an SQL query string with a single replacement
   field (%s), into which the key ID will be inserted prior to 
   executing the query on the SQL server.  It must return a single
   ID of the target database object to which the key maps.

   *inverseSQL* if not None, must be an SQL query string for
   performing the inverse mapping.  It should follow the same basic
   format as *viewSQL*, with a single replacement
   field (%s), into which the key ID will be inserted prior to 
   executing the query on the SQL server.  It must return a single
   ID of the source database object to which the key maps.


SQLGraph
--------
Provides a graph interface to data stored in a table
in a relational database.  It follows the standard pygr
graph interface, i.e. it behaves like a dictionary whose
keys are *source nodes*, and whose associated
values are dictionaries whose keys are *target nodes*,
and whose associated values are *edges* between
a pair of nodes.  This class is a subclass of
:class:`SQLTableMultiNoCache`.  By default, it assumes that
the column names for source, target and edge IDs are simply
"source_id", "target_id", and "edge_id" respectively.
To use different column names, simply provide an *attrAlias*
dictionary to the constructor, e.g.::

   g = SQLGraph('YOURDB.YOURTABLE',attrAlias=dict(source_id='left_exon_form_id',
                                                  target_id='right_exon_form_id',
                                                  edge_id='splice_id'))

For good performance, the columns storing the source_id, target_id,
and edge_id should each be indexed.

.. class:: SQLGraph(name, cursor=None, itemClass=None, ...SQLTable args..., attrAlias=None, sourceDB=None, targetDB=None, edgeDB=None, simpleKeys=False, unpack_edge=None, defaultColumnType=int, columnAttrs=('source','target','edge'), createTable=None, edgeDictClass=None, graph=None, *args, **kwargs)

   *name* provides the name of the database table to use.

   You should provide a *serverInfo* argument that provides a connection
   to the server.  See :class:`DBServerInfo` for details.

   You can also specify any :class:`SQLTable` arguments to 
   customize the table storage.

   *attrAlias*, if provided, must be a dictionary that maps desired
   attribute names to actual column names in the SQL database.
   By default, :class:`SQLGraph` looks for ``source_id``, ``target_id``,
   and ``edge_id`` columns; you can remap these using *attrAlias*, 
   e.g. ``attrAlias=dict(source_id="mrna_id", target_id="exon_id", edge_id="exon_order")``

   *simpleKeys*, if True, indicates that the nodes and edge objects saved to
   the graph by the user should themselves be used as the internal representation
   to store in the SQL database table.  This usually makes sense only for strings
   and integers, which can be directly stored as columns in a relational database,
   whereas complex Python objects generally cannot be.  To use complex Python objects
   as nodes / edges for a :class:`SQLGraph`,
   use ``simpleKeys=False`` and the *sourceDB,targetDB,edgeDB* options below.

   *sourceDB*, if provided, must be a database container (dictionary interface) whose
   keys are source node IDs, and whose values are the associated node objects.
   If no *sourceDB* is provided, that implies *simpleKeys* = True.

   *targetDB*, if provided, must be a database container (dictionary interface) whose
   keys are target node IDs, and whose values are the associated node objects.

   *edgeDB*, if provided, must be a database container (dictionary interface) whose
   keys are edge IDs, and whose values are the associated edge objects.
   If None, then any value that you later attempt to save as an edge will be
   saved directly to the database, and must therefore match the
   data type of the corresponding column in your SQL table.

   *createTable* if not None, must be a dictionary supplying the SQL
   data type to use for each *columnAttrs* attribute (by
   default, ``source_id``, ``target_id``, and ``edge_id``).  Supplying
   *createTable* instructs :class:`SQLGraph` create a new table
   on the SQL server.

   *defaultColumnType* supplies the SQL data type to use for attributes
   not found in the *createTable* dictionary.

   *columnAttrs* supplies the list of attributes to store in each row.
   You need at least ``source`` and ``target``.

   *unpack_edge*, if not None, must be a callable function that takes a "packed"
   edge value and returns the corresponding edge object.

   DEPRECATED: *cursor*, if provided, should be a Python DB API 2.0 compliant cursor
   for connecting to the database.  If not provided, the constructor will attempt
   to connect automatically to the database using the MySQLdb module and
   your .my.cnf configuration file.

:class:`SQLGraph` follows a standard dictionary interface.  In addition
to standard dictionary methods, here are some additional method behaviors
specific to :class:`SQLGraph`.

.. method:: __iadd__(node)

   Add *node* to the graph, with no edges.  *node* must be
   an item of *sourceDB*, if that option was provided.


.. method:: __delitem__(node)

   Delete *node* from the graph, and its edges.  *node* must be a
   source node in the graph.  :meth:`__isub__` does exactly the same thing.


.. method:: __contains__(id)

   Test whether *id* exists as a source node in this graph.

.. method:: __cmp__(graph)

   Test whether *graph* matches this graph, by a node vs. node
   and edge vs. edge comparison.

.. method:: __invert__()

   Return an :class:`SQLGraph` instance representing the reverse
   directed graph (i.e. swap target nodes for source nodes).

.. method:: __len__()

   Get the number of source nodes in the graph.

.. method:: edges()

   Iterate over all edges in the graph, generating each as a tuple:
   *(sourcenode, targetnode, edge)*.  

.. method:: update(graph)

   add the nodes and edges of *graph* to this :class:`SQLGraph`.
   Analogous to Python ``dict.update()``.


SQLGraphClustered
-----------------
Provides a read-only graph interface with improved performance based on
using :class:`SQLTableClustered` as the interface to the database
table.  This has several implications: 1. the table should have
a primary key; 2. the table should have a *clusterKey*
column that provides the value for clustering rows in the table.
This class can offer much better performance than :class:`SQLGraph`
for several reasons: 1. it caches data so that subsequent requests
for the same node or edge will be immediate, with no need to query
the SQL database; 2. it employs clustering to group together
data retrieval of many rows at a time sharing the same cluster key
value, instead of one by one; 3. it provides a :meth:`load`
method for loading the entire graph into cache (local dictionary);
4. use of the :meth:`items` method and other "value iterator" methods
will automatically perform a load of the entire graph, so that
only a single database query is used for the entire dataset,
rather than a separate query for each row or cluster.

As for :class:`SQLTable`, getting a list of node IDs using
:meth:`__iter__` or :meth:`keys` does not force an automatic load of
the entire table into memory, but calling :meth:`items` or
other "value" list / iterator methods will.

.. class:: SQLGraphClustered(table,source_id='source_id',target_id='target_id',edge_id='edge_id',clusterKey=None,sourceDB=None,targetDB=None,edgeDB=None,simpleKeys=False,unpack_edge=None,**kwargs)

   Similar to the :class:`SQLTableBase`, but not exactly the same format.
   *table* can either be a string table name, or an actual
   :class:`SQLTableClustered` object.  You must provide a *clusterKey*
   value.  The *sourceDB,targetDB,edgeDB,simpleKeys,unpack_edges* optional
   arguments have the same meanings as for :class:`SQLGraph` (see above).


.. method:: load(l=None)

   Load all data from the table, and store in our local cache (a
   Python dictionary).  If *l* is not None, it provides a
   list of tuples obtained via the :meth:`select` method that
   should be added to the cache, instead of loading the entire
   database table.


.. method:: __contains__(id)

   Test whether *id* exists as a source node in this graph.


.. method:: __invert__()

   Return an :class:`SQLGraphClustered` instance representing the reverse
   directed graph (i.e. swap target nodes for source nodes).


TupleO
------
Default class for "row objects" returned by :class:`SQLTable`.
Provide attribute interface to a tuple.  To subclass this,
add an :attr:`_attrcol` attribute
that maps attribute names to tuple index values (integers).
Constructor takes a single tuple argument representing a
row in the database.

SQLRow
------
Default class for row objects from NoCache variants of SQLTable.
Provides transparent interface to a row in the database: attribute access
will be mapped to SELECT of the appropriate column, but data is not cached
on this object.  Constructor takes two arguments: a database table
object, and an identifier for this row.  Actual data requests will
be relayed by :class:`SQLRow` to the database table object.

MySQLdb Large Table Performance
-------------------------------

Our testing has encountered serious performance problems in
the ``MySQLdb`` Python DB API 2.0 module for accessing MySQL.
Specifically, when using ``MySQLdb``, iteration over very
large numbers of rows uses huge amounts of memory and
can be very slow. 

* Using default ``MySQLdb`` cursors, the
  initial ``cursor.execute("SELECT...")`` will actually copy
  all the rows into Python's memory, even though you have not
  yet instructed it to ``fetch`` a single row!  This can consume
  vast amounts of memory and crash Python. 

* Using ``MySQLdb`` 
  server side cursors, the initial ``SELECT`` and ``fetch`` of
  a small number of rows are fast, but any attempt to 
  ``cursor.close()`` or ``cursor.nextset()`` before fetching all
  the rows (e.g. if the user consumes only part of the iterator),
  causes the process to hang, consuming huger and huger amounts
  of memory.  (We don't know why).

Pygr uses a workaround that enables iteration over very large
table sizes with little memory usage and good performance.
We will refer to this work-around as the ``blockIterators`` 
algorithm:

* on the initial query , use ``SELECT ... LIMIT 1024`` to retrieve
  only a block of results (in this example, 1024 rows).  Record
  the value(s) from the last row retrieved.

* on subsequent queries, use
  ``SELECT ... WHERE some_id>last_value LIMIT 1024`` to get
  the next block of results.

* Lather, rinse, repeat until all rows exhausted or the user
  deletes the iterator.  As long as ``some_id`` is indexed,
  i.e. the ``WHERE`` can be executed in *O(log N)* time, 
  the total iteration will take *O(N log N)* time, and will
  take no more memory than is required to hold a small number of
  rows at a time (1024 in this example).

This workaround is used by default with ``MySQLdb``.  Pygr
provides three alternative iteration protocols:

* ``serverSideCursors=True, blockIterators=True``: this
  combines the blockIterators workaround with ``MySQLdb``
  server-side cursors to minimize memory usage.  Since
  blockIterators always fetchs all rows requested from
  its ``SELECT``, the server-side cursor problem described
  above does not occur.  This appears to have problems
  on Windows, and is not recommended, simply because
  ``MySQLdb`` server side cursors are not widely used
  in the community and may not be reliable.

* ``serverSideCursors=False, blockIterators=True``: 
  this again uses the blockIterator algorithm, but with a 
  regular ``MySQLdb`` cursor.
  This is the default iteration protocol for use with ``MySQLdb``.

* ``serverSideCursors=False, blockIterators=False``: 
  this reverts to a simple, standard approach (``SELECT``
  all rows, then repeatedly call ``fetchmany()``).
  This works fine for small tables, but will allocate
  huge amounts of RAM for large tables, even if you do
  not actually fetch any rows!  I.e. even just ``iter()``
  on ID values will use up huge amounts of memory!

