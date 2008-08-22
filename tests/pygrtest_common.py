import sys
import os
import distutils.util
import platform
import os.path

#
# import pygr & check to make sure it's imported from the right place
# (either the build directory or the source dir, if build_ext -i was
# used)
#

# get the current directory from __file__
testdir = os.path.dirname(__file__)
pygrdir = os.path.abspath(os.path.join(testdir, '..'))

# now put pygr's top-level & build directories in the path
sys.path.insert(0, pygrdir)

os_info = distutils.util.get_platform()
ver = ".".join(platform.python_version_tuple()[:2])

build_dir = 'build/lib.%s-%s/' % (os_info, ver,)
pygr_build_dir = os.path.abspath(os.path.join(pygrdir, build_dir))
sys.path.insert(0, pygr_build_dir)

import pygr

assert pygr.__file__.startswith(pygrdir), \
       'imported pygr from Bad Place: %s' % (pygr.__file__)

try:
    import pygr.cnestedlist
except ImportError:
    print """
    ERROR: cannot import pygr.cnestedlist; did you run python setup.py build or
    setup.py build_ext -i?
    """
    sys.exit(-1)

#########

#
# enable hooks for code coverage across multiple processes
#

# only enable figleaf code coverage if it's already running OR
# environment variable is set (passed from master protest.py process)

record_code_coverage = False
try:
    import figleaf
    if figleaf.get_trace_obj():
        record_code_coverage = True
    elif os.environ.get('_PYGRTEST_FIGLEAF_ON'):
        record_code_coverage = True
except ImportError:
    pass

if record_code_coverage:
    import atexit

    figleaf.start()
    os.environ['_PYGRTEST_FIGLEAF_ON'] = 'yes'

    def save_figleaf_info():
        figleaf.stop()
        figleaf.write_coverage('.figleaf')

    atexit.register(save_figleaf_info)
