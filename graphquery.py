

class GraphQueryIterator(object):
    """iterator for a single node in graph query.  Subclasses provide different
       flavors of generator methods: graph w/ edges; container; attr; function etc."""
    def __init__(self,fromNode,queryNode,dataGraph,queryGraph,dataMatch,queryMatch):
        self.fromNode=fromNode
        self.queryNode=queryNode
        self.dataGraph=dataGraph
        self.queryGraph=queryGraph
        self.dataMatch=dataMatch
        self.queryMatch=queryMatch
        self.dataNode=None
        if fromNode!=None and queryNode!=None and queryGraph[fromNode][queryNode]!=None:
            for attr,val in queryGraph[fromNode][queryNode].items(): # SAVE OUR EDGE INFO
                setattr(self,attr,val)  # JUST ATTACH EDGE INFO AS ATTRIBUTES OF THIS OBJ
##         try:
##             self.nq=len(self.queryGraph[self.queryNode])
##         except KeyError:
##             self.nq=0

    def restart(self):
        "reset the iterator to its beginning"
        self.mustMark=True
        if self.fromNode != None:
            self.dataNode=self.queryMatch[self.fromNode]
        if self.queryNode in self.queryMatch: # ALREADY ASSIGNED TO A DATA NODE
            self.mustMark=False
            self.iterator=self.closure()
        else:
            self.iterator=self.generate()

    def closure(self):
        "this node is already matched.  Make sure there exists path to it (closure)"
        targetNode=self.queryMatch[self.queryNode]
        container=self.dataGraph[self.dataNode]
        try: # GENERATE IFF container HAS EDGE TO targetNode
            yield targetNode,container[targetNode]
        except KeyError:pass

    def generate(self):
        "generate all neighbors of data node matched to fromNode"
        try:
            it=self.dataGraph[self.dataNode]
        except KeyError:
            pass
        else:
            for i,e in it.items():
                if i not in self.dataMatch:
                    yield i,e

    def next(self):
        "returns the next node from iterator that passes all tests"
        if self.mustMark and self.queryNode in self.queryMatch:
            i=self.queryMatch[self.queryNode] # ERASE OLD NODE ASSIGNMENT
            del self.dataMatch[i]
            del self.queryMatch[self.queryNode]

        for i,e in self.iterator: # RETURN THE FIRST ACCEPTABLE ITEM
##             try: # THIS EDGE COUNT CHECK WON'T WORK IF MULTIPLE GRAPHS BEING QUERIED!!
##                 nd=len(self.dataGraph[i]) # CHECK # OF OUTGOING EDGES
##             except KeyError:
##                 nd=0
##             if nd>=self.nq and
            if (not hasattr(self,'filter') # APPLY EDGE / NODE TESTS HERE
                or self.filter(i,self.dataNode,e,self.dataMatch,
                               self.dataGraph,self)):
                if self.mustMark:
                    self.dataMatch[i]=self.queryNode  # SAVE THIS NODE ASSIGNMENT
                    self.queryMatch[self.queryNode]=i
                return i  # THIS ITEM PASSES ALL TESTS.  RETURN IT
        return None # NO MORE ITEMS FROM THE ITERATOR


class ContainerGQI(GraphQueryIterator):
    "Iterate over all nodes in self.dataGraph"
    def generate(self):
        for i in self.dataGraph:
            if i not in self.dataMatch:
                yield i,None

class AttributeGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attr of self.dataNode"
    def generate(self):
        for i,e in getattr(self.dataNode,self.attr).items():
            if i not in self.dataMatch:
                yield i,e

class AttrContainerGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attr of self.dataNode (no edge info)"
    def generate(self):
        for i in getattr(self.dataNode,self.attr):
            if i not in self.dataMatch:
                yield i,None

class CallableGQI(GraphQueryIterator):
    "Call the specified function self.f as iterator"
    def generate(self):
        for i,e in self.f(self.dataNode,self.dataGraph,self):
            if i not in self.dataMatch:
                yield i,e

class CallableContainerGQI(GraphQueryIterator):
    "Call the specified function self.f as iterator (no edge info)"
    def generate(self):
        for i in self.f(self.dataNode,self.dataGraph,self):
            if i not in self.dataMatch:
                yield i,None



def bfsEnumerate(dataGraph,queryGraph,dataMatch,queryMatch):
    'Enumerate nodes in queryGraph in BFS order, constructing iterator stack'

    # 1ST NEED TO FIND START NODES, PROCESS THEM 1ST, MARK THEM AS GENERATE ALL...
    isHead={}
    for node in queryGraph:
        if node not in isHead:
            isHead[node]=True
        for node2 in queryGraph[node]:
            isHead[node2]=False # node2 HAS INCOMING EDGE, SO NOT A START NODE!
    q=[]
    n=0
    for node in queryGraph: # PLACE START NODES AT HEAD OF QUEUE
        if isHead[node]:
            q.append(ContainerGQI(None,node,dataGraph,queryGraph,
                                  dataMatch,queryMatch))
            n += 1

    visited={}
    i=0
    while i<n: # ADD NODE TO QUEUE EVEN IF ALREADY VISITED, BUT DON'T ADD ITS NEIGHBORS
        if q[i].queryNode not in visited: # ADD NEIGHBORS TO THE QUEUE
            visited[q[i].queryNode]=None # MARK AS VISITED
            for node in queryGraph[q[i].queryNode]: # GET ALL ITS NEIGHBORS
                #print 'QUEUE:',n,node
                q.append(GraphQueryIterator(q[i].queryNode,node,dataGraph,queryGraph,
                                            dataMatch,queryMatch))
                n+=1
        i+=1
    return q

            


def graphquery(dataGraph,queryGraph):
    "generates all subgraphs of dataGraph matching queryGraph"
    dataMatch={}
    queryMatch={}
    qu=bfsEnumerate(dataGraph,queryGraph,dataMatch,queryMatch)
    i=0
    n=len(qu)
    qu[0].restart() # PRELOAD ITERATOR FOR 1ST NODE
    while i>=0:
        dataNode=qu[i].next()
        if dataNode!=None:
            #print i,qu[i].queryNode,dataNode
            if i+1<n: # MORE LEVELS TO QUERY?
                i += 1 # ADVANCE TO NEXT QUERY LEVEL
                qu[i].restart()
            else:  # GRAPH MATCH IS COMPLETE!
                yield queryMatch # RETURN COMPLETE MATCH

        else: # NO MORE ACCEPTABLE NODES AT THIS LEVEL, SO BACKTRACK
            i -= 1


def DD(**d):
    "convenience function returning a dictionary of the arguments passed to it"
    return d
