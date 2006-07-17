from __future__ import generators
import types
from mapping import *

class NestedList(list):
    """Data structure for storing intervals (with alignments) as nested
       lists.  The intervals in each list are sorted in ascending order.
       Each interval is represented by a 3-tuple: (ival,clist,alignments),
       where ival is the interval itself, clist is the NestedList containing
       intervals whose bounds are contained in ival, alignments is a list
       of intervals (in other sequences) that are aligned to ival.

       NB: since an interval could be contained within two or more overlapping
       intervals in a NestedList, in this case the choice of which
       parent interval it will be stored under in the tree is arbitrary."""
    def __init__(self,ilist=[],tupleList=None,saveDict=None):
        for i in ilist:
            if i in saveDict: # BUILD LIST OF INTERVALS CONTAINED IN THIS IVAL
                p_contains=NestedList(saveDict[i],tupleList,saveDict)
            else:
                p_contains=None
            self.saveNode(tupleList[i][0],p_contains,tupleList[i][1])

    def saveNode(self,p,p_contains,val):
        self.append((p,p_contains,val))
    def newNode(self,p,val):
        "SAVE AS TUPLE: interval,contains,mapped-to-interval"
        self.saveNode(p,None,[val])
    def newEdge(self,p,node,edge):
        "Store both a new node in graph, and edge information for it"
        self.saveNode(p,None,PathList((node,),(edge,)))

    def walk(self,getItems=None):
        "walk contains-list in sequence-contains order"
        for (p,p_contains,p_map) in self:
            if getItems==None: # iterkeys
                yield p
            elif getItems==False: # itervalues
                yield p_map
            else: # iteritems
                yield (p,p_map) # FIRST RETURN THIS INTERVAL
            if p_contains!=None and len(p_contains)>0:
                for p2 in p_contains.walk(getItems):
                    yield p2 # ALSO RETURN ALL INTERVALS CONTAINED IN IT

    def findSlice(self,pSeek,left=0,max=None):
        """generate the slice [i,j] of intervals in self that overlap pSeek,
           within the slice [left,max).  Generates indexes i,i+1,...j,
           so the first overlapping interval is self[i]."""
        if max is None:
            max=len(self)
        right=max # END OF SEARCH RANGE
        while left<right: # BINARY SEARCH FOR LEFTMOST INTERVAL THAT OVERLAPS pSeek
            mid=(left+right)/2
            p=self[mid][0]
            if p<pSeek and not p.overlaps(pSeek): # p<<pSeek, NO OVERLAP!
                left=mid+1 # NEW START OF SEARCH RANGE
            else:
                right=mid # NEW END OF SEARCH RANGE
        # right NOW POINTS TO FIRST INTERVAL THAT OVERLAPS pSeek, IF ANY
        while right<max and pSeek.overlaps(self[right][0]): # GENERATE ALL OVERLAPS
            yield right
            right+=1

    def findIntervals(self,p,left=0,max=None):
        "recursively generate all stored intervals that overlap p"
        for i in self.findSlice(p,left,max):
            (q,q_contains,q_map)=self[i] # EXTRACT THE TUPLE
            yield (q,q_map) # THIS INTERVAL OVERLAPS p
            if q_contains!=None and len(q_contains)>0:
                for p2 in q_contains.findIntervals(p):
                    yield p2 # RETURN HITS TO INTERVALS CONTAINED IN IT

    def mergeIntervals(self): # MERGES IDENTICAL INTERVALS INTO ONE ENTRY
        "utility function for rebuilding data structure in correct sorted order"
        leftSort=[]
        leftMap=[]
        i=0
        for (p,p_map) in self.walk(getItems=True):
            leftSort.append([p,i])
            leftMap.append(p_map)
            i+=1
        try:
            leftSort.sort()
        except:
            print leftSort
            raise
        for l in leftSort:
            i=l[1]
            l[1]=leftMap[i]
        i=0
        j=1
        l=len(leftSort)
        while j<l:
            if leftSort[i][0]==leftSort[j][0]: # IDENTICAL INTERVALS, SO MERGE
                leftSort[i][1].extend(leftSort[j][1]) # COPY j'S CONTENTS TO i
            else:
                i+=1
                if i<j:
                    leftSort[i]=leftSort[j]
            j+=1
        i+=1
        if i<l: # MERGED SOME INTERVALS, SO WE NEED TO COMPACT THE LIST
            del leftSort[i:]
        return leftSort

    def rebuild(self):
        "build a new NestedList in correct sorted order, and return it"
        leftSort=self.mergeIntervals() # SORT AND MERGE IDENTICAL INTERVALS
        rightSort=[(leftSort[i][0].stop,i) for i in range(len(leftSort))]
        rightSort.sort() # SORT BY INTERVAL end, FIND THOSE THAT SHIFT IN ORDER
        saveDict={}
        containDict={}
        for (i,j) in rightSort: # j IS INDEX OF THIS ENTRY IN leftSort
            k=j-1
            while k>=0 and k in containDict:
                k=containDict[k]
            containDict[j]=k
            if k>=0: # j IS CONTAINED IN INTERVAL k.  ADD TO ITS SUBLIST
                if k not in saveDict:
                    saveDict[k]=[]
                saveDict[k].append(j)
        # TOP LISTS INTERVALS NOT CONTAINED IN ANY OTHER INTERVAL
        toplist=[i for i in range(len(leftSort)) if containDict[i]<0]
        return NestedList(toplist,leftSort,saveDict)




class NestedSlice(object):
    """represents a slice of a nested list consisting of those intervals
       that overlap the initial interval p.
       Accelerates access to this slice by restricting the search to
       just this part of the nested list."""
    def __init__(self,mylist,p):
        self.nestedList=mylist
        self.ival=p
        self.subdict={}
        it=mylist.findSlice(p)
        try:
            i=it.next()
        except StopIteration:
            raise ValueError('NestedSlice is empty')
        self.start=i # START INDEX
        for i in it: # READ TO END OF LIST
            pass
        self.end=i+1 # END INDEX

    def subslice(self,i):
        "create subslice object if needed, or return from index"
        try:
            return self.subdict[i]
        except KeyError:
            self.subdict[i]=NestedSlice(self.nestedList[i][1],self.ival)
            return self.subdict[i]

    def findIntervals(self,p,left=0,max=None):
        "recursively generate all stored intervals that overlap p"
        if left<self.start:
            left=self.start
        if max is None:
            max=self.end
        for i in self.nestedList.findSlice(p,left,max):
            (q,q_contains,q_map)=self.nestedList[i] # EXTRACT THE TUPLE
            yield (q,q_map) # THIS INTERVAL OVERLAPS p
            if q_contains!=None and len(q_contains)>0:
                for p2 in self.subslice(i).findIntervals(p):
                    yield p2 # RETURN HITS TO INTERVALS CONTAINED IN IT

    def __iter__(self):
        return self.findIntervals(self.ival)


# THIS IS RIDICULOUS.
# WHY DOES list FORCE SO MUCH WORK JUST TO HANDLE ONE LITTLE OFFSET???
class OffsetList(list):
    """access a list with an offset translation.
       This allows a small list to be accessed using the same coordinate
       system as a very long list.
       WARNING: for the purposes of getting python slicing to work right,
       I was forced to make the length of this object behave like the length
       of the master list."""
    def __init__(self,offset,masterLength,*args):
        list.__init__(self,*args) # CALL THE LIST INITIALIZER WITH OPTIONAL DATA
        self.offset=offset
        self.masterLength=masterLength
    def applyOffset(self,k):
        "apply the desired offset properly to both integer and slice arguments"
        if isinstance(k,types.SliceType):
            (start,stop,step)=k.indices(self.masterLength)
            start-=self.offset
            stop-=self.offset
            if start<0 or stop>=list.__len__(self):
                raise IndexError('list index out of range')
            class GetSlice(object):
                def __getitem__(self,k):
                    return k
            return GetSlice()[start:stop:step]
        elif isinstance(k,types.IntType):
            if k<0: # HANDLE NEGATIVE INDICES
                k+=self.masterLength
            k-=self.offset
            if k<0 or k>=list.__len__(self):
                raise IndexError('list index out of range')
            return k
        else:
            raise IndexError('incorrect type used as list index')

    def __getitem__(self,k):
        return list.__getitem__(self,self.applyOffset(k))
    def __setitem__(self,k,val):
        list.__setitem__(self,self.applyOffset(k),val)
    def __len__(self): # THIS IS THE ONLY WAY TO GET SLICING TO WORK RIGHT
        return self.masterLength # COMPUTATION OF SLICE i,j DEPENDS ON IT!! GRR.
    def __getslice__(self,i,j): # TOO STOOPID FOR WORDS, WHY DO I HAVE TO DO THIS
        return self[i:j:1] # EXTENDED SLICING WILL FORCE IT TO USE __getitem__
    def __setslice__(self,i,j,val):
        self[i:j:1]=val

## class NestedRCMSA(dict):
##     """a[p.path][i] => j
##        where i is index in p.path, and j is index in target path"""
##     def __init__(self,mylist,p):
##         self.nestedList=mylist
##         self.ival=p
##         for ival,targets in mylist.findIntervals(p):
##             for tval in targets:
##                 try:
##                     l=self[tval.path]
##                 except KeyError:
##                     l=OffsetList(p.start,len(p.path),len(p)*[None])
##                     self[tval.path]=l
##                 xform=tval/ival # TRANSFORM FROM ival -> tval COORDINATES
##                 for ipos in ival:
##                     l[ipos.start]=xform.xform(ipos.start) # WRONG.  FIX THIS!!!

                    



class NestedIterator(object):
    """iterate over all positions in the specified interval.
       For each position, return iterator showing all target positions
       that it maps to.
       This needs to be implemented more efficiently.  Right now it is
       re-doing the binary search for each iteration.  Instead it should
       lazily update the contiguous group of NestedList entries that
       contain the current position."""
    def __init__(self,mylist,p):
        self.nestedSlice=NestedSlice(mylist,p)
        self.domain=p # INTERVAL WE'RE GOING TO ITERATE OVER
        self.pos=p[0:1] # FIRST LETTER OF DOMAIN INTERVAL

    def __iter__(self):
        return self

    def generateTargets(self,pos):
        "iterate over all target positions that pos maps to"
        for p,p_map in self.nestedSlice.findIntervals(pos):
            if pos in p:
                for target in p_map:
                    yield (target/p)[pos] # XFORM TO target COORDINATES

    def next(self):
        "return iterator mapping current position to all targets, or stop"
        if self.pos in self.domain:
            it=self.generateTargets(self.pos)
            self.pos += 1
            return it
        else: # OUT OF RANGE, HALT THE ITERATOR
            raise StopIteration
