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
        for dirpath,subdirs,files in os.walk(self.path):
            for name in files: # DELETE ALL FILES IN dirpath
                os.remove(os.path.join(dirpath,name))
            os.rmdir(dirpath) # FINALLY DELETE dirpath DIRECTORY
    def subfile(self,name):
        'return full path by appending name to temp dir path'
        return os.path.join(self.path,name)
    def copyFile(self,path):
        'copy file into the temp dir and return its new path'
        infile = file(path)
        filename = self.subfile(os.path.basename(path))
        outfile = file(filename,'w')
        outfile.write(infile.read())
        infile.close()
        outfile.close()
        return filename

class TempPygrData(TempDir):
    'restrict pygr.Data to an initially empty temp directory'
    def __init__(self):
        TempDir.__init__(self)
        os.environ['PYGRDATAPATH'] = str(self)
        self.force_reload()
    def force_reload(self):
        import pygr.Data
        reload(pygr.Data) # IN CASE IT WAS PREVIOUSLY IMPORTED
        return pygr.Data # HAND BACK THE CURRENT VERSION

class TempPygrDataMySQL(TempPygrData):
    'restrict pygr.Data to an initially empty MySQL resource database'
    def __init__(self,dbname='test',args=''):
        TempDir.__init__(self) # GENERATE A TEMPORARY TABLENAME
        import random
        l = [c for c in 'TeMpBiGdAcDy']
        random.shuffle(l)
        tablename = dbname+'.'+''.join(l)
        import pygr.Data
        pygr.Data.ResourceDBMySQL(tablename+args,createLayer='temp') # CREATE TABLE
        self.tablename = tablename
        os.environ['PYGRDATAPATH'] = 'mysql:'+tablename+args
        self.force_reload() # RELOAD PYGR.DATA USING NEW TABLE
    def __del__(self):
        'drop the temporary resource database table'
        TempDir.__del__(self)
        try:
            t = self.tablename
        except AttributeError: # APPARENTLY NO TABLE CREATED, SO NOTHING TO DO.
            return
        import pygr.Data
        cursor = pygr.Data.getResource.db[0].cursor
        cursor.execute('drop table if exists %s' % self.tablename)
        cursor.execute('drop table if exists %s_schema' % self.tablename)
        try:
            del pygr.Data.getResource.layer['temp'] # REMOVE FROM LAYER INDEX
        except KeyError:
            pass


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
    

