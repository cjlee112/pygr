

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
    try:
        file(path).close() # WILL RAISE IOError IF path NOT ACCESSIBLE, READABLE
    except IOError:
        try: # CONVERT TO ABSOLUTE PATH BASED ON SAVED DIRECTORY PATH
            import os
            path = os.path.normpath(os.path.join(kwargs['curdir'],path))
            file(path).close() # WILL RAISE IOError IF path NOT ACCESSIBLE, READABLE
        except KeyError:
            raise IOError('unable to open file %s' % path)
    return cls(path)
filename_unpickler.__safe_for_unpickling__ = 1

class SourceFileName(str):
    '''store a filepath string, raise IOError on unpickling
if filepath not readable, and complain if the user tries
to pickle a relative path'''
    def __reduce__(self):
        import os,sys
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
    import os
    dirname = os.path.dirname(filename)
    if dirname=='':
        return os.curdir
    else:
        return dirname

def default_tmp_path():
    'find out default location for temp files, e.g. /tmp'
    import os
    for tmp in ['/tmp','/usr/tmp']: # RETURN THE 1ST WRITABLE LOCATION
        if os.access(tmp,os.W_OK):
            return tmp
    return os.path.dirname(os.tempnam()) # GRR. ASK PYTHON WHERE tmp IS...

def report_exception():
    'print string message from exception to stderr'
    import sys,traceback
    info = sys.exc_info()[:2]
    l = traceback.format_exception_only(info[0],info[1])
    print >>sys.stderr,'Warning: caught %s\nContinuing...' % l[0]

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
        import sys
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
                       attrDict=None):
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
        subclass_init()
    shadowClass.__name__ = targetClass.__name__ + '_' + subname
    setattr(obj,classattr,shadowClass) # SHADOW CLASS REPLACES ORIGINAL
    return shadowClass

def methodFactory(methodList,methodStr,localDict):
    for methodName in methodList:
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
                import sys
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
        import os
        self.origDir = os.getcwd()
    def __str__(self):
        import os
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
    import os
    try:
        return os.environ[envname] # USER-SPECIFIED DIRECTORY
    except KeyError:
        return os.getcwd() # DEFAULT: SAVE IN CURRENT DIRECTORY
