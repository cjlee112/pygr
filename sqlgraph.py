

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
    def load(self,oclass=None):
        "Load all data from the table"
        if oclass is None:
            oclass=self.oclass
        self.cursor.execute('select * from %s' % self.name)
        l=self.cursor.fetchall()
        for t in l:
            o=oclass(t)
            self[getattr(o,self.primary_key)]=o
        self.__class__=SQLTableBase # ONLY CAN LOAD ONCE, SO REVERT TO BASE CLASS

    def select(self,whereClause,params=None,oclass=None):
        "Generate the list of objects that satisfy the database SELECT"
        if oclass is None:
            oclass=self.oclass
        self.cursor.execute('select t1.* from %s t1 %s' % (self.name,whereClause),params)
        l=self.cursor.fetchall()
        for t in l:
            o=oclass(t)
            if self.primary_key is not None:
                id=getattr(o,self.primary_key)
                try: # IF ALREADY LOADED IN OUR DICTIONARY, JUST RETURN THAT ENTRY
                    yield self[id]
                except KeyError:
                    self[id]=o # OTHERWISE HAVE TO SAVE THE NEW ENTRY
            yield o


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


class SQLTableMultiNoCache(SQLTableBase):
    "Trivial on-the-fly access for table with key that returns multiple rows"
    _distinct_key='id' # DEFAULT COLUMN TO USE AS KEY
    def __iter__(self):
        self.cursor.execute('select distinct(%s) from %s'
                            %(self._distinct_key,self.name))
        l=self.cursor.fetchall() # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        for row in l:
            yield row[0]

    def __getitem__(self,id):
        self.cursor.execute('select * from %s where %s=%%s'
                            %(self.name,self._distinct_key),(id,))
        l=self.cursor.fetchall() # PREFETCH ALL ROWS, SINCE CURSOR MAY BE REUSED
        if not hasattr(self,'oclass'):
            self.objclass() # GENERATE DEFAULT OBJECT CLASS BASED ON TupleO
        for row in l:
            yield self.oclass(row)


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
    row=rows.next() # GET 1ST ROW TO EXTRACT COLUMN INFO
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
