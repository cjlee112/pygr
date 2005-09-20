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
from distutils.core import setup

testdir = os.path.join(os.getcwd(),"tests")
sys.path.append(testdir)
os.environ['PYGRPATH'] = os.path.join(os.getcwd(),"pygr")
name = "pygr"
version = "1.0"

try:
   import test_loader
except ImportError:
   raise "Unable to load test code. Please check to see that test_loader.py resides in (%s)\n" % (testdir)

try:
   import MySQLdb
except ImportError:
   print "\nWarning: You do not have a required module installed (MySQLdb). While this module is not necessary to use core components, the provided apps code will not work. Installing anyway...\n"


if (test_loader.TestFrameWork().go()):

   print "\nAll tests passed, continuing install...\n"

else:

   print "\nSource tainted! This code has been tampered with, or has not been QA'd. Please retrieve a new archive.\n"
   sys.exit(1)

classifiers = """
Development Status :: 5 - Production/Stable
Operating System :: MacOS :: MacOS X
Operating System :: Microsoft :: Windows :: Windows NT/2000
Operating System :: OS Independent
Operating System :: POSIX
Operating System :: POSIX :: Linux
Operating System :: Unix
Programming t Language :: Python
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Bioinformatics
"""
metadata = {
    'name': name,
    'version': version,
    'description': "Pygr", 
    'long_description': __doc__,
    'author': "Christopher Lee",
    'author_email': "leec@ucla.edu",
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

setup(**metadata)                                                                               
