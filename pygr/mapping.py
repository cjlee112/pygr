

from __future__ import generators
from schema import *
import classutil

class PathList(list):
    """Internal representation for storing both nodes and edges as list
    So filter functions can see both nodes and edges"""
    def __init__(self,nodes=None,edges=None):
        if nodes!=None:
            list.__init__(self,nodes)
        else:
            list.__init__(self)
        if edges!=None:
            self.edge=list(edges)
        else:
            self.edge=[]

    def append(self,val):
        list.append(self,val)
        self.edge.append(val)

    def extend(self,l):
        list.extend(self,l) # EXTEND TOP-LEVEL LIST AS USUAL
        try: # EXTEND OUR EDGE LIST AS WELL
            self.edge.extend(l.edge)
        except AttributeError: #IF l HAS NO EDGES, PAD OUR EDGE LIST WITH Nones
            self.edge.extend(len(l)*[None])



class Edge(list):
    "Interface to edge information."
    isDirected=False
    def __init__(self,graph,nodes,edgeInfo):
        self.graph=graph
        if edgeInfo:
            self.edgeInfo=edgeInfo
        list.__init__(self,nodes) # SAVE NODES AS TUPLE


    def __getattr__(self,attr):
        try:
            return getattr(self.edgeInfo,attr)
        except AttributeError:
            if isinstance(self.edgeInfo,types.DictType):
                return self.edgeInfo[attr] # TREAT edgeInfo AS ATTRIBUTE DICTIONARY
            raise AttributeError(attr)

    # SHOULD WE DEFINE A setattr HERE TOO, TO ALLOW USER TO ADD NEW ATTRIBUTE VALUES??
    # setattr IS PAINFUL TO IMPLEMENT, BECAUSE OF THE RECURSIVE REFERENCE PROBLEM

    def __cmp__(self,other): # DO WE NEED TO COMPARE EDGE INFO??
        if not isinstance(other,Edge): # CAN ONLY COMPARE A PAIR OF EDGES
            return -1
        diff=cmp(self.graph,other.graph)
        if diff: # NOT IN THE SAME GRAPH...
            return diff
        elif self.isDirected: # IF DIRECTED, JUST COMPARE IN CURRENT ORDER
            return tuple.__cmp__(self,other)
        else: # UNDIRECTED COMPARISON REQUIRES PUTTING BOTH IN SAME ORDER
            me=[i for i in self]
            you=[i for i in other]
            me.sort()
            you.sort()
            return cmp(me,you)

    # NEEDS SCHEMA SUPPORT: RETURN A SINGLE SCHEMA TUPLE DESCRIBING THIS EDGE.

class DirectedEdge(Edge):
    isDirected=True


# need a class to provide access to the edges in a graph
# iterator, membership test
#class EdgeSet



class dictEdge(dict):
    """2nd layer graph interface implemenation using dict.
    """
    dictClass=dict
    def __init__(self,graph,fromNode):
        self.graph=graph
        self.fromNode=fromNode
        self.dictClass.__init__(self) # INITIALIZE TOPLEVEL DICTIONARY

    def __iadd__(self,target):
        "Add edge from fromNode to target with no edge-info"
        self[target]=None
        return self # THIS IS REQUIRED FROM iadd()!!

    def __setitem__(self,target,edgeInfo):
        "Add edge from fromNode to target with edgeInfo"
        self.dictClass.__setitem__(self,target,edgeInfo)
        if target not in self.graph: # ADD NEW NODE TO THE NODE DICT
            self.graph+=target

    _setitem_=dict.__setitem__ # INTERNAL INTERFACE FOR SAVING AN ENTRY

    def __delitem__(self,target):
        "Delete edge from fromNode to target"
        try:
            self.dictClass.__delitem__(self,target)
        except KeyError: # GENERATE A MORE INFORMATIVE ERROR MESSAGE
            raise KeyError('No edge from node to target')

    def __isub__(self,target):
        "Delete edge from fromNode to target"
        self.__delitem__(target)
        return self # THIS IS REQUIRED FROM iadd()!!

    def edges(self):
        "Return iterator for accessing edges from fromNode"
        for target,edgeInfo in self.items():
            if isinstance(edgeInfo,Edge):
                yield edgeInfo
            else:
                yield Edge(self.graph,(self.fromNode,target),edgeInfo)

                

class dictGraph(dict):
    """Top layer graph interface implemenation using dict.
    """
    dictClass=dict
    edgeDictClass=dictEdge
    def __init__(self,schema=None,domain=None,range=None):
        if schema and domain and range:
            if domain not in schema:
                schema += domain #ADD DOMAIN AS NODE TO schema GRAPH
            schema[domain][range]=self
        self.dictClass.__init__(self) # INITIALIZE TOPLEVEL DICTIONARY

    def __iadd__(self,node,ruleSet=False):
        "Add node to graph with no edges"
        if node not in self:
            self.dictClass.__setitem__(self,node,self.edgeDictClass(self,node))
            if ruleSet==False:
                ruleSet=getschema(node,graph=self)
            for rule in ruleSet:
                if isinstance(rule[1],types.StringType): # ATTRIBUTE BINDING!
                    setattr(node,rule[1],self[node])  # BIND DIRECTLY TO ATTRIBUTE
        return self # THIS IS REQUIRED FROM iadd()!!

    def __setitem__(self,node,target):
        "This method exists only to support g[n]+=o.  Do not use as g[n]=foo."
        if self[node]!=target:
            raise ValueError('Incorrect usage.  Add edges using g[n]+=o or g[n][o]=edge.')

    def __delitem__(self,node):
        "Delete node from graph."
        # GRR, WE REALLY NEED TO FIND ALL EDGES THAT GO TO THIS NODE, DELETE THEM TOO
        try:
            self.dictClass.__delitem__(self,node)  # DO STUFF TO REMOVE IT HERE...
        except KeyError:
            raise KeyError('Node not present in mapping.')
        for rule in getschema(node,graph=self):
            if isinstance(rule[1],types.StringType): # ATTRIBUTE BINDING!
                delattr(node,rule[1])  # REMOVE ATTRIBUTE BINDING

    def __isub__(self,node):
        "Delete node from graph"
        self.__delitem__(node)
        return self # THIS IS REQUIRED FROM isub()!!

    def __hash__(self): # SO SCHEMA CAN INDEX ON GRAPHS...
        return id(self)

    def edges(self):
        "Return iterator for all edges in this graph"
        for edgedict in self.values():
            for edge in edgedict.edges():
                yield edge





class dictEdgeFB(dictEdge):
    "dictEdge subclass that saves both forward and backward edges"
    def __setitem__(self,target,edgeInfo):
        "Save edge in both forward and backward dicts."
        dictEdge.__setitem__(self,target,edgeInfo) # FORWARD EDGE
        try:
            d=self.graph._inverse[target]
        except KeyError:
            d=self.dictClass()
            self.graph._inverse[target]=d
        d[self.fromNode]=edgeInfo # SAVE BACKWARD EDGE

    def __invert__(self):
        "Get nodes with edges to this node"
        return self.graph._inverse[self.fromNode]

class dictGraphFB(dictGraph):
    "Graph that saves both forward and backward edges"
    def __init__(self,**kwargs):
        dictGraph.__init__(self,**kwargs)
        self._inverse=self.dictClass()

    def __invert__(self):
        "Get reverse mapping: edges TO a given node"
        return self._inverse

    def __delitem__(self,node):
        "Delete node from the graph"
        try:
            fromNodes=self._inverse[node] # 
            del self._inverse[node] # REMOVE FROM _inverse DICT
        except KeyError:
            pass
        else: # DELETE EDGES TO THIS NODE
            for i in fromNodes:
                del self[i][node]
        dictGraph.__delitem__(self,node)



def listUnion(ivals):
    'merge all items using union operator'
    union=None
    for ival in ivals:
        try:
            union+=ival
        except TypeError:
            union=ival
    return union


class DictQueue(dict):
    'each index entry acts like a queue; setitem PUSHES, and delitem POPS'
    def __setitem__(self,k,val):
        try:
            dict.__getitem__(self,k).append(val)
        except KeyError:
            dict.__setitem__(self,k,[val])
    def __getitem__(self,k):
        return dict.__getitem__(self,k)[0]
    def __delitem__(self,k):
        l=dict.__getitem__(self,k)
        del l[0]
        if len(l)==0:
            dict.__delitem__(self,k)




################################ PYGR.DATA.SCHEMA - AWARE CLASSES BELOW




class Collection(object):
    'flexible storage mapping ID --> OBJECT'
    def __init__(self,saveDict=None,dictClass=dict,**kwargs):
        '''saveDict, if not None, is the internal mapping to use as our storage.
        filename: if provided, is a file path to a shelve (BerkeleyDB) file to
              store the data in.
        dictClass: if provided, is the class to use for storage of the dict data.'''
        if saveDict is not None:
            self.d = saveDict
        elif 'filename' in kwargs: # USE A SHELVE (BERKELEY DB)
            try:
                if kwargs['intKeys']: # ALLOW INT KEYS, HAVE TO USE IntShelve
                    self.__class__ = IntShelve
                    return self.__init__(**kwargs)
            except KeyError:
                pass
            self.__class__ = PicklableShelve
            return self.__init__(**kwargs)
        else:
            self.d = dictClass()
        classutil.apply_itemclass(self,kwargs)
    def __getitem__(self,k): return self.d[k]
    def __setitem__(self,k,v): self.d[k] = v
    def __delitem__(self,k): del self.d[k]
    def __len__(self): return len(self.d)
    def __contains__(self,k): return k in self.d
    def __iter__(self): return iter(self.d)
    def __getattr__(self,attr):
        if attr=='__setstate__': # PREVENT INFINITE RECURSE IN UNPICKLE
            raise AttributeError
        return getattr(self.d,attr)

class PicklableShelve(Collection):
    'persistent storage mapping ID --> OBJECT'
    def __init__(self,filename,mode=None,**kwargs):
        self.filename = filename
        if mode=='c':
            self.mode = 'w'
        else:
            self.mode = mode
        self.d = classutil.open_shelve(filename,mode)
        classutil.apply_itemclass(self,kwargs)
    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(filename=0,mode=0)
    def __setitem__(self,k,v):
        try:
            self.d[k]=v
        except TypeError:
            raise TypeError('to allow int keys, you must pass intKeys=True to constructor!')


class IntShelve(PicklableShelve):
    'provides an interface to shelve that can use int as key'
    def saveKey(self,i):
        'convert to string key'
        if isinstance(i,int):
            return 'int:%s'%i
        elif isinstance(i,str):
            return i
        try:
            return 'int:%s'%int(i)
        except TypeError:
            pass
        raise KeyError('IntShelve can only save int or str as key')
    def trueKey(self,k):
        "convert back to key's original format"
        if k.startswith('int:'):
            return int(k[4:])
        else:
            return k
    def __getitem__(self,k):
        return self.d[self.saveKey(k)]
    def __setitem__(self,k,v):
        self.d[self.saveKey(k)]=v
    def __delitem__(self,k): del self.d[self.saveKey(k)]
    def __contains__(self,k):
        return self.saveKey(k) in self.d
    def __iter__(self): ################ STANDARD ITERATOR METHODS
        for k in self.d:
            yield self.trueKey(k)
    def keys(self): return [k for k in self]
    def iteritems(self):
        for k,v in self.d.iteritems():
            yield self.trueKey(k),v
    def items(self): return [k for k in self.iteritems()]
    def close(self): self.d.close()



class MappingInverse(object):
    def __init__(self,db):
        self._inverse=db
        self.attr=db.inverseAttr
    def __getitem__(self,k):
        return self._inverse.sourceDB[getattr(k,self.attr)]
    def __invert__(self): return self._inverse

class Mapping(object):
    '''dict-like class suitable for persistent usages.  Extracts ID values from
    keys and values passed to it, and saves IDs into its internal dictionary
    instead of the actual objects.  Thus, the external interface is objects,
    but the internal storage is ID values.'''
    def __init__(self,sourceDB,targetDB,saveDict=None,IDAttr='id',targetIDAttr='id',
                 itemAttr=None,multiValue=False,inverseAttr=None,**kwargs):
        '''sourceDB: dictionary that maps key ID values to key objects
        targetDB: dictionary that maps value IDs to value objects
        saveDict, if not None, is the internal mapping to use as our storage
        IDAttr: attribute name to obtain an ID from a key object
        targetIDAttr: attribute name to obtain an ID from a value object
        itemAttr, if not None, the attribute to obtain target (value) ID
           from an internal storage value
        multiValue: if True, treat each value as a list of values.
        filename: if provided, is a file path to a shelve (BerkeleyDB) file to
              store the data in.
        dictClass: if not None, is the class to use for storage of the dict data'''
        if saveDict is None:
            self.d=classutil.get_shelve_or_dict(**kwargs)
        else:
            self.d=saveDict
        self.IDAttr=IDAttr
        self.targetIDAttr=targetIDAttr
        self.itemAttr=itemAttr
        self.multiValue=multiValue
        self.sourceDB=sourceDB
        self.targetDB=targetDB
        if inverseAttr is not None:
            self.inverseAttr=inverseAttr
    def __getitem__(self,k):
        kID=getattr(k,self.IDAttr)
        return self.getTarget(self.d[kID])
    def getTarget(self,vID):
        if self.itemAttr is not None:
            vID=getattr(vID,self.itemAttr)
        if self.multiValue:
            return [self.targetDB[j] for j in vID]
        else:
            return self.targetDB[vID]
    def __setitem__(self,k,v):
        if self.multiValue:
            v=[getattr(x,self.targetIDAttr) for x in v]
        else:
            v=getattr(v,self.targetIDAttr)
        self.d[getattr(k,self.IDAttr)]=v
    def __delitem__(self,k):
        del self.d[getattr(k,self.IDAttr)]
    def __contains__(self,k):
        return getattr(k,self.IDAttr) in self.d
    def __len__(self): return len(self.d)
    def clear(self): self.d.clear()
    def copy(self):
        return Mapping(self.sourceDB,self.targetDB,self.d.copy(),self.IDAttr,
                      self.targetIDAttr,self.itemAttr,self.multiValue)
    def update(self,b):
        for k,v in b.iteritems():
            self[k]=v
    def get(self,k,v=None):
        try:
            return self[k]
        except KeyError:
            return v
    def setdefault(self,k,v=None):
        try:
            return self[k]
        except KeyError:
            self[k]=v
            return v
    def pop(self,k,v=None):
        try:
            v=self[k]
        except KeyError:
            return v
        del self[k]
        return v
    def popitem(self):
        kID,vID=self.d.popitem()
        return kID,self.getTarget(vID)
    def __iter__(self): ######################## ITERATORS
        for kID in self.d:
            yield self.sourceDB[kID]
    def keys(self): return [k for k in self]
    def itervalues(self):
        for vID in self.d.itervalues():
            yield self.getTarget(vID)
    def values(self): return [v for v in self]
    def iteritems(self):
        for kID,vID in self.d.iteritems():
            yield self.sourceDB[kID],self.getTarget(vID)
    def items(self): return [x for x in self.iteritems()]
    def __invert__(self):
        try:
            return self._inverse
        except AttributeError:
            self._inverse=MappingInverse(self)
            return self._inverse





class IDNodeDict(object):
    """2nd layer graph interface implementation using proxy dict.
       e.g. shelve."""
    dictClass=dict
    def __init__(self,graph,fromNode):
        self.graph=graph
        self.fromNode=fromNode

    def __getitem__(self,target): ############# ACCESS METHODS
        edgeID=self.graph.d[self.fromNode][target.id]
        return self.graph.edgeDB[edgeID]

    def __setitem__(self,target,edgeInfo):
        "Add edge from fromNode to target with edgeInfo"
        if edgeInfo is not None:
            self.graph.d[self.fromNode][target.id]=edgeInfo.id
        self.graph+=target # ADD NEW NODE TO THE NODE DICT

    def __delitem__(self,target):
        "Delete edge from fromNode to target"
        try:
            del self.graph.d[self.fromNode][target.id]
        except KeyError: # GENERATE A MORE INFORMATIVE ERROR MESSAGE
            raise KeyError('No edge from node to target')
    ######### CONVENIENCE METHODS THAT USE THE ACCESS METHODS ABOVE
    def __iadd__(self,target):
        "Add edge from fromNode to target with no edge-info"
        self[target]=None
        return self # THIS IS REQUIRED FROM iadd()!!

    def __isub__(self,target):
        "Delete edge from fromNode to target"
        self.__delitem__(target)
        return self # THIS IS REQUIRED FROM iadd()!!

    def edges(self):
        "Return iterator for accessing edges from fromNode"
        for target,edgeInfo in self.graph.d[self.fromNode].items():
            yield self.graph.sourceDB[self.fromNode],\
                  self.graph.targetDB[target],\
                  self.graph.edgeDB[edgeInfo]
    def keys(self): return [k[1] for k in self.edges()] ##### ITERATORS
    def values(self): return [k[2] for k in self.edges()]
    def items(self): return [k[1:3] for k in self.edges()]
    def __iter__(self):
        for source,target,edgeInfo in self.edges():
            yield target
    def itervalues(self):
        for source,target,edgeInfo in self.edges():
            yield edgeInfo
    def iteritems(self):
        for source,target,edgeInfo in self.edges():
            yield target,edgeInfo


class IDGraphEdges(object):
    '''provides iterator over edges as (source,target,edge) tuples
       and getitem[edge] --> [(source,target),...]'''
    def __init__(self,g):
        self.g=g
        self.d=g.d.edges # GET EDGES INTERFACE IN ID-SPACE
    def __iter__(self):
        for sourceID,targetID,edgeID in self.d:
            yield (self.g.sourceDB[sourceID],self.g.targetDB[targetID],
                   self.g.edgeDB[edgeID])
    def __getitem__(self,edge):
        l=[]
        for sourceID,targetID in self.d[edge.id]:
            l.append((self.g.sourceDB[sourceID],self.g.targetDB[targetID]))
        return l

class IDGraphEdgeDescriptor(object):
    'provides interface to edges on demand'
    def __get__(self,obj,objtype):
        return IDGraphEdges(obj)
    
class IDGraph(object):
    """Top layer graph interface implemenation using proxy dict.
       Works with dict, shelve, any mapping interface."""
    edgeDictClass=IDNodeDict # DEFAULT EDGE DICT
    def __init__(self,proxyDict=None,sourceDB=None,targetDB=None,
                 edgeDB=None,**kwargs):
        if proxyDict is not None: # USE THE SUPPLIED STORAGE
            self.d=proxyDict
        else: # ACCESS THE DATA VIA A SHELVE
            self.d=IntShelve(**kwargs)
        if sourceDB is not None:
            self.sourceDB=sourceDB
        if targetDB is not None:
            self.targetDB=targetDB
        if edgeDB is not None:
            self.edgeDB=edgeDB
    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(d='proxyDict')

    # USE METHOD FROM THE SHELVE...
    classutil.methodFactory(['__contains__'],'lambda self,obj:self.d.%s(obj.id)',
                            locals())
    def __iter__(self):
        for node in self.d:
            yield self.sourceDB[node]
    def keys(self): return [k for k in self]
    def itervalues(self):
        for node in self.d:
            yield self.edgeDictClass(self,node)
    def values(self): return [v for v in self.itervalues()]
    def iteritems(self):
        for node in self.d:
            yield self.sourceDB[node],self.edgeDictClass(self,node)
    def items(self): return [v for v in self.iteritems()]
    edges=IDGraphEdgeDescriptor()

    def __iadd__(self,node):
        "Add node to graph with no edges"
        node=node.id # INTERNALL JUST USE ITS id
        if node not in self.d:
            self.d[node]={} # INITIALIZE TOPLEVEL DICTIONARY
        return self # THIS IS REQUIRED FROM iadd()!!

    def __getitem__(self,node):
        if node in self:
            return self.edgeDictClass(self,node.id)
        raise KeyError('node not in graph')
    def __setitem__(self,node,target):
        "This method exists only to support g[n]+=o.  Do not use as g[n]=foo."
        node=node.id # INTERNALL JUST USE ITS id
        try:
            if node==target.fromNode:
                return
        except AttributeError:
            pass
        raise ValueError('Incorrect usage.  Add edges using g[n]+=o or g[n][o]=edge.')

    def __delitem__(self,node):
        "Delete node from graph."
        node=node.id # INTERNALL JUST USE ITS id
        # GRR, WE REALLY NEED TO FIND ALL EDGES THAT GO TO THIS NODE, DELETE THEM TOO
        try:
            del self.d[node]  # DO STUFF TO REMOVE IT HERE...
        except KeyError:
            raise KeyError('Node not present in mapping.')

    def __isub__(self,node):
        "Delete node from graph"
        self.__delitem__(node)
        return self # THIS IS REQUIRED FROM isub()!!

    def __invert__(self):
        'get an interface to the inverse graph mapping'
        try: # CACHED
            return self._inverse
        except AttributeError: # NEED TO CONSTRUCT INVERSE MAPPING
            self._inverse=IDGraph(~(self.d),self.targetDB,self.sourceDB,self.edgeDB)
            self._inverse._inverse=self
            return self._inverse
    def __hash__(self): # SO SCHEMA CAN INDEX ON GRAPHS...
        return id(self)


