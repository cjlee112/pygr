     
typedef struct {
  char *p;
  int id;
} SeqNameID_T;

extern int readMAFrecord(IntervalMap im[],int n,SeqNameID_T seqnames[],int nseq0,int *p_nseq1,
		  int lpoStart,FILE *ifile)
     ;

extern int seqnameID_qsort_cmp(const void *void_a,const void *void_b)
     ;

extern void free_seqnames(SeqNameID_T seqnames[],int n)
     ;

