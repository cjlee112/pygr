

class GraphQueryIterator(object):
    def __init__(self,fromNode,queryNode,dataGraph,queryGraph,dataMatch,queryMatch):
        self.fromNode=fromNode
        self.queryNode=queryNode
        self.dataGraph=dataGraph
        self.queryGraph=queryGraph
        self.dataMatch=dataMatch
        self.queryMatch=queryMatch

    def restart(self,generateAll=False):
        self.mustMark=True
        if self.fromNode != None:
            self.dataNode=self.queryMatch[self.fromNode]
        if generateAll: # SEARCH AGAINST ALL NODES IN DATA GRAPH
            self.iterator=self.allNodes()
        elif self.queryNode in self.queryMatch: # ALREADY ASSIGNED TO A DATA NODE
            self.mustMark=False
            self.iterator=self.singleton()
        else: # SEARCH AGAINST ALL NEIGHBORS OF DATA NODE MAPPED TO fromNode
            self.iterator=self.neighbors()

    def singleton(self):
        #print '\t\tEntering singleton'
        # CHECK FOR EDGE IN DATA GRAPH TO OUR TARGET NODE
        if self.queryMatch[self.queryNode] in self.dataGraph[self.dataNode]:
            yield self.queryMatch[self.queryNode]

    def neighbors(self):
        #print '\t\tEntering gqi.iter()',self.dataNode
        for i in self.dataGraph[self.dataNode]:
            #print '\t\tTrying:',i
            if i not in self.dataMatch:
                yield i

    def allNodes(self):
        for i in self.dataGraph:
            yield i

    def next(self):
        if self.mustMark and self.queryNode in self.queryMatch:
            i=self.queryMatch[self.queryNode] # ERASE OLD NODE ASSIGNMENT
            del self.dataMatch[i]
            del self.queryMatch[self.queryNode]

        for i in self.iterator: # RETURN THE FIRST ACCEPTABLE ITEM
            try:
                nq=len(self.queryGraph[self.queryNode])
            except KeyError:
                nq=0
            try:
                nd=len(self.dataGraph[i])
            except KeyError:
                nd=0
            if nd>=nq:# APPLY EDGE TESTS AND NODE TESTS HERE
                if self.mustMark:
                    self.dataMatch[i]=self.queryNode  # SAVE THIS NODE ASSIGNMENT
                    self.queryMatch[self.queryNode]=i
                return i  # THIS ITEM PASSES ALL TESTS.  RETURN IT
        return None # NO MORE ITEMS FROM THE ITERATOR




def bfsEnumerate(dataGraph,queryGraph,dataMatch,queryMatch):
    'Enumerate nodes in queryGraph in BFS order, return as a list'

    # 1ST NEED TO FIND START NODES, PROCESS THEM 1ST, MARK THEM AS GENERATE ALL...
    q=[]
    n=0
    for node in queryGraph:
        #print 'QUEUE:',n,node
        q.append(GraphQueryIterator(None,node,dataGraph,queryGraph,
                                    dataMatch,queryMatch))
        n=1
        break
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
    dataMatch={}
    queryMatch={}
    qu=bfsEnumerate(dataGraph,queryGraph,dataMatch,queryMatch)
    i=0
    n=len(qu)
    qu[0].restart(True) # FORCE 1ST NODE TO TRY MATCHING ALL POSSIBLE NODES IN dataGraph
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






    
