

from schema import *

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


class PathList(list):
    """Internal representation for storing both nodes and edges as list
    So filter functions can see both nodes and edges"""
    def __init__(self):
        list.__init__(self)
        self.edge=[]

    def append(self,val):
        list.append(self,val)
        self.edge.append(val)


def newfilter(self,filter,filterClass):
    "internal function for spawning another layer of Attr/FilterPathGraph"
    l=filterClass(filter,self._last._temp,self._path,self._last._depth+1)
    self._last._next=l
    self._last=l
    return self


class AttrPathGraph(object):
    "Interface for building query graphs using attributes"
    def __init__(self,attr,graph=None,path=None,depth=0):
        #print 'creating instance of %s' % self.__class__
        self._graph=graph
        self._attr=attr
        self._last=self
        if path==None:
            self._path=PathList()
        else:
            self._path=path
        self._path.append(None)
        self._depth=depth
        self._temp=[None]
        self._next=None # NEVER USE hasattr() ON ME!  IT WILL TRIGGER getattr()...
        self._contents=None

    def __getattr__(self,attr): # THIS CAUSES SIDE EFFECTS!  PLEASE CLEAN THIS UP!!
        "extend this path, using the named attribute"
        return newfilter(self,attr,AttrPathGraph) # SOLUTION IS TO DO DEEP-COPY...

    def filter(self,filter):
        "add a filter to this path"
        return newfilter(self,filter,self.filterClass)

    def __iter__(self):
        """iterate over all paths that satisfy this PathGraph,
        returning each path as a list of nodes.
        This method specifically implements attribute access."""
        if self._next!=None: # WE HAVE MORE LAYERS BELOW US, SO NEED TO PASS INFO...
            if hasattr(self._graph,'items'): # FOR DICT CONTAINER, GET VALUES AS EDGES
                for o,e in self._graph.items(): # ITERATE OVER ALL OBJECTS IN THIS LAYER
                    self._path[self._depth]=o # SAVE IT IN CURRENT PATH
                    self._path.edge[self._depth]=e # SAVE EDGE INFO TOO!
                    self._next._graph=getattr(o,self._attr) # PASS ATTR TO NEXT LAYER
                    for n in self._next:
                        n.insert(0,o)
                        yield n
            else: # FOR NON-DICT CONTAINER, NO EDGE INFO!
                self._path.edge[self._depth]=None
                for o in self._graph: # ITERATE OVER ALL OBJECTS IN THIS LAYER
                    self._path[self._depth]=o # SAVE IT IN CURRENT PATH
                    self._next._graph=getattr(o,self._attr)
                    for n in self._next: # GET RESULTS FROM THE NEXT LAYER
                        n.insert(0,o) # ADD OUR OBJECT AT HEAD OF LIST
                        yield n
        else: # LAST LAYER, SO JUST RETURN OUR ITEMS
            for o in self._graph:
                for n in getattr(o,self._attr):
                    yield [o,n]

    def __contains__(self,item):
        "try to speed up multiple membership tests on the same PathGraph"
        if self._contents==None:
            self._contents=[o[-1] for o in self]
        return item in self._contents

class FilterPathGraph(AttrPathGraph):
    "Adds a filter to a PathGraph"
    def __iter__(self):
        "This method specifically implements filtering of input from previous layer"
        if self._next!=None:
            if hasattr(self._graph,'items'):
                for o,e in self._graph.items():
                    self._path[self._depth]=o
                    self._path.edge[self._depth]=e
                    if self._attr(self._path):
                        self._temp[0]=o
                        for n in self._next:
                            n.insert(0,o)
                            yield n
            else:
                self._path.edge[self._depth]=None
                for o in self._graph:
                    self._path[self._depth]=o
                    if self._attr(self._path):
                        self._temp[0]=o
                        for n in self._next:
                            n.insert(0,o)
                            yield n
        else:
            for o in self._graph:
                self._path[self._depth]=o
                if self._attr(self._path):
                    yield [o]


AttrPathGraph.filterClass=FilterPathGraph # SOLUTION TO REFERENCE ORDER CATCH-22








def newAttrPath(self,attr):
    return AttrPathGraph(attr,graph=self)
def newFilterPath(self,attr):
    return FilterPathGraph(attr,graph=self)


class dictEdge(dict):
    """2nd layer graph interface implemenation using dict.
    Uses __getattr__ to pass requests for unknown attributes
    down to the nodes that it contains, using the PathGraph interface.
    This means you should be VERY careful about accessing nonexistent
    attributes of this class.  Specifically, never use hasattr(),
    since it will ALWAYS succeed.  I guess __getattr__ ought to check
    if the attribute is actually present on the nodes before firing
    up the PathGraph interface..."""
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

    __getattr__=newAttrPath
    filter=newFilterPath
                

class dictGraph(dict):
    """Top layer graph interface implemenation using dict.
    Uses __getattr__ to pass requests for unknown attributes
    down to the nodes that it contains, using the PathGraph interface.
    This means you should be VERY careful about accessing nonexistent
    attributes of this class.  Specifically, never use hasattr(),
    since it will ALWAYS succeed.  I guess __getattr__ ought to check
    if the attribute is actually present on the nodes before firing
    up the PathGraph interface..."""
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

    __getattr__=newAttrPath
    filter=newFilterPath
