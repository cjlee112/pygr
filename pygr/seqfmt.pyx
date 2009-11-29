
cdef extern from "stdio.h":
    ctypedef struct FILE:
        pass
    FILE *fopen(char *, char *)
    FILE *fdopen(int, char *)
    int fclose(FILE *)
    int sscanf(char *str, char *fmt, ...)
    int sprintf(char *str, char *fmt, ...)
    char *fgets(char *str, int size, FILE *ifile)
    int fputc(int, FILE *)

cdef extern from "ctype.h":
    int isspace(int)
    int isprint(int)

cdef extern from "string.h":
    char *strcpy(char *, char *)


def read_fasta_lengths(d, pyfile, filename):
    'read seq lengths from python file object, save into dictionary d'
    cdef int i
    cdef long long seqLength, ipos, offset # MUST USE 64-BIT INT!!!
    cdef char tmp[32768], fastastart[4], *p
    cdef FILE *ifile, *ifile2

    ifile = fdopen(pyfile.fileno(), 'r') # get FILE * from python file object
    if ifile == NULL:
        raise IOError('unable to open %s' % filename)
    outfile = filename + '.pureseq'
    # Save in binary mode, though shouldn't matter.
    ifile2 = fopen(outfile, 'wb')
    if ifile2 == NULL:
        raise IOError('unable to create %s' % (filename + '.pureseq'))
    id = None
    ipos = 0
    seqLength = 0
    strcpy(fastastart, '>')
    p = fgets(tmp, 32767, ifile) # read the first line of the FASTA file
    while p:
        if fastastart[0] == p[0]: #NEW SEQUENCE
            if id is not None and seqLength > 0:
                d[id] = seqLength, offset # SAVE THIS SEQ LENGTH
            id = str(p + 1).split()[0]
            offset = ipos
            seqLength = 0
        else:
            i = 0
            while p[i]:
                if isprint(p[i]) and not isspace(p[i]):
                    seqLength = seqLength + 1
                    fputc(p[i], ifile2)
                    ipos = ipos + 1
                i = i + 1
        p = fgets(tmp, 32767, ifile) # read the next line of the FASTA file
    if id is not None and seqLength>0:
        d[id] = seqLength, offset # SAVE THIS SEQ LENGTH
    fclose(ifile2)
