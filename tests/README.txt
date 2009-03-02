General guide
=============

The default behavior is to add the source directory to the import path.
Developers are expected to build the extension libraries in place with:

python setup.py build_ext -i

See the section on flags on how to customize this behavior.

Typical use cases
=================

Test modules end with _test.py suffix. Each test module may be 
executed on its own and will produce high verbosity output.

The runtests.py script may be used to run all test modules 
or a subset of them.

Run all tests (modules that end in _test.py): 
	python runtest.py 

To run one test you can execute the file itself: 
	python seqdb_test.py

Other way to run one test is via the runtest script:
	python runtest.py seqdb_test.py

Run two tests: 
	python runtest.py seqdb_test.py sequence_test.py

Run all tests excluding seqdb_test:
	python runtest.py -x seqdb_test.py 

Change verbosity levels:
	python runtest.py -v 2

You may use full file names, or module names.

Flags
=====

To see the flags execute the script with the -h flag
	
	python runtest.py -h

Usage: runtest.py [options]

Options:
  -h, --help            show this help message and exit
  -n, --nopath          do not alter the python import path
  -b, --buildpath       use the platform specific build directory
  -s, --strict          stops testing after a test suite fails
  -x, --exclude         excludes the files that are listed
  -v VERBOSITY, --verbosity=VERBOSITY
                        sets the verbosity (0, 1, or 2)
  --coverage            runs figleaf and collects the coverage information
  --performance         runs the performance tests (not implemented)

These options are only used internally:

  --port=PORT           sets the port information for the XMLRPC server
  --pygrdatapath=PYGRDATAPATH
                        sets the pygraphdata path for the XMLRPC server
  --downloadDB=DOWNLOADDB
                        sets the downloadDB shelve for the XMLRPC server
  --resources=RESOURCES
                        sets the downloadable resources, separate multiple
                        ones with a : symbol

Notes
=====
  - The lowest (0) verbosity turns off DEBUG level messages
  - The test specific connection information is read out from the 
   mysql.cnf file in the tests2 directory (for now it is last resort 
   but should be the primary way)
  - The main test runner will delete the temp directory before each run.
  - Each test module must implement the get_suite() function that returns 
  a unittest test suite
  - Import the pathfix module at the start of each test module to alter the 
  import path. This module will parse and apply the command line variables.