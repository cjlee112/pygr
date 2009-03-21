Sequence Annotation Databases
-----------------------------

What is a pygr sequence annotation?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
*Annotation* -- information bound to specific intervals of a genome
or sequence -- is an essential concept in bioinformatics.  We would like to
be able to store and query annotations naturally as part of working with
multi-genome alignments, as a standard operation in comparative genomics.
Pygr makes this easy::

   for alignedRegion in msa[myRegion]: # FIND ALIGNMENT IN OTHER GENOMES
     for ival in alignedRegion.exons: # SEE IF THIS CONTAINS ANY ANNOTATED EXONS
       if ival.orientation>0: # ENSURE ANNOTATION IS ON SAME STRAND AS alignedRegion
         print 'exon\tID:%d\tSEQ:%s' % (ival.id,str(ival.sequence)) # PRINT ITS SEQUENCE
         for exon2,splice in ival.next.items(): # LOOK AT ALTERNATIVE SPLICING OF THIS EXON
           do something...


* In the above code, we assumed that there exists a mapping of any genomic
  sequence region (``alignedRegion``) to exon annotations.  This mapping
  is bound by pygr.Data.schema to the sequence object's ``exons`` attribute.
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
  it applies the splicegraph schema to it (see example from pygr.Data.schema
  tutorial above), so we can find out what exons it splices to via its ``next``
  attribute.



Constructing an Annotation Database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Suppose you had a set of annotations ``sliceDB`` each consisting of a sequence ID,
start, and stop coordinates.  We can easily construct an annotation database
from this::

   from pygr import seqdb,cnestedlist
   annoDB = seqdb.AnnotationDB(sliceDB,genome) # CREATE THE ANNOTATION DB
   nlmsa = cnestedlist.NLMSA('exonAnnot','w', # STORE SEQ->ANNOT MAPPING AS AN ALIGNMENT
                             pairwiseMode=True,bidirectional=False)
   for a in annoDB.itervalues(): # SAVE ALL ANNOTATION INTERVALS
     nlmsa.addAnnotation(a) # ADD ALIGNMENT BETWEEN ival AND ann INTERVALS
   nlmsa.build() # WRITE INDEXES FOR THE ALIGNMENT
   annoDB.__doc__ = 'exon annotation on the human genome'
   pygr.Data.Bio.Genomics.ASAP2.exons = annoDB # ADD AS A PYGR.DATA RESOURCE
   nlmsa.__doc__ = 'map human genome regions to contained exons'
   pygr.Data.Bio.Genomics.ASAP2.exonmap = nlmsa # NOW SAVE MAPPING AND SCHEMA
   pygr.Data.schema.Bio.Genomics.ASAP2.exonmap = \
         pygr.Data.ManyToManyRelation(genome,annoDB,bindAttrs=('exons'))
   pygr.Data.save() # SAVE ALL PENDING DATA TO THE RESOURCE DATABASE


* NLMSA provides an efficient, high-performance way to store and
  query huge annotation databases.  The mapping is stored on disk but is
  accessed with high-speed indexing.
  
* More importantly, however, a pygr.Data user need never even be
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
  from pygr.Data (and thus a pygr.Data resource ID).  If not, we would first
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

   from pygr import seqdb,cnestedlist
   annoDB = seqdb.AnnotationDB(None, genome, 'exon', # CREATE THE ANNOTATION DB
                               filename='exonAnnot',mode='c') # STORE ON DISK
   nlmsa = cnestedlist.NLMSA('exonMap','w', # STORE SEQ->ANNOT MAPPING AS AN ALIGNMENT
                             pairwiseMode=True,bidirectional=False)
   for id,s in exonSeqs.items(): # SAVE ALL ANNOTATION INTERVALS
     for ann in annoDB.add_homology(s,'megablast',id=id,maxseq=1,minIdentity=98,maxLoss=2):
       nlmsa.addAnnotation(ann)
   nlmsa.build() # WRITE INDEXES FOR THE ALIGNMENT
   annoDB.close() # SAVE ALL OUR ANNOTATION DATA TO DISK
   annoDB.__doc__ = 'exon annotation on the human genome'
   pygr.Data.Bio.Genomics.ASAP2.exons = annoDB # ADD AS A PYGR.DATA RESOURCE
   nlmsa.__doc__ = 'map human genome regions to contained exons'
   pygr.Data.Bio.Genomics.ASAP2.exonmap = nlmsa # NOW SAVE MAPPING AND SCHEMA
   pygr.Data.schema.Bio.Genomics.ASAP2.exonmap = \
         pygr.Data.ManyToManyRelation(genome, annoDB, bindAttrs=('exons',))
   pygr.Data.save() # SAVE ALL PENDING DATA TO THE RESOURCE DATABASE



* This example assumes ``exonSeqs`` is a dictionary of exon IDs and sequence
  strings.
  
* By passing ``None`` as the *sliceDB* argument, we force the
  AnnotationDB to create a new dictionary for us.  By passing the *filename*
  argument, we make it create a Python shelve disk file to store the dictionary.
  
* The :meth:`add_homology()` method takes a sequence or string argument,
  and performs a homology search against ``genome``.  This requires that
  our ``genome`` provide a method attribute matching our search name
  ('megablast'), which must return an alignment object.  For a :class:`BlastDB`
  object we could use either its :meth:`blast` or :meth:`megablast` methods.
  Since we have provided an *id*, it will be used as
  the id for the annotation.  The remaining arguments are passed to the
  homology search and filtering functions; see the :class:`BlastDB` and
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
  
* We save pygr.Data resource and schema information as before.
  
