
import datetime
import os
import pickle
import re
import sys
import UserDict
from StringIO import StringIO
from mapping import Collection, Mapping, Graph
from classutil import open_shelve, standard_invert, get_bound_subclass, \
     SourceFileName
from coordinator import XMLRPCServerBase


try:
    nonPortableClasses
except NameError: # DEFAULT LIST OF CLASSES NOT PORTABLE TO REMOTE CLIENTS
    nonPortableClasses = [SourceFileName]


class OneTimeDescriptor(object):
    'provides shadow attribute based on schema'

    def __init__(self, attrName, mdb, **kwargs):
        self.attr=attrName
        self.mdb = mdb

    def __get__(self, obj, objtype):
        try:
            resID = obj._persistent_id # GET ITS RESOURCE ID
        except AttributeError:
            raise AttributeError('attempt to access worldbase attr on \
                                 non-worldbase object')
        target = self.mdb.get_schema_attr(resID, self.attr) #get from mdb
        # Save in __dict__ to evade __setattr__.
        obj.__dict__[self.attr] = target
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
            raise AttributeError('attempt to access worldbase attr on \
                                 non-worldbase object')
        targetDict = self.mdb.get_schema_attr(resID, self.attr)
        if self.invert:
            targetDict = ~targetDict
        if self.getEdges:
            targetDict = targetDict.edges
        return targetDict

    def __get__(self, obj, objtype):
        targetDict = self.get_target(obj)
        if self.mapAttr is not None: # USE mapAttr TO GET ID FOR MAPPING obj
            obj_id = getattr(obj, self.mapAttr)
            if obj_id is None: # None MAPS TO None, SO RETURN IMMEDIATELY
                return None # DON'T BOTHER CACHING THIS
            result = targetDict[obj_id] # MAP USING THE SPECIFIED MAPPING
        else:
            result = targetDict[obj] # NOW PERFORM MAPPING IN THAT RESOURCE...
        if self.targetAttr is not None:
            # Get attribute of the result.
            result = getattr(result, self.targetAttr)
        obj.__dict__[self.attr] = result # CACHE IN THE __dict__
        return result


class ItemDescriptorRW(ItemDescriptor):

    def __set__(self, obj, newTarget):
        if not self.uniqueMapping:
            raise WorldbaseSchemaError(
'''You attempted to directly assign to a graph mapping (x.graph = y)!
Instead, treat the graph like a dictionary: x.graph[y] = edgeInfo''')
        targetDict = self.get_target(obj)
        targetDict[obj] = newTarget
        obj.__dict__[self.attr] = newTarget # CACHE IN THE __dict__


class ForwardingDescriptor(object):
    'forward an attribute request to item from another container'

    def __init__(self, targetDB, attr):
        self.targetDB = targetDB # CONTAINER TO GET ITEMS FROM
        self.attr = attr # ATTRIBUTE TO MAP TO

    def __get__(self, obj, objtype):
        target = self.targetDB[obj.id] # GET target FROM CONTAINER
        return getattr(target, self.attr) # GET DESIRED ATTRIBUTE


class SpecialMethodDescriptor(object):
    'enables shadowing of special methods like __invert__'

    def __init__(self, attrName):
        self.attr = attrName

    def __get__(self, obj, objtype):
        try:
            return obj.__dict__[self.attr]
        except KeyError:
            raise AttributeError('%s has no method %s' % (obj, self.attr))


def addSpecialMethod(obj, attr, f):
    '''bind function f as special method attr on obj.
    obj cannot be an builtin or extension class
    (if so, just subclass it)'''
    import new
    m=new.instancemethod(f, obj, obj.__class__)
    try:
        if getattr(obj, attr) == m: # ALREADY BOUND TO f
            return # ALREADY BOUND, NOTHING FURTHER TO DO
    except AttributeError:
        pass
    else:
        raise AttributeError('%s already bound to a different function' % attr)
    setattr(obj, attr, m) # SAVE BOUND METHOD TO __dict__
    # This does forwarding.
    setattr(obj.__class__, attr, SpecialMethodDescriptor(attr))


def getInverseDB(self):
    'default shadow __invert__ method'
    return self.inverseDB # TRIGGER CONSTRUCTION OF THE TARGET RESOURCE


class WorldbaseNotPortableError(ValueError):
    '''indicates that object has a local data dependency and cannot be
    transferred to a remote client'''
    pass


class WorldbaseNotFoundError(KeyError):
    '''unable to find a loadable resource for the requested worldbase
    identifier from WORLDBASEPATH'''
    pass


class WorldbaseMismatchError(ValueError):
    '''_persistent_id attr on object no longer matches its assigned
    worldbase ID?!?'''
    pass


class WorldbaseEmptyError(ValueError):
    "user hasn't queued anything, so trying to save or rollback is an error"
    pass


class WorldbaseReadOnlyError(ValueError):
    'attempt to write data to a read-only resource database'
    pass


class WorldbaseSchemaError(ValueError):
    "attempt to set attribute to an object not in the database bound by schema"
    pass


class WorldbaseNoModuleError(pickle.PickleError):
    'attempt to pickle a class from a non-importable module'
    pass


class PygrPickler(pickle.Pickler):

    def persistent_id(self, obj):
        '''convert objects with _persistent_id to PYGR_ID strings
        during pickling'''
        import types
        try:
            # Check for unpicklable class (i.e. not loaded
            # via a module import).
            if isinstance(obj, types.TypeType) and \
               obj.__module__ == '__main__':
                raise WorldbaseNoModuleError(
'''You cannot pickle a class from __main__!
To make this class (%s) picklable, it must be loaded via a regular
import statement.''' % obj.__name__)
        except AttributeError:
            pass
        try:
            if not isinstance(obj, types.TypeType) and obj is not self.root:
                try:
                    return 'PYGR_ID:%s' % self.sourceIDs[id(obj)]
                except KeyError:
                    if obj._persistent_id is not None:
                        return 'PYGR_ID:%s' % obj._persistent_id
        except AttributeError:
            pass
        for klass in self.badClasses: # CHECK FOR LOCAL DEPENDENCIES
            if isinstance(obj, klass):
                raise WorldbaseNotPortableError(
'''this object has a local data dependency and cannnot be transferred
to a remote client''')
        return None

    def setRoot(self, obj, sourceIDs={}, badClasses=()):
        '''set obj as root of pickling tree: genuinely pickle it
        (not just its id)'''
        self.root = obj
        self.sourceIDs = sourceIDs
        self.badClasses = badClasses


class MetabaseServer(object):
    'simple XMLRPC resource database server'
    xmlrpc_methods = {'getResource': 0, 'registerServer': 0, 'delResource': 0,
                      'getName': 0, 'dir': 0, 'get_version': 0}
    _pygr_data_version = (0, 1, 0)

    def __init__(self, name, readOnly=True, downloadDB=None):
        self.name = name
        self.d = {}
        self.docs = {}
        self.downloadDB = {}
        self.downloadDocs = {}
        if readOnly: # LOCK THE INDEX.  DON'T ACCEPT FOREIGN DATA!!
            # Only allow these methods!
            self.xmlrpc_methods = {'getResource': 0, 'getName': 0, 'dir': 0,
                                   'get_version': 0}
        if downloadDB is not None:
            self.read_download_db(downloadDB)

    def read_download_db(self, filename, location='default'):
        'add the designated resource DB shelve to our downloadable resources'
        d = open_shelve(filename, 'r')
        for k, v in d.items():
            if k.startswith('__doc__.'): # SAVE DOC INFO FOR THIS ID
                self.downloadDocs[k[8:]] = v
            else: # SAVE OBJECT INFO
                self.downloadDB.setdefault(k, {})[location] = v
        d.close()

    def getName(self):
        'return layer name for this server'
        return self.name

    def get_db(self, download):
        if download: # USE SEPARATE DOWNLOAD DATABASE
            return (self.downloadDB, self.downloadDocs)
        else: # USE REGULAR XMLRPC SERVICES DATABASE
            return (self.d, self.docs)

    def getResource(self, id, download=False):
        'return dict of location:pickleData for requested ID'
        db, docs = self.get_db(download)
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

    def registerServer(self, locationKey, serviceDict):
        '''add services in serviceDict to this server under the
        specified location'''
        n = 0
        for id, (infoDict, pdata) in serviceDict.items():
            self.d.setdefault(id, {})[locationKey] = pdata # SAVE RESOURCE
            if infoDict is not None:
                self.docs[id] = infoDict
            n += 1
        return n  # COUNT OF SUCCESSFULLY REGISTERED SERVICES

    def delResource(self, id, locationKey):
        'delete the specified resource under the specified location'
        try:
            del self.d[id][locationKey]
            if len(self.d[id]) == 0:
                del self.docs[id]
        except KeyError:
            pass
        return ''  # DUMMY RETURN VALUE FOR XMLRPC

    def dir(self, pattern, asDict=False, matchType='p', download=False):
        'return list or dict of resources matching the specified string'
        db, docs = self.get_db(download)
        if matchType == 'r':
            pattern = re.compile(pattern)
        l = []
        for name in db: # FIND ALL ITEMS WITH MATCHING NAME
            if matchType == 'p' and name.startswith(pattern) or \
               matchType == 'r' and pattern.search(name):
                l.append(name)
        if asDict: # RETURN INFO DICT FOR EACH ITEM
            d = {}
            for name in l:
                d[name] = docs.get(name, {})
            return d
        return l

    def get_version(self):
        return self._pygr_data_version


def raise_illegal_save(self, *l):
    raise WorldbaseReadOnlyError(
'''You cannot save data to a remote XMLRPC server.
Give a user-editable resource database as the first entry
in your WORLDBASEPATH!''')


class XMLRPCMetabase(object):
    'client interface to remote XMLRPC resource database'

    def __init__(self, url, mdb, **kwargs):
        from coordinator import get_connection
        self.server = get_connection(url, 'index')
        self.url=url
        self.mdb = mdb
        self.zoneName = self.server.getName()
        self.writeable = False

    def find_resource(self, id, download=False):
        'get pickledata,docstring for this resource ID from server'
        if download: # SPECIFICALLY ASK SERVER FOR DOWNLOADABLE RESOURCES
            d = self.server.getResource(id, download)
        else: # NORMAL MODE TO GET XMLRPC SERVICES
            d = self.server.getResource(id)
        if d == '':
            raise WorldbaseNotFoundError('resource %s not found' % id)
        try:
            docstring = d['__doc__']
            del d['__doc__']
        except KeyError:
            docstring = None
        for location, objdata in d.items(): # return the first resource found
            return objdata, docstring
        raise KeyError('unable to find %s from remote services' % id)

    def registerServer(self, locationKey, serviceDict):
        'forward registration to the server'
        return self.server.registerServer(locationKey, serviceDict)

    def getschema(self, id):
        'return dict of {attr: {args}}'
        d = self.server.getResource('SCHEMA.' + id)
        if d == '': # NO SCHEMA INFORMATION FOUND
            raise KeyError
        for schemaDict in d.values():
            return schemaDict # HAND BACK FIRST SCHEMA WE FIND
        raise KeyError

    def dir(self, pattern, matchType='p', asDict=False, download=False):
        'return list or dict of resources matching the specified string'
        if download:
            return self.server.dir(pattern, asDict, matchType, download)
        else:
            return self.server.dir(pattern, asDict, matchType)

    __setitem__ = raise_illegal_save # RAISE USEFUL EXPLANATORY ERROR MESSAGE
    __delitem__ = raise_illegal_save
    setschema = raise_illegal_save
    delschema = raise_illegal_save


class MySQLMetabase(object):
    '''To create a new resource table, call:
    MySQLMetabase("DBNAME.TABLENAME", mdb, createLayer="LAYERNAME")
    where DBNAME is the name of your database, TABLENAME is the name
    of the table you want to create, and LAYERNAME is the layer name
    you want to assign it'''
    _pygr_data_version = (0, 1, 0)

    def __init__(self, tablename, mdb, createLayer=None, newZone=None,
                 **kwargs):
        from sqlgraph import get_name_cursor, SQLGraph
        self.tablename, self.cursor, self.serverInfo = \
                get_name_cursor(tablename)
        self.mdb = mdb
        self.writeable = True
        self.rootNames = {}
        # Separate table for schema graph.
        schemaTable = self.tablename + '_schema'
        if createLayer is None:
            createLayer = newZone # use the new parameter
        if createLayer is not None: # CREATE DATABASE FROM SCRATCH
            creation_time = datetime.datetime.now()
            self.cursor.execute('drop table if exists %s' % self.tablename)
            self.cursor.execute('create table %s (pygr_id varchar(255) not \
                                null,location varchar(255) not null,docstring \
                                varchar(255),user varchar(255),creation_time \
                                datetime,pickle_size int,security_code bigint,\
                                info_blob text,objdata text not null,\
                                unique(pygr_id,location))' % self.tablename)
            self.cursor.execute('insert into %s (pygr_id,location,\
                                creation_time,objdata) values (%%s,%%s,%%s,\
                                %%s)' % self.tablename,
                                ('PYGRLAYERNAME', createLayer, creation_time,
                                 'a'))
            # Save version stamp.
            self.cursor.execute('insert into %s (pygr_id,location,objdata) \
                                values (%%s,%%s,%%s)' % self.tablename,
                                ('0version', '%d.%d.%d'
                                 % self._pygr_data_version, 'a'))
            self.zoneName = createLayer
            self.cursor.execute('drop table if exists %s' % schemaTable)
            self.cursor.execute('create table %s (source_id varchar(255) not \
                                null,target_id varchar(255),edge_id \
                                varchar(255),unique(source_id,target_id))'
                                % schemaTable)
        else:
            try:
                n = self.cursor.execute('select location from %s where \
                                        pygr_id=%%s' % self.tablename,
                                        ('PYGRLAYERNAME', ))
            except StandardError:
                print >>sys.stderr, '''%s
Database table %s appears to be missing or has no layer name!
To create this table, call
worldbase.MySQLMetabase("%s", createLayer=<LAYERNAME>)
where <LAYERNAME> is the layer name you want to assign it.
%s''' % ('!' * 40, self.tablename, self.tablename, '!' * 40)
                raise
            if n > 0:
                # Get layer name from the db.
                self.zoneName = self.cursor.fetchone()[0]
            if self.cursor.execute('select location from %s where pygr_id=%%s'
                                   % self.tablename, ('0root', )) > 0:
                for row in self.cursor.fetchall():
                    self.rootNames[row[0]] = None
                mdb.save_root_names(self.rootNames)
        self.graph = SQLGraph(schemaTable, self.cursor, attrAlias=
                              dict(source_id='source_id',
                                   target_id='target_id', edge_id='edge_id'),
                              simpleKeys=True, unpack_edge=SchemaEdge(self))

    def save_root_name(self, name):
        self.rootNames[name] = None
        self.cursor.execute('insert into %s (pygr_id,location,objdata) values \
                            (%%s,%%s,%%s)' % self.tablename, ('0root', name,
                                                              'a'))

    def find_resource(self, id, download=False):
        'get construction rule from mysql, and attempt to construct'
        self.cursor.execute('select location,objdata,docstring from %s where \
                            pygr_id=%%s' % self.tablename, (id, ))
        for location, objdata, docstring in self.cursor.fetchall():
            return objdata, docstring # return first resource found
        raise WorldbaseNotFoundError('unable to construct %s from remote \
                                     services')

    def __setitem__(self, id, obj):
        'add an object to this resource database'
        s = dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        d = get_info_dict(obj, s)
        self.cursor.execute('replace into %s (pygr_id,location,docstring,user,\
                            creation_time,pickle_size,objdata) values (%%s,\
                            %%s,%%s,%%s,%%s,%%s,%%s)' % self.tablename,
                            (id, 'mysql:' + self.tablename, obj.__doc__,
                             d['user'], d['creation_time'], d['pickle_size'],
                             s))
        root = id.split('.')[0]
        if root not in self.rootNames:
            self.save_root_name(root)

    def __delitem__(self, id):
        'delete this resource and its schema rules'
        if self.cursor.execute('delete from %s where pygr_id=%%s'
                               % self.tablename, (id, )) < 1:
            raise WorldbaseNotFoundError('no resource %s in this database'
                                         % id)

    def registerServer(self, locationKey, serviceDict):
        'register the specified services to mysql database'
        n = 0
        for id, (d, pdata) in serviceDict.items():
            n+=self.cursor.execute('replace into %s (pygr_id,location,\
                                   docstring,user,creation_time,pickle_size,\
                                   objdata) values (%%s,%%s,%%s,%%s,%%s,%%s,\
                                   %%s)' % self.tablename,
                                   (id, locationKey, d['__doc__'], d['user'],
                                    d['creation_time'], d['pickle_size'],
                                    pdata))
        return n

    def setschema(self, id, attr, kwargs):
        'save a schema binding for id.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID = kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        kwdata = dumps(kwargs)
        self.cursor.execute('replace into %s (pygr_id,location,objdata) \
                            values (%%s,%%s,%%s)' % self.tablename,
                            ('SCHEMA.' + id, attr, kwdata))

    def delschema(self, id, attr):
        'delete schema binding for id.attr'
        self.cursor.execute('delete from %s where pygr_id=%%s and location=%%s'
                            % self.tablename, ('SCHEMA.' + id, attr))

    def getschema(self, id):
        'return dict of {attr:{args}}'
        d = {}
        self.cursor.execute('select location,objdata from %s where pygr_id=%%s'
                            % self.tablename, ('SCHEMA.' + id, ))
        for attr, objData in self.cursor.fetchall():
            d[attr] = self.mdb.loads(objData)
        return d

    def dir(self, pattern, matchType='p', asDict=False, download=False):
        'return list or dict of resources matching the specified string'

        if matchType == 'r':
            self.cursor.execute('select pygr_id,docstring,user,creation_time,\
                                pickle_size from %s where pygr_id regexp %%s'
                                % self.tablename, (pattern, ))
        elif matchType == 'p':
            self.cursor.execute('select pygr_id,docstring,user,creation_time,\
                                pickle_size from %s where pygr_id like %%s'
                                % self.tablename, (pattern + '%', ))
        else:
            # Exit now to avoid fetching rows with no query executed
            if asDict:
                return {}
            else:
                return []

        d = {}
        for l in self.cursor.fetchall():
            d[l[0]] = dict(__doc__=l[1], user=l[2], creation_time=l[3],
                           pickle_size=l[4])
        if asDict:
            return d
        else:
            return [name for name in d]


class SchemaEdge(object):
    'provides unpack_edge method for schema graph storage'

    def __init__(self, schemaDB):
        self.schemaDB = schemaDB

    def __call__(self, edgeID):
        'get the actual schema object describing this ID'
        return self.schemaDB.getschema(edgeID)['-schemaEdge']


class ResourceDBGraphDescr(object):
    'this property provides graph interface to schema'

    def __get__(self, obj, objtype):
        g = Graph(filename=obj.dbpath + '_schema', mode='cw', writeNow=True,
                  simpleKeys=True, unpack_edge=SchemaEdge(obj))
        obj.graph = g
        return g


class ShelveMetabase(object):
    '''BerkeleyDB-based storage of worldbase resource databases, using
    the python shelve module.  Users will not need to create instances
    of this class themselves, as worldbase automatically creates one for
    each appropriate entry in your WORLDBASEPATH; if the corresponding
    database file does not already exist, it is automatically created
    for you.'''
    _pygr_data_version = (0, 1, 0)
    graph = ResourceDBGraphDescr() # INTERFACE TO SCHEMA GRAPH

    def __init__(self, dbpath, mdb, mode='r', newZone=None, **kwargs):
        import anydbm
        self.dbpath = os.path.join(dbpath, '.pygr_data') # CONSTRUCT FILENAME
        self.mdb = mdb
        self.writeable = True # can write to this storage
        self.zoneName = None
        try: # OPEN DATABASE FOR READING
            self.db = open_shelve(self.dbpath, mode)
            try:
                mdb.save_root_names(self.db['0root'])
            except KeyError:
                pass
            try:
                self.zoneName = self.db['0zoneName']
            except KeyError:
                pass
        except anydbm.error: # CREATE NEW FILE IF NEEDED
            self.db = open_shelve(self.dbpath, 'c')
            self.db['0version'] = self._pygr_data_version # SAVE VERSION STAMP
            self.db['0root'] = {}
            if newZone is not None:
                self.db['0zoneName'] = newZone
                self.zoneName = newZone

    def reopen(self, mode):
        self.db.close()
        self.db = open_shelve(self.dbpath, mode)

    def find_resource(self, resID, download=False):
        'get an item from this resource database'
        objdata = self.db[resID] # RAISES KeyError IF NOT PRESENT
        try:
            return objdata, self.db['__doc__.' + resID]['__doc__']
        except KeyError:
            return objdata, None

    def __setitem__(self, resID, obj):
        'add an object to this resource database'
        s = dumps(obj) # PICKLE obj AND ITS DEPENDENCIES
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        try:
            self.db[resID] = s # SAVE TO OUR SHELVE FILE
            self.db['__doc__.' + resID] = get_info_dict(obj, s)
            root = resID.split('.')[0] # SEE IF ROOT NAME IS IN THIS SHELVE
            d = self.db.get('0root', {})
            if root not in d:
                d[root] = None # ADD NEW ENTRY
                self.db['0root'] = d # SAVE BACK TO SHELVE
        finally:
            self.reopen('r') # REOPEN READ-ONLY

    def __delitem__(self, resID):
        'delete this item from the database, with a modicum of safety'
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        try:
            try:
                del self.db[resID] # DELETE THE SPECIFIED RULE
            except KeyError:
                raise WorldbaseNotFoundError('ID %s not found in %s'
                                            % (resID, self.dbpath))
            try:
                del self.db['__doc__.' + resID]
            except KeyError:
                pass
        finally:
            self.reopen('r') # REOPEN READ-ONLY

    def dir(self, pattern, matchType='p', asDict=False, download=False):
        'generate all item IDs matching the specified pattern'
        if matchType == 'r':
            pattern = re.compile(pattern)
        l = []
        for name in self.db:
            if matchType == 'p' and name.startswith(pattern) or \
               matchType == 'r' and pattern.search(name):
                l.append(name)
        if asDict:
            d = {}
            for name in l:
                d[name] = self.db.get('__doc__.' + name, None)
            return d
        return l

    def setschema(self, resID, attr, kwargs):
        'save a schema binding for resID.attr --> targetID'
        if not attr.startswith('-'): # REAL ATTRIBUTE
            targetID = kwargs['targetID'] # RAISES KeyError IF NOT PRESENT
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        d = self.db.get('SCHEMA.' + resID, {})
        d[attr] = kwargs # SAVE THIS SCHEMA RULE
        self.db['SCHEMA.' + resID] = d # FORCE shelve TO RESAVE BACK
        self.reopen('r')  # REOPEN READ-ONLY

    def getschema(self, resID):
        'return dict of {attr:{args}}'
        return self.db['SCHEMA.' + resID]

    def delschema(self, resID, attr):
        'delete schema binding for resID.attr'
        self.reopen('w')  # OPEN BRIEFLY IN WRITE MODE
        d=self.db['SCHEMA.' + resID]
        del d[attr]
        self.db['SCHEMA.' + resID] = d # FORCE shelve TO RESAVE BACK
        self.reopen('r')  # REOPEN READ-ONLY

    def __del__(self):
        'close the shelve file when finished'
        self.db.close()


def dumps(obj, **kwargs):
    'pickle to string, using persistent ID encoding'
    src = StringIO()
    pickler = PygrPickler(src) # NEED OUR OWN PICKLER, TO USE persistent_id
    # Root of pickle tree: save even if persistent_id.
    pickler.setRoot(obj, **kwargs)
    pickler.dump(obj) # PICKLE IT
    return src.getvalue() # RETURN THE PICKLED FORM AS A STRING


def get_info_dict(obj, pickleString):
    'get dict of standard info about a resource'
    d = dict(creation_time=datetime.datetime.now(),
             pickle_size=len(pickleString), __doc__=obj.__doc__)
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

    def load(self, resID, objdata, docstring):
        'load the pickled data and all its dependencies'
        obj = self.loads(objdata)
        obj.__doc__ = docstring
        if hasattr(obj, '_saveLocalBuild') and obj._saveLocalBuild:
            saver = self.writer.saver # mdb in which to record local copy
            # SAVE AUTO BUILT RESOURCE TO LOCAL PYGR.DATA
            hasPending = saver.has_pending() # any pending transaction?
            saver.add_resource(resID, obj) # add to queue for commit
            obj._saveLocalBuild = False # NO NEED TO SAVE THIS AGAIN
            if hasPending:
                print >>sys.stderr, \
'''Saving new resource %s to local worldbase...
You must use worldbase.commit() to commit!
You are seeing this message because you appear to be in the middle
of a worldbase transaction.  Ordinarily worldbase would automatically commit
this new downloaded resource, but doing so now would also commit your pending
transaction, which you may not be ready to do!''' % resID
            else: # automatically save new resource
                saver.save_pending() # commit it
        else: # NORMAL USAGE
            obj._persistent_id = resID  # MARK WITH ITS PERSISTENT ID
        self.resourceCache[resID] = obj # SAVE TO OUR CACHE
        self.bind_schema(resID, obj) # BIND SHADOW ATTRIBUTES IF ANY
        return obj

    def loads(self, data):
        'unpickle from string, using persistent ID expansion'
        src = StringIO(data)
        unpickler = pickle.Unpickler(src)
        # We provide persistent lookup.
        unpickler.persistent_load = self.persistent_load
        obj = unpickler.load() # ACTUALLY UNPICKLE THE DATA
        return obj

    def __call__(self, resID, debug=None, download=None, *args, **kwargs):
        'get the requested resource ID by searching all databases'
        try:
            return self.resourceCache[resID] # USE OUR CACHED OBJECT
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
            self.update(debug=self.debug, keepCurrentPath=True) # load if empty
            for objdata, docstr in self.find_resource(resID, download):
                try:
                    obj = self.load(resID, objdata, docstr)
                    break
                except (KeyError, IOError):
                    # Not in this DB; files not accessible...
                    if self.debug: # PASS ON THE ACTUAL ERROR IMMEDIATELY
                        raise
        finally: # RESTORE STATE BEFORE RAISING ANY EXCEPTION
            self.debug = debug_state
            self.download = download_state
        self.resourceCache[resID] = obj # save to our cache
        return obj

    def bind_schema(self, resID, obj):
        'if this resource ID has any schema, bind its attrs to class'
        try:
            schema = self.getschema(resID)
        except KeyError:
            return # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO
        self.resourceCache.schemaCache[resID] = schema # cache for speed
        for attr, rules in schema.items():
            if not attr.startswith('-'): # only bind real attributes
                self.bind_property(obj, attr, **rules)

    def bind_property(self, obj, attr, itemRule=False, **kwargs):
        'create a descriptor for the attr on the appropriate obj class'
        try: # SEE IF OBJECT TELLS US TO SKIP THIS ATTRIBUTE
            return obj._ignoreShadowAttr[attr] # IF PRESENT, NOTHING TO DO
        except (AttributeError, KeyError):
            pass # PROCEED AS NORMAL
        if itemRule: # SHOULD BIND TO ITEMS FROM obj DATABASE
            # Class used for constructing items.
            targetClass = get_bound_subclass(obj, 'itemClass')
            descr = ItemDescriptor(attr, self, **kwargs)
        else: # SHOULD BIND DIRECTLY TO obj VIA ITS CLASS
            targetClass = get_bound_subclass(obj)
            descr = OneTimeDescriptor(attr, self, **kwargs)
        setattr(targetClass, attr, descr) # BIND descr TO targetClass.attr
        if itemRule:
            try: # BIND TO itemSliceClass TOO, IF IT EXISTS...
                targetClass = get_bound_subclass(obj, 'itemSliceClass')
            except AttributeError:
                pass # NO itemSliceClass, SO SKIP
            else: # BIND TO itemSliceClass
                setattr(targetClass, attr, descr)
        if attr == 'inverseDB': # ADD SHADOW __invert__ TO ACCESS THIS
            addSpecialMethod(obj, '__invert__', getInverseDB)

    def get_schema_attr(self, resID, attr):
        'actually retrieve the desired schema attribute'
        try: # GET SCHEMA FROM CACHE
            schema = self.resourceCache.schemaCache[resID]
        except KeyError:
            # Hmm, it should be cached! Obtain from resource DB and cache.
            schema = self.getschema(resID)
            self.resourceCache.schemaCache[resID] = schema
        try:
            schema = schema[attr] # GET SCHEMA FOR THIS SPECIFIC ATTRIBUTE
        except KeyError:
            raise AttributeError('no worldbase schema info for %s.%s' \
                                 % (resID, attr))
        targetID = schema['targetID'] # GET THE RESOURCE ID
        return self(targetID) # actually load the resource

    def add_root_name(self, name):
        'add name to the root of our data namespace and schema namespace'
        # This forces the root object to add name if not present.
        getattr(self.Data, name)
        getattr(self.Schema, name)

    def save_root_names(self, rootNames):
        'add set of names to our namespace root'
        for name in rootNames:
            self.add_root_name(name)

    def clear_cache(self):
        'clear all resources from cache'
        self.resourceCache.clear()

    def get_writer(self):
        'return writeable mdb if available, or raise exception'
        try:
            return self.writer
        except AttributeError:
            raise WorldbaseReadOnlyError('this metabase is read-only!')

    def add_resource(self, resID, obj=None):
        """assign obj as the specified resource ID to our metabase.
        if obj is None, treat resID as a dictionary whose keys are
        resource IDs and values are the objects to save."""
        if obj is None:
            self.get_writer().saver.add_resource_dict(resID)
        else:
            self.get_writer().saver.add_resource(resID, obj)

    def delete_resource(self, resID):
        'delete specified resource ID from our metabase'
        self.get_writer().saver.delete_resource(resID)

    def commit(self):
        'save any pending resource assignments and schemas'
        self.get_writer().saver.save_pending()

    def rollback(self):
        'discard any pending resource assignments and schemas'
        self.get_writer().saver.rollback()

    def queue_schema_obj(self, schemaPath, attr, schemaObj):
        'add a schema to the list of pending schemas to commit'
        self.get_writer().saver.queue_schema_obj(schemaPath, attr, schemaObj)

    def add_schema(self, resID, schemaObj):
        'assign a schema relation object to a worldbase resource name'
        l = resID.split('.')
        schemaPath = SchemaPath(self, '.'.join(l[:-1]))
        setattr(schemaPath, l[-1], schemaObj)

    def list_pending(self):
        return self.get_writer().saver.list_pending()


class Metabase(MetabaseBase):

    def __init__(self, dbpath, resourceCache, zoneDict=None, parent=None,
                 **kwargs):
        '''zoneDict provides a mechanism for the caller to request information
        about what type of metabase this dbpath mapped to.  zoneDict must
        be a dict'''
        self.parent = parent
        self.Schema = SchemaPath(self)
        self.Data = ResourceRoot(self) # root of namespace
        self.resourceCache = resourceCache
        self.debug = True # single mdb should expose all errors
        self.download = False
        if zoneDict is None: # user doesn't want zoneDict info
            zoneDict = {} # use a dummy dict, disposable
        if dbpath.startswith('http://'):
            storage = XMLRPCMetabase(dbpath, self, **kwargs)
            if 'remote' not in zoneDict:
                zoneDict['remote'] = self
        elif dbpath.startswith('mysql:'):
            storage = MySQLMetabase(dbpath[6:], self, **kwargs)
            if 'MySQL' not in zoneDict:
                zoneDict['MySQL'] = self
        else: # TREAT AS LOCAL FILEPATH
            dbpath = os.path.expanduser(dbpath)
            storage = ShelveMetabase(dbpath, self, **kwargs)
            if dbpath == os.path.expanduser('~') or \
               dbpath.startswith(os.path.expanduser('~') + os.sep):
                if 'my' not in zoneDict:
                    zoneDict['my'] = self
            elif os.path.isabs(dbpath):
                if 'system' not in zoneDict:
                    zoneDict['system'] = self
            elif dbpath.split(os.sep)[0] == os.curdir:
                if 'here' not in zoneDict:
                    zoneDict['here'] = self
            elif 'subdir' not in zoneDict:
                zoneDict['subdir'] = self
        self.storage = storage
        if storage.zoneName is not None and storage.zoneName not in zoneDict:
            zoneDict[storage.zoneName] = self  # record this zone name
        if storage.writeable:
            self.writeable = True
            self.saver = ResourceSaver(self)
            self.writer = self # record downloaded resources here
        else:
            self.writeable = False

    def update(self, worldbasePath=None, debug=None, keepCurrentPath=False):
        if not keepCurrentPath: # metabase has fixed path
            raise ValueError('You cannot change the path of a Metabase')

    def find_resource(self, resID, download=False):
        yield self.storage.find_resource(resID, download)

    def get_pending_or_find(self, resID, **kwargs):
        'find resID even if only pending (not actually saved yet)'
        try: # 1st LOOK IN PENDING QUEUE
            return self.saver.pendingData[resID]
        except KeyError:
            pass
        return self(resID, **kwargs)

    def getschema(self, resID):
        'return dict of {attr: {args}} or KeyError if not found'
        return self.storage.getschema(resID)

    def save_root_names(self, rootNames):
        if self.parent is not None: # add names to parent's namespace as well
            self.parent.save_root_names(rootNames)
        MetabaseBase.save_root_names(self, rootNames) # call the generic method

    def saveSchema(self, resID, attr, args):
        '''save an attribute binding rule to the schema; DO NOT use this
        internal interface unless you know what you are doing!'''
        self.storage.setschema(resID, attr, args)

    def saveSchemaEdge(self, schema):
        'save schema edge to schema graph'
        self.saveSchema(schema.name, '-schemaEdge', schema)
        self.storage.graph += schema.sourceDB # ADD NODE TO SCHEMA GRAPH
        # Edge
        self.storage.graph[schema.sourceDB][schema.targetDB] = schema.name

    def dir(self, pattern='', matchType='p', asDict=False, download=False):
        return self.storage.dir(pattern, matchType, asDict=asDict,
                            download=download)


class ZoneDict(UserDict.DictMixin):
    'interface to current zones'

    def __init__(self, mdbList):
        self.mdbList = mdbList

    def __getitem__(self, zoneName):
        self.mdbList.update(keepCurrentPath=True) # make sure metabases loaded
        return self.mdbList.zoneDict[zoneName]

    def keys(self):
        self.mdbList.update(keepCurrentPath=True) # make sure metabases loaded
        return self.mdbList.zoneDict.keys()

    def copy(self):
        self.mdbList.update(keepCurrentPath=True) # make sure metabases loaded
        return self.mdbList.zoneDict.copy()


class MetabaseList(MetabaseBase):
    '''Primary interface for worldbase resource database access.
    A single instance of this class is created upon import of the
    worldbase module, accessible as worldbase.getResource.  Users
    normally will have no need to create additional instances of this
    class themselves.'''
    # DEFAULT WORLDBASEPATH: HOME, CURRENT DIR, XMLRPC IN THAT ORDER
    defaultPath = ['~', '.', 'http://biodb2.bioinformatics.ucla.edu:5000']

    def __init__(self, worldbasePath=None, resourceCache=None, separator=',',
                 mdbArgs={}):
        '''initializes attrs; does not connect to metabases'''
        if resourceCache is None: # create a cache for loaded resources
            resourceCache = ResourceCache()
        self.resourceCache = resourceCache
        self.mdb = None
        self.mdbArgs = mdbArgs
        self.zoneDict = {}
        self.zones = ZoneDict(self) # interface to dict of zones
        self.worldbasePath = worldbasePath
        self.separator = separator
        self.Schema = SchemaPath(self)
        self.Data = ResourceRoot(self, zones=self.zones) # root of namespace
        self.debug = False # if one load attempt fails, try other metabases
        self.download = False
        self.ready = False

    def get_writer(self):
        'ensure that metabases are loaded, before looking for our writer'
        self.update(keepCurrentPath=True) # make sure metabases loaded
        return MetabaseBase.get_writer(self) # proceed as usual

    def find_resource(self, resID, download=False):
        'search our metabases for pickle string and docstr for resID'
        for mdb in self.mdb:
            try:
                yield mdb.find_resource(resID, download).next()
            except KeyError: # not in this db
                pass
        raise WorldbaseNotFoundError('unable to find %s in WORLDBASEPATH'
                                     % resID)

    def get_worldbase_path(self):
        'get environment var, or default in that order'
        try:
            return os.environ['WORLDBASEPATH']
        except KeyError:
            try:
                return os.environ['PYGRDATAPATH']
            except KeyError:
                return self.separator.join(self.defaultPath)

    def update(self, worldbasePath=None, debug=None, keepCurrentPath=False,
               mdbArgs=None):
        'get the latest list of resource databases'
        if keepCurrentPath: # only update if self.worldbasePath is None
            worldbasePath = self.worldbasePath
        if worldbasePath is None: # get environment var or default
            worldbasePath = self.get_worldbase_path()
        if debug is None:
            debug = self.debug
        if mdbArgs is None:
            mdbArgs = self.mdbArgs
        if not self.ready or self.worldbasePath != worldbasePath: # reload
            self.worldbasePath = worldbasePath
            try: # disconnect from previous writeable interface if any
                del self.writer
            except AttributeError:
                pass
            self.mdb = []
            try: # default: we don't have a writeable mdb to save data in
                del self.writer
            except AttributeError:
                pass
            self.zoneDict = {}
            for dbpath in worldbasePath.split(self.separator):
                try: # connect to metabase
                    mdb = Metabase(dbpath, self.resourceCache, self.zoneDict,
                                   self, **mdbArgs)
                except (KeyboardInterrupt, SystemExit):
                    raise # DON'T TRAP THESE CONDITIONS
                # FORCED TO ADOPT THIS STRUCTURE BECAUSE xmlrpc RAISES
                # socket.gaierror WHICH IS NOT A SUBCLASS OF StandardError...
                # SO I CAN'T JUST TRAP StandardError, UNFORTUNATELY...
                except: # trap errors and continue to next metabase
                    if debug:
                        raise # expose the error immediately
                    else: # warn the user but keep going...
                        import traceback
                        traceback.print_exc(10, sys.stderr)
                        print >>sys.stderr, '''
WARNING: error accessing metabase %s.  Continuing...''' % dbpath
                else: # NO PROBLEM, SO ADD TO OUR RESOURCE DB LIST
                    # Save to our list of resource databases.
                    self.mdb.append(mdb)
                    if mdb.writeable and not hasattr(self, 'writer'):
                        self.writer = mdb # record as place to save resources
            self.ready = True # metabases successfully loaded

    def get_pending_or_find(self, resID, **kwargs):
        'find resID even if only pending (not actually saved yet)'
        for mdb in self.mdb:
            try: # 1st LOOK IN PENDING QUEUE
                return mdb.saver.pendingData[resID]
            except KeyError:
                pass
        return self(resID, **kwargs)

    def registerServer(self, locationKey, serviceDict):
        'register the serviceDict with the first index server in WORLDBASEPATH'
        for mdb in self.mdb:
            if hasattr(mdb.storage, 'registerServer'):
                n = mdb.storage.registerServer(locationKey, serviceDict)
                if n == len(serviceDict):
                    return n
        raise ValueError('unable to register services.  Check WORLDBASEPATH')

    def getschema(self, resID):
        'search our resource databases for schema info for the desired ID'
        for mdb in self.mdb:
            try:
                return mdb.getschema(resID) # TRY TO OBTAIN FROM THIS DATABASE
            except KeyError:
                pass # NOT IN THIS DB
        raise KeyError('no schema info available for ' + resID)

    def dir(self, pattern='', matchType='p', asDict=False, download=False):
        'get list or dict of resources beginning with the specified string'
        self.update(keepCurrentPath=True) # make sure metabases loaded
        results = []
        for mdb in self.mdb:
            results.append(mdb.dir(pattern, matchType, asDict=asDict,
                                   download=download))
        if asDict: # merge result dictionaries
            d = {}
            results.reverse() # give first results highest precedence
            for subdir in results:
                d.update(subdir)
            return d
        else: # simply remove redundancy from results
            d = {}
            for l in results:
                filter(d.setdefault, l) # add all entries to dict
            results = d.keys()
            results.sort()
            return results


class ResourceCache(dict):
    'provide one central repository of loaded resources & schema info'

    def __init__(self):
        dict.__init__(self)
        self.schemaCache = {}

    def clear(self):
        dict.clear(self) # clear our dictionary
        self.schemaCache.clear() #


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

    def check_docstring(self, obj):
        '''enforce requirement for docstring, by raising exception
        if not present'''
        try:
            if obj.__doc__ is None or (hasattr(obj.__class__, '__doc__') and
                                       obj.__doc__==obj.__class__.__doc__):
                raise AttributeError
        except AttributeError:
            raise ValueError('to save a resource object, you MUST give it a \
                             __doc__ string attribute describing it!')

    def add_resource(self, resID, obj):
        'queue the object for saving to our metabase as <resID>'
        self.check_docstring(obj)
        obj._persistent_id = resID # MARK OBJECT WITH ITS PERSISTENT ID
        self.pendingData[resID] = obj # ADD TO QUEUE
        try:
            self.rollbackData[resID] = self.mdb.resourceCache[resID]
        except KeyError:
            pass
        self.cache_if_appropriate(resID, obj)

    def cache_if_appropriate(self, resID, obj):
        try:
            if obj._worldbase_no_cache:
                return # do not cache this object; it is not ready to use!!
        except AttributeError:
            pass
        self.mdb.resourceCache[resID] = obj # SAVE TO OUR CACHE

    def add_resource_dict(self, d):
        'queue a dict of name:object pairs for saving to metabase'
        for k, v in d.items():
            self.add_resource(k, v)

    def queue_schema_obj(self, schemaPath, attr, schemaObj):
        'add a schema object to the queue for saving to our metabase'
        resID = schemaPath.getPath(attr) # GET STRING ID
        self.pendingSchema[resID] = (schemaPath, attr, schemaObj)

    def save_resource(self, resID, obj):
        'save the object as <id>'
        self.check_docstring(obj)
        if obj._persistent_id != resID:
            raise WorldbaseMismatchError(
'''The _persistent_id attribute for %s has changed!
If you changed it, shame on you!  Otherwise, this should not happen, so report
the reproducible steps to this error message as a bug report.''' % resID)
        # Finally, save the object to the database.
        self.mdb.storage[resID] = obj
        self.cache_if_appropriate(resID, obj) # SAVE TO OUR CACHE

    def has_pending(self):
        'return True if there are resources pending to be committed'
        return len(self.pendingData) > 0 or len(self.pendingSchema) > 0

    def save_pending(self):
        'save any pending worldbase resources and schema'
        if len(self.pendingData) > 0 or len(self.pendingSchema) > 0:
            d = self.pendingData
            schemaDict = self.pendingSchema
        else:
            raise WorldbaseEmptyError('there is no data queued for saving!')
        for resID, obj in d.items(): # now save the data
            self.save_resource(resID, obj)
        for schemaPath, attr, schemaObj in schemaDict.values():# save schema
            schemaObj.saveSchema(schemaPath, attr, self.mdb) # save each rule
        self.clear_pending() # FINALLY, CLEAN UP...
        self.lastData = d # keep as a historical record
        self.lastSchema = schemaDict

    def list_pending(self):
        'return tuple of pending data dictionary, pending schema'
        return list(self.pendingData), list(self.pendingSchema)

    def rollback(self):
        'dump any pending data without saving, and restore state of cache'
        if len(self.pendingData) == 0 and len(self.pendingSchema) == 0:
            raise WorldbaseEmptyError('there is no data queued for saving!')
        # Restore the rollback queue.
        self.mdb.resourceCache.update(self.rollbackData)
        self.clear_pending()

    def delete_resource(self, resID): # incorporate this into commit-process?
        'delete the specified resource from resourceCache, saver and schema'
        del self.mdb.storage[resID] # delete from the resource database
        try:
            del self.mdb.resourceCache[resID] # delete from cache if exists
        except KeyError:
            pass
        try:
            del self.pendingData[resID] # delete from queue if exists
        except KeyError:
            pass
        self.delSchema(resID)

    def delSchema(self, resID):
        'delete schema bindings TO and FROM this resource ID'
        storage = self.mdb.storage
        try:
            d = storage.getschema(resID) # GET THE EXISTING SCHEMA
        except KeyError:
            return # no schema stored for this object so nothing to do...
        # This is more aggressive than needed... Could be refined.
        self.mdb.resourceCache.schemaCache.clear()
        for attr, obj in d.items():
            if attr.startswith('-'): # A SCHEMA OBJECT
                obj.delschema(storage) # DELETE ITS SCHEMA RELATIONS
            storage.delschema(resID, attr) # delete attribute schema rule

    def __del__(self):
        try:
            self.save_pending() # SEE WHETHER ANY DATA NEEDS SAVING
            print >>sys.stderr, '''
WARNING: saving worldbase pending data that you forgot to save...
Remember in the future, you must issue the command worldbase.commit() to save
your pending worldbase resources to your resource database(s), or alternatively
worldbase.rollback() to dump those pending data without saving them.
It is a very bad idea to rely on this automatic attempt to save your
forgotten data, because it is possible that the Python interpreter
may never call this function at exit (for details see the atexit module
docs in the Python Library Reference).'''
        except WorldbaseEmptyError:
            pass


class ResourceServer(XMLRPCServerBase):
    'serves resources that can be transmitted on XMLRPC'

    def __init__(self, mdb, name, serverClasses=None, clientHost=None,
                 withIndex=True, excludeClasses=None, downloadDB=None,
                 resourceDict=None, **kwargs):
        'construct server for the designated classes'
        XMLRPCServerBase.__init__(self, name, **kwargs)
        self.mdb = mdb
        if resourceDict is None:
            resourceDict = mdb.resourceCache
        if excludeClasses is None: # DEFAULT: NO POINT IN SERVING SQL TABLES...
            from sqlgraph import SQLTableBase, SQLGraphClustered
            excludeClasses = [SQLTableBase, SQLGraphClustered]
        if serverClasses is None: # DEFAULT TO ALL CLASSES WE KNOW HOW TO SERVE
            from seqdb import SequenceFileDB, BlastDB, \
                 XMLRPCSequenceDB, BlastDBXMLRPC, \
                 AnnotationDB, AnnotationClient, AnnotationServer
            serverClasses=[(SequenceFileDB, XMLRPCSequenceDB, BlastDBXMLRPC),
                           (BlastDB, XMLRPCSequenceDB, BlastDBXMLRPC),
                           (AnnotationDB, AnnotationClient, AnnotationServer)]
            try:
                from cnestedlist import NLMSA
                from xnestedlist import NLMSAClient, NLMSAServer
                serverClasses.append((NLMSA, NLMSAClient, NLMSAServer))
            except ImportError: # cnestedlist NOT INSTALLED, SO SKIP...
                pass
        if clientHost is None: # DEFAULT: USE THE SAME HOST STRING AS SERVER
            clientHost = self.host
        clientDict = {}
        for id, obj in resourceDict.items():
            # Save all objects matching serverClasses.
            skipThis = False
            for skipClass in excludeClasses: # CHECK LIST OF CLASSES TO EXCLUDE
                if isinstance(obj, skipClass):
                    skipThis = True
                    break
            if skipThis:
                continue # DO NOT INCLUDE THIS OBJECT IN SERVER
            skipThis = True
            for baseKlass, clientKlass, serverKlass in serverClasses:
                if isinstance(obj, baseKlass) and not isinstance(obj,
                                                                 clientKlass):
                    skipThis = False # OK, WE CAN SERVE THIS CLASS
                    break
            if skipThis: # HAS NO XMLRPC CLIENT-SERVER CLASS PAIRING
                try: # SAVE IT AS ITSELF
                    self.client_dict_setitem(clientDict, id, obj,
                                             badClasses=nonPortableClasses)
                except WorldbaseNotPortableError:
                    pass # HAS NON-PORTABLE LOCAL DEPENDENCIES, SO SKIP IT
                continue # GO ON TO THE NEXT DATA RESOURCE
            try: # TEST WHETHER obj CAN BE RE-CLASSED TO CLIENT / SERVER
                # Convert to server class for serving.`
                obj.__class__ = serverKlass
            except TypeError: # GRR, EXTENSION CLASS CAN'T BE RE-CLASSED...
                state = obj.__getstate__() # READ obj STATE
                newobj = serverKlass.__new__(serverKlass) # ALLOCATE NEW OBJECT
                newobj.__setstate__(state) # AND INITIALIZE ITS STATE
                obj = newobj # THIS IS OUR RE-CLASSED VERSION OF obj
            try: # USE OBJECT METHOD TO SAVE HOST INFO, IF ANY...
                obj.saveHostInfo(clientHost, self.port, id)
            except AttributeError: # TRY TO SAVE URL AND NAME DIRECTLY ON obj
                obj.url = 'http://%s:%d' % (clientHost, self.port)
                obj.name = id
            obj.__class__ = clientKlass # CONVERT TO CLIENT CLASS FOR PICKLING
            self.client_dict_setitem(clientDict, id, obj)
            obj.__class__ = serverKlass # CONVERT TO SERVER CLASS FOR SERVING
            self[id] = obj # ADD TO XMLRPC SERVER
        self.registrationData = clientDict # SAVE DATA FOR SERVER REGISTRATION
        if withIndex: # SERVE OUR OWN INDEX AS A STATIC, READ-ONLY INDEX
            myIndex = MetabaseServer(name, readOnly=True, # CREATE EMPTY INDEX
                                     downloadDB=downloadDB)
            self['index'] = myIndex # ADD TO OUR XMLRPC SERVER
            # Add our resources to the index.
            self.register('', '', server=myIndex)

    def client_dict_setitem(self, clientDict, k, obj, **kwargs):
        'save pickle and schema for obj into clientDict'
        pickleString = dumps(obj, **kwargs) # PICKLE THE CLIENT OBJECT, SAVE
        clientDict[k] = (get_info_dict(obj, pickleString), pickleString)
        try: # SAVE SCHEMA INFO AS WELL...
            clientDict['SCHEMA.' + k] = (dict(schema_version='1.0'),
                                         self.mdb.getschema(k))
        except KeyError:
            pass # NO SCHEMA FOR THIS OBJ, SO NOTHING TO DO


class ResourcePath(object):
    'simple way to read resource names as python foo.bar.bob expressions'

    def __init__(self, mdb, base=None):
        self.__dict__['_path'] = base # AVOID TRIGGERING setattr!
        self.__dict__['_mdb'] = mdb

    def getPath(self, name):
        if self._path is not None:
            return self._path + '.' + name
        else:
            return name

    def __getattr__(self, name):
        'extend the resource path by one more attribute'
        attr = self._pathClass(self._mdb, self.getPath(name))
        # MUST NOT USE setattr BECAUSE WE OVERRIDE THIS BELOW!
        self.__dict__[name] = attr # CACHE THIS ATTRIBUTE ON THE OBJECT
        return attr

    def __call__(self, *args, **kwargs):
        'construct the requested resource'
        return self._mdb(self._path, *args, **kwargs)

    def __setattr__(self, name, obj):
        'save obj using the specified resource name'
        self._mdb.add_resource(self.getPath(name), obj)

    def __delattr__(self, name):
        self._mdb.delete_resource(self.getPath(name))
        try: # IF ACTUAL ATTRIBUTE EXISTS, JUST DELETE IT
            del self.__dict__[name]
        except KeyError: # TRY TO DELETE RESOURCE FROM THE DATABASE
            pass # NOTHING TO DO

    def __dir__(self, prefix=None, start=None):
        """return list of our attributes from worldbase search"""
        if prefix is None:
            start = len(self._path) + 1 # skip past . separator
            prefix = self._path
        l = self._mdb.dir(prefix)
        d = {}
        for name in l:
            if name.startswith(prefix):
                d[name[start:].split('.')[0]] = None
        return d.keys()

ResourcePath._pathClass = ResourcePath


class ResourceRoot(ResourcePath):
    'provide proxy to public metabase methods'

    def __init__(self, mdb, base=None, zones=None):
        ResourcePath.__init__(self, mdb, base)
        self.__dict__['schema'] = mdb.Schema # AVOID TRIGGERING setattr!
        if zones is not None:
            self.__dict__['zones'] = zones
        for attr in ('dir', 'commit', 'rollback', 'add_resource',
                     'delete_resource', 'clear_cache', 'add_schema',
                     'update', 'list_pending'):
            self.__dict__[attr] = getattr(mdb, attr) # mirror metabase methods

    def __call__(self, resID, *args, **kwargs):
        """Construct the requested resource"""
        return self._mdb(resID, *args, **kwargs)

    def __dir__(self):
        return ResourcePath.__dir__(self, '', 0)


class ResourceZone(object):
    'provide pygr.Data old-style interface to resource zones'

    def __init__(self, mdb, zoneName):
        self._mdbParent = mdb
        self._zoneName = zoneName

    def __getattr__(self, name):
        # Make sure metabases have been loaded.
        self._mdbParent.update(keepCurrentPath=True)
        try:
            mdb = self._mdbParent.zoneDict[self._zoneName] # get our zone
        except KeyError:
            raise ValueError('no zone "%s" available' % self._zoneName)
        if name == 'schema': # get schema root
            return SchemaPath.__getitem__(self, mdb)
        else: # treat as regular worldbase string
            return ResourcePath.__getitem__(self, mdb, name)


class SchemaPath(ResourcePath):
    'save schema information for a resource'

    def __setattr__(self, name, schema):
        try:
            schema.saveSchema # VERIFY THAT THIS LOOKS LIKE A SCHEMA OBJECT
        except AttributeError:
            raise ValueError('not a valid schema object!')
        self._mdb.queue_schema_obj(self, name, schema) # QUEUE IT

    def __delattr__(self, attr):
        raise NotImplementedError('schema deletion is not yet implemented.')

SchemaPath._pathClass = SchemaPath


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
        return dict(targetID=self.targetID, itemRule=True)


class ManyToManyRelation(object):
    'a general graph mapping from sourceDB -> targetDB with edge info'
    _relationCode = 'many:many'

    def __init__(self, sourceDB, targetDB, edgeDB=None, bindAttrs=None,
                 sourceNotNone=None, targetNotNone=None):
        self.sourceDB = getID(sourceDB) # CONVERT TO STRING RESOURCE ID
        self.targetDB = getID(targetDB)
        if edgeDB is not None:
            self.edgeDB = getID(edgeDB)
        else:
            self.edgeDB = None
        self.bindAttrs = bindAttrs
        if sourceNotNone is not None:
            self.sourceNotNone = sourceNotNone
        if targetNotNone is not None:
            self.targetNotNone = targetNotNone

    def save_graph_bindings(self, graphDB, attr, mdb):
        '''save standard schema bindings to graphDB attributes
        sourceDB, targetDB, edgeDB'''
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
            bindObj = (self.sourceDB, self.targetDB, self.edgeDB)
            bindArgs = [{}, dict(invert=True), dict(getEdges=True)]
            try: # USE CUSTOM INVERSE SCHEMA IF PROVIDED BY TARGET DB
                bindArgs[1] = mdb.get_pending_or_find(graphDB). \
                        _inverse_schema()
            except AttributeError:
                pass
            for i in range(3):
                if len(self.bindAttrs) > i and self.bindAttrs[i] is not None:
                    b = ItemRelation(graphDB) # SAVE ITEM BINDING
                    b.saveSchema(bindObj[i], self.bindAttrs[i],
                                 mdb, **bindArgs[i])

    def delschema(self, resourceDB):
        'delete resource attribute bindings associated with this rule'
        if self.bindAttrs is not None:
            bindObj = (self.sourceDB, self.targetDB, self.edgeDB)
            for i in range(3):
                if len(self.bindAttrs) > i and self.bindAttrs[i] is not None:
                    resourceDB.delschema(bindObj[i], self.bindAttrs[i])


class OneToManyRelation(ManyToManyRelation):
    _relationCode = 'one:many'


class OneToOneRelation(ManyToManyRelation):
    _relationCode = 'one:one'


class ManyToOneRelation(ManyToManyRelation):
    _relationCode = 'many:one'


class InverseRelation(DirectRelation):
    "bind source and target as each other's inverse mappings"
    _relationCode = 'inverse'

    def saveSchema(self, source, attr, mdb, **kwargs):
        'save schema bindings associated with this rule'
        source = source.getPath(attr) # GET STRING ID FOR source
        self.name = source
        mdb.saveSchemaEdge(self) #SAVE THIS RULE
        DirectRelation.saveSchema(self, source, 'inverseDB',
                                  mdb, **kwargs) # source -> target
        b = DirectRelation(source) # CREATE REVERSE MAPPING
        b.saveSchema(self.targetID, 'inverseDB',
                     mdb, **kwargs) # target -> source

    def delschema(self, resourceDB):
        resourceDB.delschema(self.targetID, 'inverseDB')


def getID(obj):
    'get persistent ID of the object or raise AttributeError'
    if isinstance(obj, str): # TREAT ANY STRING AS A RESOURCE ID
        return obj
    elif isinstance(obj, ResourcePath):
        return obj._path # GET RESOURCE ID FROM A ResourcePath
    else:
        try: # GET RESOURCE'S PERSISTENT ID
            return obj._persistent_id
        except AttributeError:
            raise AttributeError('this obj has no persistent ID!')
