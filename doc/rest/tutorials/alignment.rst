==========================================
Creating, Querying, and Storing Alignments
==========================================

Purpose
^^^^^^^

This tutorial teaches you how build, query, access and store
sequence alignments in Pygr, in-memory, on-disk and over networks.
You should already understand Pygr sequences (see :doc:`sequence`).


Alignment Basics
^^^^^^^^^^^^^^^^

Pygr multiple alignment objects can be treated as mappings of sequence
intervals onto sequence intervals.  Here is an example showing basic
operations for constructing and querying an alignment.

First, create an empty in-memory alignment.  We'll only be doing
pairwise alignments, so we will set pairwiseMode=True.

   >>> from pygr import cnestedlist
   >>> simple_al = cnestedlist.NLMSA('hbb', mode='memory', pairwiseMode=True)

Load some sequences, too:

   >>> from pygr import seqdb
   >>> db = seqdb.SequenceFileDB('data/sp_all_hbb')
   >>> mouse = db['HBB1_MOUSE']
   >>> rat = db['HBB1_RAT']
   >>> frog = db['HBB1_XENLA']

Now, add the mouse sequence to the alignment:

   >>> simple_al += mouse

and align several intervals from other sequences to the mouse sequence:

   >>> ival = mouse[40:60]
   >>> simple_al[ival] += rat[42:62]
   >>> simple_al[ival] += frog[38:58]

Once we're done adding aligned intervals, build the alignment object
to prepare it for querying:

   >>> simple_al.build()

Now we can query the alignment with any new interval overlapping the
mouse interval to which we aligned everything:

   >>> sub_ival = mouse[48:52]
   >>> for aligned_ival in simple_al[sub_ival]:
   ...   print repr(aligned_ival)
   HBB1_RAT[50:54]
   HBB1_XENLA[46:50]

We can also use any of the other sequences as keys, e.g. the whole
rat sequence:

   >>> for aligned_ival in simple_al[rat]:
   ...   print repr(aligned_ival)
   HBB1_MOUSE[40:60]

When you query 'simple_al' with an interval, it returns an
``NLMSASlice`` object.  The examples above all use the basic iterator
interface to ``NLMSASlice``, and it's equivalent to calling ``keys()``
with no arguments (we'll discuss ``keys()`` in more detail below).
You can also call ``edges()``, which will return a triple of source
interval, destination interval, and edge information:

   >>> for src, dest, edge in simple_al[mouse].edges():
   ...   print repr(src), 'aligns to', repr(dest)
   ...   print 'Identity across alignment:', edge.pIdentity()
   ...   print '--'
   HBB1_MOUSE[40:60] aligns to HBB1_RAT[42:62]
   Identity across alignment: 0.15
   --
   HBB1_MOUSE[40:60] aligns to HBB1_XENLA[38:58]
   Identity across alignment: 0.05
   --

You can also retrieve edges directly by querying the ``NLMSASlice`` with
the aligned sequence, treating it as a mapping:

   >>> edge = simple_al[mouse][rat]
   >>> print '%.4f' % (edge.pIdentity(),)
   0.0068

Gaps
^^^^

The alignments above deal with *ungapped* blocks of sequence similarity.
How does pygr deal with gapped alignments?

Let's start by loading in some carefully constructed sequences:

   >>> db = seqdb.SequenceFileDB('data/gapping.fa')
   >>> ungapped = db['ungapped']
   >>> gapped = db['gapped']

Here, 'gapped' is a copy of 'ungapped' with 4 extra nucleotides
('atgc') inserted into it at position 40:

   >>> print ungapped
   ATGGTGCACCTGACTGATGCTGAGAAGGCTGCTGTCTCTGGCCTGTGGGGAAAGGTGAACTCCGATGAAG
   >>> print gapped
   ATGGTGCACCTGACTGATGCTGAGAAGGCTGCTGTCTCTGatgcGCCTGTGGGGAAAGGTGAACTCCGATGAAG
   >>> print ' '*40 + '^^^^'
                                           ^^^^

Now, let's build an alignment containing the two ungapped blocks:
   
   >>> al = cnestedlist.NLMSA('hbb', mode='memory', pairwiseMode=True)
   >>> al += gapped
   >>> first_ival = gapped[:40]
   >>> second_ival = gapped[44:]
   >>> al[first_ival] += ungapped[:40]
   >>> al[second_ival] += ungapped[40:]
   >>> al.build()

As you'd expect, querying 'al' with either 'ungapped' or 'gapped'
returns two elements with 100% identity: ::

   >>> for (src, dest, edge) in al[gapped].edges():
   ...   print repr(src), repr(dest), '%.2f' % (edge.pIdentity(),)
   gapped[0:40] ungapped[0:40] 1.00
   gapped[44:74] ungapped[40:70] 1.00

   >>> for (src, dest, edge) in al[ungapped].edges():
   ...   print repr(src), repr(dest), '%.2f' % (edge.pIdentity(),)
   ungapped[0:40] gapped[0:40] 1.00
   ungapped[40:70] gapped[44:74] 1.00

Is there a way to combine these into a single interval?  Yes!  This
is where the extra arguments to the ``keys()``, ``values()``, and ``edges()``
methods on ``NLMSASlice`` come in handy.

For example, to bridge insertions in the query sequence (or, equivalently,
deletions in the target sequence), set 'maxgap':

   >>> for (src, dest, edge) in al[gapped].edges(maxgap=4):
   ...   print repr(src), repr(dest), '%.3f' % (edge.pIdentity(),)
   gapped[0:74] ungapped[0:70] 0.946

To bridge deletions in the query sequence (insertions in the target
sequence) use the 'maxinsert' parameter:

   >>> for (src, dest, edge) in al[ungapped].edges(maxinsert=4):
   ...   print repr(src), repr(dest), '%.3f' % (edge.pIdentity(),)
   ungapped[0:70] gapped[0:74] 0.946

For both of these queries, you can see that the percent identity is
properly adjusted to reflect the identity of only 70 of the 74
nucleotides (70/74 = 94.6%).

There are a number of other ways to control how ``NLMSASlice`` queries
work, including minimum identity filters, minimum aligned block sizes,
etc.

Storing alignments on disk
^^^^^^^^^^^^^^^^^^^^^^^^^^

Creating an NLMSA object can take a long time and a lot of memory;
what if you want to build it just once, and then query it multiple
times?  You can do this by creating an NLMSA in 'w' (write) mode,
rather than 'memory' mode; otherwise the semantics are the same.

Create the NLMSA,

   >>> simple_al = cnestedlist.NLMSA('tempdir/hbb', mode='w', pairwiseMode=True)
  
load the sequences,

   >>> db = seqdb.SequenceFileDB('data/sp_all_hbb')
   >>> mouse = db['HBB1_MOUSE']
   >>> rat = db['HBB1_RAT']
   >>> frog = db['HBB1_XENLA']

add the mouse sequence into the alignment

   >>> simple_al += mouse

and align several intervals from other sequences to the mouse sequence:

   >>> ival = mouse[40:60]
   >>> simple_al[ival] += rat[42:62]
   >>> simple_al[ival] += frog[38:58]

And, finally, build it and then delete the in-memory handle (to emulate
quitting Python and starting from scratch):

   >>> simple_al.build(saveSeqDict=True)
   >>> del simple_al

Now, to load this alignment, we need to specify the sequence source or
sources that we used to build it -- we can do that by using
``PrefixUnionDict`` to construct a ``seqDict`` and pass it into the NLMSA.

   >>> seqDict = seqdb.PrefixUnionDict({ 'sp_all_hbb': db })
   >>> loaded_al = cnestedlist.NLMSA('tempdir/hbb', seqDict=seqDict)
   >>> loaded_al[ival].keys()
   [HBB1_RAT[42:62], HBB1_XENLA[38:58]]

Here we can use our interval from above because the sequence references
stored in the NLMSA point to ``db``, the database that our interval came
from in the first place.

You can also load the saved seqDict (see ``simple_al.build``, above, where
we told pygr to save the sequence dictionary):

   >>> loaded_al = cnestedlist.NLMSA('tempdir/hbb')

Now, however, you can't query with our original ival, because we
loaded a new seqDict into memory. Even though it's pointing at the
same on-disk file as ``db`` did before, pygr only keeps track of
sequence-to-database relationships in memory.  So now you have to
manually retrieve the mouse sequence from the new seqDict in order to
query the NLMSA:

   >>> seqDict = loaded_al.seqDict
   >>> ival = seqDict['sp_all_hbb.HBB1_MOUSE']

and voila, now we can query the alignment, etc.

   >>> loaded_al[ival].keys()
   [HBB1_RAT[42:62], HBB1_XENLA[38:58]]

In practice, if you store your sequence collections in ``worldbase``,
you don't need to worry about seqDict mechanisms.  However, if you're
not using ``worldbase`` then you'll need to keep track of your sequence
dictionaries.

Creating alignments with BLAST
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Let's suppose you have some sequences in a database, and you'd like to use
BLAST to search that database and load the results into an alignment. Simple!
First, load in the database and create a ``BlastMapping`` against that
database:

   >>> from pygr import blast
   >>> db = seqdb.SequenceFileDB('data/gapping.fa')
   >>> blastmap = blast.BlastMapping(db)

Now pull in some sequences (for now, we'll use sequences from the same
database):

   >>> ungapped = db['ungapped']
   >>> gapped = db['gapped']

And let's use BLAST to search the database with the sequence!  The first
approach is to use the ``__getitem__`` interface to ``BlastMapping``:

   >>> slice = blastmap[gapped]
   >>> edges = slice.edges()

The ``__getitem__`` interface returns an ``NLMSASlice`` containing
intervals aligned between the source sequence (``gapped``) and
sequences in the database:

   >>> for (src, dest, edge) in edges:
   ...   print repr(src), 'matches', repr(dest)
   gapped[0:40] matches ungapped[0:40]
   gapped[0:74] matches gapped[0:74]
   gapped[44:74] matches ungapped[40:70]

Yep, it's that easy!

You can also search the entire database against itself using the
``__call__`` interface to ``BlastMapping``; this returns a full
alignment in an ``NLMSA``, from which you can retrieve individual
``NLMSASlice`` objects by querying by sequence:

   >>> al = blastmap(queryDB=db)
   >>> for seq in db.values():
   ...    for (src, dest, edge) in al[seq].edges():
   ...       print repr(src), 'matches', repr(dest)
   gapped[0:40] matches ungapped[0:40]
   gapped[0:74] matches gapped[0:74]
   gapped[44:74] matches ungapped[40:70]
   ungapped[0:40] matches gapped[0:40]
   ungapped[40:70] matches gapped[44:74]
   ungapped[0:70] matches ungapped[0:70]

Using the "translated BLASTs" (blastx and tblastx)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``BlastMapping`` objects can't handle the translated BLASTs because
they don't return coordinates in the same sequence space as the query
sequences.  So, we have to use ``BlastxMapping instead``.

For example, suppose you want to search a protein database ('sp_all_hbb')

   >>> dna_db = seqdb.SequenceFileDB('data/hbb1_mouse.fa')
   >>> dna_seq = dna_db['gi|171854975|dbj|AB364477.1|']
   >>> prot_db = seqdb.SequenceFileDB('data/sp_all_hbb')

Construct and query the ``BlastxMapping`` object as you would a
``BlastMapping`` object...

   >>> blastmap = blast.BlastxMapping(prot_db)
   >>> results = blastmap[dna_seq]

but now the results are one or more NLMSASlice objects containing alignments
between *translations* of the query sequence and the subject protein
sequences:

   >>> results = list(results)
   >>> match = results[0]
   >>> print match.seq[0:10], 'frame', match.seq.frame
   MVHLTDAEKA frame 1

and you can iterate over the matches as you normally would: 

   >>> for n, (src, dest, edge) in enumerate(match.edges()):
   ...    print src[0:10], repr(src)
   ...    print dest[:10], repr(dest)
   ...    print '--'
   ...    if n == 2: break
   MVHLTDAEKA annotgi|171854975|dbj|AB364477.1|:0[0:52]
   MVHWTQEERD HBB_MUSGR[0:52]
   --
   VHLTDAEKAA annotgi|171854975|dbj|AB364477.1|:0[1:53]
   VHWTGEEKAL HBB_SQUAC[0:52]
   --
   VHLTDAEKAA annotgi|171854975|dbj|AB364477.1|:0[1:53]
   VSLTDEEKHL HBB2_TORMA[0:52]
   --

If you use the __call__ interface to retrieve a full NLMSA object
(rather than the slice(s) associated with a single sequence), you can
query the NLMSA with translations of the DNA sequences.  You can
access those via a translation database attached to the query sequence
database:

   >>> from pygr import translationDB
   >>> translation_db = translationDB.get_translation_db(dna_db)

To get a translation starting at a particular nucleotide, you can slice
the sequences returned from the translation_db,

   >>> frame0 = translation_db[dna_seq.id][0:]
   >>> print str(frame0[:10])
   MVHLTDAEKA

   >>> frame1 = translation_db[dna_seq.id][1:]
   >>> print str(frame1[:10])
   WCT*LMLRRL

   >>> negframe0 = (-translation_db[dna_seq.id])[:0]
   >>> print str(negframe0[:10])
   LVVLVSQGSG

or you can request an annotation from the associated annotation db in
a specific frame by appending a ':' followed by the desired frame to
the sequence ID:

   >>> frame0 = translation_db.annodb[dna_seq.id + ':0']
   >>> print str(frame0[:10])
   MVHLTDAEKA
   
   >>> frame1 = translation_db.annodb[dna_seq.id + ':1']
   >>> print str(frame1[:10])
   WCT*LMLRRL

   >>> negframe0 = translation_db.annodb[dna_seq.id + ':-0']
   >>> print str(negframe0[:10])
   LVVLVSQGSG

These translations can then be used to query the matches from BlastxMapping
as you would normally do:

   >>> blastmap = blast.BlastxMapping(prot_db)
   >>> results = blastmap(dna_seq)
   >>> frame0_results = results[frame0]
   >>> print frame0_results.keys()[:3]
   [HBB_MUSGR[0:52], HBB_SQUAC[0:52], HBB2_TORMA[0:52]]

How can we get the original DNA sequence for a match?  Easy --
dereference the annotation object into its source DNA sequence:

   >>> src, dest, edge = frame0_results.edges()[0]

   >>> print repr(src.sequence), 'aligns to', repr(dest)
   gi|171854975|dbj|AB364477.1|[0:156] aligns to HBB_MUSGR[0:52]

   >>> aa = '  '.join(str(dest[:10]))
   >>> print "%s\n%s" % (src.sequence[:30], aa)
   ATGGTGCACCTGACTGATGCTGAGAAGGCT
   M  V  H  W  T  Q  E  E  R  D

Storing BLAST alignments on disk
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The BlastMapping classes offer a nice interface, but everything we've
done above is transient -- what about saving the results of a long BLAST?
That's simple -- you just have to pass the BlastMapping class an on-disk
NLMSA.

First, create the mapping.

   >>> db = seqdb.SequenceFileDB('data/gapping.fa')
   >>> blastmap = blast.BlastMapping(db)

Now, create an on-disk NLMSA.  BLAST alignments are pairwise (they
only involve two sequences) and they are not bidirectional (x matches
y does not always mean y matches x):

   >>> store_al = cnestedlist.NLMSA('tempdir/blastn', mode='w', pairwiseMode=True, bidirectional=False)

Pass the NLMSA into the BLAST search, and then build it:

   >>> _ = blastmap(queryDB=db, al=store_al)
   >>> store_al.build(saveSeqDict=True)

Now, let's pretend we're exiting and restarting Python...

   >>> del store_al

...and re-load the NLMSA from disk:

   >>> loaded_al = cnestedlist.NLMSA('tempdir/blastn')

As before, we have to use the saved seqDict because we're not using
``worldbase``.  Retrieve the sequence...

   >>> db = loaded_al.seqDict
   >>> g = db['gapping.gapped']

... and query it for matches, as above:

   >>> edges = loaded_al[g].edges()
   >>> for (src, dest, edge) in edges:
   ...   print repr(src), 'matches', repr(dest)
   gapped[0:40] matches ungapped[0:40]
   gapped[0:74] matches gapped[0:74]
   gapped[44:74] matches ungapped[40:70]

And voila, done!

.. for recipes, instead?
.. Building an Alignment Database from MAF files
.. ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. Example: Mapping an entire gene set onto a new genome version
.. ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. @CTB figure out sphinx linking stuff to link NLMSA To NLMSA docs, etc.
.. @CTB section pointing them towards MAF, gene set, etc. recipes?
.. @CTB link doctests into tests again!
.. @CTB non-pairwise, etc. (more complicated) NLMSAs?  building NLMSAs?
   @CTB talk about building NLMSAs with complicated data sets