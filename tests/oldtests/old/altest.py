
from pygr.poa import *

# CREATE A FEW SEQUENCES TO PLAY WITH...
s=Sequence('ABCDEFGHIJKLMNOPQRSTUVWXYZ','alpha')
s2=Sequence('01234567890123456789','number')
s3=Sequence('ATGCGGCCATATATGGCAGACGATAG','foo')

orf=s3[0:15:3]  # EXTENDED SLICE NOTATION MEANS start:stop:stepsize
print orf,orf.start,orf.stop
for codon in orf[1:3]: # PRINT 1ST THREE CODONS OF orf
    print codon.start,str(codon)
## codon=orf[0] # GET THE 1ST CODON IN orf
## while True: # LOOP OVER ALL CODONS IN orf
##     print codon.start,codon.end,codon.step,str(codon)
##     codon=firstItem(codon.next) # next IS DICTIONARY OF NODES WE ARE LINKED TO
##     if codon==None: # REACHED END OF THE PATH...
##         break


al=PathQueryPathMapping() # CONSTRUCT A FUNKY LITTLE PAIR OF ALIGNMENTS
al[s[:13]]=s2[:13]
al[s[18:25]]=s2[13:20]
al2=PathQueryPathMapping()
al2[s2[0:5]]=s3[0:5]
al2[s2[5:10]]=s3[7:12]
al2[s2[10:15]]=s3[14:19]
al2[s2[15:20]]=s3[21:26]

print 'Now trying path-based join...'
for i in al>>al2:
    print repr(i[0]),repr(i[1]),repr(i[2])

class foo(object):
    pass
edge=foo()
edge.blastScore=27

al=PathMapping()
al += s # PREPARE FOR ADDING EDGES FROM s
al[s[:10]][s2[10:20]]=edge
for i in al[s][s2]: # get all the edges from s -> s2
    print 'blastScore:',repr(i.srcPath),repr(i.destPath),i.blastScore

iv=s[0:10] # SLICE OF SEQUENCE IS PATH
iv2=s2[7:17]
iv2b=s2[10:20]
iv3=s3[1:11]
iva=s[7:20]

# FIND INTERSECTION OF TWO PATH SETS
m=PathMapping() # CREATE A NEW, EMPTY ALIGNMENT CONTAINER
m[iv]=None # JUST GIVE THE INTERVAL -- NOT ACTUALLY ALIGNED TO ANYTHING
ma=PathMapping() # CREATE ANOTHER CONTAINER, USE IT TO STORE A SET OF PATHS
ma[iva]=None # JUST STORE A SINGLE INTERVAL IN THIS CONTAINER...
join=m*ma # OK, FIND THE INTERSECTION OF THE TWO PATH SETS

print 'Intersection:'
for ival in join:
    print ival


# TEST A SIMPLE JOIN OF TWO ALIGNMENTS
#al=PathMappingBTree()
al=PathMapping2()  # THIS STORES ALIGNMENT AS BIDIRECTIONAL INDEX
al[iv]=iv2 # SO ORDER OF HOW YOU SPECIFY ALIGNMENT DOESNT MATTER

al2=PathMapping2()
al2[iv2b]=iv3 # SINCE ALIGNMENT'S BIDIRECTIONAL, CAN STORE IN EITHER ORDER

join=al*al2
print 'Alignment:'
for ival in join:
    print repr(ival),' --> ',join[ival]

al=PathMapping()  # SAME MAPPING TEST, BUT USING ONE-WAY ALIGNMENT INDEX
al[iv2]=iv # SO KEY MUST BE ON THE SAME SEQUENCE IN BOTH ALIGNMENTS!

al2=PathMapping()
al2[iv2b]=iv3 # NB: KEYED ON s2 JUST LIKE al ABOVE!!

join=al*al2
print 'Alignment (1-way):'
for ival in join:
    print repr(ival),' --> ',join[ival]


al2=PathMapping() # TRY ALIGNMENT WITH REVERSED ORIENTATION
al2[iv2b]= -iv3 # -iv3 MEANS iv3 IN REVERSED ORIENTATION (I.E. REV-COMP STRAND)

join=al*al2
print 'Alignment: (reversed orientation)'
for ival in join:
    print repr(ival),' --> (', join[ival],')'


#pd=PathDictBTree(None,s)
pd=PathDict(None,s)  # TEST HOW OVERLAPPING INTERVALS GET STORED IN PathDict
ivb=s[2:3]
ivc=s[8:10]
pd[ivc]=None
pd[ivb]=None
pd[iv]=None
pd[iva]=None
ivb=s[1:4]
pd[ivb]=None
print 'walk-list:',pd.ivals
for i in pd.walk():
    print i
pd.update()
print 'contains-list:',pd.ivals
for i in pd.iterkeys():
    print i
#for i in pd.ivals.keys():
#    print 'key',i




# DO A TEST ON ALISSA'S ISOFORM TO SWISSPROT FEATURES DATASET
fp=open('best_hits_B.tmp','r') # READ ALIGNMENT OF ISOFORMS TO SWISSPROT
mRNA_swiss=PathQueryPathMapping()
swiss_mRNA=PathMapping()
n1=0
for line in fp:
    l=line.split()
    i1=SeqPath(l[0],int(l[2]),int(l[3])+1)
    i2=SeqPath(l[1],int(l[4]),int(l[5])+1)
    mRNA_swiss[i1]=i2 # SAVE THIS IN OUR ALIGNMENT
    swiss_mRNA[i2]=i1
    n1+=1
fp.close()

fp=open('annotations_B.tmp','r') # READ ALIGNMENT OF SWISSPROT TO FEATURES
swiss_features=PathQueryPathMapping()
n2=0
for line in fp:
    l=line.split()
    i1=SeqPath(l[1],int(l[2])-1,int(l[3]))
    i2=SeqPath(l[5],0,int(l[3])-int(l[2])+1)
    swiss_features[i1]=i2 # SAVE THIS IN OUR ALIGNMENT
    n2+=1
fp.close()

import time
t=time.time()
join=swiss_mRNA*swiss_features # JOIN THE TWO ALIGNMENTS
print 'join time=',time.time()-t,'for %d x %d elements' % (n1,n2)
n=0
for i in join.itervalues():
    for j in i:
        n+=1
print 'join has %d elements' % n


for k in join:
    print repr(k),'aligned to',join[k]
    break

join=mRNA_swiss >> swiss_features # JOIN THE TWO ALIGNMENTS
t=time.time()
l=[i for i in join]
print 'pathquery join time=',time.time()-t
print 'join has %d elements' % len(l)

from pygr.graphquery import *
myjoin={1:{2:None},2:{3:DD(dataGraph=swiss_features)},3:{}}
t=time.time()
i=0
for d in GraphQuery(mRNA_swiss,myjoin):
    i+=1
print 'graphquery join time=',time.time()-t
print 'join has %d elements' % i

