
cdef extern from "string.h":
  ctypedef int size_t
  void *memcpy(void *dst,void *src,size_t len)
  void *memmove(void *dst,void *src,size_t len)
  void *memset(void *b,int c,size_t len)

cdef extern from "stdlib.h":
  void free(void *)
  void *malloc(size_t)
  void *calloc(size_t,size_t)
  void *realloc(void *,size_t)
  int c_abs "abs" (int)
  void qsort(void *base, size_t nmemb, size_t size,
             int (*compar)(void *,void *))

cdef extern from "stdio.h":
  ctypedef struct FILE:
    pass
  FILE *fopen(char *,char *)
  int fclose(FILE *)
  int sscanf(char *str,char *fmt,...)
  int sprintf(char *str,char *fmt,...)
  int fprintf(FILE *ifile,char *fmt,...)
  char *fgets(char *str,int size,FILE *ifile)

cdef extern from "string.h":
  int strcmp(char *s1, char *s2)
  int strncmp(char *s1,char *s2,size_t len)
  char *strcpy(char *dest,char *src)
  char *strdup(char *)
  char *strcat(char *,char *)

cdef extern from "intervaldb.h":
  ctypedef struct IntervalMap:
    int start
    int end
    int target_id
    int target_start
    int target_end
    int sublist

  ctypedef struct IntervalIndex:
    int start
    int end

  ctypedef struct SublistHeader:
    int start
    int len

  ctypedef struct SubheaderFile:
    pass
  
  ctypedef struct IntervalDBFile:
    int n
    int ntop
    int nlists
    int div
    int nii
    IntervalIndex *ii
    SublistHeader *subheader
    SubheaderFile subheader_file
    FILE *ifile_idb

  ctypedef struct IntervalIterator:
    pass

  ctypedef struct FilePtrRecord:
    FILE *ifile
    int left
    int right
    int ihead
    char *filename



  int imstart_qsort_cmp(void *void_a,void *void_b)
  int target_qsort_cmp(void *void_a,void *void_b)
  IntervalMap *read_intervals(int n,FILE *ifile) except NULL
  SublistHeader *build_nested_list(IntervalMap im[],int n,int *p_n,int *p_nlists) except NULL
  SublistHeader *build_nested_list_inplace(IntervalMap im[],int n,int *p_n,int *p_nlists) except NULL
  IntervalMap *interval_map_alloc(int n) except NULL
  IntervalIterator *interval_iterator_alloc() except NULL
  int free_interval_iterator(IntervalIterator *it)
  IntervalIterator *reset_interval_iterator(IntervalIterator *it)
  int find_intervals(IntervalIterator *it0,int start,int end,IntervalMap im[],int n,SublistHeader subheader[],int nlists,IntervalMap buf[],int nbuf,int *p_nreturn,IntervalIterator **it_return) except -1
  char *write_binary_files(IntervalMap im[],int n,int ntop,int div,SublistHeader *subheader,int nlists,char filestem[])
  IntervalDBFile *read_binary_files(char filestem[],char err_msg[],int subheader_nblock) except NULL
  int free_interval_dbfile(IntervalDBFile *db_file)
  int find_file_intervals(IntervalIterator *it0,int start,int end,IntervalIndex ii[],int nii,SublistHeader subheader[],int nlists,SubheaderFile *subheader_file,int ntop,int div,FILE *ifile,IntervalMap buf[],int nbuf,int *p_nreturn,IntervalIterator **it_return) except -1
  int write_padded_binary(IntervalMap im[],int n,int div,FILE *ifile)
  int read_imdiv(FILE *ifile,IntervalMap imdiv[],int div,int i_div,int ntop)
  int save_text_file(char filestem[],char basestem[],char err_msg[],FILE *ofile)
  int text_file_to_binaries(FILE *infile,char buildpath[],char err_msg[])
  int C_int_max



cdef extern from "apps/maf2nclist.h":
  ctypedef struct SeqNameID_T:
    char *p
    int id
  ctypedef struct SeqIDMap:
    char *id
    int length
    int ns_id
    int offset
    int nlmsa_id

  int readMAFrecord(IntervalMap im[],int n,SeqIDMap seqidmap[],int nseq,
                    int lpoStart,int *p_block_len,FILE *ifile,int maxseq,
                    long long linecode_count[],int *p_has_continuation)
  int read_axtnet(IntervalMap im[], SeqIDMap seqidmap[], int nseq,
                  FILE *ifile, int maxseq, int *isrc, char *src_prefix,
                  char *dest_prefix)
  int seqnameID_qsort_cmp(void *void_a,void *void_b)
  int seqidmap_qsort_cmp(void *void_a,void *void_b)




cdef class IntervalDB:
  cdef int n
  cdef int ntop
  cdef int nlists
  cdef IntervalMap *im
  cdef SublistHeader *subheader


cdef class IntervalDBIterator:
  cdef IntervalIterator *it,*it_alloc
  cdef IntervalMap im_buf[1024]
  cdef int ihit,nhit,start,end
  cdef IntervalDB db

  cdef int cnext(self)

cdef class IntervalFileDB:
  cdef IntervalDBFile *db

cdef class NLMSASequence

cdef class IntervalFileDBIterator:
  cdef IntervalIterator *it,*it_alloc
  cdef IntervalMap *im_buf
  cdef int ihit,nhit,start,end,nbuf
  cdef IntervalFileDB db
  cdef IntervalDB idb

  cdef int restart(self,int start,int end,IntervalFileDB db,NLMSASequence ns) except -2
  cdef int reset(self) except -2
  cdef int cnext(self,int *pkeep)
  cdef int extend(self,int ikeep)
  cdef int saveInterval(self,int start,int end,int target_id,
                        int target_start,int target_end)
  cdef int nextBlock(self,int *pkeep) except -2
  cdef IntervalMap *getIntervalMap(self)
  cdef int loadAll(self) except -1
  cdef int copy(self,IntervalFileDBIterator src)



cdef class NLMSA:
  cdef readonly object pathstem
  cdef readonly object seqs
  cdef readonly object seqlist
  cdef readonly object seqDict
  cdef readonly NLMSASequence currentUnion
  cdef int do_build
  cdef readonly object lpoList,maxLPOcoord
  cdef int lpo_id
  cdef readonly int maxlen,inlmsa,is_bidirectional,pairwiseMode,in_memory_mode
  cdef public object _persistent_id,_ignoreShadowAttr,__doc__,_saveLocalBuild
  cdef public object inverseDB

  cdef void free_seqidmap(self,int nseq0,SeqIDMap *seqidmap)
  cdef void save_nbuild(self,int nbuild[])
  cdef NLMSASequence add_seqidmap_to_union(self,int j,SeqIDMap seqidmap[],
                                           NLMSASequence ns,FILE *build_ifile[],
                                           int nbuild[])

cdef class NLMSASequence:
  cdef readonly int id,length,nbuild,is_lpo,is_union
  cdef readonly object offset
  cdef readonly object seq
  cdef readonly object name
  cdef IntervalFileDB db
  cdef IntervalDB idb
  cdef FILE *build_ifile
  cdef readonly object filestem
  cdef readonly NLMSA nlmsaLetters
  cdef readonly object buildList
  
  cdef int saveInterval(self,IntervalMap im[],int n,int expand_self,FILE *ifile)

cdef class NLMSASlice:
  cdef readonly int start,stop,id
  cdef int n,nseqBounds,nrealseq,offset
  cdef IntervalMap *im
  cdef IntervalMap *seqBounds
  cdef readonly NLMSASequence nlmsaSequence
  cdef readonly NLMSA nlmsa
  cdef readonly object seq
  cdef object weakestLink

  cdef int findSeqBounds(self,int id,int ori)
  cdef object get_seq_interval(self, NLMSA nl, int targetID, int start, int stop)

cdef class NLMSASliceLetters:
  cdef readonly NLMSASlice nlmsaSlice


cdef class NLMSANode:
  cdef readonly int id,ipos
  cdef int istart,istop,n
  cdef readonly NLMSASlice nlmsaSlice

  cdef int check_edge(self,int iseq,int ipos)


cdef class NLMSASliceIterator:
  cdef int ipos,istart,istop
  cdef NLMSASlice nlmsaSlice

