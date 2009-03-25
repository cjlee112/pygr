:mod:`sequtil` --- Basic sequence utility functions
====================================================

.. module:: sequtil
   :synopsis: Basic sequence utility functions.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>



Functions for Reading and Writing FASTA format
----------------------------------------------
The sequtil module provides several convenience functions:

.. function:: read_fasta(ifile)

   a generator function
   that yields tuples of *id,title,seq* from *ifile*.


.. function:: write_fasta(ofile, s, chunk=60, id=None)

   writes the sequence *s*
   to the output file *ofile*, using *chunk* as the line width.
   *id* can provide an identifier to use instead of the default
   ``s.id``.



