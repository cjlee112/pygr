import os,sys
from weakref import WeakValueDictionary

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


def filename_unpickler(cls,path,kwargs):
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
            print >>sys.stderr,'''
WARNING: You are trying to pickle an object that has a local
file dependency stored only as a relative file path:
%s
This is not a good idea, because anyone working in
a different directory would be unable to unpickle this object,
since it would be unable to find the file using the relative path.
To avoid this problem, SourceFileName is saving the current
working directory path so that it can translate the relative
path to an absolute path.  In the future, please use absolute
paths when constructing objects that you intend to save to pygr.Data
or pickle!''' % str(self)
        return (filename_unpickler,(self.__class__,str(self),
                                    dict(curdir=os.getcwd())))

def file_dirpath(filename):
    'return path to directory containing filename'
    dirname = os.path.dirname(filename)
    if dirname=='':
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
        mypath = os.path.join(s,b)
        if os.path.exists(mypath):
            return mypath
    raise IOError('unable to open %s from any location in %s'
                  %(filepath,pathlist))

def default_tmp_path():
    'find out default location for temp files, e.g. /tmp'
    for tmp in ['/tmp','/usr/tmp']: # RETURN THE 1ST WRITABLE LOCATION
        if os.access(tmp,os.W_OK):
            return tmp
    return os.path.dirname(os.tempnam()) # GRR. ASK PYTHON WHERE tmp IS...

def report_exception():
    'print string message from exception to stderr'
    import traceback
    info = sys.exc_info()[:2]
    l = traceback.format_exception_only(info[0],info[1])
    print >>sys.stderr,'Warning: caught %s\nContinuing...' % l[0]

def standard_invert(self):
    'keep a reference to an inverse mapping, using self._inverseClass'
    try:
        return self._inverse
    except AttributeError:
        self._inverse = self._inverseClass(self)
        return self._inverse


def standard_getstate(self):
    'get dict of attributes to save, using self._pickleAttrs dictionary'
    d={}
    for attr,arg in self._pickleAttrs.items():
        try:
            if isinstance(arg,str):
                d[arg] = getattr(self,attr)
            else:
                d[attr] = getattr(self,attr)
        except AttributeError:
            pass
    try: # DON'T SAVE itemClass IF SIMPLY A SHADOW of default itemClass from __class__
        if not hasattr(self.__class__,'itemClass') or \
           (self.itemClass is not self.__class__.itemClass and 
            (not hasattr(self.itemClass,'_shadowParent') or
             self.itemClass._shadowParent is not self.__class__.itemClass)):
            try:
                d['itemClass'] = self.itemClass._shadowParent
            except AttributeError:
                d['itemClass'] = self.itemClass
        if not hasattr(self.__class__,'itemSliceClass') or \
           (self.itemSliceClass is not self.__class__.itemSliceClass and 
            (not hasattr(self.itemSliceClass,'_shadowParent') or
             self.itemSliceClass._shadowParent is not self.__class__.itemSliceClass)):
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


def standard_setstate(self,state):
    'apply dict of saved state by passing as kwargs to constructor'
    if isinstance(state,list):  # GET RID OF THIS BACKWARDS-COMPATIBILITY CODE!
        self.__init__(*state)
        print >>sys.stderr,'WARNING: obsolete list pickle %s. Update by resaving!' \
              % repr(self)
    else:
        state['unpicklingMode'] = True # SIGNAL THAT WE ARE UNPICKLING
        self.__init__(**state)

def apply_itemclass(self,state):
    try:
        self.itemClass = state['itemClass']
        self.itemSliceClass = state['itemSliceClass']
    except KeyError:
        pass

def generate_items(items):
    'generate o.id,o for o in items'
    for o in items:
        yield o.id,o

def item_unpickler(db,*args):
    'get an item or subslice of a database'
    obj = db
    for arg in args:
        obj = obj[arg]
    return obj
item_unpickler.__safe_for_unpickling__ = 1


def item_reducer(self): ############################# SUPPORT FOR PICKLING
    'pickle an item of a database just as a reference'
    return (item_unpickler, (self.db,self.id))

def shadow_reducer(self):
    'pickle shadow class instance using its true class'
    shadowClass = self.__class__
    trueClass = shadowClass._shadowParent # super() TOTALLY FAILED ME HERE!
    self.__class__ = trueClass # FORCE IT TO PICKLE USING trueClass
    if hasattr(trueClass,'__reduce__'): # USE trueClass.__reduce__
        result = trueClass.__reduce__(self)
    elif hasattr(trueClass,'__getstate__'): # USE trueClass.__getstate__
        result = (ClassicUnpickler,(trueClass,self.__getstate__()))
    else: # PICKLE __dict__ AS USUAL PYTHON PRACTICE
        result = (ClassicUnpickler,(trueClass,self.__dict__))
    self.__class__ = shadowClass # RESTORE SHADOW CLASS
    return result


def get_bound_subclass(obj, classattr='__class__', subname=None, factories=(),
                       attrDict=None, subclassArgs=None):
    'create a subclass specifically for obj to bind its shadow attributes'
    targetClass = getattr(obj,classattr)
    try:
        if targetClass._shadowOwner is obj:
            return targetClass # already shadowed, so nothing to do
    except AttributeError: # not a shadow class, so just shadow it
        pass
    else: # someone else's shadow class, so shadow its parent
        targetClass = targetClass._shadowParent
    if subname is None: # get a name from pygr.Data ID
        subname = obj._persistent_id.split('.')[-1]
    class shadowClass(targetClass):
        __reduce__ = shadow_reducer
        _shadowParent = targetClass # NEED TO KNOW ORIGINAL CLASS
        _shadowOwner = obj # need to know who owns it
        if attrDict is not None: # add attributes to the class dictionary
            locals().update(attrDict)
        for f in factories:
            f(locals())
    try: # run subclass initializer if present
        subclass_init = shadowClass._init_subclass
    except AttributeError: # no subclass initializer, so nothing to do
        pass
    else: # run the subclass initializer
        if subclassArgs is None:
            subclassArgs = {}
        subclass_init(**subclassArgs)
    shadowClass.__name__ = targetClass.__name__ + '_' + subname
    setattr(obj,classattr,shadowClass) # SHADOW CLASS REPLACES ORIGINAL
    return shadowClass

def method_not_implemented(*args,**kwargs):
    raise NotImplementedError
def read_only_error(*args, **kwargs):
    raise NotImplementedError("read only dict")

def methodFactory(methodList, methodStr, localDict):
    'save a method or exec expression for each name in methodList'
    for methodName in methodList:
        if callable(methodStr):
            localDict[methodName] = methodStr
        else:
            localDict[methodName]=eval(methodStr%methodName)

def open_shelve(filename,mode=None,writeback=False,allowReadOnly=False,
                useHash=False,verbose=True):
    '''Alternative to shelve.open with several benefits:
- uses bsddb btree by default instead of bsddb hash, which is very slow
  for large databases.  Will automatically fall back to using bsddb hash
  for existing hash-based shelve files.  Set useHash=True to force it to use bsddb hash.
      
- allowReadOnly=True will automatically suppress permissions errors so
  user can at least get read-only access to the desired shelve, if no write permission.

- mode=None first attempts to open file in read-only mode, but if the file
  does not exist, opens it in create mode.

- raises standard exceptions defined in dbfile: WrongFormatError, PermissionsError,
  ReadOnlyError, NoSuchFileError
  '''
    import dbfile
    if mode=='r': # READ-ONLY MODE, RAISE EXCEPTION IF NOT FOUND
        return dbfile.BtreeShelf(filename,mode,useHash=useHash)
    elif mode is None:
        try: # 1ST TRY READ-ONLY, BUT IF NOT FOUND CREATE AUTOMATICALLY
            return dbfile.BtreeShelf(filename,'r',useHash=useHash)
        except dbfile.NoSuchFileError:
            mode = 'c' # CREATE NEW SHELVE FOR THE USER
    try: # CREATION / WRITING: FORCE IT TO WRITEBACK AT close() IF REQUESTED
        return dbfile.BtreeShelf(filename,mode,writeback=writeback,useHash=useHash)
    except dbfile.ReadOnlyError:
        if allowReadOnly:
            d = dbfile.BtreeShelf(filename,'r',useHash=useHash)
            if verbose:
                print >>sys.stderr,'''Opening shelve file %s in read-only mode because you lack
write permissions to this file.  You will NOT be able to modify the contents
of this shelve dictionary.  To avoid seeing this warning message, use verbose=False
argument for the classutil.open_shelve() function.''' % filename
            return d
        else:
            raise


def get_shelve_or_dict(filename=None,dictClass=None,**kwargs):
    if filename is not None:
        if dictClass is not None:
            return dictClass(filename,**kwargs)
        else:
            from mapping import IntShelve
            return IntShelve(filename,**kwargs)
    return {}


class PathSaver(object):
    def __init__(self,origPath):
        self.origPath = origPath
        self.origDir = os.getcwd()
    def __str__(self):
        if os.access(self.origPath,os.R_OK):
            return self.origPath
        trypath = os.path.join(self.origDir,self.origPath)
        if os.access(trypath,os.R_OK):
            return trypath

def override_rich_cmp(localDict):
    'create rich comparison methods that just use __cmp__'
    mycmp = localDict['__cmp__']
    localDict['__lt__'] = lambda self,other: mycmp(self,other)<0
    localDict['__le__'] = lambda self,other: mycmp(self,other)<=0
    localDict['__eq__'] = lambda self,other: mycmp(self,other)==0
    localDict['__ne__'] = lambda self,other: mycmp(self,other)!=0
    localDict['__gt__'] = lambda self,other: mycmp(self,other)>0
    localDict['__ge__'] = lambda self,other: mycmp(self,other)>=0


class DBAttributeDescr(object):
    'obtain an attribute from associated db object'
    def __init__(self,attr):
        self.attr = attr
    def __get__(self,obj,objtype):
        return getattr(obj.db,self.attr)

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
        self.i = 0 # counter
        self._keepDict = {} # most recent queue
    def __getitem__(self, k):
        v = WeakValueDictionary.__getitem__(self, k) # KeyError if not found
        self.keep_this(v)
        return v
    def keep_this(self, v):
        'add v as our most recent ref; drop oldest ref if over size limit'
        self._keepDict[v] = self.i # mark as most recent request
        self.i += 1
        if len(self._keepDict)>self.n: # delete oldest entry
            l = self._keepDict.items()
            imin = l[0][1]
            vmin = l[0][0]
            for v,i in l[1:]:
                if i<imin:
                    imin = i
                    vmin = v
            del self._keepDict[vmin]
    def __setitem__(self, k, v):
        WeakValueDictionary.__setitem__(self, k, v)
        self.keep_this(v)
    def clear(self):
        self._keepDict.clear()
        WeakValueDictionary.clear(self)


            
