
cdef extern from "stdio.h":
  ctypedef struct FILE:
    pass
  FILE *fopen(char *,char *)
  int fclose(FILE *)
  int sscanf(char *str,char *fmt,...)
  int sprintf(char *str,char *fmt,...)
  char *fgets(char *str,int size,FILE *ifile)

cdef extern from "ctype.h":
    int isspace(int)
    int isprint(int)

cdef extern from "string.h":
    char *strcpy(char *,char *)



def read_fasta_lengths(d,filename):
    cdef int i,seqLength
    cdef char tmp[32768],fastastart[4],*p
    cdef FILE *ifile

    ifile=fopen(filename,'r')
    if ifile==NULL:
        raise IOError('unable to open %s' % filename)
    id=None
    seqLength=0
    strcpy(fastastart,'>')
    p=fgets(tmp,32767,ifile) # READ THE FIRST LINE OF THE MAF FILE
    while p:
        if fastastart[0]==p[0]: #NEW SEQUENCE
            if id is not None and seqLength>0:
                d[id]=seqLength # SAVE THIS SEQ LENGTH
            id=str(p+1).split()[0]
            seqLength=0
        else:
            i=0
            while p[i]:
                if isprint(p[i]) and not isspace(p[i]):
                    seqLength=seqLength+1
                i=i+1
        p=fgets(tmp,32767,ifile) # READ THE FIRST LINE OF THE MAF FILE
    if id is not None and seqLength>0:
        d[id]=seqLength # SAVE THIS SEQ LENGTH
    fclose(ifile)
    
