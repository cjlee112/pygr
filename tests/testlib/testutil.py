"""
Utility functions for testing
"""

import sys, os, shutil, unittest, random, warnings, threading, time, re
import tempfile as tempfile_mod
import atexit

import pathfix, logger

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

###

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

    # Fix for figleaf misbehaving. It is adding a logger at root level 
    # and that will add a handler to all subloggers (ours as well)
    # needs to be fixed in figleaf
    import logging
    root = logging.getLogger()
    # remove all root handlers
    for hand in root.handlers: 
        root.removeHandler(hand)

    if os.path.isdir(path):
        shutil.rmtree(path)       
    
    figleaf.start() 
    # execute the function itself
    func(*args, **kwds)
    figleaf.stop()
    
    logger.info('generating coverage')
    coverage = figleaf.get_data().gather_files()
    annotate_html.prepare_reportdir(path)
    
    # skip python modules and the test modules
    regpatt  = lambda patt: re.compile(patt, re.IGNORECASE)
    patterns = map(regpatt, [ 'python', 'tests' ])
    annotate_html.report_as_html(coverage, path, exclude_patterns=patterns,
                                 files_list='')

class TempDir(object):
    """
    Returns a directory in the temporary directory, either named or a 
    random one
    """

    def __init__(self, prefix, path='tempdir', reset=False):
        self.tempdir = path_join( pathfix.curr_dir, '..', path )
        
        # will remove the root directory of all temporary directories
        # removes content 
        if reset and os.path.isdir(self.tempdir):
            logger.info('resetting path %s' % self.tempdir)
            shutil.rmtree(self.tempdir, ignore_errors=True)

        if not os.path.isdir(self.tempdir):
            os.mkdir(self.tempdir)
        
        self.path = tempfile_mod.mkdtemp(prefix=prefix, dir=self.tempdir)
        atexit.register(self.remove)

    def randname(self, prefix='x', size=56):
        "Generates a random name"
        id = prefix + str(random.getrandbits(size))
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
    def __init__(self,*pygrDataNames,**kwargs):
        'starts server, returns without blocking'
        import pygr.Data
        
        # point it to a temporary directory
        tempdir = TempDir('pygrdata').path
        self.port = kwargs.get('port', 83756)

        # check that all resources are available
        if kwargs.get('checkResources'):
            map(pygr.Data.getResource, *pygrDataNames)

        self.pygrDataNames = pygrDataNames
        
        # user specified or default values
        self.pygrDataPath = kwargs.get('PYGRDATAPATH', tempdir)

        self.downloadDB = '%s' % kwargs.get('downloadDB', '')
        
        # create temporary directory for its logs
        currdir = os.path.dirname(__file__)
        self.server_script = path_join(currdir, 'pygrdata_server.py')

        self.outname = path_join(tempdir, 'xmlrcp-out.txt')
        self.errname = path_join(tempdir, 'xmlrcp-err.txt')
    
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
        

        cmd = '%s %s %s' % \
              (sys.executable, self.server_script, flags)
        logger.debug('Starting XML-RPC server: ')
        logger.debug(cmd)

        try:
            os.system(cmd)
        finally:
            pass

        logger.debug('server stopped')
    
    def access_server(self):
        'force pygr.Data to only use the XMLRPC server'
        pass
        
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

DATADIR = path_join(pathfix.curr_dir, '..', 'data')
TEMPDIR = TempDir('tempdata').path

# shortcuts for creating full paths to files in the data and temporary
# directories
datafile = lambda name: path_join(DATADIR, name)
def tempdatafile(name, errorIfExists=True):
    filepath = path_join(TEMPDIR, name)
    if errorIfExists and os.path.exists(filepath):
        raise AssertionError('tempdatafile %s already exists!' % name)
    return filepath

if __name__ == '__main__':
    TempDir(reset=True)
    TestXMLRPCServer()
