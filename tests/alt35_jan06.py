from lldb_jan06 import *
from pygr.seqdb import *

def printResults(prefix,orient,msa,site,altID=None,cluster_id=None,dbUnion=None):
    edges=msa[site].edges(mergeMost=True)
    for src,dest,e in edges:
        if len(str(src)[:2]) < 2 or len(str(dest)[:2]) < 2: continue
        print '%s\t%s\t%s\t%s\t%2.1f\t%2.1f\t%s\t%s' \
              %(altID,cluster_id,prefix,dbUnion.dicts[dest.pathForward.db],
                100.*e.pIdentity(),100.*e.pAligned(),str(src)[:2].upper(),str(dest)[:2].upper())

def getSSMap(msa,gene,ss1,ss2,ss3,e1,e2,**kwargs):
    zone=e1+ss3 # LET CACHE KNOW WE NEED ALL ALIGNMENTS OF zone
    try:
        printResults('ss1',gene.orientation,msa,ss1,**kwargs)
    except: pass
    try:
        printResults('ss2',gene.orientation,msa,ss2,**kwargs)
    except: pass
    try:
        printResults('ss3',gene.orientation,msa,ss3,**kwargs)
    except: pass
    try:
        printResults('e1',gene.orientation,msa,e1,**kwargs)
    except: pass
    try:
        printResults('e2',gene.orientation,msa,e2,**kwargs)
    except: pass

from pygr.mapping import listUnion

def getAlt5Conservation2(msa,gene,start1,start2,stop,**kwargs):
    ss1=gene[start1-2:start1]
    ss2=gene[start2-2:start2]
    ss3=gene[stop:stop+2]
    e1=ss1+ss2 # GET INTERVAL BETWEEN PAIR OF SPLICE SITES
    e2=gene[max(start1,start2):stop]
    getSSMap(msa,gene,ss1,ss2,ss3,e1,e2,**kwargs)

def getAlt3Conservation2(msa,gene,start,stop1,stop2,**kwargs):
    ss1=gene[stop1:stop1+2]
    ss2=gene[stop2:stop2+2]
    ss3=gene[start-2:start]
    e1=ss1+ss2 # GET INTERVAL BETWEEN PAIR OF SPLICE SITES
    e2=gene[start:min(stop1,stop2)]
    getSSMap(msa,gene,ss1,ss2,ss3,e1,e2,**kwargs)

def splice_genomic_jan06(hg17):
    cursor=getUserCursor('SPLICE_JAN06')
    t=SQLTable('splice_genomic_hg17',cursor)
    # leftOffset for 1-based convention. leftOffset move left direction, rightOffset move right direction
    return SliceDB(t,hg17,leftOffset=1) # APPLY SLICES OF t TO SEQUENCES OF hg17

import sys, os, string

args = sys.argv
if len(args) != 3:
    print 'Usage:', args[0], 'inputtxt [5/3]'
    sys.exit()

from pygr import seqdb

hg17 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/hg17')
mm7 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/mm7')
rn3 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/rn3')
dr3 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/dr3')
bt2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/bt2')
cf2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/cf2')
gg2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/gg2')
fr1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/fr1')
xt1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/xt1')
oc1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/oc1')
pt1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/pt1')
rm1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/rm1')
rm2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/rm2')
dn1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/dn1')
la1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/la1')
et1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/et1')
tn1 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/tn1')
md2 = seqdb.BlastDB('/Volumes/LaCie2/deepreds/md2')

genomes={'hg17':hg17,'mm7':mm7, 'rn3':rn3, 'canFam2':cf2, 'danRer3':dr3, 'fr1':fr1,'galGal2':gg2, \
         'panTro1':pt1, 'bosTau2':bt2, 'xenTro1':xt1, 'oryCun1':oc1, 'rheMac2':rm2, 'dasNov1':dn1, \
         'loxAfr1':la1, 'echTel1':et1, 'monDom2':md2, 'tetNig1':tn1, 'rheMac1':rm1}
genomeUnion=seqdb.PrefixUnionDict(genomes)

cluster_id = args[1]

from pygr import cnestedlist
CHRDB=cnestedlist.NLMSA('/Volumes/LaCie2/deepreds/hg17_msa','r',seqDict=genomeUnion)

genomic_seq=splice_genomic_jan06(genomeUnion.prefixDict['hg17'])

for lines in open(args[1], 'r').xreadlines():
    if args[2] == '5':
        altid, cluster_id, exid, ex1start, exid, ex2start, exend, spid, spid, spstart = lines.split()
        gene=genomic_seq[cluster_id]
        getAlt5Conservation2(CHRDB, gene, int(ex1start)-1, int(ex2start)-1, int(exend), \
            cluster_id=cluster_id,altID=altid, dbUnion=genomeUnion)
    if args[2] == '3':
        altid, cluster_id, ex_start, exid, ex1end, exid, ex2end, spid, spid, spend = lines.split()
        gene=genomic_seq[cluster_id]
        getAlt3Conservation2(CHRDB, gene, int(ex_start)-1, int(ex1end), int(ex2end), \
            cluster_id=cluster_id,altID=altid, dbUnion=genomeUnion)

