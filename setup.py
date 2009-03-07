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

import os, sys, stat
from shutil import copyfile
from distutils.core import setup, Extension
from distutils.command.build import build

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
Topic :: Scientific/Engineering :: Bioinformatics
"""

# split into lines and filter empty ones
CLASSIFIERS = filter(None, CLASSIFIERS.splitlines() )

# if pyrex is not present try compiling the C files
try:
    from Pyrex.Compiler.Version import version as PYREX_VERSION
    from Pyrex.Distutils import build_ext
    if PYREX_VERSION < "0.9.8":
        error ( "pyrex version >=0.9.8 required, found %s" % PYREX_VERSION )
    ext = 'pyx'
    cmdclass = { 'build_ext': build_ext }
except ImportError, exc:
    ext = 'c'
    cmdclass = {}

# extension sources 
seqfmt_src = [ 'pygr/seqfmt.%s' % ext ]
cdict_src  = [ 'pygr/cgraph.c', 'pygr/cdict.%s' % ext ]
nested_src = [ 'pygr/intervaldb.c', 'pygr/cnestedlist.%s' % ext, 'pygr/apps/maf2nclist.c' ]

def main():
    setup(
        name = PYGR_NAME ,
        version= PYGR_VERSION,
        description = __doc__,
        author = "Christopher Lee",
        author_email='leec@chem.ucla.edu',
        url = 'http://sourceforge.net/projects/pygr',
        classifiers = CLASSIFIERS,

        packages = [ 'pygr', 'pygr.apps' ],

        ext_modules = [
            Extension( 'pygr.seqfmt', seqfmt_src ),
            Extension( 'pygr.cdict',  cdict_src ),
            Extension( 'pygr.cnestedlist', nested_src), 
        ],

        cmdclass = cmdclass,
     )

if __name__ == '__main__':
    main()    
