
class Autodict(dict):
    'dict whose values are lists of length n, initially filled with blanks " "'
    def __init__(self,n):
        self.n=n
        self.first=None
        dict.__init__(self)
    def __getitem__(self,k):
        'get list associated with key k, or create one if not present'
        try:
            return dict.__getitem__(self,k)
        except KeyError:
            l=[' ']*self.n
            self[k]=l
            if self.first is None:
                self.first=k
            return l
    def items(self):
        'return k,list pairs sorted by level of match to self.first'
        t=[]
        reference=self[self.first]
        for k,v in self.iteritems():
            i=0
            for j in range(self.n):
                if v[j]!=reference[j]:
                    i+=1
            t.append((i,k,v))
        t.sort()
        return [(k,v) for i,k,v in t]

def writeSeqToArray(start,offset,g,d,namedict,srcName=None):
    'write letters of seq interval g to list associated with its seq'
    if srcName is None:
        srcName=namedict[g] # <<<FIX THIS>>>
    a=d[srcName]
    i=g.start - start + offset
    s=str(g)
    for l in s: # WRITE LETTERS OF THIS SOURCE SEQ
        a[i]=l
        i += 1

def writeNumToArray(n,offset,a):
    'write digits of number n as label at position n in list'
    s=str(n)
    i=n-1-offset
    for l in s:
        try:
            a[i]=l
        except IndexError: return
    
        i += 1

def printHTML(d,ifile,blockStep=80):
    'print HTML view of alignment'
    reference=d[d.first]
    print >>ifile,'<HTML>\n<BODY><PRE>\n'
    start=0
    while start<len(reference):
        end=start+blockStep
        if end>len(reference):
            end=len(reference)
        print >>ifile,'Position               '[:15],''.join(d['#'][start:end])
        for name,s in d.items():
            l=[]
            for i in range(start,end):
                if s is reference or s[i]==' ' or s[i].upper()!=reference[i].upper():
                    l.append(s[i])
                else:
                    l.append('.')
            print >>ifile,(name+32*' ')[:15],''.join(l)
        print >>ifile,'\n'
        start += blockStep
       
    print >>ifile,'</PRE></BODY></HTML>'





def printSliceAlignment(myslice,ifile=None):
    '''print alignment of a gene as text, with numbering,
    seq differences in bold.  Suitable for viewing as .html file in a browser...'''
    from pygr import sequence
    if ifile is None:
        import sys
        ifile=sys.stdout
    d=Autodict(myslice.stop-myslice.start)
    namedict=~(myslice.nlmsaSequence.nlmsaLetters.seqDict)
    writeSeqToArray(myslice.start,0,sequence.absoluteSlice(myslice.seq,myslice.start,
                                                           myslice.stop),d,namedict)
    numline=d['#']
    i=(myslice.start+19) - ((myslice.start+19) % 20)
    while i<myslice.stop:
        writeNumToArray(i,myslice.start,numline)
        i+=20
    for srcPath,destPath,t in myslice.edges():
        writeSeqToArray(destPath.start,srcPath.start - myslice.start,destPath,d,
                        namedict)

    printHTML(d,ifile,100)




