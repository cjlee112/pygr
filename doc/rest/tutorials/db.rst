

=====================
Working with Mappings
=====================

Purpose
^^^^^^^

This tutorial teaches you how to create and query 
mappings stored in memory, on disk, and in SQL databases.
This focuses on traditional Python mappings, in which
each value maps to a unique value.  You should first understand
how Pygr works with databases (see :doc:`db_basic`).

The Standard Mapping: dict
^^^^^^^^^^^^^^^^^^^^^^^^^^

Every Python programmer knows how to use a Python mapping -- it's
just ``dict``.  For example, given a database of UCSC "known genes"
and a database of RefSeq mRNAs, we can use ``dict`` to store a mapping
from RefSeq to UCSC genes::

   >>> from pygr import sqlgraph
   >>> serverInfo = sqlgraph.DBServerInfo(host='genome-mysql.cse.ucsc.edu',
   ...                                    user='genome')
   >>> genes = sqlgraph.SQLTable('hg18.knownGene', serverInfo=serverInfo)
   >>> refseq = sqlgraph.SQLTable('hg18.refLink', serverInfo=serverInfo)

Let's get 5 refseq entries and 5 genes, and map them to each other::

   >>> refseq_it = iter(refseq)
   >>> genes_it = iter(genes)
   >>> list1 = [refseq_it.next() for i in range(5)]
   >>> list2 = [genes_it.next() for i in range(5)]
   >>> m = {}
   >>> for i in range(5):
   ...    m[list1[i]] = list2[i]

Now we can query with refseq objects and find the corresponding gene::

   >>> m[list1[2]]

This is nice, but it has several important limitations:

* the mapping is stored in memory.  Big mappings will take up lots of memory,
  and if they get too big, we wont't be able to create the mapping at all.
  This is a serious problem for bioinformatics datasets, which are often
  huge.

* To improve scalability, we'd like to be able to save this mapping to
  a disk file.  But this requires using a more sophisticated approach --
  this will only give us a real benefit if the data are stored using
  an on-disk index structure so that we can quickly look up individual
  records without having to load a sizable fraction of the data into
  memory.  Python doesn't provide a complete solution for this;
  its solution (``shelve``) requires that the key be a string,
  whereas the value is allowed to be any picklable Python object.

* Persistence: one of the real benefits of storing the mapping
  on disk would be that we could build the mapping just once,
  and then reuse it in any subsequent Python process.  However,
  that requires being able to automatically "recreate" the 
  Python objects that we mapped to the file, in a later Python process.
  This is referred to as the "persistence" problem.
  Commonly, objects from a large, complex database are not
  "picklable" (Python's standard method for persistence).

Storing Mappings on Disk Using Indexed Files
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

So we need a slightly more sophisticated approach.  The standard
solution in the database world is to store not the complete
objects, but simply their unique IDs, to save the mapping.
Pygr provides a standard class to do this for you:
:class:`mapping.Mapping`.  Let's apply it to our refseq - genes
mapping::

   >>> from pygr import mapping
   >>> m = mapping.Mapping(refseq, genes, filename='mymap.shelve', mode='c')

This tells :class:`mapping.Mapping` that we are mapping objects
from the database ``refseq`` to objects from the database ``genes``,
and to create a new file to store the mapping.

Now we simply use the mapping exactly as before::

   >>> for i in range(5):
   ...    m[list1[i]] = list2[i]

Always close the mapping when you are done; this closes its
open file descriptor and ensures that all data has been completely
written to disk::

   >>> m.close()

Now we can test whether this mapping is really persistent, by
re-opening it from the disk file (this time without the create flag)::

   >>> m = mapping.Mapping(refseq, genes, filename='mymap.shelve')
   >>> m[list1[2]]

Great!  Storing the mapping on disk has several benefits:

* since the data are accessed via on-disk indexes, without loading
  the dataset into memory, we can work with huge datasets without
  using up much memory.

* because these files are indexed, performance should still be reasonably
  scalable, ideally *O(log(N))* time for looking up one entry, in a 
  database of size *N*.

Saving Mappings in Worldbase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use Pygr, whenever someone says "persistence" you should think
:mod:`worldbase` -- it makes access to persistent data as easy as
just "saying the name" of the dataset you want (see :doc:`worldbase`
for more details).  So let's try adding our mapping to worldbase.
First let's save our ``genes`` and ``refseq`` datasets::

   >>> from pygr import worldbase
   >>> serverInfo.__doc__ = 'MySQL server with UCSC genome annotations'
   >>> worldbase.Bio.MSA.UCSC.genome_mysql = serverInfo
   >>> genes.__doc__ = 'UCSC hg18.knownGene database'
   >>> worldbase.Test.Annotation.UCSC.hg18.knownGene = genes
   >>> refseq.__doc__ = 'UCSC hg18.refseqLink database'
   >>> worldbase.Test.Annotation.UCSC.hg18.refseqLink = refseq

Now our mapping::

   >>> m.__doc__ = 'refseq to knownGene mapping'
   >>> worldbase.Test.Annotation.UCSC.hg18.refseqToKG = m

Now let's tell worldbase that this is a one-to-one mapping::

   >>> from pygr import metabase
   >>> worldbase.schema.Test.Annotation.UCSC.hg18.refseqToKG = \
   ...   metabase.OneToOneMapping(refseq, genes, bindAttrs=('gene', 'refseq'))

This tells worldbase that ``Test.Annotation.UCSC.hg18.refseqToKG``
is a one-to-one mapping from ``Test.Annotation.UCSC.hg18.refseqLink``
to ``Test.Annotation.UCSC.hg18.knownGene``.  It furthermore instructs
worldbase to automatically bind this mapping to ``refseq`` objects
as an attribute called ``gene`` and to ``genes`` objects as the
``refseq`` attribute.

Finally, let's commit all our data::

   >>> worldbase.commit()

Let's see if all this worked.  First, let's clear the worldbase cache,
which is equivalent to closing Python and starting a new Python
interpreter::

   >>> worldbase.clear_cache()

This allows us to test whether this worked, without having to quit and
restart.  Let's just request our ``refseq`` dataset, grab an
object from it, and try getting its mapping to our genes::

   >>> refseq = worldbase.Test.Annotation.UCSC.hg18.refseqLink()
   >>> r = refseq['NM_003710']
   >>> r.gene, r.gene.id

Wow!  Look how much easier it is to use the mapping via our bound
``gene`` attribute -- we didn't even have to tell worldbase to
load the ``Test.Annotation.UCSC.hg18.refseqToKG`` mapping or
the ``Test.Annotation.UCSC.hg18.knownGene`` gene database.
Just because we requested this bound attribute, worldbase 
automatically loaded both of the needed resources for us.
That's the idea of worldbase: to work with data, all you should
need to know is the *name* of what you want.  In this case,
all we needed to know was the name of the ``gene`` attribute
that serves as a proxy for obtaining this mapping.

Accessing Mappings from SQL Databases
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Often the mapping that you want is stored in an SQL database.
Pygr provides a way to use such a mapping directly:
:class:`sqlgraph.MapView`.  Let's apply that to our refseq
- UCSC known genes mapping.  UCSC provides a table that gives
a mapping between known gene IDs and refseq IDs; it's called
``kgXref``.  :class:`sqlgraph.MapView` enables us to create
a Pygr mapping using any SQL query that our back-end database
server can execute::

   >>> kgXref = sqlgraph.MapView(refseq, genes,
   ...             'select kgID from hg18.kgXref where refseq=%s',
   ...             inverseSQL='select refseq from hg18.kgXref where kgID=%s')

This tells ``MapView`` that it can provide a 1:1 mapping from
``refseq`` to ``genes`` using ths supplied SQL query.  Note that 
``MapView`` can automatically get the necessary ``serverInfo``
from the source database you supplied as the first argument.
Note that we also supplied an SQL statement for performing the
inverse mapping, so that the ``MapView`` can automatically provide
the inverse mapping as well.

The ``MapView`` query works in a very simple way, whenever we perform an
actual mapping operation::

   >>> g = kgXref[r]

* given a key object ``r`` (which must be from the ``refseq`` database)
  ``MapView`` first extracts the ID from that object.

* it then formats the query, substituting in the ID in place of the
  ``%s``

* it runs the query, receiving back an ID for a known gene.

* it then uses that ID as a key to the ``genes`` database,
  which returns the final result: our desired gene object. 

Of course, our :class:`sqlgraph.MapView` can be saved to 
:mod:`worldbase` just like we saved the :class:`mapping.Mapping`::

   >>> kgXref.__doc__ = 'refseq to knownGene mapping'
   >>> worldbase.Test.Annotation.UCSC.hg18.refseqToKG = kgXref
   >>> worldbase.schema.Test.Annotation.UCSC.hg18.refseqToKG = \
   ...   metabase.OneToOneMapping(refseq, genes, bindAttrs=('gene', 'refseq'))
   ...
   >>> worldbase.commit()

Now, if we wanted we could use the inverse mapping directly from
the ``refseq`` attribute that we bound to gene objects::

   >>> worldbase.clear_cache()
   >>> genes = worldbase.Test.Annotation.UCSC.hg18.knownGene()
   >>> g = genes['SOME ID']
   >>> g.refseq, g.refseq.id
   
Storing Mappings in an SQL Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Because :class:`sqlgraph.MapView` allows you to use arbitrary SQL
expressions to generate the mapping, there is no guaranteed way for
it to be able to save mapping data to your schema.  Instead, simply
use :class:`sqlgraph.SQLTable` to create an SQL table and save
mapping information to it.  Let's go through a simple example
of storing our mapping in an sqlite table.  First let's create the table::

   >>> liteserver = sqlgraph.SQLiteServerInfo('mapping.sqlite')
   >>> m = sqlgraph.SQLTable('refseq_knowngene', serverInfo=liteserver,
   ...                       writeable=True, 
   ...                       createTable='CREATE TABLE refseq_knowngene (refseq_id VARCHAR(40) PRIMARY KEY, kg_id VARCHAR(40) NOT NULL, INDEX(kg_id));')
   ...

Now all we have to do is save the ID pairs to the table, using its
:meth:`sqlgraph.SQLTable.new()` method::

   >>> for i in range(5):
   ...    m.new(refseq_id=list1[i].id, kg_id=list2[i].id)

When we're done saving our data, all we have to do is create a
:class:`sqlgraph.MapView` object to access the table::

   >>> m = sqlgraph.MapView(refseq, genes,
   ...             'select kg_id from refseq_knowngene where refseq_id=%s',
   ...             inverseSQL='select refseq_id from refseq_knowngene where kg_id=%s')
   ...
   >>> m[list1[1]]



Types of Databases and Mappings
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. csv-table:: Pygr Database categories
   :header: "Data Type", "ID:data dictionary", "1:1 mapping", "many:many mapping"

   "shelve", :class:`mapping.Collection`, :class:`mapping.Mapping`, :class:`mapping.Graph`
   SQL, :class:`sqlgraph.SQLTable`, :class:`sqlgraph.MapView`, ":class:`sqlgraph.SQLGraph` or :class:`sqlgraph.GraphView`"
   Sequence, :class:`seqdb.SequenceFileDB`, ":class:`cnestedlist.NLMSA` (pairwise)", :class:`cnestedlist.NLMSA`
   Annotation, :class:`annotation.AnnotationDB`, ":class:`cnestedlist.NLMSA` (pairwise)", ":class:`mapping.Graph`, etc."


Collection, Mapping, Graph, SQLTable and SQLGraph classes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
One of the main challenges in persistent storage (e.g. keeping a database
on disk) of Python objects is how to store their inter-relations
in an efficient and transparent way.  For example, in a database
application we want to be able to load just one object at a time
(rather than being forced to load all the objects from the database into memory)
even though each object may have references to many other objects
(and we obviously want these references to work transparently for the
user).  The standard database answer is to associate a unique identifier
(e.g. an integer) with each object in a specific collection, and
to store references in the database in terms of these identifiers.
This gives the database a flexible way to refer to objects (by their unique
identifiers) that we have not yet actually loaded into memory.

The :mod:`pygr.mapping` module provides classes that make it very easy for
you to store your data in this way.

* Its :class:`Collection` class acts like a dictionary
  whose keys are the unique identifiers you've chosen for your objects,
  and whose values are the associated objects.  This provides the essential
  association between Python objects and unique identifiers that allows
  us to store inter-relationships persistently in a database by simply
  storing them in terms of their unique identifiers.
  
* The :class:`Mapping` class
  acts like a dictionary that maps objects of a given collection to
  arbitrary objects of a second collection.  However, because internally
  it stores only identifiers, the :class:`Mapping` class can be stored
  persistently, for example to a disk database.
  
* Indeed, you can make both of
  these classes be stored as a database on disk, simply by passing a *filename*
  argument that specifies the file in which the database should be stored.
  If you do not provide a *filename*, a normal (in-memory) Python dictionary
  is used.
  
* Alternatively you can use the :class:`SQLTable` classes that
  provide a dict-like interface to data from an SQL database server
  such as MySQL, that is analogous to the :class:`Collection` class.
  
* The :class:`Graph` class provides a general extension of the
  mapping concept to represent a *graph of nodes connected by edges*.
  Whereas the :class:`Mapping` class stores a one-to-one correspondence
  from the first collection to the second,
  the :class:`Graph` class stores a many-to-many relation between
  them, and associates an *edge* object with each
  node-to-node mapping relationship, which is highly useful for many
  bioinformatics problems.  To see example uses of pygr graphs, see
  section 1.5 below.  Like :class:`Mapping`, :class:`Graph` can store its graph data
  in memory in a Python dict, or on disk using a BerkeleyDB file.
  
* Alternatively you can use the :class:`SQLGraph` classes that
  provide an interface to store graph data in an SQL database server
  such as MySQL, that provides an SQL database version of the functionality
  provided by the :class:`Graph` or :class:`Mapping` classes.
  
* All of these classes can be saved as resources in worldbase, making
  it very easy for you to capture entire datasets of complex bioinformatics
  data in worldbase.
  
* It's important to distinguish that these classes divide into
  *primary data* (e.g. :class:`Collection`, :class:`SQLTable`), versus
  *relations* between data (e.g. :class:`Mapping`, :class:`Graph`,
  :class:`SQLGraph`).  The latter should be given worldbase.schema information,
  so that worldbase can automatically construct the appropriate data inter-relations
  for any user of these data.
  

Here's a simple example of using a pygr :class:`Collection`::

   ens_genes = Collection(filename='genes.db', mode='c' # create new database
                          itemClass=Transcript)
   for gene_id,gene_data in geneList:
       gene = Transcript(gene_id, gene_data, ens_genes)
       ens_genes[gene_id] = gene # store in our database


:class:`Mapping` enables you to store a relationship between one collection
and another collection in a way that is easily stored as a database.  For
example, assuming that *ens_genes* is a collection of genes,
and *exon_db* is a collection of exons, we can store the mapping from
a gene to its exons as follows::

   gene_exons = Mapping(ens_genes, exon_db, multiValue=True,
                        inverseAttr='gene_id', filename='gene_exons.db', mode='c')
   for exon in exon_db:
       gene = ens_genes[exon.gene_id] # get its gene
       exons = gene_exons.get(gene, []) # get its list of exons, or an empty list
       exons.append(exon) # add our exon to its list
       gene_exons[gene] = exons # save expanded exon mapping list

The optional *multiValue* flag indicates that this is a one-to-many
mapping (i.e. each gene maps to a *list* of exons.  Again, we used the
*filename* variable to make pygr store our mapping on disk using a Python
:mod:`shelve` (BerkeleyDB file).

The :class:`Collection`, :class:`Mapping` and :class:`Graph` classes provide
general and flexible storage options for storing data and graphs.  These classes
can be accessed from the :mod:`pygr.mapping` module.
For further details, see the :mod:`pygr.mapping` module documentation.
The :class:`SQLTable` and :class:`SQLGraph` classes in the :mod:`pygr.sqlgraph`
module provide analogous interfaces for storing data and graphs in an SQL
database server (such as MySQL).

Here's an example of creating an :class:`SQLGraph` representing
the splices connecting pairs of exons, using data stored in an
existing database table::

   splicegraph = sqlgraph.SQLGraphClustered('PYGRDB_JAN06.splicegraph_hg17',
                                            source_id='left_exon_form_id',
                                            target_id='right_exon_form_id',
                                            edge_id='splice_id',
                                            sourceDB=exons, targetDB=exons,
                                            edgeDB=splices,
                                            clusterKey='cluster_id')
   worldbase.Bio.ASAP2.hg17.splicegraph = splicegraph
   from pygr.metabase import ManyToManyRelation
   worldbase.schema.Bio.ASAP2.hg17.splicegraph = \
       ManyToManyRelation(exons, exons, splices,
                          bindAttrs=('next', 'previous', 'exons'))
   worldbase.commit() # SAVE ALL PENDING DATA TO THE METABASE

This variant of :class:`SQLGraph` is optimized for typical usage patterns,
by loading data in clusters (rather than each individual splice one by one).
Since the key that we provided for the clustering ('cluster_id') is the
gene identifier, this means that looking at any splice will have the effect
of loading all splices for that gene.  This makes sense, because only exons
that are in the same gene can have splices to each other.  This makes
communication with the SQL server efficient, but only loads data that
is likely to be used next by the user.

