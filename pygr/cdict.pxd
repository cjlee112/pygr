cdef extern from "string.h":
  ctypedef int size_t

cdef extern from "stdlib.h":
  void free(void *)
  void qsort(void *base, size_t nmemb, size_t size,
             int (*compar)(void *,void *))

cdef extern from "cgraph.h":
    ctypedef struct CDictEntry:
        int k
        int v

    ctypedef struct CDict:
        int n
        CDictEntry *dict

    CDict *cdict_alloc(int n)
    int cdict_free(CDict *d)
    int cdict_qsort_cmp(void *void_a,void *void_b)
    CDictEntry *cdict_getitem(CDict *d,int k)

    ctypedef struct CGraphEntry:
        int k
        CDict *v

    ctypedef struct CGraph:
        int n
        CGraphEntry *dict

    CGraph *cgraph_alloc(int n)
    int cgraph_free(CGraph *d)
    CGraphEntry *cgraph_getitem(CGraph *d,int k)
    int *calloc_int(int n)



cdef class CIntDictionary:
    cdef CDict *d
cdef class CDictionary:
    cdef CDict *d
    cdef object key_index
cdef class CDictionaryRef:
    cdef CDict *d
    cdef object key_index
    cdef object graph


cdef class CGraphDict:
    cdef CGraph *d
    cdef public object key_index

cdef class CDictIterator:
    cdef int i
    cdef CDict *d
    cdef object cd
    cdef int yieldKeys
    cdef int yieldValues
    cdef object key_index


cdef class CGraphIterator:
    cdef int i
    cdef CGraphDict g
    cdef int yieldKeys
    cdef int yieldValues

cdef class IntTupleArray:
    cdef int *data
    cdef int n
    cdef int dim
    cdef int n_alloc
    cdef int vector_len
    cdef int *vector
    cdef int skipIndex
    cdef readonly int isDone

