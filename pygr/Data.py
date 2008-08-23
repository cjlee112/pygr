
import pickle,sys
from StringIO import StringIO
import shelve
from mapping import Collection,Mapping,Graph
from classutil import standard_invert


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
                 targetAttr=None,uniqueMapping=False,**kwargs):
        self.attr=attrName
        self.invert=invert
        self.getEdges=getEdges
        self.mapAttr=mapAttr
        self.targetAttr=targetAttr
        self.uniqueMapping = uniqueMapping
    def get_target(self,obj):
        'return the mapping object for this schema relation'
        try:
            id = obj.db._persistent_id # GET RESOURCE ID OF DATABASE
        except AttributeError:
            raise AttributeError('attempt to access pygr.Data attr on non-pygr.Data object')
        targetDict = getResource.schemaAttr(id,self.attr) # ATTEMPT TO GET FROM pygr.Data
        if self.invert:
            targetDict = ~targetDict
        if self.getEdges:
            targetDict = targetDict.edges
        return targetDict
    def __get__(self,obj,objtype):
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

class ItemDescriptorRW(ItemDescriptor):
    def __set__(self,obj,newTarget):
        if not self.uniqueMapping:
            raise PygrDataSchemaError('''You attempted to directly assign to a graph mapping
(x.graph = y)! Instead, treat the graph like a dictionary: x.graph[y] = edgeInfo''')
        targetDict = self.get_target(obj)
        targetDict[obj] = newTarget
        obj.__dict__[self.attr] = newTarget # CACHE IN THE __dict__


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


class PygrDataNotPortableError(ValueError):
    'indicates that object has a local data dependency and cannnot be transferred to a remote client'
    pass
class PygrDataNotFoundError(KeyError):
    'unable to find a loadable resource for the requested pygr.Data identifier from PYGRDATAPATH'
    pass
class PygrDataMismatchError(ValueError):
    '_persistent_id attr on object no longer matches its assigned pygr.Data ID?!?'
    pass
class PygrDataEmptyError(ValueError):
    "user hasn't queued anything, so trying to save or rollback is an error"
    pass
class PygrDataReadOnlyError(ValueError):
    'attempt to write data to a read-only resource database'
    pass
class PygrDataSchemaError(ValueError):
    "attempt to set attribute to an object not in the database bound by schema"
    pass

class PygrDataNoModuleError(pickle.PickleError):
    'attempt to pickle a class from a non-importable module'
    pass

class PygrPickler(pickle.Pickler):
    def persistent_id(self,obj):
        'convert objects with _persistent_id to PYGR_ID strings during pickling'
        import types
        try: # check for unpicklable class (i.e. not loaded via a module import)
            if isinstance(obj, types.TypeType) and obj.__module__ == '__main__':
                raise PygrDataNoModuleError('''You cannot pickle a class from __main__!
To make this class (%s) picklable, it must be loaded via a regular import
statement.''' % obj.__name__)
        except AttributeError:
            pass
        try:
            if not isinstance(obj,types.TypeType) and obj is not self.root:
                try:
                    return 'PYGR_ID:%s' % self.sourceIDs[id(obj)]
                except KeyError:
                    if obj._persistent_id is not None:
                        return 'PYGR_ID:%s' % obj._persistent_id
        except AttributeError:
            pass
        for klass in self.badClasses: # CHECK FOR LOCAL DEPENDENCIES
            if isinstance(obj,klass):
                raise PygrDataNotPortableError('this object has a local data dependency and cannnot be transferred to a remote client')
        return None
    def setRoot(self,obj,sourceIDs={},badClasses=()):
        'set obj as root of pickling tree: genuinely pickle it (not just its id)'
        self.root=obj
        self.sourceIDs=sourceIDs
        self.badClasses = badClasses


class ResourceDBServer(object):
    'simple XMLRPC resource database server'
    xmlrpc_methods={'getResource':0,'registerServer':0,'delResource':0,
                    'getName':0,'dir':0,'get_version':0}
    _pygr_data_version=(0,1,0)
    def __init__(self,name,readOnly=True,downloadDB=None):
        self.name=name
        self.d={}
        self.docs={}
        self.downloadDB = {}
        self.downloadDocs = {}
        if readOnly: # LOCK THE INDEX.  DON'T ACCEPT FOREIGN DATA!!
            self.xmlrpc_methods={'getResource':0,'getName':0,'dir':0,
                                 'get_version':0} # ONLY ALLOW THESE METHODS!
        if downloadDB is not None:
            self.read_download_db(downloadDB)
    def read_download_db(self,filename,location='default'):
        'add the designated resource DB shelve to our downloadable resources'
        d = shelve.open(filename,'r')
        for k,v in d.items():
            if k.startswith('__doc__.'): # SAVE DOC INFO FOR THIS ID
                self.downloadDocs[k[8:]] = v
            else: # SAVE OBJECT INFO
                self.downloadDB.setdefault(k,{})[location] = v
        d.close()
    def getName(self):
        'return layer name for this server'
        return self.name
    def get_db(self,download):
        if download: # USE SEPARATE DOWNLOAD DATABASE
            return (self.downloadDB, self.downloadDocs)
        else: # USE REGULAR XMLRPC SERVICES DATABASE
            return (self.d, self.docs)
    def getResource(self,id,download=False):
        'return dict of location:pickleData for requested ID'
        db,docs = self.get_db(download)
        try:
            d = db[id] # RETURN DICT OF PICKLED OBJECTS
        except KeyError:
            return '' # EMPTY STRING INDICATES FAILURE
        if id.startswith('SCHEMA.'): # THIS IS A REQUEST FOR SCHEMA INFO
            for location in d: # -schemaEdge DATA NOT SENDABLE BY XMLRPC
                try:
                    del d[location]['-schemaEdge']
                except KeyError:
                    pass
        else: # THIS IS A REGULAR RESOURCE REQUEST
            try: # PASS ITS DOCSTRING AS A SPECIAL ENTRY
                d['__doc__'] = docs[id]['__doc__']
            except KeyError:
                pass
        return d
    def registerServer(self,locationKey,serviceDict):
        'add services in serviceDict to this server under the specified location'
        n=0
        for id,(infoDict,pdata) in serviceDict.items():
            self.d.setdefault(id,{})[locationKey] = pdata # SAVE RESOURCE
            if infoDict is not None:
                self.docs[id]=infoDict
            n+=1
        return n  # COUNT OF SUCCESSFULLY REGISTERED SERVICES
    def delResource(self,id,locationKey):
        'delete the specified resource under the specified location'
        try:
            del self.d[id][locationKey]
            if len(self.d[id])==0:
                del self.docs[id]
        except KeyError:
            pass
        return ''  # DUMMY RETURN VALUE FOR XMLRPC
    def dir(self,prefix,asDict=False,download=False):
        'return list or dict of resources beginning with the specified prefix'
        db,docs = self.get_db(download)
        l=[]
        for name in db: # FIND ALL ITEMS WITH MATCHING NAME
            if name.startswith(prefix):
                l.append(name)
        if asDict: # RETURN INFO DICT FOR EACH ITEM
            d = {}
            for name in l:
                d[name] = docs.get(name,{})
            return d
        return l
    def get_version(self):
        return self._pygr_data_version


def raise_illegal_save(self,*l):
    raise PygrDataReadOnlyError('''You cannot save data to a remote XMLRPC server.
Give a user-editable resource database as the first entry in your PYGRDATAPATH!''')


class ResourceDBClient(object):
    'client interface to remote XMLRPC resource database'
    def __init__(self,url,finder):
        from coordinator import get_connection
        self.server=get_connection(url,'index')
        self.url=url
        self.finder=finder
        self.name=self.server.getName()
        finder.addLayer(self.name,self) # ADD NAMED RESOURCE LAYER
    def __getitem__(self,id,download=False):
        'get construction rule from index server, and attempt to construct'
        if download: # SPECIFICALLY ASK SERVER FOR DOWNLOADABLE RESOURCES
            d = self.server.getResource(id,download)
        else: # NORMAL MODE TO GET XMLRPC SERVICES
            d=self.server.getResource(id)
        if d=='':
            raise PygrDataNotFoundError('resource %s not found'%id)
        try:
            docstring = d['__doc__']
            del d['__doc__']
        except KeyError:
            docstring = None
        for location,objData in d.items():
            try:
                obj = self.finder.loads(objData)
                obj.__doc__ = docstring
                return obj
            except KeyError:
                pass # HMM, TRY ANOTHER LOCATION
        raise KeyError('unable to construct %s from remote services'%id)
    def registerServer(self,locationKey,serviceDict):
        'forward registration to the server'
        return self.server.registerServer(locationKey,serviceDict)
    def getschema(self,id):
        'return dict of {attr:{args}}'
        d=self.server.getResource('SCHEMA.'+id)
        if d=='': # NO SCHEMA INFORMATION FOUND
            raise KeyError
        for schemaDict in d.values():
            return schemaDict # HAND BACK FIRST SCHEMA WE FIND
        raise KeyError
    def dir(self,prefix,asDict=False,download=False):
        'return list or dict of resources starting with prefix'
        if download:
            return self.server.dir(prefix,asDict,download)
        else:
            return self.server.dir(prefix,asDict)
    __setitem__ = raise_illegal_save # RAISE USEFUL EXPLANATORY ERROR MESSAGE
    __delitem__ = raise_illegal_save
    setschema = raise_illegal_save
    delschema = raise_illegal_save



class ResourceDBMySQL(object):
    '''To create a new resource table, call:
ResourceDBMySQL("DBNAME.TABLENAME",createLayer="LAYERNAME")
where DBNAME is the name of your database, TABLENAME is the name of the
table you want to create, and LAYERNAME is the layer name you want to assign it'''
    _pygr_data_version=(0,1,0)
    def __init__(self,tablename,finder=None,createLayer=None):
        from sqlgraph import getNameCursor,SQLGraph
        self.tablename,self.cursor=getNameCursor(tablename)
        if finder is None: # USE DEFAULT FINDER IF NOT PROVIDED
            finder=getResource
        self.finder=finder
        self.rootNames={}
        schemaTable = self.tablename+'_schema' # SEPARATE TABLE FOR SCHEMA GRAPH
        if createLayer is not None: # CREATE DATABASE FROM SCRATCH
            from datetime import datetime
            creation_time = datetime.now()
            self.cursor.execute('drop table if exists %s' % self.tablename)
            self.cursor.execute('create table %s (pygr_id varchar(255) not null,location varchar(255) not null,docstring varchar(255),user varchar(255),creation_time datetime,pickle_size int,security_code bigint,info_blob text,objdata text not null,unique(pygr_id,location))'%self.tablename)
            self.cursor.execute('insert into %s (pygr_id,location,creation_time,objdata) values (%%s,%%s,%%s,%%s)'
                                %self.tablename,
                                ('PYGRLAYERNAME',createLayer,creation_time,'a'))
            self.cursor.execute('insert into %s (pygr_id,location,objdata) values (%%s,%%s,%%s)'
                                %self.tablename,
                                ('0version','%d.%d.%d' % self._pygr_data_version,
                                 'a')) # SAVE VERSION STAMP
            self.name=createLayer
            finder.addLayer(self.name,self) # ADD NAMED RESOURCE LAYER
            self.cursor.execute('drop table if exists %s' % schemaTable)
            self.cursor.execute('create table %s (source_id varchar(255) not null,target_id varchar(255),edge_id varchar(255),unique(source_id,target_id))' % schemaTable)
        else:
            try:
                n = self.cursor.execute('select location from %s where pygr_id=%%s'
                                        % self.tablename,('PYGRLAYERNAME',))
            except StandardError:
                print >>sys.stderr,'''%s
Database table %s appears to be missing or has no layer name!
To create this table, call pygr.Data.ResourceDBMySQL("%s",createLayer=<LAYERNAME>)
where <LAYERNAME> is the layer name you want to assign it.
%s'''  %('!'*40,self.tablename,self.tablename,'!'*40)
                raise
            if n>0:
                self.name=self.cursor.fetchone()[0] # GET LAYERNAME FROM DB
                finder.addLayer(self.name,self) # ADD NAMED RESOURCE LAYER
            if self.cursor.execute('select location from %s where pygr_id=%%s'
                                   % self.tablename,('0root',))>0:
                for row in self.cursor.fetchall():
                    self.rootNames[row[0]]=None
                finder.save_root_names(self.rootNames)
        self.graph = SQLGraph(schemaTable,self.cursor,attrAlias=
                              dict(source_id='source_id',target_id='target_id',
                                   edge_id='edge_id'),simpleKeys=True,
                              unpack_edge=SchemaEdge(self))
    def save_root_name(self,name):
        self.rootNames[name]=None
        self.cursor.execute('insert into %s (pygr_id,location,objdata) values (%%s,%%s,%%s)'
                            %self.tablename,('0root',name,'a'))
    def __getitem__(self,id,download=False):
        'get construction rule from mysql, and attempt to construct'
        self.cursor.execute('select location,objdata,docstring from %s where pygr_id=%%s'
                            % self.tablename,(id,))
        for location,objData,docstring in self.cursor.fetchall():
            try:
                obj = self.finder.loads(objData,self.cursor)
                obj.__doc__ = docstring
                return obj
            except KeyError: # MUST HAVE FAILED TO LOAD A REQUIRED DEPENDENCY
                pass # HMM, TRY ANOTHER LOCATION
        raise PygrDataNotFoundError('unable to construct %s from remote services')
    def __setitem__(self,id,obj):
        'add an object to this resource database'
        s=self.finder.dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        d = getResource.get_info_dict(obj,s)
        self.cursor.execute('replace into %s (pygr_id,location,docstring,user,creation_time,pickle_size,objdata) values (%%s,%%s,%%s,%%s,%%s,%%s,%%s)'
                            %self.tablename,
                            (id,'mysql:'+self.tablename,obj.__doc__,d['user'],
                             d['creation_time'],d['pickle_size'],s))
        root=id.split('.')[0]
        if root not in self.rootNames:
            self.save_root_name(root)
    def __delitem__(self,id):
        'delete this resource and its schema rules'
        if self.cursor.execute('delete from %s where pygr_id=%%s'
                               %self.tablename,(id,))<1:
            raise PygrDataNotFoundError('no resource %s in this database'%id)
    def registerServer(self,locationKey,serviceDict):
        'register the specified services to mysql database'
        n=0
        for id,(d,pdata) in serviceDict.items():
            n+=self.cursor.execute('replace into %s (pygr_id,location,docstring,user,creation_time,pickle_size,objdata) values (%%s,%%s,%%s,%%s,%%s,%%s,%%s)'
                                   % self.tablename,
                                   (id,locationKey,d['__doc__'],d['user'],
                                    d['creation_time'],d['pickle_size'],pdata))
        return n
    def setschema(self,id,attr,kwargs):
        'save a schema binding for id.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID=kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        kwdata=self.finder.dumps(kwargs)
        self.cursor.execute('replace into %s (pygr_id,location,objdata) values (%%s,%%s,%%s)'
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
    def dir(self,prefix,asDict=False,download=False):
        self.cursor.execute('select pygr_id,docstring,user,creation_time,pickle_size from %s where pygr_id like %%s'
                            % self.tablename,(prefix+'%',))
        d={}
        for l in self.cursor.fetchall():
            d[l[0]] = dict(__doc__=l[1],user=l[2],creation_time=l[3],pickle_size=l[4])
        if asDict:
            return d
        else:
            return [name for name in d]


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
    def __getitem__(self,id,download=False):
        'get an item from this resource database'
        s=self.db[id] # RAISES KeyError IF NOT PRESENT
        obj = self.finder.loads(s) # RUN THE UNPICKLER ON THE STRING
        try:
            obj.__doc__ = self.db['__doc__.'+id]['__doc__']
        except KeyError:
            pass
        return obj
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



class ResourceFinder(object):
    '''Primary interface for pygr.Data resource database access.  A single instance
    of this class is created upon import of the pygr.Data module, accessible as
    pygr.Data.getResource.  Users normally will have no need to create additional
    instances of this class themselves.'''
    def __init__(self,separator=',',saveDict=None,PYGRDATAPATH=None):
        self.db=None
        self.layer={}
        self.dbstr=''
        self.d={}
        self.schemaCache = {}
        self.separator=separator
        self.sourceIDs={}
        self.cursors=[]
        self.clear_pending()
        self.debug = False
        self.download = False
        if saveDict is not None:
            self.saveDict=saveDict # SAVE NEW LAYER NAMES HERE...
            self.update(PYGRDATAPATH) # LOAD RESOURCE DBs FROM PYGRDATAPATH
            del self.saveDict
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
    def update(self,PYGRDATAPATH=None):
        'get the latest list of resource databases'
        import os
        if PYGRDATAPATH is not None: # USE MANUALLY SUPPLIED SETTING
            self.PYGRDATAPATH  = PYGRDATAPATH
            self.d.clear() # DUMP LOADED RESOURCE CACHE
            self.dbstr = None # FORCE RELOAD
        else: # OBTAIN BEST SETTING
            PYGRDATAPATH = self.get_pygr_data_path()
        if self.dbstr!=PYGRDATAPATH: # LOAD NEW RESOURCE PYGRDATAPATH
            self.dbstr=PYGRDATAPATH
            self.db = []
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
                        dbpath = os.path.expanduser(dbpath)
                        rdb = ResourceDBShelve(dbpath,self)
                        if dbpath==os.path.expanduser('~') \
                               or dbpath.startswith(os.path.expanduser('~')+os.sep):
                            if 'my' not in self.layer:
                                self.layer['my'] = rdb
                        elif os.path.isabs(dbpath):
                            if 'system' not in self.layer:
                                self.layer['system'] = rdb
                        elif dbpath.split(os.sep)[0]==os.curdir:
                            if 'here' not in self.layer:
                                self.layer['here'] = rdb
                        elif 'subdir' not in self.layer:
                            self.layer['subdir'] = rdb
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
    def save_root_names(self,rootNames):
        'add resource path root to the module dictionary'
        if hasattr(self,'saveDict'): # ONLY SAVE IF INITIALIZING THE MODULE
            for name in rootNames:
                if name not in self.saveDict:
                    self.saveDict[name]=ResourcePath(name)
    def resourceDBiter(self,layer=None):
        'iterate over all available databases, read from PYGRDATAPATH env var.'
        if layer is not None: # USE THE SPECIFIED LAYER
            yield self.layer[layer]
            return
        self.update()
        if self.db is None or len(self.db)==0:
            raise ValueError('empty PYGRDATAPATH! Please check environment variable.')
        for db in self.db:
            yield db
    def loads(self,data,cursor=None):
        'unpickle from string, using persistent ID expansion'
        src=StringIO(data)
        unpickler=pickle.Unpickler(src)
        unpickler.persistent_load=self.persistent_load # WE PROVIDE PERSISTENT LOOKUP
        if cursor is not None: # PUSH OUR CURSOR ONTO THE STACK
            self.cursors.append(cursor)
        obj=unpickler.load() # ACTUALLY UNPICKLE THE DATA
        if cursor is not None: # POP OUR CURSOR STACK
            self.cursors.pop()
        return obj
    def dumps(self,obj,**kwargs):
        'pickle to string, using persistent ID encoding'
        src=StringIO()
        pickler=PygrPickler(src) # NEED OUR OWN PICKLER, TO USE persistent_id
        pickler.setRoot(obj,self.sourceIDs, # ROOT OF PICKLE TREE: SAVE EVEN IF persistent_id
                        **kwargs)
        pickler.dump(obj) # PICKLE IT
        return src.getvalue() # RETURN THE PICKLED FORM AS A STRING
    def persistent_load(self,persid):
        'check for PYGR_ID:... format and return the requested object'
        if persid.startswith('PYGR_ID:'):
            return self(persid[8:]) # RUN OUR STANDARD RESOURCE REQUEST PROCESS
        else: # UNKNOWN PERSISTENT ID... NOT FROM PYGR!
            raise pickle.UnpicklingError, 'Invalid persistent ID %s' % persid
    def getTableCursor(self,tablename):
        'try to get the desired table using our current resource database cursor, if any'
        try:
            cursor=self.cursors[-1]
        except IndexError:
            try:
                cursor = self.defaultCursor # USE IF WE HAVE ONE...
            except AttributeError: # TRY TO GET ONE...
                import sqlgraph
                try:
                    basename,cursor = sqlgraph.getNameCursor(tablename)
                    self.defaultCursor = cursor # SAVE FOR RE-USE
                except StandardError:
                    return None
        try: # MAKE SURE THIS CURSOR CAN PROVIDE tablename
            cursor.execute('describe %s' % tablename)
            return cursor # SUCCEEDED IN ACCESSING DESIRED TABLE
        except StandardError:
            return None
        
    def __call__(self,id,layer=None,debug=None,download=None,*args,**kwargs):
        'get the requested resource ID by searching all databases'
        try:
            return self.d[id] # USE OUR CACHED OBJECT
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
            obj = None
            for db in self.resourceDBiter(layer): # SEARCH ALL OF OUR DATABASES
                try:
                    obj = db.__getitem__(id,download) # TRY TO OBTAIN FROM THIS DATABASE
                    break # SUCCESS!  NOTHING MORE TO DO
                except (KeyError,IOError): # NOT IN THIS DB, FILES NOT ACCESSIBLE...
                    if self.debug: # PASS ON THE ACTUAL ERROR IMMEDIATELY
                        raise
            if obj is None:
                raise PygrDataNotFoundError('unable to find %s in PYGRDATAPATH' % id)
            if hasattr(obj,'_saveLocalBuild') and obj._saveLocalBuild:
                # SAVE AUTO BUILT RESOURCE TO LOCAL PYGR.DATA
                hasPending = self.has_pending() # any pending transaction?
                self.addResource(id, obj) # add to queue for commit
                obj._saveLocalBuild = False # NO NEED TO SAVE THIS AGAIN
                if hasPending:
                    print >>sys.stderr,'''Saving new resource %s to local pygr.Data...
You must use pygr.Data.save() to commit!
You are seeing this message because you appear to be in the
middle of a pygr.Data transaction.  Ordinarily pygr.Data would
automatically commit this new downloaded resource, but doing so
now would also commit your pending transaction, which you may
not be ready to do!''' % id
                else: # automatically save new resource
                    self.save_pending() # commit it
            else: # NORMAL USAGE
                obj._persistent_id = id  # MARK WITH ITS PERSISTENT ID
                self.d[id] = obj # SAVE TO OUR CACHE
            self.applySchema(id,obj) # BIND SHADOW ATTRIBUTES IF ANY
        finally: # RESTORE STATE BEFORE RAISING ANY EXCEPTION
            self.debug = debug_state
            self.download = download_state
        return obj
    def check_docstring(self,obj):
        'enforce requirement for docstring, by raising exception if not present'
        try:
            if obj.__doc__ is None or (hasattr(obj.__class__,'__doc__')
                                       and obj.__doc__==obj.__class__.__doc__):
                raise AttributeError
        except AttributeError:
            raise ValueError('to save a resource object, you MUST give it a __doc__ string attribute describing it!')
    def addResource(self,resID,obj,layer=None):
        'queue the object for saving to the specified database layer as <id>'
        self.check_docstring(obj)
        db = self.getLayer(layer) # VERIFY THE LAYER EXISTS
        if isinstance(db,ResourceDBClient): # THIS IS NOT WRITABLE!
            raise_illegal_save(db)
        obj._persistent_id = resID # MARK OBJECT WITH ITS PERSISTENT ID
        self.pendingData[resID] = (obj,layer) # ADD TO QUEUE
        try:
            self.rollbackData[resID] = self.d[resID]
        except KeyError:
            pass
        self.d[resID] = obj # SAVE TO OUR CACHE
    def addResourceDict(self,d,layer=None):
        'queue a dict of name:object pairs for saving to specified db layer'
        for k,v in d.items():
            self.addResource(k,v,layer)
    def queue_schema_obj(self,schemaPath,attr,layer,schemaObj):
        'add a schema object to the queue for saving to the specified database layer'
        resID = schemaPath.getPath(attr) # GET STRING ID
        self.pendingSchema[resID] = (schemaPath,attr,layer,schemaObj)
    def saveResource(self,resID,obj,layer=None):
        'save the object to the specified database layer as <id>'
        self.check_docstring(obj)
        if obj._persistent_id!=resID:
            raise PygrDataMismatchError('''The _persistent_id attribute for %s has changed!
If you changed it, shame on you!  Otherwise, this should not happen,
so report the reproducible steps to this error message as a bug report.''' % resID)
        db = self.getLayer(layer)
        db[resID] = obj # FINALLY, SAVE THE OBJECT TO THE DATABASE
        self.d[resID] = obj # SAVE TO OUR CACHE
    def has_pending(self):
        'return True if there are resources pending to be committed'
        return len(self.pendingData)>0 or len(self.pendingSchema)>0
    def get_pending_or_find(self,resID,**kwargs):
        'find resID even if only pending (not actually saved yet)'
        try: # 1st LOOK IN PENDING QUEUE
            return self.pendingData[resID][0]
        except KeyError:
            pass
        return self(resID,**kwargs)
    def save_pending(self,layer=None):
        'save any pending pygr.Data resources and schema'
        if layer is not None:
            self.getLayer(layer) # VERIFY THE LAYER EXISTS 
        if len(self.pendingData)>0 or len(self.pendingSchema)>0:
            d = self.pendingData
            schemaDict = self.pendingSchema
        elif len(self.lastData)>0 or len(self.lastSchema)>0:
            d = self.lastData
            schemaDict = self.lastSchema
        else:
            raise PygrDataEmptyError('there is no data queued for saving!')
        # NOW SAVE THE DATA
        for resID,(obj,layerGiven) in d.items():
            if layer is not None: # OVERRIDES ORIGINAL LAYER GIVEN ON OBJECT
                self.saveResource(resID,obj,layer)
            else:
                self.saveResource(resID,obj,layerGiven)
        # NEXT SAVE THE SCHEMA
        for schemaPath,attr,layerGiven,schemaObj in schemaDict.values():
            if layer is not None: # OVERRIDES ORIGINAL LAYER GIVEN ON OBJECT
                schemaObj.saveSchema(schemaPath,attr,layer=layer) # SAVE THIS SCHEMA INFO
            else:
                schemaObj.saveSchema(schemaPath,attr,layer=layerGiven) # USE ORIGINAL LAYER
        self.clear_pending() # FINALLY, CLEAN UP...
        self.lastData = d # KEEP IN CASE USER WANTS TO SAVE TO MULTIPLE LAYERS
        self.lastSchema = schemaDict
    def clear_pending(self):
        self.pendingData = {} # CLEAR THE PENDING QUEUE
        self.pendingSchema = {} # CLEAR THE PENDING QUEUE
        self.lastData = {}
        self.lastSchema = {}
        self.rollbackData = {} # CLEAR THE ROLLBACK CACHE
    def list_pending(self):
        'return tuple of pending data dictionary, pending schema'
        return list(self.pendingData),list(self.pendingSchema)
    def rollback(self):
        'dump any pending data without saving, and restore state of cache'
        if len(self.pendingData)==0 and len(self.pendingSchema)==0:
            raise PygrDataEmptyError('there is no data queued for saving!')
        self.d.update(self.rollbackData) # RESTORE THE ROLLBACK QUEUE
        self.clear_pending()
    def saveResourceDict(self,saveDict,layer=None):
        'save an entire set of resources, so dependency order is not an issue'
        for k,v in saveDict.items(): # CREATE DICT OF OBJECT IDs FOR DEPENDENCIES
            self.check_docstring(v)
            self.sourceIDs[id(v)]=k
        for k,v in saveDict.items(): # NOW ACTUALLY SAVE THE OBJECTS
            self.saveResource(k,v,layer) # CALL THE PICKLER...
        self.sourceIDs.clear() # CLEAR THE OBJECT ID DICTIONARY
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
    def newServer(self, name, serverClasses=None, clientHost=None,
                  withIndex=False, excludeClasses=None, downloadDB=None,
                  **kwargs):
        'construct server for the designated classes'
        if excludeClasses is None: # DEFAULT: NO POINT IN SERVING SQL TABLES...
            from sqlgraph import SQLTableBase,SQLGraphClustered
            excludeClasses = [SQLTableBase,SQLGraphClustered]
        if serverClasses is None: # DEFAULT TO ALL CLASSES WE KNOW HOW TO SERVE
            from seqdb import BlastDB,XMLRPCSequenceDB,BlastDBXMLRPC, \
                 AnnotationDB, AnnotationClient, AnnotationServer
            serverClasses=[(BlastDB,XMLRPCSequenceDB,BlastDBXMLRPC),
                           (AnnotationDB,AnnotationClient,AnnotationServer)]
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
                obj.url='http://%s:%d' % (clientHost,server.port)
                obj.name=id
            obj.__class__=clientKlass # CONVERT TO CLIENT CLASS FOR PICKLING
            self.client_dict_setitem(clientDict,id,obj)
            obj.__class__=serverKlass # CONVERT TO SERVER CLASS FOR SERVING
            server[id]=obj # ADD TO XMLRPC SERVER
        server.registrationData=clientDict # SAVE DATA FOR SERVER REGISTRATION
        if withIndex: # SERVE OUR OWN INDEX AS A STATIC, READ-ONLY INDEX
            myIndex=ResourceDBServer(name,readOnly=True,
                                     downloadDB=downloadDB) # CREATE EMPTY INDEX
            server['index']=myIndex # ADD TO OUR XMLRPC SERVER
            server.register('','',server=myIndex) # ADD OUR RESOURCES TO THE INDEX
        return server
    def client_dict_setitem(self,clientDict,k,obj,**kwargs):
        'save pickle and schema for obj into clientDict'
        pickleString = self.dumps(obj,**kwargs) # PICKLE THE CLIENT OBJECT, SAVE
        clientDict[k] = (self.get_info_dict(obj,pickleString),pickleString)
        try: # SAVE SCHEMA INFO AS WELL...
            clientDict['SCHEMA.'+k] = (dict(schema_version='1.0'),
                                       self.findSchema(k))
        except KeyError:
            pass # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO
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
        try: # GET SCHEMA FROM CACHE
            schema = self.schemaCache[id]
        except KeyError: # HMM, IT SHOULD BE CACHED!
            schema = self.findSchema(id) # OBTAIN FROM RESOURCE DB
            self.schemaCache[id] = schema # KEEP IT IN OUR CACHE
        try:
            schema = schema[attr] # GET SCHEMA FOR THIS SPECIFIC ATTRIBUTE
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
        self.schemaCache[id] = schema # KEEP THIS IN CACHE FOR SPEED
        for attr,rules in schema.items():
            if not attr.startswith('-'): # ONLY SHADOW REAL ATTRIBUTES
                self.shadowAttr(obj,attr,**rules)
    def shadowAttr(self,obj,attr,itemRule=False,**kwargs):
        'create a descriptor for the attr on the appropriate obj shadow class'
        try: # SEE IF OBJECT TELLS US TO SKIP THIS ATTRIBUTE
            return obj._ignoreShadowAttr[attr] # IF PRESENT, NOTHING TO DO
        except (AttributeError,KeyError):
            pass # PROCEED AS NORMAL
        from classutil import get_bound_subclass
        if itemRule: # SHOULD BIND TO ITEMS FROM obj DATABASE
            targetClass = get_bound_subclass(obj,'itemClass') # CLASS USED FOR CONSTRUCTING ITEMS
            descr=ItemDescriptor(attr,**kwargs)
        else: # SHOULD BIND DIRECTLY TO obj VIA ITS CLASS
            targetClass = get_bound_subclass(obj)
            descr=OneTimeDescriptor(attr,**kwargs)
        setattr(targetClass,attr,descr) # BIND descr TO targetClass.attr
        if itemRule:
            try: # BIND TO itemSliceClass TOO, IF IT EXISTS...
                targetClass = get_bound_subclass(obj,'itemSliceClass')
            except AttributeError:
                pass # NO itemSliceClass, SO SKIP
            else: # BIND TO itemSliceClass
                setattr(targetClass,attr,descr)
        if attr=='inverseDB': # ADD SHADOW __invert__ TO ACCESS THIS
            addSpecialMethod(obj,'__invert__',getInverseDB)
    def addSchema(self,name,schemaObj,layer=None):
        'use this public method to assign a schema relation object to a pygr.Data resource name'
        l = name.split('.')
        schemaPath = SchemaPath('.'.join(l[:-1]),layer)
        setattr(schemaPath,l[-1],schemaObj)
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
    def delSchema(self,id,layer=None):
        'delete schema bindings TO and FROM this resource ID'
        db=self.getLayer(layer)
        d=db.getschema(id) # GET THE EXISTING SCHEMA
        self.schemaCache.clear() # THIS IS MORE AGGRESSIVE THAN NEEDED... COULD BE REFINED
        for attr,obj in d.items():
            if attr.startswith('-'): # A SCHEMA OBJECT
                obj.delschema(db) # DELETE ITS SCHEMA RELATIONS
            db.delschema(id,attr) # DELETE THIS ATTRIBUTE SCHEMA RULE
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
    def get_info_dict(self,obj,pickleString):
        'get dict of standard info about a resource'
        import os,datetime
        d = dict(creation_time=datetime.datetime.now(),
                 pickle_size=len(pickleString),__doc__=obj.__doc__)
        try:
            d['user'] = os.environ['USER']
        except KeyError:
            d['user'] = None
        return d
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
            schema.saveSchema # VERIFY THAT THIS LOOKS LIKE A SCHEMA OBJECT
        except AttributeError:
            raise ValueError('not a valid schema object!')
        getResource.queue_schema_obj(self,name,self._layer,schema) # QUEUE IT
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
        self.targetID = getID(target)
    def schemaDict(self):
        return dict(targetID=self.targetID)
    def saveSchema(self,source,attr,layer=None,**kwargs):
        d = self.schemaDict()
        d.update(kwargs) # ADD USER-SUPPLIED ARGS
        try: # IF kwargs SUPPLIED A TARGET, SAVE ITS ID
            d['targetID'] = getID(d['targetDB'])
            del d['targetDB']
        except KeyError:
            pass
        getResource.saveSchema(getID(source),attr,d,layer)

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
    def save_graph_bindings(self,graphDB,attr,layer=None):
        'save standard schema bindings to graphDB attributes sourceDB, targetDB, edgeDB'
        graphDB = graphDB.getPath(attr) # GET STRING ID FOR source
        self.name = graphDB
        getResource.saveSchemaEdge(self,layer) #SAVE THIS RULE
        b = DirectRelation(self.sourceDB) # SAVE sourceDB BINDING
        b.saveSchema(graphDB,'sourceDB',layer)
        b = DirectRelation(self.targetDB) # SAVE targetDB BINDING
        b.saveSchema(graphDB,'targetDB',layer)
        if self.edgeDB is not None: # SAVE edgeDB BINDING
            b = DirectRelation(self.edgeDB)
            b.saveSchema(graphDB,'edgeDB',layer)
        return graphDB
    def saveSchema(self,path,attr,layer=None):
        'save schema bindings associated with this rule'
        graphDB = self.save_graph_bindings(path,attr,layer)
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
                    b.saveSchema(bindObj[i],self.bindAttrs[i],
                                 layer,**bindArgs[i])
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
    def saveSchema(self,source,attr,layer=None,**kwargs):
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
    __invert__ = standard_invert


class ForeignKeyMap(object):
    'provide mapping interface to a foreign key accessible via a container'
    def __init__(self,foreignKey,sourceDB=None,targetDB=None):
        self.keyName=foreignKey
        self.sourceDB=sourceDB
        self.targetDB=targetDB
    def __getitem__(self,k):
        return [x for x in self.targetDB.foreignKey(self.keyName,k.id)]
    __invert__ = standard_invert
    _inverseClass = ForeignKeyMapInverse



###########################################################
schema = SchemaPath() # ROOT OF OUR SCHEMA NAMESPACE

# PROVIDE TOP-LEVEL NAMES IN OUR RESOURCE HIERARCHY
Bio = ResourcePath('Bio')
Life = ResourcePath('Life')


# TOP-LEVEL NAMES FOR STANDARDIZED LAYERS
here = ResourceLayer('here')
my = ResourceLayer('my')
system = ResourceLayer('system')
subdir = ResourceLayer('subdir')
remote = ResourceLayer('remote')
MySQL = ResourceLayer('MySQL')

################# CREATE AN INTERFACE TO THE RESOURCE DATABASE
def check_test_env():
    try:
        return pygrDataPath
    except NameError:
        return None
try:
    getResource
except NameError:
    pass
else: # HMM. THIS MUST BE A reload() OF THIS MODULE
    if len(getResource.pendingData)>0 or len(getResource.pendingSchema)>0:
        print >>sys.stderr,'''
WARNING: You appear to have forced a reload() of pygr.Data without first
having called pygr.Data.save() on the new data resources that you
added to pygr.Data.  This would permanently strand the pygr.Data
resources that you added but forgot to save.  Therefore we are automatically
calling pygr.Data.save() for you.  To avoid this warning in the
future, remember you must always call pygr.Data.save() to save the
data that you added to pygr.Data!'''
        try:
            getResource.save_pending() # SAVE USER'S DATA FOR HIM...
        except StandardError: # TRAP ERRORS SO IMPORT OF THIS MODULE WILL NOT DIE!
            import traceback
            traceback.print_exc(10,sys.stderr) # JUST PRINT TRACEBACK
            print >>sys.stderr,'''
An error occurred during the saving of your added resources.
This should not happen.  Please file a bug report.
This error WILL NOT prevent successful reload of this module.
Continuing with reload...'''

getResource = ResourceFinder(saveDict=locals(),PYGRDATAPATH=check_test_env())
addResource = getResource.addResource
addSchema = getResource.addSchema
deleteResource = getResource.deleteResource
dir = getResource.dir
newServer = getResource.newServer
save = getResource.save_pending
rollback = getResource.rollback
list_pending = getResource.list_pending
loads = getResource.loads
dumps = getResource.dumps

try:
    firstLoad
except NameError:
    firstLoad = True
    def save_on_exit(): # THIS SHOULD BE RUN ON INTERPRETER EXIT
        'try to save any pygr.Data that the user forgot...'
        getResource.__del__()
    import atexit
    atexit.register(save_on_exit) # ONLY REGISTER ONCE, EVEN IF MODULE RELOADED MANY TIMES
else:
    firstLoad = False
try:
    nonPortableClasses
except NameError: # DEFAULT LIST OF CLASSES NOT PORTABLE TO REMOTE CLIENTS
    from classutil import SourceFileName
    nonPortableClasses = [SourceFileName]


