:mod:`classutil` --- Basic support classes and functions
========================================================

.. module:: classutil
   :synopsis: Basic support classes and functions.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>


This module provides basic support functions for pickling and unpickling,
etc.

FilePopen
---------

A subprocess.Popen-like class interface that works not only on Python 2.4+
(which have the subprocess module)
but also on Python 2.3 (which lacks the subprocess module).  The main goal
is to avoid the pitfalls of subprocess.Popen.communicate(), which cannot handle
more than a small amount of data, and to avoid both the possibility of deadlocks
and the issue of threading, by using temporary files instead of pipes.

Note: on Python 2.4+, this class simply uses Python's subprocess module.
On Python 2.3, which lacks the subprocess module, it provides its own
equivalent functionality (e.g. properly escaping arguments etc.).

.. class:: FilePopen(args, bufsize=0, executable=None, stdin=None, stdout=None, stderr=None, *largs, **kwargs)

   Mimics the interface of subprocess.Popen() with a few additions:

   *stdin=classutil.PIPE* will create a temporary file for communicating
   with the subprocess (rather than using a pipe as subprocess.Popen() does).
   The temporary file will automatically be deleted when the :class:`FilePopen`
   object is deleted.  Instead of using Popen.communicate() (which cannot
   handle more than a moderate amount of data), you directly write to the
   :attr:`FilePopen.stdin` file object.

   *stdout=classutil.PIPE* will create a temporary file for communicating
   with the subprocess (rather than using a pipe as subprocess.Popen() does).
   The temporary file will automatically be deleted when the :class:`FilePopen`
   object is deleted.  Instead of using Popen.communicate() (which cannot
   handle more than a moderate amount of data), you directly read from the
   :attr:`FilePopen.stdout` file object.

   *stderr=classutil.PIPE* will create a temporary file for communicating
   with the subprocess (rather than using a pipe as subprocess.Popen() does).
   The temporary file will automatically be deleted when the :class:`FilePopen`
   object is deleted.  Instead of using Popen.communicate() (which cannot
   handle more than a moderate amount of data), you directly read from the
   :attr:`FilePopen.stderr` file object.

   *stdinFlag*, if passed, gives a flag to add the stdin filename directly
   to the command line (rather than passing it by redirecting stdin).
   Example: ``stdinFlag="-i"`` will add the following to the commandline:
   ``-i /path/to/the/file``

   If set to None, the stdin filename is still appended to the commandline,
   but without a preceding flag argument.

   *stdoutFlag*: exactly the same thing, except for the stdout filename.

.. method:: FilePopen.wait()

   Use this exactly as for subprocess.Popen.wait(), to wait for the 
   subprocess to complete.

   Note: you do *not* need to rewind the *stdin* file prior to calling
   :meth:`FilePopen.wait()`; it does that automatically.  Similarly,
   you do not need to rewind the *stdout* or *stderr* files after
   calling :meth:`FilePopen.wait()`; it does that automatically.

.. method:: FilePopen.close()

   Close and delete any temporary files, i.e. any cases where you
   specified *stdin*, *stdout*, or *stderr* as ``classutil.PIPE``.
   Note: if you supplied a file
   object as an argument to *stdin*, *stdout*, or *stderr*, it will 
   *not* be closed for you.

.. attribute:: FilePopen.stdin

   A file object for writing to the subprocess' standard input.  Unlike
   subprocess.Popen (which warns that writing to this attribute may hang),
   you can safely write directly to this file object, prior to calling
   :meth:`FilePopen.wait()`, which actually starts the subprocess,
   passing it your input on its stdin.

.. attribute:: FilePopen.stdout

   A file object for reading the subprocess' standard output.  Unlike
   subprocess.Popen (which warns that reading from this attribute may hang),
   you can safely read directly from this file object, after calling
   :meth:`FilePopen.wait()`.

.. attribute:: FilePopen.stderr

   A file object for reading from the subprocess' standard error.  Unlike
   subprocess.Popen (which warns that reading from this attribute may hang),
   you can safely read directly from this file object, after calling
   :meth:`FilePopen.wait()`.

Here is an example of how we use :class:`FilePopen` to run a Python
XMLRPC server script in our test suite::

    def run_server(self):
        'this method blocks, so run it in a separate thread'
        cmdArgs = (sys.executable, self.server_script) + tuple(sys.argv) \
                  + ('--port=' + str(self.port),
                     '--port-file=' + self.port_file,
                     '--pygrdatapath=' + self.pygrDataPath,
                     '--downloadDB=' + self.downloadDB,
                     '--resources=' + ':'.join(self.pygrDataNames))
        p = classutil.FilePopen(cmdArgs, stdout=classutil.PIPE,
                                stderr=classutil.PIPE)
        try:
            logger.debug('Starting XML-RPC server: ')
            logger.debug(repr(cmdArgs))
            if p.wait():
                logger.warn('XML-RPC server command failed!')
            output = p.stdout.read()
            errout = p.stderr.read()
            logger.debug('XML-RPC server output: %s' % output)
            logger.debug('XML-RPC server error out: %s' % errout)
        finally:
            p.close()

In this example, we did not write to stdin, but did read from the subprocess'
stdout and stderr.


.. function:: call_subprocess(*popenargs, **kwargs)

   Mimics the subprocess.call() interface, using :class:`FilePopen`.


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

* avoids generating bogus __del__ warnings as Python shelve.open() does.

* makes shelve raise a clearly stated error message if accessed after being
  closed, regardless of the Python version.
  Prior to Python 2.6, the standard library shelve raised a totally
  baffling error message in this case.


SourceFileName
--------------

.. class:: SourceFileName(s)

   *s*: a file path string.

   A subclass of ``str``, specifically for recording file path strings.
   :mod:`worldbase` uses this in a couple ways:

   * when data is saved to :mod:`worldbase`, it automatically recognizes
     that this class cannot be transported via XMLRPC (i.e. a reference to
     a local file will not be valid / accessible on a remote computer).

   * when data is saved to :mod:`worldbase`, it automatically recognizes
     non-absolute path strings (e.g. in UNIX, a path that does not begin with /)
     and saves information about the current directory, so that if a 
     future user is in a different directory when trying to unpickle this
     object, it will still be able to find the file (by re-constructing
     an absolute path to that file).

   In all other respects it simply behaves like a string.

   We recommend that whenever you are creating objects that you might later
   want to save to :mod:`worldbase`, you should use this class for storing any
   strings that are actually file paths.


Pickling Convenience Methods
----------------------------

:mod:`worldbase` relies on Python pickling.  To make it easier to provide
correct pickling / unpickling methods for classes that you write, 
Pygr provides a standard __getstate__ and __setstate__ method:

.. function:: standard_getstate(self)

   Use this within one of your classes as follows::

      class MyClass(object):
          __getstate__ = classutil.standard_getstate
          _pickleAttrs = dict(foo=0, bar=0)

   * like any __getstate__, this function returns the "state" of your
     object as a dictionary of attribute name:value pairs.

   * this function expects ``self._pickleAttrs`` to be a dictionary
     whose keys represent attribute names from ``self`` which should
     be saved as the "state" of the object.  If a key has an associated
     string value, the attribute is saved as that name rather than the
     original name.

   * in keeping with the :func:`get_bound_subclass()` mechanism, it
     *always* looks for the attributes ``itemClass`` and ``itemSliceClass``
     and saves them specially.  Specifically, if such a class has been
     automatically subclassed, it saves the original class (rather than
     the automatically generated subclass).

     Simple recommendation: if your class uses ``itemClass``, 
     ``itemSliceClass``, and the :func:`get_bound_subclass()` mechanism,
     it should also use :func:`standard_getstate()`.

.. function:: standard_setstate(self)

   Use this within one of your classes as follows::

      class MyClass(object):
          __setstate__ = classutil.standard_setstate

   * like any __setstate__, this function applies a state dictionary
     for re-instantiating your object data.  Specifically, it passes
     the state dictionary as keyword arguments to the __init__ of your class.

   * It adds the keyword argument ``unpicklingMode=True`` when calling your
     __init__, to allow it to detect that it is being unpickled (rather than
     created for the first time).  Your __init__ should either accept this
     as a keyword argument, or ignore it (by having a ``**kwargs`` for
     accepting keyword args that did not match your list of explicit argument
     names).

   Recommendation: if your class uses :func:`standard_getstate` it should
   probably also use :func:`standard_setstate`.

Subclass Binding
----------------

This refers to a common Pygr pattern of automatically creating a subclass of
a user class, solely for the purpose of binding descriptors to it.

.. function:: get_bound_subclass(obj, classattr='__class__', subname=None, factories=(), attrDict=None, subclassArgs=None)

   Automatically creates a subclass of a specific instance, for binding
   attribute descriptors to.  Pygr uses this mechanism widely, as a replacement
   for __getattr__ / __setattr__.  Python descriptors ("properties") are
   far more modular than writing __getattr__ / __setattr__ methods.

   Example usage: :class:`sqlgraph.SQLTable` uses :class:`sqlgraph.TupleO`
   as its ``itemClass``.  In other words, each "row object" is an instance
   of :class:`sqlgraph.TupleO`, which stores the row data as a simple tuple
   (this takes less memory than storing a __dict__ for each row object).
   To provide named attributes for each of the columns, we can simply add
   a Python descriptor to the ``itemClass``, for each column name.  However,
   we must first create a subclass of :class:`sqlgraph.TupleO` to which
   we can add these descriptors, so that different instances of
   :class:`sqlgraph.SQLTable` will be isolated from each other.  (If we
   added the descriptors directly to :class:`sqlgraph.TupleO`, 
   every table instance using :class:`sqlgraph.TupleO` as its itemClass
   would see each other's column attributes).  The SQLTable.__init__ uses
   :func:`get_bound_subclass()` to create a subclass of the specified
   class attribute as follows::

       get_bound_subclass(self, 'itemClass', self.name)

   This replaces self.itemClass with the new, subclassed version.  As 
   part of creating this subclass, :func:`get_bound_subclass()` will call
   its _init_subclass() class method.  :class:`sqlgraph.TupleO` has
   such a class method, which adds to itself all the column descriptors
   from its associated :class:`sqlgraph.SQLTable` column list.

   *obj*: the object whose attribute is to be subclassed.

   *classattr*: specifies the name of the attribute to be subclassed.
   Naturally, this attribute must be a Python class object.  If this
   class object is already a subclass created by :func:`get_bound_subclass()`,
   it will be left unchanged.  Otherwise, a subclass of this class
   will be created, and saved in place of the original class on
   the *obj* object's attribute specified by *classattr*.

   Typical settings of *classattr* include ``'__class__'``, ``'itemClass'``,
   ``'itemSliceClass'``, etc.  If *classattr* is either ``'itemClass'`` or
   ``'itemSliceClass'``, :func:`get_bound_subclass()` automatically adds the 
   attribute ``db`` to the subclass, set to *obj* itself.

   *subname*, if not None, gives a string suffix to be appended to 
   the original class name, for constructing the subclass name.  This is
   only for making the output of ``repr()`` meaningful.

   *factories*, if not None, must be a list of callable functions that
   each take a single dictionary argument, into which they can save
   attribute name:value pairs, which will be added to the subclass' __dict__.
   This provides a general way for being able to add custom attributes
   to the subclass.

   *attrDict*, if not None, must be a dictionary of attribute name:value pairs,
   which will be added to the subclass __dict__.  This provides another way
   to add custom attributes to the subclass.

   If the subclass has a ``_init_subclass()`` class method (possibly 
   inherited from the base class), it will be called to initialize the
   subclass.  

   *subclassArgs*, if not None, will be passed as the set of keyword arguments
   to the ``_init_subclass()`` class method.  If None, no arguments are passed.

      
RecentValueDictionary
---------------------

A subclass of weakref.WeakValueDictionary.  Rather than flushing a value
the instant its refcount falls to zero, it keeps the *most recently accessed*
N values even if their refcount falls to zero.  
This combines the elegant cache behavior of a WeakValueDictionary
(only keep an item in cache if the user is still using it),
with the most common efficiency pattern: locality, i.e.
references to a given thing tend to cluster in time.  Note that
this works *even* if the user is not holding a reference to
the item between requests for it.  Our Most Recent queue will
hold a reference to it, keeping it in the WeakValueDictionary,
until it is bumped by more recent requests.

.. class:: RecentValueDictionary(n)

   *n*: the maximum number of objects to keep in the Most Recent queue,
   default value 50.

