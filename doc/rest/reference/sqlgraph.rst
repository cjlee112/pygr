:mod:`sqlgraph` --- Relational database interfaces
==================================================

.. module:: sqlgraph
   :synopsis: Relational database interfaces.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>

This module provides back-end database access.

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

.. class:: SQLTable(name, cursor=None, itemClass=None, attrAlias=None, clusterKey=None,maxCache=None, arraysize=1024)

   Open a connection to the existing SQL table specified by *name*.
   You can supply a Python DB API *cursor* providing a connection
   to the database server.  If *cursor* is None, it will attempt
   to connect to a MySQL server using authentication information either
   from your the *name* string (treated as a whitespace separated
   list in the form *tablename* *host* *user* *passwd*;
   at least *tablename* and *host* must be present), or from your
   .my.cnf configuration file in the usual MySQL way (in which case only
   *tablename* needs to be specified).

   *itemClass* indicates
   the class that should be used for constructing item objects (representing
   individual rows in the database).

   *attrAlias*, if provided, must be a dictionary whose keys are
   attribute names that should be bound to items from your database,
   and whose values are an SQL column name or SQL expression that should
   be used to obtain the value of the bound attribute.

   *clusterKey*, if provided, is a caching hint for speeding up
   database access by "clustering" queries to load an entire block
   of rows that share the same value of the specified *clusterKey* column.
   This caching hint is only used by the :class:`Clustered` SQLTable variants
   described in detail below.

   *maxCache*, if not None, specifies the maximum number of database
   objects to keep in the cache.  For large databases, this is an important
   parameter for ensuring that :class:`SQLTable` will not consume too much
   memory (e.g. if you iterate over all or a large fraction of the items
   in the database).

   *arraysize*: specifies the number of rows to be transfered from the
   database server in each cursor.fetchmany() operation.  This can be important
   for speeding up data transfer from the database server.



This class and its variants follow a simple rule for controlling
how data is loaded into memory.  For the most common usage,
iterating over the objects in the database, you should use the
iterator methods :meth:`iteritems()` (which yields tuples of (*id,obj*)),
or :meth:`itervalues()` (which just yields each object).  These methods
use the parameters *maxCache* and *arraysize* to control the
size of caching and data transfer from the database server (see details above).
This allows you to keep tight control over the total memory usage of :class:`SQLTable`
when iterating over all the items in a very large database, and also to ensure
efficient data transfer using the Python DB API 2.0 :meth:`fetchmany()` method.

.. method:: iteritems()


.. method:: itervalues()



By contrast, if you call the table's
:meth:`items()` or :meth:`values()` method, it will load data for the entire table into
memory, since these methods actually require creating a list object
containing every object in the database.
These methods ensure very efficient data transfer from the database server
(using the :meth:`fetchall()` method), but can consume large amounts of
memory limited only by the size of your database!

.. method:: items()

   return a list of all (id,obj) pairs representing all data in the table,
   after first loading the entire table into memory.

.. method:: values()

   return a list of all obj representing each row in the table,
   after first loading the entire table into memory.


Finally, if you iterate over IDs using :meth:`__iter__()` or :meth:`keys()`
(i.e. ``for id in mytable``), data is not pre-loaded into memory;
each object will be fetched individually when you try to access it
(e.g. ``obj=mytable[id]``).

.. method:: __iter__()

   Iterate over all IDs (primary key values) in the table,
   without loading the entire table into memory.


Accessing individual objects by *id* also obeys the *maxCache*
caching limits:

.. method:: __getitem__(id)

   get the object whose primary key is *id*, and cache it in
   our local dictionary (so that subsequent requests will return the
   same Python object, immediately, with no need to re-run an SQL query).
   For non-caching versions of :class:`SQLTable`, see below.


You can also force loading of the entire database directly:

.. method:: load(oclass=None)

   Load all data from the table, using *oclass* as the row object
   class if specified (otherwise use the oclass for this table).
   All rows are loaded from the database and saved as row objects
   in the Python dictionary of this class.


.. method:: objclass(itemClass)

   Specify a object class to use for creating new "row" objects.
   *itemClass* must accept a single argument, a tuple object representing
   a row in the database.

   Otherwise, the default *oclass* for SQLTable is
   the :class:`TupleO` class, which provides a named attribute interface
   to the tuple values representing the row.


.. method:: select(whereClause,params=None,oclass=None,selectCols='t1.*')

   Generate the list of objects that satisfy the *whereClause*
   via a SQL SELECT query.  This function is a generator, so you
   use it as an iterator.  *params* is passed to the
   cursor execute statement to allow additional control over
   the query.  *selectCols* allows you to control what subset of
   columns should actually be retrieved.


.. method:: _attrSQL(attr)

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

.. class:: SQLGraph(name,cursor=None,itemClass=None,attrAlias=None,sourceDB=None,targetDB=None,edgeDB=None,simpleKeys=False,unpack_edge=None,**kwargs)

   *name* provides the name of the database table to use.

   *cursor*, if provided, should be a Python DB API 2.0 compliant cursor
   for connecting to the database.  If not provided, the constructor will attempt
   to connect automatically to the database using the MySQLdb module and
   your .my.cnf configuration file.

   *attrAlias*, if provided, must be a dictionary that maps desired
   attribute names to actual column names in the SQL database.

   *simpleKeys*, if True, indicates that the nodes and edge objects saved to
   the graph by the user should themselves be used as the internal representation
   to store in the SQL database table.  This usually makes sense only for strings
   and integers, which can be directly stored as columns in a relational database,
   whereas complex Python objects generally cannot be.  To use complex Python objects
   as nodes / edges for a SQLGraph, use the *sourceDB,targetDB,edgeDB* options below.

   *sourceDB*, if provided, must be a database container (dictionary interface) whose
   keys are source node IDs, and whose values are the associated node objects.
   If no *sourceDB* is provided, that implies *simpleKeys*=True.

   *targetDB*, if provided, must be a database container (dictionary interface) whose
   keys are target node IDs, and whose values are the associated node objects.

   *edgeDB*, if provided, must be a database container (dictionary interface) whose
   keys are edge IDs, and whose values are the associated edge objects.

   *unpack_edge*, if not None, must be a callable function that takes a "packed"
   edge value and returns the corresponding edge object.


.. method:: __iadd__(node)

   Add *node* to the graph, with no edges.  *node* must be
   an item of *sourceDB*, if that option was provided.


.. method:: __delitem__(node)

   Delete *node* from the graph, and its edges.  *node* must be a
   source node in the graph.  :meth:`__isub__` does exactly the same thing.


.. method:: __contains__(id)

   Test whether *id* exists as a source node in this graph.


.. method:: __invert__()

   Return an :class:`SQLGraph` instance representing the reverse
   directed graph (i.e. swap target nodes for source nodes).


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
