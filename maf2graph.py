from seqref import *

class Align2:
    s1=''
    s2=''
    
    def __init__(self, s1='', s2=''):
        self.s1=s1
        self.s2=s2
        if(len(self.s1)<len(self.s2)):
            self.s1=self.s1+(len(self.s2)-len(self.s1))*'?'
        elif(len(self.s2)<len(self.s1)):
            self.s2=self.s2+(len(self.s1)-len(self.s2))*'?'
            
    def intervals(self):
        begin=0
        gaps1=0
        gaps2=0
        for end in range(len(self.s1)):
            if(self.s1[end]=='-' or self.s2[end]=='-'):
                if(begin<end):
                    yield ((begin-gaps1,end-gaps1,self.s1[begin:end]),(begin-gaps2,end-gaps2,self.s2[begin:end]))
                begin=end+1
                if(self.s1[end]=='-'):
                    gaps1=gaps1+1
                if(self.s2[end]=='-'):
                    gaps2=gaps2+1
        end=end+1
        if(begin<end):
            yield ((begin-gaps1,end-gaps1,self.s1[begin:end]),(begin-gaps2,end-gaps2,self.s2[begin:end]))

def reverse_complement(s):
    compl={'a':'t', 'c':'g', 'g':'c', 't':'a', 'u':'a', 'n':'n',
           'A':'T', 'C':'G', 'G':'C', 'T':'A', 'U':'A', 'N':'N'}
    return ''.join([compl.get(c,c) for c in s[::-1]])

class MafParser:
    """
    Parses .maf files as defined by the Haussler dataset. The results of parsing are
    available as pathmapping between the sequences in the alignment. The sequences
    themselves are assumed unknown and use AnonSequence class.
    """
    
    options={}
    mAlign=PathMapping()
    sequences={}
    def setpar(self, arry):
        """internal function """
        for p in arry:
            (key,value)=p.split('=')
            self.options[key]=value

    def readalign(self,opt,fh):
        """internal function parses alignment record from .maf file """
##        print "entering readalign:", opt
        edgeInfo={}
        for p in opt:
            (key,value)=p.split('=')
            edgeInfo[key]=value

        s=fh.readline().split()
##        print s;
        newnodes=[]
        while len(s)==7 and s[0]=='s':
            if(not self.sequences.has_key(s[1])):
                self.sequences[s[1]]=AnonSequence(int(s[5]),s[1])
                self.mAlign+=self.sequences[s[1]]
            if(s[4]=='-'):
                node=(self.sequences[s[1]][-int(s[2]):-int(s[2])-int(s[3])],s[6])
                self.sequences[s[1]].seqsplice(reverse_complement(node[1].replace('-','')),node[0].start,node[0].end)
            else:
                node=(self.sequences[s[1]][ int(s[2]): int(s[2])+int(s[3])],s[6])
                self.sequences[s[1]].seqsplice(node[1].replace('-',''),node[0].start,node[0].end)
            newnodes+=[node]

            s=fh.readline().split()
            
        for i in range(len(newnodes)):
            for j in range(i+1, len(newnodes)):
                for inter in Align2(newnodes[i][1],newnodes[j][1]).intervals():
                    self.mAlign[newnodes[i][0][inter[0][0]:inter[0][1]]][newnodes[j][0][inter[1][0]:inter[1][1]]]=(edgeInfo,inter[0][2],inter[1][2])
                    self.mAlign[newnodes[j][0][inter[1][0]:inter[1][1]]][newnodes[i][0][inter[0][0]:inter[0][1]]]=(edgeInfo,inter[1][2],inter[0][2])
               
    def parse(self,filehandle):
        """parses the .maf filehandle """
        l=filehandle.readline();
        if l.split()[0]!='##maf':
            return
        else:
            self.setpar(l.split()[1:])

        l=filehandle.readline()
        while l:
            la = l.split();
##            print la
            if(len(la)==0 or la[0]=='#'):
##                print "skipping"
                1
            elif(la[0]=='a'):
##                print "reading alignment"
                self.readalign(la[1:],filehandle)
            else:
##                print "end of records"
                return
            l=filehandle.readline()
