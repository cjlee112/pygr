Sequence Annotation Databases
-----------------------------

What is a pygr sequence annotation?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
*Annotation* -- information bound to specific intervals of a genome
or sequence -- is an essential concept in bioinformatics.  We would like to
be able to store and query annotations naturally as part of working with
multi-genome alignments, as a standard operation in comparative genomics.
Pygr makes this easy::

   for alignedRegion in msa[myRegion]: # find alignment in other genomes
     for ival in alignedRegion.exons: # see if this contains any annotated exons
       if ival.orientation>0: # ensure annotation is on same strand as alignedregion
         print 'exon\tID:%d\tSEQ:%s' % (ival.id,str(ival.sequence)) # print its sequence
         for exon2,splice in ival.next.items(): # look at alternative splicing of this exon
           do something...


* In the above code, we assumed that there exists a mapping of any genomic
  sequence region (``alignedRegion``) to exon annotations.  This mapping
  is bound by worldbase.schema to the sequence object's ``exons`` attribute.
  In a moment we will see how to construct such a mapping.
  
* An annotation is an interval (i.e. it has length, and can be sliced,
  or negated to get the opposite strand) that has bound attributes giving
  biological information about the annotation.  It acts like a little coordinate
  system, i.e. ``annotation[0]`` is the first position in the annotation;
  ``annotation[-10:]`` is the last ten positions of the annotation etc.
  Any subslice of the annotation gives its coordinates and orientation
  relative to the original annotation.  In the example above, we used this
  to check whether the annotation slice ``ival`` (which is returned
  in the same orientation as ``alignedRegion``) is on the same strand
  (orientation = 1) as the original exon annotation,
  or the opposite strand (orientation = -1).
  
* An annotation object or slice is associated with the corresponding
  sequence interval of the sequence to which it is bound.  To obtain that
  sequence interval, simply request the annotation's :attr:`sequence`
  attribute.  Use this if you want to get its sequence string via ``str``,
  for example.
  
* An annotation object or slice always has an
  :attr:`annotationType` attribute giving a string identifier for
  its annotation type.
  
* For any annotation slice, its ``pathForward`` attribute
  points to its parent annotation
  object.  For example, in the case above, ``alignedRegion`` might not contain
  the whole exon, in which case ``ival`` would be just the part of the exon
  contained in ``alignedRegion``, and ``ival.pathForward`` would be the complete
  exon.  Note that for nucleotide sequence annotations, orientation matters.
  In this example, we restricted our analysis to exons that are on the same
  strand as ``alignedRegion``.
  
* In addition, pygr also marks it with
  two attributes that identify it as belonging to its annotation database:
  ``id`` gives its unique identifier (primary key) in that database,
  and ``db`` points to the annotation database object itself.
  
* Because pygr can see that ``ival`` is part of the exons annotation database,
  it can apply schema information automatically to it.  In this particular case,
  it applies the splicegraph schema to it (see example from worldbase.schema
  tutorial above), so we can find out what exons it splices to via its ``next``
  attribute.



Constructing an Annotation Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Suppose you had a set of annotations ``sliceDB`` each consisting of a sequence ID,
start, and stop coordinates.  We can easily construct an annotation database
from this::

   from pygr import annotation, cnestedlist, worldbase, metabase
   annoDB = annotation.AnnotationDB(sliceDB, genome) # construct from slice db
   nlmsa = cnestedlist.NLMSA('exonAnnot','w', # store seq->annot mapping as an alignment
                             pairwiseMode=True, bidirectional=False)
   for a in annoDB.itervalues(): # save all annotation intervals
     nlmsa.addAnnotation(a) # add alignment between ival and ann intervals
   nlmsa.build() # write indexes for the alignment
   annoDB.__doc__ = 'exon annotation on the human genome'
   worldbase.Bio.Genomics.ASAP2.exons = annoDB # add to worldbase
   nlmsa.__doc__ = 'map human genome regions to contained exons'
   worldbase.Bio.Genomics.ASAP2.exonmap = nlmsa # now save mapping and schema
   worldbase.schema.Bio.Genomics.ASAP2.exonmap = \
         metabase.ManyToManyRelation(genome, annoDB, bindAttrs=('exons'))
   worldbase.commit() # save all pending data to the resource database


* NLMSA provides an efficient, high-performance way to store and
  query huge annotation databases.  The mapping is stored on disk but is
  accessed with high-speed indexing.
  
* More importantly, however, a worldbase user need never even be
  aware that an NLMSA is being used to provide this mapping.  As far as
  users are concerned, all they need to know is that any sequence object from ``genome``
  has an ``exons`` attribute that automatically gives a list of exon
  annotations contained within that sequence.  I.e. as in the previous
  example, you would simply access it via::
  
     for exon in someRegion.exons:
       do something...
  
  
* The ``ManyToManyRelation`` indicates that ``nlmsa`` should
  be interpreted as being a many-to-many relation from items of ``genome``
  to items of ``annoDB``.  It also creates an ``exons`` attribute on
  items of ``genome`` that translates to ``g.exons=nlmsa[g]``.
  
* In the above example, we assumed that ``genome`` was obtained
  from worldbase (and thus a worldbase resource ID).  If not, we would first
  have to add it, just as we did for ``annoDB``.
  
* Note that we only bound an attribute (``exons``, to the
  ``genome`` items) for the forward mapping (from ``genome`` to ``annoDB``).
  We did not even store the reverse mapping in ``nlmsa``, because
  it is completely trivial.  (i.e. an annotation from ``annoDB`` is itself
  the interval of ``genome`` that it maps to).  This was set by
  the ``bidirectional=False`` option to the ``NLMSA``.
  
* The ``pairwiseMode`` option indicates that this is a pairwise
  (sequence to sequence) alignment, not a true multiple sequence alignment
  (which requires its own coordinate system, called an LPO; see the reference
  docs on NLMSA for more information).  This option could have been omitted;
  pygr would have figured it out automatically from the fact that we saved
  direct alignments of sequence interval pairs to ``nlmsa``.  NLMSA does not
  permit mixing pairwise and true MSA alignment formats in a single NLMSA.


Constructing an Annotation Mapping using Megablast
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
What if someone provided you with a set of "exon annotations" in the form
of short sequences representing the exons, rather than actual genomic
coordinates?  Again, pygr makes this mapping extremely easy to save::

   from pygr import annotation, cnestedlist, blast, worldbase, metabase
   annoDB = annotation.AnnotationDB(None, genome, 'exon', # create the annotation db
                                    filename='exonAnnot', mode='c') # store on disk
   nlmsa = cnestedlist.NLMSA('exonMap','w', # store seq->annot mapping as an alignment
                             pairwiseMode=True, bidirectional=False)
   megablast = blast.MegablastMapping(genome) # query object for searching genome
   for annID,s in exonSeqs.items(): # save all annotation intervals
     for ann in annoDB.add_homology(s, search=megablast, id=annID, maxseq=1, 
                                    minIdentity=98, maxLoss=2):
       nlmsa.addAnnotation(ann)
   nlmsa.build() # write indexes for the alignment
   annoDB.close() # save all our annotation data to disk
   annoDB.__doc__ = 'exon annotation on the human genome'
   worldbase.Bio.Genomics.ASAP2.exons = annoDB # add as a worldbase resource
   nlmsa.__doc__ = 'map human genome regions to contained exons'
   worldbase.Bio.Genomics.ASAP2.exonmap = nlmsa # now save mapping and schema
   worldbase.schema.Bio.Genomics.ASAP2.exonmap = \
         metabase.ManyToManyRelation(genome, annoDB, bindAttrs=('exons',))
   worldbase.commit() # save all pending data to the metabase



* This example assumes ``exonSeqs`` is a dictionary of exon IDs and sequence
  strings.
  
* By passing ``None`` as the *sliceDB* argument, we force the
  AnnotationDB to create a new dictionary for us.  By passing the *filename*
  argument, we make it create a Python shelve disk file to store the dictionary.
  
* The :meth:`add_homology()` method takes a sequence or string argument,
  and performs a homology search using the *search* argument
  (``megablast``), which when called must return an alignment object.  
  Since we have provided an *id*, it will be used as
  the id for the annotation.  The remaining arguments are passed to the
  homology search and filtering functions; see the :class:`MegablastMapping` and
  :meth:`NLMSASlice.keys` documentation for full details of the options you
  can use.  These specific arguments indicate that only the top hit should
  be processed (maxseq=1), that it must have at least 98\% identity to the
  query, and that no more than 2 nucleotides can be missing relative to the
  original query.  :meth:`add_homology()` returns a list of the resulting
  annotation(s) for this search, which are added to the alignment as usual.
  
* Because we requested creation of a disk file to store the annotation.sliceDB,
  we must call the annotationDB's close() method, when we are done, to
  save all of the annotation data to disk.  Otherwise, the Python shelve file might be
  left in an incomplete state.
  
* We save worldbase resource and schema information as before.
  
