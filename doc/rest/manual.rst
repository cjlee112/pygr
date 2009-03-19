=============================
Pygr Installation and Testing
=============================


.. _install:

Installation
============

Installing pygr is quite simple::

   tar -xzvf pygr-0.3.tar.gz
   cd pygr
   python setup.py install


Once the test framework has completed successfully, the setup script
will install pygr into python's respective site-packages directory.

If you don't want to install pygr into your system-wide site-packages,
replace the "python setup.py install" command with::

   python setup.py build

This will build pygr but not install it in site-packages.

Pygr contains several modules imported as follows::

   from pygr import seqdb # IMPORT SEQUENCE DATABASE MODULE


If you did not install pygr in your system-wide site-packages, you
must set your PYTHONPATH to the location of your pygr build.
For example, if your top-level pygr source directory is PYGRDIR then
you'd type something like::

   setenv PYTHONPATH PYGRDIR/build/lib.linux-i686-2.3

where the last directory name depends on your specific architecture.










.. _testing-doc:

Testing
=======


The following subsections provide details about how the testing of different
modules of Pygr functionality.

Running Tests
-------------
First, you must have ``nose`` installed.  Then simply go to
the testing directory and run the tests::

   cd pygr/tests
   python protest.py

One can also run individual test files::

   python protest.py pygrdata_test.py


To run ALL tests, including very time-consuming and resource-intensive
NLMSA build tests, tell it to include our "megatests"::

   python protest.py *_megatest.py

Note: depending on what modules you have installed, and what data resources
you have available locally, some tests may be skipped; it will indicate
which tests were skipped.  Note that you must have the necessary input
datasets to run some of the megatests.  For obvious reasons, we do not include
these massive datasets in the Pygr source code repository or install packages.
To run a specific megatest, first look at its source code to determine what
input data it requires; often this is obvious from the megatest file name.

What is protest.py?
-------------------
For testing pygr.Data, it is helpful to use a testing framework
that enables each test to run in a separate process.  Since nose does
not allow this, we use a small script compatible with nose, that
runs the each test in a separate process (i.e. separate Python interpreter
session).

.. _test-utils:

Testing Approach
----------------

Given Pygr's focus on working with large datasets, testing has been a bit of a puzzle.
We have always included an automated test suite with the source code package.
However, we obviously can't include big datasets in the package, so how can
we code our tests so that they will automatically run only those tests that
are possible in the user's local environment and resources?

Here's a summary of the testing approach we've developed to solve these challenges:

* Based on advice from Titus Brown, we've adopted ``nose`` as the testing
  framework for testing Pygr.
* Tests are included with the source code package
  in ``pygr/tests" in files with names like "foo_test.py".
* We moved our existing unit tests to be run by nose.
* We are adding our extensive tutorial examples as a wide-ranging set of functional tests.  The main goal is for the complete set of tests to be sensitive to failures in just about any area of pygr functionality.  So, for example, checking that the calculated percent identity for each result in a multigenome alignment query matches the stored correct result is very sensitive to many functions working right (correct construction of the alignment; correct query results; correct sequence interval retrieval; etc.)
* Major data dependencies for individual tests will be managed with pygr.Data.  That is, each test setup() will simply try to obtain the data it needs by requesting named pygr.Data resources.  If required data are missing, the test will be skipped.  In my lab, we will keep a nightly test platform where ALL tests must pass (no skipping!).
* Tests that take a long time or a lot of resources (e.g. 28 vertebrate genome alignment NLMSA build) will have the suffix "_megatest" (instead of the default suffix "_test"), and thus will be omitted by a normal nosetests run.  We will include all megatests on our nightly test platform.


How To Automatically Skip Tests?
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
When resources necessary for running a specific test are missing
(such as a data file, or network access), the test should be automatically
skipped.  The pattern mandated by nose, which we follow, is that the
:meth:`setup()` method should raise a nose.SkipTest exception to
indicate that the test should be skipped.  E.g.::

   class PygrDownload_Test(object):
       def setup(self,**kwargs):
           try:
               s = SourceURL('http://www.doe-mbi.ucla.edu/~leec/test.gz')
           except socket.gaierror:
               raise nose.SkipTest

The :class:`SourceURL` class raises an exception if the network connection
fails, which in turn causes the test to be skipped (rather than being
reported as "test failed".

Testing Utilities
-----------------

nosebase Module
^^^^^^^^^^^^^^^
This module is included in the pygr/tests directory and provides the following
convenience classes and functions:

.. function:: TempDir()

   Creates a temporary directory, which will be automatically deleted
   when the :class:`TempDir` instance is released.  Provides convenience methods
   :meth:`subfile()` and :meth:`copyFile()` used as follows::

      tmp = TempDir()
      path = str(tmp) # GET THE PATH TO THIS TEMPORARY DIRECTORY
      targetPath = tmp.subfile('foo.test') # APPEND foo.test TO THE DIRECTORY PATH
      newPath = tmp.copyFile('/some/path/to/some/file') # COPY TO TMP DIR AND RETURN ITS PATH



.. function:: TempPygrData()

   Subclass of :class:`TempDir`; creates a temporary directory,
   and forces pygr.Data to use it as an (initially
   empty) resource database.  Useful for testing pygr.Data functionality.


.. function:: TempPygrDataMySQL(dbname='test',args=")

   Subclass of :class:`TempPygrData`; creates a temporary table in MySQL,
   and forces pygr.Data to use it as an (initially
   empty) resource database.  Useful for testing pygr.Data functionality.

   *dbname* should be the name of the MySQL database in which the temp
   table should be created.  *args*, if provided, should be a whitespace
   separated list of one or more of *host, user, password*.  NOTE: *args*
   MUST begin with a space, because it is simply appended to the tablename for
   calling the standard pygr.Data creation mechanism.


.. function:: skip_errors(errors...)

   Decorator for making a setup function skip a specified list of errors
   (i.e. if one of those errors occurs, cause the associated test(s) to be skipped).
   For example, to protect against the user either lacking the necessary
   database module, or access to a database server that can run the test::

      @skip_errors(ImportError)
      def setup(self):
      import MySQLdb
      try:
      Seq_Test.setup(self,**self.mysqlArgs)
      except MySQLdb.MySQLError:
      raise ImportError



.. function:: PygrDataTextFile(path,mode='r')

   dict-like interface to a text file storage that is pygr.Data-smart,
   i.e. it uses pygr.Data.getResource.loads(), so data will be saved
   and loaded in terms of pygr.Data resource IDs, which will be loaded
   from pygr.Data in the usual way.  Intended for storing test results
   in a platform-independent text format.  *mode* can be "r" (read),
   "w" (write) or "a" (append).

   For example, to save a correct test result, just give it a unique
   name::

      store = nosebase.PygrDataTextFile('tryme.pickle','w')
      store['hbb1 fragment'] = ival # SAVE AS PICKLE IN TEXT FILE

   The data is saved to the disk file immediately, each time you
   execute such a "key assignment" statement.
   You can now write a testcase that runs the appropriate steps to
   construct *ival*, and check whether your test result matches the correct
   answer you previously stored::

      store = nosebase.PygrDataTextFile('tryme.pickle')
      saved = store['hbb1 fragment']
      assert ival == saved, 'seq ival should match stored result'

   Note: when you open a :class:`PygrDataTextFile` in read or append mode, the
   file is read into memory as text.  Only when you request a specific key name
   will it attempt to obtain the pygr.Data resource associated with that key name.

   By convention, our correct test results are stored in ``pygr/tests/results``.
   So a convenient way to save a new test result (which you have verified is
   correct, and now wish to store), is to append it to an existing
   :class:`PygrDataTextFile`::

      store = nosebase.PygrDataTextFile('results/seqdb1.pickle','a')
      store['hbb1 fragment'] = ival # SAVE AS PICKLE IN TEXT FILE



.. function:: TestXMLRPCServer(*pygrDataNames)

   create an XMLRPC server loaded with the pygr.Data resources specified
   by the arguments provided as *pygrDataNames*.  Note: the XMLRPC server
   runs in a separate process (see the script ``pygrdata_server.py``)
   launched using :meth:`os.system`, to simulate
   real client-server usage patterns.  Note: this class will first attempt to
   load the specified pygr.Data resources (using your PYGRDATAPATH as usual)
   to ensure that they exist, before launching the XMLRPC server.  If a pygr.Data
   resource cannot be found, :exc:`KeyError` will be raised.

   To access the XMLRPC server
   using pygr.Data, call the object's :meth:`access_server` method to receive a reference
   to pygr.Data that will load data only from the XMLRPC server.  To shut down the
   XMLRPC server, call the object's :meth:`close` method::

      self.server = nosebase.TestXMLRPCServer('Bio.Seq.Swissprot.sp42')
      pygrData = self.server.access_server()
      sp = pygrData.Bio.Seq.Swissprot.sp42() # TRY TO ACCESS FROM XMLRPC SERVER
      self.server.close() # SHUT DOWN THE XMLRPC SERVER




protest: single-test per process
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
We found that trying to use nose to test pygr.Data was not ideal.
The problem is that what we really want to test is that pygr.Data works persistently
between separate python interpreter sessions, whereas nose forces ALL of the tests
to be performed within a single session.  I found myself wasting a lot of time
trying to figure out why a particular nose test did not work,
rather than trying to find / figure out potential pygr bugs.
I therefore wrote a short script (protest.py) that performs the
same function as nose, but runs each test in a separate Python
interpreter session.

To run all tests::

   python protest.py

To tell it to run tests in one particular file::

   python protest.py pygrdata_test.py


