
import pickle
from StringIO import StringIO
import shelve

class PygrPickler(pickle.Pickler):
    def persistent_id(self,obj):
        'convert objects with _persistent_id to PYGR_ID strings during pickling'
        import types
        try:
            if not isinstance(obj,types.TypeType) and obj is not self.root and obj._persistent_id is not None:
                return 'PYGR_ID:%s' % obj._persistent_id
        except AttributeError:
            pass
        return None
    def setRoot(self,obj):
        'set obj as root of pickling tree: genuinely pickle it (not just its id)'
        self.root=obj


class ResourceDBShelve(object):
    def __init__(self,dbpath,finder,mode='r'):
        import anydbm
        self.dbpath=dbpath
        self.finder=finder
        try: # OPEN DATABASE FOR READING
            self.db=shelve.open(dbpath,mode)
        except anydbm.error: # CREATE NEW FILE IF NEEDED
            self.db=shelve.open(dbpath,'c')
    def reopen(self,mode):
        self.db.close()
        self.db=shelve.open(self.dbpath,mode)
    def __getitem__(self,id):
        'get an item from this resource database'
        s=self.db[id] # RAISES KeyError IF NOT PRESENT
        return self.finder.loads(s) # RUN THE UNPICKLER ON THE STRING
    def __setitem__(self,id,obj):
        'add an object to this resource database'
        s=self.finder.dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        self.db[id]=s # SAVE TO OUR SHELVE FILE
        self.reopen('r') # REOPEN READ-ONLY
    def __delitem__(self,id):
        'delete this item from the database, with a modicum of safety'
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        missingKey=False
        try: 
            del self.db[id] # DELETE THE SPECIFIED RULE
        except KeyError:
            missingKey=True
        self.reopen('r') # REOPEN READ-ONLY
        if missingKey: # NOW IT'S SAFE TO RAISE THE EXCEPTION...
            raise KeyError('ID %s not found in %s' % (id,self.dbpath))
    def dir(self,prefix):
        'generate all item IDs starting with this prefix'
        for id in self.db:
            if id.startswith(prefix):
                yield id


class ResourceFinder(object):
    def __init__(self,separator=','):
        self.db=None
        self.layer={}
        self.dbstr=''
        self.d={}
        self.separator=separator
    def update(self):
        import os
        try:
            PYGRDATAPATH=os.environ['PYGRDATAPATH']
        except KeyError: # DEFAULT: HOME, CURRENT DIR, IN THAT ORDER
            PYGRDATAPATH=self.separator.join(['~','.'])
        if self.dbstr!=PYGRDATAPATH: # LOAD NEW RESOURCE PYGRDATAPATH
            self.dbstr=PYGRDATAPATH
            self.db=[]
            self.layer={}
            for dbpath in PYGRDATAPATH.split(self.separator):
                dbpath=os.path.join(dbpath,'.pygr_data')
                rdb=ResourceDBShelve(os.path.expanduser(dbpath),self)
                self.db.append(rdb)
                if dbpath[0]=='/' and 'system' not in self.layer:
                    self.layer['system']=rdb
                if dbpath[:2]=='~/' and 'my' not in self.layer:
                    self.layer['my']=rdb
                if dbpath[:2]=='./' and 'here' not in self.layer:
                    self.layer['here']=rdb
                if dbpath[:5]=='http:' and 'remote' not in self.layer:
                    self.layer['remote']=rdb
    def resourceDBiter(self):
        'iterate over all available databases, read from PYGRDATAPATH env var.'
        self.update()
        if self.db is None or len(self.db)==0:
            raise ValueError('empty PYGRDATAPATH! Please check environment variable.')
        for db in self.db:
            yield db
    def loads(self,data):
        'unpickle from string, using persistent ID expansion'
        src=StringIO(data)
        unpickler=pickle.Unpickler(src)
        unpickler.persistent_load=self.persistent_load # WE PROVIDE PERSISTENT LOOKUP
        return unpickler.load()
    def dumps(self,obj):
        'pickle to string, using persistent ID encoding'
        src=StringIO()
        pickler=PygrPickler(src) # NEED OUR OWN PICKLER, TO USE persistent_id
        pickler.setRoot(obj) # ROOT OF THE PICKLE TREE: SAVE EVEN IF persistent_id
        pickler.dump(obj) # PICKLE IT
        return src.getvalue() # RETURN THE PICKLED FORM AS A STRING
    def persistent_load(self,persid):
        'check for PYGR_ID:... format and return the requested object'
        if persid.startswith('PYGR_ID:'):
            return self(persid[8:]) # RUN OUR STANDARD RESOURCE REQUEST PROCESS
        else: # UNKNOWN PERSISTENT ID... NOT FROM PYGR!
            raise pickle.UnpicklingError, 'Invalid persistent ID %s' % persid
    def __call__(self,id,layer=None,*args,**kwargs):
        'get the requested resource ID by searching all databases'
        try:
            return self.d[id] # USE OUR CACHED OBJECT
        except KeyError:
            pass
        if layer is not None: # USE THE SPECIFIED LAYER
            obj=self.layer[layer][id]
        else: # SEARCH ALL OF OUR DATABASES
            obj=None
            for db in self.resourceDBiter():
                try:
                    obj=db[id] # TRY TO OBTAIN FROM THIS DATABASE
                    break # SUCCESS!  NOTHING MORE TO DO
                except KeyError:
                    pass
            if obj is None:
                raise KeyError('unable to find %s in PYGRDATAPATH' % id)
        obj._persistent_id=id  # MARK WITH ITS PERSISTENT ID
        self.d[id]=obj # SAVE TO OUR CACHE
        return obj
    def addResource(self,id,obj,layer=None):
        'save the object to the specified database layer as <id>'
        obj._persistent_id=id # MARK OBJECT WITH ITS PERSISTENT ID
        db=self.getLayer(layer)
        db[id]=obj # SAVE THE OBJECT TO THE DATABASE
        self.d[id]=obj # SAVE TO OUR CACHE
    def getLayer(self,layer):
        self.update() # MAKE SURE WE HAVE LOADED CURRENT DATABASE LIST
        if layer is not None:
            return self.layer[layer]
        else: # JUST USE OUR PRIMARY DATABASE
            return self.db[0]
    def deleteResource(self,id,layer=None):
        'delete the specified resource from the specified layer'
        db=self.getLayer(layer)
        del db[id]



################# CREATE AN INTERFACE TO THE RESOURCE DATABASE
getResource=ResourceFinder()

class ResourcePath(object):
    'simple way to read resource names as python foo.bar.bob expressions'
    def __init__(self,base,layer=None):
        self.__dict__['_path']=base # AVOID TRIGGERING setattr!
        self.__dict__['_layer']=layer
    def __getattr__(self,name):
        'extend the resource path by one more attribute'
        attr=ResourcePath(self._path+'.'+name,self._layer)
        # MUST NOT USE setattr BECAUSE WE OVERRIDE THIS BELOW!
        self.__dict__[name]=attr # CACHE THIS ATTRIBUTE ON THE OBJECT
        return attr
    def __setattr__(self,name,obj):
        'save obj using the specified resource name'
        id=self._path+'.'+name
        getResource.addResource(id,obj,self._layer)
    def __delattr__(self,name):
        try: # IF ACTUAL ATTRIBUTE EXISTS, JUST DELETE IT
            del self.__dict__[name]
        except KeyError: # TRY TO DELETE RESOURCE FROM THE DATABASE
            getResource.deleteResource(self._path+'.'+name,self._layer)
    def __call__(self,*args,**kwargs):
        'construct the requested resource'
        return getResource(self._path,layer=self._layer,*args,**kwargs)


class ResourceLayer(object):
    def __init__(self,layer):
        self._layer=layer
    def __getattr__(self,name):
        attr=ResourcePath(name,self._layer)
        setattr(self,name,attr) # CACHE THIS ATTRIBUTE ON THE OBJECT
        return attr

# PROVIDE TOP-LEVEL NAMES IN OUR RESOURCE HIERARCHY
Bio=ResourcePath('Bio')


# TOP-LEVEL NAMES FOR STANDARDIZED LAYERS
here=ResourceLayer('here')
my=ResourceLayer('my')
system=ResourceLayer('system')
remote=ResourceLayer('remote')
