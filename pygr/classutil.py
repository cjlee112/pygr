

def ClassicUnpickler(cls, state):
    self = cls.__new__(cls)
    self.__setstate__(state)
    return self
ClassicUnpickler.__safe_for_unpickling__ = 1


def filename_unpickler(cls,path,kwargs):
    'raise IOError if path not readable'
    try:
        file(path).close() # WILL RAISE IOError IF path NOT ACCESSIBLE, READABLE
    except IOError:
        try:
            import os
            path = os.path.join(kwargs['curdir'],path) # CONVERT TO ABSOLUTE PATH
            file(path).close() # WILL RAISE IOError IF path NOT ACCESSIBLE, READABLE
        except KeyError:
            raise IOError('unable to open file %s' % path)
    return cls(path)
filename_unpickler.__safe_for_unpickling__ = 1

class SourceFileName(str):
    'store a filepath string, raise IOError on unpickling if filepath not readable'
    def __reduce__(self):
        import os
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
    return os.path.dirname(os.tempnam())

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
    try:
        if not hasattr(self.__class__,'itemClass') or \
           self.itemClass is not self.__class__.itemClass:
            d['itemClass'] = self.itemClass
        if not hasattr(self.__class__,'itemSliceClass') or \
           self.itemSliceClass is not self.__class__.itemSliceClass:
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
        self.__init__(**state)

def apply_itemclass(self,state):
    try:
        self.itemClass = state['itemClass']
        self.itemSliceClass = state['itemSliceClass']
    except KeyError:
        pass


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

def methodFactory(methodList,methodStr,localDict):
    for methodName in methodList:
        localDict[methodName]=eval(methodStr%methodName)


def open_shelve(filename,mode=None,writeback=True):
    import shelve,anydbm
    if mode=='r': # READ-ONLY MODE, RAISE EXCEPTION IF NOT FOUND
        return shelve.open(filename,mode)
    elif mode is None:
        try: # 1ST TRY READ-ONLY, BUT IF NOT FOUND CREATE AUTOMATICALLY
            return shelve.open(filename,'r')
        except anydbm.error:
            mode='c' # CREATE NEW SHELVE FOR THE USER
    # CREATION / WRITING: FORCE IT TO WRITEBACK AT close()
    return shelve.open(filename,mode,writeback=writeback)


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
