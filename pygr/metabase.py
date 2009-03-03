
import pickle,sys
from StringIO import StringIO
import shelve
from mapping import Collection,Mapping,Graph
from classutil import standard_invert,get_bound_subclass
from coordinator import XMLRPCServerBase

class OneTimeDescriptor(object):
    'provides shadow attribute based on schema'
    def __init__(self, attrName, mdb, **kwargs):
        self.attr=attrName
        self.mdb = mdb
    def __get__(self, obj, objtype):
        try:
            pygrID = obj._persistent_id # GET ITS RESOURCE ID
        except AttributeError:
            raise AttributeError('attempt to access pygr.Data attr on non-pygr.Data object')
        target = self.mdb.get_schema_attr(pygrID, self.attr) #get from mdb
        obj.__dict__[self.attr] = target # save in __dict__ to evade __setattr__
        return target

class ItemDescriptor(object):
    'provides shadow attribute for items in a db, based on schema'
    def __init__(self, attrName, mdb, invert=False, getEdges=False,
                 mapAttr=None, targetAttr=None, uniqueMapping=False, **kwargs):
        self.attr = attrName
        self.mdb = mdb
        self.invert = invert
        self.getEdges = getEdges
        self.mapAttr = mapAttr
        self.targetAttr = targetAttr
        self.uniqueMapping = uniqueMapping
    def get_target(self, obj):
        'return the mapping object for this schema relation'
        try:
            resID = obj.db._persistent_id # GET RESOURCE ID OF DATABASE
        except AttributeError:
            raise AttributeError('attempt to access pygr.Data attr on non-pygr.Data object')
        targetDict = self.mdb.get_schema_attr(resID, self.attr)
        if self.invert:
            targetDict = ~targetDict
        if self.getEdges:
            targetDict = targetDict.edges
        return targetDict
    def __get__(self, obj, objtype):
        targetDict = self.get_target(obj)
        if self.mapAttr is not None: # USE mapAttr TO GET ID FOR MAPPING obj
            obj_id = getattr(obj,self.mapAttr)
            if obj_id is None: # None MAPS TO None, SO RETURN IMMEDIATELY
                return None # DON'T BOTHER CACHING THIS
            result=targetDict[obj_id] # MAP USING THE SPECIFIED MAPPING
        else:
            result=targetDict[obj] # NOW PERFORM MAPPING IN THAT RESOURCE...
        if self.targetAttr is not None:
            result=getattr(result,self.targetAttr) # GET ATTRIBUTE OF THE result
        obj.__dict__[self.attr]=result # CACHE IN THE __dict__
        return result



class SchemaEdge(object):
    'provides unpack_edge method for schema graph storage'
    def __init__(self,schemaDB):
        self.schemaDB = schemaDB
    def __call__(self,edgeID):
        'get the actual schema object describing this ID'
        return self.schemaDB.getschema(edgeID)['-schemaEdge']



class ResourceDBGraphDescr(object):
    'this property provides graph interface to schema'
    def __get__(self,obj,objtype):
        g = Graph(filename=obj.dbpath+'_schema',mode='cw',writeNow=True,
                  simpleKeys=True,unpack_edge=SchemaEdge(obj))
        obj.graph = g
        return g

class ResourceDBShelve(object):
    '''BerkeleyDB-based storage of pygr.Data resource databases, using the python
    shelve module.  Users will not need to create instances of this class themselves,
    as pygr.Data automatically creates one for each appropriate entry in your
    PYGRDATAPATH; if the corresponding database file does not already exist, 
    it is automatically created for you.'''
    _pygr_data_version=(0,1,0)
    graph = ResourceDBGraphDescr() # INTERFACE TO SCHEMA GRAPH
    def __init__(self,dbpath,finder,mode='r'):
        import anydbm,os
        self.dbpath=os.path.join(dbpath,'.pygr_data') # CONSTRUCT FILENAME
        self.finder=finder
        try: # OPEN DATABASE FOR READING
            self.db=shelve.open(self.dbpath,mode)
            try:
                finder.save_root_names(self.db['0root'])
            except KeyError:
                pass
        except anydbm.error: # CREATE NEW FILE IF NEEDED
            self.db=shelve.open(self.dbpath,'c')
            self.db['0version']=self._pygr_data_version # SAVE VERSION STAMP
            self.db['0root']={}
    def reopen(self,mode):
        self.db.close()
        self.db=shelve.open(self.dbpath,mode)
    def find_resource(self,id,download=False):
        'get an item from this resource database'
        objdata = self.db[id] # RAISES KeyError IF NOT PRESENT
        try:
            return objdata, self.db['__doc__.'+id]['__doc__']
        except KeyError:
            return objdata, None
    def __setitem__(self,id,obj):
        'add an object to this resource database'
        s=self.finder.dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        try:
            self.db[id]=s # SAVE TO OUR SHELVE FILE
            self.db['__doc__.'+id]=getResource.get_info_dict(obj,s)
            root=id.split('.')[0] # SEE IF ROOT NAME IS IN THIS SHELVE
            d = self.db.get('0root',{})
            if root not in d:
                d[root]=None # ADD NEW ENTRY
                self.db['0root']=d # SAVE BACK TO SHELVE
        finally:
            self.reopen('r') # REOPEN READ-ONLY
    def __delitem__(self,id):
        'delete this item from the database, with a modicum of safety'
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        try:
            try:
                del self.db[id] # DELETE THE SPECIFIED RULE
            except KeyError:
                raise PygrDataNotFoundError('ID %s not found in %s' % (id,self.dbpath))
            try:
                del self.db['__doc__.'+id]
            except KeyError:
                pass
        finally:
            self.reopen('r') # REOPEN READ-ONLY
    def dir(self,prefix,asDict=False,download=False):
        'generate all item IDs starting with this prefix'
        l=[]
        for name in self.db:
            if name.startswith(prefix):
                l.append(name)
        if asDict:
            d={}
            for name in l:
                d[name] = self.db.get('__doc__.'+name,None)
            return d
        return l
    def setschema(self,id,attr,kwargs):
        'save a schema binding for id.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID=kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        d = self.db.get('SCHEMA.'+id,{})
        d[attr]=kwargs # SAVE THIS SCHEMA RULE
        self.db['SCHEMA.'+id]=d # FORCE shelve TO RESAVE BACK
        self.reopen('r')  # REOPEN READ-ONLY
    def getschema(self,id):
        'return dict of {attr:{args}}'
        return self.db['SCHEMA.'+id]
    def delschema(self,id,attr):
        'delete schema binding for id.attr'
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        d=self.db['SCHEMA.'+id]
        del d[attr]
        self.db['SCHEMA.'+id]=d # FORCE shelve TO RESAVE BACK
        self.reopen('r')  # REOPEN READ-ONLY





def dumps(obj, **kwargs):
    'pickle to string, using persistent ID encoding'
    src = StringIO()
    pickler = PygrPickler(src) # NEED OUR OWN PICKLER, TO USE persistent_id
    pickler.setRoot(obj, **kwargs) # ROOT OF PICKLE TREE: SAVE EVEN IF persistent_id
    pickler.dump(obj) # PICKLE IT
    return src.getvalue() # RETURN THE PICKLED FORM AS A STRING

def get_info_dict(obj, pickleString):
    'get dict of standard info about a resource'
    import os,datetime
    d = dict(creation_time=datetime.datetime.now(),
             pickle_size=len(pickleString),__doc__=obj.__doc__)
    try:
        d['user'] = os.environ['USER']
    except KeyError:
        d['user'] = None
    return d

class MetabaseBase(object):
    def persistent_load(self, persid):
        'check for PYGR_ID:... format and return the requested object'
        if persid.startswith('PYGR_ID:'):
            return self(persid[8:]) # RUN OUR STANDARD RESOURCE REQUEST PROCESS
        else: # UNKNOWN PERSISTENT ID... NOT FROM PYGR!
            raise pickle.UnpicklingError, 'Invalid persistent ID %s' % persid
    def load(self, pygrID, objdata, docstring):
        'load the pickled data and all its dependencies'
        obj = self.loads(objdata)
        obj.__doc__ = docstring
        if hasattr(obj,'_saveLocalBuild') and obj._saveLocalBuild:
            saver = self.downloadKeeper.saver # mdb in which to record local copy
            # SAVE AUTO BUILT RESOURCE TO LOCAL PYGR.DATA
            hasPending = saver.has_pending() # any pending transaction?
            saver.addResource(pygrID, obj) # add to queue for commit
            obj._saveLocalBuild = False # NO NEED TO SAVE THIS AGAIN
            if hasPending:
                print >>sys.stderr,'''Saving new resource %s to local pygr.Data...
You must use pygr.Data.save() to commit!
You are seeing this message because you appear to be in the
middle of a pygr.Data transaction.  Ordinarily pygr.Data would
automatically commit this new downloaded resource, but doing so
now would also commit your pending transaction, which you may
not be ready to do!''' % pygrID
            else: # automatically save new resource
                saver.save_pending() # commit it
        else: # NORMAL USAGE
            obj._persistent_id = pygrID  # MARK WITH ITS PERSISTENT ID
        self.loader[pygrID] = obj # SAVE TO OUR CACHE
        self.bind_schema(pygrID, obj) # BIND SHADOW ATTRIBUTES IF ANY
        return obj
    def loads(self, data):
        'unpickle from string, using persistent ID expansion'
        src = StringIO(data)
        unpickler = pickle.Unpickler(src)
        unpickler.persistent_load = self.persistent_load # WE PROVIDE PERSISTENT LOOKUP
        obj = unpickler.load() # ACTUALLY UNPICKLE THE DATA
        return obj
    def __call__(self, resID, debug=None, download=None, *args, **kwargs):
        'get the requested resource ID by searching all databases'
        try:
            return self.loader[resID] # USE OUR CACHED OBJECT
        except KeyError:
            pass
        debug_state = self.debug # SAVE ORIGINAL STATE
        download_state = self.download
        if debug is not None:
            self.debug = debug
        if download is not None: # apply the specified download mode
            self.download = download
        else: # just use our current download mode
            download = self.download
        try: # finally... TO RESTORE debug STATE EVEN IF EXCEPTION OCCURS.
            for objdata,docstr in self.find_resource(resID, download):
                try:
                    obj = self.load(resID, objdata, docstr) 
                    break
                except (KeyError,IOError): # NOT IN THIS DB, FILES NOT ACCESSIBLE...
                    if self.debug: # PASS ON THE ACTUAL ERROR IMMEDIATELY
                        raise
        finally: # RESTORE STATE BEFORE RAISING ANY EXCEPTION
            self.debug = debug_state
            self.download = download_state
        self.loader[resID] = obj # save to our cache
        return obj
    def bind_schema(self, resID, obj):
        'if this resource ID has any schema, bind its attrs to class'
        try:
            schema = self.getschema(resID)
        except KeyError:
            return # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO
        self.loader.schemaCache[resID] = schema # cache for speed
        for attr,rules in schema.items():
            if not attr.startswith('-'): # only bind real attributes
                self.bind_property(obj, attr, **rules)
    def bind_property(self, obj, attr, itemRule=False, **kwargs):
        'create a descriptor for the attr on the appropriate obj class'
        try: # SEE IF OBJECT TELLS US TO SKIP THIS ATTRIBUTE
            return obj._ignoreShadowAttr[attr] # IF PRESENT, NOTHING TO DO
        except (AttributeError,KeyError):
            pass # PROCEED AS NORMAL
        if itemRule: # SHOULD BIND TO ITEMS FROM obj DATABASE
            targetClass = get_bound_subclass(obj,'itemClass') # CLASS USED FOR CONSTRUCTING ITEMS
            descr = ItemDescriptor(attr, self, **kwargs)
        else: # SHOULD BIND DIRECTLY TO obj VIA ITS CLASS
            targetClass = get_bound_subclass(obj)
            descr = OneTimeDescriptor(attr, self, **kwargs)
        setattr(targetClass, attr, descr) # BIND descr TO targetClass.attr
        if itemRule:
            try: # BIND TO itemSliceClass TOO, IF IT EXISTS...
                targetClass = get_bound_subclass(obj,'itemSliceClass')
            except AttributeError:
                pass # NO itemSliceClass, SO SKIP
            else: # BIND TO itemSliceClass
                setattr(targetClass, attr, descr)
        if attr == 'inverseDB': # ADD SHADOW __invert__ TO ACCESS THIS
            addSpecialMethod(obj, '__invert__', getInverseDB)
    def get_schema_attr(self, resID, attr):
        'actually retrieve the desired schema attribute'
        try: # GET SCHEMA FROM CACHE
            schema = self.loader.schemaCache[resID]
        except KeyError: # HMM, IT SHOULD BE CACHED!
            schema = self.getschema(resID) # OBTAIN FROM RESOURCE DB
            self.loader.schemaCache[resID] = schema # KEEP IT IN OUR CACHE
        try:
            schema = schema[attr] # GET SCHEMA FOR THIS SPECIFIC ATTRIBUTE
        except KeyError:
            raise AttributeError('no pygr.Data schema info for %s.%s' \
                                 % (resID,attr))
        targetID = schema['targetID'] # GET THE RESOURCE ID
        return self(targetID) # actually load the resource



class Metabase(MetabaseBase):
    def __init__(self, dbpath, loader, layer=None):
        '''layer provides a mechanism for the caller to request information
        about what type of metabase this dbpath mapped to.  layer must
        be a dict'''
        if layer is None: # user doesn't want layer info
            layer = {} # save into a dummy dict
        if dbpath.startswith('http://'):
            rdb = ResourceDBClient(dbpath, self)
            if 'remote' not in layer:
                layer['remote'] = rdb
            self.__class__ = ReadOnlyMetabase
        elif dbpath.startswith('mysql:'):
            rdb = ResourceDBMySQL(dbpath[6:], self)
            if 'MySQL' not in self.layer:
                layer['MySQL'] = rdb
        else: # TREAT AS LOCAL FILEPATH
            dbpath = os.path.expanduser(dbpath)
            rdb = ResourceDBShelve(dbpath, self)
            if dbpath == os.path.expanduser('~') \
                   or dbpath.startswith(os.path.expanduser('~')+os.sep):
                if 'my' not in self.layer:
                    layer['my'] = rdb
            elif os.path.isabs(dbpath):
                if 'system' not in self.layer:
                    layer['system'] = rdb
            elif dbpath.split(os.sep)[0]==os.curdir:
                if 'here' not in self.layer:
                    layer['here'] = rdb
            elif 'subdir' not in self.layer:
                layer['subdir'] = rdb
        self.rdb = rdb
        self.init_saver()
        self.loader = loader
        self.Data = ResourcePath(None, self) # root of namespace
        self.Schema = SchemaPath(None, self)
        self.debug = False
        self.download = False
    def init_saver(self):
        self.saver = ResourceSaver(self)
        self.downloadKeeper = self # record downloaded resources here
    def find_resource(self, resID, download=False):
        yield self.rdb.find_resource(resID, download)
    def add_resource(self, resID, obj):
        self.saver.add_resource(resID, obj)
    def delete_resource(self, resID):
        self.saver.delete_resource(resID)
    def dir(self, prefix, asDict=False, download=False):
        pass
    def commit(self):
        self.saver.save_pending()
    def rollback(self):
        self.saver.rollback()
    def clear_all(self):
        'clear all resources from cache'
        self.loader.clear()
    def add_schema(self, resID, schemaObj):
        'use this public method to assign a schema relation object to a pygr.Data resource name'
        l = resID.split('.')
        schemaPath = SchemaPath('.'.join(l[:-1]), self)
        setattr(schemaPath, l[-1], schemaObj)
    def get_pending_or_find(self, resID, **kwargs):
        'find resID even if only pending (not actually saved yet)'
        try: # 1st LOOK IN PENDING QUEUE
            return self.saver.pendingData[resID][0]
        except KeyError:
            pass
        return self(resID,**kwargs)
    def getschema(self, resID):
        'return dict of {attr:{args}} or KeyError if not found'
        return self.rdb.getschema(resID)

class ReadOnlyMetabase(Metabase):
    'resource loading but no resource saving'
    def init_saver(self):
        return # do nothing

# public interface
# dir()
# update()
# __call__()
# 

class MetabaseList(MetabaseBase):
    '''Primary interface for pygr.Data resource database access.  A single instance
    of this class is created upon import of the pygr.Data module, accessible as
    pygr.Data.getResource.  Users normally will have no need to create additional
    instances of this class themselves.'''
    def __init__(self, loader, separator=',', saveDict=None, PYGRDATAPATH=None):
        self.loader = loader
        self.mdb = None
        self.layer = {}
        self.dbstr = ''
        self.separator = separator
        self.cursors = []
        self.debug = False
        self.download = False
        if saveDict is not None:
            self.saveDict = saveDict # SAVE NEW LAYER NAMES HERE...
            self.update(PYGRDATAPATH) # LOAD RESOURCE DBs FROM PYGRDATAPATH
            del self.saveDict
    def find_resource(self, resID, download=False):
        'search our metabases for pickle string and docstr for resID'
        for mdb in self.mdb:
            try:
                yield mdb.find_resource(resID, download)
            except KeyError: # not in this db
                pass
        raise PygrDataNotFoundError('unable to find %s in PYGRDATAPATH' % resID)
    ## def iter_mdb(self):
    ##     'iterate over all available databases, read from PYGRDATAPATH env var.'
    ##     self.update()
    ##     if self.db is None or len(self.db)==0:
    ##         raise ValueError('empty PYGRDATAPATH! Please check environment variable.')
    ##     return iter(self.db)
    def get_pygr_data_path(self):
        'use internal attribute, environment var, or default in that order'
        try:
            return self.PYGRDATAPATH
        except AttributeError:
            pass
        import os
        try:
            return os.environ['PYGRDATAPATH']
        except KeyError: # DEFAULT: HOME, CURRENT DIR, IN THAT ORDER
            return self.separator.join(['~','.',
                                        'http://biodb2.bioinformatics.ucla.edu:5000'])
    def update(self, PYGRDATAPATH=None):
        'get the latest list of resource databases'
        import os
        if PYGRDATAPATH is not None: # USE MANUALLY SUPPLIED SETTING
            self.PYGRDATAPATH  = PYGRDATAPATH
            self.loader.clear() # DUMP LOADED RESOURCE CACHE
            self.dbstr = None # FORCE RELOAD
        else: # OBTAIN BEST SETTING
            PYGRDATAPATH = self.get_pygr_data_path()
        if self.dbstr != PYGRDATAPATH: # LOAD NEW RESOURCE PYGRDATAPATH
            self.dbstr = PYGRDATAPATH
            self.mdb = []
            self.layer = {}
            for dbpath in PYGRDATAPATH.split(self.separator):
                try: # create metabase
                    mdb = Metabase(dbpath, self.loader, self.layer)
                except (KeyboardInterrupt,SystemExit):
                    raise # DON'T TRAP THESE CONDITIONS
                # FORCED TO ADOPT THIS STRUCTURE BECAUSE xmlrpc RAISES
                # socket.gaierror WHICH IS NOT A SUBCLASS OF StandardError...
                # SO I CAN'T JUST TRAP StandardError, UNFORTUNATELY...
                except: # TRAP ERRORS SO IMPORT OF THIS MODULE WILL NOT DIE!
                    if hasattr(self,'saveDict'): # IN THE MIDDLE OF MODULE IMPORT
                        import traceback
                        traceback.print_exc(10,sys.stderr) # JUST PRINT TRACEBACK
                        print >>sys.stderr,'''
error loading resource %s
NOTE: Just skipping this resource, without halting on this exception.
This error WILL NOT prevent successful import of this module.
Continuing with import...'''%dbpath
                    else:
                        raise # JUST PROPAGATE THE ERROR AS USUAL
                else: # NO PROBLEM, SO ADD TO OUR RESOURCE DB LIST
                    self.mdb.append(mdb) # SAVE TO OUR LIST OF RESOURCE DATABASES
    # Not sure this is needed anymore...
    def addLayer(self,layerName,rdb):
        'add resource database as a new named layer'
        if layerName in self.layer: # FOR SECURITY, DON'T ALLOW OVERWRITING
            print 'WARNING: ignored duplicate pygr.Data resource layer',layerName
            return
        self.layer[layerName]=rdb # INTERNAL DICTIONARY
        try: # ADD NAME TO THE MODULE TOP-LEVEL DICTIONARY
            self.saveDict[layerName]=ResourceLayer(layerName)
        except AttributeError:
            pass
    def save_root_names(self,rootNames):
        'add resource path root to the module dictionary'
        if hasattr(self,'saveDict'): # ONLY SAVE IF INITIALIZING THE MODULE
            for name in rootNames:
                if name not in self.saveDict:
                    self.saveDict[name]=ResourcePath(name)
    ## def getTableCursor(self,tablename):
    ##     'try to get the desired table using our current resource database cursor, if any'
    ##     try:
    ##         cursor = self.cursors[-1]
    ##     except IndexError:
    ##         try:
    ##             cursor = self.defaultCursor # USE IF WE HAVE ONE...
    ##         except AttributeError: # TRY TO GET ONE...
    ##             import sqlgraph
    ##             try:
    ##                 basename,cursor = sqlgraph.getNameCursor(tablename)
    ##                 self.defaultCursor = cursor # SAVE FOR RE-USE
    ##             except StandardError:
    ##                 return None
    ##     try: # MAKE SURE THIS CURSOR CAN PROVIDE tablename
    ##         cursor.execute('describe %s' % tablename)
    ##         return cursor # SUCCEEDED IN ACCESSING DESIRED TABLE
    ##     except StandardError:
    ##         return None
        
    def get_pending_or_find(self, resID, **kwargs):
        'find resID even if only pending (not actually saved yet)'
        for mdb in self.db:
            try: # 1st LOOK IN PENDING QUEUE
                return mdb.saver.pendingData[resID][0]
            except KeyError:
                pass
        return self(resID, **kwargs)
    def getLayer(self,layer):
        self.update() # MAKE SURE WE HAVE LOADED CURRENT DATABASE LIST
        if layer is not None:
            return self.layer[layer]
        else: # JUST USE OUR PRIMARY DATABASE
            return self.db[0]
    def registerServer(self,locationKey,serviceDict):
        'register the serviceDict with the first index server in PYGRDATAPATH'
        for db in self.resourceDBiter():
            if hasattr(db,'registerServer'):
                n=db.registerServer(locationKey,serviceDict)
                if n==len(serviceDict):
                    return n
        raise ValueError('unable to register services.  Check PYGRDATAPATH')
    def getschema(self, resID):
        'search our resource databases for schema info for the desired ID'
        for mdb in self.mdb:
            try:
                return mdb.getschema(resID) # TRY TO OBTAIN FROM THIS DATABASE
            except KeyError:
                pass # NOT IN THIS DB
        raise KeyError('no schema info available for ' + resID)
    def dir(self,prefix,layer=None,asDict=False,download=False):
        'get list or dict of resources beginning with the specified string'
        if layer is not None:
            db=self.getLayer(layer)
            return db.dir(prefix,asDict=asDict,download=download)
        d={}
        def iteritems(s):
            try:
                return s.iteritems()
            except AttributeError:
                return iter([(x,None) for x in s])
        for db in self.resourceDBiter():
            for k,v in iteritems(db.dir(prefix,asDict=asDict,download=download)):
                if k[0].isalpha() and k not in d: # ALLOW EARLIER DB TO TAKE PRECEDENCE
                    d[k]=v
        if asDict:
            return d
        else:
            l=[k for k in d]
            l.sort()
            return l




class ResourceLoader(dict):
    'provide one central repository of loaded resources & schema info'
    def __init__(self):
        dict.__init__(self)
        self.schemaCache = {}




class ResourceSaver(object):
    'queues new resources until committed to our mdb'
    def __init__(self, mdb):
        self.clear_pending()
        self.mdb = mdb
    def clear_pending(self):
        self.pendingData = {} # CLEAR THE PENDING QUEUE
        self.pendingSchema = {} # CLEAR THE PENDING QUEUE
        self.lastData = {}
        self.lastSchema = {}
        self.rollbackData = {} # CLEAR THE ROLLBACK CACHE
    def check_docstring(self,obj):
        'enforce requirement for docstring, by raising exception if not present'
        try:
            if obj.__doc__ is None or (hasattr(obj.__class__,'__doc__')
                                       and obj.__doc__==obj.__class__.__doc__):
                raise AttributeError
        except AttributeError:
            raise ValueError('to save a resource object, you MUST give it a __doc__ string attribute describing it!')
    def add_resource(self, resID, obj):
        'queue the object for saving to the specified database layer as <id>'
        self.check_docstring(obj)
        obj._persistent_id = resID # MARK OBJECT WITH ITS PERSISTENT ID
        self.pendingData[resID] = obj # ADD TO QUEUE
        try:
            self.rollbackData[resID] = self.mdb.loader[resID]
        except KeyError:
            pass
        self.mdb.loader[resID] = obj # SAVE TO OUR CACHE
    def addResourceDict(self, d):
        'queue a dict of name:object pairs for saving to specified db layer'
        for k,v in d.items():
            self.add_resource(k, v)
    def queue_schema_obj(self,schemaPath,attr,layer,schemaObj):
        'add a schema object to the queue for saving to the specified database layer'
        resID = schemaPath.getPath(attr) # GET STRING ID
        self.pendingSchema[resID] = (schemaPath,attr,layer,schemaObj)
    def save_resource(self, resID, obj):
        'save the object as <id>'
        self.check_docstring(obj)
        if obj._persistent_id != resID:
            raise PygrDataMismatchError('''The _persistent_id attribute for %s has changed!
If you changed it, shame on you!  Otherwise, this should not happen,
so report the reproducible steps to this error message as a bug report.''' % resID)
        self.mdb.rdb[resID] = obj # FINALLY, SAVE THE OBJECT TO THE DATABASE
        self.mdb.loader[resID] = obj # SAVE TO OUR CACHE
    def has_pending(self):
        'return True if there are resources pending to be committed'
        return len(self.pendingData)>0 or len(self.pendingSchema)>0
    def save_pending(self):
        'save any pending pygr.Data resources and schema'
        if len(self.pendingData)>0 or len(self.pendingSchema)>0:
            d = self.pendingData
            schemaDict = self.pendingSchema
        elif len(self.lastData)>0 or len(self.lastSchema)>0:
            d = self.lastData
            schemaDict = self.lastSchema
        else:
            raise PygrDataEmptyError('there is no data queued for saving!')
        # NOW SAVE THE DATA
        for resID,obj in d.items():
            self.save_resource(resID, obj)
        # NEXT SAVE THE SCHEMA
        for schemaPath,attr,layerGiven,schemaObj in schemaDict.values():
            schemaObj.saveSchema(schemaPath, attr, self) # save to mdb
        self.clear_pending() # FINALLY, CLEAN UP...
        self.lastData = d # KEEP IN CASE USER WANTS TO SAVE TO MULTIPLE LAYERS
        self.lastSchema = schemaDict
    def list_pending(self):
        'return tuple of pending data dictionary, pending schema'
        return list(self.pendingData),list(self.pendingSchema)
    def rollback(self):
        'dump any pending data without saving, and restore state of cache'
        if len(self.pendingData)==0 and len(self.pendingSchema)==0:
            raise PygrDataEmptyError('there is no data queued for saving!')
        self.mdb.loader.update(self.rollbackData) # RESTORE THE ROLLBACK QUEUE
        self.clear_pending()
    def delete_resource(self, resID): # incorporate this into commit-process?
        'delete the specified resource from loader, saver and schema'
        del self.mdb.rdb[resID] # delete from the resource database
        try: del self.mdb.loader[resID] # delete from cache if exists
        except KeyError: pass
        try: del self.pendingData[resID] # delete from queue if exists
        except KeyError: pass
        self.delSchema(resID)
    def saveSchema(self,id,attr,args,layer=None):
        'save an attribute binding rule to the schema; DO NOT use this internal interface unless you know what you are doing!'
        db=self.getLayer(layer)
        db.setschema(id,attr,args)
    def saveSchemaEdge(self,schema,layer):
        'save schema edge to schema graph'
        self.saveSchema(schema.name,'-schemaEdge',schema,layer)
        db = self.getLayer(layer)
        db.graph += schema.sourceDB # ADD NODE TO SCHEMA GRAPH
        db.graph[schema.sourceDB][schema.targetDB] = schema.name # ADD EDGE TO GRAPH
    def delSchema(self, resID):
        'delete schema bindings TO and FROM this resource ID'
        rdb = self.mdb.rdb
        try:
            d = rdb.getschema(resID) # GET THE EXISTING SCHEMA
        except KeyError:
            return # no schema stored for this object so nothing to do...
        self.schemaCache.clear() # THIS IS MORE AGGRESSIVE THAN NEEDED... COULD BE REFINED
        for attr,obj in d.items():
            if attr.startswith('-'): # A SCHEMA OBJECT
                obj.delschema(rdb) # DELETE ITS SCHEMA RELATIONS
            rdb.delschema(resID, attr) # delete attribute schema rule
    def __del__(self):
        self.lastData = {} # NO NEED TO RESAVE DATA THAT'S ALREADY SAVED
        self.lastSchema = {}
        try:
            self.save_pending() # SEE WHETHER ANY DATA NEEDS SAVING
            print >>sys.stderr,'''
WARNING: saving pygr.Data pending data that you forgot to save...
Remember in the future, you must issue the command pygr.Data.save() to save
your pending pygr.Data resources to your resource database(s), or alternatively
pygr.Data.rollback() to dump those pending data without saving them.
It is a very bad idea to rely on this automatic attempt to save your
forgotten data, because it is possible that the Python interpreter
may never call this function at exit (for details see the atexit module
docs in the Python Library Reference).'''
        except PygrDataEmptyError:
            pass


class ResourceServer(XMLRPCServerBase):
    'serves resources that can be transmitted on XMLRPC'
    def __init__(self, resourceDict, name, serverClasses=None, clientHost=None,
                 withIndex=False, excludeClasses=None, downloadDB=None,
                 **kwargs):
        'construct server for the designated classes'
        XMLRPCServerBase.__init__(self, name, **kwargs)
        if excludeClasses is None: # DEFAULT: NO POINT IN SERVING SQL TABLES...
            from sqlgraph import SQLTableBase,SQLGraphClustered
            excludeClasses = [SQLTableBase,SQLGraphClustered]
        if serverClasses is None: # DEFAULT TO ALL CLASSES WE KNOW HOW TO SERVE
            from seqdb import SequenceFileDB,BlastDB, \
                 XMLRPCSequenceDB,BlastDBXMLRPC, \
                 AnnotationDB, AnnotationClient, AnnotationServer
            serverClasses=[(SequenceFileDB,XMLRPCSequenceDB,BlastDBXMLRPC),
                           (BlastDB,XMLRPCSequenceDB,BlastDBXMLRPC),
                           (AnnotationDB,AnnotationClient,AnnotationServer)]
            try:
                from cnestedlist import NLMSA
                from xnestedlist import NLMSAClient,NLMSAServer
                serverClasses.append((NLMSA,NLMSAClient,NLMSAServer))
            except ImportError: # cnestedlist NOT INSTALLED, SO SKIP...
                pass
        if clientHost is None: # DEFAULT: USE THE SAME HOST STRING AS SERVER
            clientHost=server.host
        clientDict={}
        for id,obj in resourceDict.items(): # SAVE ALL OBJECTS MATCHING serverClasses
            skipThis = False
            for skipClass in excludeClasses: # CHECK LIST OF CLASSES TO EXCLUDE
                if isinstance(obj,skipClass):
                    skipThis = True
                    break
            if skipThis:
                continue # DO NOT INCLUDE THIS OBJECT IN SERVER
            skipThis=True
            for baseKlass,clientKlass,serverKlass in serverClasses:
                if isinstance(obj,baseKlass) and not isinstance(obj,clientKlass):
                    skipThis=False # OK, WE CAN SERVE THIS CLASS
                    break
            if skipThis: # HAS NO XMLRPC CLIENT-SERVER CLASS PAIRING
                try: # SAVE IT AS ITSELF
                    self.client_dict_setitem(clientDict,id,obj,badClasses=nonPortableClasses)
                except PygrDataNotPortableError:
                    pass # HAS NON-PORTABLE LOCAL DEPENDENCIES, SO SKIP IT
                continue # GO ON TO THE NEXT DATA RESOURCE
            try: # TEST WHETHER obj CAN BE RE-CLASSED TO CLIENT / SERVER
                obj.__class__=serverKlass # CONVERT TO SERVER CLASS FOR SERVING
            except TypeError: # GRR, EXTENSION CLASS CAN'T BE RE-CLASSED...
                state=obj.__getstate__() # READ obj STATE
                newobj=serverKlass.__new__(serverKlass) # ALLOCATE NEW OBJECT
                newobj.__setstate__(state) # AND INITIALIZE ITS STATE
                obj=newobj # THIS IS OUR RE-CLASSED VERSION OF obj
            try: # USE OBJECT METHOD TO SAVE HOST INFO, IF ANY...
                obj.saveHostInfo(clientHost,server.port,id)
            except AttributeError: # TRY TO SAVE URL AND NAME DIRECTLY ON obj
                obj.url = 'http://%s:%d' % (clientHost,server.port)
                obj.name = id
            obj.__class__ = clientKlass # CONVERT TO CLIENT CLASS FOR PICKLING
            self.client_dict_setitem(clientDict,id,obj)
            obj.__class__ = serverKlass # CONVERT TO SERVER CLASS FOR SERVING
            self[id] = obj # ADD TO XMLRPC SERVER
        self.registrationData = clientDict # SAVE DATA FOR SERVER REGISTRATION
        if withIndex: # SERVE OUR OWN INDEX AS A STATIC, READ-ONLY INDEX
            myIndex = ResourceDBServer(name, readOnly=True, # CREATE EMPTY INDEX
                                       downloadDB=downloadDB)
            self['index'] = myIndex # ADD TO OUR XMLRPC SERVER
            self.register('', '', server=myIndex) # ADD OUR RESOURCES TO THE INDEX
    def client_dict_setitem(self, clientDict, k, obj, **kwargs):
        'save pickle and schema for obj into clientDict'
        pickleString = dumps(obj,**kwargs) # PICKLE THE CLIENT OBJECT, SAVE
        clientDict[k] = (get_info_dict(obj,pickleString),pickleString)
        try: # SAVE SCHEMA INFO AS WELL...
            clientDict['SCHEMA.'+k] = (dict(schema_version='1.0'),
                                       self.findSchema(k))
        except KeyError:
            pass # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO



class ResourcePath(object):
    'simple way to read resource names as python foo.bar.bob expressions'
    def __init__(self, base=None, mdb=None):
        self.__dict__['_path'] = base # AVOID TRIGGERING setattr!
        self.__dict__['_mdb'] = mdb
    def getPath(self, name):
        if self._path is not None:
            return self._path+'.'+name
        else:
            return name
    def __getattr__(self, name):
        'extend the resource path by one more attribute'
        attr = self._pathClass(self.getPath(name), self._mdb)
        # MUST NOT USE setattr BECAUSE WE OVERRIDE THIS BELOW!
        self.__dict__[name] = attr # CACHE THIS ATTRIBUTE ON THE OBJECT
        return attr
    def __setattr__(self, name, obj):
        'save obj using the specified resource name'
        self._mdb.add_resource(self.getPath(name), obj)
    def __delattr__(self, name):
        self._mdb.delete_resource(self.getPath(name))
        try: # IF ACTUAL ATTRIBUTE EXISTS, JUST DELETE IT
            del self.__dict__[name]
        except KeyError: # TRY TO DELETE RESOURCE FROM THE DATABASE
            pass # NOTHING TO DO
    def __call__(self, *args, **kwargs):
        'construct the requested resource'
        return self._mdb(self._path, *args, **kwargs)
ResourcePath._pathClass=ResourcePath

class SchemaPath(ResourcePath):
    'save schema information for a resource'
    def __setattr__(self,name,schema):
        try:
            schema.saveSchema # VERIFY THAT THIS LOOKS LIKE A SCHEMA OBJECT
        except AttributeError:
            raise ValueError('not a valid schema object!')
        self._mdb.queue_schema_obj(self, name, schema) # QUEUE IT
    def __delattr__(self,attr):
        raise NotImplementedError('schema deletion is not yet implemented.')
    def set_attr_mapping(self,attr,targetDB,mapAttr=None):
        'bind attr to targetDB[getattr(self,mapAttr)]; mapAttr default is attr+"_id"'
        if idAttr is None: # CREATE DEFAULT 
            mapAttr = attr+'_id'
        b = ItemRelation(targetDB)
        b.saveSchema(self._path,attr,self._layer,dict(mapAttr=mapAttr))
    def del_attr_mapping(self,attr):
        raise NotImplementedError('schema deletion is not yet implemented.')
SchemaPath._pathClass=SchemaPath



class DirectRelation(object):
    'bind an attribute to the target'
    def __init__(self, target):
        self.targetID = getID(target)
    def schemaDict(self):
        return dict(targetID=self.targetID)
    def saveSchema(self, source, attr, mdb, **kwargs):
        d = self.schemaDict()
        d.update(kwargs) # ADD USER-SUPPLIED ARGS
        try: # IF kwargs SUPPLIED A TARGET, SAVE ITS ID
            d['targetID'] = getID(d['targetDB'])
            del d['targetDB']
        except KeyError:
            pass
        mdb.saveSchema(getID(source), attr, d)

class ItemRelation(DirectRelation):
    'bind item attribute to the target'
    def schemaDict(self):
        return dict(targetID=self.targetID,itemRule=True)

class ManyToManyRelation(object):
    'a general graph mapping from sourceDB -> targetDB with edge info'
    _relationCode='many:many'
    def __init__(self,sourceDB,targetDB,edgeDB=None,bindAttrs=None,
                 sourceNotNone=None,targetNotNone=None):
        self.sourceDB=getID(sourceDB) # CONVERT TO STRING RESOURCE ID
        self.targetDB=getID(targetDB)
        if edgeDB is not None:
            self.edgeDB=getID(edgeDB)
        else:
            self.edgeDB=None
        self.bindAttrs=bindAttrs
        if sourceNotNone is not None:
            self.sourceNotNone = sourceNotNone
        if targetNotNone is not None:
            self.targetNotNone = targetNotNone
    def save_graph_bindings(self, graphDB, attr, mdb):
        'save standard schema bindings to graphDB attributes sourceDB, targetDB, edgeDB'
        graphDB = graphDB.getPath(attr) # GET STRING ID FOR source
        self.name = graphDB
        mdb.saveSchemaEdge(self) #SAVE THIS RULE
        b = DirectRelation(self.sourceDB) # SAVE sourceDB BINDING
        b.saveSchema(graphDB, 'sourceDB', mdb)
        b = DirectRelation(self.targetDB) # SAVE targetDB BINDING
        b.saveSchema(graphDB, 'targetDB', mdb)
        if self.edgeDB is not None: # SAVE edgeDB BINDING
            b = DirectRelation(self.edgeDB)
            b.saveSchema(graphDB, 'edgeDB', mdb)
        return graphDB
    def saveSchema(self, path, attr, mdb):
        'save schema bindings associated with this rule'
        graphDB = self.save_graph_bindings(path, attr, mdb)
        if self.bindAttrs is not None:
            bindObj = (self.sourceDB,self.targetDB,self.edgeDB)
            bindArgs = [{},dict(invert=True),dict(getEdges=True)]
            try: # USE CUSTOM INVERSE SCHEMA IF PROVIDED BY TARGET DB
                bindArgs[1] = getResource.get_pending_or_find(graphDB)._inverse_schema()
            except AttributeError:
                pass
            for i in range(3):
                if len(self.bindAttrs)>i and self.bindAttrs[i] is not None:
                    b = ItemRelation(graphDB) # SAVE ITEM BINDING
                    b.saveSchema(bindObj[i], self.bindAttrs[i],
                                 mdb, **bindArgs[i])
    def delschema(self,resourceDB):
        'delete resource attribute bindings associated with this rule'
        if self.bindAttrs is not None:
            bindObj=(self.sourceDB,self.targetDB,self.edgeDB)
            for i in range(3):
                if len(self.bindAttrs)>i and self.bindAttrs[i] is not None:
                    resourceDB.delschema(bindObj[i],self.bindAttrs[i])

class OneToManyRelation(ManyToManyRelation):
    _relationCode='one:many'

class OneToOneRelation(ManyToManyRelation):
    _relationCode='one:one'

class ManyToOneRelation(ManyToManyRelation):
    _relationCode='many:one'

class InverseRelation(DirectRelation):
    "bind source and target as each other's inverse mappings"
    _relationCode = 'inverse'
    def saveSchema(self, source, attr, db, **kwargs):
        'save schema bindings associated with this rule'
        source=source.getPath(attr) # GET STRING ID FOR source
        self.name = source
        getResource.saveSchemaEdge(self,layer) #SAVE THIS RULE
        DirectRelation.saveSchema(self,source,'inverseDB',
                                  layer,**kwargs) # source -> target
        b=DirectRelation(source) # CREATE REVERSE MAPPING
        b.saveSchema(self.targetID,'inverseDB',
                     layer,**kwargs) # target -> source
    def delschema(self,resourceDB):
        resourceDB.delschema(self.targetID,'inverseDB')
        
