from __future__ import generators
from seqref import *
from pygr.seqdb import *
import string


def refIntervals(s):
    begin = 0
    gaps = 0

    end = 0
    for end in range(len(s)):
        if (s[end] == '-'):
            if (begin < end):
                yield (begin, end, begin - gaps, end - gaps, s[begin:end])
            begin = end + 1
            gaps += 1
    if end == 0:
        return
    end = end + 1
    if (begin < end):
        yield (begin, end, begin - gaps, end - gaps, s[begin:end])


def reverse_complement(s):
    compl={'a': 't', 'c': 'g', 'g': 'c', 't': 'a', 'u': 'a', 'n': 'n',
           'A': 'T', 'C': 'G', 'G': 'C', 'T': 'A', 'U': 'A', 'N': 'N'}
    return ''.join([compl.get(c, c) for c in s[::-1]])


class MafParser:
    """
    Parses .maf files as defined by the Haussler dataset. The results
    of parsing are available as pathmapping between the sequences
    in the alignment. The sequences themselves are assumed unknown
    and use AnonSequence class.
    """
    options = {}

    def __init__(self, vbase=''):
        self.mAlign = PathMapping()
        self.sequences = {}
        self.vbase = vbase
        self._vid = 0

    def setpar(self, arry):
        """internal function """
        for p in arry:
            (key, value) = p.split('=')
            self.options[key] = value

    def readalign(self, opt, fh):
        """internal function parses alignment record from .maf file"""
##        print "entering readalign:", opt
        edgeInfo = {}
        for p in opt:
            (key, value) = p.split('=')
            edgeInfo[key] = value

        s = fh.readline().split()
##        print s;
        if(len(s) == 7 and s[0] == 's'):
            vseq = self._vseq(len(s[6]))
            self.mAlign += vseq
        while len(s) == 7 and s[0] == 's':
            # Add the sequence name to the dictionary,
            # then add a corresponding node to the mapping.
            if s[1] not in self.sequences:
                self.sequences[s[1]] = AnonSequence(int(s[5]), s[1])
                self.mAlign += self.sequences[s[1]]

            # PROCESS THE KNOWN INTERVALS
            if(s[4] == '-'):
                ns = self.sequences[s[1]][-int(s[2]):-int(s[2]) - int(s[3])]
                self.sequences[s[1]].seqsplice(reverse_complement(
                    s[6].replace('-', '')), ns.start, ns.stop)
            else:
                ns = self.sequences[s[1]][int(s[2]):int(s[2]) + int(s[3])]
                self.sequences[s[1]].seqsplice(s[6].replace('-', ''),
                                               ns.start, ns.stop)

            for inter in refIntervals(s[6]):
                self.mAlign[vseq[inter[0]:inter[1]]][ns[inter[2]:inter[3]]] = \
                        (inter[4])
                self.mAlign[ns[inter[2]:inter[3]]][vseq[inter[0]:inter[1]]] = \
                        (inter[4])

            s = fh.readline().split()

    def parse(self, filehandle):
        """parses the .maf filehandle """
        l = filehandle.readline()
        if l.split()[0] != '##maf':
            return
        else:
            self.setpar(l.split()[1:])

        l=filehandle.readline()
        while l:
            la = l.split()
##            print la
            if(len(la)==0 or la[0]=='#'):
##                print "skipping"
                1
            elif(la[0]=='a'):
##                print "reading alignment"
                self.readalign(la[1:], filehandle)
            else:
##                print "end of records"
                return

            l=filehandle.readline()

    def _vseq(self, slen):
        alen = len(string.letters)
        uid = self.vbase
        cum = self._vid
        while cum / alen > 0:
            uid += string.letters[cum % alen]
            cum /= alen
        uid += string.letters[cum % alen]
        self._vid += 1
        return AnonSequence(slen, uid)

    def _dump(self, alignTab, sequenceTab=None):
        for row in self.mAlign.repr_dict():
            alignTab.write('\t'.join(map(lambda x: str(x), row.values()))
                           + '\n')

        if(sequenceTab):
            for s in self.sequences.values():
                for inter in s.known_int():
                    sequenceTab.write('\t'.join(map(lambda x: str(x),
                                                    inter.values())) + '\n')

        del self.mAlign
        del self.sequences
        self.mAlign = PathMapping()
        self.sequences = {}

    def parseIntoDB(self, filehandle, cursor, alignTab, sequenceTab=None,
                    update=None):
        """parses the .maf filehandle into database using cursors"""
        c = filehandle.tell()
        filehandle.seek(0, 2)
        filesize = filehandle.tell()
        filehandle.seek(c)
        l = filehandle.readline()
        rc = 0
        count = 0
        if l.split()[0] != '##maf':
            return
        else:
            self.setpar(l.split()[1:])

        l=filehandle.readline()
        while l:
            la = l.split()
##            print la
            if(len(la)==0 or la[0]=='#'):
##                print "skipping"
                1
            elif(la[0]=='a'):
##                print "reading alignment"
                count+=1
                self.readalign(la[1:], filehandle)
                self._dump(alignTab, sequenceTab)
                if(update and not count % 1000):
                    cursor.execute(update % (int(filehandle.tell() * 100.
                                                 / filesize)))
            else:
##                print "end of records"
                return
            l=filehandle.readline()
