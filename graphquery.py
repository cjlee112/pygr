

class GraphQueryIterator(object):
    """iterator for a single node in graph query.  Subclasses provide different
       flavors of generator methods: graph w/ edges; container; attr; function etc."""
    def __init__(self,fromNode,queryNode,dataGraph,queryGraph,dataMatch,queryMatch,attrDict={}):
        self.fromNode=fromNode
        self.queryNode=queryNode
        self.dataGraph=dataGraph
        self.queryGraph=queryGraph
        self.dataMatch=dataMatch
        self.queryMatch=queryMatch
        self.dataNode=None
        for attr,val in attrDict.items(): # SAVE OUR EDGE INFO
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
                yield i,e

    def next(self):
        "returns the next node from iterator that passes all tests"
        if self.mustMark and self.queryNode in self.queryMatch:
            i=self.queryMatch[self.queryNode] # ERASE OLD NODE ASSIGNMENT
            del self.dataMatch[i]
            del self.queryMatch[self.queryNode]
        try: del self.queryMatch[(self.fromNode,self.queryNode)] #ERASE OLD EDGE
        except KeyError: pass

        for i,e in self.iterator: # RETURN THE FIRST ACCEPTABLE ITEM
##             try: # THIS EDGE COUNT CHECK WON'T WORK IF MULTIPLE GRAPHS BEING QUERIED!!
##                 nd=len(self.dataGraph[i]) # CHECK # OF OUTGOING EDGES
##             except KeyError:
##                 nd=0
##             if nd>=self.nq and
            if self.mustMark and i in self.dataMatch:
                continue # THIS NODE ALREADY ASSIGNED. CAN'T REUSE IT!
            if (not hasattr(self,'filter') # APPLY EDGE / NODE TESTS HERE
                or self.filter(toNode=i,fromNode=self.dataNode,edge=e,
                               queryMatch=self.queryMatch,gqi=self)):
                if self.mustMark:
                    self.dataMatch[i]=self.queryNode  # SAVE THIS NODE ASSIGNMENT
                    self.queryMatch[self.queryNode]=i
                if e is not None: # SAVE EDGE INFO, IF ANY
                    self.queryMatch[(self.fromNode,self.queryNode)]=e
                return i  # THIS ITEM PASSES ALL TESTS.  RETURN IT
        return None # NO MORE ITEMS FROM THE ITERATOR


class ContainerGQI(GraphQueryIterator):
    "Iterate over all nodes in self.dataGraph"
    def generate(self):
        for i in self.dataGraph:
            yield i,None

class AttributeGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attr of self.dataNode"
    def generate(self):
        for i,e in getattr(self.dataNode,self.attr).items():
            yield i,e

class AttrContainerGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attrN of self.dataNode (no edge info)"
    def generate(self):
        for i in getattr(self.dataNode,self.attrN):
            yield i,None

class CallableGQI(GraphQueryIterator):
    "Call the specified function self.f as iterator"
    def generate(self):
        for i,e in self.f(self.dataNode,self.dataGraph,self):
            yield i,e

class CallableContainerGQI(GraphQueryIterator):
    "Call the specified function self.fN as iterator (no edge info)"
    def generate(self):
        for i in self.fN(self.dataNode,self.dataGraph,self):
            yield i,None

# DEFAULT MAPPING OF ATTRIBUTE NAMES TO GQI CLASSES TO USE WITH THEM
defaultGQIDict={'attr':AttributeGQI,
                'attrN':AttrContainerGQI,
                'f':CallableGQI,
                'fN':CallableContainerGQI}



def newGQI(oclass,fromNode,toNode,dataGraph,queryGraph,dataMatch,queryMatch,
           gqiDict=defaultGQIDict):
    """figure out a default GQI class to use, based on an attribute dictionary,
       then return a new object of that class initialized with the input data."""
    if fromNode is not None and toNode is not None and \
           queryGraph[fromNode][toNode] is not None:
        kwargs=queryGraph[fromNode][toNode]
        for attr in kwargs:
            try: oclass=gqiDict[attr] # USE ATTRIBUTE NAME TO DETERMINE DEFAULT CLASS
            except KeyError: pass
    else:
        kwargs={}
    try: oclass=kwargs['__class__'] # LET USER SET CLASS TO USE
    except KeyError: pass
    return oclass(fromNode,toNode,dataGraph,queryGraph,dataMatch,queryMatch,kwargs)



def bfsEnumerate(dataGraph,queryGraph,dataMatch,queryMatch):
    'Enumerate nodes in queryGraph in BFS order, constructing iterator stack'
    # 1ST NEED TO FIND START NODES, PROCESS THEM 1ST, MARK THEM AS GENERATE ALL...
    isFollower={}
    for node in queryGraph:
        for node2 in queryGraph[node]:
            isFollower[node2]=True # node2 HAS INCOMING EDGE, SO NOT A START NODE!
    q=[]
    n=0
    for node in queryGraph: # PLACE START NODES AT HEAD OF QUEUE
        if node not in isFollower:
            q.append(newGQI(ContainerGQI,None,node,dataGraph,queryGraph,
                            dataMatch,queryMatch))
            n += 1

    visited={}
    i=0
    while i<n: # ADD NODE TO QUEUE EVEN IF ALREADY VISITED, BUT DON'T ADD ITS NEIGHBORS
        if q[i].queryNode not in visited: # ADD NEIGHBORS TO THE QUEUE
            visited[q[i].queryNode]=None # MARK AS VISITED
            for node in queryGraph[q[i].queryNode]: # GET ALL ITS NEIGHBORS
                #print 'QUEUE:',n,node
                q.append(newGQI(GraphQueryIterator,q[i].queryNode,node,dataGraph,queryGraph,
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
