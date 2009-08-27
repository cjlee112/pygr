:mod:`blast` --- BLAST mapping interfaces
=============================================

.. module:: blast
   :synopsis: BLAST mapping interfaces.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>


This module provides classes for performing BLAST or MEGABLAST
searches on a sequence database.  This module was added in Pygr 0.8.

External Requirements
---------------------
This module makes use of several external programs:

* *NCBI toolkit*: The BLAST database functionality in this module
  requires that the NCBI toolkit
  be installed on your system.  Specifically, some functions will call the command line
  programs ``formatdb``, ``blastall``, and ``megablast``.
  
* *RepeatMasker*: :class:`MegablastMapping` calls the command line
  program ``RepeatMasker`` to mask out repetitive sequences from seeding alignments,
  but to allow extension of alignments into masked regions.
  
BLAST as a Many-to-Many Mapping Between Sequences
-------------------------------------------------

Pygr treats BLAST as a many-to-many mapping, just like any other
Pygr graph object.  That is, a :class:`BlastMapping` object 
acts like a graph whose nodes are sequence interval objects, and
whose edges are alignment edge objects. 

Thus to perform a query, you can simply use a sequence object
as a key for querying the :class:`BlastMapping`.  The
result will simply be a :class:`cnestedlist.NLMSASlice` as 
usual for an alignment query.

To construct a :class:`BlastMapping` instance, you simply
pass it the sequence database to be searched.

Here's a simple example of opening a BLAST database and searching it for matches to a specific piece of sequence::

   db = SequenceFileDB('sp') # open swissprot sequence db
   blastmap = BlastMapping(db) # create a mapping object for running blast
   m = blastmap[db['CYGB_HUMAN'][40:-40]] # do blast search
   try:
       hit = m[db['MYG_CHICK']] # is MYG_CHICK homologous?
       print 'Identity:', hit.pIdentity()*100, 'Aligned:', hit.pAligned()*100
       for src,dest in hit.items(): # print matching intervals
           print src, repr(src), '\n', dest, repr(dest), '\n'
   except KeyError:
       print 'MYG_CHICK not homologous.'

Let's go through this example line by line:
  
* We can create a :class:`BlastMapping` for any sequence database.
  :class:`BlastMapping`
  will figure out what type of sequences (nucleotide vs. protein) are
  in the database, in order to construct the BLAST index file properly.
  
* ``db['CYGB_HUMAN']`` obtains a sequence object
  representing the SwissProt sequence whose ID is CYGB_HUMAN.
  The slice operation [40:-40] behaves just like normal Python slicing:
  it obtains a sequence object representing the subinterval omitting
  the first 40 letters and last 40 letters of the sequence.
  
* Querying the blast mapping object with a sequence object as a key
  searches the BLAST database for homologies to it, using NCBI BLAST.
  It chooses reasonable parameters based upon the sequence types of
  the database and supplied query.
  
* You can specify search parameter options if you wish, by calling
  the blast mapping as a function with the sequence object and
  your extra parameters.  It returns a Pygr sequence mapping (multiple alignment) that represents a standard Pygr graph of alignment relationships between s and the homologies that were found.  Since this mode is designed for being
  able to save alignments for multiple sequences in a single multiple
  sequence alignment, when reading this alignment you need to specify
  which source sequence you want alignment information for, e.g.::
  
     msa = blastmap(db['CYGB_HUMAN'][40:-40], expmax=1e-10)
     m = msa[db['CYGB_HUMAN']]
  
  The rest of the code would be identical to the example above.
  
* The expression ``m[db['MYG_CHICK']]`` obtains the
  "edge information" for the graph relationship between
  the two sequence nodes s and MYG_CHICK.  (if there was no edge
  in the m graph representing a relationship between these two sequences,
  this would produce a :exc:`KeyError`).
  This edge information consists of a set of interval alignment
  relationships, which are printed out in this example.
  

To pass additional parameters for controlling the BLAST search,
use the :class:`BlastMapping` as a callable (function) object
to which you pass these parameters as arguments.  The result will
be an :class:`cnestedlist.NLMSA` alignment object.



BlastMapping
------------
This class provides a mapping interface for searching a sequence
database with BLAST.  You simply create the mapping object with the
target database you want it to search, then use it as a mapping.

Use :class:`BlastMapping` for the following BLAST modes:

* **blastn**: automatically selected by Pygr
  when the query and database sequences are both nucleotide;

* **blastp**: when the query and database sequences are both protein;

* **tblastn**: when the query is protein and the database sequences are 
  nucleotide.


.. class:: BlastMapping(seqDB, filepath=None, blastReady=False, blastIndexPath=None, blastIndexDirs=None, **kwargs)

   * *seqDB*: the sequence database to search via BLAST.

   * *filepath*: location of a FASTA file to initialize from (optional;
     if not provided, BlastMapping will try to obtain it from the
     *seqDB* object).

   * *blastReady* option specifies whether BLAST index files should
     be immediately
     constructed (using :meth:`formatdb()`).  Note, if you ask it to generate
     BLAST results, it will automatically create the index files for you
     if they are missing.

   * *blastIndexPath*, if not None, specifies the path to the BLAST index
     files for this database.  For example, if the BLAST index files are
     ``/some/path/foo.psd`` etc., then ``blastIndexPath='/some/path/foo'``.

   * *blastIndexDirs*, if not None, specifies a list of directories in which
     to search for and create BLAST index files.  Entries in the list can be
     either a string, or a function that takes no parameters and returns
     a string path.  A string value "FILEPATH" instructs it to use the
     filepath of the FASTA file associated with the BlastDB.
     The default value of this attribute is::

        ['FILEPATH',os.getcwd,os.path.expanduser,tempfile.gettempdir()]

     This corresponds to: self.filepath, current directory, the user's HOME
     directory, and the first user- and/or system-specific temporary directory
     returned by the Python function :meth:`tempfile.gettempdir()`.


Useful methods:

.. method:: BlastMapping.formatdb(filepath=None)

   Triggers the :class:`BlastMapping` to construct new
   BLAST index files, either at the
   location specified by *filepath*, if not None, or in the first
   directory in the :attr:`blastIndexDirs` list where the index files
   can be succesfully built.  Index files are generated using the
   "formatdb" program provided by NCBI, which must be in your
   PATH for this method to work.

.. method:: BlastMapping.__getitem__(seq)

   search our database for homologies to *seq*, using default parameters.
   Returns a :class:`cnestedlist.NLMSASlice` instance.

.. method:: BlastMapping.__call__(seq, al=None, blastpath='blastall', blastprog=None, expmax=0.001, maxseq=None, opts=", verbose=None, queryDB=None)

   run a BLAST search on sequence object seq, with additional
   parameters controlling the search.

   *maxseq* will limit the number of returned hits to the best *maxseq* hits.

   *al* if not None, must be an alignment object in which you want the results
   to be saved.  Note: in this case, it will not automatically
   call the alignment's :meth:`cnestedlist.NLMSA.build()` method;
   you will have to do that yourself.

   *blastpath* gives the command to run BLAST.

   *blastprog*, if not None, should be a string giving the name of the BLAST
   program variant you wish to run, e.g. 'blastp' or 'blastn' etc.  If None,
   this will be figured out automatically based on the sequence type of *seq*
   and of the sequences in this database.

   *expmax* should be a float value giving the largest "expectation score"
   you wish to allow homology to be reported for.

   *opts* allows you to specify arbitrary command line arguments to the BLAST
   program, for controlling its search parameters.

   *verbose=False* allows you to switch off printing of explanatory messages to
   stderr.

   You can also use the optional *queryDB* argument
   to pass a dictionary containing multiple
   sequences to be used as queries.  Since the blastall program
   will only be invoked once for all the queries (instead of
   once for each sequence), this can be more efficient.  Pass
   the optional argument *queryDB* to the callable; its values
   must be sequence (interval) objects to be used as queries.

   Returns a :class:`cnestedlist.NLMSA` alignment object (which will simply
   be the *al* argument, if not None; otherwise a new alignment object,
   in which case it will automatically call its
   :meth:`cnestedlist.NLMSA.build()` method prior to returning it).


Useful attributes:

  
.. attribute:: BlastMapping.filepath

   the location of the FASTA sequence file upon which
   this :class:`BlastMapping` is based.
  
.. attribute:: BlastMapping.blastIndexPath

   if present, the location of the BLAST index files
   associated with this :class:`BlastMapping`.  If not present, the location is assumed
   to be the same as the FASTA file.
  
.. attribute:: BlastMapping.blastIndexDirs

   the list of directories in which to search for
   or build BLAST index files for this :class:`BlastMapping`.  For details, see
   the explanation for the constructor method, above.
  



MegablastMapping
----------------
This class provides a mapping interface for searching a sequence
database with MEGABLAST, with repeat masking.  
You use it just like a :class:`BlastMapping` object.
It accepts some different arguments when you use a megablast mapping
object as a callable:

.. method:: MegablastMapping.__call__(seq, al=None, blastpath='megablast', expmax=1e-20, maxseq=None, minIdentity=None, maskOpts='-U T -F m', rmPath='RepeatMasker', rmOpts='-xsmall', opts=", verbose=True)

   first performs repeat masking on the sequence by converting repeats to lowercase,
   then runs megablast with command line options to prevent seeding new alignments
   within repeats, but allowing extension of alignments into repeats.
   In addition to the blast options (described above),

   *minIdentity* should be a number (maximum value, 100)
   indicating the minimum percent identity for hits to be returned.

   *rmPath* gives the command to use to run RepeatMasker.

   *rmOpts* allows you to give command line options to RepeatMasker.
   The default setting causes RepeatMasker to mark repetitive regions in the
   query in lowercase, which then works in concert with the *maskOpts* option, next.

   *maskOpts* gives command line options for controlling the megablast program's
   masking behavior.  The default value prevents megablast from using repetitive
   sequence as a seed for starting a hit, but allows it to propagate a regular
   (non-repetitive hit) through a repetitive region.


Understanding Translated BLAST Results
--------------------------------------

BLAST has several modes (tblastn, blastx, tblastx) that translate the
input sequence(s) from nucleotide to protein when reporting search
results.  It is important to understand how Pygr handles this complication.
Pygr follows a few key principles here:

* Pygr reports the alignment that BLAST reports.  In other words, if BLAST
  reports a protein vs. protein alignment, that is what Pygr returns,
  even if (for example) the query sequence was actually a nucleotide
  sequence (which BLAST's results have translated to protein).

* To do this, Pygr creates translations of the underlying nucleotide
  sequences where necessary.  Specifically, if the actual sequence
  was nucleotide, but BLAST reported it as a protein sequence, 
  Pygr creates a :class:`annotation.TranslationAnnot` "translation
  annotation" of the actual (nucleotide) sequence, and returns the 
  alignment of that translation annotation.

* Such a translation annotation gives you the "best of both worlds".
  On the one hand, in all respects it acts like a protein sequence object.
  You can obtain its amino acid sequence using ``str()`` as usual;
  requesting its length using ``len()`` will return the length of its
  amino acid sequence (i.e. 1/3 the length of the corresponding nucleotide
  sequence), etc.  Thus the results Pygr returns to you will correspond
  exactly to the protein-protein alignment that BLAST reported.

  On the other hand, any translation annotation object (or slice thereof)
  also has a :attr:`annotation.AnnotationSeq.sequence` attribute, which
  will return the corresponding interval of the underlying **nucleotide**
  sequence, i.e. the original sequence object that you used in your query.

Pygr provides two classes that handle translated BLAST results:

* :class:`BlastMapping` handles the case where only the homology hits
  (what BLAST results refer to as the *subject* sequences)
  are translation annotations, i.e. **tblastn**, where the query is
  protein and the database sequences are nucleotide, so BLAST
  translates the database sequences to protein in its results.

* :class:`BlastxMapping` handles the more complicated case where
  the query sequence itself is reported as a translation annotation.
  Use this class for both **blastx** and **tblastx**.  This complicates
  Pygr's task significantly and requires special handling, since in
  principle each BLAST hit could be to a *different* ORF in the query
  sequence.  Because of this, Pygr makes a new translation annotation
  of the query sequence specifically for each hit.

BlastxMapping
-------------
This subclass of :class:`BlastMapping` provides the following search modes:

* **blastx**: automatically selected by Pygr
  when the query is nucleotide and the database sequences are protein.
  In this case, the alignment results are returned with the query
  transformed to a translation annotation (:class:`annotation.TranslationAnnot`).

* **tblastx**: when the query and database sequences are both nucleotide.
  In this case, the alignment results are returned with both the query
  and the database sequences
  transformed to translation annotations (:class:`annotation.TranslationAnnot`).

The key difference vs. :class:`BlastMapping` is that it does not make sense
for :class:`BlastxMapping` to combine different hits into a single "multiple
sequence alignment", for the simple reason that (in principle) each hit
may be to a completely different ORF in the query sequence.  
I.e. BLAST may report each hit aligned to a *different* query sequence.

So instead of saving all results into a single :class:`cnestedlist.NLMSA`, 
:class:`BlastxMapping` returns its results as a list of 
:class:`cnestedlist.NLMSASlice` objects (one for each hit in the results).

.. class:: BlastxMapping(seqDB, filepath=None, blastReady=False, blastIndexPath=None, blastIndexDirs=None, **kwargs)

   The constructor for this class is identical to :class:`BlastMapping`.

.. method:: BlastxMapping.__getitem__(seq)

   search our database for homologies to *seq*, using default parameters.
   Returns a list of :class:`cnestedlist.NLMSASlice` instances, one for
   each hit in the search results.

.. method:: BlastxMapping.__call__(seq, blastpath='blastall', blastprog=None, expmax=0.001, maxseq=None, verbose=None, opts='', xformSrc=True, xformDest=False, **kwargs)

   run a blastx-style search on sequence object *seq*, with additional
   parameters controlling the search.

   *blastprog*, if None, is automatically set to the correct value based on
   the query and database sequence types (i.e. ``'blastx'`` or ``'tblastx'``).

   *xformSrc* specifies whether the query sequence must be transformed to
   a translation annotation in the reported results.

   *xformDest* specifies whether the database sequences must be transformed to
   a translation annotation in the reported results.  It is automatically set
   to True for **tblastx** mode.

   Returns a list of :class:`cnestedlist.NLMSASlice` instances, one for
   each hit in the search results.


