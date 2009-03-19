=================
Pygr Data Recipes
=================

What is pygr.Data
-----------------

This module provides a simple but powerful interface for creating a 
'data namespace' in which users can access complex datasets by simply 
requesting the name chosen for a given dataset - much like 
Python's import mechanism enables users to access a specified 
code resource by name, without worrying about where it should be 
found or how to assemble its many parts. 

``pygr.Data`` is intended to be used for commonly used top-level data resources, 
such as a sequence database or alignment database.  Typically, each resource 
that you store in it should be a database, a container for a 
particular set of data items.  Here we are using the term "database" loosely, 
to refer to a container object that gives you access to a large number of individual data items.  

For example,this could be a MySQL table, a BLAST sequence database, a Python dictionary,
or a Python shelve.  It is NOT recommended that you treat pygr.Data resource 
names as a substitute for a database, i.e. you should store the 
container object as a ``pygr.Data`` resource, not each of the individual 
data items that it contains.  In this sense, pygr.Data is 
intended to be a "database of databases" rather than a database 
of individual data items.  

.. note::
 
 to store an object in ``pygr.Data``

 1. your object must be picklable
 2. your object must have a __doc__ string, which should describe
    what kind of data it contains, so that users can view this information
    when they do a dir() directory listing of pygr.Data.

How to store data in pygr.Data
------------------------------

To store a large set of data items we suggest that
you first place them in a ``pygr.Data.Collection`` (either in memory or on disk),
then save the ``Collection`` object as a ``pygr.Data`` resource.

.. testsetup:: [*]
    
    >>> import os, pathfix, testutil
    >>> out_name = testutil.tempfile( 'exontuples.db' )
    >>> tempdir  = testutil.TempDir( 'pygrdata' )
    >>> testutil.change_pygrdatapath( tempdir.path )
    
We'll assume that ``out_name`` is the file name that will store the saved collection.
To create a ``Collection`` stored as a BerkeleyDB (using the Python shelve module),
we need to supply a path for the file in which we want the data stored:

>>> # the data that needs to be stored
>>> data = dict( values=[100, 200, 300], gene='BPT2' )
>>> 
>>> import pygr.Data
>>> collect = pygr.Data.Collection( filename=out_name, mode='wr',writeback=False)
>>> collect.__doc__ = 'Test data'
>>>
>>> # collect behaves like a dictionary
>>> collect.update( data )
>>>
>>> sorted( collect.keys() )
['gene', 'values']
>>>
>>> collect['values']
[100, 200, 300]
>>> 
>>> # assign to a pygr.Data resource name
>>> pygr.Data.Bio.Genomics.SomeData = collect 
>>> pygr.Data.save()

.. testsetup:: [*]
    
    This is to verify that the output file has been created 
    >>> os.path.isfile( out_name )
    True

Now we can retrieve the data later and operate on it as needed:

>>> other = pygr.Data.Bio.Genomics.SomeData()
>>> sorted( other.keys() )
['gene', 'values']
>>> other['values']
[100, 200, 300]

How to download with pygr.Data
------------------------------

To download data with pygr.Data use the ``SourceURL`` class. The download will be performed 
when the resource is reloaded. This happens either in the same process via a reload(pygr.Data)
or automatically in a different process.

    >>> from pygr.downloader import SourceURL
    >>>
    >>> url = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
    >>> url.__doc__ = 'test download'
    >>>
    >>> pygr.Data.addResource('Bio.Test.Download1', url)
    >>> pygr.Data.save()
    >>>
    >>> # the download will be performed after a reload
    >>> mod = reload( pygr.Data ) 
    >>> fpath = pygr.Data.Bio.Test.Download1( download=True )
