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
	"pygr/__init__",
	"pygr/graphquery",
	"pygr/mapping",
        "pygr/coordinator",
        "pygr/Data",
        "pygr/classutil",
        "pygr/dbfile",
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

def compilePyrex(cfile):
   'for proper class pickling, pyrexc needs full-dotted-module-path filename format'
   from shutil import copyfile
   modulename='.'.join(cfile.split('/')) # e.g. pygr/cdict.c -> pygc.cdict.c
   ctarget=os.path.join(os.path.dirname(cfile),modulename) # ADD DIRECTORY PATH
   copyfile(cfile[:-2]+'.pyx',ctarget[:-2]+'.pyx') # COPY pyx FILE TO DESIRED NAME
   try: # COPY pxd FILE IF IT EXISTS...
      copyfile(cfile[:-2]+'.pxd',ctarget[:-2]+'.pxd') # COPY pxd FILE TO DESIRED NAME
   except IOError:
      pass
   cmd='pyrexc %s.pyx'%ctarget[:-2]
   print cmd
   exit_status=os.system(cmd) # TRY USING PYREX TO COMPILE EXTENSIONS
   if exit_status!=0:  # CAN'T RUN THE PYREX COMPILER TO PRODUCE C
      print '\n\nPyrex compilation failed!  Is pyrexc missing or not in your PATH?'
      return False # SIGNAL COMPILATION FAILED
   copyfile(ctarget,cfile) # COPY .c FILE BACK TO DESIRED NAME
   return True # SIGNAL COMPILATION SUCCEEDED

def pyrexIsUpToDate(cfile):
   'True if .c file is newer than the .pyx file'
   cstat=os.stat(cfile)
   try: 
      pyxstat=os.stat(cfile[:-2]+'.pyx')
   except OSError: # PYREX .pyx CODE IS MISSING??  JUST USE OUR EXISTING C CODE THEN.
      print 'Warning: pyrex code %s is missing!  Check your distribution!' % (cfile[:-2]+'.pyx')
      return True
   try:
      if cstat[8]<os.stat(cfile[:-2]+'.pxd')[8]:
         return False # pxd FILE IS NEWER THAN C FILE, MUST RERUN PYREXC
   except OSError:
      pass
   return cstat[8]>pyxstat[8] # COMPARE THEIR st_mtime VALUES

def add_pyrex_extensions():
   'prepare extension module code, add to setup metadata'
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


try:
   v1, v2, v3 = sys.version_info[:3] # ONLY AVAILABLE IN >= 2.0
   if v1 == 2 and v2 < 2: # 2.1 LACKS GENERATORS... SO NOT GOOD ENOUGH
      raise AttributeError
except AttributeError:
   raise EnvironmentError('Sorry, pygr does not support python versions before 2.2')
else:
   if v1>2 or v2>2 or v3>=3: # ONLY ALLOWED IF >=2.2.3
      metadata['download_url'] = "http://prdownloads.sourceforge.net/pygr/pygr-%s.tar.gz" % version
      metadata['classifiers'] = [ c for c in classifiers.split('\n') if c ]


def check_extensions(dist,ext_modules):
   from distutils.command.build import build
   b = build(dist)
   b.finalize_options()
   sys.path.append(os.path.join(b.build_lib,'pygr'))
   for extmodule in ext_modules:
      try:
         exec 'import %s' % extmodule.name.split('.')[-1]
      except ImportError:
         print >>sys.stderr,'Build of module %s appears to have failed!' % extmodule.name
         return False
   return True
      
def clean_up_pyrex_files(ext_modules,base='pygr'):
   for ext_module in ext_modules:
      name = ext_module.name.split('.')[-1]
      rmfiles = ['%s/%s.c' %(base,name),'%s/%s.%s.c' %(base,base,name)]
      for filename in rmfiles:
         try:
            os.remove(filename)
         except OSError:
            pass


if __name__=='__main__':
   add_pyrex_extensions() # PREPARE EXTENSION CODE FOR COMPILATION
   retry = False
   try:
      dist = setup(**metadata) # NOW DO THE BUILD AND WHATEVER ELSE IS REQUESTED
   except SystemExit: # SOMETHING WENT WRONG WITH THE BUILD, CLEAN UP AND RETRY IT...
      retry = True
   if retry or not check_extensions(dist,metadata['ext_modules']):
      print >>sys.stderr,'Attempting to clean up pyrex files and try again...'
      clean_up_pyrex_files(metadata['ext_modules'])
      add_pyrex_extensions()
      dist = setup(**metadata)
      if not check_extensions(dist,metadata['ext_modules']):
         raise OSError('Build failed. You are either missing pyrex or a C compiler.\nPlease fix this, and run the build command again!')
      else:
         print 'Build succeeded!'

   
