:mod:`classutil` --- Basic support classes and functions
========================================================

.. module:: classutil
   :synopsis: Basic support classes and functions.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>


This module provides basic support functions for pickling and unpickling,
etc.

open_shelve
-----------
Alternative to Python standard library function :class:`shelve.open` with several benefits:

.. function:: open_shelve(filename,mode=None,writeback=False,allowReadOnly=False,useHash=False,verbose=True)



* uses bsddb btree by default instead of bsddb hash, which is very slow
  for large databases.  Will automatically fall back to using bsddb hash
  for existing hash-based shelve files.  Set *useHash=True* to force it to use bsddb hash.
  In our experience, the Python standard library :class:`shelve` object using
  bsddb hash file by default, becomes very slow and produces unreasonably large
  files, when the number of records exceeds several million.  Fortunately, the
  bsddb btree file seems to solve this problem, so :meth:`open_shelve()` uses
  it by default.
  
* *allowReadOnly=True* will automatically suppress permissions errors so
  user can at least get read-only access to the desired shelve, if no write permission.
  
* *mode=None* first attempts to open file in read-only mode, but if the file
  does not exist, opens it in create mode.
  
* raises standard exceptions defined in dbfile: :class:`WrongFormatError`,
  :class:`PermissionsError`, :class:`ReadOnlyError`, :class:`NoSuchFileError`

