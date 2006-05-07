     
typedef struct {
  char *p;
  int id;
} SeqNameID_T;

typedef struct {
  char *id;
  int length;
  int ns_id;
  int offset;
  int nlmsa_id;
} SeqIDMap;




extern int readMAFrecord(IntervalMap im[],int n,SeqIDMap seqidmap[],int nseq,
		  int lpoStart,int *p_block_len,FILE *ifile,int maxseq)
     ;

extern int seqnameID_qsort_cmp(const void *void_a,const void *void_b)
     ;

extern void free_seqnames(SeqNameID_T seqnames[],int n)
     ;

extern int seqidmap_qsort_cmp(const void *void_a,const void *void_b);
