=====================
Sequence manipulation
=====================

----------------------
Operating on sequences
----------------------

In Python there is a distinction between the `printable string` and the 
`printable representation` (repr) of an object. For pygr sequence objects 
the former is used to access the content, while the latter is used to display 
what the object represents.

.. doctest::

    >>> from pygr.sequence import *
    >>>
    >>> # create a sequence named MyGene
    >>> s = Sequence('attatatgccactat', 'MyGene') 
    >>>
    >>> # printable string
    >>> str( s )
    'attatatgccactat'
    >>>
    >>> # printable representation
    >>> repr( s ) 
    'MyGene[0:15]'
    >>>
    >>> # python slice gives last 8 nt of s
    >>> st = s[-8:] 
    >>> str( st ) # string conversion just yields the sequence as a string 
    'gccactat'
    >>> repr ( st ) 
    'MyGene[7:15]'
    >>> rc = -s # get the reverse complement
    >>> str( rc[:5] ) # its first five letters
    'atagt'

See more about indexing later in the document.

-------------------
Reading FASTA files
-------------------

The ``tests2/data`` directory contains a FASTA file that stores a partial 
yeast sequence (chromosomes 1, 2 and 3). We will use this file to 
demonstrate pygr's sequence manipulation functionality.

The seqdb module provides an interface to a sequence databases stored 
in FASTA, BLAST or relational databases. The first step is to read the 
file as a ``SequenceFileDB`` class instance. If this is first time accessing 
this file pygr will create a number of index files (stored under the same path) 
that will speed up access to the sequence stored in the fasta file.

.. doctest::

    >>> import pygr
    >>> from pygr.seqdb import SequenceFileDB
    >>> db = SequenceFileDB( 'data/partial-yeast.fasta' )

The ``db`` name represents a dictionary like object (interface), meaning it 
has all that methods that a python dictionary, such as: ``keys(), values(), items()``...

>>> # list all fasta ids extracted from the file
>>> db.keys()
['chr01', 'chr02', 'chr03']
>>>
>>> # make a shortcut to chromosome 1
>>> chr01 = db['chr01']
>>>
>>> # the lenght of chromosome 1 
>>> len(chr01)
230208

.. note::
    
    Keep in mind that while most pygr objects 
    behave as containers, they may represent different classes 
    behind the scenes. This distinction becomes important when trying to 
    access functionality that only certain types have. 

For example the type of the ``db`` object above is a sequence-file based database:

>>> type( db )
<class 'pygr.seqdb.SequenceFileDB'>

whereas the type of the object ``chr01`` that references chromosome 1 is 
a file-based sequence:

>>> type( chr01 )
<class 'pygr.classutil.FileDBSequence_partial-yeast.fasta'>

Most of the time these objects behave in a convenient way. Occasionally, 
when in we're in doubt of what a particular instance can do we can print 
its type then look up the details in the class documentation.

-----------------
Sequence indexing
-----------------

In pygr sequence indices start from 0 and are *non-inclusive* at the end, 
(similar to the UCSC bed format). The slice of the first 10 bases will 
be written as [start:end] (``[0:10]``), its lenght is ``end-start = 10``, 
and maps to indices of 0 to 9. We will get an error if we try to access 
index=10! Consecutive non-overlapping sequences of lenght 10 would be written 
as ``[0:10]``, ``[10:20]``, ``[20:30]`` etc. In pygr positive indexes count forward from 
the start, negative indices count backward from the end of the slice. 
To get the reverse complement of a sequence you can apply the minus operator.

>>> # the sequence indices start from 0! 
>>> seq = chr01[0:10]
>>>
>>> # remind ourselves what the type of this object is
>>> type(seq)
<class 'pygr.sequence.SeqDBSlice'>
>>>
>>> len(seq)
10
>>>
>>> # the sequence may be transfored into a string
>>> type( str(seq) )
<type 'str'>
>>>
>>> str(seq)
'CCACACCACA'
>>>
>>> # get the last three bases 
>>> str( seq[-3:] )
'ACA'
>>>
>>> # get the reverse complement of 'CCACACCACA'
>>> str( -seq )
'TGTGGTGTGG'

Note above that applying the 'str' function transformed
the SeqDBSlice object into a python string. This is can 
be a handy transformation when attempting to save or print 
some results. 

.. note::

    Failing to properly reconcile data with zero vs one based indexing is a source common errors. 
    
A common type of indexing operates on indices that start at 1 and include
the last index (for example the GFF format from Sanger Institute). 
In that representation the slice of the first 10 bases will have the indices 
of 1 to 10 (including 1 and 10). While this type of indexing appears 
more convenient, it can lead to other type of problems. Note that
the lenght of the interval is now ``10-1 = 9`` and consecutive nonoverlapping 
slices would need to be written as ``[1:10]``, ``[11:20]``, ``[21:30]``. 

The problem is further confounded by the fact that some formats display 
the intervals with smaller coordinates first regardless of the orientation 
(in which case one needs to know the strand information) while others 
use the start coordinate as the one where the transcription starts
(5' to 3' direction) therefore on the reverse strands start > end. 

It is essential to be aware of these distinctions and to know how to 
transform the coordinates to the pygr format! Being "one off" is one of 
the most common errors one can make.

For a practical example lets retrieve the chromosomal coordinates for yeast 
orfs *YCL054W* and *YBL074C* from various online resources:

    - from UCSC we get ``(chr3, 31448, 33974)`` and ``(chr2, 86719, 87787)``
    - from SGD we get  ``(chr3, 31449, 33974)`` and ``(chr2, 87787, 86720)``
    - from ENSEMBLE we get ``(chr3, 31449, 33974)`` and ``(chr2, 86720, 87787)``

Note how all three are slightly different. First let's look at orf 
*YCL054W* of lenght 2526 located on the forward strand:

>>> # get some shortcuts to chromosomes
>>> chr02, chr03 = db['chr02'], db['chr03']
>>>
>>> # the UCSC format works directly with pygr
>>> start, stop = (31448, 33974)
>>> YCL054W = chr03[start:stop]
>>> len(YCL054W)
2526
>>> # get the orientation forward=1, reverse=-1
>>> YCL054W.orientation
1
>>> # fetch the first 10 and the last 10 bases
>>> str( YCL054W[:10]),  str( YCL054W[-10:]) 
('ATGGGTAAGA', 'GAAAAAGTAG')

To get the same result with the SGD and ENSEMBLE output we would 
need to decrement the start coordinate by one while keeping the 
end coordinate the same. 

The reverse strand is bit more work. pygr interprets the start coordinate 
in the coordinate system that corresponds to transcriptional direction. This means
that inverting the start:end coordinates will return the reverse complement.

>>> str( chr01[0:10])
'CCACACCACA'
>>> str( chr01[10:0]  )
'TGTGGTGTGG'

Orf YBL074C of lenght 1068 is located on the reverse strand thus we'll need 
to indicate this either by specifying start > end or by reverse complementing
the intervals wherever start < end. As it turns out, each of the 
coordinate formats returned above will need small adjustments 
when accessing features on the reverse strand. First option:

>>> # use the original interval as specified by UCSC
>>> start, stop = (86719, 87787)
>>>
>>> # apply reverse complement
>>> YBL074C = -chr02[start:stop]
>>> len(YBL074C)
1068
>>> # get the orientation forward=1, reverse=-1
>>> YBL074C.orientation
-1
>>> # fetch the first 10 and the last 10 bases
>>> str( YBL074C[:10]),  str( YBL074C[-10:]) 
('ATGAATACTG', 'AAGGCCATAA')

An alternative way to write the same would have been to swap the start and end
coordinates:

>>> # start, stop = (86719, 87787) reverse these coordinates
>>> start, stop = (87787, 86719) 
>>> YBL074C = chr02[start:stop]
>>> len(YBL074C)
1068
>>> # get the orientation forward=1, reverse=-1
>>> YBL074C.orientation
-1
>>> # fetch the first 10 and the last 10 bases
>>> str( YBL074C[:10]),  str( YBL074C[-10:]) 
('ATGAATACTG', 'AAGGCCATAA')

.. note::

    Thus to transform data from a *one-based* index to a *zero-based* index:
    
        1. identify which number represents the transcription start 
        2. decrement the transcription start and keep the end coordinate the same 
      
    For the reverse transformation increment the start.