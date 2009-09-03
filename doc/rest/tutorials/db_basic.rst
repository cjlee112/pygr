
======================================
Working with Databases and Annotations
======================================

Purpose
^^^^^^^

This tutorial will teach you how to use Pygr to work with databases
stored in memory, on disk, and in SQL databases.  The examples will
focus on setting up simple annotation databases, both by plugging in
external data sources and creating new databases.  No previous 
knowledge of Pygr is required (although you may want to look at
the annotation tutorial, to learn about what you can do with annotations...).

Using dict as a Database
^^^^^^^^^^^^^^^^^^^^^^^^

You may have noticed an analogy between traditional databases,
which associate a unique identifier (the "primary key") for each row,
and Python dictionaries, which map a unique key value to an associated
value.  Pygr builds on this analogy by adopting the Python dictionary
interface (the "Mapping Protocol") as its standard database interface.
That means you can just use a Python ``dict`` anywhere that Pygr
expects a "database" object.

Example: An Annotation Database based on dict
---------------------------------------------

For example, Pygr annotation databases are themselves built on top of two
"databases": a *slice information* database that gives the coordinates
of an annotation interval for each key; and a *sequence* database
on which to apply those coordinates.  So we can build an annotation
database by supplying a dictionary containing some slice information.
We just need to create a class that stores the slice coordinate attributes
expected by the annotation database.  Here is the content of our
simple module ``slice_pickle_obj.py``::

  class MySliceInfo(object):
     def __init__(self, seq_id, start, stop, orientation):
        (self.id, self.start, self.stop, self.orientation) = \
            (seq_id, start, stop, orientation)

Let's use this to create a dict "database"::

  >>> from slice_pickle_obj import MySliceInfo
  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'
  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)
  >>> slice_db = dict(A=slice1, B=slice2) 

Now all we have to do is open the sequence database and 
create the annotation database object::

  >>> from pygr import seqdb, annotation
  >>> dna_db = seqdb.SequenceFileDB('../tests/data/hbb1_mouse.fa')
  >>> annodb = annotation.AnnotationDB(slice_db, dna_db)

We can get our annotations and their associated
sequence intervals::

  >>> annodb.keys()
  ['A', 'B']
  >>> a = annodb['A']
  >>> len(a)
  50
  >>> s = a.sequence
  >>> print repr(s), str(s)
  gi|171854975|dbj|AB364477.1|[0:50] ATGGTGCACCTGACTGATGCTGAGAAGGCTGCTGTCTCTGGCCTGTGGGG

Using Collection as a Persistent Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Of course, in real life you probably need to worry about scalability --
we'd like to be able to build annotation databases that are much larger
than will fit in memory, by storing them on disk and using fast indexing
methods to retrieve data from them.

For this purpose Pygr provides its :class:`mapping.Collection` class.
It adds a few crucial features on top of Python's ``shelve`` persistent
dictionary interface:

* unlike shelve objects, :class:`mapping.Collection` objects are
  picklable.  So they can be stored in :mod:`worldbase`.

* unlike shelve dictionaries, :class:`mapping.Collection` can
  work with integer keys, if you pass the ``intKeys=True`` argument.

So let's modify our previous example to work with 
:class:`mapping.Collection`.  All we need to do is create the
Collection with a ``filename`` argument, and it will be stored on disk
(in that file).  We use the standard shelve argument ``mode='c'``
to tell it to create a new file (overwriting any existing file 
if present)::

   >>> from pygr import mapping
   >>> slice_db = mapping.Collection(filename='myshelve', mode='c')
   >>> slice_db['A'] = slice1
   >>> slice_db['B'] = slice2
   >>> slice_db.close()

Closing the database is essential to ensuring that all data has been
written to disk.  Now we can re-open the Collection in read-only mode,
and use it as the back-end for our annotation database::

   >>> slice_db = mapping.Collection(filename='myshelve', mode='r')
   >>> annodb = annotation.AnnotationDB(slice_db, dna_db)
   >>> for k in annodb:
   ...     print repr(annodb[k]), repr(annodb[k].sequence)
   annotA[0:50] gi|171854975|dbj|AB364477.1|[0:50]
   annotB[0:100] -gi|171854975|dbj|AB364477.1|[300:400]


Accessing SQL Databases
^^^^^^^^^^^^^^^^^^^^^^^

In many cases, you'll want to access data stored in external
database servers via SQL.  Pygr makes this very easy.  The first
thing you need is a connection to the database server.  Pygr
uses a standard class :class:`sqlgraph.DBServerInfo` (and its
subclasses) for this::

   >>> serverInfo = sqlgraph.DBServerInfo(host='genome-mysql.cse.ucsc.edu',
                                          user='genome')

In this case, it enables us to connect to UCSC's Genome Browser 
MySQL database.

:class:`sqlgraph.DBServerInfo` adds several capabilities on top of
the standard Python DB API 2.0 "database connection" and Cursor
objects:

* it helps Pygr automatically figure out the schema of the target
  database, and enables it to work with different databases
  (e.g. MySQL, sqlite) that have slight differences in SQL syntax.

* It is guaranteed to be picklable (unlike Cursor or Connection objects),
  and therefore can be stored in worldbase.  That is, it stores whatever
  information is necessary to re-connect to the target database
  server at a later time, in a form that can be pickled and unpickled.

* It can automatically use your saved authentication information 
  (e.g. for MySQL, in your ~/.my.cnf file) to connect to your database
  server.

Let's use this to connect to UCSC "known genes" annotations for
human genome draft 18.  We simply create a :class:`sqlgraph.SQLTable`
object with the desired table name::

   >>> genes = sqlgraph.SQLTable('hg18.knownGene', serverInfo=serverInfo)
   >>> len(genes)
   66803
   >>> genes.columnName
   ['name', 'chrom', 'strand', 'txStart', 'txEnd', 'cdsStart', 'cdsEnd', 'exonCount', 'exonStarts', 'exonEnds', 'proteinID', 'alignID']
   >>> genes.primary_key
   None

As you can see, :class:`sqlgraph.SQLTable` has automatically analyzed
the table's schema, determining that the table lacks a primary key.
We can force it to use ``name`` as the default column for looking up
identifiers, by simply setting the ``primary_key`` attribute::

   >>> genes.primary_key = 'name'

Now we can look up rows directly; if a given query found more than
one row, it would raise a ``KeyError``::

   >>> tx = genes['uc009vjh.1']
   >>> tx.chrom
   'chr1'
   >>> tx.txStart
   55424L
   >>> tx.txEnd
   59692L
   >>> tx.strand
   '+'

Customizing SQL Database Access
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's use this table as the back-end for gene annotations on the
human genome draft 18.  We have to solve a few problems:

* Note that the attribute names used by UCSC
  (``chrom``, ``txStart``, ``txEnd``, ``strand``) are different
  than what :class:`annotation.AnnotationDB` expects.

  This is easy to fix.  :class:`annotation.AnnotationDB` accepts
  a ``sliceAttrDict`` dictionary that can provide aliases.
  For example ``sliceAttrDict=dict(id='chrom')`` would make it
  use the ``chrom`` attribute as the sequence ID.

* A more basic problem: UCSC's ``strand`` attribute returns a string
  '+' or '-', instead of an integer (1 or -1) as 
  :class:`annotation.AnnotationDB` expects.  That requires writing a little
  code to translate it.  All we have to do is write a Python 
  descriptor class to perform this translation::

   class UCSCStrandDescr(object):
      def __get__(self, obj, objtype):
         if obj.strand == '+':
            return 1
         else:
            return -1

Next we create a subclass of Pygr's standard SQL row class,
:class:`sqlgraph.TupleO`, with this descriptor bound as its
``orientation`` attribute::

   class UCSCSeqIntervalRow(sqlgraph.TupleO):
      orientation = UCSCStrandDescr()

Finally, we just tell :class:`sqlgraph.SQLTable` to use our new
row class::

   >>> txInfo = sqlgraph.SQLTable('hg18.knownGene', serverInfo=serverInfo,
   ...                             itemClass=UCSCSeqIntervalRow)
   ...
   >>> txInfo.primary_key = 'name'
   >>> tx = txInfo['uc009vjh.1']
   >>> tx.orientation
   1
   
OK, now we can use this as the slice database for our annotation.
Let's get the human genome database, and create our annotation database::

   >>> from pygr import worldbase
   >>> hg18 = worldbase.Bio.Seq.Genome.HUMAN.hg18()
   >>> annodb = annotation.AnnotationDB(txInfo, hg18,
   ...                                  sliceAttrDict=
   ...                                  dict(id='chrom', start='txStart', 
   ...                                       stop='txEnd'))
   ...
   >>> gene = annodb['uc009vjh.1']
   >>> print repr(gene.sequence), gene.sequence
   chr1[55424:59692] GTTATGAAGAAGGTAGGTGGAAACAAAGACAAAACACATATATTAGAAGAATGAATGAAATTGTAGCATTTTATTGACAATGAGATGGTTCTATTAGTAGGAATCTATTCTGCATAATTCCATTTTGTGTTTACCTTCTGGAAAAATGAAAGGATTCTGTATGGTTAACTTAAATACTTAGAGAAATTAATATGAATAATGTTAGCAAGAATAACCCTTGTTATAAGTATTATGCTGGCAACAATTGTCGAGTCCTCCTCCTCACTCTTCTGGGCTAATTTGTTCTTTTCTCCCCATTTAATAGTCCTTTTCCCCATCTTTCCCCAGGTCCGGTGTTTTCTTACCCACCTCCTTCCCTCCTTTTTATAATACCAGTGAAACTTGGTTTGGAGCATTTCTTTCACATAAAGGTACAaatcatactgctagagttgtgaggatttttacagcttttgaaagaataaactcattttaaaaacaggaaagctaaggcccagagatttttaaatgatattcccatgatcacactgtgaatttgtgccagaacccaaatgcctactcccatctcactgaGACTTACTATAAGGACATAAGGCatttatatatatatatattatatatactatatatttatatatattacatattatatatataatatatattatataatatatattatattatataatatataatataaatataatataaattatattatataatatataatataaatataatataaattatataaatataatatatattttattatataatataatatatattatataaatataatatataaattatataatataatatatattatataatataatatattttattatataaatatatattatattatataatatatattttattatataatatatattatatatttatagaatataatatatattttattatataatatatattatataatatatattatatttatatataacatatattattatataaaatatgtataatatatattatataaatatatttatatattatataaatatatatattatatataatTCTAATGGTTGAATTCCAAGAATAATCTATGGCATGAAAGATTTTACCTGTCAACAGTGGCTGGCTCTTCATGGTTGCTACAATGAGTGTGTAAGATTCTGAAGGACTCCTTTAATAAGCCTAAACTTAATGTTCAACTTAGAATAAATACAATTCTTCTAATTTTTTTTGAATAATTTTTAAAAAGTCAGAAATGAGCTTTGAAAGAATTATGGTGGTGAAGGATCCCCTCAGCAGCACAAATTCAGGAGAGAGATGTCTTAACTACGTTAGCAAGAAATTCCTTTTGCTAAAGAATAGCATTCCTGAATTCTTACTAACAGCCATGATAGAAAGTCTTTTGCTACAGATGAGAACCCTCGGGTCAACCTCATCCTTGGCATATTTCATGTGAAGATATAACTTCAAGATTGTCCTTGCCTATCAATGAAATGAATTAATTTTATGTCAATGCATATTTAAGGTCTATTCTAAATTGCACACTTTGATTCAAAAGAAACAGTCCAACCAACCAGTCAGGACAGAAATTATCTCACAATAAAAATCCTATCGTTTGTACTGTCAATGATTAGTATGATTATATTTATTACCGTGCTAAGCAGAAGAGAAATGAAGTGAATGTTCATGATTTATTCCACTATTAGACTTCTCTTTATTCTTAAAAATATTTAAGATCACTAAATTTTTATAGGACTTTAAAAACAGTAATGTGCTGCTTTGAGTGTGTAGGACTAAGAAATGGGATTCAGAGTAGTAAAGAGAAAAGTGGAATTTCCAAGCACTATGAATTACTGTTCTTTAAAAAACAGCAAAAATCAAATAACAGTATTCCTCCAAAAAAGATGGCAAGTGTAAACTCTATACCTTCATGTCTCCCGTGGAATGTTAGTGATCAATTTCCACTTCTCTCTTTTACATCTTACTTGCCCATTAACTCTTATACCTAATCCAAAGATTGTTAATATGGCTATGTCTCACTTTCAGGACACCTTTTATTTGTTACTTCTCTTCACTGCAAAACTTCTTGAAACAGTACTTATTTTCTCTCCTCCATACACAATTGAAATGGCTCTCAACTCATGCCCAGAAGTCAGTGTTCAGTCTCTCACCTGGCAGATAGCAACTTACAAAGATGCCCCAACAATACCTCCTTGTGTCTAGACAGTCATCATTATCCTTTACCTTTTTCTGTATTTATTTCTGCTCCTAAAAGGGATCTCTATGTAAAGTATTGTTATACTAGTGCTTGTTATAATTATTATCAGAGTTAAAGCCATCACAATGTTCCCAATTACTTAAAGACATTGGAATAACATTTTTTTTATTTTCCACATCTTGCCAAAAAATATTTTGTTATCAGTACCTTaataatggctattatatattgaccattactatttgctagaaaatttatatacctggtcgtatccaatcctcacagaacttctataaagttgtgctattatcacctatattttccagatgtggccgtaagactgaaatcacttaggtgacttgtctaaggtcattcagatacatagtagataacccaggatttgaacacaggcctcctagcacacaagctcatatcttaactactttaatacgttgctcGATGGGATCTTACAGGTCTTCATTCACCCCTTTCCTGCTCACACAACCACAACCTGCAGCTATTACCTATTGTTAGGCTTAAAATAATTACTTGGCTTCATTTCCAAGCTCCCTCCCTTCCAATTCACATTGAGTCCAGAGCTAAATTAAACAATCATTCAAAATTTTTCAGTAGTTCTTGTCTCTATAATAAAACAGAAATGCTTTAGAAAGCATTCCAAAATCTCTTACCAGTTTTATCTCCTATGAAAGTCCTTCACactttctctcatttaaactttattgcattttcctcactttttctcacttcacttttgaattccctattcttttatcctctgttaatttttaagtattatatttgtgatattattttttctttttttctattttttatctttcatttcattttggcctatttttttctcttAAGAACTTTAATATCACCAAATAACATGTGTGCTACAAACTGTTTTGTAGTTCAAAGAAAAAGGAGATAAACATAGAGTTATGGCATAGACTTAATCTGGCAGAGAGACAAGCATAAATAATGGTATTTTATATTAGGAATAAACCTAACATTAATGGAGACACTGAGAAGCCGAGATAACTGAATTATAAGGCATAGCCAGGGAAGTAGTGCGAGATAGAATTATGATCTTGTTGAATTCTGAATGTCTTTAAGTAATAGATTATAGAAAGTCACTGTAAGAGTGAGCAGAATGATATAAAATGAGGCTTTGAATTTGAATATAATAATTCTGACTTCCTTCTCCTTCTCTTCTTCAAGGTAACTGCAGAGGCTATTTCCTGGAATGAATCAACGAGTGAAACGAATAACTCTATGGTGACTGAATTCATTTTTCTGGGTCTCTCTGATTCTCAGGAACTCCAGACCTTCCTATTTATGTTGTTTTTTGTATTCTATGGAGGAATCGTGTTTGGAAACCTTCTTATTGTCATAACAGTGGTATCTGACTCCCACCTTCACTCTCCCATGTACTTCCTGCTAGCCAACCTCTCACTCATTGATCTGTCTCTGTCTTCAGTCACAGCCCCCAAGATGATTACTGACTTTTTCAGCCAGCGCAAAGTCATCTCTTTCAAGGGCTGCCTTGTTCAGATATTTCTCCTTCACTTCTTTGGTGGGAGTGAGATGGTGATCCTCATAGCCATGGGCTTTGACAGATATATAGCAATATGCAAGCCCCTACACTACACTACAATTATGTGTGGCAACGCATGTGTCGGCATTATGGCTGTCACATGGGGAATTGGCTTTCTCCATTCGGTGAGCCAGTTGGCGTTTGCCGTGCACTTACTCTTCTGTGGTCCCAATGAGGTCGATAGTTTTTATTGTGACCTTCCTAGGGTAATCAAACTTGCCTGTACAGATACCTACAGGCTAGATATTATGGTCATTGCTAACAGTGGTGTGCTCACTGTGTGTTCTTTTGTTCTTCTAATCATCTCATACACTATCATCCTAATGACCATCCAGCATCGCCCTTTAGATAAGTCGTCCAAAGCTCTGTCCACTTTGACTGCTCACATTACAGTAGTTCTTTTGTTCTTTGGACCAT

Victory!  We are able to serve up gene annotations over the whole
genome on our local machine, simply by plugging in to UCSC's database server!

