
=============================================
Accessing, Building, and Querying Annotations
=============================================

Purpose
^^^^^^^

This tutorial teaches you the finer points of constructing
annotation databases, mapping them onto associated sequence
databases, and saving them in :mod:`worldbase`.  You should 
understand Pygr sequences (see :doc:`sequence`).  While not
required, you may find it helpful to view the :doc:`db_basic`
tutorial, to get comfortable with Pygr's different database types.

Pygr Sequence Annotations
^^^^^^^^^^^^^^^^^^^^^^^^^

*Annotation* -- information bound to specific intervals of a genome
or sequence -- is an essential concept in bioinformatics.  We would like to
be able to store and query annotations naturally as part of working with
sequence datasets of any size, from single sequences to multigenome
alignments.  Pygr makes this fairly easy.

An annotation is an interval (i.e. it has length, and can be sliced,
or negated to get the opposite strand) that has bound attributes giving
biological information about the annotation.  It acts like a little coordinate
system, i.e. ``annotation[0]`` is the first position in the annotation;
``annotation[-10:]`` is the last ten positions of the annotation etc.
Any subslice of the annotation gives its coordinates and orientation
relative to the original annotation.  

Let's set up a basic example, by  opening a sequence database to
annotate, and a ``MySliceInfo`` class that will store the basic
coordinate attributes (``id``, ``start``, ``stop``, ``orientation``
required by a default Pygr :class:`annotation.AnnotationDB` database::
 
  >>> from slice_pickle_obj import MySliceInfo, MyFunkySliceInfo
  >>> from pygr import seqdb, annotation, worldbase

  >>> dna_db = seqdb.SequenceFileDB('../tests/data/hbb1_mouse.fa')
  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'

Constructing an annotation database using regular Python objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To start simple, let's just save a couple annotation intervals
to our database using its :meth:`annotation.AnnotationDB.new_annotation()`
method::

  >>> annodb = annotation.AnnotationDB({}, dna_db)

  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('A', slice1)
  >>> annot2 = annodb.new_annotation('B', slice2)

An annotation object or slice is associated with the corresponding
sequence interval of the sequence to which it is bound.  To obtain that
sequence interval, simply request the annotation's :attr:`sequence`
attribute.  Use this if you want to get its sequence string via ``str``,
for example::

  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  annotA[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  annotB[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

As a general, an object from a Pygr database have
two attributes that identify it as belonging to its database:
``id`` gives its unique identifier (primary key) in that database,
and ``db`` points to the annotation database object itself::

  >>> a = annodb['A']
  >>> a.id
  'A'
  >>> a.db is annodb
  True

While an annotation behaves like a sequence in most respects,
usually it will *not* provide a string value::

  >>> str(a)
   Traceback (most recent call last):
     File "<stdin>", line 1, in <module>
     File "/Users/leec/projects/pygr/pygr/sequence.py", line 483, in __str__
       return self.path.strslice(self.start,self.stop)
     File "/Users/leec/projects/pygr/pygr/annotation.py", line 61, in strslice
       Use its sequence attribute to get a sequence object representing this interval.''')
   ValueError: this is an annotation, and you cannot get a sequence string from it.
   Use its sequence attribute to get a sequence object representing this interval.

One exception to this rule: :class:`annotation.TranslationAnnot`
annotations, which represent the protein translation of an underlying
nucleotide sequence interval.  
  
Modifying annotationType
^^^^^^^^^^^^^^^^^^^^^^^^

An annotation object or slice always has an
:attr:`annotation.AnnotationDB.annotationType` 
attribute giving a string identifier for
its annotation type.  You can set this by passing an argument::

  >>> annodb = annotation.AnnotationDB({}, dna_db, annotationType='foo:')

  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('A', slice1)
  >>> annot2 = annodb.new_annotation('B', slice2)

  >>> for k in annodb:
  ...    print repr(annodb[k])
  foo:A[0:50]
  foo:B[0:100]

Using sliceAttrDict to point AnnotationDB at different attributes for slice info
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  >>> annodb = annotation.AnnotationDB({}, dna_db, annotationType='foo:', sliceAttrDict=dict(id='seq_id', start='begin', stop='end', orientation='strand'))

  >>> slice1 = MyFunkySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MyFunkySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('C', slice1)
  >>> annot2 = annodb.new_annotation('D', slice2)

  >>> for k in annodb:
  ...    print repr(annodb[k]), repr(annodb[k].sequence)
  foo:C[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  foo:D[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  
Using tuples for slice info
^^^^^^^^^^^^^^^^^^^^^^^^^^^

  >>> annodb = annotation.AnnotationDB({}, dna_db, annotationType='bar:', sliceAttrDict=dict(id=0, start=1, stop=2, orientation=3))

  >>> annot1 = annodb.new_annotation('E', (seq_id, 0, 50, 1))
  >>> annot2 = annodb.new_annotation('F', (seq_id, 300, 400, -1))

  >>> for k in annodb:
  ...    print repr(annodb[k]), repr(annodb[k].sequence)
  bar:E[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  bar:F[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

Using a pre-built dictionary of slice info objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  >>> slicedb = { 'slice1' : MySliceInfo(seq_id, 0, 50, +1),
  ...             'slice2' : MySliceInfo(seq_id, 300, 400, -1) }

  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='baz:')

  >>> for k in annodb:
  ...    print repr(annodb[k]), repr(annodb[k].sequence)
  baz:slice1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  baz:slice2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  
Saving and restoring slice info dictionaries manually
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  >>> import shelve

  >>> slicedb = shelve.open('slicedb.db', 'c')

  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='baz:')

  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('A', slice1)
  >>> annot2 = annodb.new_annotation('B', slice2)

  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  baz:B[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  baz:A[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  
  >>> slicedb.close()
  >>> del slicedb, annodb

  >>> slicedb = shelve.open('slicedb.db', 'c')
  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='baz:')

  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  baz:B[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  baz:A[0:50] gi|171854975|dbj|AB364477.1|[0:50]
# cover: unpicklable db error message from shelve; cannot load class,
#   from worldbase
# 2.

  >>> import os.path
  >>> from slice_pickle_obj import MySliceInfo, MyFunkySliceInfo
  >>> from pygr import seqdb, annotation, worldbase

  >>> filename = os.path.abspath('../tests/data/hbb1_mouse.fa')
  >>> dna_db = seqdb.SequenceFileDB(filename)
  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'

Saving an AnnotationDB into worldbase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  >>> annodb = annotation.AnnotationDB({}, dna_db)

  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('A', slice1)
  >>> annot2 = annodb.new_annotation('B', slice2)

  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  annotA[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  annotB[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  
  >>> dna_db.__doc__ = 'DNA database for annotation tutorial'
  >>> worldbase.here.annotationTutorial.dna_db = dna_db

  >>> annodb.__doc__ = 'example annotationdb based on objects'
  >>> worldbase.here.annotationTutorial.annodb1 = annodb

  >>> worldbase.commit()
  >>> del annodb
  >>> worldbase.clear_cache()

  >>> annodb = worldbase.here.annotationTutorial.annodb1()
  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  annotA[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  annotB[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  
Building a pickleable mapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  >>> from pygr import mapping
  >>> import os.path

  >>> filename = os.path.abspath('slicedb2.db')
  >>> slicedb2 = mapping.PicklableShelve(filename, 'nw')

  >>> slicedb2['slice1'] = MySliceInfo(seq_id, 0, 50, +1)
  >>> slicedb2['slice2'] = MySliceInfo(seq_id, 300, 400, -1)
  >>> slicedb2.close()

  >>> slicedb2 = mapping.PicklableShelve(filename, 'r')

  >>> annodb2 = annotation.AnnotationDB(slicedb2, dna_db, annotationType='baz:')

  >>> for k in annodb2:
  ...     print repr(annodb2[k]), repr(annodb2[k].sequence)
  baz:slice1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  baz:slice2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  
  >>> annodb2.__doc__ = 'example annotationdb based on objects'
  >>> worldbase.here.annotationTutorial.annodb2 = annodb2

  >>> worldbase.commit()
  >>> del annodb2, slicedb2
  >>> worldbase.clear_cache()

  >>> annodb2 = worldbase.here.annotationTutorial.annodb2()
  >>> for k in annodb2:
  ...     print repr(annodb2[k]), repr(annodb2[k].sequence)
  baz:slice1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  baz:slice2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
# 3.

Retrieving slice information from a SQL database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, create the database:

  >>> import sqlite3
  >>> import testlib

  >>> db = sqlite3.connect('slicedb.sqlite')
  >>> c = db.cursor()
  >>> _ = c.execute('DROP TABLE IF EXISTS annotations;')
  >>> _ = c.execute('CREATE TABLE annotations (k INTEGER PRIMARY KEY, seq_id TEXT, start INT, stop INT, orientation INT);')

  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'

  >>> _ = c.execute("INSERT INTO annotations (seq_id, start, stop, orientation) VALUES (?, ?, ?, ?)", (seq_id, 0, 50, +1))
  >>> _ = c.execute("INSERT INTO annotations (seq_id, start, stop, orientation) VALUES (?, ?, ?, ?)", (seq_id, 300, 400, -1))

  >>> db.commit()

Now, load it into pygr objects:

  >>> from pygr import sqlgraph, seqdb, annotation
  >>> from pygr.sqlgraph import SQLiteServerInfo

  >>> dna_db = seqdb.SequenceFileDB('../tests/data/hbb1_mouse.fa')
  >>> slicedb = sqlgraph.SQLTable('annotations', serverInfo=SQLiteServerInfo('slicedb.sqlite'))

  >>> print slicedb[1].id, slicedb[1].seq_id, slicedb[1].start
  1 gi|171854975|dbj|AB364477.1| 0

  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='sql:', sliceAttrDict=dict(id='seq_id'))

  >>> for k in annodb:
  ...     print k, repr(annodb[k]), repr(annodb[k].sequence)
  1 sql:1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  2 sql:2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

Note that with a minimum of extra work, you can save it into worldbase:

  >>> from pygr import worldbase

  >>> dna_db.__doc__ = 'DNA database for annotation tutorial'
  >>> worldbase.here.annotationTutorial.dna_db = dna_db

  >>> annodb.__doc__ = 'example annotationdb based on sqlite rows'
  >>> worldbase.here.annotationTutorial.annodb3 = annodb

  >>> worldbase.commit()
  >>> del annodb, slicedb
  >>> worldbase.clear_cache()

  >>> annodb3 = worldbase.here.annotationTutorial.annodb3()

  >>> for k in annodb3:
  ...     print k, repr(annodb3[k]), repr(annodb3[k].sequence)
  1 sql:1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  2 sql:2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

# 4. using 'addAnnotation'.
# suggest read alignment tutorial first!

Using an NLMSA to retrieve annotations by sequence position
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

  >>> from slice_pickle_obj import MySliceInfo
  >>> from pygr import seqdb, annotation, cnestedlist

  >>> dna_db = seqdb.SequenceFileDB('../tests/data/hbb1_mouse.fa')
  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'
  >>> seq = dna_db[seq_id]

###

  >>> annodb = annotation.AnnotationDB({}, dna_db)

  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('A', slice1)
  >>> annot2 = annodb.new_annotation('B', slice2)

###

  >>> al = cnestedlist.NLMSA('foo', 'memory', pairwiseMode=True)

  >>> for k in annodb:
  ...     al.addAnnotation(annodb[k])

  >>> al.build()

  >>> print al[seq].keys()
  [annotA[0:50], -annotB[0:100]]

  >>> print al[seq[:100]].keys()
  [annotA[0:50]]
