:mod:`annotation` --- Annotation database interfaces
====================================================

.. module:: annotation
   :synopsis: Annotation database interfaces.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>


This module provides a general interface (:class:`AnnotationDB`) 
for sequence annotation databases.
This interface follows several principles:

* Pygr's approach to annotation is explicitly "database-centric".
  That is, rather than constructing annotation objects one by one,
  you instead specify a *sliceDB* database of annotation coordinates;
  each *sliceDB* value marks a contiguous interval on a specified sequence
  ID, to be marked as one annotation.  *sliceDB* should follow a dict-like
  interface; it maps an annotation ID key to a coordinate interval value.
  Next, you provide a *seqDB* sequence database containing the sequence
  objects to be annotated.  Finally, you construct an
  :class:`annotation.AnnotationDB` with both of these arguments;
  given an annotation ID, it returns a annotation object.

* An *annotation object* acts like a sliceable interval
  (representing the region of sequence that it annotates)
  with annotation attributes that provide further information or relations
  for that annotation.  An annotation object always has three identifying attributes:
  :attr:`db`, which gives the :class:`AnnotationDB` object containing this
  annotation;
  :attr:`id`, which gives the unique identifier of this annotation within
  its :class:`AnnotationDB`;
  and :attr:`annotationType`, which gives a string identifier for the
  type of annotation, e.g. "exon".
  All slices derived from an annotation object retain its
  ``db``, ``id`` and ``annotationType`` attributes.
  
* An annotation will generally have additional attributes that
  describe its specific biological information; for example,
  a gene annotation might have a :attr:`symbol` attribute giving
  its gene symbol.  These annotation-specific attributes are accessed
  from the associated *sliceDB* value for that annotation; see below for details.
  
* You can always obtain the actual sequence object corresponding
  to an annotation object or slice, by simply requesting its
  :attr:`sequence` attribute.
  
* An annotation object can itself be sliced
  (e.g. ``e[:10]`` gets the slice representing
  the first ten bases of the exon); such annotation slices can themselves
  also be sliced.  More generally, an annotation is itself a coordinate
  system that can be sliced, negated (only for nucleotide sequence
  annotations, to obtain the opposite strand), and have a length
  (obtainable as usual via the builtin ``len()`` function).
  
* Annotation objects provide a consistent interface
  to the annotation coordinate system, based on the :class:`SeqPath`
  class.  Pretty much anything that you can do with :class:`SeqPath`
  you can also do with an annotation or annotation slice.
  You can tell whether
  an annotation is on the same strand (or opposite strand)
  from the original annotation in the usual way, by checking
  its :attr:`orientation` attribute, which is +1 for same strand
  and -1 for opposite strand.  You can also obtain the entire
  original annotation in the usual way, by accessing the :attr:`pathForward`
  attribute of any annotation slice.
  
* One difference is that you (usually) cannot obtain the string value
  (letters of the corresponding sequence) directly from an annotation
  object or slice.  Instead, you must first obtain the corresponding
  sequence slice, via its :attr:`sequence` attribute, to which
  you can then apply the :meth:`str()` builtin function.
  
* Because annotations obey the
  coordinate system and slicing behaviors of sequence objects,
  they can be aligned in an NLMSA sequence alignment just like any
  sequence.  This provides a powerful and convenient way for
  querying annotation databases.
  
* The mapping of an annotation object to the sequence region it
  represents is trivial, i.e. simply request its :attr:`sequence` attribute.
  The reverse mapping (for any region of sequence, find the annotation(s)
  that map to that region) is best performed by creating an NLMSA alignment
  object and saving the mapping as follows::
  
     nlmsa = cnestedlist.NLMSA('myAnnotDB','w', # STORE SEQ->ANNOT MAPPING AS AN ALIGNMENT
                               pairwiseMode=True,bidirectional=False)
     for a in annoDB.itervalues(): # GET EACH ANNOTATION OBJ IN DATABASE
       nlmsa.addAnnotation(a) # SAVE ALIGNMENT OF ITS SEQ INTERVAL TO THIS ANNOTATION
     nlmsa.build() # CREATE FINAL INDEXES FOR THE ALIGNMENT DATABASE
  
  Later you can get the list of annotations in some sequence interval ``s``
  as easily as::
  
     for a in nlmsa[s]: # FIND ANNOTATIONS THAT MAP TO s
       # DO SOMETHING...
  
* Based on your worldbase schema, an annotation object may
  have other attributes that connect it to other data.
  For example, an object ``e`` representing an exon annotation
  might have attributes that link it
  to its *splice graph*.  ``for e2,splice in e.next.items()`` would iterate
  through the list of exons it is connected to by a forward splice, etc.
  
AnnotationDB
------------

.. class:: AnnotationDB(sliceDB, seqDB, annotationType=None, itemClass=AnnotationSeq, itemSliceClass=AnnotationSlice, sliceAttrDict=dict(), filename=None, mode='r', maxCache=None)

   Constructs an annotation database using several arguments:

   *sliceDB*, a database that takes an annotation ID as a key, and returns
   a slice information object with attributes that give the sequence ID and start/stop
   coordinates of the sequence interval representing the annotation,
   and any other information about the annotation.  In general, any
   attribute on the slice information object, will also be accessible
   on the corresponding annotation object and slices derived from it.

   You can give ``None`` as the *sliceDB*, in which case the
   AnnotationDB will create one for you, either using an in-memory dictionary,
   or by opening a Python shelve file if you provide the *filename* argument;
   see below.

   *seqDB*, a sequence database that takes a sequence ID as a key, and
   returns a sequence object.

   *annotationType* should be a string identifier for the type of
   annotation.  This will be propagated to all annotation objects / slices
   derived from this annotation database.

   *itemClass*: the class to use for constructing an annotation object
   to be returned from the AnnotationDB.__getitem__.  You can extend the
   behavior of annotation objects by subclassing :class:`AnnotationSeq`.
   If the AnnotationDB participates in important schema relations,
   :mod:`worldbase` may add properties to the *itemClass* that implement
   its schema relations to other database containers.  (See the reference
   docs on :mod:`metabase` below for details).

   *itemSliceClass*: the class to use for slices of annotation
   objects returned from the AnnotationDB.__getitem__.  You can extend the
   behavior of annotation objects by subclassing :class:`AnnotationSlice`.
   If the AnnotationDB participates in important schema relations,
   :mod:`worldbase` may add properties to the *itemSliceClass* that implement
   its schema relations to other database containers.  (See the reference
   docs on :mod:`metabase` below for details).

   *sliceAttrDict*, a dictionary providing the attribute name aliases
   for attributes on annotation objects to access attributes or tuple values
   in the sliceInfo objects.  The minimal required attributes are the
   sequence ID, start and stop coordinates in each object returned from *sliceDB*.
   For example::

      sliceAttrDict = dict(id='chromosome',start='gen_start',stop='gen_stop')

   would make it use ``s.chromosome,s.gen_start,s.gen_stop`` as the ID and interval
   coordinates for each slice information object ``s``.  Note: the start,stop
   coordinates should follow the :class:`sequence.SeqPath` sign convention, i.e. positive
   coordinates mean an interval on the positive strand, and negative coordinates
   mean an interval on the negative strand (i.e. the reverse complement of
   the positive strand.  See the reference documentation on :class:`sequence.SeqPath` above
   for details).

   If the sliceAttrDict (or sliceInfo object directly) provides a :attr:`orientation`
   attribute, it will be used to be change positive intervals to negative intervals
   if the :attr:`orientation` attribute is negative.  This gives the user an alternative
   method to represent orientation: give all coordinates in positive orientation
   (positive integer values), and give an :attr:`orientation` attribute that
   is a negative value if the interval should be reversed (to negative orientation).

   If a sliceAttrDict value is an integer, then it will not be treated as an
   attribute name, but instead will be used as an index, treating the sliceInfo
   object as a tuple.  This makes it possible to use a *sliceDB* whose
   items are tuples.  Here's an example::

      exon_db = AnnotationDB(exon_slices, db,
      sliceAttrDict=dict(id=0, orientation=3, # GIVE ATTR INTERFACE TO 2PLE
      transcript_id=4, start=5, stop=6))

   Additional tuples values beyond the required :attr:`id,start,stop`
   attributes may be used to provide additional informative attributes
   for the individual annotations.

   *filename*, if not None, indicates a Python shelve file to store the
   *sliceDB* info.  It will be opened according to the *mode* argument;
   see the Python :mod:`shelve` docs for details.  Note: if you write data
   to an :class:`AnnotationDB` stored using a shelve, you *must* call its
   :meth:`close()` method to ensure that all data is saved to the Python
   shelve file!

   *maxCache*, if not None, specifies the maximum number of annotation
   objects to keep in the cache.  For large databases, this is an important
   parameter for ensuring that the :class:`AnnotationDB` will not consume too much
   memory (e.g. if you iterate over all or a large fraction of the annotations
   in the database).

   *autoGC=True* makes :class:`AnnotationDB` automatically
   flush unused annotations
   from the cache using :class:`classutil.RecentValueDictionary`.

   Note: the argument *itemAttrDict* is deprecated, and does nothing.  Do
   not use it, as there is currently no need.  The annotation and slice
   objects will automatically reflect whatever attributes are present on
   your associated *sliceDB* objects; see :class:`AnnotationSeq`
   below for details.


.. method:: AnnotationDB.__getitem__(id)

   Get the annotation object with primary key *id*.  This annotation object
   is both a sequence interval (representing the region of sequence that it
   annotates, e.g. for an exon, the region of genomic sequence that constitutes
   that exon), and also an annotation (i.e. it may have additional attributes
   from the slice information object, that give useful information about this
   annotation).

Saving New Annotations
----------------------

Ordinarily, you use an :class:`AnnotationDB` as a read-only database; i.e.
you use it simply to access annotations derived from data already stored in
the *sliceDB*.

To save *new* annotations to the :class:`AnnotationDB`, 
what you are really doing is
saving new coordinate information to the *sliceDB*.  You could do that directly,
but :class:`AnnotationDB` provides methods for doing this more
conveniently.  It will even run homology searches for you and automatically
turn the results into new annotations.  To use these methods:

* *sliceDB* must be writeable.

* alternatively, if you pass *sliceDB=None*, :class:`AnnotationDB` will
  try to create a new shelve for you, using the *filename* and *mode* 
  optional arguments.

To save a new annotation, use either of the following two convenience
methods, instead of :meth:`__setitem__`, which is not permitted (because
there would be no way of guaranteeing that the annotation object provided
by the user could be stored persistently).

.. method:: AnnotationDB.new_annotation(k,sliceInfo)

   Use this method to save new annotations to an :class:`AnnotationDB`,
   instead of using ``annoDB[k] = v``, which is not permitted.
   Creates a new annotation with ID *k*, based on *sliceInfo*,
   which must provide a sequence ID, start, stop, either by attribute
   names or integer indices (as specified by the *sliceAttrDict*),
   and any addition attributes that we want to associate with this annotation.
   *sliceInfo* is saved in the :class:`AnnotationDB` 's *sliceDB*.
   Returns an annotation object associated with *sliceInfo*.


.. method:: AnnotationDB.add_homology(seq, search, id=None, idFormat='\%s_\%d', autoIncrement=False, maxAnnot=999999, maxLoss=None, sliceInfo=None, **kwargs)

   Search for homology to *seq* in the sequence database self.seqDB
   using the named method specified by the *search* argument,
   and filtered using the :meth:`cnestedlist.NLMSASlice.keys()`
   function, and store
   them as new annotations in the annotation database.

   *seq* can be a string or sequence object or slice.

   *search* should be a homology search object such as
   :class:`blast.BlastMapping` that can be used as a callable function.
   The *search* function must take a sequence object as its
   first argument, and optional keyword arguments for controlling its
   search parameters.  Note: since both searching and filtering keyword
   arguments are passed as a single dictionary, the function should not
   die on unexpected keyword arguments.  The function must return an
   alignment object (e.g. :class:`cnestedlist.NLMSA`).

   Deprecated: *search* can be a string, in which case it will be treated as an
   attribute name for a method on ``self.seqDB`` to run the homology search.
   This only works if ``self.seqDB`` is the deprecated class 
   :class:`blast.BlastDB`.

   *id* if not None, will be used as the annotation ID.  Otherwise,
   the *seq.id* will be used as the annotation ID.

   *idFormat* controls the generation of ID strings for cases where
   multiple hits pass the search and filter criteria.  It simply appends
   an integer counter to the id.

   *autoIncrement=True* forces it to generate its own integer IDs for
   each new annotation.

   *maxAnnot* specifies the maximum numbers of hits that will be
   processed for *seq*.  If the number of hits passing both search
   and filter criteria exceed this number, a :class:`ValueError` will be raised.

   *maxLoss* if not None, must be an integer indicating the maximum
   number of residues that can be missing from the alignment to *seq*
   to be acceptable as an annotation.

   *sliceInfo* if not None, will be appended to the (id,start,stop)
   tuple that is saved for each annotation.  This enables you to add
   annotation attributes, by giving a sliceAttrDict setting to your AnnotationDB
   constructor that defines these additional attributes.  Note: :meth:`add_homology()`
   saves each annotation as a slice tuple to self.sliceDB, in the form:
   ``(id,start,stop)+sliceInfo``.

   You can (and should) specify many additional arguments for controlling
   the homology search, and results filtering.  For the former, see the list
   of arguments for :class:`blast.BlastMapping` and related variants in
   the :mod:`blast` module.  For results filtering,
   see the list of arguments for :meth:`cnestedlist.NLMSASlice.keys()`.

   :meth:`add_homology()` returns a list of the annotation objects
   created as a result of the homology search.

Iterating over Annotations
--------------------------

For iteration over annotations in a very large annotation database, it is
important to understand how to control the caching of annotation objects.
We try to follow Python's iterators rules closely: :meth:`iteritems()`
and :meth:`itervalues()` simply iterate over the annotation, applying
the *maxCache* limit to the total number of annotations that will be
kept in cache at any one time.

.. method:: AnnotationDB.iteritems()


.. method:: AnnotationDB.itervalues()


By contrast, :meth:`items()` and :meth:`values()`
force loading of all annotations in the entire database into cache, since
that is what these methods require.

.. method:: AnnotationDB.items()


.. method:: AnnotationDB.values()


Finally, :meth:`__iter__()` and :meth:`keys()` just obtain the
list of annotation IDs, without loading anything into the cache.

.. method:: AnnotationDB.close()

   You must call this method to ensure that any data added to the AnnotationDB
   will be written to its Python shelve file on disk.
   This method is irrelevant, but harmless,
   if you are instead using an in-memory dictionary as storage.


Annotation Classes
------------------

.. class:: AnnotationSeq(id, db, parent, start, stop)

   The base class for annotations.  *id* specifies the annotation ID, 
   and *db* must be the :class:`AnnotationDB` instance that contains this
   annotation.  *parent* must be the sequence object that this annotation
   is associated with, and *start*, *stop* specify the coordinates for
   the annotation interval within that sequence's coordinate system
   (following Pygr's standard positive-negative coordinate convention,
   in which positive coordintes refer to the positive strand, and 
   negative coordinates refer to the negative strand).

.. method:: AnnotationSeq.__getattr__(attr)

   :class:`AnnotationSeq` does *not* use the
   :func:`classutil.get_bound_subclass()` mechanism for reflecting attributes
   on the *sliceDB* object (see :class:`AnnotationDB` details above)
   to its associated :class:`AnnotationSeq` instance.  Instead,
   the old-style ``__getattr__`` mechanism is used.  Thus any named attributes
   of the *sliceDB* object can be accessed also on the 
   associated :class:`AnnotationSeq` object.  Note: currently,
   they are only accessible via a direct request for a named attribute,
   not through ``dir()`` introspection.

.. class:: AnnotationSlice(path, start=0, stop=None, step=None, reversePath=None, relativeToStart=False, absoluteCoords=False)

   The base class for annotation slices.  Can be subclassed.
   Uses the same ``__getattr__`` mechanism as :class:`AnnotationSeq`,
   so it too reflects all named attributes on its associated
   *sliceDB* object.


.. class:: TranslationAnnot(id, db, parent, start, stop)

   A subclass of :class:`AnnotationSeq` specifically for
   representing protein Open Reading Frames (ORFs).  It differs from a regular
   annotation in two respects:

   * it represents a *translation* of the sequence interval it
     annotates.  Therefore its length is 1/3 that of the sequence
     interval it annotates.

   * Unlike a regular annotation, you *can* request its string value
     (using ``str()``).  The result will be the amino acid translation
     of the selected ORF interval.  Thus an ORF annotation object
     can be treated like a sequence object in all respects -- you
     can align it, measure its sequence similarity to another sequence etc.

   Translation (ORF) annotations are used for representing the results
   of :class:`blast.BlastxMapping` searches and any blast search whose
   results are actually a translation of the input sequence (such as tblastn).

.. class:: TranslationAnnotSlice(path, start=0, stop=None, step=None, reversePath=None, relativeToStart=False, absoluteCoords=False)

   A subclass of :class:`AnnotationSlice` for ORF annotations.



