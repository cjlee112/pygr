
from maftest import *

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

def writeSeqToArray(start,offset,g,d,srcName=None):
    'write letters of seq interval g to list associated with its seq'
    if srcName is None:
        srcName=genomeUnion.getName(g.path)
    a=d[srcName]
    i=g.start - start + offset
    s=str(g)
    for l in s: # WRITE LETTERS OF THIS SOURCE SEQ
        a[i]=l
        i += 1

def writeNumToArray(n,a):
    'write digits of number n as label at position n in list'
    s=str(n)
    i=n-1
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
                if s[i]==reference[i]:
                    l.append(s[i])
                else:
                    l.append('<B>%s</B>' % s[i])
            print >>ifile,(name+32*' ')[:15],''.join(l)
        print >>ifile,'\n'
        start += blockStep
       
    print >>ifile,'</PRE></BODY></HTML>'





def printClusterAlignment(cluster_id,msa,ifile=None):
    '''print alignment of a gene as text, with numbering,
    seq differences in bold.  Suitable for viewing as .txt file in a browser...'''
    if ifile is None:
        import sys
        ifile=sys.stdout
    c=clusters[cluster_id] # GET DATA FOR THIS CLUSTER ON chr22
    loadCluster(c,exons,splices,clusterExons,clusterSplices,spliceGraph,alt5Graph,alt3Graph)
    gene=genomic_seq[cluster_id]
    start=None
    stop=None
    for g in cm[gene]:  # GET BOUNDS
        if start is None or g.start<start:
            start=g.start
        if stop is None or g.stop>stop:
            stop=g.stop
    d=Autodict(stop-start)
    for ed0 in cm[gene].edges():  # GET GENE SEQUENCE
        g=ed0.destPath
        writeSeqToArray(start,0,g,d)
        numline=d['#']
        i=(ed0.srcPath.start+9) - ((ed0.srcPath.start+9) % 10)
        while i<ed0.srcPath.stop:
            writeNumToArray(i,numline)
            i+=10
        #maf=MAFStoredPathMapping(g,alTable,genomeUnion) # LOAD ALIGNMENT FROM THE DATABASE
        #for ed in maf.edges(): # PRINT THE ALIGNED SEQUENCES
        alignSlice=msa[g]
        for ival in alignSlice.keys(maxgap=10000,maxinsert=10000):
            str(ival) # CACHE THE SEQUENCE REGIONS WE'LL BE USING...
        for srcPath,destPath,t in alignSlice.edges():
            writeSeqToArray(destPath.start,srcPath.start - start,destPath,d)
##     for e in c.exons:  # MARK THE EXONS AS WELL...
##         for g in cm[e]:
##             writeSeqToArray(start,0,g,d,'Exons')


    printHTML(d,ifile,100)
##     print 'Position             '[:15],''.join(d['#'])
##     for name,l in d.items():
##         print (name+32*' ')[:15],''.join(l)



if __name__=='__main__':
    CHRDB=getNLMSA()
    printClusterAlignment('Hs.3080',CHRDB)
