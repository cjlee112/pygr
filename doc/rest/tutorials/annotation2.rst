
=============================================
Accessing, Building, and Querying Annotations
=============================================

.. @CTB we should provide slice_pickle_obj for download.  It's in
   'rest/tutorials/'; how do we copy it over to html?

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
required by a default Pygr :class:`annotation.AnnotationDB` database.

First, we'll import the necessary pygr modules:
 
  >>> from pygr import seqdb, annotation, worldbase, mapping, cnestedlist

Next, let's import some useful classes.  These need to be imported
from a separate module rather than defined in a Python interpreter
session, so that they can be loaded later on by pickle:

  >>> from slice_pickle_obj import MySliceInfo, MyFunkySliceInfo

You can create the 'slice_pickle_obj' module yourself by putting
the following code in the file 'slice_pickle_obj.py'::

   class MySliceInfo(object):
       def __init__(self, id, start, stop, orientation):
           self.id = id
           self.start = start
           self.stop = stop
           self.orientation = orientation
   
   class MyFunkySliceInfo(object):
       def __init__(self, seq_id, begin, end, strand):
           self.seq_id = seq_id
           self.begin = begin
           self.end = end
           self.strand = strand

Finally, let's load in some data from pygr's test data suite:

  >>> dna_db = seqdb.SequenceFileDB('../tests/data/hbb1_mouse.fa')
  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'

Constructing an annotation database using regular Python objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

To start, let's create an empty annotation database
(:class:`annotation.AnnotationDB`) and save a couple annotation
intervals to it using its
:meth:`annotation.AnnotationDB.new_annotation()` method::

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

As a general rule, an object from a Pygr database has
two attributes that identify it:
``id`` gives its unique identifier (primary key) in that database,
and ``db`` points to the database object itself::

  >>> a = annodb['A']
  >>> a.id
  'A'
  >>> a.db is annodb
  True

While an annotation behaves like a sequence in most respects,
it does *not* provide a string value by default::

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

Note that the usual sequence rules apply to annotation objects: '-'
returns an annotation that maps to the reverse strand::

  >>> -a
  -annotA[0:50]

and the :attr:`pathForward` attribute always returns the original annotation,
no matter what slice or reverse-complement operations have been performed:

  >>> (-a[10:20]).pathForward
  annotA[0:50]

This lets you do some neat tricks; for example, if an annotation
represented a gene's location on the genome, you could get all of the
sequence upstream of the gene, *relative to the annotations
orientation*, by using ``a.before()`` (and ``a.after()`` to get the
sequence after the gene).

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

This changes the default :meth:`repr` output for objects from this database:

  >>> for k in annodb:
  ...    print repr(annodb[k])
  foo:A[0:50]
  foo:B[0:100]

Using sliceAttrDict to point AnnotationDB at different attributes for slice info
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Above, the :class:`annotation.AnnotationDB` database is retrieving the sequence
and interval information from expected attributes on the slice objects
-- :attr:`id`, :attr:`start`, :attr:`stop`, and :attr:`orientation`.
That's great if you're defining and creating the slice objects
yourself, but what if you are taking in objects from a different
library that uses different naming conventions?  Easy -- you can give
:class:`annotation.AnnotationDB` a dictionary, :attr:`sliceAttrDict`, that tells it
how to map from the slice attributes into the attributes it uses::

  >>> annodb = annotation.AnnotationDB({}, dna_db, annotationType='foo:', sliceAttrDict=dict(id='seq_id', start='begin', stop='end', orientation='strand'))

  >>> slice1 = MyFunkySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MyFunkySliceInfo(seq_id, 300, 400, -1)

And, as you can see, this results in the same actual annotations::

  >>> annot1 = annodb.new_annotation('C', slice1)
  >>> annot2 = annodb.new_annotation('D', slice2)

  >>> for k in annodb:
  ...    print repr(annodb[k]), repr(annodb[k].sequence)
  foo:C[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  foo:D[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  
Using tuples for slice info
^^^^^^^^^^^^^^^^^^^^^^^^^^^

What if you're just dealing with tuples or lists containing the
slice information?  You can give indices (0, 1, 2, etc.) instead of
attribute names with :attr:`sliceAttrDict`, like so::

  >>> annodb = annotation.AnnotationDB({}, dna_db, annotationType='bar:', sliceAttrDict=dict(id=0, start=1, stop=2, orientation=3))

  >>> annot1 = annodb.new_annotation('E', (seq_id, 0, 50, 1))
  >>> annot2 = annodb.new_annotation('F', (seq_id, 300, 400, -1))

And again, you get the same actual annotations::

  >>> for k in annodb:
  ...    print repr(annodb[k]), repr(annodb[k].sequence)
  bar:E[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  bar:F[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

Using a pre-built dictionary of slice info objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

So far, we've been creating an empty :class:`annotation.AnnotationDB` and then
adding annotations with :meth:`annotation.AnnotationDB.new_annotation`.  You can also pass
in a dictionary that contains some slice information already, and
:class:`annotation.AnnotationDB` will automatically wrap them and make them available
as annotation objects::

  >>> slicedb = { 'slice1' : MySliceInfo(seq_id, 0, 50, +1),
  ...             'slice2' : MySliceInfo(seq_id, 300, 400, -1) }

  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='baz:')

  >>> for k in annodb:
  ...    print repr(annodb[k]), repr(annodb[k].sequence)
  baz:slice1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  baz:slice2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

Note that this conversion happens on the fly, so you can pass in a large
dictionary of slices and it won't take any longer to create the
:class:`annotation.AnnotationDB` than if you use a small dictionary of slices.
  
Saving and restoring slice info dictionaries manually
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Now suppose you've gone to all the effort of creating your slice information
and annotations, and you want to save them for later use.   There are several
ways to do this; we'll start by showing you the brute-fore manual way, with
shelve.  First, create an empty shelve db::

  >>> import shelve

  >>> slicedb = shelve.open('slicedb.db', 'c')

Pass it into the :class:`annotation.AnnotationDB` constructor, and populate it with
some annotations::

  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='baz:')

  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('A', slice1)
  >>> annot2 = annodb.new_annotation('B', slice2)

  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  baz:B[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  baz:A[0:50] gi|171854975|dbj|AB364477.1|[0:50]

Now, close the slicedb and delete both the annodb and slicedb objects,
as if you were closing the Python session::
  
  >>> slicedb.close()
  >>> del slicedb, annodb

OK, pretend you're in a new Python session and you want to retrieve those
annotations again.  All you have to do is re-open the slicedb and pass
it into :class:`annotation.AnnotationDB`::

  >>> slicedb = shelve.open('slicedb.db', 'r')
  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='baz:')

Voila!  You have all of your annotations back::

  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  baz:B[0:100] -gi|171854975|dbj|AB364477.1|[300:400]
  baz:A[0:50] gi|171854975|dbj|AB364477.1|[0:50]

.. @CTB # cover: unpicklable db error message from shelve; cannot load class,
   #   from worldbase
   # 2.

Saving an AnnotationDB into worldbase
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It's inconvenient to have to remember where you saved things, though,
especially if you're dealing with multiple annotation and sequence
databases.  This is where :mod:`worldbase` comes in handy.

First, reload the database using an absolute path, so that worldbase
knows exactly where to go to get the files::

  >>> import os.path

  >>> filename = os.path.abspath('../tests/data/hbb1_mouse.fa')
  >>> dna_db = seqdb.SequenceFileDB(filename)
  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'

Next, create an annotation database with an empty dictionary::

  >>> annodb = annotation.AnnotationDB({}, dna_db)

Add slice information::

  >>> slice1 = MySliceInfo(seq_id, 0, 50, +1)
  >>> slice2 = MySliceInfo(seq_id, 300, 400, -1)

  >>> annot1 = annodb.new_annotation('A', slice1)
  >>> annot2 = annodb.new_annotation('B', slice2)

...and verify that it's there::

  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  annotA[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  annotB[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

Now, give both the DNA database and the annodb docstrings, and
save them into worldbase::
  
  >>> dna_db.__doc__ = 'DNA database for annotation tutorial'
  >>> worldbase.Bio.pygr.annotationTutorial.dna_db = dna_db

  >>> annodb.__doc__ = 'example annotationdb based on objects'
  >>> worldbase.Bio.pygr.annotationTutorial.annodb1 = annodb

Commit the worldbase changes, and delete all of the objects (again,
pretend that we're exiting Python)::

  >>> worldbase.commit()
  >>> del annodb, dna_db
  >>> worldbase.clear_cache()

Now, pretend we're starting up a new session.  You can retrieve the
annodb object easily, just by remembering the worldbase name::

  >>> annodb = worldbase.Bio.pygr.annotationTutorial.annodb1()
  >>> for k in annodb:
  ...     print repr(annodb[k]), repr(annodb[k].sequence)
  annotA[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  annotB[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

What's particularly nice about this is that even though you didn't
explicitly load the DNA database, worldbase knows that annodb
depends upon dna_db, and so it automatically loads it for you,
behind the scenes.  Neat, eh?

  >>> dna_db = annodb.seqDB
  >>> print repr(dna_db[seq_id])
  gi|171854975|dbj|AB364477.1|[0:444]

One note: by default, :class:`annotation.AnnotationDB` will pickle its
dictionary of slice information if it has to, and loading an
:class:`annotation.AnnotationDB` object will load the entire
dictionary. So, the above technique doesn't scale well; instead, you
want to use a pickleable mapping, below, where only those slice objects
that you request will be loaded, on demand.
  
Building a pickleable mapping
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In the previous example, we constructed an
:class:`annotation.AnnotationDB` starting with an empty mapping,
and then populated it by adding annotations one at a time; what
if we already have a mapping that we want to save?  It turns out
we can't use a straight shelf, because they can't themselves
be pickled for technical reasons; instead, you need to use a
:class:`mapping.PicklableShelve` type.  First, create it::

  >>> filename = os.path.abspath('slicedb2.db')
  >>> slicedb2 = mapping.PicklableShelve(filename, 'nw')

Now, populate it with slice information and save/close::

  >>> slicedb2['slice1'] = MySliceInfo(seq_id, 0, 50, +1)
  >>> slicedb2['slice2'] = MySliceInfo(seq_id, 300, 400, -1)
  >>> slicedb2.close()

Then, reopen it in read-only mode and pass it into
:class:`annotation.AnnotationDB`::

  >>> slicedb2 = mapping.PicklableShelve(filename, 'r')

  >>> annodb2 = annotation.AnnotationDB(slicedb2, dna_db, annotationType='baz:')

  >>> for k in annodb2:
  ...     print repr(annodb2[k]), repr(annodb2[k].sequence)
  baz:slice1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  baz:slice2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

This annodb can be saved directly into worldbase, just as before,
but this time the underlying slice info will be stored in the
:class:`mapping.PicklableShelf` rather than in a single lump
dictionary::
  
  >>> annodb2.__doc__ = 'example annotationdb based on objects'
  >>> worldbase.Bio.pygr.annotationTutorial.annodb2 = annodb2

  >>> worldbase.commit()
  >>> del annodb2, slicedb2
  >>> worldbase.clear_cache()

And voila, this works as well!

  >>> annodb2 = worldbase.Bio.pygr.annotationTutorial.annodb2()
  >>> for k in annodb2:
  ...     print repr(annodb2[k]), repr(annodb2[k].sequence)
  baz:slice1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  baz:slice2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

Retrieving slice information from a SQL database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The techniques above work well, but quite often we already have our
slice information loaded into a SQL database.  How can we make use
of an existing SQL database?

First, for our example, we need to create the database and add some
slice information::

  >>> from pygr import sqlgraph, seqdb, annotation
  >>> sqlite = sqlgraph.import_sqlite()
  >>> import testlib

(Note that we use 'import_sqlite' in order to be compatible with older
versions of Python that didn't include the sqlite3 module.)

  >>> db = sqlite.connect('slicedb.sqlite')
  >>> c = db.cursor()
  >>> _ = c.execute('DROP TABLE IF EXISTS annotations;')
  >>> _ = c.execute('CREATE TABLE annotations (k INTEGER PRIMARY KEY, seq_id TEXT, start INT, stop INT, orientation INT);')

  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'

  >>> _ = c.execute("INSERT INTO annotations (seq_id, start, stop, orientation) VALUES (?, ?, ?, ?)", (seq_id, 0, 50, +1))
  >>> _ = c.execute("INSERT INTO annotations (seq_id, start, stop, orientation) VALUES (?, ?, ?, ?)", (seq_id, 300, 400, -1))

  >>> db.commit()

Now, load it into pygr objects::

  >>> from pygr.sqlgraph import SQLiteServerInfo

  >>> dna_db = seqdb.SequenceFileDB('../tests/data/hbb1_mouse.fa')

The slicedb can be constructed using :class:`sqlgraph.SQLTable`, which
takes the table name and (for sqlite-based DBs) the sqlite database
filename, packaged in a serverInfo object:

  >>> slicedb = sqlgraph.SQLTable('annotations', serverInfo=SQLiteServerInfo('slicedb.sqlite'))

As you can see, now we can directly access slices using the primary
IDs of the rows of slice information::

  >>> print slicedb[1].id, slicedb[1].seq_id, slicedb[1].start
  1 gi|171854975|dbj|AB364477.1| 0

And of course we can pass this slicedb directly into the
:class:`annotation.AnnotationDB` constructor::

  >>> annodb = annotation.AnnotationDB(slicedb, dna_db, annotationType='sql:', sliceAttrDict=dict(id='seq_id'))

  >>> for k in annodb:
  ...     print k, repr(annodb[k]), repr(annodb[k].sequence)
  1 sql:1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  2 sql:2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

Note that with a minimum of extra work, you can save it into worldbase::

  >>> from pygr import worldbase

  >>> dna_db.__doc__ = 'DNA database for annotation tutorial'
  >>> worldbase.Bio.pygr.annotationTutorial.dna_db = dna_db

  >>> annodb.__doc__ = 'example annotationdb based on sqlite rows'
  >>> worldbase.Bio.pygr.annotationTutorial.annodb3 = annodb

  >>> worldbase.commit()
  >>> del annodb, slicedb
  >>> worldbase.clear_cache()

  >>> annodb3 = worldbase.Bio.pygr.annotationTutorial.annodb3()

  >>> for k in annodb3:
  ...     print k, repr(annodb3[k]), repr(annodb3[k].sequence)
  1 sql:1[0:50] gi|171854975|dbj|AB364477.1|[0:50]
  2 sql:2[0:100] -gi|171854975|dbj|AB364477.1|[300:400]

pygr's ability to interact with many sources of slice data --
dictionaries, shelves, and SQL databases -- in virtually identical
ways is quite powerful, as is the ability to save this information
into worldbase and retrieve it without caring about the storage
method.

.. # 4. using 'addAnnotation'.
.. @CTB # suggest read alignment tutorial first!

Using an NLMSA to retrieve annotations by sequence position
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's do one more trick with annotations: let's retrieve them by
their sequence interval.

First, load in some annotations::

  >>> annodb = worldbase.Bio.pygr.annotationTutorial.annodb3()

Now, create an NLMSA and add the annotations into the NLMSA using
:meth:`cnestedlist.NLMSA.addAnnotation`::

  >>> al = cnestedlist.NLMSA('foo', 'memory', pairwiseMode=True)

  >>> for k in annodb:
  ...     al.addAnnotation(annodb[k])

  >>> al.build()

Once we build the NLMSA, we can now retrieve annotations that
overlap any given sequence or interval on that sequence::

  >>> dna_db = worldbase.Bio.pygr.annotationTutorial.dna_db()
  >>> seq_id = 'gi|171854975|dbj|AB364477.1|'
  >>> seq = dna_db[seq_id]

  >>> print al[seq].keys()
  [sql:1[0:50], -sql:2[0:100]]

  >>> print al[seq[:100]].keys()
  [sql:1[0:50]]
