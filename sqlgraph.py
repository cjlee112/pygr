

from mapping import *
import types
    

class TupleO(object):
    """Provide attribute interface to a tuple.  Subclass this and create _attrcol
    that maps attribute names to tuple index values."""
    def __init__(self,data):
        self.data=data
    def __getattr__(self,attr):
        return self.data[self._attrcol[attr]]


class SQLRow(object):
    """Provide transparent interface to a row in the database: attribute access
       will be mapped to SELECT of the appropriate column, but data is not cached
       on this object.
    """
    def __init__(self,table,id):
        self.table=table
        self.id=id

    def _select(self,what):
        "Get SQL select expression for this row"
        self.table.cursor.execute('select %s from %s where %s=%%s'
                                  % (what,self.table.name,self.table.primary_key),(self.id,))
        l=self.table.cursor.fetchall()
        if len(l)!=1:
            raise KeyError('%s %s not found in %s, or not unique'
                           % (str(self.id),what,self.name))
        return l[0][0] # RETURN THE SINGLE FIELD WE REQUESTED

    def _attrSQL(self,attr):
        "Translate python attribute name to appropriate SQL expression"
        if attr=='id':
            attr=self.table.primary_key
        else: # MAKE SURE THIS ATTRIBUTE CAN BE MAPPED TO DATABASE EXPRESSION
            try:
                field=self.table.data[attr]
            except KeyError:
                raise AttributeError('%s not a valid column in %s' % (attr,self.table.name))
            if isinstance(field,types.StringType):
                attr=field # USE ALIASED EXPRESSION FOR DATABASE SELECT INSTEAD OF attr
        return attr

    def __getattr__(self,attr):
        return self._select(self._attrSQL(attr))

class SQLTableBase(dict):
    "Store information about an SQL table as dict keyed by primary key"
    def __init__(self,name,cursor):
        dict.__init__(self) # INITIALIZE EMPTY DICTIONARY
        cursor.execute('describe %s' % name)
        columns=cursor.fetchall()
        self.cursor=cursor
        self.name=name
        self.primary_key=None
        self.indexed={}
        self.data={}
        self.description={}
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

    def __repr__(self):
        return '<SQL table '+self.name+'>'

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
        if oclass==None: # DEFAULT: SUBCLASS TupleO TO PROVIDE ATTRIBUTE ACCESS
            class foo(TupleO):
                pass
            oclass=foo
        if issubclass(oclass,TupleO) and not hasattr(oclass,'_attrcol'):
            oclass._attrcol=self.data # BIND ATTRIBUTE LIST TO TUPLEO INTERFACE
        if hasattr(oclass,'_tableclass') and not isinstance(self,oclass._tableclass):
            self.__class__=oclass._tableclass # ROW CLASS CAN OVERRIDE OUR CURRENT TABLE CLASS
        self.oclass=oclass


def iterSQLKey(self):
    self.cursor.execute('select %s from %s' %(self.primary_key,self.name))
    l=self.cursor.fetchall() # GET ALL AT ONCE, SINCE OTHER CALLS MAY REUSE THIS CURSOR...
    for t in l:
        yield t[0]


class SQLTable(SQLTableBase):
    "Provide on-the-fly access to rows in the database, caching the results in dict"
    __iter__=iterSQLKey
    def load(self,oclass):
        "Load all data from the table"
        self.cursor.execute('select * from %s' % self.name)
        l=self.cursor.fetchall()
        for t in l:
            o=oclass(t)
            self[getattr(o,self.primary_key)]=o
        self.__class__=SQLTableBase # ONLY CAN LOAD ONCE, SO REVERT TO BASE CLASS

    def __getitem__(self,k): # FIRST TRY LOCAL INDEX, THEN TRY DATABASE
        try:
            return dict.__getitem__(self,k) # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            self.cursor.execute('select * from %s where %s=%%s'
                                % (self.name,self.primary_key),(k,))
            l=self.cursor.fetchall()
            if len(l)!=1:
                raise KeyError('%s not found in %s, or not unique' %(str(k),self.name))
            try:
                o=self.oclass(l[0]) # SAVE USING SPECIFIED OBJECT CLASS
            except AttributeError:
                self.objclass() # CREATE A CLASS FOR OUR ROW-OBJECT
                o=self.oclass(l[0]) # TRY AGAIN...
            dict.__setitem__(self,k,o) # CACHE IT IN LOCAL DICTIONARY
            return o


class SQLTableNoCache(SQLTableBase):
    "Provide on-the-fly access to rows in the database, but never cache results"
    oclass=SQLRow # DEFAULT OBJECT CLASS FOR ROWS...
    __iter__=iterSQLKey

    def __getitem__(self,k): # FIRST TRY LOCAL INDEX, THEN TRY DATABASE
        try:
            return dict.__getitem__(self,k) # DIRECTLY RETURN CACHED VALUE
        except KeyError: # NOT FOUND, SO TRY THE DATABASE
            o=self.oclass(self,k) # RETURN AN EMPTY CONTAINER FOR ACCESSING THIS ROW
            dict.__setitem__(self,k,o) # STORE EMPTY CONTAINER IN LOCAL DICTIONARY
            return o
    def addAttrAlias(self,**kwargs):
        self.data.update(kwargs) # ALIAS KEYS TO EXPRESSION VALUES

SQLRow._tableclass=SQLTableNoCache  # SQLRow IS FOR NON-CACHING TABLE INTERFACE


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
