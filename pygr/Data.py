
import pickle
from StringIO import StringIO
import shelve


class OneTimeDescriptor(object):
    'provides shadow attribute based on schema'
    def __init__(self,attrName,**kwargs):
        self.attr=attrName
    def __get__(self,obj,objtype):
        try:
            id=obj._persistent_id # GET ITS RESOURCE ID
        except AttributeError:
            raise AttributeError('attempt to access pygr.Data attr on non-pygr.Data object')
        target=getResource.schemaAttr(id,self.attr) # ATTEMPT TO GET FROM pygr.Data
        obj.__dict__[self.attr]=target # PROVIDE DIRECTLY TO THE __dict__
        return target

class ItemDescriptor(object):
    'provides shadow attribute for items in a db, based on schema'
    def __init__(self,attrName,invert=False,getEdges=False,mapAttr=None,
                 targetAttr=None,**kwargs):
        self.attr=attrName
        self.invert=invert
        self.getEdges=getEdges
        self.mapAttr=mapAttr
        self.targetAttr=targetAttr
    def __get__(self,obj,objtype):
        try:
            id=obj.db._persistent_id # GET RESOURCE ID OF DATABASE
        except AttributeError:
            raise AttributeError('attempt to access pygr.Data attr on non-pygr.Data object')
        targetDict=getResource.schemaAttr(id,self.attr) # ATTEMPT TO GET FROM pygr.Data
        if self.invert:
            targetDict= ~targetDict
        if self.getEdges:  # NEED TO FIX THIS !!!
            targetDict=targetDict.edges
        if self.mapAttr is not None: # USE mapAttr TO GET ID FOR MAPPING obj
            result=targetDict[getattr(obj,self.mapAttr)]
        else:
            result=targetDict[obj] # NOW PERFORM MAPPING IN THAT RESOURCE...
        if self.targetAttr is not None:
            result=getattr(result,self.targetAttr) # GET ATTRIBUTE OF THE result
        obj.__dict__[self.attr]=result # PROVIDE DIRECTLY TO THE __dict__
        return result

class ForwardingDescriptor(object):
    'forward an attribute request to item from another container'
    def __init__(self,targetDB,attr):
        self.targetDB=targetDB # CONTAINER TO GET ITEMS FROM
        self.attr=attr # ATTRIBUTE TO MAP TO
    def __get__(self,obj,objtype):
        target=self.targetDB[obj.id] # GET target FROM CONTAINER
        return getattr(target,self.attr) # GET DESIRED ATTRIBUTE

class SpecialMethodDescriptor(object):
    'enables shadowing of special methods like __invert__'
    def __init__(self,attrName):
        self.attr=attrName
    def __get__(self,obj,objtype):
        try:
            return obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError('%s has no method %s'%(obj,self.attr))

def addSpecialMethod(obj,attr,f):
    '''bind function f as special method attr on obj.
       obj cannot be an builtin or extension class
       (if so, just subclass it)'''
    import new
    m=new.instancemethod(f,obj,obj.__class__)
    try:
        if getattr(obj,attr) == m: # ALREADY BOUND TO f
            return # ALREADY BOUND, NOTHING FURTHER TO DO
    except AttributeError:
        pass
    else:
        raise AttributeError('%s already bound to a different function' %attr)
    setattr(obj,attr,m) # SAVE BOUND METHOD TO __dict__
    setattr(obj.__class__,attr,SpecialMethodDescriptor(attr)) # DOES FORWARDING

def getInverseDB(self):
    'default shadow __invert__ method'
    return self.inverseDB # TRIGGER CONSTRUCTION OF THE TARGET RESOURCE


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


class ResourceDBServer(object):
    xmlrpc_methods={'getResource':0,'registerServer':0,'delResource':0,
                    'getName':0}
    def __init__(self,name,readOnly=False):
        self.name=name
        self.d={}
        if readOnly: # LOCK THE INDEX.  DON'T ACCEPT FOREIGN DATA!!
            self.xmlrpc_methods={'getResource':0,'getName':0} # ONLY ALLOW THESE METHODS!
    def getName(self):
        return self.name
    def getResource(self,id):
        try:
            return self.d[id] # RETURN DICT OF PICKLED OBJECTS
        except KeyError:
            return '' # EMPTY STRING INDICATES FAILURE
    def registerServer(self,locationKey,serviceDict):
        n=0
        for id,pdata in serviceDict.items():
            try:
                self.d[id][locationKey]=pdata # ADD TO DICT FOR THIS RESOURCE
            except KeyError:
                self.d[id]={locationKey:pdata} # CREATE NEW DICT FOR THIS RESOURCE
            n+=1
        return n  # COUNT OF SUCCESSFULLY REGISTERED SERVICES
    def delResource(self,id,locationKey):
        try:
            del self.d[id][locationKey]
        except KeyError:
            pass
        return ''  # DUMMY RETURN VALUE FOR XMLRPC

class ResourceDBClient(object):
    def __init__(self,url,finder):
        from coordinator import get_connection
        self.server=get_connection(url,'index')
        self.url=url
        self.finder=finder
        self.name=self.server.getName()
        finder.addLayer(self.name,self) # ADD NAMED RESOURCE LAYER
    def __getitem__(self,id):
        'get construction rule from index server, and attempt to construct'
        d=self.server.getResource(id) # RAISES KeyError IF NOT FOUND
        for location,objData in d.items():
            try:
                return self.finder.loads(objData)
            except KeyError:
                pass # HMM, TRY ANOTHER LOCATION
        raise KeyError('unable to construct %s from remote services'%id)
    def registerServer(self,locationKey,serviceDict):
        'forward registation to the server'
        return self.server.registerServer(locationKey,serviceDict)

class ResourceDBMySQL(object):
    '''mysql schema:
    (pygr_id varchar(255) not null,location varchar(255) not null,
    objdata text not null,unique(pygr_id,location))'''
    def __init__(self,tablename,finder=None,createLayer=None):
        import MySQLdb,os
        self.cursor=MySQLdb.connect(read_default_file=os.environ['HOME']
                                    +'/.my.cnf').cursor()
        self.tablename=tablename
        if finder is None: # USE DEFAULT FINDER IF NOT PROVIDED
            finder=getResource
        self.finder=finder
        if createLayer is not None: # CREATE DATABASE FROM SCRATCH
            self.cursor.execute('create table %s (pygr_id varchar(255) not null,location varchar(255) not null,objdata text not null,unique(pygr_id,location))'%tablename)
            self.cursor.execute('insert into %s values (%%s,%%s,%%s)'
                                %self.tablename,('PYGRLAYERNAME',createLayer,'a'))
            self.name=createLayer
            finder.addLayer(self.name,self) # ADD NAMED RESOURCE LAYER
        elif self.cursor.execute('select location from %s where pygr_id=%%s'
                               % self.tablename,('PYGRLAYERNAME',))>0:
            self.name=self.cursor.fetchone()[0] # GET LAYERNAME FROM DB
            finder.addLayer(self.name,self) # ADD NAMED RESOURCE LAYER
    def __getitem__(self,id):
        'get construction rule from mysql, and attempt to construct'
        self.cursor.execute('select location,objdata from %s where pygr_id=%%s'
                            % self.tablename,(id,))
        for location,objData in self.cursor.fetchall():
            try:
                return self.finder.loads(objData)
            except KeyError:
                pass # HMM, TRY ANOTHER LOCATION
        raise KeyError('unable construct %s from remote services')
    def __setitem__(self,id,obj):
        'add an object to this resource database'
        s=self.finder.dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        self.cursor.execute('replace into %s values (%%s,%%s,%%s)'
                            %self.tablename,(id,'mysql:'+self.tablename,s))
    def __delitem__(self,id):
        'delete this resource and its schema rules'
        if self.cursor.execute('delete from %s where pygr_id=%%s'
                               %self.tablename,(id,))<1:
            raise KeyError('no resource %s in this database'%id)
    def registerServer(self,locationKey,serviceDict):
        'register the specified services to mysql database'
        n=0
        for id,pdata in serviceDict.items():
            n+=self.cursor.execute('replace into %s values (%%s,%%s,%%s)' %
                                   self.tablename,(id,locationKey,pdata))
        return n
    def setschema(self,id,attr,kwargs):
        'save a schema binding for id.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID=kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        kwdata=self.finder.dumps(kwargs)
        self.cursor.execute('replace into %s values (%%s,%%s,%%s)'
                            %self.tablename,('SCHEMA.'+id,attr,kwdata))
    def delschema(self,id,attr):
        'delete schema binding for id.attr'
        self.cursor.execute('delete from %s where pygr_id=%%s and location=%%s'
                            %self.tablename,('SCHEMA.'+id,attr))
    def getschema(self,id):
        'return dict of {attr:{args}}'
        d={}
        self.cursor.execute('select location,objdata from %s where pygr_id=%%s'
                            % self.tablename,('SCHEMA.'+id,))
        for attr,objData in self.cursor.fetchall():
            d[attr]=self.finder.loads(objData)
        return d
            

class ResourceDBShelve(object):
    def __init__(self,dbpath,finder,mode='r'):
        import anydbm,os
        self.dbpath=os.path.join(dbpath,'.pygr_data') # CONSTRUCT FILENAME
        self.finder=finder
        try: # OPEN DATABASE FOR READING
            self.db=shelve.open(self.dbpath,mode)
        except anydbm.error: # CREATE NEW FILE IF NEEDED
            self.db=shelve.open(self.dbpath,'c')
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
    def setschema(self,id,attr,kwargs):
        'save a schema binding for id.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID=kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        try:
            d=self.db['SCHEMA.'+id]
        except KeyError:
            d={}
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


class ResourceFinder(object):
    def __init__(self,separator=',',saveDict=None):
        self.db=None
        self.layer={}
        self.dbstr=''
        self.d={}
        self.separator=separator
        if saveDict is not None:
            self.saveDict=saveDict # SAVE NEW LAYER NAMES HERE...
            self.update() # FORCE LOADING OF RESOURCE DBs FROM PYGRDATAPATH
            del self.saveDict
    def update(self):
        'get the latest list of resource databases'
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
                try:
                    if dbpath.startswith('http://'):
                        rdb=ResourceDBClient(dbpath,self)
                        if 'remote' not in self.layer:
                            self.layer['remote']=rdb
                    elif dbpath.startswith('mysql:'):
                        rdb=ResourceDBMySQL(dbpath[6:],self)
                        if 'MySQL' not in self.layer:
                            self.layer['MySQL']=rdb
                    else: # TREAT AS LOCAL FILEPATH
                        dbpath=os.path.expanduser(dbpath)
                        rdb=ResourceDBShelve(dbpath,self)
                        if dbpath.startswith('/') and 'system' not in self.layer:
                            self.layer['system']=rdb
                        if dbpath.startswith(os.path.expanduser('~')) \
                               and 'my' not in self.layer:
                            self.layer['my']=rdb
                        if dbpath.startswith('.') and 'here' not in self.layer:
                            self.layer['here']=rdb
                except: # TRAP ERRORS SO IMPORT OF THIS MODULE WILL NOT DIE!
                    if hasattr(self,'saveDict'): # IN THE MIDDLE OF MODULE IMPORT
                        import traceback,sys
                        traceback.print_exc(10,sys.stderr) # JUST PRINT TRACEBACK
                        print >>sys.stderr,'''
error loading resource %s
NOTE: Just skipping this resource, without halting on this exception.
This error WILL NOT prevent successful import of this module.
Continuing with import...'''%dbpath
                    else:
                        raise # JUST PROPAGATE THE ERROR AS USUAL
                else: # NO PROBLEM, SO ADD TO OUR RESOURCE DB LIST
                    self.db.append(rdb) # SAVE TO OUR LIST OF RESOURCE DATABASES
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
                except KeyError,IOError:
                    pass # NOT IN THIS DB, OR OBJECT DATAFILES NOT LOADABLE HERE...
            if obj is None:
                raise KeyError('unable to find %s in PYGRDATAPATH' % id)
        obj._persistent_id=id  # MARK WITH ITS PERSISTENT ID
        self.d[id]=obj # SAVE TO OUR CACHE
        self.applySchema(id,obj) # BIND SHADOW ATTRIBUTES IF ANY
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
        self.delSchema(id,layer)
    def newServer(self,name,serverClasses=None,clientHost=None,
                  withIndex=False,**kwargs):
        'construct server for the designated classes'
        if serverClasses is None: # DEFAULT TO ALL CLASSES WE KNOW HOW TO SERVE
            from seqdb import BlastDB,XMLRPCSequenceDB,BlastDBXMLRPC
            serverClasses=[(BlastDB,XMLRPCSequenceDB,BlastDBXMLRPC)]
            try:
                from cnestedlist import NLMSA
                from xnestedlist import NLMSAClient,NLMSAServer
                serverClasses.append((NLMSA,NLMSAClient,NLMSAServer))
            except ImportError: # cnestedlist NOT INSTALLED, SO SKIP...
                pass
        import coordinator
        server=coordinator.XMLRPCServerBase(name,**kwargs)
        if clientHost is None: # DEFAULT: USE THE SAME HOST STRING AS SERVER
            clientHost=server.host
        clientDict={}
        for id,obj in self.d.items(): # SAVE ALL OBJECTS MATCHING serverClasses
            skipThis=True
            for baseKlass,clientKlass,serverKlass in serverClasses:
                if isinstance(obj,baseKlass) and not isinstance(obj,clientKlass):
                    skipThis=False # OK, WE CAN SERVE THIS CLASS
                    break
            if skipThis: # CAN'T SERVE THIS CLASS, SO SKIP IT
                continue
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
                obj.url='http://%s:%d' % (clientHost,server.port)
                obj.name=id
            obj.__class__=clientKlass # CONVERT TO CLIENT CLASS FOR PICKLING
            clientDict[id]=self.dumps(obj) # PICKLE THE CLIENT OBJECT, SAVE
            obj.__class__=serverKlass # CONVERT TO SERVER CLASS FOR SERVING
            server[id]=obj # ADD TO XMLRPC SERVER
        server.registrationData=clientDict # SAVE DATA FOR SERVER REGISTRATION
        if withIndex: # SERVE OUR OWN INDEX AS A STATIC, READ-ONLY INDEX
            myIndex=ResourceDBServer(name,readOnly=True) # CREATE EMPTY INDEX
            server['index']=myIndex # ADD TO OUR XMLRPC SERVER
            server.register('','',server=myIndex) # ADD OUR RESOURCES TO THE INDEX
        return server
    def registerServer(self,locationKey,serviceDict):
        'register the serviceDict with the first index server in PYGRDATAPATH'
        for db in self.resourceDBiter():
            if hasattr(db,'registerServer'):
                n=db.registerServer(locationKey,serviceDict)
                if n==len(serviceDict):
                    return n
        raise ValueError('unable to register services.  Check PYGRDATAPATH')
    def findSchema(self,id):
        'search our resource databases for schema info for the desired ID'
        for db in self.resourceDBiter():
            try:
                return db.getschema(id) # TRY TO OBTAIN FROM THIS DATABASE
            except KeyError:
                pass # NOT IN THIS DB
        raise KeyError('no schema info available for '+id)
    def schemaAttr(self,id,attr):
        'actually retrieve the desired schema attribute'
        try:
            schema=self.findSchema(id)[attr]
        except KeyError:
            raise AttributeError('no pygr.Data schema info for %s.%s'%(id,attr))
        targetID=schema['targetID'] # GET THE RESOURCE ID
        return self(targetID) # ACTUALLY GET THE RESOURCE
    def applySchema(self,id,obj):
        'if this resource ID has any schema, bind appropriate shadow attrs'
        try:
            schema=self.findSchema(id)
        except KeyError:
            return # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO
        for attr,rules in schema.items():
            if not attr.startswith('-'): # ONLY SHADOW REAL ATTRIBUTES
                self.shadowAttr(obj,attr,**rules)
    def shadowAttr(self,obj,attr,itemRule=False,**kwargs):
        'create a descriptor for the attr on the appropriate obj class'
        try: # SEE IF OBJECT TELLS US TO SKIP THIS ATTRIBUTE
            return obj._ignoreShadowAttr[attr] # IF PRESENT, NOTHING TO DO
        except AttributeError,KeyError:
            pass # PROCEED AS NORMAL
        if itemRule: # SHOULD BIND TO ITEMS FROM obj DATABASE
            targetClass=obj.itemClass # CLASS USED FOR CONSTRUCTING ITEMS
            descr=ItemDescriptor(attr,**kwargs)
        else: # SHOULD BIND DIRECTLY TO obj VIA ITS CLASS
            targetClass=obj.__class__
            descr=OneTimeDescriptor(attr,**kwargs)
        setattr(targetClass,attr,descr) # BIND TO THE TARGET CLASS
        if itemRule:
            try: # BIND TO itemSliceClass TOO, IF IT EXISTS...
                setattr(obj.itemSliceClass,attr,descr)
            except AttributeError:
                pass
        if attr=='inverseDB': # ADD SHADOW __invert__ TO ACCESS THIS
            addSpecialMethod(obj,'__invert__',getInverseDB)
    def saveSchema(self,id,attr,args,layer=None):
        'save an attribute binding rule to the schema'
        db=self.getLayer(layer)
        db.setschema(id,attr,args)
    def delSchema(self,id,layer=None):
        'delete schema bindings TO and FROM this resource ID'
        db=self.getLayer(layer)
        d=db.getschema(id) # GET THE EXISTING SCHEMA
        for attr,obj in d.items():
            if attr.startswith('-'): # A SCHEMA OBJECT
                obj.delschema(db) # DELETE ITS SCHEMA RELATIONS
            db.delschema(id,attr) # DELETE THIS ATTRIBUTE SCHEMA RULE
        





class ResourcePath(object):
    'simple way to read resource names as python foo.bar.bob expressions'
    def __init__(self,base=None,layer=None):
        self.__dict__['_path']=base # AVOID TRIGGERING setattr!
        self.__dict__['_layer']=layer
    def getPath(self,name):
        if self._path is not None:
            return self._path+'.'+name
        else:
            return name
    def __getattr__(self,name):
        'extend the resource path by one more attribute'
        attr=self._pathClass(self.getPath(name),self._layer)
        # MUST NOT USE setattr BECAUSE WE OVERRIDE THIS BELOW!
        self.__dict__[name]=attr # CACHE THIS ATTRIBUTE ON THE OBJECT
        return attr
    def __setattr__(self,name,obj):
        'save obj using the specified resource name'
        getResource.addResource(self.getPath(name),obj,self._layer)
    def __delattr__(self,name):
        getResource.deleteResource(self.getPath(name),self._layer)
        try: # IF ACTUAL ATTRIBUTE EXISTS, JUST DELETE IT
            del self.__dict__[name]
        except KeyError: # TRY TO DELETE RESOURCE FROM THE DATABASE
            pass # NOTHING TO DO
    def __call__(self,*args,**kwargs):
        'construct the requested resource'
        return getResource(self._path,layer=self._layer,*args,**kwargs)
ResourcePath._pathClass=ResourcePath

class SchemaPath(ResourcePath):
    'save schema information for a resource'
    def __setattr__(self,name,schema):
        try:
            m=schema.saveSchema
        except AttributeError:
            AttributeError('not a valid schema object!')
        m(self,name) # SAVE THIS SCHEMA INFO
SchemaPath._pathClass=SchemaPath

class ResourceLayer(object):
    def __init__(self,layer):
        self._layer=layer
        self.schema=SchemaPath(layer=layer) # SCHEMA CONTROL FOR THIS LAYER
    def __getattr__(self,name):
        attr=ResourcePath(name,self._layer)
        setattr(self,name,attr) # CACHE THIS ATTRIBUTE ON THE OBJECT
        return attr


class DirectRelation(object):
    'bind an attribute to the target'
    def __init__(self,target):
        self.target=getID(target)
    def schemaDict(self):
        return dict(targetID=self.target)
    def saveSchema(self,source,attr,layer=None,**kwargs):
        d=self.schemaDict()
        d.update(kwargs) # ADD USER-SUPPLIED ARGS
        getResource.saveSchema(getID(source),attr,d,layer)

class ItemRelation(DirectRelation):
    'bind item attribute to the target'
    def schemaDict(self):
        return dict(targetID=self.target,itemRule=True)

class ManyToManyRelation(object):
    'a general graph mapping from sourceDB -> targetDB with edge info'
    def __init__(self,sourceDB,targetDB,edgeDB=None,bindAttrs=None):
        self.sourceDB=getID(sourceDB) # CONVERT TO STRING RESOURCE ID
        self.targetDB=getID(targetDB)
        if edgeDB is not None:
            self.edgeDB=getID(edgeDB)
        else:
            self.edgeDB=None
        self.bindAttrs=bindAttrs
    def saveSchema(self,source,attr,layer=None):
        'save schema bindings associated with this rule'
        source=source.getPath(attr) # GET STRING ID FOR source
        getResource.saveSchema(source,'-many:many',self,layer) #SAVE THIS RULE
        b=DirectRelation(self.sourceDB) # SAVE sourceDB BINDING
        b.saveSchema(source,'sourceDB',layer)
        b=DirectRelation(self.targetDB) # SAVE targetDB BINDING
        b.saveSchema(source,'targetDB',layer)
        if self.edgeDB is not None: # SAVE edgeDB BINDING
            b=DirectRelation(self.edgeDB)
            b.saveSchema(source,'edgeDB',layer)
        if self.bindAttrs is not None:
            bindObj=(self.sourceDB,self.targetDB,self.edgeDB)
            bindArgs=({},dict(invert=True),dict(getEdges=True))
            for i in range(3):
                if len(self.bindAttrs)>i and self.bindAttrs[i] is not None:
                    b=ItemRelation(source) # SAVE ITEM BINDING
                    b.saveSchema(bindObj[i],self.bindAttrs[i],
                                 layer,**bindArgs[i])
    def delschema(self,resourceDB):
        'delete resource attribute bindings associated with this rule'
        if self.bindAttrs is not None:
            bindObj=(self.sourceDB,self.targetDB,self.edgeDB)
            for i in range(3):
                if len(self.bindAttrs)>i and self.bindAttrs[i] is not None:
                    resourceDB.delschema(bindObj[i],self.bindAttrs[i])


class InverseRelation(DirectRelation):
    "bind source and target as each other's inverse mappings"
    def saveSchema(self,source,attr,layer=None,**kwargs):
        'save schema bindings associated with this rule'
        source=source.getPath(attr) # GET STRING ID FOR source
        getResource.saveSchema(source,'-inverse',self,layer) # THIS RULE
        DirectRelation.saveSchema(self,source,'inverseDB',
                                  layer,**kwargs) # source -> target
        b=DirectRelation(source) # CREATE REVERSE MAPPING
        b.saveSchema(self.target,'inverseDB',
                     layer,**kwargs) # target -> source
    def delschema(self,resourceDB):
        resourceDB.delschema(self.target,'inverseDB')
        
def getID(obj):
    'get persistent ID of the object or raise AttributeError'
    if isinstance(obj,str): # TREAT ANY STRING AS A RESOURCE ID
        return obj
    elif isinstance(obj,ResourcePath):
        return obj._path # GET RESOURCE ID FROM A ResourcePath
    else:
        try: # GET RESOURCE'S PERSISTENT ID
            return obj._persistent_id
        except AttributeError:
            raise AttributeError('this obj has no persistent ID!')


class ForeignKeyMapInverse(object):
    def __init__(self,forwardMap):
        self._inverse=forwardMap
    def __getitem__(self,k):
        return self._inverse.sourceDB[getattr(k,self._inverse.keyName)]
    def __invert__(self):
        return self._inverse


class ForeignKeyMap(object):
    def __init__(self,foreignKey,sourceDB=None,targetDB=None):
        self.keyName=foreignKey
        self.sourceDB=sourceDB
        self.targetDB=targetDB
    def __getitem__(self,k):
        return self.targetDB.foreignKey(self.keyName,k.id)
    def __invert__(self):
        try:
            return self._inverse
        except AttributeError:
            self._inverse=ForeignKeyMapInverse(self)
            return self._inverse


###########################################################
schema=SchemaPath() # ROOT OF OUR SCHEMA NAMESPACE

# PROVIDE TOP-LEVEL NAMES IN OUR RESOURCE HIERARCHY
Bio=ResourcePath('Bio')


# TOP-LEVEL NAMES FOR STANDARDIZED LAYERS
here=ResourceLayer('here')
my=ResourceLayer('my')
system=ResourceLayer('system')
remote=ResourceLayer('remote')
MySQL=ResourceLayer('MySQL')

################# CREATE AN INTERFACE TO THE RESOURCE DATABASE
getResource=ResourceFinder(saveDict=locals())
