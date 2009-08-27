:mod:`metabase` --- Easy data sharing and access
=================================================

.. module:: metabase
   :synopsis: easy data sharing and access
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>

This module contains classes for scientific sharing in a "virtual
name space".  It does this through "metabases" -- *metadata databases*
that store not the primary data (which should be stored in a normal
database or other optimized back-end), but the "metadata" describing
*what* that data is, and its *relations* with other datasets.  Naturally,
Pygr organizes these metadata as a graph database whose nodes are
datasets and whose edges are relations between datasets.  A vital
part of the metadata describing this structure is *schema* information,
specifying whether a given relation is one-to-one, many-to-many, etc.
and optionally *binding* a given relation to a dataset as a named
attribute.

Pygr provides two main classes for managing metabases, which share
substantially the same interface.

* :class:`Metabase`: a single metabase stored in a specific location

* :class:`MetabaseList`: a collection of :class:`Metabase` stored
  in different locations.  Any search request applied to the 
  :class:`MetabaseList` will be applied to all the metabases in
  the collection.  The :mod:`worldbase` interface is simply a 
  :class:`MetabaseList` containing the set of metabases specified by
  the user's WORLDBASEPATH setting.

The Standard Metabase Interface
-------------------------------

This applies both to :class:`Metabase` (representing a single metabase)
and :class:`MetabaseList` (representing a set of metabases).  They both
provide the following methods:

.. method:: Metabase.__call__(resID, debug=None, download=None, *args, **kwargs)

   Retrieve the resource specified by *resID*.

   *debug=True* will force it to raise any exception that occurs during
   the search.  By default it ignores exceptions and continues the search
   to subsequent metabases.

   *download=True* will restrict the search to downloadable resources,
   and will download and install the resource (and its dependencies) if
   it / they are not already installed locally.  If a resource is available
   locally, it will simply be used as-is.  If a resource is downloaded, it
   will also be saved to the first writeable (local) metabase for future use.

.. attribute:: Metabase.Data

   Root of the virtual data namespace indexed by this metabase.  You can
   read and write to the namespace just as you would to :mod:`worldbase`,
   but of course the results will be restricted to this specific metabase.
   For example::

      mdb.Data.Bio.MSA.UCSC.hg17_multiz17way = my_msa # add to this metabase
      mdb.commit() # save it

.. attribute:: Metabase.Schema

   Root of the virtual schema namespace indexed by this metabase.  You can
   read and write to the namespace just as you would to ``worldbase.schema``,
   but of course the results will be restricted to this specific metabase.
   For example::

      mdb.Schema.Bio.Test.splicegraph = \
         metabase.ManyToManyRelation(exons, exons, splices,
                                     bindAttrs=('next','previous','exons'))
      mdb.commit() # save it to this metabase



.. method:: Metabase.add_resource(resID, obj=None)

   Add *obj* as resource ID *resID* to this metabase or metabase list.
   Queues *obj* for addition to
   the metabase, and marks it with its :attr:`_persistent_id`
   attribute, whose value is just *resID*.  

   If *obj* is None, the first argument must be a dictionary of 
   resID:obj pairs, which will all be added to the metabase / list.

.. method:: Metabase.delete_resource(resID)

   Delete the resource specified by *resID* from the metabase.  For 
   a metabase list, delete it from the first writeable metabase in the list.

.. method:: Metabase.add_schema(resID, schemaObj)

   Add the schema object *schemaObj* as the schema for resource *resID*.

.. method:: Metabase.commit()

   Commit all pending resource / schema additions to the metabase.

.. method:: Metabase.rollback()

   Abandon all pending resource / schema additions since the last commit()
   or rollback().

.. method:: Metabase.list_pending()

   Returns a pair of two lists ([ *data* ],[ *schema* ]), where
   the first list shows newly added worldbase IDs that are currently pending,
   and the second list worldbase IDs that with newly added schema information
   pending.


.. method:: Metabase.clear_cache()

   Clear the metabase / list's associated cache of resources that have been
   loaded during this session.  This forces any subsequent resource requests
   to (re)load a new object.

.. method:: Metabase.dir(pattern='', matchType='p', asDict=False, download=False)

   Return a list of dictionary of all resources that match the specified
   prefix or regular expression *pattern*.

   *matchType='p'* specifies a prefix pattern.

   *matchType='r'* specifies a regular expression pattern.
 
   *asDict=True* causes the result to be returned as a dictionary of
   resID:info pairs, providing additional information about each resource.

   *download=True* will restrict the search to downloadable resources.

.. method:: Metabase.get_schema(resID)

   Returns a dictionary for the schema (if any) found for the worldbase resource
   specified by *resID*.  The dictionary keys are attribute names (representing
   attributes of the specified resource or its contents that should have
   schema relations with other worldbase resources), and whose values are
   themselves dictionaries specifying the precise schema rules for constructing
   this specific attribute relation.


.. method:: Metabase.get_schema_attr(resID, attr)

   Return the target data linked to by attribute *attr* of worldbase
   resource *resID*, based on the stored worldbase schema.  The target resource
   object will be obtained by the metabase as usual.


.. method:: Metabase.bind_schema(resID, obj)

   Apply the worldbase schema for resource *resID* to the actual data
   object representing it (*obj*), by decorating it (and / or its itemClass
   and itemSliceClass) with properties representing its schema attributes.
   These properties are implemented by adding descriptor attributes to the
   associated class, such as :class:`OneTimeDescriptor` or :class:`ItemDescriptor`.


.. method:: Metabase.loads(data)

   Unpickles the string pickle contained in *data* in a worldbase-aware
   manner.  I.e. any references in the pickle of the form "PYGR_DATA_ID:"
   will be retrieved by worldbase in the usual way.  Do not use this internal
   interface unless you know what you are doing.

   *data* should have
   been generated by a previous call to :func:`dumps()`.



Metabase
--------

You construct a new metabase object as follows:

.. class:: Metabase(dbpath, resourceCache, zoneDict=None, parent=None, **kwargs)

   Interface to a single metabase.

   *dbpath* is the string path for this metabase

   *resourceCache* must be a :class:`ResourceCache` object, for storing any
   resources retrieved by the metabase.

   *zoneDict*, if not None, must be a dictionary: the metabase constructor
   will add a name:value pair to this dictionary consisting of its zone name
   and the metabase itself as the associated value.

   *parent*, if not None, should be the :class:`MetabaseList` that this
   metabase will be part of.

* a :class:`Metabase` is tied to a single back-end; you cannot ``update()`` it.
  Instead, just create a new :class:`Metabase` with the new path.




MetabaseList
------------

You construct a new MetabaseList object as follows:

.. class:: MetabaseList(worldbasePath=None, resourceCache=None, separator=',', mdbArgs={})

   Interface to a set of one or more metabases to be searched as a group.

   *worldbasePath* specifies the list of metabases, as a comma-separated 
   string of metabase paths.

   *resourceCache* must be a :class:`ResourceCache` object, for storing any
   resources retrieved by the metabase.

   *mdbArgs* must be a dictionary of keyword arguments to pass to the metabase
   constructor during any update operation.

* any resource request will be returned from the first metabase in its
  list that successfully constructs the specified resource ID.

* any resource saved to a :class:`MetabaseList` will be saved to the first
  metabase in its list that is writeable.

:class:`MetabaseList` offers several additional methods / attributes:

.. method:: MetabaseList.update(newpath)

   Change the list of metabases to *newpath*, which must be a comma-separated
   string of metabase paths.

.. method:: MetabaseList.registerServer(locationKey, serviceDict)

   Registers the set of resources specified by *serviceDict* to the
   first metabase index in WORLDBASEPATH that will accept them.
   *serviceDict* must be a dictionary whose keys are resource IDs and
   whose associated values are pickled resource objects (encoded as strings).
   *locationKey* should be a string name chosen to represent the "location"
   where the data are stored.  This can be anything you wish, and is mainly used
   to let the user know where the data will come from.  This might be used
   in future versions of worldbase to allow preferential screening of where
   to get data from (local disk is better than NFS mounted disk, which in turn
   might be preferable over remote XMLRPC data access).

.. attribute:: MetabaseList.zones

   A dictionary of the zone names in this :class:`MetabaseList`, each with its
   associated :class:`Metabase` object.  For further information on zones,
   see the :mod:`worldbase` documentation.


ManyToManyRelation, OneToManyRelation, ManyToOneRelation, OneToOneRelation
--------------------------------------------------------------------------
Convenience class for constructing schema relations for
a general graph mapping from a sourceDB to targetDB with edge info.

.. class:: ManyToManyRelation(sourceDB, targetDB, edgeDB=None, bindAttrs=None)

   *sourceDB*,*targetDB*, and *edgeDB* can be either
   a string resource ID, a :class:`ResourcePath` object, or
   an actual worldbase resource (automatically marked with its ID
   as the :attr:`_persistent_id` attribute).

   *bindAttrs*, if provided, must give a list of string attribute names to be
   bound, in order, to items of *sourceDB*, *targetDB*,
   and *edgeDB*, in that order.  A None value in this list simply
   means that no attribute binding will be made to the corresponding
   worldbase resource.

   Note: this class simply records the information necessary for this
   schema relation.  The information is not actually saved to the resource
   database until its :meth:`saveSchema` method is called by
   the :class:`SchemaPath` object.  In addition to saving attribute
   bindings given by *bindAttrs*, this will also create bindings
   on the mapping resource object itself (i.e. the resource whose
   schema is being set; see an example in the tutorial).  Specifically,
   it will save bindings for its :attr:`sourceDB`,:attr:`targetDB`,
   and :attr:`edgeDB` attributes to the corresponding resources
   given by the *sourceDB*, *targetDB*,
   and *edgeDB* arguments.

:class:`OneToOneRelation`, :class:`OneToManyRelation`, :class:`ManyToOneRelation`
and :class:`ManyToManyRelation` differ only in the uniqueness vs. multiplicity
of the mapping indicated.
E.g.  ``~m1[v] --> k`` vs.
``~mMany[v] --> [k1,k2,...]``


XMLRPC Resource Server
----------------------

.. class:: ResourceServer(mdb, name, serverClasses=None, clientHost=None, withIndex=False, host=None, port=5000, excludeClasses=None, downloadDB=None, **kwargs)

   Construct a new XMLRPC server to serve all worldbase resources
   currently loaded in a specified metabase's cache
   that are capable of XMLRPC client-server
   operation.  

   *mdb* specifies the :class:`Metabase` or :class:`MetabaseList` whose cached
   resources you wish to make available online.  Typically this will just
   be ``worldbase._mdb``.  Note: only resources that have actually
   been *loaded* by that metabase before you create the 
   :class:`ResourceServer` will be served to XMLRPC clients.

   The server *name* will be used for
   purposes of XMLRPC communication.  The *withIndex=True* option
   will cause the server to also act as a worldbase metabase
   accessible via XMLRPC (i.e. add its URL to your WORLDBASEPATH environment
   variable, to make its resources accessible to any Python script).
   In this case, the server will add itself as new worldbase layer
   *name*, for any Python script that accesses its resource index.

   Currently, :class:`ResourceServer` can serve three types of data as remote
   XMLRPC services: :class:`cnestedlist.NLMSA`,
   :class:`seqdb.SequenceFileDB`, and :class:`annotation.AnnotationDB`.

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
   to your server port via SSH, you could pass a *clientHost='localhost'*
   setting.

   *excludeClasses*, if not None, should be a list of classes that
   should be excluded from the new server.  If None, the default is::

      [pygr.sqlgraph.SQLTableBase,pygr.sqlgraph.SQLGraphClustered]

   since
   such relational database resources are better accessed directly from
   the relational database server, rather than via the XMLRPC server as
   an intermediate step.

   *downloadDB*, if not None, should be a file path to a :class:`ShelveMetabase`
   shelve file in which a set of downloadable resource records have been
   stored.  See the section "download=True Mode" above for more details.

   *host, port* arguments are passed to the
   :class:`coordinator.XMLRPCServerBase` constructor.
   For details see that section below.

   If the server does not provide its
   own index (i.e. *withIndex=False*), then you should first register
   it to your local metabase server (so that clients of that server
   will know about the new services your new server is providing), by
   calling its :meth:`ResourceServer.register()` method.

.. method:: ResourceServer.register(url=None, name='index', server=None)

   *server* if not None, must be a :class:`XMLRPCMetabase` or 
   :class:`MySQLMetabase` object representing a metabase server that
   you want to register with.

   *url* if not None, specifies a XMLRPC service (served by a
   :class:`ResourceServer` running on that URL) to which you want to
   register.

   If both are None, it will try to register via :mod:`worldbase`,
   to the first server in your WORLDBASEPATH that accepts the 
   registration.

   *name* provides the name you want to register as.

.. method:: ResourceServer.serve_forever(demonize=True)

   Use this method to start the XMLRPC service.

   *demonize=True* will cause the process to detach as a background
   demon.  Use this mode for a non-interactive Python process.

   *demonize=False* will run the server as a Python thread,
   so that you can continue to use your interactive Python prompt
   *while the server is running*.  This will *not* work if Python
   was run in non-interactive mode (the server will immediately die).

   To make it easy to manage your
   XMLRPC server using the command line, we recommend that you
   run it in an interactive Python interpreter session as follows:

   * in the interactive shell, start Python within
     the ``screen`` utility::

        screen python

   * in the interactive Python shell, import whatever script(s) you
     need to create your :class:`ResourceServer` object.

   * start the server in interactive mode::

        myserver.serve_forever(False)

     This runs the server in a separate Python thread, immediately
     returning control to your interactive Python prompt.

   * Detach from your session using the ``screen`` key sequence **Ctrl-A D**

   * At any later time use the ``screen -r`` command to re-attach to
     this interactive session, if you wish to execute Python commands
     altering the contents of the server, reloading it etc.  This will
     work even if you have logged out in the meantime.

ResourceCache
-------------

.. class:: ResourceCache()

   This is essentially just a dictionary that caches both data
   and schema that have been loaded from back-end metabases.
   Any subsequent requests for the same worldbase IDs will simply
   receive the cached object.  This guarantees that any two
   references to a given worldbase ID within a single interpreter
   session, will in fact get the same Python object.


Internal Metabase Interfaces
----------------------------

The following classes and functions are not intended for regular users, 
but are documented here for Pygr developers.

Do not use this internal function unless you know what you are doing:

.. function:: dumps(obj)

   Provides a worldbase-aware pickling service; that is, if
   during pickling of *obj* any references are encountered
   to objects that worldbase IDs, it will simply save the ID.
   Returns a string pickle of *obj*.
   Use :meth:`Metabase.loads()` to restore an object pickled using this function.




MySQLMetabase
---------------
Implements a back-end interface to storage of a metabase in a MySQL
database table.


.. class:: MySQLMetabase(tablename, mdb, createLayer=LAYERNAME, newZone=None, **kwargs)

   Create a metabase in a MySQL database table.
   *tablename* is the table to use in the database, in the format
   "*DBNAME.TABLENAME* *dbinfo*", where *DBNAME* is the name of the
   database in the MySQL server, and *TABLENAME* is the name of
   the table in that database that you wish to use to store the
   metabase.  *dbinfo* is optional.
   If provided, it must be a whitespace separated
   list of arguments for connecting to the MySQL server, of the form
   *host* *user* *passwd*.  You can provide one, two
   or three of these optional arguments.
   If no *dbinfo* is provided, host, port, user and password info are obtained
   from your .my.cnf config file as usual for the mysql client.

   *mdb* must be the :class:`Metabase` object associated with this back-end.

   To create a new table in the MySQL database (automatically initializing its schema),
   instead of assuming that it already exists, you must provide
   the *createLayer* argument, which is saved as the layer name
   of the new metabase.  If worldbase finds that it is unable
   to connect to a MySQL database table specified in your WORLDBASEPATH
   it will print a warning message, and ignore the offending database table.
   It will NOT silently create a database table for you in this case.
   The rationale is that whereas a misspelled directory name will result in
   an IOError (thus allowing worldbase to detect a bad directory name in WORLDBASEPATH),
   there would be no easy way for worldbase to tell whether you simply mistyped the name
   of an existing MySQL table, or whether you actually wanted to create a new MySQL table.

   Example: create a new metabase, give it the layer name "leelab",
   and register it in our list of metabases::

      rdb = metabase.MySQLMetabase('pygrdata.index', mdb, createLayer='leelab')

   Note that you must provide the *createLayer* argument, in order to
   create a new metabase table.  :class:`MySQLMetabase` will not
   automatically create a new table without this argument, simply because the
   *tablename* you provided does not exist.  In that case, it will
   raise an exception to alert you to the fact that either the correct table name
   was not given, or the table does not exist.



.. method:: MySQLMetabase.find_resource(resID)

   Find resource *resID* from this metabase, or :exc:`KeyError`
   if not found.  Returns its pickle representation and docstring as a tuple.


.. method:: MySQLMetabase.__delitem__(id)

   Delete resource *id* from this metabase, or :exc:`KeyError`
   if not found.


.. method:: MySQLMetabase.__setitem__(id, obj)

   Save resource *id* to this metabase, by pickling it
   with ``self.finder.dumps(obj)``.


.. method:: MySQLMetabase.registerServer(locationKey, serviceDict)

   Saves the set of resources specified by *serviceDict* to the
   database.

   *serviceDict* must be a dictionary whose keys are resource IDs and
   whose associated values are pickled resource objects (encoded as strings).

   *locationKey* should be a string name chosen to represent the "location"
   where the data are stored.  This can be anything you wish, and is mainly used
   to let the user know where the data will come from.  This might be used
   in future versions of worldbase to allow preferential screening of where
   to get data from (local disk is better than NFS mounted disk, which in turn
   might be preferable over remote XMLRPC data access).


.. method:: MySQLMetabase.setschema(id, attr, ruleDict)

   Save schema information for attribute *attr* on resource *id*
   by pickling the *ruleDict*.


.. method:: MySQLMetabase.delschema(id, attr)

   Delete schema information for attribute *attr* on resource *id*.


.. method:: MySQLMetabase.getschema(id)

   Get schema information for resource *id*, in the form of a dictionary
   whose keys are attribute names, and whose values are the associated
   schema *ruleDict* for each bound attribute.


ShelveMetabase
----------------

Implements an interface to storage of a metabase in a Python
:mod:`shelve` (i.e. BerkeleyDB file) stored on local disk.
Provides the same interface as :class:`MySQLMetabase`, except for
no :meth:`MySQLMetabase.registerServer` method.  Note: any method call that would
save information to the database temporarily re-opens the database
file in write mode, saves the required information, and immediately
closes and re-opens
the database in read-only mode.  Thus, unless two clients try
to save information to the same file at exactly the same time,
successive writes by multiple clients will not interfere with each
other.

.. class:: ShelveMetabase(dbpath, mdb, mode='r', newZone=None, **kwargs)

   *dbpath* is the path to the directory in which the shelve
   file is found (or should be created, if none present).

   *mdb* must be the :class:`Metabase` object associated with this back-end.


XMLRPCMetabase
----------------
Implements a client interface to storage of a metabase in an XMLRPC
server.  

MetabaseServer
----------------
Implements a server interface for storage of a metabase in
a standard Python dict, served to clients via an XMLRPC
server (use :class:`coordinator.XMLRPCServerBase` as the XMLRPC
server to serve this object).  Ordinarily, users will have no need to 
construct an instance of this class themselves.

.. class:: MetabaseServer(zoneName, readOnly=True)

   *zoneName* is the zone name that this server will provide
   to worldbase clients.  *readOnly* if True, makes the server reject
   any requests to add new database rules received via XMLRPC, i.e.
   it only allows :meth:`getName` and :meth:`getResource` calls via XMLRPC.
   If False, also allows calls to :meth:`registerServer` and :meth:`delResource`.


ResourceSaver
-------------

.. class:: ResourceSaver(mdb)

   queues new resources until committed to the *mdb*.

.. method:: ResourceSaver.save_resource(resID, obj)

   Raw interface to actually save a specific resource to the metabase.
   DO NOT use this internal interface unless you know what you are doing!

.. method:: ResourceSaver.delSchema(resID)

   Delete schema bindings for all attributes of the resource *resID*
   from our metabase, as well as all schema relations
   on other resources that are targeted to resource *resID*.



ResourcePath
------------
Used for providing the dynamically extensible worldbase namespace
that provides the normal interface for users to access worldbase resources.

.. class:: ResourcePath(mdb, base=None)

   *mdb* must be the :class:`MetabaseList` or :class:`Metabase` 
   object that you want this ResourcePath to be associated with.

   *base* specifies the ID string to use for this resourcePath.



.. method:: ResourcePath.__getattr__(attr)

   extends the resource path by one step, returning a
   :class:`ResourcePath` object representing the requested attribute.


.. method:: ResourcePath.__setattr__(attr,obj)

   saves *obj* as the specified resource ID, by calling the *mdb* 's
   :meth:`Metabase.add_resource()`.


.. method:: ResourcePath.__delattr__(attr)

   deletes the specified resource ID, by calling the *mdb* 's
   :meth:`Metabase.delete_resource()`.


.. method:: ResourcePath.__call__(resID, *args,**kwargs)

   Construct the specified resource ID, by calling the *mdb*
   (with any additional arguments, if present).


SchemaPath
----------
Class for top-level object representing a schema namespace. 



Schema Rule Implementation
--------------------------

Although users do not need to know
how this information is saved, I will outline the methodology
as a reference for developers who want to work directly with this
internal data (skip this section otherwise).

* In a given metabase (dictionary), information for constructing a
  given resource ``id`` is stored with its resource ID as the key.
  i.e. if ``rdb`` is a metabase, ``rdb[id]`` gives
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

  * they are bound to the class object, not the instance object;

  * they are only invoked if the specified attribute name is
    missing from the instance object's :attr:`__dict__`;

  * once invoked, they save their
    result on the instance object (in its :attr:`__dict__`)
    as the same-named attribute; 4. thus, the descriptor method
    will only be called once; thereafter the attribute will be
    obtained directly from the value cached on the instance object;

  * the descriptor only loads its target resource(s) when the user
    attempts to read the value of the attribute.  Thus no extra
    resources are loaded until the user actually demands information
    that requires them.
  
* Currently, these shadow attributes are implemented by
  three different descriptor classes in worldbase:

  * :class:`OneTimeDescriptor`, for binding attributes directly on a resource
    object (container);

  * :class:`ItemDescriptor`, for binding attributes on items (or slices of
    items) obtained from a resource object (via its __getitem__ method);

  * :class:`SpecialMethodDescriptor`, for binding special Python methods like
    :meth:`__invert__`.
  
* The rule information for a given attribute is itself a dictionary,
  with the following string keys governing the behavior of the shadow attribute.

  *targetID*: the worldbase resource ID of the resource that this
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
a single schema attribute relation on a worldbase resource,
linking it to another worldbase resource.

.. class:: DirectRelation(target)

   *target* gives a reference to a worldbase resource, which will
   be the target of a bound schema attribute.  *target* can be either
   a string resource ID, a :class:`ResourcePath` object, or
   an actual worldbase resource (automatically marked with its ID
   as the :attr:`_persistent_id` attribute).


.. method:: schemaDict()

   returns a basic *ruleDict* dictionary for saving this schema binding.
   Can be over-ridden by subclasses to customize schema binding behavior.


.. method:: saveSchema(source,attr,layer=None,**ruleDict)

   Saves a schema binding for attribute *attr* on worldbase resource
   *source* to the specified metabase *layer* (or
   to the default metabase if not specified).  *ruleDict*
   if specified provides additional binding rules (which can add to or
   over-ride those returned by the :meth:`schemaDict` method).
   *source* can be either
   a string resource ID, a :class:`ResourcePath` object, or
   an actual worldbase resource (automatically marked with its ID
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


nonPortableClasses, SourceFileName
----------------------------------
The variable *metabase.nonPortableClasses* specifies a list of
classes which have local data dependencies (e.g. requires reading a file
that is on your local disk),
and therefore cannot be transferred over XMLRPC to a remote client
by simple pickling / unpickling.  :class:`ResourceServer` will
automatically cull any data that has such dependencies from the list
of resources it loads into the XMLRPC server it constructs, so that
the server will not attempt to serve data that actually will not work
on remote clients.  You can add your own classes to this list if
needed.

By default, the *metabase.nonPortableClasses* list consists of simply a single
class, :class:`classutil.SourceFileName`, which is a subclass of str
that marks a string as representing a path to a file.  It behaves
just like a string, but allows worldbase to be smart about checking
whether the required file actually exists and is readable before returning
a resource to the user.  If you save filenames on your own objects using
this class, worldbase will therefore be able to handle them properly for
many issues such as XMLRPC portability to remote clients.  You do this simply
as follows::

   class Foo(object):
     def __init__(self,filename):
       self.filename = SourceFileName(str(filename)) # MARK THIS A BEING A FILE NAME
       ifile = file(self.filename) # OPEN THIS FILE NOW IF YOU WANT...


  
