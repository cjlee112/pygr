"""
Utility functions for testing
"""

import sys, os, shutil, unittest, random, warnings, threading, time, re, md5, glob
import tempfile as tempfile_mod
import atexit

import pathfix
from pygr import logger

# a list that keeps track of the messages
# generated when skipping tests
SKIP_MESSAGES = []

# represents a test data
class TestData(object):
    pass

# a shortcut
path_join = pathfix.path_join

# use the main logger to produce 
info, error, warn, debug = logger.info, logger.error, logger.warn, logger.debug

# global port setting
default_xmlrpc_port = 89324              # should be set by test runner

###

def approximate_cmp(x, y, delta):
    '''expects two lists of tuples.  Performs comparison as usual,
    except that numeric types are considered equal if they differ by
    less than delta'''
    diff = cmp(len(x),len(y))
    if diff != 0:
        return diff
    x.sort() # SORT TO ENSURE IN SAME ORDER...
    y.sort()
    for i in range(len(x)):
        s = x[i]
        t = y[i]
        diff = cmp(len(s),len(t))
        if diff != 0:
            return diff
        for j in range(len(s)):
            u = s[j]
            v = t[j]
            if isinstance(u,int) or isinstance(u,float):
                diff = u - v
                if diff < -delta:
                    return -1
                elif diff >delta:
                    return 1
            else:
                diff = cmp(u,v)
                if diff != 0:
                    return diff
    return 0

def stop(text):
    "Unrecoverable error"
    logger.error (text)
    sys.exit()

def change_pygrdatapath(*args):
    "Overwrites the PYGRDATAPATH enviroment variable (local copy)"
    path = path_join(*args)
    if not os.path.isdir(path):
        stop('cannot access pygrdatapath %s' % path)
    os.environ['PYGRDATAPATH'] = path
    os.environ['PYGRDATADOWNLOAD'] = path
    import pygr.Data

def generate_coverage(func, path, *args, **kwds):
    """
    Generates code coverage for the function 
    and places the results in the path
    """
    import figleaf
    from figleaf import annotate_html

    if os.path.isdir(path):
        shutil.rmtree(path)       
    
    # execute the function itself
    return_vals = func(*args, **kwds)
    
    logger.info('generating coverage')
    coverage = figleaf.get_data().gather_files()
    annotate_html.prepare_reportdir(path)
    
    # skip python modules and the test modules
    regpatt  = lambda patt: re.compile(patt, re.IGNORECASE)
    patterns = map(regpatt, [ 'python', 'tests' ])
    annotate_html.report_as_html(coverage, path, exclude_patterns=patterns,
                                 files_list='')

    return return_vals

class TempDir(object):
    """
    Returns a directory in the temporary directory, either named or a 
    random one
    """

    def __init__(self, prefix, path='tempdir'):
        self.prefix = prefix
        self.tempdir = path_join( pathfix.curr_dir, '..', path )
        self.path = self.get_path()
        atexit.register(self.remove)

    def reset(self):
        "Resets the root temporary directory"
       
        logger.debug('resetting path %s' % self.tempdir)
        shutil.rmtree(self.path, ignore_errors=True)
        shutil.rmtree(self.tempdir, ignore_errors=True)
        self.path = self.get_path()

    def get_path(self):
        if not os.path.isdir(self.tempdir):
            os.mkdir(self.tempdir)
        path = tempfile_mod.mkdtemp(prefix=self.prefix, dir=self.tempdir)
        return path

    def randname(self, prefix='x'):
        "Generates a random name"
        id = prefix + str(random.randint(0, 2**31))
        return id

    def subfile(self, name=None):
        """
        Returns a path to a file in the temporary directory, 
        either the named or a random one
        """
        name = name or self.randname(prefix='f')
        return path_join(self.path, name)

    def remove(self):
        "Removes the temporary directory"
        #shutil.rmtree(self.path, ignore_errors=True)
        pass

class TestXMLRPCServer(object):
    """
    Runs XMLRPC server in the background with a list of pygr.Data resources
    Makes server exit when this object is released. Because we want this to 
    work even on Windows, we can't use fork, backgrounding or any other 
    quasi-sensible method for running the server process in the background.  
    So we just use a separate thread to keep our caller from blocking...

    Optional arguments:
    PYGRDATAPATH: passed to the server process command line as its PYGRDATAPATH
    checkResources: if True, first check that all pygrDataNames are loadable.
    """
    def __init__(self, pygrDataNames, pygrDataPath, port=None, downloadDB=''):
        'starts server, returns without blocking'
        self.pygrDataNames = pygrDataNames
        self.pygrDataPath = pygrDataPath
        self.downloadDB = downloadDB

        global default_xmlrpc_port
        if port is None:
            assert default_xmlrpc_port
            self.port = default_xmlrpc_port
        else:
            self.port = port

        # check that all resources are available
        ## if kwargs.get('checkResources'):
        ##     map(pygr.Data.getResource, *pygrDataNames)

        currdir = os.path.dirname(__file__)
        self.server_script = path_join(currdir, 'pygrdata_server.py')
        # create temporary directory for its logs
        tempdir = TempDir('pygrdata').path
        self.outname = path_join(tempdir, 'xmlrpc-out.txt')
        self.errname = path_join(tempdir, 'xmlrpc-err.txt')
    
        # start the tread
        thread = threading.Thread(target=self.run_server)
        thread.start()
        
        # wait for it to start for 
        time.sleep(1) 

    def run_server(self):
        'this method blocks, so run it in a separate thread'
        logger.debug('starting server on port %s', self.port)

        params = dict(
            port=self.port, 
            downloadDB=self.downloadDB, 
            pygrdatapath=self.pygrDataPath,
            resources = ':'.join(self.pygrDataNames),
            incoming_flags = " ".join(sys.argv)
       )

        flags = """%(incoming_flags)s --port=%(port)s \
        --pygrdatapath=%(pygrdatapath)s \
        --downloadDB=%(downloadDB)s --resources=%(resources)s""" % params

        flags = ' '.join(flags.split() )
        # CTB -- warning, these could fail when passed to the os.system
        # without quoting, IF weird characters are present in TMP or TMPDIR.
        

        cmd = '%s %s %s > %s 2> %s' % \
              (sys.executable, self.server_script, flags,
               self.outname, self.errname)
        logger.debug('Starting XML-RPC server: ')
        logger.debug(cmd)

        try:
            os.system(cmd)
        finally:
            output = open(self.outname).read()
            errout = open(self.errname).read()

            logger.debug('XML-RPC server output: %s' % output)
            logger.debug('XML-RPC server error out: %s' % errout)

        logger.debug('server stopped')
    
    def close(self):
        import xmlrpclib
        s = xmlrpclib.ServerProxy('http://localhost:%d' % self.port)
        s.exit_now() # TELL THE SERVER TO EXIT

def make_suite(tests):
    "Makes a test suite from a list of TestCase classes"
    loader = unittest.TestLoader().loadTestsFromTestCase
    suites = map(loader, tests)
    return unittest.TestSuite(suites)

def mysql_enabled():
    """
    Detects wether mysql is functional on the current system
    """
    global SKIP_MESSAGES

    try:
        import MySQLdb
    except ImportError, exc:
        msg = 'MySQLdb error: %s' % exc
        SKIP_MESSAGES.append(msg)
        warn(msg)
        return False
    try:
        from pygr import sqlgraph
        tempcurs = sqlgraph.getNameCursor()[1]
        # disable some MySQL specific spurious warnings, current scope only
        warnings.simplefilter("ignore") 
        tempcurs.execute('create database if not exists test')
    except Exception, exc:
        msg = 'cannot operate on MySql database: %s' % exc
        SKIP_MESSAGES.append(msg)
        warn(msg)
        return False

    return True


def sqlite_enabled():
    """
    Detects whether sqlite3 is functional on the current system
    """
    global SKIP_MESSAGES
    from pygr.sqlgraph import import_sqlite
    try:
        sqlite = import_sqlite() # from 2.5+ stdlib, or pysqlite2
    except ImportError, exc:
        msg = 'sqlite3 error: %s' % exc
        SKIP_MESSAGES.append(msg)
        warn(msg)
        return False
    return True


class SQLite_Mixin(object):
    'use this as a base for any test'
    def setUp(self):
        from pygr.sqlgraph import import_sqlite
        sqlite = import_sqlite() # from 2.5+ stdlib, or external module
        self.sqlite_file = tempdatafile('test_sqlite.db', False)
        self.tearDown(False) # delete the file if it exists
        self.sqlite_db = sqlite.connect(self.sqlite_file)
        self.cursor = self.sqlite_db.cursor()
        self.sqlite_load() # load data provided by subclass method
    def tearDown(self, closeConnection=True):
        'delete the sqlite db file after (optionally) closing connection'
        if closeConnection:
            self.cursor.close() # close the cursor
            self.sqlite_db.close() # close the connection
        try:
            os.remove(self.sqlite_file)
        except OSError:
            pass

def temp_table_name(dbname='test'):
    import random
    l = [c for c in 'TeMpBiGdAcDy']
    random.shuffle(l)
    return dbname+'.'+''.join(l)

def drop_tables(cursor, tablename):
    cursor.execute('drop table if exists %s' % tablename)
    cursor.execute('drop table if exists %s_schema' % tablename)
                
def blast_enabled():
    """
    Detects whether the blast suite is functional on the current system
    """
    global SKIP_MESSAGES

    try:
        pass
    except ImportError, exc:
        msg = 'blast utilities not enabled: %s' % exc
        SKIP_MESSAGES.append(msg)
        warn(msg)
        return False

    return True

###

DATADIR  = path_join(pathfix.curr_dir, '..', 'data')
TEMPROOT = TempDir('tempdir')
TEMPDIR  = TEMPROOT.path

# shortcuts for creating full paths to files in the data and temporary
# directories
datafile = lambda name: path_join(DATADIR, name)

def tempdatafile(name, errorIfExists=True, copyData=False):
    filepath = path_join(TEMPDIR, name)
    if errorIfExists and os.path.exists(filepath):
        raise AssertionError('tempdatafile %s already exists!' % name)
    if copyData: # copy data file to new location
        shutil.copyfile(datafile(name), filepath)
    return filepath

def remove_files( path, patterns=[ "*.seqlen" ]):
    "Removes files matching any pattern in the list"
    for patt in patterns:
        fullpatt = path_join(path, patt)
        for name in glob.glob( fullpatt ):
            os.remove(name)

def get_file_md5(fpath):
    ifile = file(fpath, 'rb')
    try:
        h = md5.md5(ifile.read())
    finally:
        ifile.close()
    return h

if __name__ == '__main__':
    t = TempDir('tempdir')
    t.reset()

    #TestXMLRPCServer()
