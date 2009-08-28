#!/usr/bin/env python
"""
Pygr
====

Pygr is an open source software project used to develop graph database 
interfaces for the popular Python language, with a strong emphasis 
on bioinformatics applications ranging from genome-wide analysis of 
alternative splicing patterns, to comparative genomics queries of 
multi-genome alignment data.
"""

import os, sys

try:
    from setuptools import setup, Extension
except ImportError:
    print 'Setuptools not imported, falling back to distutils'
    from distutils.core import setup, Extension

def error(msg):
    "Fatal errors"
    print( '*** error %s' % msg )
    sys.exit()

import pygr

PYGR_NAME = "pygr"
PYGR_VERSION = pygr.__version__

if sys.version_info < (2, 3):
    error( 'pygr requires python 2.3 or higher' )

CLASSIFIERS = """
Development Status :: 5 - Production/Stable
Operating System :: MacOS :: MacOS X
Operating System :: Microsoft :: Windows :: Windows NT/2000
Operating System :: OS Independent
Operating System :: POSIX
Operating System :: POSIX :: Linux
Operating System :: Unix
Programming Language :: Python
Topic :: Scientific/Engineering
Topic :: Scientific/Engineering :: Bio-Informatics
"""

# split into lines and filter empty ones
CLASSIFIERS = filter(None, CLASSIFIERS.splitlines() )

cmdclass = {}

def main():
    setup(
        name = PYGR_NAME ,
        version= PYGR_VERSION,
        description = 'Pygr, a Python graph-database toolkit oriented primarily on bioinformatics applications',
        long_description = __doc__,
        author = "Christopher Lee",
        author_email='leec@chem.ucla.edu',
        url = 'http://code.google.com/p/pygr/',
        license = 'New BSD License',
        classifiers = CLASSIFIERS,

        packages = [ 'pygr', 'pygr.apps' ],

        cmdclass = cmdclass,
     )

if __name__ == '__main__':
    main()    
