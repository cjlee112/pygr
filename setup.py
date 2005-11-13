#!/usr/bin/python
"""\

Pygr
****

Pygr is an open source software project used to develop graph database 
interfaces for the popular Python language, with a strong emphasis 
on bioinformatics applications ranging from genome-wide analysis of 
alternative splicing patterns, to comparative genomics queries of 
multi-genome alignment data. 
"""\


import os
import sys
from distutils.core import setup, Extension

def runTests():
   testdir = os.path.join(os.getcwd(),"tests")
   sys.path.append(testdir)
   os.environ['PYGRPATH'] = os.path.join(os.getcwd(),"pygr")

   try:
      import test_loader
   except ImportError:
      raise "Unable to load test code. Please check to see that test_loader.py resides in (%s)\n" % (testdir)

   try:
      import MySQLdb
   except ImportError:
      print "\nWarning: You do not have a required module installed (MySQLdb). While this module is not necessary to use core components, the provided apps code will not work. Installing anyway...\n"


   if (test_loader.TestFrameWork(testExtensions=False).go()):
      print "\nAll tests passed, continuing install...\n"
      return True
   else:
      print "\nSource tainted! This code has been tampered with, or has not been QA'd. Please retrieve a new archive.\n"
      return False





name = "pygr"
version = "1.0"

classifiers = """
Development Status :: 5 - Production/Stable
Operating System :: MacOS :: MacOS X
Operating System :: Microsoft :: Windows :: Windows NT/2000
Operating System :: OS Independent
Operating System :: POSIX
Operating System :: POSIX :: Linux
Operating System :: Unix
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Bioinformatics
"""



metadata = {
    'name': name,
    'version': version,
    'description': "Pygr", 
    'long_description': __doc__,
    'author': "Christopher Lee",
    'author_email': "leec@chem.ucla.edu",
    'license': "GPL",
    'platforms': "ALL",
    'url': "http://sourceforge.net/projects/pygr",
    'download_url': "http://prdownloads.sourceforge.net/pygr/" \
                    "pygr-%s.tar.gz" % version, 
    'classifiers': [ c for c in classifiers.split('\n') if c ],

    'py_modules': [
	"pygr/__init__",
	"pygr/graphquery",
	"pygr/mapping",
        "pygr/coordinator",
        "pygr/nestedlist",
	"pygr/poa",
	#"pygr/lpo",  # THIS IS TEMPORARY
	"pygr/schema",
	"pygr/seqdb",
	"pygr/sequence",
	"pygr/sequtil",
	"pygr/sqlgraph",
        "pygr/parse_blast",
	"pygr/apps/__init__",
	"pygr/apps/leelabdb",
	"pygr/apps/seqref",
	"pygr/apps/splicegraph",
        "pygr/apps/maf2VSgraph",
        ]

   }

def runSetup(script_args=None):
   buildExtensions=True
   if os.access('pygr/cdict.c',os.R_OK):
      print 'Using existing pyrexc-generated C-code...'
   else:  # HMM, NO PYREXC COMPILED CODE, HAVE TO RUN PYREXC
      exit_status=os.system('cd pygr;pyrexc cdict.pyx') # TRY USING PYREX TO COMPILE EXTENSIONS
      if exit_status!=0:  # CAN'T RUN THE PYREX COMPILER TO PRODUCE C
         print '\n\nPyrex compilation failed!  Is pyrex missing or not in your PATH?'
         print 'Skipping all extension modules... you will be lacking some functionality: pygr.cdict'
         buildExtensions=False
      else:
         print 'Generating C code using pyrexc: cdict.c...'
         exit_status=os.system('cd pygr;pyrexc cnestedlist.pyx') # COMPILE PYREX cnestedlist


   if buildExtensions:
      cdict_module = Extension('pygr.cdict',sources = ['pygr/cgraph.c', 'pygr/cdict.c'])
      cnestedlist_module = Extension('pygr.cnestedlist',
                                     sources = ['pygr/intervaldb.c', 'pygr/cnestedlist.c',
                                                'pygr/apps/maf2nclist.c'])
      metadata['ext_modules'] = [cdict_module,cnestedlist_module]

   setup(**metadata) # NOW DO THE BUILD AND WHATEVER ELSE IS REQUESTED


if __name__=='__main__':
   if runTests(): # DID EVERYTHING TEST OK?
      runSetup() # DO THE INSTALL
   else: # EXIT WITH ERROR CODE
      sys.exit(1)
      
