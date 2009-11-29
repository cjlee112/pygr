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

import os
import sys

try:
    from setuptools import setup, Extension
except ImportError:
    print 'Setuptools not imported, falling back to distutils'
    from distutils.core import setup, Extension

import pygr


def error(msg):
    "Fatal errors"
    print('*** error %s' % msg)
    sys.exit()

PYGR_NAME = "pygr"
PYGR_VERSION = pygr.__version__

if sys.version_info < (2, 3):
    error('pygr requires python 2.3 or higher')

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
CLASSIFIERS = filter(None, CLASSIFIERS.splitlines())

# Setuptools should handle all this automatically
if 'setuptools' in sys.modules:
    try:
        import pkg_resources
        pkg_resources.require('Pyrex>=0.9.8')
        ext = 'pyx'
    except pkg_resources.DistributionNotFound:
        ext = 'c'
    cmdclass = {}
else:
# if pyrex is not present try compiling the C files
    try:
        from Pyrex.Compiler.Version import version as PYREX_VERSION
        from Pyrex.Distutils import build_ext
        if PYREX_VERSION < "0.9.8":
            error("pyrex version >=0.9.8 required, found %s" % PYREX_VERSION)
        ext = 'pyx'
        cmdclass = {'build_ext': build_ext}
    except ImportError, exc:
        ext = 'c'
        cmdclass = {}

# extension sources
seqfmt_src = [os.path.join('pygr', 'seqfmt.%s' % ext)]
cdict_src = [os.path.join('pygr', 'cgraph.c'),
             os.path.join('pygr', 'cdict.%s' % ext)]
nested_src = [os.path.join('pygr', 'intervaldb.c'),
              os.path.join('pygr', 'cnestedlist.%s' % ext),
              os.path.join('pygr', 'apps', 'maf2nclist.c')]


def main():
    setup(
        name = PYGR_NAME,
        version= PYGR_VERSION,
        description = \
'Pygr, a Python graph-database toolkit oriented primarily on bioinformatics',
        long_description = __doc__,
        author = "Christopher Lee",
        author_email='leec@chem.ucla.edu',
        url = 'http://code.google.com/p/pygr/',
        license = 'New BSD License',
        classifiers = CLASSIFIERS,

        packages = ['pygr', 'pygr.apps'],

        ext_modules = [
            Extension('pygr.seqfmt', seqfmt_src),
            Extension('pygr.cdict', cdict_src),
            Extension('pygr.cnestedlist', nested_src),
        ],

        cmdclass = cmdclass,
     )

if __name__ == '__main__':
    main()
