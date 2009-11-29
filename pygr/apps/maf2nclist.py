from pygr.cnestedlist import *
from specialseq import *


def maf2nclist(maffiles, stem):
    align = NLMSALetters(stem, 'w')
    seqs = {}
    for i in maffiles:
        f = open(i, 'r')
        if f.readline().split()[0] != '##maf':
            raise "Error processing %s: Invalid file format" % (i)

        l = f.readline()
        while l:
##            print l
            la = l.split()
            if(len(la) == 0 or la[0] == '#'):
                pass
            elif(la[0] == 'a'):
                storeMAFrecord(align, seqs, f)
            else:
                return
            l=f.readline()
    align.build()
    return align


def storeMAFrecord(align, seqs, fh):
    s = fh.readline().split()
    begin = align.seqlist[0].length
    while len(s) == 7 and s[0] == 's':
##        print s
        lpoStart = begin
        seqStart = int(s[2])
        try:
            seq = seqs[s[1]]
        except:
            seq = refSequence(s[1])
            seqs[s[1]] = seq
        if (s[4] == '-'):
            rev = True
        else:
            rev = False
        for ival in s[6].split('-'):
            if len(ival) > 0:
                if (rev):
                    align[-(lpoStart + len(ival)):-lpoStart] = \
                            seq[seqStart:seqStart + len(ival)]
                else:
                    align[lpoStart:lpoStart + len(ival)] = \
                            seq[seqStart:seqStart + len(ival)]
            seqStart += len(ival)
            lpoStart += len(ival) + 1
        s = fh.readline().split()


maf2nclist(['chrX.maf', ], 'testdb/chrX')
