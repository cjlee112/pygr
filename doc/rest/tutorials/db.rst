
=========================
Using Databases with Pygr
=========================

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

