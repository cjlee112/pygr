C Library for NestedList: libnclist
===================================


The C library (libnclist) for NestedList storage and query
is actually included in the pygr source code package,
however we have not yet added documentation on its C interfaces.
It is straightforward to compile intervaldb.c as a library,
and link that to your own C program, following the examples in
our Python interface code (cnestedlist.pyx) to see how to call the C functions.
You can see extensive examples of how to build or query using these intervaldb functions, by looking at the :class:`IntervalDBIterator` and :class:`IntervalDB` classes (in-memory nested list) or :class:`IntervalFileDBIterator` and :class:`IntervalFileDB` classes (on disk) in the cnestedlist.pyx file.  This code directly calls the intervaldb C functions so you can see exactly how everything is done (the pyx suffix signifies that this is Pyrex code, i.e. for providing a python interface to C functionality).  It is not a very complicated process: basically, a few steps:

Using the Library
-----------------

To build the C library
^^^^^^^^^^^^^^^^^^^^^^
To build libnclist, just cd to the pygr/pygr source directory and type ``make``.
The current version of the Makefile builds a statically linked library (libnclist.a).
To build a shared library on your platform, just modify the compilation flags
in the Makefile.

To build a nested list database
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* 1. load a bunch of 1:1 interval:interval pairs into an array of IntervalMap data structures, whose start,end members are your source coordinate system, and target_id gives an integer ID of the aligned sequence, and target_start,target_end are coordinates in the aligned sequence.  As you can see in the IntervalDB constructor, there is a read_intervals() convenience function that will load this for you from a text file.  The save_tuples() function shows a trivial example of how to store the data yourself...
  
* 2. call build_nested_list() or build_nested_list_inplace() on the array.  This actually builds the nested list in memory.  The _inplace variant uses less memory (algorithm described in detail in the paper).
  
* 3. if you wish to store the nested list to on-disk index files (for querying from disk rather than in-memory), call write_binary_files() with the desired filename.  Note that multiple files will be saved by adding different suffixes to this filename.


To query a nested list database stored in-memory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* 1. allocate an iterator using interval_iterator_alloc() and call find_intervals() to do the query.  See IntervalDB.find_overlap_list() for a detailed example.
* 2. call free_interval_iterator() to free the iterator.


To query a nested list database stored on-disk
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

* 1. call read_binary_files() to get a data structure describing the size values, sublist structure etc.  Note that this does not load the nested list database into memory, it just loads a small amount of information for efficiently accessing its indexes.
* 2. allocate an iterator as usual, and call find_file_intervals() to do the query.  See IntervalFileDB.find_overlap_list() for detailed example.
* 3. call free_interval_iterator() as usual.


I also suggest you start by looking at intervaldb.c, which has build_nested_list() functions, query functions for both in-memory and on-disk nested list databases (find_intervals() and find_file_intervals() respectively), and reading / writing functions for the binary index (on-disk nested list), read_binary_files() and write_binary_files().

Important Caveats
^^^^^^^^^^^^^^^^^
Note that the Python alignment class (NLMSA) built on top of intervaldb can handle much larger alignments than can be built in memory, because it knows how to split up an alignment into separate coordinate systems that can each be built separately.  At this time, intervaldb.c is limited in the size of nested list it can build, by the total amount of memory you can allocate.  This only affects the build phase, obviously, not the on-disk query phase.  We haven't gotten around to implementing a pure on-disk build algorithm, which would obviously be slower, but would eliminate this memory size build limitation.

