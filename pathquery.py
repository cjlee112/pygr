
from mapping import *


def newfilter(self,filter,filterClass):
    "internal function for spawning another layer of Attr/FilterPathGraph"
    l=filterClass(filter,self._last._temp,self._path,self._last._depth+1)
    self._last._next=l
    self._last=l
    return self


class AttrPathGraph(object):
    "Interface for building query graphs using attributes"
    def __init__(self,attr,graph=None,path=None,depth=0):
        #print 'creating instance of %s:%s' % (self.__class__,attr)
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

    def __rshift__(self,graph):
        "add a join step to this path"
        return newfilter(self,graph,self.joinClass)

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
                        n.edge.insert(0,e)
                        yield n
            else: # FOR NON-DICT CONTAINER, NO EDGE INFO!
                self._path.edge[self._depth]=None
                for o in self._graph: # ITERATE OVER ALL OBJECTS IN THIS LAYER
                    self._path[self._depth]=o # SAVE IT IN CURRENT PATH
                    self._next._graph=getattr(o,self._attr)
                    for n in self._next: # GET RESULTS FROM THE NEXT LAYER
                        n.insert(0,o) # ADD OUR OBJECT AT HEAD OF LIST
                        n.edge.insert(0,None)
                        yield n
        else: # LAST LAYER, SO JUST RETURN OUR ITEMS
            if hasattr(self._graph,'items'): # FOR DICT CONTAINER, GET VALUES AS EDGES
                for o,e in self._graph.items(): # ITERATE OVER ALL OBJECTS IN THIS LAYER
                    g=getattr(o,self._attr)
                    if hasattr(g,'items'):
                        for n,e2 in g.items():
                            yield PathList((o,n),(e,e2))
                    else:
                        for n in g:
                            yield PathList((o,n),(e,None))
            else:
                for o in self._graph:
                    g=getattr(o,self._attr)
                    if hasattr(g,'items'):
                        for n,e2 in g.items():
                            yield PathList((o,n),(None,e2))
                    else:
                        for n in g:
                            yield PathList((o,n))

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
                            n.edge.insert(0,e)
                            yield n
            else:
                self._path.edge[self._depth]=None
                for o in self._graph:
                    self._path[self._depth]=o
                    if self._attr(self._path):
                        self._temp[0]=o
                        for n in self._next:
                            n.insert(0,o)
                            n.edge.insert(0,None)
                            yield n
        else:
            if hasattr(self._graph,'items'): # FOR DICT CONTAINER, GET VALUES AS EDGES
                for o,e in self._graph.items(): # ITERATE OVER ALL OBJECTS IN THIS LAYER
                    self._path[self._depth]=o
                    self._path.edge[self._depth]=e
                    if self._attr(self._path):
                        yield PathList((o,),(e,))
            else:
                for o in self._graph:
                    self._path[self._depth]=o
                    if self._attr(self._path):
                        yield PathList((o,))


AttrPathGraph.filterClass=FilterPathGraph # SOLUTION TO REFERENCE ORDER CATCH-22

class GraphPathGraph(AttrPathGraph):
    "Adds a graph join step to a PathGraph"
    def __iter__(self):
        """iterate over all paths that satisfy this PathGraph,
        returning each path as a list of nodes.
        This method specifically implements join with graph stored as _attr."""
        if self._next!=None: # WE HAVE MORE LAYERS BELOW US, SO NEED TO PASS INFO...
            if hasattr(self._graph,'items'): # FOR DICT CONTAINER, GET VALUES AS EDGES
                for o,e in self._graph.items(): # ITERATE OVER ALL OBJECTS IN THIS LAYER
                    self._path[self._depth]=o # SAVE IT IN CURRENT PATH
                    self._path.edge[self._depth]=e # SAVE EDGE INFO TOO!
                    try:
                        self._next._graph=self._attr[o] # USE GRAPH TO GET NEXT LAYER
                    except KeyError:
                        pass # OUR NODE MAY JUST NOT BE IN TARGET GRAPH, NEED TO HANDLE THAT
                    else:
                        for n in self._next:
                            n.insert(0,o)
                            n.edge.insert(0,e)
                            yield n
            else: # FOR NON-DICT CONTAINER, NO EDGE INFO!
                self._path.edge[self._depth]=None
                for o in self._graph: # ITERATE OVER ALL OBJECTS IN THIS LAYER
                    self._path[self._depth]=o # SAVE IT IN CURRENT PATH
                    try:
                        self._next._graph=self._attr[o] # USE GRAPH TO GET NEXT LAYER
                    except KeyError:
                        pass # OUR NODE MAY JUST NOT BE IN TARGET GRAPH, NEED TO HANDLE THAT
                    else:
                        for n in self._next: # GET RESULTS FROM THE NEXT LAYER
                            n.insert(0,o) # ADD OUR OBJECT AT HEAD OF LIST
                            n.edge.insert(0,None)
                            yield n
        else: # LAST LAYER, SO JUST RETURN OUR ITEMS
            if hasattr(self._graph,'items'): # FOR DICT CONTAINER, GET VALUES AS EDGES
                for o,e in self._graph.items():
                    try:
                        g=self._attr[o]
                    except KeyError:
                        pass # OUR NODE MAY JUST NOT BE IN TARGET GRAPH, NEED TO HANDLE THAT
                    else:
                        if hasattr(g,'items'):
                            for n,e2 in g.items():
                                yield PathList((o,n),(e,e2))
                        else:
                            for n in g:
                                yield PathList((o,n),(e,None))
            else:
                for o in self._graph:
                    try:
                        g=self._attr[o]
                    except KeyError:
                        pass # OUR NODE MAY JUST NOT BE IN TARGET GRAPH, NEED TO HANDLE THAT
                    else:
                        if hasattr(g,'items'):
                            for n,e2 in g.items():
                                yield PathList((o,n),(None,e2))
                        else:
                            for n in g:
                                yield PathList((o,n))

AttrPathGraph.joinClass=GraphPathGraph # SOLUTION TO REFERENCE ORDER CATCH-22






def newAttrPath(self,attr):
    return AttrPathGraph(attr,graph=self)
def newFilterPath(self,attr):
    return FilterPathGraph(attr,graph=self)
def newJoinPath(self,attr):
    return GraphPathGraph(attr,graph=self)


# ADD WRAPPER FUNCTIONS TO dictEdge and dictGraph SO THEY PROVIDE ACCESS TO
# PATH QUERY INTERFACE
class PathQueryDictEdge(dictEdge):
    """Uses __getattr__ to pass requests for unknown attributes
    down to the nodes that it contains, using the PathGraph interface.
    This means you should be VERY careful about accessing nonexistent
    attributes of this class.  Specifically, never use hasattr(),
    since it will ALWAYS succeed.  I guess __getattr__ ought to check
    if the attribute is actually present on the nodes before firing
    up the PathGraph interface..."""
    __getattr__=newAttrPath
    filter=newFilterPath
    __rshift__=newJoinPath

class PathQueryDictGraph(dictGraph):
    """Uses __getattr__ to pass requests for unknown attributes
    down to the nodes that it contains, using the PathGraph interface.
    This means you should be VERY careful about accessing nonexistent
    attributes of this class.  Specifically, never use hasattr(),
    since it will ALWAYS succeed.  I guess __getattr__ ought to check
    if the attribute is actually present on the nodes before firing
    up the PathGraph interface..."""
    __getattr__=newAttrPath
    filter=newFilterPath
    __rshift__=newJoinPath

from poa import *
class PathQueryTempIntervalDict(TempIntervalDict):
    filter=newFilterPath
    __rshift__=newJoinPath

class AlignPathGraph(GraphPathGraph):
    def __iter__(self):
        "Wrapper around GraphPathGraph iterator, designed for alignments"
        for i in GraphPathGraph.__iter__(self):
            clipUnalignedRegions(i) # RESTRICT TO ACTUAL REGION OF ALIGNMENT
            yield i

def newAlignJoinPath(self,graph):
    q=AlignPathGraph(self,self)
    return q >> graph

class PathQueryPathMapping(PathMapping):
    filter=newFilterPath
    __rshift__=newAlignJoinPath
