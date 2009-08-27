:mod:`sequence` --- Base classes for representing sequences and sequence intervals
==================================================================================

.. module:: sequence
   :synopsis: Base classes for representing sequences and sequence intervals.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>


This module provides a base class representing both sequences and sequence intervals (SeqPath),
from which all sequence classes are derived (Sequence, SQLSequence, BlastSequence etc.).
In this section we document both the features of the base class, and ways to extend or
customize it by creating your own subclasses derived from SeqPath.  The IntervalTransform
class represents a coordinate system mapping from one interval of a sequence, onto
another interval of the same or a different sequence.

A Pythonic Sequence Model
-------------------------
This class provides the basic capabilities of a sliceable sequence or sequence interval,
widely used in Pygr.  It tries to provide core operations on sequences in a highly
Pythonic way:

  
* *Python Sequence*: of course, SeqPath behaves like a Python sequence. i.e.
  the length of a :class:`SeqPath` *s* is just ``len(s)``,
  and you iterate over the "letters" in it using ``for l in s:``
  (Note, the individual letters produced by this iterator
  will themselves be :class:`SeqPath` objects (by default, of length 1)).
  And all the slicing
  operations defined for Python Sequences also apply to
  :class:`SeqPath` (see below).
  
* *Slicing*: :class:`SeqPath` is designed to represent a slice
  (subinterval) of a sequence.
  Like the Python builtin :class:`slice` class, it has :attr:`start`,
  :attr:`stop`, and :attr:`step` attributes that indicate
  the interval beginning, end, and "stride".
  Moreover, it is itself sliceable in the usual pythonic way,
  i.e. ``s[start:stop]``,
  where *start* and *stop* are in the local coordinate system of *s*
  (i.e. ``s[0]`` is the first letter of the interval represented by
  *s*). Note that :class:`SeqPath`
  follows the Python slicing coordinate conventions of positive integers as
  forward coordinates (i.e. counting from the interval start) and negative integers
  as reverse coordinates (i.e. counting from the interval end).
  
* *String value*: to obtain the actual sequence string representation
  of a :class:`SeqPath`, just use the Python builtin ``str(s)``.
  Note that in most cases
  a SeqPath object does not itself store the sequence string associated with it
  but obtains it from somewhere else when the user requests it.
  
* *comparison and containment*: :class:`SeqPath`
  implements the interval-ordering
  and interval-containment relations using the standard Python order operators
  and containment operators. i.e. s<t iff s.start<t.start, and s in t iff
  t.start<=s.start and s.stop<=t.stop.
  
* *orientation*: :class:`SeqPath` carefully represents relationships between intervals
  on opposite strands of a double-stranded nucleotide sequence.  A SeqPath object
  knows whether it is an interval on the forward or reverse strand.  Pygr provides
  a number of operations for manipulating and comparing intervals of different
  orientations.  For example, ``-s`` yields the interval of the opposite strand that
  is base-paired to interval s (i.e. this is not just the reverse-complement of *s*
  in the string 'atgc' $\rightarrow$ 'gcat' sense, but is specifically the SeqPath
  object representing the coordinate
  interval on the opposite strand that is base-paired to *s*).
  
* *schema*: a :class:`SeqPath` object knows "what sequence" it is an interval of;
  it is not just a (start,stop) coordinate pair, but is actually bound to a specific
  parent sequence object.  Specifically, s.path is the parent sequence object of
  which s is a subinterval; s.path will itself be an instance of :class:`SeqPath`, and its path
  attribute will simply be itself.  All :class:`SeqPath` objects are descended from such "top-level"
  :class:`SeqPath` objects.  Note that when you have sequence intervals from both forward
  and reverse strands of a sequence, all of the forward strand intervals will share
  the same path attribute (your original top-level sequence object representing
  the whole sequence in forward orientation), while all the reverse strand intervals
  will reference another top-level :class:`SeqPath` created automatically to represent the
  reverse strand.
  
* *graph structure*: a :class:`SeqPath` object itself acts as a graph, whose nodes are
  the individual letters of the sequence, and whose edges represent the link
  from each letter to the next (if any).  Thus standard graph query works on
  :class:`SeqPath` objects, through the usual interfaces::
  
     for l in s: # GET EACH LETTER OF THE SEQUENCE
         c=str(l)
  
     edge = s[l1][l2] # GET EDGE INFORMATION FOR l1 --> l2
  
     for l1,l2,edge in s.edges(): # GET ALL l1 --> l2 EDGES
         do_something(l1,l2,e)
  
     # DUMB GRAPH QUERY TO FIND 'AG' SUBSTRINGS IN SEQUENCE s
     for d in GraphQuery(s,{0:{1:dict(filter=lambda fromNode,toNode:
                                      str(fromNode)=='A' and str(toNode)=='G')},
                            1:{}})
         l1,l2,edge = d[0],d[1],d[0,1]
  
  
  For more information about edges, see the LetterEdge class.
  
* *Mutable Sequences*: Just as the Python builtin list class implements
  "mutable sequence" objects that can be resized, SeqPath objects can be
  resized and changed, without breaking existing subinterval objects that
  are "part of" the resized SeqPath object.  In particular, just as a list
  can be resized by extending its "stop" coordinate to a higher value, a SeqPath can
  be resized by extending its stop coordinate to a higher value.  Indeed,
  you can even create a SeqPath for a particular sequence without knowing that
  sequence's length (computing the length of a genome sequence might take a long
  time, if all you want to do is create a sequence object to represent that
  sequence).  You can do this by passing *None* as the stop (or start)
  coordinate.  In that case, SeqPath will automatically determine its own
  length at a later time iff a specific user operation makes it absolutely
  necessary to know this length.
  
* *intersection, union, difference*: SeqPath uses the Python \*, + and -
  operators to implement interval intersection, union, and difference
  operations respectively.
  

.. class:: SeqPath([initialdata])

   In addition to the above, the base class also defines convenience methods:

.. method:: before()

   This method returns the entire sequence interval preceding this interval.
   For example, if ``exon`` is an interval of genomic sequence, then
   ``exon.before()[-2:]`` is its acceptor splice site (i.e. the 2 nt immediately
   before ``exon``).


.. method:: after()

   This method returns the entire sequence interval following this interval.
   For example, if ``exon`` is an interval of genomic sequence, then
   ``exon.after()[:2]`` is its donor splice site, (i.e. the 2 nt immediately
   after ``exon``).


Coordinate System
-----------------
SeqPath follows Python slicing conventions (i.e. 0-based indexing, positive indexes
count forward from start, negative indexes count backwards from the sequence
end, and always *s.start<s.stop*).

Each SeqPath object has a number of attributes giving information about its
"location":


  
.. attribute:: orientation

   +1 if on the forward strand, or -1 if on the reverse strand.
  
.. attribute:: path

   the top-level sequence object that this interval is part of, or self
   if this object is its top-level (i.e. not a slice of a larger sequence).  Note that
   all forward intervals share the same path attribute, but reverse strand intervals
   all have a path attribute that represents the entire reverse strand.
  
.. attribute:: pathForward

   same as *path*, but always the forward strand sequence.
  
.. attribute:: start

   start coordinate of the interval.  NB: SeqPath stores coordinates
   relative to the start of the *forward* strand.  This is necessary for allowing
   resizing of the top-level SeqPath; if coordinates were relative to the end of the
   sequence, they would have to be recomputed every time the length of the sequence
   changed.  The main consequence of this is that coordinates for forward intervals
   are always positive, whereas coordinates for reverse intervals are always
   negative (i.e. following the Python convention
   that negative coordinates count backwards
   from the end, and the fact that the end of the reverse strand corresponds to
   the start of the forward strand). NB2: if the SeqPath was originally created with
   *start=None*, requesting its start attribute will force it to compute its start
   coordinate, typically requiring a computation of the sequence length.  In this
   case, the start attribute will computed automatically by SeqPath.__getattr__().
  
.. attribute:: stop

   end coordinate of the interval.  The above comments for *start*
   apply to *stop*.  Note that for reverse intervals, a *stop* value of 0
   means the end of the reverse strand (i.e. -1 is the last nucleotide of the
   reverse strand, and 0 is one beyond the last nucleotide of the reverse strand).
  
.. attribute:: _abs_interval

   a tuple giving the (*start,stop*) coordinates of the
   interval on the forward strand corresponding to this interval (i.e. for a
   forward interval, itself, or for a reverse interval, the interval that base-pairs
   to it).
  



Extending and Customizing
-------------------------
There are several methods and attributes you can override to extend or customize
the behavior of your own SeqPath-derived classes.  Typically you will derive
either from the Sequence class, or in some cases from the SeqPath class.

.. method:: strslice(start, stop, useCache=True)

   called to get the string
   sequence of the interval (*start, stop*).  You can provide your own strslice()
   method to customize how sequence is stored and accessed.  For example,
   :meth:`SQLSequence.strslice()` gets the sequence via a SQL query, and
   :meth:`BlastSequence.strslice()` obtains it using the
   ``fastacmd -L start,stop``
   UNIX shell command from the NCBI toolkit.
   The optional *useCache* argument controls whether your :meth:`strslice` method
   should attempt to get the sequence slice from its database cache (if any),
   or, if false, only directly from its back-end storage (in the usual way
   described above).


.. method:: __len__()

   called to compute the length of the sequence.  You can
   customize this to provide an efficient length method for your particular
   sequence storage.  e.g. :class:`SQLSequence` obtains it via a SQL query;
   :class:`BlastSequence` obtains it from a precomputed length index.
   The default :meth:`Sequence.__len__()` method computes it from
   ``len(self.seq)``, assuming that the sequence can be accessed
   from the :attr:`seq` attribute.


.. method:: __getitem__(slice_obj)

   if you want to monitor or intercept slicing
   requests on your sequence, you can do so by providing your own getitem method.
   See :class:`seqdb.BlastSequenceCache` class for an example.
   If the sequence object has a ``db`` attribute, and that database object
   it points to has an ``itemSliceClass`` attribute, ``SeqPath.__getitem__``
   will use that class to construct the subinterval object.  Similarly,
   if the sequence object has an ``annot`` attribute, and that annotation
   object has a ``db`` attribute, again the ``itemSliceClass`` attribute
   of that database will be used as the class to construct the subinterval
   object.  Otherwise it will
   use ``SeqPath`` itself as the class for constructing the subinterval object.

   Note: this ``itemSliceClass`` behavior applies not only to
   sequence slices obtained via :meth:`__getitem__`, but also from all other
   methods that return sequence slices, such as the following list:
   :meth:`before`, :meth:`after`, :meth:`__mul__`, :meth:`__neg__`.
   :meth:`__add__`, :meth:`__iadd__`.


.. method:: __mul__(other)

   get the sequence interval intersection of *self* and *other*.


.. method:: __neg__()

   get the sequence interval representing the opposite strand of *self*
   i.e. the slice whose string value is the reverse complement of the string
   value of *self*.


.. method:: __add__(other)

   get the sequence interval union of *self* and *other*, i.e.
   the smallest sequence interval that contains both of them.



.. method:: __getattr__(attr)

   if you subclass a :class:`SeqPath`-derived class and supply a :meth:`__getattr__`
   method for your subclass, it *must* call the parent class's
   :meth:`__getattr__`.  This is essential for "delayed evaluation" of
   :attr:`start` and :attr:`stop` attributes, which are generated automatically
   by :class:`SeqPath`'s :meth:`__getattr__`.  If your subclass inherits from
   more than one parent class, check whether *both* parents supply a
   :meth:`__getattr__`, in which case your subclass must supply a
   :meth:`__getattr__` that explicitly calls both of them.  Failing to do so
   will lead to strange bugs.



.. attribute:: seq

   the :meth:`Sequence.strslice()` method assumes that
   the actual sequence is stored
   on the :attr:`seq` attribute.  You could customize this behavior by
   making the :attr:`seq` attribute a property that is computed on the fly
   by some method of your own.
  

.. class:: Sequence(s, id)

   The :class:`Sequence` class provides a SeqPath flavor that stores a sequence string
   *s* and identifier *id* for this sequence::

      from pygr import sequence
      seq = sequence.Sequence('GPTPCDLMETQ','FOOG_HUMAN')


.. method:: Sequence.update(s)

   You can change the actual string sequence to a new string *s*
   using the *update* method::

      seq.update('TKRRPLEDKMNEPS')



.. method:: Sequence.seqtype()

   returns DNA_SEQTYPE for DNA sequences,
   RNA_SEQTYPE for RNA, and PROTEIN_SEQTYPE for protein.



.. method:: reverse_complement(s)

   returns the reverse complement of the sequence string s.




.. attribute:: Sequenceid

   stores the sequence's identifier.
  



.. class:: IntervalTransform([initialdata])

   This class provides a mapping transform between the coordinate
   systems of a pair of intervals::

      xform = IntervalTransform(srcPath,destPath)
      d2 = xform(s2) # MAPS s2 FROM srcPath coords to destPath coord system
      d3 = xform[s2] # CLIPS s2 TO NOT EXTEND OUTSIDE srcPath, THEN XFORMS
      s3 = xform.reverse(d3) # MAP BACK TO srcPath COORD SYSTEM


.. class:: Seq2SeqEdge(msaSlice, targetPath, sourcePath=None)

   This class represents a segment of alignment between two sequences.
   It is a temporary object created in association with a MSASlice
   object (see Alignment Module).

   Create a Seq2SeqEdge for the targetPath, on the specified alignment
   slice.  If sourcePath is None, it will be calculated automatically
   by calling the slice's methods.


.. method:: __iter__(sourceOnly=True, **kwargs)

   iterate over source intervals within this segment of alignment.
   *kwargs* will be passed on to the *msaSlice*'s
   :meth:`groupByIntervals` and :meth:`groupBySequences` methods.


.. method:: items(**kwargs)

   same as :meth:`__iter__`, but gets tuples of (source_interval,target_interval).


.. method:: pIdentity(mode=max,trapOverflow=True)

   Compute the percent identity between the source and target sequence
   intervals in this segment of the alignment.  *mode* controls
   the method used for determining the denominator based on the lengths of
   the two aligned sequence intervals.  *trapOverflow* controls
   whether overflow (due to multiple mappings of the query sequence to
   *different* regions of the alignment) is trapped as an error.
   To turn off such error trapping, set *trapOverflow=False*.


.. method:: pAligned(mode=max,trapOverflow=True)

   Compute the percent alignment between the source and target sequence
   intervals in this segment of the alignment, i.e. the fraction of
   residues that are actually aligned as opposed to gaps / insertions,
   in the two intervals.


.. method:: conservedSegment(pIdentityMin=.9,minAlignSize=1,mode=max)

   Return the longest alignment interval (possibly including gaps) with
   a \%identity fraction higher than *pIdentityMin*.  If there is no
   such interval, or the longest such interval
   is shorter than *minAlignSize*, it returns *None*.  The interval
   is returned as a tuple of integers ``(srcStart,srcEnd,destStart,destEnd)``.


*Warning*: if your query sequence has multiple mappings in the alignment
(i.e. it is aligned to two or more different regions in the alignment),
:meth:`pIdentity()` and :meth:`pAligned()` may return fractions larger
than 1.0.  This is because the query sequence may align to a given
target sequence via *more* than one region in the alignment.  If you
encounter this problem, you can iterate through the individual mappings
yourself (by calling the :meth:`iter()`, :meth:`items()` or
:meth:`edges()` iterator methods for your alignment slice object),
and calculating the percentage identity or alignment (via your own algorithm)
individually for each specific mapping.  For more
background on this problem, see "Multiple Mappings", below.

Note that the presence of multiple mappings is *not* a Pygr bug,
but simply reflects the alignment data loaded into Pygr.  :class:`Seq2SeqEdge`
should be able to avoid this problem mostly, beginning with release 0.6.
(It tries to screen out hits not consistent with the specific region-region
mapping stored with this edge).

.. class:: SeqFilterDict([initialdata])

   This dict-like class provides a simple way for masking a set of sequences
   to specific intervals.  It stores a specific interval for each
   sequence.  Subsequent look-up using a sequence interval as a key will
   return the intersection between that interval and the stored interval
   for that sequence in the dictionary.  If there is no overlap, it
   raises ``KeyError``::
   
      d = SeqFilterDict(seqIntervalList)
      overlap = d[ival] # RETURNS INTERSECTION OF ival AND STORED IVAL, OR KeyError


   You can pass a list of intervals to store to the class constructor (as
   shown above).  You can also add a single interval using the syntax
   ``d[saveInterval]=saveInterval``.  (This syntax reflects the actual
   mapping that the dictionary will perform if later called with the
   same interval).

.. class:: LetterEdge([initialdata])

   This class represents an edge from origin -> target node.

.. method:: __iter__()

   iterate over seqpos for sequences that traverse this edge.


.. method:: iteritems()

   generate origin, target seqpos for sequences that traverse this edge.


.. method:: __getitem__(seq)

   return origin,target seqpos for sequence *seq*;
   raise ``KeyError`` if not in this edge



.. attribute:: seqs

   returns its sequences that traverse this edge



Functions
---------
The sequence module also provides convenience functions:

.. function:: guess_seqtype(s)

   based on the letter composition of
   the string *s*, returns DNA_SEQTYPE for DNA sequences,
   RNA_SEQTYPE for RNA, and PROTEIN_SEQTYPE for protein.


.. function:: absoluteSlice(seq, start, stop)

   returns the sequence interval of top-level sequence object associated
   with *seq*, interpreting *start* and *stop* according to
   the Pygr convention: a pair of positive values represents an interval
   on the forward strand; a pair of negative values represents an
   interval on the reverse strand (see Coordinate System, above).
   Note: if *seq* is itself a subinterval, then the *start,stop*
   coordinates are interpreted relative to its parent sequence, i.e.
   ``seq.pathForward[start:stop]``.



.. function:: relativeSlice(seq, start, stop)

   returns the sequence interval of *seq*, interpreting
   *start* and *stop* according to
   the Pygr convention: a pair of positive values represents an interval
   on the forward strand; a pair of negative values represents an
   interval on the reverse strand (see Coordinate System, above).
   Note: if *seq* is itself a subinterval, then the *start,stop*
   coordinates are interpreted relative to *seq* itself, i.e.
   ``seq[start:stop]".


