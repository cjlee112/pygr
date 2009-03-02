"""
The sole purpose of this module is to alter the sys.path upon 
import in such a way to get pygr from the source directory rather than
@CTB finish comment?

See the README.txt file for details on how to change the behavior.

NOTE in place builds are required:

python setup.py build_ext -i
"""

import sys, os, distutils.util, platform

import testoptions, logger

def path_join(*args):
    "Joins and normalizes paths"
    return os.path.abspath(os.path.join(*args))

def stop(msg):
    "A fatal unrecoverable error"
    logger.error(msg)
    sys.exit()

# get the current directory of the current module
curr_dir = os.path.dirname(__file__)

# this is the extra path that needs be added
base_dir = path_join(curr_dir, '..', '..')

# get the pygr source directory
pygr_source_dir = path_join(base_dir, 'pygr')

# build specific directories
os_info = distutils.util.get_platform()
version = ".".join(platform.python_version_tuple()[:2])
lib_dir  = 'lib.%s-%s' % (os_info, version,)
temp_dir = 'temp.%s-%s' % (os_info, version,)
pygr_build_dir = path_join(base_dir, 'build', lib_dir)
pygr_temp_dir  = path_join(base_dir, 'build', temp_dir)

# we'll do a top level option parsing in this module as well
parser = testoptions.option_parser()

# parse the arguments
options, args = parser.parse_args()

# this makes it less clunky
use_pathfix = not options.no_pathfix

if use_pathfix:
    # alter the import path
    if options.builddir:
        sys.path = [ pygr_build_dir  ] + sys.path 
        required_prefix = pygr_build_dir
    else:
        sys.path = [ base_dir  ] + sys.path
        required_prefix = pygr_source_dir

try:
    # import the main pygr module
    import pygr
except ImportError, exc:
    stop ("unable to import: %s" %  exc)
      
try:
    # import an extension module
    from pygr import cnestedlist
except ImportError, exc:
    stop("unable to import extension module: %s" %  exc )

if use_pathfix:
    
    for mod in [ pygr, cnestedlist ]:
        # test that the imported python modules have the required prefix
        if not mod.__file__.startswith(required_prefix):
            stop ("module %s imported from invalid path: %s" % \
                  (mod.__name__, mod.__file__))
