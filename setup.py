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

   # version check
   v1, v2 = sys.version_info[:2]
   if v1 < 2:
      raise 'pygr does not support python 1.x'
   if v1 == 2 and v2 < 2:
      raise 'pygr does not support python2.1 or earlier version'

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
    #'download_url': "http://prdownloads.sourceforge.net/pygr/" \
    #                "pygr-%s.tar.gz" % version, 
    #'classifiers': [ c for c in classifiers.split('\n') if c ],

    'py_modules': [
	"pygr/__init__",
	"pygr/graphquery",
	"pygr/mapping",
        "pygr/coordinator",
        "pygr/Data",
        "pygr/nlmsa_utils",
        "pygr/nestedlist",
        "pygr/xnestedlist",
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

v1, v2 = sys.version_info[:2]
if v1 >= 2 and v2 > 2:
    metadata['download_url'] = "http://prdownloads.sourceforge.net/pygr/pygr-%s.tar.gz" % version
    metadata['classifiers'] = [ c for c in classifiers.split('\n') if c ]

def copyFile(source,target):
   'OS independent copy function'
   if source==target: # PROTECT AGAINST POSSIBILITY OF OVER-WRITING SELF
      return # NO NEED TO DO ANYTHING
   ifile=file(os.path.normpath(source))
   ofile=file(os.path.normpath(target),'w')
   ofile.write(ifile.read())
   ifile.close()
   ofile.close()

def compilePyrex(cfile):
   'for proper class pickling, pyrexc needs full-dotted-module-path filename format'
   modulename='.'.join(cfile.split('/')) # e.g. pygr/cdict.c -> pygc.cdict.c
   ctarget=os.path.join(os.path.dirname(cfile),modulename) # ADD DIRECTORY PATH
   copyFile(cfile[:-2]+'.pyx',ctarget[:-2]+'.pyx') # COPY pyx FILE TO DESIRED NAME
   try: # COPY pxd FILE IF IT EXISTS...
      copyFile(cfile[:-2]+'.pxd',ctarget[:-2]+'.pxd') # COPY pxd FILE TO DESIRED NAME
   except IOError:
      pass
   cmd='pyrexc %s.pyx'%ctarget[:-2]
   print cmd
   exit_status=os.system(cmd) # TRY USING PYREX TO COMPILE EXTENSIONS
   if exit_status!=0:  # CAN'T RUN THE PYREX COMPILER TO PRODUCE C
      print '\n\nPyrex compilation failed!  Is pyrexc missing or not in your PATH?'
      return False # SIGNAL COMPILATION FAILED
   copyFile(ctarget,cfile) # COPY .c FILE BACK TO DESIRED NAME
   return True # SIGNAL COMPILATION SUCCEEDED

def pyrexIsUpToDate(cfile):
   'True if .c file is newer than the .pyx file'
   cstat=os.stat(cfile)
   try: 
      pyxstat=os.stat(cfile[:-2]+'.pyx')
   except OSError: # PYREX .pyx CODE IS MISSING??  JUST USE OUR EXISTING C CODE THEN.
      print 'Warning: pyrex code %s is missing!  Check your distribution!' % (cfile[:-2]+'.pyx')
      return True
   return cstat[8]>pyxstat[8] # COMPARE THEIR st_mtime VALUES

def runSetup(script_args=None):
   'prepare extension module code, run distutils setup'
   buildExtensions=[]
   pyrexTargets={'pygr/cdict.c':
                 Extension('pygr.cdict',sources = ['pygr/cgraph.c', 'pygr/cdict.c']),
                 'pygr/cnestedlist.c':
                 Extension('pygr.cnestedlist',
                           sources = ['pygr/intervaldb.c', 'pygr/cnestedlist.c',
                                      'pygr/apps/maf2nclist.c']),
                 'pygr/seqfmt.c':Extension('pygr.seqfmt',sources = ['pygr/seqfmt.c'])}
   for cfile,extmodule in pyrexTargets.items():
      if os.access(cfile,os.R_OK) and pyrexIsUpToDate(cfile):
         print 'Using existing pyrexc-generated C-code',cfile
      else:
         compilePyrex(cfile)  # HMM, NO PYREXC COMPILED CODE, HAVE TO RUN PYREXC
      if os.access(cfile,os.R_OK): 
         buildExtensions.append(extmodule)
      else: # PYREX COMPILATION FAILED, CAN'T ADD THIS MODULE TO OUR EXTENSIONS
         print 'Skipping extension module... you will be lacking some functionality:',\
               cfile[:-2]

   if len(buildExtensions)>0:
      metadata['ext_modules'] = buildExtensions

   setup(**metadata) # NOW DO THE BUILD AND WHATEVER ELSE IS REQUESTED


if __name__=='__main__':
   if runTests(): # DID EVERYTHING TEST OK?
      runSetup() # DO THE INSTALL
   else: # EXIT WITH ERROR CODE
      sys.exit(1)
      
