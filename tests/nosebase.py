import os
from nose.tools import *


class TempDir(object):
    'temporary directory that is automatically deleted when object is released'
    def __init__(self):
        import tempfile
        self.path = tempfile.mkdtemp()
    def __str__(self):
        return self.path
    def __del__(self):
        'recursively delete the temp dir and its subdirs'
        if self.path is not None:
            from shutil import rmtree
            rmtree(self.path)
            self.path = None
    def subfile(self,name):
        'return full path by appending name to temp dir path'
        return os.path.join(self.path,name)
    def copyFile(self,path):
        'copy file into the temp dir and return its new path'
        filename = self.subfile(os.path.basename(path))
        from shutil import copyfile
        copyfile(path,filename)
        return filename

def get_pygr_data_path(newpath=''):
    'force pygr.Data to use newpath, without side-effects on environment'
    import pygr.Data
    pygr.Data.pygrDataPath = newpath
    reload(pygr.Data)
    del pygr.Data.pygrDataPath
    return pygr.Data

class TempPygrData(TempDir):
    'restrict pygr.Data to an initially empty temp directory'
    def __init__(self):
        TempDir.__init__(self)
        self.force_reload(str(self))
    def force_reload(self,newpath=None):
        if newpath is None:
            newpath = self.pygrdatapath
        else:
            self.pygrdatapath = newpath
        return get_pygr_data_path(newpath)
    def __del__(self):
        get_pygr_data_path(None)
        TempDir.__del__(self)

class TempPygrDataMySQL(TempPygrData):
    'restrict pygr.Data to an initially empty MySQL resource database'
    def __init__(self,dbname='test',args=''):
        TempDir.__init__(self) # GENERATE A TEMPORARY TABLENAME
        import random
        l = [c for c in 'TeMpBiGdAcDy']
        random.shuffle(l)
        tablename = dbname+'.'+''.join(l)
        import pygr.Data
        db = pygr.Data.ResourceDBMySQL(tablename+args,createLayer='temp') # CREATE TABLE
        self.cursor = db.cursor
        self.tablename = tablename
        self.force_reload('mysql:'+tablename+args) # RELOAD PYGR.DATA USING NEW TABLE
    def __del__(self):
        'drop the temporary resource database table'
        TempDir.__del__(self)
        try:
            t = self.tablename
        except AttributeError: # APPARENTLY NO TABLE CREATED, SO NOTHING TO DO.
            pass
        else:
            import pygr.Data
            self.cursor.execute('drop table if exists %s' % self.tablename)
            self.cursor.execute('drop table if exists %s_schema' % self.tablename)
            try:
                del pygr.Data.getResource.layer['temp'] # REMOVE FROM LAYER INDEX
            except KeyError:
                pass
        get_pygr_data_path(None)


def skiptest():
    'cause nose to skip the current test case'
    import nose
    raise nose.SkipTest

def skip_errors(*skipErrors):
    'decorator will force skipping of tests on specified error types'
    def decorate(f):
        def new_f(*args,**kwargs):
            try:
                return f(*args,**kwargs)
            except skipErrors:
                skiptest()
        return new_f
    return decorate
    

class PygrDataTextFile(object):
    '''dict interface to a text file storage that is pygr.Data-smart,
    i.e. it uses pygr.Data.getResource.loads(), so data will be saved
    and loaded in terms of pygr.Data resource IDs, which will be loaded
    from pygr.Data in the usual way.  Intended for storing test results
    in a platform-independent text format.'''
    def __init__(self,path,mode='r'):
        'open in mode r, a or w'
        self.path = path
        self.mode = mode
        if mode=='r' or mode=='a':
            ifile = file(path)
            import pickle
            self.d = pickle.load(ifile)
            ifile.close()
        elif mode=='w':
            self.d = {}
        else:
            raise ValueError('unknown file mode %s.  Use r, w, or a.' % mode)
    def __getitem__(self,k):
        s = self.d[k]
        import pygr.Data
        return pygr.Data.getResource.loads(s)
    def __setitem__(self,k,obj):
        if self.mode=='r':
            raise ValueError('this PygrDataTextFile was opened read-only! Use append mode')
        import pygr.Data
        s = pygr.Data.getResource.dumps(obj)
        self.d[k] = s
        self.save()
    def __delitem__(self,k):
        if self.mode=='r':
            raise ValueError('this PygrDataTextFile was opened read-only! Use append mode')
        del self.d[k]
        self.save()
    def __iter__(self): return iter(self.d)
    def save(self):
        'save our dictionary to text file by pickling'
        if self.mode=='r':
            raise ValueError('this PygrDataTextFile was opened read-only! Use append mode')
        ifile = file(self.path,'w')
        import pickle
        pickle.dump(self.d,ifile)
        ifile.close()


def find_unused_port(port=5123):
    'look for an unused port begining at the specified port number.'
    import xmlrpclib,socket
    while port<9999:
        s = xmlrpclib.ServerProxy('http://localhost:%d' %port)
        try:
            s.listMethods()
            port += 1
        except socket.error:
            return port
    raise OSError('unable to find any open port')

class TestXMLRPCServer(object):
    """runs XMLRPC server in the background with a list of pygr.Data resources
    Makes server exit when this object is released.
    Because we want this to work even on Windows (gag! choke!),
    we can't use fork, backgrounding or any other quasi-sensible method for
    running the server process in the background.  So we just use a separate
    thread to keep our caller from blocking...
    Optional arguments:
    PYGRDATAPATH: passed to the server process command line as its PYGRDATAPATH
    checkResources: if True, first check that all pygrDataNames are loadable."""
    def __init__(self,*pygrDataNames,**kwargs):
        'starts server, returns without blocking'
        self.port = find_unused_port()
        import pygr.Data
        try:
            if kwargs['checkResources']:                
                for name in pygrDataNames: # ENSURE ALL RES FOR THE TEST ARE AVAILABLE
                    obj = pygr.Data.getResource(name)
        except KeyError:
            pass
        self.pygrDataNames = pygrDataNames
        try:
            self.pygrDataPath = kwargs['PYGRDATAPATH'] # USER-SPECIFIED PATH
        except KeyError:
            self.pygrDataPath = 'PYGRDATAPATH' # DEFAULT: JUST USE ENV AS USUAL
        try:
            self.downloadDB = 'downloadDB='+kwargs['downloadDB']
        except KeyError:
            self.downloadDB = ''
        from threading import Thread
        t = Thread(target=self.run_server)
        t.start()
        import time
        time.sleep(1) # WAIT TO MAKE SURE THE CHILD IS STARTED
    def run_server(self):
        'this method blocks, so run it in a separate thread'
        print 'starting server on port',self.port
        import sys
        os.system('%s pygrdata_server.py %d %s %s %s'
                  %(sys.executable,self.port,self.pygrDataPath,
                    self.downloadDB,' '.join(self.pygrDataNames)))
        print 'server exited.'
    def access_server(self):
        'force pygr.Data to only use the XMLRPC server'
        return get_pygr_data_path('http://localhost:%d' % self.port)
    def close(self):
        import xmlrpclib
        s = xmlrpclib.ServerProxy('http://localhost:%d' % self.port)
        s.exit_now() # TELL THE SERVER TO EXIT
        get_pygr_data_path(None) # FORCE IT TO RESTORE STANDARD PYGRDATAPATH



def approximate_cmp(x,y,delta):
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

class TestBase(object):
    '''base class for tests that can skip on setup errors.
       You can subclass the following attributes:

       Class attribute _skipSetupErrors gives tuple of
       setup error types that will cause the test to be skipped.

       Class attribute _testLevel, if provided, should be an
       integer indicating the intensity level of the test,
       starting from 0 (lowest).  This will be compared against
       the environment variable PYGR_TEST_LEVEL, and if greater,
       will force skipping of this test class.'''
    _skipSetupErrors = (KeyError,AttributeError,IOError)
    def setup(self):
        if not self.is_approved():
            skiptest()
        try:
            m = self.try_setup
        except AttributeError:
            return
        try:
            m()
        except self._skipSetupErrors:
            skiptest()
    def is_approved(self):
        'True if this test class is approved'
        try:
            level = self._testLevel
        except AttributeError:
            return True # NO LEVEL, SO NO APPROVAL REQUIRED
        import os
        try:
            approved = int(os.environ['PYGR_TEST_LEVEL'])
        except (KeyError,ValueError):
            approved = 0
        if level>approved:
            return False
        else:
            return True
        
##     def teardown(self):
##         try:
##             self.tear_me_down()
##         except KeyError:
##             skiptest()
    

