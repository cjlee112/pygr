

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

