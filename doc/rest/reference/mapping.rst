:mod:`mapping` --- Basic graph database and query interfaces
============================================================

.. module:: mapping
   :synopsis: Basic graph database interfaces.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>

The Pygr graph model
--------------------
The basic idea of Pygr is that all Python data can be viewed as a graph whose nodes are objects and whose edges are object relations (in Python, references from one object to another).  This has a number of advantages.

   1. All data in a Python program become a database  that can be queried through simple but general graph query tools.  In many cases the need to write new code for some task can be replaced by a database query.

   2. Graph databases are more general and flexible in terms of what they can represent and query than relational databases, which is very important for complex bioinformatics data.

   3. Indeed, in Pygr, a query is itself just a graph that can be stored and queried in a database, opening paths to automated query construction.

   4. Pygr graphs are fully indexed, making queries about edge relationships (which are often unacceptably slow in relational databases) fast.

   5. The interface can be very simple and pythonic: it's just a Mapping.  In Python "everything is a dictionary", also known as "the Mapping protocol": a dictionary maps some set of inputs to some set of outputs. e.g. m[a]=b maps a onto b, as a unique relation.  In Pygr, if we want to be able to map a node to multiple target nodes (i.e. allow it to have multiple edges), we simply add another layer of mapping: m[a][b]=edgeInfo (where edgeInfo is optional edge info.)

Examples of the Pygr syntax::

   graph += node1 # ADD node1 TO graph
   graph[node1] += node2 # ADD AN EDGE FROM node1 TO node2
   graph[node1][node2] = edge_info # ADD AN EDGE WITH ASSOCIATED edge_info
   # ADD SCHEMA BINDING WITH graph[node] BOUND AS node.attr
   setschema(node,attr,graph)
   # SEARCH graph FOR SUBGRAPH {1->2; 1->3; 2->3},
   # I.E. EXONSKIP, WHERE THE SPLICE FROM 2 -> 3 HAS ATTRIBUTE type 'U11/U12'
   for m in GraphQuery(graph,{1:{2:None,3:None},\
                      2:{3:dict(filter=lambda edge,**kwargs:edge.type=='U11/U12')},\
                      3:{}}):
       print m[1].id,m[2].id,m[1,2].id


Let's examine these examples one by one:

  
* adding a node to a graph is distinct from creating edges between it and other nodes.  The graph+=node notation simply adds node to the graph, initially with no edges to other nodes.
  
* A similar syntax (graph[node1]+=node2) can be used to add an edge between two nodes, but with no edge information.  In this case the edge information stored for this relation is simply the Python None value.  Note that in Pygr the default type of graph has directed edges; that is a->b does not imply b->a.  In the default dictGraph graph class, these are two distinct edges that would have to be added separately if you truly want to have an edge going both from a to b and from b to a.
  
* To add an edge between two nodes with edge information, use the graph[node1][node2]=edge_info syntax.
  
* You can bind an object attribute to a graph, using setschema(obj,attr,graph).  This acts like Python's built-in setattr(obj,attr,value), but instead of obj.attr simply storing the specified value, it is bound to the graph so that obj.attr is equivalent to graph[obj].  Both syntaxes are interchangeable and can be mixed in different pieces of code accessing the same object.
  
* Since Pygr adopts the Mapping protocol as its model for storing graphs, you can create graphs simply by creating Python dict objects e.g. {foo:bar}.  In this example we construct a query graph whose "nodes" are just the integers 1, 2, and 3.  Since any kind of object is a valid key in Python mappings, they can therefore also be used as "nodes" in a Pygr graph.  This query graph illustrates a few simple principles:
  
* a Pygr graph is just a two-level Python mapping.  For example, {1:{2,None}} is a graph with a single edge from 1 to 2, with no edge information.  Pygr graphs can have multiple edges from or to a given node.
  
* edge information in a query graph can be used to specify extra query arguments, again in the form of a Python dictionary.  This dictionary is interpreted as a set of "named arguments" to be used by the GraphQuery search method.  For example, a filter argument is interpreted as a callable function that is passed a set of named arguments describing the current edge / node matching being tested, and whose return value (True or False) will determine whether this edge "matches" our query graph.  In this example, we used it to check whether the edge.type attribute is "U11/U12" (an unusual type of splicing in gene structure graphs).
  
* Graph query in Pygr simply means finding a subgraph of the datagraph that has node-to-node match to the edge structure given in the query graph.  In this example it is a simple exon-skip structure (3 exons, one of which can either be included or skipped).  The GraphQuery class provides a general mechanism for performing graph queries on any Python data (see below for full details).  It can be used as an iterator that will return all matches to the query (if any).
  
* Matches are themselves returned as a mapping of nodes and edges of the query graph (in this example, its nodes are the integers 1, 2 and 3) onto nodes and edges of the data graph.  In this example the match is returned as m, so m[1] is the node in the data graph corresponding to node 1 in the query graph.  This example assumes that object has an id attribute, which is printed out.  To refer to an edge, just use a tuple corresponding to a pair of nodes in the query graph.  In this example, 1,2 refers to the edge from node 1 to node 2 in the query graph, so m[1,2] is the edge in data graph between nodes m[1] and m[2].  This example also attempts to print an id attribute from that edge object.
  
* Note on current behavior: currently, GraphQuery will throw a :exc:`KeyError` exception if it tries to search for a query node in the query graph and does not find it.  That's why we have to add the "node with no edges" entry 3:{} for node 3.  This will probably be addressed in the future, since this seems like a potential source of annoying unexpected behaviors.
  
* ``for node in graph``: iterator method returns all nodes in the graph; you could also use graph.items() to get node,dictEdge pairs, etc.
  
* ``for node in graph[node]``:  iterator method returns all nodes that are targets of edges originating at node.  Again, you could use graph[node].items() to get node,edgeInfo pairs.  Note: if node is not in graph, this will throw a :exc:`KeyError` exception just like any regular Python dict.
  
* ``if node in graph``:  :meth:`__contains__` method checks whether node is present in the graph, using dict indexing.
  
* ``if node2 in graph[node1]``:  test whether node1 has an edge to node2.  Again, if node1 isn't in graph, this will throw a :exc:`KeyError` exception.
  


Directionality and Reverse Traversal
------------------------------------

Note that dictGraph stores directed edges, that is, a->b does not imply b->a; those are two distinct edges that would have to be added separately if you want an edge going both directions.  Moreover, the current implementation of dictGraph does not provide a mechanism for traveling an edge backwards.  To do so with algorithmic efficiency requires storing each edge twice: once in a forward index and once in a reverse index.  Since that doubles the memory requirements for storing a graph, the default dictGraph class does not do this.  If you want such a "forward-backwards" graph, use the dictGraphFB subclass that stores both forwad and reverse indexes, and supports the inverse operator ($\sim$).  $\sim$ graph gets the reverse mapping, e.g. ($\sim$ graph)[node2] corresponds to the set of nodes that have edges to node2.  This area of the code hasn't been tested much yet.

Graph
-----
This class provides a graph interface that can work with external storage
typically, a BerkeleyDB file, based on storing node ID and
edgeID values in the external storage instead of the python objects themselves.

.. class:: Graph(saveDict=None, dictClass=dict, writeNow=False, filename=None, sourceDB=None, targetDB=None, edgeDB=None, intKeys=False, simpleKeys=False, unpack_edge=None, **kwargs)

   *filename*, if provided, gives a path to a BerkeleyDB file to use as the
   storage for the graph.  If the file does not exist, it will be created automatically.
   If the ``intKeys=True`` option is provided, this will be an :class:`IntShelve`,
   which allows the use of :class:`int` values as keys.  Otherwise a regular Python
   :class:`shelve` will be used (via the :class:`PicklableShelve` class),
   which only allows string keys.  Note that in this case you *must*
   call the Graph's :meth:`close()` method when you are done adding nodes / edges,
   to ensure that all the data is written to disk (unless you are using the
   ``writeNow=True`` option, see below).

   The *writeNow*=True option makes all
   writing operations atomic; i.e. the shelve file is opened read-only, and
   any attempt to write a single edge will re-open in write mode, save the data,
   and immediately close it, then re-open it in read-only mode.  This minimizes
   the probability that multiple processes simultaneously accessing the graph
   database will over-write each others' data.  Note: if you leave this option False,
   and write data to the graph, you *must* call the :meth:`close()` method
   once you have finished writing data to the graph, as described below.

   *saveDict*, if provided, must be a graph-style interface that stores the graph
   purely in terms of node ID and edge ID values.  This could be an :class:`IntShelve`,
   :class:`PicklableShelve` or dict instance, for example.  If None provided,
   the constructor will create storage for you using the *dictClass* class, passing
   on *kwargs* to its constructor.

   *simpleKeys*, if True, indicates that the nodes and edge objects saved to
   the graph by the user should themselves be used as the internal representation
   to store in the graph database file.  This usually makes sense only for strings
   and integers, which can be directly stored as keys in a BerkeleyDB (Python shelve),
   whereas complex Python objects generally cannot be.  To use complex Python objects
   as nodes / edges for a Graph, use the *sourceDB,targetDB,edgeDB* options below.

   *sourceDB*, if provided, must be a database container (dictionary interface) whose
   keys are source node IDs, and whose values are the associated node objects.
   If no *sourceDB* is provided, that implies ``simpleKey=True``.

   *targetDB*, if provided, must be a database container (dictionary interface) whose
   keys are target node IDs, and whose values are the associated node objects.

   *edgeDB*, if provided, must be a database container (dictionary interface) whose
   keys are edge IDs, and whose values are the associated edge objects.


.. method:: Graph.__iadd__(node)

   Add *node* to the graph, with no edges.  *node* must be an
   item of *sourceDB*.


.. method:: Graph.__delitem__(node)

   Delete *node* from the graph, and its edges.  *node* must be a
   source node in the graph.  :meth:`__isub__` does exactly the same thing.


.. method:: Graph.close()

   If you chose to use a Python :mod:`shelve` as the actual storage, you used
   the default setting of *writeNow*``=False``, and you
   wrote data to the graph, then you *must* call the :class:`Graph` object's
   :meth:`close()` method to finalize writing to the disk of any data that may
   be pending, once you have finished writing data to the graph.  Failure to do
   so may leave the shelve index file in an incomplete and corrupted state.

.. attribute:: edges

   provides an interface to iterating
   over or querying its edge dictionary.

dictGraph
---------

.. class:: dictGraph(schema=None, domain=None, range=None)

   Pygr's in-memory graph class.  For persistent
   graph storage and query (e.g. stored in a relational database table
   or BerkeleyDB file), see the :class:`Graph` class above.

   This class provides all the standard behaviors described above.  The current reference implementation uses standard Python dict objects to store the graph.  All the usual Mapping protocol methods can be used on dictGraph objects (top-level interface, in the examples above graph) and dictEdge objects (second-level interface; in the examples above graph[node]).

Collection
----------

Provides a :class:`dict`-like container that can be directly saved as a
container in :mod:`worldbase`.  Ordinary :class:`dict` instances cannot be
conveniently saved as worldbase resources, because they do not allow
attributes to be saved (which is required for storing worldbase information
like _persistent_id and itemClass), and because older versions of Python
have a bug that affects pickling of dicts with cyclic references (i.e. contents
that refer to the container).  :class:`Collection` provides a drop-in
substitute that uses :class:`dict` or a Python :class:`shelve`
as its internal storage, and provides
a full dict-like interface externally.  It takes several arguments:

.. class:: Collection(saveDict=None, dictClass=dict, fileName=None, mode=None, writeback=False, **kwargs)

   *saveDict*, if not None, is the internal mapping to use as our storage.

   *filename*: if provided, is a file path to a shelve (BerkeleyDB) file to
   store the data in.  NOTE: if you add data to a Collection stored in such a file,
   you *must* call the Collection's :meth:`close()` method to ensure
   that all the data will be saved to the Python shelve.  Otherwise, the
   Python shelve file might be left in an incomplete state.
   NOTE: opening a collection with the *filename* option will cause
   it to use the PicklableShelve or IntShelve class for the Collection.

   *mode* is passed to the Python :meth:`shelve.open()` function
   to control whether *filename* is opened in read, write or create mode;
   see the Python :mod:`shelve` module documentation for details.  If *mode*
   is None, it will first try to open the shelve in mode 'r' (read-only),
   but if the file is missing, will open it in mode 'c' (create).

   *writeback* is passed to the Python :meth:`shelve.open()` function
   to control the saving of data to the shelve.
   See the Python :mod:`shelve` module documentation for details.
   The default *writeback=True* setting can consume large amounts of
   memory if you are writing a lot of data to the shelve.  To avoid
   this problem, use *writeback=False*; note that this means updates
   to the shelve will only be saved when you explicitly set an item
   in the Collection (e.g. ``collection[k] = v``; specifically, if
   ``v`` is a mutable object, subsequently changing the contents of
   ``v`` will not automatically update the :mod:`shelve`, whereas
   it would be with *writeback=True*).

   *dictClass*: if provided, is the class to use for storage of the dict data.

   *itemClass*: class to use for storing the values in the dictionary.

   For example::

      ens_genes = mapping.Collection(itemClass=Transcript) # DICTIONARY OF GENES
      ens_genes[gene_id] = gene

   Pygr generally needs to know the :class:`itemClass` of items stored
   inside a resource, so that it can add shadow attributes (by adding properties,
   directly to the itemClass).

.. method:: Collection.close()

   You must call this method to ensure that any data added to the Collection
   will be written to its Python shelve file on disk.
   This method is irrelevant, but harmless,
   if you are instead using an in-memory dictionary as storage.


Mapping
-------
This class provides dict-like class suitable for persistent usages.
It extracts ID values from
keys and values passed to it, and saves these IDs into its internal dictionary
instead of the actual objects.  Thus, the external interface is objects,
but the internal storage is ID values.  This allows the mapping to be stored
persistently (i.e. pickled) separately from the objects which it maps,
because only IDs are stored in the :class:`Mapping`.

You can use any object that obeys the
Python mapping protocol (e.g. :class:`dict`, or Python :mod:`shelve`)
as the internal storage.  :class:`Mapping` behaves exactly like a standard
Python dictionary, providing all the standard methods of the Mapping Protocol.

.. class:: Mapping(sourceDB, targetDB, saveDict=None, IDAttr='id', targetIDAttr='id', itemAttr=None, multiValue=False, inverseAttr=None,filename=None,dictClass=None,mode=None)

   Initializes a mapping between items of *sourceDB* and items of *targetDB*.

   *sourceDB*: container whose items will serve as keys for this Mapping.
   i.e. *sourceDB* must be a dictionary that maps key ID values to key objects.

   *targetDB*: container whose items will serve as values of this Mapping.
   i.e. *targetDB* must be a dictionary that maps value IDs to value objects.

   *saveDict*, if not None, is the internal mapping to use as our storage.
   If None, attempts to open or create a suitable storage for you.
   See also the *filename*, *dictClass* and *mode* arguments.
   If none of these arguments are provided, a standard Python dictionary will be used.

   *IDAttr*: attribute name to obtain an ID from a key object.

   *targetIDAttr*: attribute name to obtain an ID from a value object.

   *itemAttr*, if not None, the attribute to obtain target (value) ID
   from an internal storage value

   *multiValue*: if True, treat each value as a list of values, i.e. this
   Mapping will serve as a one-to-many mapping from *sourceDB* to *targetDB*.

   *inverseAttr*, if not None, attribute name to obtain a source ID from
   a value object.

   *filename*: if not None, is a file path to a shelve (BerkeleyDB) file to
   store the data in.

   NOTE: if you add data to a Mapping stored in such a disk file,
   you *must* call the Mapping's :meth:`close()` method to ensure
   that all the data will be saved to the Python shelve.  Otherwise, the
   Python shelve file might be left in an incomplete state.

   *mode*: if not None, specifies how the shelve file should be opened:
   'r' (read-only), 'c' (create), 'w' (read/write).  For more details see the
   Python Library :mod:`shelve` documentation.

   *dictClass*: if not None, is the class to use for storage of the dict data.


.. method:: Mapping.close()

   You must call this method to ensure that any data added to the Mapping
   will be written to its Python shelve file on disk.
   This method is irrelevant, but harmless,
   if you are instead using an in-memory dictionary as storage.




Here's an example usage::

   gene_exons = Mapping(ens_genes, exon_db, multiValue=True, inverseAttr='transcript_id')
   for exon in exon_db:
       gene = ens_genes[exon.transcript_id]
       exons = gene_exons.get(gene, [])
       exons.append(exon)
       gene_exons[gene] = exons # save expanded exon mapping list
   # save to worldbase, and create genes -> exons schema relation
   worldbase.Bio.Titus.Test1.GeneExons = gene_exons
   worldbase.schema.Bio.Titus.Test1.GeneExons = \
        metabase.OneToManyRelation(ens_genes,exon_db,bindAttrs=('exons','gene'))
   worldbase.commit() # save all pending data and schema to metabase


PicklableShelve
---------------
Subclass of :class:`Collection` that
provides an interface to the Python :mod:`shelve` persistent dictionary
storage, as an object that can be pickled; unpickling the object will
correctly re-open the associated :mod:`shelve` file.  One important
difference is that it allows you to specify both the mode flag for opening
the shelve *now* and the mode flag for re-opening the shelve in the
future whenever this object is unpickled.

Note also that since :class:`PicklableShelve` is designed to be pickled
and potentially shared among users, it automatically supports re-opening in
read-only mode.  That is, if re-opening in read/write mode fails, it will
automatically re-open in read-only mode, and prints a warning message to the
user.  This feature avoids permissions problems that commonly occur, e.g.
if one user builds a PicklableShelve, and shares that to other users, they
typically will not have write-permission to the file, and could only access
it in read-only mode.

.. class:: PicklableShelve(filename,mode=None,writeback=False,unpicklingMode=False,verbose=True,**kwargs)

   Ideally, you
   should specify a TWO letter mode string: the first letter to
   indicate what mode the shelve should be initially opened in, and
   the second to indicate the mode to open the shelve during unpickling.
   e.g. ``mode='nr'``: to create an empty shelve (writable),
   which in future will be re-opened read-only.

   Single letter *mode* values such as 'n' (create empty file), 'c'
   (open read-write, but create if missing), and 'w' (open read-write)
   are permitted, but will default to read-only for re-opening the file
   in *future* unpickling operations.  Use a two-letter *mode*
   if you want the file re-opened in read-write mode; e.g. ``mode='nw'``
   to create an empty file now and re-open it in read-write mode in future
   unpickling operations.

   *mode=None* makes it first attempt to open read-only, but if the file
   does not exist will create it using mode 'c'.  Note that it will also
   follow this behavior pattern in future unpickling operations (i.e. if
   the file is missing, it will be silently re-created, empty, in read-write mode).
   This is appropriate if you want to be able to "empty the database" by
   simply deleting the shelve file manually.  This behavior is different from
   the 'nr' mode, which will create the shelve file empty *now*, but
   will raise an exception if it is missing when future unpickling operations
   attempt to re-open it read-only.


.. method:: PicklableShelve.reopen(mode='r')

   Re-open the shelve file in the specified *mode* and also save this
   *mode* as the mode for re-opening the shelve file in future unpickling
   operations.


.. method:: PicklableShelve.close()

   After saving data into a :class:`PicklableShelve` you must "commit" the transaction
   by calling its :meth:`close()` method, which will ensure that all pending data
   will be written to its shelve file.


IntShelve
---------
Subclass of PicklableShelve,
provides an interface to the Python :mod:`shelve` persistent dictionary
storage, that can accept :class:`int` values as keys.

.. class:: IntShelve(filename,mode=None,writeback=False,unpicklingMode=False,verbose=True,**kwargs)

   Open the specified :mod:`shelve` BerkeleyDB file, using the specified
   mode.


.. method:: IntShelve.close()

   After saving data into a :class:`IntShelve` you must "commit" the transaction
   by calling its :meth:`close()` method, which will ensure that all pending data
   will be written to its shelve file.

In other respects the :class:`IntShelve` behaves like a regular shelve
(dictionary interface).




%Schema: binding object attributes to graphs
--------------------------------------------

%The goal of Pygr is to provide a single consistent model for working with data explicitly modeled as graphs (i.e. dictGraph-like objects) and standard Python objects that were not originally designed to be queried (or thought of) as a "graph".  Since Python uses the Mapping concept throughout the language and object model, and provides introspection, there is no reason why Pygr can't work with both kinds of data transparently.  One mechanism for making this idea explicit is the idea of binding an object attribute to a graph, via the new method we've called setschema(obj,attr,graph).  The idea here is that once you bind an object attribute to a graph, the two different data models obj.attr (object model) or graph[obj] (graph model) are made equivalent and interchangeable.  Operating on one affects the other and vice versa; they are two ways of referring to the same relation.  This concept can be applied at several different levels

%\begin{itemize}
%\item
%individual objects: just like getattr() and setattr(), you can apply schema methods to individual objects: getschema(obj,attr) (returns the bound graph) or setschema(obj,attr,graph) (binds the object attribute to the graph).

%\item
%all instances of a class: you can bind specific attributes of a given class to a graph using the following class attribute syntax:

%\end{itemize}
%@INDENT:   :\end{verbatim}
%class ExonForm(object): # ADD ATTRIBUTES STORING SCHEMA INFO
%    __class_schema__=SchemaDict(((spliceGraph,'next'),(alt5Graph,'alt5'),(alt3Graph,'alt3')))
%\end{verbatim}
%
%In this class we bound the next attribute to spliceGraph, alt5 attribute to alt5Graph, and alt3 attribute to alt3Graph.  That means, every instance obj of this class will have an attribute obj.next that is equivalent to spliceGraph[obj], etc.  Note that this is schema, not the actual operation of adding the object as a node to the graph.  Indeed, when obj is first created, it is not automatically added to spliceGraph; that is up to the user.  Unless your code has added the node to the graph (e.g. spliceGraph+=obj), obj.next should throw a :exc:`KeyError` exception.
%
%The general method getschema(obj,attr) works regardless of whether the schema was stored on an individual object or at the class level.

GraphQuery
----------

The GraphQuery class implements simple node-to-node matching, 
in which each new node-set is generated by an iterator associated 
with a specific node in the query graph.  This iterator model is general: 
since indexes (mappings) support the iterator protocol, a given iterator 
may actually be an index lookup (or other clever search algorithm).  
The GraphQuery constructor takes two arguments: the default data graph 
being queried, and the query graph.  The query graph is just a graph; 
its nodes can be any object that can be a graph node (i.e. any object 
that is indexible, e.g. by adding a __hash__() method).  Its node objects 
will not be modified in any way by the GraphQuery.  Its edges are expected 
to be dictionaries that can be checked for specific keyword arguments:


  
* filter: must be a callable function that accepts keyword arguments and returns True (accept this edge as a match to the queryGraph) or False (do not accept this edge as a match).  This function will be called with the following keyword arguments:

   * toNode: the target node of this edge, in the data graph
   * fromNode: the origin node of this edge, in the data graph
   * edge: the edge information for this edge in the data graph
   * queryMatch: a mapping of the query graph to the data graph, based on the partial matchings made so far
   * gqi: the GraphQueryIterator instance associated with this matching operation.  Much more data is available from specific attributes of this object.

* dataGraph: graph in which the current edge should be search for.  This allows a query to traverse multiple graphs.  In other words, when searching for edges from the current node, look up dataGraph[node] instead of defaultGraph[node].

* attr: object attribute name to use as the iterator, instead of the defaultGraph.In other words, generate edges from the current node via getattr(node,attr) instead of defaultGraph[node].  The object obtained from this attribute must act like a mapping; specifically, it must provide an items() method that returns zero or more pairs of targetNode,edgeInfo, just like a standard Pygr dictEdge object.

* attrN: object attribute name to use as the iterator, instead of the defaultGraph. In other words, generate edges from the current node via getattr(node,attr) instead of defaultGraph[node].  The object obtained from this attribute must act like a sequence; specifically, it must provide an iterator that returns zero or more targetNode.  The edgeInfo for any edges generated this way will be None.

* f: a callable function that must return an iterator producing zero or more pairs of targetNode,edgeInfo.  Typically f is a Python generator function containing a statement like yield targetNode,edgeInfo.

* fN: a callable function that must return an iterator producing zero or more targetNode.  Typically fN is a Python generator function containing a statement like yield targetNode.  The edgeInfo for any edges generated this way will be None.

* subqueries: a tuple of query graphs to be performed.  Since GraphQuery traversalcorresponds to logical AND (i.e. all the query graph nodes must be successfully matched to return a match), the subqueries are currently treated as a union (logical OR), by simply returning every match from each subquery as a match (at least for this node).  Each subquery is itself just another query graph.  Moreover, since query graphs can share nodes (i.e. the same object can appear as a node in multiple query graphs), subqueries can make reference to nodes that are already matched by the higher query.  This is an area that has not been explored much yet, but provides a pretty general model for powerful queries.


The attr - subqueries options are all implemented as extremely simple subclasses of GraphQuery.  If you want to see just how easy it is to write new subclasses of GraphQuery functionality, look at the graphquery.py module (the entire graph query module is only 237 lines long).

Note: an easy way to pass keyword dictionaries (e.g. as edge information) is simply using the dict() constructor, e.g. dict(dataGraph=myGraph,filter=my_filter).  I think this is a little more readable than {'dataGraph':myGraph, 'filter':my_filter}.

Note on current behavior: currently, the GraphQuery iterator returns the same mapping object for each iteration (simply changing its contents).  So to save these multiple values safely in a list comprehension we have to copy each one into a new dict object via dict(m).

What is GraphQuery actually doing?
----------------------------------

A GraphQuery is basically an iterator that returns all possible mappings of the query graph onto the datagraph that match all of the nodes and edges of the query graph onto nodes and edges of the data graph.  As an iterator, it does not instantiate a list of the matches, but simply returns the matches one by one.  The current design is very simple.  The GraphQuery constructor builds an "iterator stack" of GraphQueryIterators, each representing one node in the query graph; they are enumerated in order by a breadth-first-search of the query graph.  The GraphQuery iterator processes the stack of GraphQueryIterators: any match simply pushes the stack to the next level; any match at the deepest level of the stack is a complete match (yield the queryMatch mapping); the end of any GraphQueryIterator simply pops the stack.  One obvious idea for improving all this is to replace this "interpreter" with a "compiler" that compiles Python for loops that are equivalent to this stack, and run that... likely to be many fold faster.



