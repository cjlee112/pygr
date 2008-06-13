

from __future__ import generators
from mapping import *
import types
from classutil import ClassicUnpickler,methodFactory,standard_getstate,\
     override_rich_cmp,generate_items,get_shadow_class
    

class TupleO(object):
    """Provide attribute interface to a tuple.  Subclass this and create _attrcol
    that maps attribute names to tuple index values."""
    def __init__(self,data):
        self.data=data
    def __getattr__(self,attr):
        try:
            return self.data[self._attrcol[attr]]
        except KeyError:
            raise AttributeError('no attribute %s' % attr)
        except TypeError: # treat as an alias
            return getattr(self, self._attrcol[attr])


class SQLRow(object):
    """Provide transparent interface to a row in the database: attribute access
       will be mapped to SELECT of the appropriate column, but data is not cached
       on this object.
    """
    def __init__(self,table,id):
        self.db=table
        self.id=id

    def _select(self,what):
        "Get SQL select expression for this row"
        self.db.cursor.execute('select %s from %s where %s=%%s'
                               % (what,self.db.name,self.db.primary_key),(self.id,))
        l=self.db.cursor.fetchall()
        if len(l)!=1:
            raise KeyError('%s[%s].%s not found, or not unique'
                           % (self.db.name,str(self.id),what))
        return l[0][0] # RETURN THE SINGLE FIELD WE REQUESTED

    def __getattr__(self,attr):
        return self._select(self.db._attrSQL(attr))



def list_to_dict(names,values):
    'return dictionary of those named args that are present'
    d={}
    for i in range(len(values)):
        try:
            d[names[i]]=values[i]
        except IndexError:
            pass
    return d


def getNameCursor(name,connect=None,configFile=None,**kwargs):
    'get table name and cursor by parsing name or using configFile'
    if connect is None:
        import MySQLdb
        connect=MySQLdb.connect
    argList=name.split() # TREAT AS WS-SEPARATED LIST
    if len(argList)>1:
        name=argList[0] # USE 1ST ARG AS TABLE NAME
        argnames=('host','user','passwd') # READ ARGS IN THIS ORDER
        kwargs = list_to_dict(argnames,argList[1:])
    else: # USE .my.cnf TO GET CONNECTION PARAMETERS
        kwargs = {}
    if configFile is None:
        import os
        configFile=os.environ['HOME']+'/.my.cnf'
    try:
        ifile = file(configFile)
    except IOError:
        pass
    else:
        ifile.close()
        kwargs['read_default_file'] = configFile
    cursor=connect(compress=True,**kwargs).cursor()
    return name,cursor


class SQLTableBase(dict):
    "Store information about an SQL table as dict keyed by primary key"
    def __init__(self,name,cursor=None,itemClass=None,attrAlias=None,
                 clusterKey=None,createTable=None,graph=None,maxCache=None,
                 arraysize=1024, itemSliceClass=None, **kwargs):
        dict.__init__(self) # INITIALIZE EMPTY DICTIONARY
        if cursor is None:
            name,cursor=getNameCursor(name,**kwargs)
        if createTable is not None: # RUN COMMAND TO CREATE THIS TABLE
            cursor.execute(createTable)
        cursor.execute('describe %s' % name)
        columns=cursor.fetchall()
        self.cursor=cursor
        self.name=name
        self.primary_key=None
        self.indexed={}
        self.data={}
        self.description={}
        if graph is not None:
            self.graph = graph
        if maxCache is not None:
            self.maxCache = maxCache
        if arraysize is not None:
            self.arraysize = arraysize
            cursor.arraysize = arraysize
        icol=0
        cursor.execute('select * from %s limit 1' % name)
        for c in columns:
            field=c[0]
            if c[3]=="PRI":
                self.primary_key=field
            elif c[3]=="MUL":
                self.indexed[field]=icol
            self.data[field]=icol
            self.description[field]=cursor.description[icol]
            icol += 1
        if self.primary_key != None: # MAKE PRIMARY KEY ALWAYS ACCESSIBLE AS ATTRIBUTE id
            self.data['id']=self.data[self.primary_key]
        if hasattr(self,'_attr_alias'): # FINALLY, APPLY ANY ATTRIBUTE ALIASES FOR THIS CLASS
            self.addAttrAlias(**self._attr_alias)
        self.objclass(itemClass) # NEED TO SET OUR DEFAULT ITEM CLASS
        if itemSliceClass is not None:
            self.itemSliceClass = itemSliceClass
        if attrAlias is not None: # ADD ATTRIBUTE ALIASES
            self.data.update(attrAlias)
        if clusterKey is not None:
            self.clusterKey=clusterKey

    def __hash__(self):
        return id(self)
    def __reduce__(self): ############################# SUPPORT FOR PICKLING
        return (ClassicUnpickler, (self.__class__,self.__getstate__()))
    _pickleAttrs = dict(name=0,clusterKey=0,maxCache=0,arraysize=0)
    def __getstate__(self):
        state = standard_getstate(self)
        state['attrAlias'] = self.getAttrAlias() # SAVE ATTRIBUTE ALIASES
        return state
    def __setstate__(self,state):
        if isinstance(state,list):  # GET RID OF THIS BACKWARDS-COMPATIBILITY CODE!
            name = state[0]
        else:
            name = state['name']
        try: # SEE IF WE CAN GET CURSOR DIRECTLY FROM RESOURCE DATABASE
            from Data import getResource
            cursor=getResource.getTableCursor(name)
        except ImportError:
            cursor=None # FAILED, SO TRY TO GET A CURSOR IN THE USUAL WAYS...
        if isinstance(state,list):  # GET RID OF THIS BACKWARDS-COMPATIBILITY CODE!
            state[1] = cursor
            self.__init__(*state)
            import sys
            print >>sys.stderr,'WARNING: obsolete list pickle %s. Update by resaving!' \
                  % repr(self)
        else:
            state['cursor'] = cursor
            self.__init__(**state)
    def __repr__(self):
        return '<SQL table '+self.name+'>'

    def _attrSQL(self,attr):
        "Translate python attribute name to appropriate SQL expression"
        try: # MAKE SURE THIS ATTRIBUTE CAN BE MAPPED TO DATABASE EXPRESSION
            field=self.data[attr]
        except KeyError:
            raise AttributeError('%s not a valid column in %s' % (attr,self.name))
        if isinstance(field,types.StringType):
            attr=field # USE ALIASED EXPRESSION FOR DATABASE SELECT INSTEAD OF attr
        elif attr=='id':
            attr=self.primary_key
        return attr
    def getAttrAlias(self):
        'get a dict of attribute aliases'
        d={}
        for k,v in self.data.items():
            if isinstance(v,types.StringType):
                d[k]=v
        return d
    def addAttrAlias(self,**kwargs):
        """Add new attributes as aliases of existing attributes.
           They can be specified either as named args:
           t.addAttrAlias(newattr=oldattr)
           or by passing a dictionary kwargs whose keys are newattr
           and values are oldattr:
           t.addAttrAlias(**kwargs)
        """
        for key,val in kwargs.items():
            try: # 1ST TREAT AS ALIAS TO EXISTING COLUMN
                self.data[key]=self.data[val]
            except KeyError: # TREAT AS ALIAS TO SQL EXPRESSION
                self.data[key]=val

    def objclass(self,oclass=None):
        "Specify class for python object representing a row in this table"
        if oclass is not None: # use this as our base itemClass
            self.itemClass = oclass
        oclass = get_shadow_class(self, 'itemClass', self.name)
        if issubclass(oclass,TupleO): # TupleO needs _attrcol info
            oclass._attrcol=self.data # BIND ATTRIBUTE LIST TO TUPLEO INTERFACE
        if hasattr(oclass,'_tableclass') and not isinstance(self,oclass._tableclass):
            self.__class__=oclass._tableclass # ROW CLASS CAN OVERRIDE OUR CURRENT TABLE CLASS
    def _select(self,whereClause='',params=None,selectCols='t1.*'):
        'execute the specified query but do not fetch'
        self.cursor.execute('select %s from %s t1 %s'
                            % (selectCols,self.name,whereClause),params)
    def select(self,whereClause,params=None,oclass=None,selectCols='t1.*'):
        "Generate the list of objects that satisfy the database SELECT"
        if oclass is None:
            oclass=self.itemClass
        self._select(whereClause,params,selectCols)
        l=self.cursor.fetchall()
        for t in l:
            yield self.cacheItem(t,oclass)
    def tupleItem(self,t,oclass):
        'create object to represent this row, using oclass'
        o=oclass(t)
        o.db=self # MARK THE OBJECT AS BEING PART OF THIS CONTAINER
        return o
    def getID(self,t):
        try:
            return t[self.data['id']] # GET ID FROM TUPLE
        except TypeError: # treat as alias
            return t[self.data[self.data['id']]]
    def cacheItem(self,t,oclass):
        'get obj from cache if possible, or construct from tuple'
        try:
            id=self.getID(t)
        except KeyError: # NO PRIMARY KEY?  IGNORE THE CACHE.
            return self.tupleItem(t,oclass)
        try: # IF ALREADY LOADED IN OUR DICTIONARY, JUST RETURN THAT ENTRY
            return dict.__getitem__(self,id)
        except KeyError:
            pass
        o=self.tupleItem(t,oclass)
        dict.__setitem__(self,id,o)   # CACHE THIS ITEM IN OUR DICTIONARY
        return o
    def cache_items(self,rows,oclass=None):
        if oclass is None:
            oclass=self.itemClass
        for t in rows:
            yield self.cacheItem(t,oclass) 
    def foreignKey(self,attr,k):
        'get iterator for objects with specified foreign key value'
        return self.select('where %s=%%s'%attr,(k,))
    def limit_cache(self):
        'APPLY maxCache LIMIT TO CACHE SIZE'
        try:
            if self.maxCache<dict.__len__(self):
                self.clear()
        except AttributeError:
            pass
    def generic_iterator(self,fetch_f=None,cache_f=cache_items,map_f=iter):
        'generic iterator that runs fetch, cache and map functions'
        if fetch_f is None: # JUST USE CURSOR'S PREFERRED CHUNK SIZE
            fetch_f = self.cursor.fetchmany
        while True:
            self.limit_cache()
            rows = fetch_f() # FETCH THE NEXT SET OF ROWS
            if len(rows)==0: # NO MORE DATA SO ALL DONE
                break
            for v in map_f(cache_f(rows)): # CACHE AND GENERATE RESULTS
                yield v


def getKeys(self,queryOption=''):
    'uses db select; does not force load'
    self.cursor.execute('select %s from %s %s' 
                        %(self.primary_key,self.name,queryOption))
    return [t[0] for t in self.cursor.fetchall()] # GET ALL AT ONCE, SINCE OTHER CALLS MAY REUSE THIS CURSOR...


class SQLTable(SQLTableBase):
    "Provide on-the-fly access to rows in the database, caching the results in dict"
    itemClass = TupleO # our default itemClass; constructor can override
    keys=getKeys
    def __iter__(self): return iter(self.keys())
    def load(self,oclass=None):
        "Load all data from the table"
        try: # IF ALREADY LOADED, NO NEED TO DO ANYTHING
            return self._isLoaded
        except AttributeError:
            pass
        if oclass is None:
            oclass=self.itemClass
        self.cursor.execute('select * from %s' % self.name)
        l=self.cursor.fetchall()
        for t in l:
            self.cacheItem(t,oclass) # CACHE IT IN LOCAL DICTIONARY
        self._isLoaded=True # MARK THIS CONTAINER AS FULLY LOADED

    def __getitem__(self,k): # FIRST TRY LOCAL INDEX, THEN TRY DATABASE
        try:
            return dict.__getitem__(self,k) # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            self.cursor.execute('select * from %s where %s=%%s'
                                % (self.name,self.primary_key),(k,))
            l=self.cursor.fetchall()
            if len(l)!=1:
                raise KeyError('%s not found in %s, or not unique' %(str(k),self.name))
            self.limit_cache()
            return self.cacheItem(l[0],self.itemClass) # CACHE IT IN LOCAL DICTIONARY
    def items(self):
        'forces load of entire table into memory'
        self.load()
        return dict.items(self)
    def iteritems(self):
        'uses arraysize / maxCache and fetchmany() to manage data transfer'
        self._select()
        return self.generic_iterator(map_f=generate_items)
    def values(self):
        'forces load of entire table into memory'
        self.load()
        return dict.values(self)
    def itervalues(self):
        'uses arraysize / maxCache and fetchmany() to manage data transfer'
        self._select()
        return self.generic_iterator()

def getClusterKeys(self,queryOption=''):
    'uses db select; does not force load'
    self.cursor.execute('select distinct %s from %s %s'
                        %(self.clusterKey,self.name,queryOption))
    return [t[0] for t in self.cursor.fetchall()] # GET ALL AT ONCE, SINCE OTHER CALLS MAY REUSE THIS CURSOR...


class SQLTableClustered(SQLTable):
    '''use clusterKey to load a whole cluster of rows at once,
       specifically, all rows that share the same clusterKey value.'''
    def keys(self):
        return getKeys(self,'order by %s' %self.clusterKey)
    def clusterkeys(self):
        return getClusterKeys(self, 'order by %s' %self.clusterKey)
    def __getitem__(self,k):
        try:
            return dict.__getitem__(self,k) # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            self.cursor.execute('select t2.* from %s t1,%s t2 where t1.%s=%%s and t1.%s=t2.%s'
                                % (self.name,self.name,self.primary_key,
                                   self.clusterKey,self.clusterKey),(k,))
            l=self.cursor.fetchall()
            self.limit_cache()
            for t in l: # LOAD THE ENTIRE CLUSTER INTO OUR LOCAL CACHE
                self.cacheItem(t,self.itemClass)
            return dict.__getitem__(self,k) # SHOULD BE IN CACHE, IF ROW k EXISTS
    def itercluster(self,cluster_id):
        'iterate over all items from the specified cluster'
        self.limit_cache()
        return self.select('where %s=%%s'%self.clusterKey,(cluster_id,))
    def fetch_cluster(self):
        'use self.cursor.fetchmany to obtain all rows for next cluster'
        icol = self.data[self.clusterKey]
        result = []
        try:
            rows = self._fetch_cluster_cache # USE SAVED ROWS FROM PREVIOUS CALL
            del self._fetch_cluster_cache
        except AttributeError:
            rows = self.cursor.fetchmany()
        try:
            cluster_id = rows[0][icol]
        except IndexError:
            return result
        while len(rows)>0:
            for i,t in enumerate(rows): # CHECK THAT ALL ROWS FROM THIS CLUSTER
                if cluster_id != t[icol]: # START OF A NEW CLUSTER
                    result += rows[:i] # RETURN ROWS OF CURRENT CLUSTER
                    self._fetch_cluster_cache = rows[i:] # SAVE NEXT CLUSTER
                    return result
            result += rows
            rows = self.cursor.fetchmany() # GET NEXT SET OF ROWS
        return result
    def itervalues(self):
        'uses arraysize / maxCache and fetchmany() to manage data transfer'
        self._select('order by %s' %self.clusterKey)
        return self.generic_iterator(self.fetch_cluster)
    def iteritems(self):
        'uses arraysize / maxCache and fetchmany() to manage data transfer'
        self._select('order by %s' %self.clusterKey)
        return self.generic_iterator(self.fetch_cluster,map_f=generate_items)
        
class SQLForeignRelation(object):
    'mapping based on matching a foreign key in an SQL table'
    def __init__(self,table,keyName):
        self.table=table
        self.keyName=keyName
    def __getitem__(self,k):
        'get list of objects o with getattr(o,keyName)==k.id'
        l=[]
        for o in self.table.select('where %s=%%s'%self.keyName,(k.id,)):
            l.append(o)
        if len(l)==0:
            raise KeyError('%s not found in %s' %(str(k),self.name))
        return l


class SQLTableNoCache(SQLTableBase):
    "Provide on-the-fly access to rows in the database, but never cache results"
    itemClass=SQLRow # DEFAULT OBJECT CLASS FOR ROWS...
    keys=getKeys
    def __iter__(self): return iter(self.keys())
    def getID(self,t): return t[0] # GET ID FROM TUPLE
    def select(self,whereClause,params):
        return SQLTableBase.select(self,whereClause,params,self.oclass,
                                   self._attrSQL('id'))
    def oclass(self,t): # CREATE OBJECT FROM TUPLE
        return self.itemClass(self,t[0]) # AN EMPTY CONTAINER FOR ACCESSING THIS ROW
    def __getitem__(self,k): # FIRST TRY LOCAL INDEX, THEN TRY DATABASE
        try:
            return dict.__getitem__(self,k) # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            o=self.itemClass(self,k) # RETURN AN EMPTY CONTAINER FOR ACCESSING THIS ROW
            dict.__setitem__(self,k,o) # STORE EMPTY CONTAINER IN LOCAL DICTIONARY
            return o
    def addAttrAlias(self,**kwargs):
        self.data.update(kwargs) # ALIAS KEYS TO EXPRESSION VALUES

SQLRow._tableclass=SQLTableNoCache  # SQLRow IS FOR NON-CACHING TABLE INTERFACE


class SQLTableMultiNoCache(SQLTableBase):
    "Trivial on-the-fly access for table with key that returns multiple rows"
    itemClass = TupleO # default itemClass; constructor can override
    _distinct_key='id' # DEFAULT COLUMN TO USE AS KEY
    def __iter__(self):
        self.cursor.execute('select distinct(%s) from %s'
                            %(self._attrSQL(self._distinct_key),self.name))
        l=self.cursor.fetchall() # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        for row in l:
            yield row[0]

    def __getitem__(self,id):
        self.cursor.execute('select * from %s where %s=%%s'
                            %(self.name,self._attrSQL(self._distinct_key)),(id,))
        l=self.cursor.fetchall() # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        for row in l:
            yield self.itemClass(row)
    def addAttrAlias(self,**kwargs):
        self.data.update(kwargs) # ALIAS KEYS TO EXPRESSION VALUES



class SQLEdges(SQLTableMultiNoCache):
    '''provide iterator over edges as (source,target,edge)
       and getitem[edge] --> [(source,target),...]'''
    _distinct_key='edge_id'
    _pickleAttrs = SQLTableMultiNoCache._pickleAttrs.copy()
    _pickleAttrs.update(dict(graph=0))
    def keys(self):
        self.cursor.execute('select %s,%s,%s from %s where %s is not null order by %s,%s'
                            %(self._attrSQL('source_id'),self._attrSQL('target_id'),
                              self._attrSQL('edge_id'),self.name,
                              self._attrSQL('target_id'),self._attrSQL('source_id'),
                              self._attrSQL('target_id')))
        l = [] # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        for source_id,target_id,edge_id in self.cursor.fetchall():
            l.append((self.graph.unpack_source(source_id),
                      self.graph.unpack_target(target_id),
                      self.graph.unpack_edge(edge_id)))
        return l
    __call__=keys
    def __iter__(self):
        return iter(self.keys())
    def __getitem__(self,edge):
        self.cursor.execute('select %s,%s from %s where %s=%%s'
                            %(self._attrSQL('source_id'),
                              self._attrSQL('target_id'),
                              self.name,self._attrSQL(self._distinct_key)),
                            (self.graph.pack_edge(edge),))
        l = [] # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        for source_id,target_id in self.cursor.fetchall():
            l.append((self.graph.unpack_source(source_id),
                      self.graph.unpack_target(target_id)))
        return l


class SQLEdgeDict(object):
    '2nd level graph interface to SQL database'
    def __init__(self,fromNode,table):
        self.fromNode=fromNode
        self.table=table
        if self.table.cursor.execute('select %s from %s where %s=%%s limit 1'
                                     %(self.table._attrSQL('source_id'),
                                       self.table.name,
                                       self.table._attrSQL('source_id')),
                                     (self.fromNode,))<1:
            raise KeyError('node not in graph!')

    def __getitem__(self,target):
        self.table.cursor.execute('select %s from %s where %s=%%s and %s=%%s'
                                  %(self.table._attrSQL('edge_id'),
                                    self.table.name,self.table._attrSQL('source_id'),
                                    self.table._attrSQL('target_id')),
                                  (self.fromNode,self.table.pack_target(target)))
        l=self.table.cursor.fetchall()
        try:
            return self.table.unpack_edge(l[0][0]) # RETURN EDGE
        except IndexError:
            raise KeyError('no edge from node to target')
    def __setitem__(self,target,edge):
        self.table.cursor.execute('replace into %s values (%%s,%%s,%%s)'
                                  %self.table.name,
                                  (self.fromNode,self.table.pack_target(target),
                                   self.table.pack_edge(edge)))
        if not hasattr(self.table,'sourceDB') or \
           (hasattr(self.table,'targetDB') and self.table.sourceDB==self.table.targetDB):
            self.table += target # ADD AS NODE TO GRAPH
    def __iadd__(self,target):
        self[target] = None
        return self # iadd MUST RETURN self!
    def __delitem__(self,target):
        if self.table.cursor.execute('delete from %s where %s=%%s and %s=%%s'
                                     %(self.table.name,self.table._attrSQL('source_id'),
                                       self.table._attrSQL('target_id')),
                                     (self.fromNode,self.table.pack_target(target)))<1:
            raise KeyError('no edge from node to target')
        
    def __iter__(self): return self.iteritems(0)
    def keys(self): return [k for k in self]
    def itervalues(self): return self.iteritems(1)
    def values(self): return [k for k in self.iteritems(1)]
    def items(self): return [k for k in self.iteritems()]
    def edges(self): return [(self.table.unpack_source(self.fromNode),)
                             +k for k in self.iteritems()]
    def iteritems(self,k=slice(0,2)):
        self.table.cursor.execute('select %s,%s from %s where %s=%%s and %s is not null'
                                  %(self.table._attrSQL('target_id'),
                                    self.table._attrSQL('edge_id'),
                                    self.table.name,self.table._attrSQL('source_id'),
                                    self.table._attrSQL('target_id')),
                                  (self.fromNode,))
        for target_id,edge_id in self.table.cursor.fetchall():
            row = (self.table.unpack_target(target_id),
                   self.table.unpack_edge(edge_id))
            yield row[k]
    def __len__(self):
        return len(self.keys())
    __cmp__ = graph_cmp

class SQLGraphEdgeDescriptor(object):
    'provide an SQLEdges interface on demand'
    def __get__(self,obj,objtype):
        return SQLEdges(obj.name,obj.cursor,attrAlias=obj.getAttrAlias(),
                        graph=obj)

def getColumnTypes(createTable,attrAlias={},defaultColumnType='int',
                  columnAttrs=('source','target','edge'),**kwargs):
    'return list of [(colname,coltype),...] for source,target,edge'
    l = []
    for attr in columnAttrs:
        try:
            attrName = attrAlias[attr+'_id']
        except KeyError:
            attrName = attr+'_id'
        try:
            db = kwargs[attr+'DB']
        except KeyError:
            try: # SEE IF USER SPECIFIED A DESIRED TYPE
                l.append((attrName,createTable[attr+'_id']))
            except (KeyError,TypeError): # OTHERWISE USE THE DEFAULT
                l.append((attrName,defaultColumnType))
        else: # INFER THE COLUMN TYPE FROM THE ASSOCIATED DATABASE KEYS...
            it = iter(db)
            k = it.next()
            if isinstance(k,int):
                l.append((attrName,'int'))
            elif isinstance(k,str):
                l.append((attrName,'varchar(32)'))
            else:
                raise ValueError('SQLGraph node / edge must be int or str!')
    return l


class SQLGraph(SQLTableMultiNoCache):
    '''provide a graph interface via a SQL table.  Key capabilities are:
       - setitem with an empty dictionary: a dummy operation
       - getitem with a key that exists: return a placeholder
       - setitem with non empty placeholder: again a dummy operation
       EXAMPLE TABLE SCHEMA:
       create table mygraph (source_id int not null,target_id int,edge_id int,
              unique(source_id,target_id));
       '''
    _distinct_key='source_id'
    _pickleAttrs = SQLTableMultiNoCache._pickleAttrs.copy()
    _pickleAttrs.update(dict(sourceDB=0,targetDB=0,edgeDB=0))
    def __init__(self,name,*l,**kwargs):
        if 'createTable' in kwargs: # CREATE A SCHEMA FOR THIS TABLE
            c = getColumnTypes(**kwargs)
            kwargs['createTable'] = \
              'create table %s (%s %s not null,%s %s,%s %s,unique(%s,%s))' \
              % (name,c[0][0],c[0][1],c[1][0],c[1][1],c[2][0],c[2][1],c[0][0],c[1][0])
        SQLTableMultiNoCache.__init__(self,name,*l,**kwargs)
        save_graph_db_refs(self,**kwargs)
    def __getitem__(self,k):
        return SQLEdgeDict(self.pack_source(k),self)
    def __iadd__(self,k):
        self.cursor.execute('delete from %s where %s=%%s and %s is null'
                            % (self.name,self._attrSQL('source_id'),
                               self._attrSQL('target_id')),
                            (self.pack_source(k),))
        self.cursor.execute('insert ignore into %s values (%%s,NULL,NULL)'
                            % self.name,(self.pack_source(k),))
        return self # iadd MUST RETURN SELF!
    def __isub__(self,k):
        if self.cursor.execute('delete from %s where %s=%%s'
                               % (self.name,self._attrSQL('source_id')),
                               (self.pack_source(k),))==0:
            raise KeyError('node not found in graph')
        return self # iadd MUST RETURN SELF!
    __setitem__ = graph_setitem
    def __contains__(self,k):
        return self.cursor.execute('select * from %s where %s=%%s'
                                   %(self.name,self._attrSQL('source_id')),
                                   (self.pack_source(k),))>0
    def __invert__(self):
        'get an interface to the inverse graph mapping'
        try: # CACHED
            return self._inverse
        except AttributeError: # CONSTRUCT INTERFACE TO INVERSE MAPPING
            self._inverse=SQLGraph(self.name,self.cursor, # SWAP SOURCE & TARGET
                                   attrAlias=dict(source_id=self.data['target_id'],
                                                  target_id=self.data['source_id'],
                                                  edge_id=self.data['edge_id']),
                                   **graph_db_inverse_refs(self))
            self._inverse._inverse=self
            return self._inverse
    def iteritems(self,myslice=slice(0,2)):
        for k in self:
            result=(self.pack_source(k),SQLEdgeDict(k,self))
            yield result[myslice]
    def keys(self): return [k for k in self]
    def itervalues(self): return self.iteritems(1)
    def values(self): return [k for k in self.iteritems(1)]
    def items(self): return [k for k in self.iteritems()]
    edges=SQLGraphEdgeDescriptor()
    update = update_graph
    def __len__(self):
        'get number of nodes in graph'
        return self.cursor.execute('select distinct(%s) from %s'
                                   %(self._attrSQL('source_id'),self.name))
    __cmp__ = graph_cmp
    override_rich_cmp(locals()) # MUST OVERRIDE __eq__ ETC. TO USE OUR __cmp__!
##     def __cmp__(self,other):
##         node = ()
##         n = 0
##         d = None
##         it = iter(self.edges)
##         while True:
##             try:
##                 source,target,edge = it.next()
##             except StopIteration:
##                 source = None
##             if source!=node:
##                 if d is not None:
##                     diff = cmp(n_target,len(d))
##                     if diff!=0:
##                         return diff
##                 if source is None:
##                     break
##                 node = source
##                 n += 1 # COUNT SOURCE NODES
##                 n_target = 0
##                 try:
##                     d = other[node]
##                 except KeyError:
##                     return 1
##             try:
##                 diff = cmp(edge,d[target])
##             except KeyError:
##                 return 1
##             if diff!=0:
##                 return diff
##             n_target += 1 # COUNT TARGET NODES FOR THIS SOURCE
##         return cmp(n,len(other))
            
    add_standard_packing_methods(locals())  ############ PACK / UNPACK METHODS

class SQLIDGraph(SQLGraph):
    add_trivial_packing_methods(locals())
SQLGraph._IDGraphClass = SQLIDGraph



class SQLEdgeDictClustered(dict):
    'simple cache for 2nd level dictionary of target_id:edge_id'
    def __init__(self,g,fromNode):
        self.g=g
        self.fromNode=fromNode
        dict.__init__(self)
    def __iadd__(self,l):
        for target_id,edge_id in l:
            dict.__setitem__(self,target_id,edge_id)
        return self # iadd MUST RETURN SELF!

class SQLEdgesClusteredDescr(object):
    def __get__(self,obj,objtype):
        e=SQLEdgesClustered(obj.table,obj.edge_id,obj.source_id,obj.target_id,
                            graph=obj,**graph_db_inverse_refs(obj,True))
        for source_id,d in obj.d.iteritems(): # COPY EDGE CACHE
            e.load([(edge_id,source_id,target_id)
                    for (target_id,edge_id) in d.iteritems()])
        return e

class SQLGraphClustered(object):
    'SQL graph with clustered caching -- loads an entire cluster at a time'
    _edgeDictClass=SQLEdgeDictClustered
    def __init__(self,table,source_id='source_id',target_id='target_id',
                 edge_id='edge_id',clusterKey=None,**kwargs):
        import types
        if isinstance(table,types.StringType): # CREATE THE TABLE INTERFACE
            if clusterKey is None:
                raise ValueError('you must provide a clusterKey argument!')
            if 'createTable' in kwargs: # CREATE A SCHEMA FOR THIS TABLE
                c = getColumnTypes(attrAlias=dict(source_id=source_id,target_id=target_id,
                                                  edge_id=edge_id),**kwargs)
                kwargs['createTable'] = \
                  'create table %s (%s %s not null,%s %s,%s %s,unique(%s,%s))' \
                  % (table,c[0][0],c[0][1],c[1][0],c[1][1],
                     c[2][0],c[2][1],c[0][0],c[1][0])
            table = SQLTableClustered(table,clusterKey=clusterKey,**kwargs)
        self.table=table
        self.source_id=source_id
        self.target_id=target_id
        self.edge_id=edge_id
        self.d={}
        save_graph_db_refs(self,**kwargs)
    _pickleAttrs = dict(table=0,source_id=0,target_id=0,edge_id=0,sourceDB=0,targetDB=0,
                        edgeDB=0)
    def __getstate__(self):
        state = standard_getstate(self)
        state['d'] = {} # UNPICKLE SHOULD RESTORE GRAPH WITH EMPTY CACHE
        return state
    def __getitem__(self,k):
        'get edgeDict for source node k, from cache or by loading its cluster'
        try: # GET DIRECTLY FROM CACHE
            return self.d[k]
        except KeyError:
            if hasattr(self,'_isLoaded'):
                raise # ENTIRE GRAPH LOADED, SO k REALLY NOT IN THIS GRAPH
        # HAVE TO LOAD THE ENTIRE CLUSTER CONTAINING THIS NODE
        self.table.cursor.execute('select t2.%s,t2.%s,t2.%s from %s t1,%s t2 where t1.%s=%%s and t1.%s=t2.%s group by t2.%s'
                                  %(self.source_id,self.target_id,
                                    self.edge_id,self.table.name,
                                    self.table.name,self.source_id,
                                    self.table.clusterKey,self.table.clusterKey,
                                    self.table.primary_key),
                                  (self.pack_source(k),))
        self.load(self.table.cursor.fetchall()) # CACHE THIS CLUSTER
        return self.d[k] # RETURN EDGE DICT FOR THIS NODE
    def load(self,l=None,unpack=True):
        'load the specified rows (or all, if None provided) into local cache'
        if l is None:
            try: # IF ALREADY LOADED, NO NEED TO DO ANYTHING
                return self._isLoaded
            except AttributeError:
                pass
            self.table.cursor.execute('select %s,%s,%s from %s'
                                      %(self.source_id,self.target_id,
                                        self.edge_id,self.table.name))
            l=self.table.cursor.fetchall()
            self._isLoaded=True
            self.d.clear() # CLEAR OUR CACHE AS load() WILL REPLICATE EVERYTHING
        for source,target,edge in l: # SAVE TO OUR CACHE
            if unpack:
                source = self.unpack_source(source)
                target = self.unpack_target(target)
                edge = self.unpack_edge(edge)
            try:
                self.d[source] += [(target,edge)]
            except KeyError:
                d = self._edgeDictClass(self,source)
                d += [(target,edge)]
                self.d[source] = d
    def __invert__(self):
        'interface to reverse graph mapping'
        try:
            return self._inverse # INVERSE MAP ALREADY EXISTS
        except AttributeError:
            pass
        # JUST CREATE INTERFACE WITH SWAPPED TARGET & SOURCE
        self._inverse=SQLGraphClustered(self.table,self.target_id,self.source_id,
                                        self.edge_id,**graph_db_inverse_refs(self))
        self._inverse._inverse=self
        for source,d in self.d.iteritems(): # INVERT OUR CACHE
            self._inverse.load([(target,source,edge)
                                for (target,edge) in d.iteritems()],unpack=False)
        return self._inverse
    edges=SQLEdgesClusteredDescr() # CONSTRUCT EDGE INTERFACE ON DEMAND
    update = update_graph
    add_standard_packing_methods(locals())  ############ PACK / UNPACK METHODS
    def __iter__(self): ################# ITERATORS
        'uses db select; does not force load'
        return iter(self.keys())
    def keys(self):
        'uses db select; does not force load'
        self.table.cursor.execute('select distinct(%s) from %s'
                                  %(self.source_id,self.table.name))
        return [self.unpack_source(t[0])
                for t in self.table.cursor.fetchall()]
    methodFactory(['iteritems','items','itervalues','values'],
                  'lambda self:(self.load(),self.d.%s())[1]',locals())
    def __contains__(self,k):
        try:
            x=self[k]
            return True
        except KeyError:
            return False

class SQLIDGraphClustered(SQLGraphClustered):
    add_trivial_packing_methods(locals())
SQLGraphClustered._IDGraphClass = SQLIDGraphClustered

class SQLEdgesClustered(SQLGraphClustered):
    'edges interface for SQLGraphClustered'
    _edgeDictClass = list
    _pickleAttrs = SQLGraphClustered._pickleAttrs.copy()
    _pickleAttrs.update(dict(graph=0))
    def keys(self):
        self.load()
        result = []
        for edge_id,l in self.d.iteritems():
            for source_id,target_id in l:
                result.append((self.graph.unpack_source(source_id),
                               self.graph.unpack_target(target_id),
                               self.graph.unpack_edge(edge_id)))
        return result


def describeDBTables(name,cursor,idDict):
    """
    Get table info about database <name> via <cursor>, and store primary keys
    in idDict, along with a list of the tables each key indexes.
    """
    cursor.execute('use %s' % name)
    cursor.execute('show tables')
    tables={}
    l=[c[0] for c in cursor.fetchall()]
    for t in l:
        tname=name+'.'+t
        o=SQLTable(tname,cursor)
        tables[tname]=o
        if o.primary_key:
            if o.primary_key not in idDict:
                idDict[o.primary_key]=[]
            idDict[o.primary_key].append(o) # KEEP LIST OF TABLES WITH THIS PRIMARY KEY
        for f in o.description:
            if f[-3:]=='_id' and f not in idDict:
                idDict[f]=[]
    return tables



def indexIDs(tables,idDict=None):
    "Get an index of primary keys in the <tables> dictionary."
    if idDict==None:
        idDict={}
    for o in tables.values():
        if o.primary_key:
            if o.primary_key not in idDict:
                idDict[o.primary_key]=[]
            idDict[o.primary_key].append(o) # KEEP LIST OF TABLES WITH THIS PRIMARY KEY
        for f in o.description:
            if f[-3:]=='_id' and f not in idDict:
                idDict[f]=[]
    return idDict
        


def suffixSubset(tables,suffix):
    "Filter table index for those matching a specific suffix"
    subset={}
    for name,t in tables.items():
        if name.endswith(suffix):
            subset[name]=t
    return subset


PRIMARY_KEY=1

def graphDBTables(tables,idDict):
    g=dictgraph()
    for t in tables.values():
        for f in t.description:
            if f==t.primary_key:
                edgeInfo=PRIMARY_KEY
            else:
                edgeInfo=None
            g.setEdge(f,t,edgeInfo)
            g.setEdge(t,f,edgeInfo)
    return g

SQLTypeTranslation= {types.StringType:'varchar(32)',
                     types.IntType:'int',
                     types.FloatType:'float'}

def createTableFromRepr(rows,tableName,cursor,typeTranslation=None,
                        optionalDict=None,indexDict=()):
    """Save rows into SQL tableName using cursor, with optional
       translations of columns to specific SQL types (specified
       by typeTranslation dict).
       - optionDict can specify columns that are allowed to be NULL.
       - indexDict can specify columns that must be indexed; columns
       whose names end in _id will be indexed by default.
       - rows must be an iterator which in turn returns dictionaries,
       each representing a tuple of values (indexed by their column
       names).
    """
    try:
        row=rows.next() # GET 1ST ROW TO EXTRACT COLUMN INFO
    except StopIteration:
        return # IF rows EMPTY, NO NEED TO SAVE ANYTHING, SO JUST RETURN
    try:
        createTableFromRow(cursor, tableName,row,typeTranslation,
                           optionalDict,indexDict)
    except:
        pass
    storeRow(cursor,tableName,row) # SAVE OUR FIRST ROW
    for row in rows: # NOW SAVE ALL THE ROWS
        storeRow(cursor,tableName,row)

def createTableFromRow(cursor, tableName, row,typeTranslation=None,
                        optionalDict=None,indexDict=()):
    create_defs=[]
    for col,val in row.items(): # PREPARE SQL TYPES FOR COLUMNS
        coltype=None
        if typeTranslation!=None and col in typeTranslation:
            coltype=typeTranslation[col] # USER-SUPPLIED TRANSLATION
        elif type(val) in SQLTypeTranslation:
            coltype=SQLTypeTranslation[type(val)]
        else: # SEARCH FOR A COMPATIBLE TYPE
            for t in SQLTypeTranslation:
                if isinstance(val,t):
                    coltype=SQLTypeTranslation[t]
                    break
        if coltype==None:
            raise TypeError("Don't know SQL type to use for %s" % col)
        create_def='%s %s' %(col,coltype)
        if optionalDict==None or col not in optionalDict:
            create_def+=' not null'
        create_defs.append(create_def)
    for col in row: # CREATE INDEXES FOR ID COLUMNS
        if col[-3:]=='_id' or col in indexDict:
            create_defs.append('index(%s)' % col)
    cmd='create table if not exists %s (%s)' % (tableName,','.join(create_defs))
    cursor.execute(cmd) # CREATE THE TABLE IN THE DATABASE


def storeRow(cursor, tableName, row):
    row_format=','.join(len(row)*['%s'])
    cmd='insert into %s values (%s)' % (tableName,row_format)
    cursor.execute(cmd,tuple(row.values()))

def storeRowDelayed(cursor, tableName, row):
    row_format=','.join(len(row)*['%s'])
    cmd='insert delayed into %s values (%s)' % (tableName,row_format)
    cursor.execute(cmd,tuple(row.values()))


class TableGroup(dict):
    'provide attribute access to dbname qualified tablenames'
    def __init__(self,db='test',suffix=None,**kw):
        dict.__init__(self)
        self.db=db
        if suffix is not None:
            self.suffix=suffix
        for k,v in kw.items():
            if v is not None and '.' not in v:
                v=self.db+'.'+v  # ADD DATABASE NAME AS PREFIX
            self[k]=v
    def __getattr__(self,k):
        return self[k]
