from seqref import *

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
                newnodes+=[(self.sequences[s[1]][-int(s[2]):-int(s[2])-int(s[3])],s[6])]
            else:
                newnodes+=[(self.sequences[s[1]][int(s[2]):int(s[2])+int(s[3])],s[6])]
                
            s=fh.readline().split()
            
        for i in range(len(newnodes)):
            for j in range(i+1, len(newnodes)):
                self.mAlign[newnodes[i][0]][newnodes[j][0]]=(edgeInfo,newnodes[i][1],newnodes[j][1])
                self.mAlign[newnodes[j][0]][newnodes[i][0]]=(edgeInfo,newnodes[j][1],newnodes[i][1])
               
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
