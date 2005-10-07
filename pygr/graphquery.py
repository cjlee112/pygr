

from mapping import *


class QueryMatchWrapper(dict):
    "build a queryMatch mapping on demand, since its not actually needed during query traversal"
    def __init__(self,dataMatch,compiler):
        dict.__init__(self)
        for k,v in dataMatch.items(): # INVERT THE DATA MATCH MAPPING
            self[v]=k
        for i in range(compiler.n): # ALSO SAVE MAPPINGS TO DATA EDGES
            gqi=compiler.gqi[i]
            self[gqi.fromNode,gqi.queryNode]=compiler.dataEdge[i]

class QueryMatchDescriptor(object):
    def __get__(self,obj,objtype):
        return QueryMatchWrapper(obj.dataMatch,obj)


class QueryMatcher(object):
    "map a query node or edge on demand"
    def __init__(self,compiler):
        self.compiler=compiler
    def __getitem__(self,k):
        for q,d in self.iteritems():
            if q==k:
                return d
        return KeyError
    def __iter__(self,k):
        for k,v in self.iteritems():
            yield k
    def iteritems(self):
        for dataNode,queryNode in self.compiler.dataMatch.items():
            yield queryNode,dataNode # RETURN NODE MAPPINGS
        for i in range(self.compiler.n): # ALSO SAVE MAPPINGS TO DATA EDGES
            gqi=self.compiler.gqi[i] # RETURN EDGE MAPPINGS
            yield (gqi.fromNode,gqi.queryNode),self.compiler.dataEdge[i]
    def items(self):
        return [x for x in self.iteritems()]
    def __repr__(self):
        return '{'+','.join([repr(k)+':'+repr(v) for k,v in self.iteritems()])+'}'



class GraphQueryCompiler(object):
    'compile a series of GraphQueryIterators into python code, run them'
    #queryMatch=QueryMatchDescriptor()
    def __init__(self,name='graphquery',globalDict=None):
        self.name=name
        self.code=[]
        self.unmark_code=[]
        self.indent=[]
        self.gqi=[]
        self.queryLayerGraph=dictGraph()
        self.n=0
        if globalDict is None:
            self._compiled={}
        else:
            self._compiled=globalDict
        self.queryMatch=QueryMatcher(self)
    def __getitem__(self,key):
        'return appropropriate code for accessing nodes / edges in data or query'
        if key=='dataGraph':
            queryEdge=self.gqi[self.n].queryGraph[self.gqi[self.n].fromNode][self.gqi[self.n].queryNode]
            try: # CHECK IF QUERY EDGE USES A NON-DEFAULT DATA GRAPH
                dg=queryEdge['dataGraph']
                return 'self.gqi[%d].dataGraph' % self.n
            except (TypeError,KeyError):
                return 'dataGraph'
        elif key=='filter':
            return 'self.gqi[%d].filter' % self.n
        elif key=='toQueryNode':
            return 'self.gqi[%d].queryNode' % self.n
        elif key=='fromQueryNode':
            return 'self.gqi[%d].fromNode' % self.n
        if key[:2]=='to':
            layer=self.queryLayerGraph[self.gqi[self.n].queryNode]
        elif key[:4]=='from':
            layer=self.queryLayerGraph[self.gqi[self.n].fromNode]
        if key[-8:]=='DataNode': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'dataNode%d' %layer.values()[0]
        if key[-8:]=='DataEdge': # GET LAST LAYER, WHERE THIS EDGE CREATED
            return 'dataEdge[%d]' %layer.values()[-1]
        if key=='level':
            return self.n
        try:
            return getattr(self.gqi[self.n],key)
        except AttributeError:
            raise KeyError('%s not a valid GraphQueryCompiler key' % key)        

    def indent_code(self,codestr,current_indent):
        'calculate indentation levels added by code in codestr'
        lines=codestr.split('\n')
        lastline=lines[-1]
        if lastline=='': # IGNORE TERMINAL BLANK LINE
            lastline=lines[-2]
        nindent=len(lastline.split('\t'))-1 # DETERMINE FINAL INDENTATION LEVEL
        if lastline[-1]==':':
            nindent+=1
        s='' # NOW FORMAT THE CODE WITH PROPER INDENTATION LEVEL
        for line in lines:
            s+=current_indent*'\t'+(line%self)+'\n'
        return s,current_indent+nindent
    
    def __iadd__(self,gqi):
        'add a GraphQueryIterator to be compiled into this query'
        self.gqi.append(gqi)
        if gqi.queryNode not in self.queryLayerGraph: # NOT ALREADY BOUND?
            self.queryLayerGraph+=gqi.queryNode
            codestr=gqi._generator_code
            markstr=gqi._index_code
            unmarkstr=gqi._unmark_code
        else:
            codestr=gqi._closure_code
            markstr=None
            unmarkstr=gqi._unmark_closure_code
        #BIND QUERY EDGE TO THIS LAYER
        self.queryLayerGraph[gqi.queryNode][gqi.fromNode]=self.n
        try: # GET INDENTATION LEVEL FROM PREVIOUS LAYER
            current_indent=self.indent[-1]
        except IndexError:
            current_indent=1 # TOPLEVEL: MUST INDENT INSIDE def
        s,current_indent=self.indent_code(codestr,current_indent)
        if hasattr(gqi,'filter'):
            s2,current_indent=self.indent_code(gqi._filter_code,current_indent)
            s+=s2
        if hasattr(gqi,'filtercode'):
            s2,current_indent=self.indent_code(gqi.filtercode,current_indent)
            s+=s2
        if markstr is not None:
            s2,current_indent=self.indent_code(markstr,current_indent)
            s+=s2
        if unmarkstr is not None:
            s2,tail_indent=self.indent_code(unmarkstr,current_indent)
            self.unmark_code.append(s2)
        else:
            self.unmark_code.append('')
        self.code.append(s)
        self.indent.append(current_indent)
        self.n+=1
        return self # iadd MUST RETURN self!!
    def __str__(self):
        'generate code for this query, as a string function definition'
        s='def %s(self,dataGraph,dataMatch=None,queryMatch=None):\n' \
           % self.name
        s+='\tif dataMatch is None: dataMatch={}\n'
        s+='\tself.dataMatch=dataMatch\n'
        s+='\tdataEdge=%d*[None]\n' % self.n
        s+='\tself.dataEdge=dataEdge\n'
        for layer in self.code: # GENERATE ALL THE TRAVERSAL CODE
            s+=layer
        s+=self.indent[-1]*'\t'+'yield self.queryMatch\n' # yield THE RESULT
        i=len(self.unmark_code)-1
        while i>=0: # GENERATE THE UNMARKING CODE...
            s+=self.unmark_code[i]
            i-=1
        return s
    def run(self,dataGraph,*args,**kwargs):
        'run the query, pre-compiling it if necessary'
        try: # JUST TRY RUNNING OUR FUNCTION: IT RETURNS AN ITERATOR
            return self._compiled[self.name](self,dataGraph,*args,**kwargs)
        except KeyError:
            exec str(self) in self._compiled # COMPILE OUR FUNCTION
            return self._compiled[self.name](self,dataGraph,*args,**kwargs) # RUN IT


class GraphQueryIterator(object):
    """iterator for a single node in graph query.  Subclasses provide different
       flavors of generator methods: graph w/ edges; container; attr; function etc."""
    def __init__(self,fromNode,queryNode,dataGraph,queryGraph,
                 dataMatch,queryMatch,attrDict={}):
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
            if self.fromNode is None: # NO PATH TO HERE, SO JUST ECHO SINGLETON
                self.iterator=self.echo()
            else: # CHECK FOR PATH FROM fromNode TO THIS DATA NODE
                self.iterator=self.closure()
        else:
            self.iterator=self.generate()

    def echo(self):
        "Just return what our node is ALREADY matched to"
        yield self.queryMatch[self.queryNode],None
        
    def closure(self):
        "this node is already matched.  Make sure there exists path to it (closure)"
        targetNode=self.queryMatch[self.queryNode]
        try: # GENERATE IFF container HAS EDGE TO targetNode
            container=self.dataGraph[self.dataNode]
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

    _generator_code="""
try: # GENERATOR
	it%(level)d=%(dataGraph)s[%(fromDataNode)s]
except KeyError:
	continue
for %(toDataNode)s,%(toDataEdge)s in it%(level)d.items():"""
    _index_code="""
if %(toDataNode)s in dataMatch:
	continue
else:
	dataMatch[%(toDataNode)s]=%(toQueryNode)s
        #queryMatch[%(toQueryNode)s]=%(toDataNode)s
        #queryMatch[%(fromQueryNode)s,%(toQueryNode)s]=%(toDataEdge)s
# THIS LINE PREVENTS COMPILER FROM PUSHING EXTRA INDENTATION LAYER"""
    _closure_code="""
try: # CLOSURE
	%(toDataEdge)s=%(dataGraph)s[%(fromDataNode)s][%(toDataNode)s]
except KeyError:
	pass
else:
	#queryMatch[%(fromQueryNode)s,%(toQueryNode)s]=%(toDataEdge)s"""
    _filter_code="if self.gqi[%(level)d].filter(toNode=%(toDataNode)s,fromNode=%(fromDataNode)s,edge=%(toDataEdge)s,queryMatch=self.queryMatch,gqi=self.gqi[%(level)d]):"
    _unmark_code="""
del dataMatch[%(toDataNode)s]
#del queryMatch[%(toQueryNode)s]
#del queryMatch[%(fromQueryNode)s,%(toQueryNode)s]"""
    _unmark_closure_code="#del queryMatch[%(fromQueryNode)s,%(toQueryNode)s]"

    def unmark(self):
        "erase node and edge assignment associated with the iterator"
        if self.mustMark and self.queryNode in self.queryMatch:
            i=self.queryMatch[self.queryNode] # ERASE OLD NODE ASSIGNMENT
            del self.dataMatch[i]
            del self.queryMatch[self.queryNode]
        try: del self.queryMatch[(self.fromNode,self.queryNode)] #ERASE OLD EDGE
        except KeyError: pass

            
    def next(self):
        "returns the next node from iterator that passes all tests"
        self.unmark()
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
    _generator_code="""
%(toDataEdge)s=None # CONTAINER
for %(toDataNode)s in dataGraph:"""

class AttributeGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attr of self.dataNode"
    def generate(self):
        for i,e in getattr(self.dataNode,self.attr).items():
            yield i,e
    _generator_code="for %(toDataNode)s,%(toDataEdge)s in getattr(%(fromDataNode)s,'%(attr)s').items():"

class AttrContainerGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attrN of self.dataNode (no edge info)"
    def generate(self):
        for i in getattr(self.dataNode,self.attrN):
            yield i,None
    _generator_code="""
%(toDataEdge)s=None
for %(toDataNode)s in getattr(%(fromDataNode)s,'%(attrN)s'):"""

class CallableGQI(GraphQueryIterator):
    "Call the specified function self.f as iterator"
    def generate(self):
        for i,e in self.f(self.dataNode,self.dataGraph,self):
            yield i,e
    _generator_code="for %(toDataNode)s,%(toDataEdge)s in self.gqi[%(level)d].f(%(fromDataNode)s,dataGraph,self.gqi[%(level)d]):"

class CallableContainerGQI(GraphQueryIterator):
    "Call the specified function self.fN as iterator (no edge info)"
    def generate(self):
        for i in self.fN(self.dataNode,self.dataGraph,self):
            yield i,None
    _generator_code="""
%(toDataEdge)s=None
for %(toDataNode)s in self.gqi[%(level)d].fN(%(fromDataNode)s,dataGraph,self.gqi[%(level)d]):"""
    
class SubqueryGQI(GraphQueryIterator):
    """base class for running subqueries; produces a union of all subquery solutions.
    self.subqueries must be list of graph objects, each representing a subquery"""
    def __init__(self,fromNode,queryNode,dataGraph,queryGraph,
                 dataMatch,queryMatch,attrDict={}):
        GraphQueryIterator.__init__(self,fromNode,queryNode,dataGraph,queryGraph,
                 dataMatch,queryMatch,attrDict)
        self.graphQueries=[]
        for qg in self.subqueries: # INITIALIZE OUR SUBQUERIES
            self.graphQueries.append(self.gqClass(self.dataGraph,qg,
                                                  dataMatch,queryMatch))
    def closure(self):
        "Generate union of all solutions returned by all subqueries"
        for gq in self.graphQueries:
            for d in gq: # LAUNCHES THE GRAPH QUERY, GETS ALL ITS SOLUTIONS
                yield self.queryMatch[self.queryNode],None
            gq.cleanup() # REMOVE ITS QUERY-DATA MAPPING BEFORE GOING TO NEXT SUBQUERY




def newGQI(self,oclass,fromNode,toNode,dataGraph,queryGraph,
           dataMatch,queryMatch,gqiDict):
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



class GraphQuery(object):
    "represents a single query or subquery"
    # DEFAULT MAPPING OF ATTRIBUTE NAMES TO GQI CLASSES TO USE WITH THEM
    gqiDict={'attr':AttributeGQI,
             'attrN':AttrContainerGQI,
             'f':CallableGQI,
             'fN':CallableContainerGQI,
             'subqueries':SubqueryGQI}
    newGQI=newGQI # USE THIS METHOD TO CHOOSE GQI CLASS FOR EACH ITERATOR
    def __init__(self,dataGraph,queryGraph,dataMatch=None,queryMatch=None):
        'Enumerate nodes in queryGraph in BFS order, constructing iterator stack'
        self.dataGraph=dataGraph
        self.queryGraph=queryGraph
        if dataMatch is None:
            dataMatch={}
        if queryMatch is None:
            queryMatch={}
        self.dataMatch=dataMatch
        self.queryMatch=queryMatch
        # 1ST NEED TO FIND START NODES, PROCESS THEM 1ST, MARK THEM AS GENERATE ALL...
        isFollower={}
        for node in queryGraph:
            for node2 in queryGraph[node]:
                isFollower[node2]=True # node2 HAS INCOMING EDGE, SO NOT A START NODE!
        q=[]
        self.q=q
        n=0
        for node in queryGraph: # PLACE START NODES AT HEAD OF QUEUE
            if node not in isFollower:
                q.append(self.newGQI(ContainerGQI,None,node,dataGraph,queryGraph,
                                     dataMatch,queryMatch,self.gqiDict))
                n += 1
        if n==0: # NO START NODES, SO JUST ADD THE FIRST QUERY NODE TO THE QUEUE
            for node in queryGraph:
                q.append(self.newGQI(ContainerGQI,None,node,dataGraph,queryGraph,
                                     dataMatch,queryMatch,self.gqiDict))
                n += 1
                break # JUST ADD THE FIRST NODE TO THE QUEUE
        if n==0: raise ValueError('query graph is empty!')
        visited={}
        i=0
        while i<n: # ADD NODE TO QUEUE EVEN IF ALREADY VISITED, BUT DON'T ADD ITS NEIGHBORS
            if q[i].queryNode not in visited: # ADD NEIGHBORS TO THE QUEUE
                visited[q[i].queryNode]=True # MARK AS VISITED
                for node in queryGraph[q[i].queryNode]: # GET ALL ITS NEIGHBORS
                    #print 'QUEUE:',n,node
                    q.append(self.newGQI(GraphQueryIterator,q[i].queryNode,node,
                                         dataGraph,queryGraph,
                                         dataMatch,queryMatch,self.gqiDict))
                    n+=1
            i+=1

            
    def __iter__(self):
        "generates all subgraphs of dataGraph matching queryGraph"
        i=0
        n=len(self.q)
        self.q[0].restart() # PRELOAD ITERATOR FOR 1ST NODE
        while i>=0:
            dataNode=self.q[i].next()
            if dataNode is not None:
                #print i,qu[i].queryNode,dataNode
                if i+1<n: # MORE LEVELS TO QUERY?
                    i += 1 # ADVANCE TO NEXT QUERY LEVEL
                    self.q[i].restart()
                else:  # GRAPH MATCH IS COMPLETE!
                    yield self.queryMatch # RETURN COMPLETE MATCH

            else: # NO MORE ACCEPTABLE NODES AT THIS LEVEL, SO BACKTRACK
                i -= 1

    def cleanup(self):
        "erase any query:data node matching associated with this subquery"
        for q in self.q:
            q.unmark()

    def compile(self,globals=None):
        'return a compiled version of this query, using globals namespace if specified'
        compiler=GraphQueryCompiler(globalDict=globals)
        for gqi in self.q:
            compiler+=gqi
        return compiler
        

SubqueryGQI.gqClass=GraphQuery # CLASS FOR CONSTRUCTING SUBQUERIES


