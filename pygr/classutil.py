import os
import sys
import tempfile
from weakref import WeakValueDictionary
import dbfile
import logger


class FilePopenBase(object):
    '''Base class for subprocess.Popen-like class interface that
can be supported on Python 2.3 (without subprocess).  The main goal
is to avoid the pitfalls of Popen.communicate(), which cannot handle
more than a small amount of data, and to avoid the possibility of deadlocks
and the issue of threading, by using temporary files'''

    def __init__(self, args, bufsize=0, executable=None,
                 stdin=None, stdout=None, stderr=None, *largs, **kwargs):
        '''Mimics the interface of subprocess.Popen() with two additions:
- stdinFlag, if passed, gives a flag to add the stdin filename directly
to the command line (rather than passing it by redirecting stdin).
example: stdinFlag="-i" will add the following to the commandline:
-i /path/to/the/file
If set to None, the stdin filename is still appended to the commandline,
but without a preceding flag argument.

-stdoutFlag: exactly the same thing, except for the stdout filename.
'''
        self.stdin, self._close_stdin = self._get_pipe_file(stdin, 'stdin')
        self.stdout, self._close_stdout = self._get_pipe_file(stdout, 'stdout')
        self.stderr, self._close_stderr = self._get_pipe_file(stderr, 'stderr')
        kwargs = kwargs.copy() # get a copy we can change
        try: # add as a file argument
            stdinFlag = kwargs['stdinFlag']
            if stdinFlag:
                args.append(stdinFlag)
            args.append(self._stdin_path)
            del kwargs['stdinFlag']
            stdin = None
        except KeyError: # just make it read this stream
            stdin = self.stdin
        try: # add as a file argument
            stdoutFlag = kwargs['stdoutFlag']
            if stdoutFlag:
                args.append(stdoutFlag)
            args.append(self._stdout_path)
            del kwargs['stdoutFlag']
            stdout = None
        except KeyError: # make it write to this stream
            stdout = self.stdout
        self.args = (args, bufsize, executable, stdin, stdout,
                     self.stderr) + largs
        self.kwargs = kwargs

    def _get_pipe_file(self, ifile, attr):
        'create a temp filename instead of a PIPE; save the filename'
        if ifile == PIPE: # use temp file instead!
            fd, path = tempfile.mkstemp()
            setattr(self, '_' + attr + '_path', path)
            return os.fdopen(fd, 'w+b'), True
        elif ifile is not None:
            setattr(self, '_' + attr + '_path', ifile.name)
        return ifile, False

    def _close_file(self, attr):
        'close and delete this temp file if still open'
        if getattr(self, '_close_' + attr):
            getattr(self, attr).close()
            setattr(self, '_close_' + attr, False)
            os.remove(getattr(self, '_' + attr + '_path'))

    def _rewind_for_reading(self, ifile):
        if ifile is not None:
            ifile.flush()
            ifile.seek(0)

    def close(self):
        """Close any open temp (PIPE) files. """
        self._close_file('stdin')
        self._close_file('stdout')
        self._close_file('stderr')

    def __del__(self):
        self.close()


def call_subprocess(*popenargs, **kwargs):
    'portable interface to subprocess.call(), even if subprocess not available'
    p = FilePopen(*popenargs, **kwargs)
    return p.wait()

try:
    import subprocess
    PIPE = subprocess.PIPE

    class FilePopen(FilePopenBase):
        'this subclass uses the subprocess module Popen() functionality'

        def wait(self):
            self._rewind_for_reading(self.stdin)
            p = subprocess.Popen(*self.args, **self.kwargs)
            p.wait()
            self._close_file('stdin')
            self._rewind_for_reading(self.stdout)
            self._rewind_for_reading(self.stderr)
            return p.returncode

except ImportError:
    CSH_REDIRECT = False # SH style redirection is default
    import platform
    if platform.system() == 'Windows':

        def mkarg(arg):
            """Very basic quoting of arguments for Windows """
            return '"' + arg + '"'
    else: # UNIX
        from commands import mkarg
        try:
            if os.environ['SHELL'].endswith('csh'):
                CSH_REDIRECT = True
        except KeyError:
            pass

    badExecutableCode = None

    class FilePopen(FilePopenBase):
        'this subclass fakes subprocess.Popen.wait() using os.system()'

        def wait(self):
            self._rewind_for_reading(self.stdin)
            args = map(mkarg, self.args[0])
            if self.args[3]: # redirect stdin
                args += ['<', mkarg(self._stdin_path)]
            if self.args[4]: # redirect stdout
                args += ['>', mkarg(self._stdout_path)]
            cmd = ' '.join(args)
            if self.args[5]: # redirect stderr
                if CSH_REDIRECT:
                    cmd = '(%s) >& %s' % (cmd, mkarg(self._stderr_path))
                else:
                    cmd = cmd + ' 2> ' + mkarg(self._stderr_path)
            returncode = os.system(cmd)
            self._close_file('stdin')
            self._rewind_for_reading(self.stdout)
            self._rewind_for_reading(self.stderr)
            if badExecutableCode is not None and \
               badExecutableCode == returncode:
                raise OSError('no such command: %s' % str(self.args[0]))
            return returncode
    PIPE = id(FilePopen) # an arbitrary code for identifying this code

    # find out exit code for a bad executable name, silently
    badExecutableCode = call_subprocess(('aZfDqW9', ),
                                        stdout=PIPE, stderr=PIPE)


def ClassicUnpickler(cls, state):
    'standard python unpickling behavior'
    self = cls.__new__(cls)
    try:
        setstate = self.__setstate__
    except AttributeError: # JUST SAVE TO __dict__ AS USUAL
        self.__dict__.update(state)
    else:
        setstate(state)
    return self

ClassicUnpickler.__safe_for_unpickling__ = 1


def filename_unpickler(cls, path, kwargs):
    'raise IOError if path not readable'
    if not os.path.exists(path):
        try:# CONVERT TO ABSOLUTE PATH BASED ON SAVED DIRECTORY PATH
            path = os.path.normpath(os.path.join(kwargs['curdir'], path))
            if not os.path.exists(path):
                raise IOError('unable to open file %s' % path)
        except KeyError:
            raise IOError('unable to open file %s' % path)
    if cls is SourceFileName:
        return SourceFileName(path)
    raise ValueError('Attempt to unpickle untrusted class ' + cls.__name__)

filename_unpickler.__safe_for_unpickling__ = 1


class SourceFileName(str):
    '''store a filepath string, raise IOError on unpickling
if filepath not readable, and complain if the user tries
to pickle a relative path'''

    def __reduce__(self):
        if not os.path.isabs(str(self)):
            print >>sys.stderr, '''
WARNING: You are trying to pickle an object that has a local
file dependency stored only as a relative file path:
%s
This is not a good idea, because anyone working in
a different directory would be unable to unpickle this object,
since it would be unable to find the file using the relative path.
To avoid this problem, SourceFileName is saving the current
working directory path so that it can translate the relative
path to an absolute path.  In the future, please use absolute
paths when constructing objects that you intend to save to worldbase
or pickle!''' % str(self)
        return (filename_unpickler, (self.__class__, str(self),
                                    dict(curdir=os.getcwd())))


def file_dirpath(filename):
    'return path to directory containing filename'
    dirname = os.path.dirname(filename)
    if dirname == '':
        return os.curdir
    else:
        return dirname


def get_valid_path(*pathTuples):
    '''for each tuple in args, build path using os.path.join(),
    and return the first path that actually exists, or else None.'''
    for t in pathTuples:
        mypath = os.path.join(*t)
        if os.path.exists(mypath):
            return mypath


def search_dirs_for_file(filepath, pathlist=()):
    'return successful path based on trying pathlist locations'
    if os.path.exists(filepath):
        return filepath
    b = os.path.basename(filepath)
    for s in pathlist: # NOW TRY EACH DIRECTORY IN pathlist
        mypath = os.path.join(s, b)
        if os.path.exists(mypath):
            return mypath
    raise IOError('unable to open %s from any location in %s'
                  % (filepath, pathlist))


def report_exception():
    'print string message from exception to stderr'
    import traceback
    info = sys.exc_info()[:2]
    l = traceback.format_exception_only(info[0], info[1])
    print >>sys.stderr, 'Warning: caught %s\nContinuing...' % l[0]


def standard_invert(self):
    'keep a reference to an inverse mapping, using self._inverseClass'
    try:
        return self._inverse
    except AttributeError:
        self._inverse = self._inverseClass(self)
        return self._inverse


def lazy_create_invert(klass):
    """Create a function to replace __invert__ with a call to a cached object.

    lazy_create_invert defines a method that looks up self._inverseObj
    and, it it doesn't exist, creates it from 'klass' and then saves it.
    The resulting object is then returned as the inverse.  This allows
    for one-time lazy creation of a single object per parent class.
    """

    def invert_fn(self, klass=klass):
        try:
            return self._inverse
        except AttributeError:
            # does not exist yet; create & store.
            inverseObj = klass(self)
            self._inverse = inverseObj
            return inverseObj

    return invert_fn


def standard_getstate(self):
    'get dict of attributes to save, using self._pickleAttrs dictionary'
    d = {}
    for attr, arg in self._pickleAttrs.items():
        try:
            if isinstance(arg, str):
                d[arg] = getattr(self, attr)
            else:
                d[attr] = getattr(self, attr)
        except AttributeError:
            pass
    try:
        # DON'T SAVE itemClass IF SIMPLY A SHADOW of default itemClass
        # from __class__
        if not hasattr(self.__class__, 'itemClass') or \
           (self.itemClass is not self.__class__.itemClass and
            (not hasattr(self.itemClass, '_shadowParent') or
             self.itemClass._shadowParent is not self.__class__.itemClass)):
            try:
                d['itemClass'] = self.itemClass._shadowParent
            except AttributeError:
                d['itemClass'] = self.itemClass
        if not hasattr(self.__class__, 'itemSliceClass') or \
           (self.itemSliceClass is not self.__class__.itemSliceClass and
            (not hasattr(self.itemSliceClass, '_shadowParent') or
             self.itemSliceClass._shadowParent is not
             self.__class__.itemSliceClass)):
            try:
                d['itemSliceClass'] = self.itemSliceClass._shadowParent
            except AttributeError:
                d['itemSliceClass'] = self.itemSliceClass
    except AttributeError:
        pass
    try: # SAVE CUSTOM UNPACKING METHOD
        d['unpack_edge'] = self.__dict__['unpack_edge']
    except KeyError:
        pass
    return d


def standard_setstate(self, state):
    'apply dict of saved state by passing as kwargs to constructor'
    if isinstance(state, list):  # GET RID OF THIS BACKWARDS-COMPATIBILITY CODE
        self.__init__(*state)
        print >>sys.stderr, 'WARNING: obsolete list pickle %s. Update \
                by resaving!' % repr(self)
    else:
        state['unpicklingMode'] = True # SIGNAL THAT WE ARE UNPICKLING
        self.__init__(**state)


def apply_itemclass(self, state):
    try:
        self.itemClass = state['itemClass']
        self.itemSliceClass = state['itemSliceClass']
    except KeyError:
        pass


def generate_items(items):
    'generate o.id,o for o in items'
    for o in items:
        yield o.id, o


def item_unpickler(db, *args):
    'get an item or subslice of a database'
    obj = db
    for arg in args:
        obj = obj[arg]
    return obj
item_unpickler.__safe_for_unpickling__ = 1


def item_reducer(self): ############################# SUPPORT FOR PICKLING
    'pickle an item of a database just as a reference'
    return (item_unpickler, (self.db, self.id))


def shadow_reducer(self):
    'pickle shadow class instance using its true class'
    shadowClass = self.__class__
    trueClass = shadowClass._shadowParent # super() TOTALLY FAILED ME HERE!
    self.__class__ = trueClass # FORCE IT TO PICKLE USING trueClass
    keepDB = False
    if hasattr(shadowClass, 'db') and not hasattr(self, 'db'):
        keepDB = True
        self.__dict__['db'] = shadowClass.db # retain this attribute!!
    if hasattr(trueClass, '__reduce__'): # USE trueClass.__reduce__
        result = trueClass.__reduce__(self)
    elif hasattr(trueClass, '__getstate__'): # USE trueClass.__getstate__
        result = (ClassicUnpickler, (trueClass, self.__getstate__()))
    else: # PICKLE __dict__ AS USUAL PYTHON PRACTICE
        result = (ClassicUnpickler, (trueClass, self.__dict__))
    self.__class__ = shadowClass # RESTORE SHADOW CLASS
    if keepDB: # now we can drop the temporary db attribute we added
        del self.__dict__['db']
    return result


def get_bound_subclass(obj, classattr='__class__', subname=None, factories=(),
                       attrDict=None, subclassArgs=None):
    'create a subclass specifically for obj to bind its shadow attributes'
    targetClass = getattr(obj, classattr)
    try:
        if targetClass._shadowOwner is obj:
            return targetClass # already shadowed, so nothing to do
    except AttributeError: # not a shadow class, so just shadow it
        pass
    else: # someone else's shadow class, so shadow its parent
        targetClass = targetClass._shadowParent
    if subname is None: # get a name from worldbase ID
        try:
            subname = obj._persistent_id.split('.')[-1]
        except AttributeError:
            subname = '__generic__'

    class shadowClass(targetClass):
        __reduce__ = shadow_reducer
        _shadowParent = targetClass # NEED TO KNOW ORIGINAL CLASS
        _shadowOwner = obj # need to know who owns it
        if attrDict is not None: # add attributes to the class dictionary
            locals().update(attrDict)
        for f in factories:
            f(locals())

    if classattr == 'itemClass' or classattr == 'itemSliceClass':
        shadowClass.db = obj # the class needs to know its db object
    try: # run subclass initializer if present
        subclass_init = shadowClass._init_subclass
    except AttributeError: # no subclass initializer, so nothing to do
        pass
    else: # run the subclass initializer
        if subclassArgs is None:
            subclassArgs = {}
        subclass_init(**subclassArgs)
    shadowClass.__name__ = targetClass.__name__ + '_' + subname
    setattr(obj, classattr, shadowClass) # SHADOW CLASS REPLACES ORIGINAL
    return shadowClass


def method_not_implemented(*args, **kwargs):
    raise NotImplementedError


def read_only_error(*args, **kwargs):
    raise NotImplementedError("read only dict")


def methodFactory(methodList, methodStr, localDict):
    'save a method or exec expression for each name in methodList'
    for methodName in methodList:
        if callable(methodStr):
            localDict[methodName] = methodStr
        else:
            localDict[methodName] = eval(methodStr % methodName)


def open_shelve(filename, mode=None, writeback=False, allowReadOnly=False,
                useHash=False, verbose=True):
    '''Alternative to shelve.open with several benefits:
- uses bsddb btree by default instead of bsddb hash, which is very slow
  for large databases.  Will automatically fall back to using bsddb hash
  for existing hash-based shelve files.  Set useHash=True to force it to use
  bsddb hash.

- allowReadOnly=True will automatically suppress permissions errors so
  user can at least get read-only access to the desired shelve, if no write
  permission.

- mode=None first attempts to open file in read-only mode, but if the file
  does not exist, opens it in create mode.

- raises standard exceptions defined in dbfile: WrongFormatError,
  PermissionsError, ReadOnlyError, NoSuchFileError

- avoids generating bogus __del__ warnings as Python shelve.open() does.
  '''
    if mode=='r': # READ-ONLY MODE, RAISE EXCEPTION IF NOT FOUND
        return dbfile.shelve_open(filename, flag=mode, useHash=useHash)
    elif mode is None:
        try: # 1ST TRY READ-ONLY, BUT IF NOT FOUND CREATE AUTOMATICALLY
            return dbfile.shelve_open(filename, 'r', useHash=useHash)
        except dbfile.NoSuchFileError:
            mode = 'c' # CREATE NEW SHELVE FOR THE USER
    try: # CREATION / WRITING: FORCE IT TO WRITEBACK AT close() IF REQUESTED
        return dbfile.shelve_open(filename, flag=mode, writeback=writeback,
                                  useHash=useHash)
    except dbfile.ReadOnlyError:
        if allowReadOnly:
            d = dbfile.shelve_open(filename, flag='r', useHash=useHash)
            if verbose:
                logger.warn('''
Opening shelve file %s in read-only mode because you lack
write permissions to this file.  You will NOT be able to modify the contents
of this shelve dictionary.  To avoid seeing this warning message,
use verbose=False argument for the classutil.open_shelve() function.
''' % filename)
            return d
        else:
            raise


def get_shelve_or_dict(filename=None, dictClass=None, **kwargs):
    if filename is not None:
        if dictClass is not None:
            return dictClass(filename, **kwargs)
        else:
            from mapping import IntShelve
            return IntShelve(filename, **kwargs)
    return {}


class PathSaver(object):

    def __init__(self, origPath):
        self.origPath = origPath
        self.origDir = os.getcwd()

    def __str__(self):
        if os.access(self.origPath, os.R_OK):
            return self.origPath
        trypath = os.path.join(self.origDir, self.origPath)
        if os.access(trypath, os.R_OK):
            return trypath


def override_rich_cmp(localDict):
    'create rich comparison methods that just use __cmp__'
    mycmp = localDict['__cmp__']
    localDict['__lt__'] = lambda self, other: mycmp(self, other) < 0
    localDict['__le__'] = lambda self, other: mycmp(self, other) <= 0
    localDict['__eq__'] = lambda self, other: mycmp(self, other) == 0
    localDict['__ne__'] = lambda self, other: mycmp(self, other) != 0
    localDict['__gt__'] = lambda self, other: mycmp(self, other) > 0
    localDict['__ge__'] = lambda self, other: mycmp(self, other) >= 0


class DBAttributeDescr(object):
    'obtain an attribute from associated db object'

    def __init__(self, attr):
        self.attr = attr

    def __get__(self, obj, objtype):
        return getattr(obj.db, self.attr)


def get_env_or_cwd(envname):
    'get the specified environment value or path to current directory'
    try:
        return os.environ[envname] # USER-SPECIFIED DIRECTORY
    except KeyError:
        return os.getcwd() # DEFAULT: SAVE IN CURRENT DIRECTORY


class RecentValueDictionary(WeakValueDictionary):
    '''keep the most recent n references in a WeakValueDictionary.
    This combines the elegant cache behavior of a WeakValueDictionary
    (only keep an item in cache if the user is still using it),
    with the most common efficiency pattern: locality, i.e.
    references to a given thing tend to cluster in time.  Note that
    this works *even* if the user is not holding a reference to
    the item between requests for it.  Our Most Recent queue will
    hold a reference to it, keeping it in the WeakValueDictionary,
    until it is bumped by more recent requests.

    n: the maximum number of objects to keep in the Most Recent queue,
       default value 50.'''

    def __init__(self, n=None):
        WeakValueDictionary.__init__(self)
        if n<1: # user doesn't want any Most Recent value queue
            self.__class__ = WeakValueDictionary # revert to regular WVD
            return
        if isinstance(n, int):
            self.n = n # size limit
        else:
            self.n = 50
        self._head = self._tail = None
        self._keepDict = {} # most recent queue

    def __getitem__(self, k):
        v = WeakValueDictionary.__getitem__(self, k) # KeyError if not found
        self.keep_this(v)
        return v

    def _splice(self, previous, after):
        'link previous <--> after in queue, setting head & tail if needed'
        if previous is not None:
            self._keepDict[previous][1] = after
        if after is not None:
            self._keepDict[after][0] = previous
        elif previous is not None: # previous is end of queue!
            self._tail = previous
        if after is self._head:
            self._head = previous
            
    def keep_this(self, v):
        """add v as our most recent ref; drop oldest ref if over size limit.
        """
        if v is self._head:
            return # already at head of queue, so nothing to do
        try: # check if already in _keepDict
            previous, after = self._keepDict[v]
        except KeyError:
            self._keepDict[v] = [None, None]
        else: # remove from current position
            self._splice(previous, after)
            self._keepDict[v][0] = None
        self._splice(v, self._head) # place at head of queue
        if len(self._keepDict) > self.n: # delete oldest entry
            vdel = self._tail # get current tail
            self._splice(self._keepDict[vdel][0], None) # set new tail
            del self._keepDict[vdel]

    def __setitem__(self, k, v):
        WeakValueDictionary.__setitem__(self, k, v)
        self.keep_this(v)

    def clear(self):
        self._head = self._tail = None
        self._keepDict.clear()
        WeakValueDictionary.clear(self)

    def __repr__(self):
        return '<RecentValueDictionary object: %d members, cachesize %d>' %\
               (len(self._keepDict), self.n)


def make_attribute_interface(d):
    """
    If 'd' contains int values, use them to index tuples.

    If 'd' contains str values, use them to retrieve attributes from an obj.

    If d empty, use standard 'getattr'.
    """
    if len(d):
        v = d.values()[0]
        if isinstance(v, int):
            return AttrFromTuple(d)
        elif isinstance(v, str):
            return AttrFromObject(d)
        raise ValueError('dictionary values must be int or str!')

    return getattr


class AttrFromTuple(object):

    def __init__(self, attrDict):
        self.attrDict = attrDict

    def __call__(self, obj, attr, default=None):
        'getattr from tuple obj'
        try:
            return obj[self.attrDict[attr]]
        except (IndexError, KeyError):
            if default is not None:
                return default
        raise AttributeError("object has no attribute '%s'" % attr)


class AttrFromObject(AttrFromTuple):

    def __call__(self, obj, attr, default=None):
        'getattr with attribute name aliases'
        try:
            return getattr(obj, self.attrDict[attr])
        except KeyError:
            try:
                return getattr(obj, attr)
            except KeyError:
                if default is not None:
                    return default
        raise AttributeError("object has no attribute '%s'" % attr)


def kwargs_filter(kwargs, allowed):
    'return dictionary of kwargs filtered by list allowed'
    d = {}
    for arg in allowed:
        try:
            d[arg] = kwargs[arg]
        except KeyError:
            pass
    return d


def split_kwargs(kwargs, *targets):
    '''split kwargs into n+1 dicts for n targets; each target must
    be a list of arguments for that target'''
    kwargs = kwargs.copy()
    out = []
    for args in targets:
        d = {}
        for arg in args:
            try:
                d[arg] = kwargs[arg]
                del kwargs[arg]
            except KeyError:
                pass
        out.append(d)
    out.append(kwargs)
    return out
