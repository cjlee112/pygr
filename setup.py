#!/usr/bin/env python
"""
Pygr
****

Pygr is an open source software project used to develop graph database 
interfaces for the popular Python language, with a strong emphasis 
on bioinformatics applications ranging from genome-wide analysis of 
alternative splicing patterns, to comparative genomics queries of 
multi-genome alignment data.
"""

try:
   from setuptools import setup
except ImportError:
   print '(WARNING: importing distutils, not setuptools!)'
   from distutils.core import setup
                  
import os
import sys
import imp
from stat import ST_MTIME

from distutils.command.build import build
from distutils.core import setup, Extension
from shutil import copyfile

###

name = "pygr"
version = "0.7"

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

def ppath(*args):
   'return path in form pygr/arg1/arg2... using os.path.join()'
   l = ['pygr'] + list(args)
   return os.path.join(*l)

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
    'py_modules': [
	"pygr.__init__",
	"pygr.graphquery",
	"pygr.mapping",
        "pygr.coordinator",
        "pygr.Data",
        "pygr.downloader",
        "pygr.classutil",
        "pygr.dbfile",
        "pygr.nlmsa_utils",
        "pygr.nestedlist",
        "pygr.xnestedlist",
	"pygr.poa",
	"pygr.schema",
	"pygr.seqdb",
	"pygr.sequence",
	"pygr.sequtil",
	"pygr.sqlgraph",
        "pygr.parse_blast",
	"pygr.apps.__init__",
	"pygr.apps.leelabdb",
	"pygr.apps.seqref",
	"pygr.apps.splicegraph",
        "pygr.apps.maf2VSgraph",
        "pygr.apps.catalog_downloads"
        ]
   }

pyrexTargetDict = {ppath('cdict.c'):
                   Extension('pygr.cdict',
                             sources = [ppath('cgraph.c'),
                                        ppath('cdict.c')]),
                   ppath('cnestedlist.c'):
                   Extension('pygr.cnestedlist',
                             sources = [ppath('intervaldb.c'),
                                        ppath('cnestedlist.c'),
                                        ppath('apps','maf2nclist.c')]),
                   ppath('seqfmt.c'):
                   Extension('pygr.seqfmt',
                             sources = [ppath('seqfmt.c')])}




def compilePyrex(cfile):
   # for proper class pickling, pyrexc needs full-dotted-module-path
   # filename format
   
   sep = os.path.sep                    # path separator used on this platform

   # e.g. pygr/cdict.c -> pygc.cdict.c   
   modulename = '.'.join(cfile.split(sep))

   # add dir path
   ctarget = os.path.join(os.path.dirname(cfile), modulename)
   
   # copy pyx file to desired name
   copyfile(cfile[:-2] + '.pyx', ctarget[:-2] + '.pyx')
   
   # copy pxd file if it exists
   try:
      copyfile(cfile[:-2] + '.pxd', ctarget[:-2] + '.pxd') 
   except IOError:
      pass
   
   cmd = 'pyrexc %s.pyx' % ctarget[:-2]
   
   print '** Running:', cmd
   exit_status = os.system(cmd) # Try compiling with pyrex
   
   if exit_status != 0:
      print >>sys.stderr, '''
      
Pyrex compilation failed!  Is pyrexc missing or not in your PATH?
'''
      return False

   # success!
   
   copyfile(ctarget, cfile) # copy .c file back to desired name
   return True

def pyrexIsUpToDate(cfile):
   'True if .c file is newer than the .pyx file'
   
   c_modtime = os.stat(cfile)[ST_MTIME]
   
   # Is pyx file newer than C file?
   pyx_file = cfile[:-2] + '.pyx'
   try:
      # compare time of last modification
      if c_modtime < os.stat(pyx_file)[ST_MTIME]:
         return False
   except OSError:
      print 'Warning: pyrex code %s is missing!  Check your distribution!' \
            % (pyrex_file)
      return True

   # Is pxd file newer than C file?
   pxd_file = cfile[:-2] + '.pxd'
   try:
      if c_modtime < os.stat(pxd_file)[ST_MTIME]:
         return False
   except OSError:
      pass

   # C file is up to date
   return True

def add_pyrex_extensions(pyrex_targets):
   'prepare extension module code, add to setup metadata'
   buildExtensions = []
   for cfile, extmodule in pyrex_targets.items():
      if os.access(cfile, os.R_OK) and pyrexIsUpToDate(cfile):
         print 'Using existing pyrexc-generated C-code', cfile
      else:
         # hmm, no pyrexc compiled code; have to run pyrexc
         compilePyrex(cfile)

      if os.access(cfile, os.R_OK): 
         buildExtensions.append(extmodule)
         
      else: # pyrex compilation failed; can't add this module to our extensions
         print 'Skipping extension module:', cfile[:-2]
         # @CTB fail?

   if len(buildExtensions) > 0:
      metadata['ext_modules'] = buildExtensions


try:
   v1, v2, v3 = sys.version_info[:3]
   
   if v1 == 2 and v2 < 2: # 2.1 lacks generators!
      raise AttributeError
except AttributeError:
   raise EnvironmentError('pygr does not support python versions before 2.2')
else:
   if v1 > 2 or v2 > 2 or v3 >= 3: # ONLY ALLOWED IF >=2.2.3
      metadata['download_url'] = "http://prdownloads.sourceforge.net/pygr/pygr-%s.tar.gz" % version
      metadata['classifiers'] = [ c for c in classifiers.split('\n') if c ]

def try_load_extension(name, modpath):
   "Try to load 'name' module from the given module path."
   try:
      (fp, pathname, descr) = imp.find_module(name, [modpath])
   except ImportError:
      return False

   fp.close()
   return True

def check_extensions(dist, ext_modules):
   'True if all ext_modules can be successfully imported'

   b = build(dist)
   b.finalize_options()
   
   # by default, look for modules in build
   modpath = os.path.join(b.build_lib, 'pygr')
   
   # if --inplace specified, look for modules in source code.
   if '--inplace' in sys.argv or '-i' in sys.argv:
      modpath = 'pygr'

   for module in ext_modules:
      module_name = module.name.split('.')[-1]
      if not try_load_extension(module_name, modpath):
         print >>sys.stderr, '''\
Unable to find module %s in build directory: %s
Did the build fail?
''' % (module.name, modpath)
         return False
      
   return True
      
def clean_up_pyrex_files(ext_modules, base='pygr'):
   'remove pyrex-compiled C files'

   rmfiles = []
   for ext_module in ext_modules:
      name = ext_module.name.split('.')[-1]
      
      rmfiles.append(os.path.join(base, name + '.c'))
      rmfiles.append(os.path.join(base, base + '.' + name + '.c'))

   for filename in rmfiles:
      try:
         os.remove(filename)
      except OSError:
         pass

if __name__=='__main__':
   # Prepare extension code for compilation
   add_pyrex_extensions(pyrexTargetDict)
   
   retry = False
   try:
      # Now do the build & whatever else is requested
      dist = setup(**metadata)
   except SystemExit:
      # If something went wrong with the build, clean up & retry it
      retry = True
      
   if retry or not check_extensions(dist, pyrexTargetDict.values()):
      print >>sys.stderr, 'Attempting to clean up pyrex files and try again...'
      clean_up_pyrex_files(pyrexTargetDict.values())
      
      add_pyrex_extensions(pyrexTargetDict)
      dist = setup(**metadata)
      
   if not check_extensions(dist, pyrexTargetDict.values()):
      raise OSError('''Build appears to have failed.
You may be missing pyrex or a C compiler.
Please fix this, and run the build command again!''')

   print 'Build succeeded!'
