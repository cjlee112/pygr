
# BASIC CLASS ATTRIBUTES DEFINED IN cdict.pxd

class KeyIndex(object):
    'construct integer index for sets of python objects'

    def __init__(self):
        self.key_index = {}
        self.index_keys = []

    def __getitem__(self, k):
        'get the integer index for python object k, or create one if needed'
        try:
            return self.key_index[k]
        except KeyError:
            i = len(self.index_keys)
            self.key_index[k] = i
            self.index_keys.append(k)
            return i


class CGraphQueryMatch(dict):
    'provides mapping of query nodes / edges onto CGraphDict nodes / edges'

    def __init__(self, gqcompiler, dataTuple, dataGraph):
        dict.__init__(self)
        i = 0
        index_keys = dataGraph.key_index.index_keys
        l = dataTuple
        while len(l) >= 2: # STORE MAPPING INTO OUR DICT
            node, edge = l[:2]
            self[gqcompiler.gqi[i].queryNode] = index_keys[node]
            if gqcompiler.gqi[i].fromNode is not None:
                self[gqcompiler.gqi[i].fromNode, gqcompiler.gqi[i].queryNode] \
                        = index_keys[edge]
            i = i + 1
            l = l[2:]


class QueryMatchIterator(object):
    'iterate over items in QueryMatchList'

    def __init__(self, qmlist):
        self.qmlist = qmlist
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.i >= len(self.qmlist.matches):
            raise StopIteration
        queryMatch = CGraphQueryMatch(self.qmlist.gqcompiler,
                                      self.qmlist.matches[self.i],
                                      self.qmlist.dataGraph)
        self.i = self.i + 1
        return queryMatch


class QueryMatchList(object):
    'provide queryMatch mapping based on a list of (node,edge) tuples'

    def __init__(self, gqcompiler, matches, dataGraph, query_f):
        self.gqcompiler = gqcompiler
        self.matches = matches
        self.dataGraph = dataGraph
        self.key_index = dataGraph.key_index
        self.query_f = query_f

    def __len__(self):
        return len(self.matches)

    def __iter__(self):
        return QueryMatchIterator(self)

    def __getitem__(self, k):
        import types
        # Rewrap just the specified splice of our list.
        if isinstance(k, types.SliceType):
            raise IndexError('this type cannot do slicing...')
            #return QueryMatchList(self.gqcompiler, self.matches.__getitem__(k), self.dataGraph)
        else: # RETURN THE SPECIFIC ITEM REQUESTED AS A QUERY MATCH MAPPING
            return CGraphQueryMatch(self.gqcompiler, self.matches[k],
                                    self.dataGraph)

    def get_more(self):
        if self.matches.isDone:
            raise StopIteration
        self.query_f(self.gqcompiler, self.dataGraph, 0, self.matches, self)


cdef class CIntDictionary:
    'both keys and values MUST be integers'

    def __new__(self, d):
        cdef int i, k, v
        self.d = cdict_alloc(len(d))
        if self.d == NULL: # NO MORE MEMORY??
            raise MemoryError()
        i = 0
        for k, v in d.iteritems():
            self.d[0].dict[i].k = k
            self.d[0].dict[i].v = v
            i = i + 1
        self.d[0].n = i
        qsort(self.d[0].dict, self.d[0].n, sizeof(CDictEntry), cdict_qsort_cmp)

    def keys(self):
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append(self.d[0].dict[i].k)
        return l

    def __iter__(self):
        return iter(self.keys())

    def items(self):
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append((self.d[0].dict[i].k, self.d[0].dict[i].v))
        return l

    def iteritems(self):
        return iter(self.items())

    def __getitem__(self, k):
        cdef CDictEntry *e

        e = cdict_getitem(self.d, k)
        if e == NULL:
            raise KeyError
        return e[0].v

    def __dealloc__(self):
        if self.d:
            cdict_free(self.d)


cdef CDict *cdict_init(object d, object key_index):
    cdef int i
    cdef CDict *cd
    cd = cdict_alloc(len(d))
    if cd == NULL: # NO MORE MEMORY??
        raise MemoryError()
    i = 0
    for k, v in d.iteritems():
        cd[0].dict[i].k = key_index[k]
        cd[0].dict[i].v = key_index[v]
        i = i + 1
    cd[0].n = i
    qsort(cd[0].dict, cd[0].n, sizeof(CDictEntry), cdict_qsort_cmp)
    return cd


cdef class CDictionary:
    'general purpose dict in C; key_index supplies mapping to integer indexes'

    def __new__(self, d, key_index):
        self.d = cdict_init(d, key_index)
        self.key_index = key_index

    def __getitem__(self, k):
        cdef CDictEntry *e

        # This raises KeyError if k not in key_index.
        e = cdict_getitem(self.d, self.key_index.key_index[k])
        if e==NULL:
            raise KeyError
        return self.key_index.index_keys[e[0].v]

    def __iter__(self): # GRR, ALL THESE DARN ITERATOR VARIANTS...
        return CDictIterator(self)

    def iteritems(self):
        return CDictIterator(self, 1, 0)

    def itervalues(self):
        return CDictIterator(self, 0, 1)

    def items(self): # GRR, ALL THESE DARN LIST VARIANTS
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append((self.key_index.index_keys[self.d[0].dict[i].k],
                      self.key_index.index_keys[self.d[0].dict[i].v]))
        return l

    def keys(self):
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append(self.key_index.index_keys[self.d[0].dict[i].k])
        return l

    def values(self):
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append(self.key_index.index_keys[self.d[0].dict[i].v])
        return l

    def __dealloc__(self):
        if self.d:
            cdict_free(self.d)


cdef class CDictionaryRef:
    'holds a reference to a CDict'

    def __new__(self, CGraphDict graph, int idict):
        self.graph = graph # HOLD A REFERENCE TO OUR GRAPH
        self.key_index = graph.key_index
        self.d = graph.d[0].dict[idict].v

    def __getitem__(self, k):
        cdef CDictEntry *e

        # This raises KeyError if k not in key_index.
        e = cdict_getitem(self.d, self.key_index.key_index[k])
        if e == NULL:
            raise KeyError
        return self.key_index.index_keys[e[0].v]

    def __iter__(self): # GRR, ALL THESE DARN ITERATOR VARIANTS...
        return CDictIterator(None, 1, 0, self)

    def iteritems(self):
        return CDictIterator(None, 1, 1, self)

    def itervalues(self):
        return CDictIterator(None, 0, 1, self)

    def items(self): # GRR, ALL THESE DARN LIST VARIANTS
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append((self.key_index.index_keys[self.d[0].dict[i].k],
                      self.key_index.index_keys[self.d[0].dict[i].v]))
        return l

    def keys(self):
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append(self.key_index.index_keys[self.d[0].dict[i].k])
        return l

    def values(self):
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append(self.key_index.index_keys[self.d[0].dict[i].v])
        return l


cdef class CGraphDict:
    'general purpose graph in C; key_index supplies mapping to integer indexes'

    def __new__(self, d, key_index):
        cdef int i
        self.d = cgraph_alloc(len(d))
        self.key_index = key_index
        if self.d == NULL: # NO MORE MEMORY??
            raise MemoryError()
        l = []
        for k in d:
            l.append(key_index[k])
        l.sort()
        i = 0
        for k in l:
            self.d[0].dict[i].k = k
            self.d[0].dict[i].v = cdict_init(d[key_index.index_keys[k]],
                                             key_index)
            i = i + 1
        self.d[0].n = i

    def __getitem__(self, k):
        cdef CGraphEntry *e
        cdef CDictionaryRef cd
        cdef int i

        # This raises KeyError if k not in key_index.
        e = cgraph_getitem(self.d, self.key_index.key_index[k])
        if e == NULL:
            raise KeyError
        i = e - self.d[0].dict # GET INDEX BY SUBTRACTING POINTERS
        # Reference holder for Python to access this cdict.
        cd = CDictionaryRef(self, i)
        return cd

    def __iter__(self): # GRR, ALL THESE DARN ITERATOR VARIANTS...
        return CGraphIterator(self)

    def iteritems(self):
        return CGraphIterator(self, 1, 1)

    def itervalues(self):
        return CGraphIterator(self, 0, 1)

    def items(self): # GRR, ALL THESE DARN LIST VARIANTS
        cdef int i
        cdef CDictionaryRef cd
        l = []
        for i from 0 <= i < self.d[0].n:
            # Reference holder for Python to access this cdict.
            cd = CDictionaryRef(self, i)
            l.append((self.key_index.index_keys[self.d[0].dict[i].k], cd))
        return l

    def keys(self):
        cdef int i
        l = []
        for i from 0 <= i < self.d[0].n:
            l.append(self.key_index.index_keys[self.d[0].dict[i].k])
        return l

    def values(self):
        cdef int i
        cdef CDictionaryRef cd
        l = []
        for i from 0 <= i < self.d[0].n:
            # Reference holder for Python to access this cdict.
            cd = CDictionaryRef(self, i)
            l.append(cd)
        return l

    def __dealloc__(self):
        if self.d:
            free(self.d[0].dict)
            free(self.d)


cdef class CDictIterator:
    'iterator for looping over elements in CDictionary'

    def __init__(self, CDictionary cd, yieldKeys=1, yieldValues=0,
                 CDictionaryRef cdr=None):
        if cdr is not None:
            self.cd = cdr
            self.d = cdr.d
            self.key_index = cdr.key_index
        elif cd is not None:
            self.cd = cd
            self.d = cd.d
            self.key_index = cd.key_index
        else:
            raise TypeError('cd or cdr must be non-None')
        self.yieldKeys = yieldKeys
        self.yieldValues = yieldValues
        self.i = 0

    def __iter__(self):
        return self

    def __next__(self): # PYREX USES THIS NON-STANDARD NAME!!!
        if self.i >= self.d[0].n:
            raise StopIteration
        if self.yieldKeys:
            k = self.key_index.index_keys[self.d[0].dict[self.i].k]
        if self.yieldValues:
            v = self.key_index.index_keys[self.d[0].dict[self.i].v]
            if self.yieldKeys:
                result = (k, v)
            else:
                result = v
        else:
            result = k
        self.i = self.i + 1
        return result


cdef class CGraphIterator:
    'iterator for looping over elements in CGraphDict'

    def __init__(self, CGraphDict g, yieldKeys=1, yieldValues=0):
        self.g = g
        self.yieldKeys = yieldKeys
        self.yieldValues = yieldValues
        self.i =0

    def __iter__(self):
        return self

    def __next__(self): # PYREX USES THIS NON-STANDARD NAME!!!
        cdef CDictionaryRef cd
        if self.i >= self.g.d[0].n:
            raise StopIteration
        if self.yieldKeys:
            k = self.g.key_index.index_keys[self.g.d[0].dict[self.i].k]
        if self.yieldValues:
            # Reference holder for Python to access this cdict.
            cd = CDictionaryRef(self.g, self.i)
            if self.yieldKeys:
                result = (k, cd)
            else:
                result = cd
        else:
            result = k
        self.i = self.i + 1
        return result

cdef class IntTupleArray:
    'holder for array of integer index values'

    def __new__(self, n, vector_len, dim=1, skipIndex=None):
        self.n_alloc = n
        self.n = 0
        self.dim = dim
        self.data = calloc_int(n * vector_len * dim)
        self.vector_len = vector_len
        self.vector = calloc_int(vector_len)
        if skipIndex is None:
            self.skipIndex = vector_len - 1
        else:
            self.skipIndex = skipIndex
        self.isDone = 0

    def set_vector(self, vector, gotoNext=0):
        'save vector for continuing from this point, or next point'
        cdef int i
        for i from 0 <= i < self.vector_len:
            self.vector[i] = vector[i]
        if gotoNext: # INCREMENT THE LAST VALUE
            self.vector[self.skipIndex] = self.vector[self.skipIndex] + 1

    def __getitem__(self, int k):
        cdef int i
        cdef int *data
        if k < 0 or k >= self.n:
            raise IndexError('index out of bounds')
        data = self.data + k * self.vector_len * self.dim
        l = []
        for i from 0 <= i < self.vector_len * self.dim:
            l.append(data[i])
        return l

    def __len__(self):
        return self.n

    def realloc(self, n):
        'change the number of hits to be loaded as one block'
        free(self.data)
        self.n_alloc = n
        self.data=calloc_int(n * self.vector_len * self.dim)

    def __dealloc__(self):
        if self.data:
            free(self.data)
        if self.vector:
            free(self.vector)
