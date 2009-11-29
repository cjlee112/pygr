

from __future__ import generators
from mapping import *


class QueryMatchWrapper(dict):
    """build a queryMatch mapping on demand, since its not actually needed
    during query traversal"""

    def __init__(self, dataMatch, compiler):
        dict.__init__(self)
        for k, v in dataMatch.items(): # INVERT THE DATA MATCH MAPPING
            self[v] = k
        for i in range(compiler.n): # ALSO SAVE MAPPINGS TO DATA EDGES
            gqi = compiler.gqi[i]
            self[gqi.fromNode, gqi.queryNode] = compiler.dataEdge[i]


class QueryMatchDescriptor(object):

    def __get__(self, obj, objtype):
        return QueryMatchWrapper(obj.dataMatch, obj)


class QueryMatcher(object):
    "map a query node or edge on demand"

    def __init__(self, compiler):
        self.compiler = compiler

    def __getitem__(self, k):
        for q, d in self.iteritems():
            if q == k:
                return d
        return KeyError

    def __iter__(self, k):
        for k, v in self.iteritems():
            yield k

    def iteritems(self):
        for dataNode, queryNode in self.compiler.dataMatch.items():
            yield queryNode, dataNode # RETURN NODE MAPPINGS
        for i in range(self.compiler.n): # ALSO SAVE MAPPINGS TO DATA EDGES
            gqi = self.compiler.gqi[i] # RETURN EDGE MAPPINGS
            yield (gqi.fromNode, gqi.queryNode), self.compiler.dataEdge[i]

    def items(self):
        return [x for x in self.iteritems()]

    def __repr__(self):
        return '{' + ','.join([repr(k) + ':' + repr(v)
                               for k, v in self.iteritems()]) + '}'


class GraphQueryCompiler(object):
    'compile a series of GraphQueryIterators into python code, run them'
    #queryMatch = QueryMatchDescriptor()
    _lang = "" # NO LANGUAGE STEM

    def __init__(self, name='graphquery', globalDict=None):
        self.name = name
        self.code = []
        self.unmark_code = []
        self.next_code = []
        self.end_code = []
        self.indent = []
        self.gqi = []
        self.queryLayerGraph = dictGraph()
        self.n = 0
        if globalDict is None:
            self._compiled = {}
        else:
            self._compiled = globalDict
        self.queryMatch = QueryMatcher(self)

    def __getitem__(self, key):
        'return appropropriate code for accessing nodes/edges in data or query'
        if key == 'n':
            return self.n
        elif key == 'name':
            return self.name
        elif key == 'dataGraph':
            queryEdge = self.gqi[self.n].queryGraph[self.gqi[self.n].fromNode]\
                    [self.gqi[self.n].queryNode]
            try: # CHECK IF QUERY EDGE USES A NON-DEFAULT DATA GRAPH
                dg = queryEdge['dataGraph']
                return 'self.gqi[%d].dataGraph' % self.n
            except (TypeError, KeyError):
                return 'dataGraph'
        elif key == 'filter':
            return 'self.gqi[%d].filter' % self.n
        elif key == 'toQueryNode':
            return 'self.gqi[%d].queryNode' % self.n
        elif key == 'fromQueryNode':
            return 'self.gqi[%d].fromNode' % self.n
        if key[:2] == 'to':
            layer = self.queryLayerGraph[self.gqi[self.n].queryNode]
        elif key[:4] == 'from':
            layer = self.queryLayerGraph[self.gqi[self.n].fromNode]
        if key[-8:] == 'DataNode': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'dataNode%d' % layer.values()[0]
        if key[-8:] == 'DataEdge': # GET LAST LAYER, WHERE THIS EDGE CREATED
            return 'dataEdge[%d]' % layer.values()[-1]
        if key == 'level':
            return self.n
        try:
            return getattr(self.gqi[self.n], key)
        except AttributeError:
            raise KeyError('%s not a valid GraphQueryCompiler key' % key)

    def indent_code(self, codestr, current_indent):
        'calculate indentation levels added by code in codestr'
        codestr = codestr % self # PERFORM MACRO SUBSTITUTIONS
        lines = codestr.split('\n')
        lastline = lines[-1]
        if lastline == '' and len(lines) > 1: # IGNORE TERMINAL BLANK LINE
            lastline = lines[-2]
        # Determine final indentation level.
        nindent = len(lastline.split('\t')) - 1
        if len(lastline) > 0 and lastline[-1] == ':':
            nindent += 1
        s = '' # NOW FORMAT THE CODE WITH PROPER INDENTATION LEVEL
        for line in lines:
            s += current_indent * '\t' + line + '\n'
        return s, current_indent + nindent

    def __iadd__(self, gqi):
        'add a GraphQueryIterator to be compiled into this query'
        self.gqi.append(gqi)
        if gqi.queryNode not in self.queryLayerGraph: # NOT ALREADY BOUND?
            self.queryLayerGraph += gqi.queryNode
            codestr = getattr(gqi, self._lang + '_generator_code')
            markstr = getattr(gqi, self._lang + '_index_code')
            unmarkstr = getattr(gqi, self._lang + '_unmark_code')
            try:
                endcode = getattr(gqi, self._lang + '_end_code')
            except AttributeError:
                endcode = ''
            try:
                nextcode = getattr(gqi, self._lang + '_next_code')
            except AttributeError:
                nextcode = ''
            self.lastGenerator = self.n
        else:
            codestr = getattr(gqi, self._lang + '_closure_code')
            markstr = None
            unmarkstr = getattr(gqi, self._lang + '_unmark_closure_code')
            try:
                endcode = getattr(gqi, self._lang + '_end_closure_code')
            except AttributeError:
                endcode = ''
            try:
                nextcode = getattr(gqi, self._lang + '_next_closure_code')
            except AttributeError:
                nextcode = ''
        #BIND QUERY EDGE TO THIS LAYER
        self.queryLayerGraph[gqi.queryNode][gqi.fromNode] = self.n
        try: # GET INDENTATION LEVEL FROM PREVIOUS LAYER
            current_indent = self.indent[-1]
        except IndexError:
            current_indent = 1 # TOPLEVEL: MUST INDENT INSIDE def
        self.end_code.append(self.indent_code(endcode, current_indent)[0])
        s, current_indent = self.indent_code(codestr, current_indent)
        self.next_code.append(self.indent_code(nextcode, current_indent)[0])
        if hasattr(gqi, 'filter'):
            s2, current_indent = self.indent_code(getattr(gqi, self._lang + \
                                                          '_filter_code'),
                                                  current_indent)
            s += s2
        if hasattr(gqi, 'filtercode'):
            s2, current_indent = self.indent_code(gqi.filtercode,
                                                  current_indent)
            s += s2
        if markstr is not None:
            s2, current_indent = self.indent_code(markstr, current_indent)
            s += s2
        if unmarkstr is not None:
            s2, tail_indent = self.indent_code(unmarkstr, current_indent)
            self.unmark_code.append(s2)
        else:
            self.unmark_code.append('') # NO UNMARK CODE, SO JUST APPEND BLANK
        self.code.append(s)
        self.indent.append(current_indent)
        self.n += 1
        return self # iadd MUST RETURN self!!
    _def_code = """
def %(name)s(self, dataGraph, dataMatch=None, queryMatch=None):
\tif dataMatch is None: dataMatch={}
\tself.dataMatch = dataMatch
\tdataEdge = %(n)d * [None]
\tself.dataEdge = dataEdge
"""
    _yield_code = 'yield self.queryMatch\n'
    _end_code = ''

    def __str__(self):
        'generate code for this query, as a string function definition'
        s = self._def_code % self
        for layer in self.code: # GENERATE ALL THE TRAVERSAL CODE
            s += layer
        # yield the result
        s2 = self.indent_code(self._yield_code, self.indent[-1])[0]
        s += s2
        i = len(self.unmark_code) - 1
        while i >= 0: # GENERATE THE UNMARKING CODE...
            s += self.unmark_code[i]
            s += self.next_code[i]
            s += self.end_code[i]
            i -= 1
        s += self._end_code % self
        return s

    def run(self, dataGraph, *args, **kwargs):
        'run the query, pre-compiling it if necessary'
        try: # JUST TRY RUNNING OUR FUNCTION: IT RETURNS AN ITERATOR
            return self._compiled[self.name](self, dataGraph, *args, **kwargs)
        except KeyError:
            self.compile()
            # Run it.
            return self._compiled[self.name](self, dataGraph, *args, **kwargs)

    def compile(self):
        'compile using Python exec statement'
        exec str(self) in self._compiled # COMPILE OUR FUNCTION


def find_distutils_lib(path='build'):
    'locate the build/lib path where distutils builds modules'
    import os
    dirs = os.listdir('build')
    for d in dirs:
        if d[:4] == 'lib.':
            return path + '/' + d
    raise OSError((1, 'Unable to locate where distutils built your module!'))


class GraphQueryPyrex(GraphQueryCompiler):
    'compile a series of GraphQueryIterators into pyrex code, run them'
    #queryMatch = QueryMatchDescriptor()
    _lang = "_pyrex" # NO LANGUAGE STEM

    def __getitem__(self, key):
        'return appropropriate code for accessing nodes/edges in data or query'
        if key == 'n':
            return self.n
        elif key == 'name':
            return self.name
        elif key == 'dataGraph':
            try: # CHECK IF QUERY EDGE USES A NON-DEFAULT DATA GRAPH
                queryEdge = self.gqi[self.n].queryGraph[self.gqi[self.n].\
                                          fromNode][self.gqi[self.n].queryNode]
                dg = queryEdge['dataGraph']
                return 'self.gqi[%d].dataGraph' % self.n
            except (TypeError, KeyError):
                return 'dataGraph'
        elif key == 'filter':
            return 'self.gqi[%d].filter' % self.n
        elif key == 'toQueryNode':
            return 'self.gqi[%d].queryNode' % self.n
        elif key == 'fromQueryNode':
            return 'self.gqi[%d].fromNode' % self.n
        if key[:2] == 'to':
            layer = self.queryLayerGraph[self.gqi[self.n].queryNode]
        elif key[:4] == 'from':
            layer = self.queryLayerGraph[self.gqi[self.n].fromNode]
        if key[-8:] == 'DataNode': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'dataNode%d' % layer.values()[0]
        if key[-8:] == 'DataEdge': # GET LAST LAYER, WHERE THIS EDGE CREATED
            return 'dataEdge%d' % layer.values()[-1]
        if key[-8:] == 'DataDict': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'cDict%d' % layer.values()[0]
        if key[-7:] == 'DataPtr': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'pDictEntry%d' % layer.values()[0]
        if key[-11:] == 'DataPtrCont': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'pGraphEntry%d' % layer.values()[0]
        if key[-11:] == 'DataCounter': # GET 1ST LAYER WHERE THIS NODE ASSIGNED
            return 'i%d' % layer.values()[0]
        if key == 'toDataNodeUnmatched':
            l = ['dataNode%d!=dataNode%d'
                 % (self.queryLayerGraph[self.gqi[i].queryNode].values()[0],
                  self.queryLayerGraph[self.gqi[self.n].queryNode].values()[0])
               for i in range(self.n)]
            if len(l) > 0:
                return ' and '.join(l)
            else:
                return 'True'
        if key == 'dataNodeDefs':
            return ','.join(['dataNode%d' % i for i in range(self.n)])
        if key == 'dataEdgeDefs':
            return ','.join(['dataEdge%d' % i for i in range(self.n)])
        if key == 'dataDictDefs':
            return ','.join(['*cDict%d' % i for i in range(self.n)])
        if key == 'dataPtrDefs':
            return ','.join(['*pDictEntry%d' % i for i in range(self.n)])
        if key == 'dataPtrContDefs':
            return ','.join(['*pGraphEntry%d' % i for i in range(self.n)])
        if key == 'dataCounterDefs':
            return ','.join(['i%d' % i for i in range(self.n)])
        if key == 'dataCounterArgs':
            return ','.join(['int i%d' % i for i in range(self.n)])
        if key == 'itaVector':
            return ','.join(['ita.vector[%d]' % i for i in range(self.n)])
        if key == 'itaTuple':
            return ',\\\n'.join(['p_ita[%d]' % i for i in range(2 * self.n)])
        if key == 'resultTuple':
            return ',\\\n'.join(['dataNode%d,dataEdge%d'
                 % (self.queryLayerGraph[self.gqi[i].queryNode].values()[0], i)
                                 for i in range(self.n)])
        if key == 'resultTuples':
            return ','.join(['(dataNode%d,dataEdge%d)'
                 % (self.queryLayerGraph[self.gqi[i].queryNode].values()[0], i)
                             for i in range(self.n)])
        if key == 'level' or key == 'nEdges':
            return self.n
        if key == 'lastGenerator':
            return self.lastGenerator
        try:
            return getattr(self.gqi[self.n], key)
        except AttributeError:
            raise KeyError('%s not a valid GraphQueryPyrex key' % key)

    _def_code = """
cimport cdict
cdef c_%(name)s(cdict.CGraphDict cgd, cdict.IntTupleArray ita,
                    %(dataCounterArgs)s):
\tcdef cdict.CGraph *dataGraph
\tcdef cdict.CDict %(dataDictDefs)s
\tcdef cdict.CDictEntry %(dataPtrDefs)s
\tcdef cdict.CDictEntry *pd_temp
\tcdef cdict.CGraphEntry %(dataPtrContDefs)s
\tcdef cdict.CGraphEntry *p_temp
\t#cdef int %(dataCounterDefs)s
\tcdef int %(dataNodeDefs)s
\tcdef int %(dataEdgeDefs)s
\tcdef int *p_ita
\tdataGraph = cgd.d
\tp_ita = ita.data
"""
    _yield_code = """
%(itaTuple)s = %(resultTuple)s
p_ita = p_ita + 2 * %(nEdges)d
ita.n = ita.n + 1
if ita.n >= ita.n_alloc:
\tita.set_vector((%(dataCounterDefs)s), 1)
\treturn
"""
    #results.append((%(resultTuples)s))\n
    _end_code = """
\tita.isDone = 1 # COMPLETED THIS QUERY

from pygr import cdict
def %(name)s(self, g, int maxhit=1000, cdict.IntTupleArray ita=None, qml=None):
\tif not isinstance(g, cdict.CGraphDict):
\t\tg = cdict.CGraphDict(g, cdict.KeyIndex())
\tif ita is None:
\t\tita = cdict.IntTupleArray(maxhit, %(nEdges)d, 2, %(lastGenerator)d)
\tita.n = 0
\tc_%(name)s(g, ita, %(itaVector)s) # RUN THE QUERY
\tif qml is not None:
\t\tqml.matches = ita
\t\treturn qml
\telse:
\t\treturn cdict.QueryMatchList(self, ita, g, %(name)s)
"""

    def compile(self):
        'compile using Pyrex, Distutils, and finally import!'
        import os
        try:
            # We need access to Pygr source code to access cgraph functions
            # in this module.
            pygrpath = os.environ['PYGRPATH']
        except KeyError:
            raise OSError((1,
                           """pyrex compilation requires access to pygr source.
                           Please set the environment variable PYGRPATH to \
                           the top of the pygr source package."""))
        if not os.access(pygrpath + '/pygr/cgraph.c', os.R_OK):
            raise OSError((1, """Unable to access %s/pygr/cgraph.c.
            Is PYGRPATH set to the top of the pygr source package?"""
                           % pygrpath))
        exit_status = os.system('cp %s/pygr/cgraph.c %s/pygr/cgraph.h \
                                %s/pygr/cdict.pxd .'
                                % (pygrpath, pygrpath, pygrpath))
        if exit_status != 0:  # RUN THE PYREX COMPILER TO PRODUCE C
            raise OSError((exit_status,
                           'unable to copy source code to this directory.'))
        # Construct a unique name for the module.
        modulename = self.name + str(id(self))
        myfile = file(modulename + '.pyx', 'w') # GENERATE PYREX CODE
        myfile.write(str(self)) # WRITE CODE
        myfile.close()
        exit_status = os.system('pyrexc %s.pyx' % (modulename))
        if exit_status != 0:  # RUN THE PYREX COMPILER TO PRODUCE C
            raise OSError((exit_status, 'pyrex compilation failed. Is \
pyrexc missing or not in your PATH?'))
        # Build the module using distutils.
        from distutils.core import setup, Extension
        module1 = Extension(modulename, sources=['cgraph.c',
                                                 modulename + '.c'])
        setup(name=modulename,
              description='autogenerated by pygr.graphquery',
              ext_modules=[module1], script_args=['build'])
        # Find out where distutils put our built module.
        modulepath = find_distutils_lib()
        # Work around a nasty problem with Pyrex cimport - there is no way to
        # tell it the module is in a subdirectory! Here, 'from pygr cimport
        # cdict' or 'cimport pygr.cdict' fail; one MUST say 'cimport cdict'.
        import sys
        import os.path
        from pygr import cdict
        # Add the module's location to our path.
        sys.path += [os.path.dirname(cdict.__file__)]
        import imp  # FINALLY, TRY TO IMPORT THE NEW MODULE
        modulefile, path, desc = imp.find_module(modulename, [modulepath])
        # Load and bind the module.
        self._module = imp.load_module(modulename, modulefile, path, desc)
        # Bind our query function.
        self._compiled[self.name] = getattr(self._module, self.name)
        modulefile.close()


class GraphQueryIterator(object):
    """iterator for a single node in graph query.  Subclasses provide different
       flavors of generator methods: graph w/ edges; container; attr;
       function etc."""

    def __init__(self, fromNode, queryNode, dataGraph, queryGraph,
                 dataMatch, queryMatch, attrDict={}):
        self.fromNode = fromNode
        self.queryNode = queryNode
        self.dataGraph = dataGraph
        self.queryGraph = queryGraph
        self.dataMatch = dataMatch
        self.queryMatch = queryMatch
        self.dataNode = None
        for attr, val in attrDict.items():
            # Save our edge information as attributes of this object.
            setattr(self, attr, val)
##         try:
##             self.nq = len(self.queryGraph[self.queryNode])
##         except KeyError:
##             self.nq = 0

    def restart(self):
        "reset the iterator to its beginning"
        self.mustMark = True
        if self.fromNode != None:
            self.dataNode = self.queryMatch[self.fromNode]
        if self.queryNode in self.queryMatch: # ALREADY ASSIGNED TO A DATA NODE
            self.mustMark = False
            if self.fromNode is None: # NO PATH TO HERE, SO JUST ECHO SINGLETON
                self.iterator = self.echo()
            else: # CHECK FOR PATH FROM fromNode TO THIS DATA NODE
                self.iterator = self.closure()
        else:
            self.iterator = self.generate()

    def echo(self):
        "Just return what our node is ALREADY matched to"
        yield self.queryMatch[self.queryNode], None

    def closure(self):
        "This node is already matched. Make sure a path to it (closure) exists"
        targetNode = self.queryMatch[self.queryNode]
        try: # GENERATE IF container HAS EDGE TO targetNode
            container = self.dataGraph[self.dataNode]
            yield targetNode, container[targetNode]
        except KeyError:
            pass

    def generate(self):
        "generate all neighbors of data node matched to fromNode"
        try:
            it = self.dataGraph[self.dataNode]
        except KeyError:
            pass
        else:
            for i, e in it.items():
                yield i, e

    _generator_code = """
try: # GENERATOR
\tit%(level)d = %(dataGraph)s[%(fromDataNode)s]
except KeyError:
\tcontinue
for %(toDataNode)s, %(toDataEdge)s in it%(level)d.items():"""

    _index_code = """
if %(toDataNode)s in dataMatch:
\tcontinue
else:
\tdataMatch[%(toDataNode)s] = %(toQueryNode)s
\t#queryMatch[%(toQueryNode)s] = %(toDataNode)s
\t#queryMatch[%(fromQueryNode)s, %(toQueryNode)s] = %(toDataEdge)s
# THIS LINE PREVENTS COMPILER FROM PUSHING EXTRA INDENTATION LAYER"""

    _filter_code = """
if self.gqi[%(level)d].filter(toNode=%(toDataNode)s, fromNode=%(fromDataNode)s, \
                              edge=%(toDataEdge)s, queryMatch=self.queryMatch, \
                              gqi=self.gqi[%(level)d]):"""

    _unmark_code = """
del dataMatch[%(toDataNode)s]
#del queryMatch[%(toQueryNode)s]
#del queryMatch[%(fromQueryNode)s, %(toQueryNode)s]"""

    _closure_code = """
try: # CLOSURE
\t%(toDataEdge)s = %(dataGraph)s[%(fromDataNode)s][%(toDataNode)s]
except KeyError:
\tpass
else:
\t#queryMatch[%(fromQueryNode)s, %(toQueryNode)s] = %(toDataEdge)s"""

    _unmark_closure_code = """
#del queryMatch[%(fromQueryNode)s, %(toQueryNode)s]"""

    # PYREX CODE
    _pyrex_generator_code = """
p_temp = cdict.cgraph_getitem(%(dataGraph)s, %(fromDataNode)s)
if p_temp != NULL:
\t%(fromDataDict)s = p_temp[0].v
\t%(toDataPtr)s = %(fromDataDict)s[0].dict
\twhile %(toDataCounter)s < %(fromDataDict)s[0].n:
\t\t%(toDataNode)s = %(toDataPtr)s[%(toDataCounter)s].k
\t\t%(toDataEdge)s = %(toDataPtr)s[%(toDataCounter)s].v
"""
    #for %(toDataCounter)s from 0 <= %(toDataCounter)s < %(fromDataDict)s[0].n:

    _pyrex_index_code = 'if %(toDataNodeUnmatched)s:'

    _pyrex_unmark_code = '# COMPILER NEEDS AT LEAST ONE LINE, \
                          EVEN THOUGH NOTHING TO DO HERE'

    _pyrex_next_code = '%(toDataCounter)s = %(toDataCounter)s + 1'

    _pyrex_end_code = '%(toDataCounter)s = 0'

    _pyrex_closure_code = """
p_temp = cdict.cgraph_getitem(%(dataGraph)s, %(fromDataNode)s)
if p_temp != NULL:
\t%(fromDataDict)s = p_temp[0].v
\tpd_temp = cdict.cdict_getitem(%(fromDataDict)s, %(toDataNode)s)
\tif pd_temp != NULL:
\t\t%(toDataEdge)s = pd_temp[0].v
"""

    _pyrex_unmark_closure_code = '# COMPILER NEEDS AT LEAST ONE LINE, \
                                  EVEN THOUGH NOTHING TO DO HERE'

    def unmark(self):
        "erase node and edge assignment associated with the iterator"
        if self.mustMark and self.queryNode in self.queryMatch:
            i = self.queryMatch[self.queryNode] # ERASE OLD NODE ASSIGNMENT
            del self.dataMatch[i]
            del self.queryMatch[self.queryNode]
        try:
            # Erase old edge.
            del self.queryMatch[(self.fromNode, self.queryNode)]
        except KeyError:
            pass

    def next(self):
        "returns the next node from iterator that passes all tests"
        self.unmark()
        for i, e in self.iterator: # RETURN THE FIRST ACCEPTABLE ITEM
##             try:
##                 # Check the number of outgoing edges. NOTE: This check
##                 # will NOT work if multiple graphs are queried!
##                 nd = len(self.dataGraph[i])
##             except KeyError:
##                 nd = 0
##             if nd >= self.nq and
            if self.mustMark and i in self.dataMatch:
                continue # THIS NODE ALREADY ASSIGNED. CAN'T REUSE IT!
            if (not hasattr(self, 'filter') # APPLY EDGE / NODE TESTS HERE
               or self.filter(toNode=i, fromNode=self.dataNode, edge=e,
                               queryMatch=self.queryMatch, gqi=self)):
                if self.mustMark:
                    # Save this node assignment.
                    self.dataMatch[i] = self.queryNode
                    self.queryMatch[self.queryNode] = i
                if e is not None: # SAVE EDGE INFO, IF ANY
                    self.queryMatch[(self.fromNode, self.queryNode)] = e
                return i  # THIS ITEM PASSES ALL TESTS.  RETURN IT
        return None # NO MORE ITEMS FROM THE ITERATOR


class ContainerGQI(GraphQueryIterator):
    "Iterate over all nodes in self.dataGraph"

    def generate(self):
        for i in self.dataGraph:
            yield i, None

    _generator_code = """
%(toDataEdge)s = None # CONTAINER
for %(toDataNode)s in dataGraph:"""

    _pyrex_generator_code="""
%(toDataPtrCont)s = %(dataGraph)s[0].dict
for %(toDataCounter)s from 0 <= %(toDataCounter)s < %(dataGraph)s[0].n:
\t%(toDataNode)s = %(toDataPtrCont)s[%(toDataCounter)s].k
\t%(toDataEdge)s = -1 # NO EDGE INFO
"""


class AttributeGQI(GraphQueryIterator):
    "Iterate over all nodes in attribute called self.attr of self.dataNode"

    def generate(self):
        for i, e in getattr(self.dataNode, self.attr).items():
            yield i, e

    _generator_code = """
for %(toDataNode)s, %(toDataEdge)s in getattr(%(fromDataNode)s, \
                                              '%(attr)s').items():"""


class AttrContainerGQI(GraphQueryIterator):
    """Iterate over all nodes in attribute called self.attrN of self.dataNode
    (no edge info)"""

    def generate(self):
        for i in getattr(self.dataNode, self.attrN):
            yield i, None

    _generator_code = """
%(toDataEdge)s = None
for %(toDataNode)s in getattr(%(fromDataNode)s, '%(attrN)s'):"""


class CallableGQI(GraphQueryIterator):
    "Call the specified function self.f as iterator"

    def generate(self):
        for i, e in self.f(self.dataNode, self.dataGraph, self):
            yield i, e

    _generator_code = """
for %(toDataNode)s, %(toDataEdge)s in self.gqi[%(level)d].f(%(fromDataNode)s, \
                                            dataGraph, self.gqi[%(level)d]):"""


class CallableContainerGQI(GraphQueryIterator):
    "Call the specified function self.fN as iterator (no edge info)"

    def generate(self):
        for i in self.fN(self.dataNode, self.dataGraph, self):
            yield i, None

    _generator_code = """
%(toDataEdge)s = None
for %(toDataNode)s in self.gqi[%(level)d].fN(%(fromDataNode)s, dataGraph, \
                                             self.gqi[%(level)d]):"""


class SubqueryGQI(GraphQueryIterator):
    """base class for running subqueries; produces a union of all subquery
    solutions. self.subqueries must be list of graph objects, each
    representing a subquery"""

    def __init__(self, fromNode, queryNode, dataGraph, queryGraph,
                 dataMatch, queryMatch, attrDict={}):
        GraphQueryIterator.__init__(self, fromNode, queryNode, dataGraph,
                                    queryGraph, dataMatch, queryMatch,
                                    attrDict)
        self.graphQueries = []
        for qg in self.subqueries: # INITIALIZE OUR SUBQUERIES
            self.graphQueries.append(self.gqClass(self.dataGraph, qg,
                                                  dataMatch, queryMatch))

    def closure(self):
        "Generate union of all solutions returned by all subqueries"
        for gq in self.graphQueries:
            for d in gq: # LAUNCHES THE GRAPH QUERY, GETS ALL ITS SOLUTIONS
                yield self.queryMatch[self.queryNode], None
            # Remove its query-data mapping before going to the next subquery.
            gq.cleanup()


def newGQI(self, oclass, fromNode, toNode, dataGraph, queryGraph,
           dataMatch, queryMatch, gqiDict):
    """figure out a default GQI class to use, based on an attribute dictionary,
       then return a new object of that class initialized with the input data
       """
    if fromNode is not None and toNode is not None and \
           queryGraph[fromNode][toNode] is not None:
        kwargs = queryGraph[fromNode][toNode]
        for attr in kwargs:
            try:
                # Use attribute name to determine default class.
                oclass = gqiDict[attr]
            except KeyError:
                pass
    else:
        kwargs = {}
    try:
        oclass = kwargs['__class__'] # LET USER SET CLASS TO USE
    except KeyError:
        pass
    return oclass(fromNode, toNode, dataGraph, queryGraph, dataMatch,
                  queryMatch, kwargs)


class GraphQuery(object):
    "represents a single query or subquery"
    # DEFAULT MAPPING OF ATTRIBUTE NAMES TO GQI CLASSES TO USE WITH THEM
    gqiDict = {'attr': AttributeGQI,
               'attrN': AttrContainerGQI,
               'f': CallableGQI,
               'fN': CallableContainerGQI,
               'subqueries': SubqueryGQI}
    newGQI = newGQI # USE THIS METHOD TO CHOOSE GQI CLASS FOR EACH ITERATOR

    def __init__(self, dataGraph, queryGraph, dataMatch=None, queryMatch=None):
        """Enumerate nodes in queryGraph in BFS order,
        constructing iterator stack"""
        self.dataGraph = dataGraph
        self.queryGraph = queryGraph
        if dataMatch is None:
            dataMatch = {}
        if queryMatch is None:
            queryMatch = {}
        self.dataMatch = dataMatch
        self.queryMatch = queryMatch
        # First we need to find start nodes: process them first and mark them
        # as generate all.
        isFollower = {}
        for node in queryGraph:
            for node2 in queryGraph[node]:
                # node2 has an incoming edge so it cannot be a start node.
                isFollower[node2] = True
        q = []
        self.q = q
        n = 0
        for node in queryGraph: # PLACE START NODES AT HEAD OF QUEUE
            if node not in isFollower:
                q.append(self.newGQI(ContainerGQI, None, node, dataGraph,
                                     queryGraph, dataMatch, queryMatch,
                                     self.gqiDict))
                n += 1
        if n == 0:
            # No start nodes; just add the first query node to the queue.
            for node in queryGraph:
                q.append(self.newGQI(ContainerGQI, None, node, dataGraph,
                                     queryGraph, dataMatch, queryMatch,
                                     self.gqiDict))
                n += 1
                break # Only add the first node.
        if n == 0:
            raise ValueError('query graph is empty!')

        visited = {}
        i = 0
        while i < n:
            # Add node to the queue even if it's already been visited
            # - but don't add its neighbours.
            if q[i].queryNode not in visited: # ADD NEIGHBORS TO THE QUEUE
                visited[q[i].queryNode] = True # MARK AS VISITED
                for node in queryGraph[q[i].queryNode]: # GET ALL ITS NEIGHBORS
                    #print 'QUEUE:', n, node
                    q.append(self.newGQI(GraphQueryIterator, q[i].queryNode,
                                         node, dataGraph, queryGraph,
                                         dataMatch, queryMatch,
                                         self.gqiDict))
                    n += 1
            i += 1

    def __iter__(self):
        "generates all subgraphs of dataGraph matching queryGraph"
        i = 0
        n = len(self.q)
        self.q[0].restart() # PRELOAD ITERATOR FOR 1ST NODE
        while i >= 0:
            dataNode = self.q[i].next()
            if dataNode is not None:
                #print i,qu[i].queryNode,dataNode
                if i + 1 < n: # MORE LEVELS TO QUERY?
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

    def compile(self, globals=None, compilerClass=GraphQueryCompiler,
                **kwargs):
        """return a compiled version of this query, using globals namespace
        if specified"""
        compiler = compilerClass(globalDict=globals, **kwargs)
        for gqi in self.q:
            compiler += gqi
        return compiler


SubqueryGQI.gqClass = GraphQuery # CLASS FOR CONSTRUCTING SUBQUERIES
