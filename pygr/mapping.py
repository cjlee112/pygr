

from __future__ import generators
from schema import *
import classutil


def update_graph(self, graph):
    'save nodes and edges of graph to self'
    for node, d in graph.iteritems():
        self += node
        saveDict = self[node]
        for target, edge in d.iteritems():
            saveDict[target] = edge


class PathList(list):
    """Internal representation for storing both nodes and edges as list
    So filter functions can see both nodes and edges"""

    def __init__(self, nodes=None, edges=None):
        if nodes != None:
            list.__init__(self, nodes)
        else:
            list.__init__(self)
        if edges != None:
            self.edge = list(edges)
        else:
            self.edge = []

    def append(self, val):
        list.append(self, val)
        self.edge.append(val)

    def extend(self, l):
        list.extend(self, l) # EXTEND TOP-LEVEL LIST AS USUAL
        try: # EXTEND OUR EDGE LIST AS WELL
            self.edge.extend(l.edge)
        except AttributeError: #IF l HAS NO EDGES, PAD OUR EDGE LIST WITH Nones
            self.edge.extend(len(l) * [None])


class Edge(list):
    "Interface to edge information."
    isDirected = False

    def __init__(self, graph, nodes, edgeInfo):
        self.graph = graph
        if edgeInfo:
            self.edgeInfo = edgeInfo
        list.__init__(self, nodes) # SAVE NODES AS TUPLE

    def __getattr__(self, attr):
        try:
            return getattr(self.edgeInfo, attr)
        except AttributeError:
            if isinstance(self.edgeInfo, types.DictType):
                # Treat edgeInfo as an attribute dictionary.
                return self.edgeInfo[attr]
            raise AttributeError(attr)

    # Should we define setattr here too, to allow users to add new attribute
    # values? The problem is setattr is painful to implement due to the
    # recursive reference problem.

    def __cmp__(self, other): # DO WE NEED TO COMPARE EDGE INFO??
        if not isinstance(other, Edge): # CAN ONLY COMPARE A PAIR OF EDGES
            return -1
        diff = cmp(self.graph, other.graph)
        if diff: # NOT IN THE SAME GRAPH...
            return diff
        elif self.isDirected: # IF DIRECTED, JUST COMPARE IN CURRENT ORDER
            return tuple.__cmp__(self, other)
        else: # UNDIRECTED COMPARISON REQUIRES PUTTING BOTH IN SAME ORDER
            me = [i for i in self]
            you = [i for i in other]
            me.sort()
            you.sort()
            return cmp(me, you)

    # NEEDS SCHEMA SUPPORT: RETURN A SINGLE SCHEMA TUPLE DESCRIBING THIS EDGE.

class DirectedEdge(Edge):
    isDirected = True


# need a class to provide access to the edges in a graph
# iterator, membership test
#class EdgeSet


class dictEdge(dict):
    """2nd layer graph interface implemenation using dict.
    """
    dictClass = dict

    def __init__(self, graph, fromNode):
        self.graph = graph
        self.fromNode = fromNode
        self.dictClass.__init__(self) # INITIALIZE TOPLEVEL DICTIONARY

    def __iadd__(self, target):
        "Add edge from fromNode to target with no edge-info"
        self[target] = None
        return self # THIS IS REQUIRED FROM iadd()!!

    def __setitem__(self, target, edgeInfo):
        "Add edge from fromNode to target with edgeInfo"
        self.dictClass.__setitem__(self, target, edgeInfo)
        if target not in self.graph: # ADD NEW NODE TO THE NODE DICT
            self.graph += target

    _setitem_ = dict.__setitem__ # INTERNAL INTERFACE FOR SAVING AN ENTRY

    def __delitem__(self, target):
        "Delete edge from fromNode to target"
        try:
            self.dictClass.__delitem__(self, target)
        except KeyError: # GENERATE A MORE INFORMATIVE ERROR MESSAGE
            raise KeyError('No edge from node to target')

    def __isub__(self, target):
        "Delete edge from fromNode to target"
        self.__delitem__(target)
        return self # THIS IS REQUIRED FROM iadd()!!

    def edges(self):
        "Return iterator for accessing edges from fromNode"
        for target, edgeInfo in self.items():
            if isinstance(edgeInfo, Edge):
                yield edgeInfo
            else:
                yield Edge(self.graph, (self.fromNode, target, edgeInfo),
                           edgeInfo)


class dictGraph(dict):
    """Top layer graph interface implemenation using dict.
    """
    dictClass = dict
    edgeDictClass = dictEdge

    def __init__(self, schema=None, domain=None, range=None):
        if schema and domain and range:
            if domain not in schema:
                schema += domain #ADD DOMAIN AS NODE TO schema GRAPH
            schema[domain][range] = self
        self.dictClass.__init__(self) # INITIALIZE TOPLEVEL DICTIONARY

    def __iadd__(self, node, ruleSet=False):
        "Add node to graph with no edges"
        if node not in self:
            self.dictClass.__setitem__(self, node, self.edgeDictClass(self,
                                                                      node))
            if ruleSet == False:
                ruleSet = getschema(node, graph=self)
            for rule in ruleSet:
                if isinstance(rule[1], types.StringType):
                    # Attribute binding; bind directly to attribute.
                    setattr(node, rule[1], self[node])
        return self # THIS IS REQUIRED FROM iadd()!!

    def __setitem__(self, node, target):
        "This method exists only to support g[n]+=o.  Do not use as g[n]=foo."
        if self[node] != target:
            raise ValueError('Incorrect usage. Add edges using g[n]+=o \
                             or g[n][o]=edge.')

    def __delitem__(self, node):
        "Delete node from graph."
        # Grr, we really need to find all edges going to this node
        # and delete them.
        try:
            # Do stuff to remove it here...
            self.dictClass.__delitem__(self, node)
        except KeyError:
            raise KeyError('Node not present in mapping.')
        for rule in getschema(node, graph=self):
            if isinstance(rule[1], types.StringType): # ATTRIBUTE BINDING!
                delattr(node, rule[1])  # REMOVE ATTRIBUTE BINDING

    def __isub__(self, node):
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
    update = update_graph


class dictEdgeFB(dictEdge):
    "dictEdge subclass that saves both forward and backward edges"

    def __setitem__(self, target, edgeInfo):
        "Save edge in both forward and backward dicts."
        dictEdge.__setitem__(self, target, edgeInfo) # FORWARD EDGE
        try:
            d = self.graph._inverse[target]
        except KeyError:
            d = self.dictClass()
            self.graph._inverse[target] = d
        d[self.fromNode] = edgeInfo # SAVE BACKWARD EDGE

    def __invert__(self):
        "Get nodes with edges to this node"
        return self.graph._inverse[self.fromNode]


class dictGraphFB(dictGraph):
    "Graph that saves both forward and backward edges"

    def __init__(self, **kwargs):
        dictGraph.__init__(self, **kwargs)
        self._inverse = self.dictClass()
    __invert__ = classutil.standard_invert

    def __delitem__(self, node):
        "Delete node from the graph"
        try:
            fromNodes = self._inverse[node]
            del self._inverse[node] # REMOVE FROM _inverse DICT
        except KeyError:
            pass
        else: # DELETE EDGES TO THIS NODE
            for i in fromNodes:
                del self[i][node]
        dictGraph.__delitem__(self, node)


def listUnion(ivals):
    'merge all items using union operator'
    union = None
    for ival in ivals:
        try:
            union += ival
        except TypeError:
            union = ival
    return union


class DictQueue(dict):
    'each index entry acts like a queue; setitem PUSHES, and delitem POPS'

    def __setitem__(self, k, val):
        try:
            dict.__getitem__(self, k).append(val)
        except KeyError:
            dict.__setitem__(self, k, [val])

    def __getitem__(self, k):
        return dict.__getitem__(self, k)[0]

    def __delitem__(self, k):
        l=dict.__getitem__(self, k)
        del l[0]
        if len(l) == 0:
            dict.__delitem__(self, k)


################################ PYGR.DATA.SCHEMA - AWARE CLASSES BELOW


def close_if_possible(self):
    'close storage to ensure any pending data is written'
    try:
        do_close = self.d.close
    except AttributeError:
        pass
    else:
        do_close()


class Collection(object):
    'flexible storage mapping ID --> OBJECT'

    def __init__(self, saveDict=None, dictClass=dict, **kwargs):
        '''saveDict, if not None, the internal mapping to use as our storage.
        filename: if provided, a file path to a shelve (BerkeleyDB) file to
              store the data in.
        dictClass: if provided, the class to use for storage of dict data.'''
        if saveDict is not None:
            self.d = saveDict
        elif 'filename' in kwargs: # USE A SHELVE (BERKELEY DB)
            try:
                if kwargs['intKeys']: # ALLOW INT KEYS, HAVE TO USE IntShelve
                    self.__class__ = IntShelve
                else:
                    raise KeyError
            except KeyError:
                self.__class__ = PicklableShelve
            return self.__init__(**kwargs)
        else:
            self.d = dictClass()
        classutil.apply_itemclass(self, kwargs)

    def __getitem__(self, k):
        return self.d[k]

    def __setitem__(self, k, v):
        self.d[k] = v

    def __delitem__(self, k):
        del self.d[k]

    def __len__(self):
        return len(self.d)

    def __contains__(self, k):
        return k in self.d

    def __iter__(self):
        return iter(self.d)

    def __getattr__(self, attr):
        if attr == '__setstate__' or attr == '__dict__':
            # This prevents infinite recursion during unpickling.
            raise AttributeError
        try: # PROTECT AGAINST INFINITE RECURSE IF NOT FULLY __init__ED...
            return getattr(self.__dict__['d'], attr)
        except KeyError:
            raise AttributeError('Collection has no subdictionary')
    close = close_if_possible

    def __del__(self):
        'must ensure that shelve object is closed to save pending data'
        try:
            self.close()
        except classutil.FileAlreadyClosedError:
            pass


class PicklableShelve(Collection):
    'persistent storage mapping ID --> OBJECT'

    def __init__(self, filename, mode=None, writeback=False,
                 unpicklingMode=False, verbose=True, **kwargs):
        '''Wrapper for a shelve object that can be pickled.  Ideally, you
should specify a TWO letter mode string: the first letter to
indicate what mode the shelve should be initially opened in, and
the second to indicate the mode to open the shelve during unpickling.
e.g. mode='nr': to create an empty shelve (writable),
which in future will be re-opened read-only.
Also, mode=None makes it first attempt to open read-only, but if the file
does not exist will create it using mode 'c'. '''
        # Mark this string as a file path.
        self.filename = classutil.SourceFileName(str(filename))
        self.writeback = writeback
        if unpicklingMode or mode is None or mode == 'r':
            # Just use mode as given.
            self.mode = mode
        elif mode == 'n' or mode == 'c' or mode == 'w':
            # Ambiguous modes, warn & set default.
            if verbose:
                import sys
                print >>sys.stderr, '''Warning: you opened shelve file %s
in mode '%s' but this is ambiguous for how the shelve should be
re-opened later during unpickling.  By default it will be
re-opened in mode 'r' (read-only).  To make it be re-opened
writable, create it in mode '%sw', or call its method
reopen('w'), which will make it be re-opened in mode 'w' now and
in later unpickling.  To suppress this warning message, use the
verbose=False option.''' % (filename, mode, mode)
            self.mode = 'r'
        else: # PROCESS UNAMBIGUOUS TWO-LETTER mode STRING
            try:
                if len(mode) == 2 and mode[0] in 'ncwr' and mode[1] in 'cwr':
                    self.mode = mode[1] # IN FUTURE OPEN IN THIS MODE
                    mode = mode[0] # OPEN NOW IN THIS MODE
                else:
                    raise ValueError('invalid mode string: ' + mode)
            except TypeError:
                raise ValueError('file mode must be a string!')
        if unpicklingMode:
            self.d = classutil.open_shelve(filename, mode, writeback,
                                           allowReadOnly=True)
        else:
            self.d = classutil.open_shelve(filename, mode, writeback)
        classutil.apply_itemclass(self, kwargs)

    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(filename=0, mode=0, writeback=0)

    def close(self):
        '''close our shelve index file.'''
        self.d.close()

    def __setitem__(self, k, v):
        try:
            self.d[k] = v
        except TypeError:
            raise TypeError('to allow int keys, you must pass intKeys=True \
to constructor!')

    def reopen(self, mode='r'):
        're-open shelve in the specified mode, and save mode on self'
        self.close()
        self.d = classutil.open_shelve(self.filename, mode,
                                       writeback=self.writeback)
        self.mode = mode


class IntShelve(PicklableShelve):
    'provides an interface to shelve that can use int as key'

    def saveKey(self, i):
        'convert to string key'
        if isinstance(i, int):
            return 'int:%s' % i
        elif isinstance(i, str):
            return i
        try:
            return 'int:%s' % int(i)
        except TypeError:
            pass
        raise KeyError('IntShelve can only save int or str as key')

    def trueKey(self, k):
        "convert back to key's original format"
        if k.startswith('int:'):
            return int(k[4:])
        else:
            return k

    def __getitem__(self, k):
        return self.d[self.saveKey(k)]

    def __setitem__(self, k, v):
        self.d[self.saveKey(k)] = v

    def __delitem__(self, k):
        del self.d[self.saveKey(k)]

    def __contains__(self, k):
        return self.saveKey(k) in self.d

    def __iter__(self): ################ STANDARD ITERATOR METHODS
        for k in self.d:
            yield self.trueKey(k)

    def keys(self):
        return [k for k in self]

    def iteritems(self):
        for k, v in self.d.iteritems():
            yield self.trueKey(k), v

    def items(self):
        return [k for k in self.iteritems()]


## PACKING / UNPACKING METHODS FOR SEPARATING INTERNAL VS. EXTERNAL
## REPRESENTATIONS OF GRAPH NODES AND EDGES
## 1. ID-BASED PACKING: USE obj.id AS INTERNAL REPRESENTATION
##
## 2. TRIVIAL: INTERNAL AND EXTERNAL REPRESENTATIONS IDENTICAL
##    WORKS WELL FOR STRING OR INT NODES / EDGES.
##
## 3. PICKLE PACKING: USE PICKLE AS INTERNAL REPRESENTATION
def pack_id(self, obj):
    'extract id attribute from obj'
    try:
        return obj.id
    except AttributeError:
        if obj is None:
            return None
        raise


def unpack_source(self, objID):
    return self.sourceDB[objID]


def unpack_target(self, objID):
    return self.targetDB[objID]


def unpack_edge(self, objID):
    try:
        return self.edgeDB[objID]
    except KeyError:
        if objID is None:
            return None
        raise


def add_standard_packing_methods(localDict):
    localDict['pack_source'] = pack_id
    localDict['pack_target'] = pack_id
    localDict['pack_edge'] = pack_id
    localDict['unpack_source'] = unpack_source
    localDict['unpack_target'] = unpack_target
    localDict['unpack_edge'] = unpack_edge


def add_trivial_packing_methods(localDict):
    for name in ('pack_source', 'pack_target', 'pack_edge',
                 'unpack_source', 'unpack_target', 'unpack_edge'):
        localDict[name] = lambda self, obj: obj


def pack_pickle(self, obj):
    'get pickle string for obj'
    import pickle
    return pickle.dumps(obj)


def unpack_pickle(self, s):
    'unpickle string to get obj'
    import pickle
    return pickle.loads(s)


class MappingInverse(object):

    def __init__(self, db):
        self._inverse = db
        self.attr = db.inverseAttr

    def __getitem__(self, k):
        return self._inverse.sourceDB[getattr(k, self.attr)]
    __invert__ = classutil.standard_invert


class Mapping(object):
    '''dict-like class suitable for persistent usages.  Extracts ID values from
    keys and values passed to it, and saves IDs into its internal dictionary
    instead of the actual objects.  Thus, the external interface is objects,
    but the internal storage is ID values.'''

    def __init__(self, sourceDB, targetDB, saveDict=None, IDAttr='id',
                 targetIDAttr='id', itemAttr=None, multiValue=False,
                 inverseAttr=None, **kwargs):
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
        dictClass: if not None, is the class to use for storage of dict data'''
        if saveDict is None:
            self.d = classutil.get_shelve_or_dict(**kwargs)
        else:
            self.d = saveDict
        self.IDAttr = IDAttr
        self.targetIDAttr = targetIDAttr
        self.itemAttr = itemAttr
        self.multiValue = multiValue
        self.sourceDB = sourceDB
        self.targetDB = targetDB
        if inverseAttr is not None:
            self.inverseAttr = inverseAttr

    def __getitem__(self, k):
        kID = getattr(k, self.IDAttr)
        return self.getTarget(self.d[kID])

    def getTarget(self, vID):
        if self.itemAttr is not None:
            vID = getattr(vID, self.itemAttr)
        if self.multiValue:
            return [self.targetDB[j] for j in vID]
        else:
            return self.targetDB[vID]

    def __setitem__(self, k, v):
        if self.multiValue:
            v = [getattr(x, self.targetIDAttr) for x in v]
        else:
            v = getattr(v, self.targetIDAttr)
        self.d[getattr(k, self.IDAttr)] = v

    def __delitem__(self, k):
        del self.d[getattr(k, self.IDAttr)]

    def __contains__(self, k):
        return getattr(k, self.IDAttr) in self.d

    def __len__(self):
        return len(self.d)

    def clear(self):
        self.d.clear()

    def copy(self):
        return Mapping(self.sourceDB, self.targetDB, self.d.copy(),
                       self.IDAttr, self.targetIDAttr, self.itemAttr,
                       self.multiValue)

    def update(self, b):
        for k, v in b.iteritems():
            self[k] = v

    def get(self, k, v=None):
        try:
            return self[k]
        except KeyError:
            return v

    def setdefault(self, k, v=None):
        try:
            return self[k]
        except KeyError:
            self[k] = v
            return v

    def pop(self, k, v=None):
        try:
            v = self[k]
        except KeyError:
            return v
        del self[k]
        return v

    def popitem(self):
        kID, vID = self.d.popitem()
        return kID, self.getTarget(vID)

    def __iter__(self): ######################## ITERATORS
        for kID in self.d:
            yield self.sourceDB[kID]

    def keys(self):
        return [k for k in self]

    def itervalues(self):
        for vID in self.d.itervalues():
            yield self.getTarget(vID)

    def values(self):
        return [v for v in self.itervalues()]

    def iteritems(self):
        for kID, vID in self.d.iteritems():
            yield self.sourceDB[kID], self.getTarget(vID)

    def items(self):
        return [x for x in self.iteritems()]

    __invert__ = classutil.standard_invert
    _inverseClass = MappingInverse
    close = close_if_possible

    def __del__(self):
        close_if_possible(self)


def graph_cmp(self, other):
    'compare two graph dictionaries'
    import sys
    diff = cmp(len(self), len(other))
    if diff != 0:
        print >>sys.stderr, 'len diff:', len(self), len(other)
        return diff
    for node, d in self.iteritems():
        try:
            d2 = other[node]
        except KeyError:
            print >>sys.stderr, 'other missing key'
            return 1
        diff = cmp(d, d2)
        if diff != 0:
            print >>sys.stderr, 'value diff', d, d2
            return diff
    return 0


class IDNodeDict(object):
    """2nd layer graph interface implementation using proxy dict.
       e.g. shelve."""
    dictClass = dict

    def __init__(self, graph, fromNode):
        self.graph = graph
        self.fromNode = fromNode

    def __getitem__(self, target): ############# ACCESS METHODS
        edgeID = self.graph.d[self.fromNode][self.graph.pack_target(target)]
        return self.graph.unpack_edge(edgeID)

    def __setitem__(self, target, edgeInfo):
        "Add edge from fromNode to target with edgeInfo"
        self.graph.d[self.fromNode][self.graph.pack_target(target)] \
             = self.graph.pack_edge(edgeInfo)
        if not hasattr(self.graph, 'sourceDB') or \
           (hasattr(self.graph, 'targetDB') and \
           self.graph.sourceDB == self.graph.targetDB):
            self.graph += target # ADD NEW NODE TO THE NODE DICT

    def __delitem__(self, target):
        "Delete edge from fromNode to target"
        try:
            del self.graph.d[self.fromNode][self.graph.pack_target(target)]
        except KeyError: # GENERATE A MORE INFORMATIVE ERROR MESSAGE
            raise KeyError('No edge from node to target')

    ######### CONVENIENCE METHODS THAT USE THE ACCESS METHODS ABOVE
    def __iadd__(self, target):
        "Add edge from fromNode to target with no edge-info"
        self[target] = None
        return self # THIS IS REQUIRED FROM iadd()!!

    def __isub__(self, target):
        "Delete edge from fromNode to target"
        self.__delitem__(target)
        return self # THIS IS REQUIRED FROM iadd()!!

    def edges(self):
        "Return iterator for accessing edges from fromNode"
        for target, edgeInfo in self.graph.d[self.fromNode].items():
            yield (self.graph.unpack_source(self.fromNode),
                   self.graph.unpack_target(target),
                   self.graph.unpack_edge(edgeInfo))

    def __len__(self):
        return len(self.graph.d[self.fromNode])

    def keys(self):
        return [k[1] for k in self.edges()] ##### ITERATORS

    def values(self):
        return [k[2] for k in self.edges()]

    def items(self):
        return [k[1:3] for k in self.edges()]

    def __iter__(self):
        for source, target, edgeInfo in self.edges():
            yield target

    def itervalues(self):
        for source, target, edgeInfo in self.edges():
            yield edgeInfo

    def iteritems(self):
        for source, target, edgeInfo in self.edges():
            yield target, edgeInfo

    __cmp__ = graph_cmp


class IDNodeDictWriteback(IDNodeDict):
    'forces writing of subdictionary in shelve opened without writeback=True'

    def __setitem__(self, target, edgeInfo):
        d = self.graph.d[self.fromNode]
        d[self.graph.pack_target(target)] = self.graph.pack_edge(edgeInfo)
        self.graph.d[self.fromNode] = d # WRITE IT BACK... REQUIRED FOR SHELVE
        self.graph += target # ADD NEW NODE TO THE NODE DICT

    def __delitem__(self, target):
        d = self.graph.d[self.fromNode]
        del d[self.graph.pack_target(target)]
        self.graph.d[self.fromNode] = d # WRITE IT BACK... REQUIRED FOR SHELVE


class IDNodeDictWriteNow(IDNodeDictWriteback):
    'opens shelve for writing, writes an item, immediately reopens'

    def __setitem__(self, target, edgeInfo):
        self.graph.d.reopen('w')
        IDNodeDictWriteback.__setitem__(self, target, edgeInfo)
        self.graph.d.reopen('w')

    def __delitem__(self, target):
        self.graph.d.reopen('w')
        IDNodeDictWriteback.__delitem__(self, target)
        self.graph.d.reopen('w')


class IDGraphEdges(object):
    '''provides iterator over edges as (source, target, edge) tuples
       and getitem[edge] --> [(source, target), ...]'''

    def __init__(self, g):
        self.g = g

    def __iter__(self):
        for d in self.g.itervalues():
            for edge in d.edges():
                yield edge

    def __getitem__(self, edge):
        l = []
        for sourceID, targetID in self.d[edge.id]:
            l.append((self.g.sourceDB[sourceID], self.g.targetDB[targetID]))
        return l

    def __call__(self):
        return self


class IDGraphEdgeDescriptor(object):
    'provides interface to edges on demand'

    def __get__(self, obj, objtype):
        return IDGraphEdges(obj)


def save_graph_db_refs(self, sourceDB=None, targetDB=None, edgeDB=None,
                       simpleKeys=False, unpack_edge=None,
                       edgeDictClass=None, graph=None, **kwargs):
    'apply kwargs to reference DB objects for this graph'
    if sourceDB is not None:
        self.sourceDB = sourceDB
    else:
        # No source DB, store keys as internal representation.
        simpleKeys = True
    if targetDB is not None:
        self.targetDB=targetDB
    if edgeDB is not None:
        self.edgeDB=edgeDB
    else: # just save the edge object as itself (not its ID)
        self.pack_edge = self.unpack_edge = lambda edge: edge
    if simpleKeys: # SWITCH TO USING TRIVIAL PACKING: OBJECT IS ITS OWN ID
        self.__class__ = self._IDGraphClass
    if unpack_edge is not None:
        self.unpack_edge = unpack_edge # UNPACKING METHOD OVERRIDES DEFAULT
    if graph is not None:
        self.graph = graph
    if edgeDictClass is not None:
        self.edgeDictClass = edgeDictClass


def graph_db_inverse_refs(self, edgeIndex=False):
    'return kwargs for inverse of this graph, or edge index of this graph'
    if edgeIndex: # TO CONSTRUCT AN EDGE INDEX
        db = ('edgeDB', 'sourceDB', 'targetDB')
    else: # DEFAULT: TO CONSTRUCT AN INVERSE MAPPING OF THE GRAPH
        db = ('targetDB', 'sourceDB', 'edgeDB')
    try:
        d = dict(sourceDB=getattr(self, db[0]), targetDB=getattr(self, db[1]))
        try:
            d['edgeDB'] = getattr(self, db[2]) # EDGE INFO IS OPTIONAL
        except AttributeError:
            pass
    except AttributeError:
        d = dict(simpleKeys=True) # NO SOURCE / TARGET DB, SO USE IDs AS KEYS
    try: # COPY THE LOCAL UNPACKING METHOD, IF ANY
        if not edgeIndex:
            d['unpack_edge'] = self.__dict__['unpack_edge']
    except KeyError:
        pass
    return d


def graph_setitem(self, node, target):
    "This method exists only to support g[n]+=o.  Do not use as g[n]=foo."
    node = self.pack_source(node)
    try:
        if node == target.fromNode:
            return
    except AttributeError:
        pass
    raise ValueError('Incorrect usage. Add edges using g[n]+=o or \
g[n][o]=edge.')


class Graph(object):
    """Top layer graph interface implemenation using proxy dict.
       Works with dict, shelve, any mapping interface."""
    edgeDictClass = IDNodeDict # DEFAULT EDGE DICT

    def __init__(self, saveDict=None, dictClass=dict, writeNow=False,
                 **kwargs):
        if saveDict is not None: # USE THE SUPPLIED STORAGE
            self.d = saveDict
        elif 'filename' in kwargs: # USE A SHELVE (BERKELEY DB)
            try:
                if kwargs['intKeys']: # ALLOW INT KEYS, HAVE TO USE IntShelve
                    self.d = IntShelve(writeback=False, **kwargs)
                else:
                    raise KeyError
            except KeyError:
                self.d = PicklableShelve(writeback=False, **kwargs)
            if writeNow:
                # Write immediately.
                self.edgeDictClass = IDNodeDictWriteNow
            else:
                # Use our own writeback.
                self.edgeDictClass = IDNodeDictWriteback
        else:
            self.d = dictClass()
        save_graph_db_refs(self, **kwargs)

    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(d='saveDict', sourceDB=0, targetDB=0, edgeDB=0,
                        edgeDictClass=0)
    add_standard_packing_methods(locals())  ############ PACK / UNPACK METHODS

    def close(self):
        '''If possible, close our dict.'''
        try:
            do_close = self.d.close
        except AttributeError:
            pass
        else:
            do_close()

    def __len__(self):
        return len(self.d)

    def __iter__(self):
        for node in self.d:
            yield self.unpack_source(node)

    def keys(self):
        return [k for k in self]

    def itervalues(self):
        for node in self.d:
            yield self.edgeDictClass(self, node)

    def values(self):
        return [v for v in self.itervalues()]

    def iteritems(self):
        for node in self.d:
            yield self.unpack_source(node), self.edgeDictClass(self, node)

    def items(self):
        return [v for v in self.iteritems()]

    edges = IDGraphEdgeDescriptor()

    def __iadd__(self, node):
        "Add node to graph with no edges"
        node = self.pack_source(node)
        if node not in self.d:
            self.d[node] = {} # INITIALIZE TOPLEVEL DICTIONARY
        return self # THIS IS REQUIRED FROM iadd()!!

    def __contains__(self, node):
        return self.pack_source(node) in self.d

    def __getitem__(self, node):
        if node in self:
            return self.edgeDictClass(self, self.pack_source(node))
        raise KeyError('node not in graph')
    __setitem__ = graph_setitem

    def __delitem__(self, node):
        "Delete node from graph."
        node = self.pack_source(node)
        # Grr, we really need to find all edges going to this node
        # and delete them.
        try:
            del self.d[node]  # DO STUFF TO REMOVE IT HERE...
        except KeyError:
            raise KeyError('Node not present in mapping.')

    def __isub__(self, node):
        "Delete node from graph"
        self.__delitem__(node)
        return self # THIS IS REQUIRED FROM isub()!!
    update = update_graph
    __cmp__ = graph_cmp

    def __del__(self):
        try:
            self.close()
        except classutil.FileAlreadyClosedError:
            pass

# NEED TO PROVIDE A REAL INVERT METHOD!!
##     def __invert__(self):
##         'get an interface to the inverse graph mapping'
##         try: # CACHED
##             return self._inverse
##         except AttributeError: # NEED TO CONSTRUCT INVERSE MAPPING
##             self._inverse = IDGraph(~(self.d), self.targetDB, self.sourceDB,
##                                     self.edgeDB)
##             self._inverse._inverse = self
##             return self._inverse
##
    def __hash__(self): # SO SCHEMA CAN INDEX ON GRAPHS...
        return id(self)


class IDGraph(Graph):
    add_trivial_packing_methods(locals())

Graph._IDGraphClass = IDGraph


class KeepUniqueDict(dict):
    'dict that blocks attempts to overwrite an existing key'

    def __setitem__(self, k, v):
        try:
            if self[k] is v:
                return # ALREADY SAVED.  NOTHING TO DO!
        except KeyError: # NOT PRESENT, SO JUST SAVE THE VALUE
            dict.__setitem__(self, k, v)
            return
        raise KeyError('attempt to overwrite existing key!')

    def __hash__(self):
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)
