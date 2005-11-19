
#include "../intervaldb.h"
#include "maf2nclist.h"

int seqnameID_qsort_cmp(const void *void_a,const void *void_b)
{
  return strcmp(((SeqNameID_T *)void_a)->p,((SeqNameID_T *)void_b)->p);
}


int findseqname(char seqName[],SeqNameID_T seqnames[],int nseq0,int *p_nseq1,
		int maxseq)
{
  int i,l=0,r,mid;
  r=nseq0;
  while (l<r) { /* TRY FINDING IT USING BINARY SEARCH */
    mid=(l+r)/2;
    i=strcmp(seqnames[mid].p,seqName);
    if (i==0) /* FOUND IT */
      return seqnames[mid].id;
    else if (i<0) /* seqnames[mid] < seqName */
      l=mid+1;
    else /* seqName < seqnames[mid] */
      r=mid;
  }
  for (i=nseq0;i< *p_nseq1;i++) /* TRY FINDING IT IN UNSORTED ADDENDUM*/
    if (0==strcmp(seqnames[i].p,seqName))
      return seqnames[i].id;
  if (*p_nseq1 >= maxseq)
    return -1; /* ERROR: RAN OUT OF SPACE!!! */
  seqnames[*p_nseq1].p=malloc(strlen(seqName)+1); /* CREATE A NEW ENTRY HERE */
  strcpy(seqnames[*p_nseq1].p,seqName);
  seqnames[*p_nseq1].id = *p_nseq1;
  return (*p_nseq1)++;
}


void free_seqnames(SeqNameID_T seqnames[],int n)
{
  int i;
  for (i=0;i<n;i++) {
    free(seqnames[i].p);
    seqnames[i].p=NULL;
  }
}


int save_interval(IntervalMap *im,int start,int stop,int iseq,int istart,int istop)
{
  im->start=start;
  im->end=stop;
  im->target_id=iseq;
  im->target_start=istart;
  im->target_end=istop;
  im->sublist= -1; /* DEFAULT VALUE */
  return 1;
}


int readMAFrecord(IntervalMap im[],int n,SeqNameID_T seqnames[],int nseq0,int *p_nseq1,
		  int lpoStart,int *p_block_len,FILE *ifile,int maxseq)
{
  int i,start,seqStart,rev,junk,iseq,max_len=0;
  char *p,tmp[32768],seq[32768],prefix[8],seqName[64],oriFlag[8];
  for (p=fgets(tmp,32767,ifile);
       p && 7==sscanf(tmp,"%2s %s %d %d %2s %d %s",prefix,seqName,&seqStart,&junk,
		      oriFlag,&junk,seq) && 's'==prefix[0] && '\0'==prefix[1];
       p=fgets(tmp,32767,ifile)) {
/*     printf("\tALIGN: %s,%s,%d,%d,%s,%d,%s\n",prefix,seqName,seqStart,junk,oriFlag,junk,seq); */
    iseq=findseqname(seqName,seqnames,nseq0,p_nseq1,maxseq); /* LOOK UP INDEX FOR SEQ */
    if (iseq<0) return -1;  /* ERROR: RAN OUT OF SPACE!!! */
    if (0==strcmp("-",oriFlag))
      rev=1;
    else 
      rev=0;
    i=0;
    while (seq[i]) {
      while ('-'==seq[i]) i++; /* SKIP GAP REGIONS */
      if (seq[i]==0) break; /* END OF SEQUENCE */
      for (start=i;seq[i] && seq[i]!='-';i++); /* GET A SEQUENCE INTERVAL */
/*       printf("\t\t%d,%d\n",start,i); */
      if (n>=maxseq) return -1; /* ERROR: RAN OUT OF SPACE!!! */
      if (rev) 
	save_interval(im+n,-(lpoStart+i),-(lpoStart+start),iseq,seqStart,seqStart+i-start);
      else
	save_interval(im+n,lpoStart+start,lpoStart+i,iseq,seqStart,seqStart+i-start);
      n++;
      seqStart += i-start;
    }
    if (i>max_len) /* RECORD MAXIMUM seq LENGTH */
      max_len = i;
  }
/*   printf("readMAFrecord: %d hits\n",n); */
  if (p_block_len)
    *p_block_len = max_len;
  return n;
}
