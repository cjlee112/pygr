
import types
from mapping import *
from sequtil import *




class PathEdgeDict(dict):
    def __init__(self,p):
        self.path=p.path
        self.pos=p.end-1
        if p.end<len(p.path):
            dict.__setitem__(self,p.path[p.end],1)
        if hasattr(p.path,'_next') and self.pos in p.path._next:
            dict.update(self,p.path._next[self.pos])
    def __setitem__(self,k,val):
        print 'entered PathEdgeDict.setitem'
        if not hasattr(self.path,'_next'):
            self.path._next={}
        if self.pos not in self.path._next:
            self.path._next[self.pos]={}
        self.path._next[self.pos][k]=val
        dict.__setitem__(self,k,val)
        


class PathNextDescr(object):
    def __init__(self,attrName='next'):
        self.attrName=attrName

    def __get__(self,obj,objtype):
        return PathEdgeDict(obj)

    def __set__(self,obj,val):
        raise AttributeError(self.attrName+' is read-only!')


NOT_ON_SAME_PATH= -2

# BASE CLASS FOR SPECIFYING A PATH, IE. SEQUENCE INTERVAL.
# THIS IMPLEMENTATION TAKES A SEQUENCE AS INITIALIZER
# AND SIMPLY REPRESENTS THE INTERVAL AS A SLICE OF THE SEQUENCE.
class SeqPath(object):
    #next=PathNextDescr()
    def __init__(self,s,start=0,end=None,step=1,orientation=1):
        self.path=s
        if start and end and start>end: # DETECT REVERSED ORIENTATION
            self.orientation= -orientation
            t=start
            start=end+1 # ALWAYS STORE INTERVAL AS start <= end
            end=t+1 # +1 BECAUSE OF SLICE PROTOCOL ASSYMMETRY
        else:
            self.orientation= orientation
        self.start=start
        if end==None:
            self.end=len(s)
        else:
            self.end=end
        self.step=step

    def __getitem__(self,k):
        if isinstance(k,types.SliceType):
            (start,stop,step)=k.indices(self.end-self.start)
        elif isinstance(k,types.IntType):
            start=k
            stop=k+1
            step=1
        else:
            raise KeyError('requires a slice object or integer key')
        if self.step==1 and not hasattr(self,'_next') and self.orientation>0:
            return SeqPath(self.path,self.start+start*self.step,
                           self.start+stop*self.step,
                           self.step*step)
        else:
            return SeqPath(self,start,stop,step)

    def __len__(self):
        return (self.end-self.start)/self.step

    def generate(self):
        for i in range(len(self)):
            yield self[i]
    
    def __iter__(self):
        #return self.path[self.start:self.end:self.step].__iter__()
        return self.generate()

    def __cmp__(self,other):
        if not isinstance(other,SeqPath):
            return -1
        if id(self.path)==id(other.path) or \
               (isinstance(self.path,types.StringType) and
                isinstance(other.path,types.StringType) and
                self.path==other.path):
            return cmp((self.start,self.end),(other.start,other.end))
        else:
            return NOT_ON_SAME_PATH
            #raise TypeError('SeqPath not comparable, not on same path: %s,%s'
            #                % (self.path,other.path))
    
    def __contains__(self,k):
        # PUT OTHER LOGIC HERE FOR CHECKING WHETHER INTERVAL IS CONTAINED...
        if isinstance(k,SeqPath):
            if k.path==self.path and self.start<=k.start and k.end<=self.end:
                return True
            else:
                return False
        elif isinstance(k,types.IntType):
            return self.start<=k and k<self.end

    def overlaps(self,p): # CHECK WHETHER TWO PATHS ON SAME SEQ OVERLAP
        if self.path!=p.path:
            return False
        if (self.start<=p.start and p.start<self.end) or \
               (p.start<=self.start and self.start<p.end):
            return True
        else:
            return False

    def __mul__(self,other): # FIND INTERSECTION OF TWO INTERVALS
        if isinstance(other,SeqPath):
            if self.path!=other.path:
                return None
            start=max(self.start,other.start)
            end=min(self.end,other.end)
            if start<end:
                return SeqPath(self.path,start,end)
            else:
                return None
        else:
            raise TypeError('SeqPath can only intersect SeqPath')

    def __neg__(self): # RETURN SAME INTERVAL IN REVERSE ORIENTATION
        return SeqPath(self.path,self.start,self.end,self.step,
                       -self.orientation)

    def reverse_complement(self,s):
        compl={'a':'t', 'c':'g', 'g':'c', 't':'a', 'u':'a', 'n':'n',
               'A':'T', 'C':'G', 'G':'C', 'T':'A', 'U':'A', 'N':'N'}
        l=[compl[c] for c in s]
        l.reverse()
        return ''.join(l)

    def seqtype(self):
        "Get the sequence type for this sequence"
        obj=self
        while 1:
            if hasattr(obj,'_seqtype'):
                return obj._seqtype
            if obj.path!=obj:
                obj=obj.path
            else:
                break
        return guess_seqtype(str(self))

    def strslice(self,start,end):
        s=str(self)
        return s[start*self.step:end*self.step]

    def __str__(self):
        if isinstance(self.path,SeqPath):
            s=self.path.strslice(self.start,self.end)
            if self.orientation<0: # REVERSE ORI ONLY MAKES SENSE FOR DNA
                s=self.reverse_complement(s)
            return s
        else:
            s=str(self.path)
            if self.orientation<0: # REVERSE ORI ONLY MAKES SENSE FOR DNA
                s=self.reverse_complement(s)
            return s[self.start:self.end]
    def __repr__(self):
        if self.orientation<0: # INDICATE NEGATIVE ORIENTATION
            ori='-'
        else:
            ori=''
        if isinstance(self.path,types.StringType):
            return '%s%s[%d:%d]' % (ori,self.path,self.start,self.end)
        else:
            return '%s%s[%d:%d]' % (ori,self.path.id,self.start,self.end)


class LengthDescriptor(object):
    def __init__(self,attr):
        self.attr=attr
    def __get__(self,obj,objtype):
        return len(getattr(obj,self.attr))
    def __set__(self,obj,val):
        raise AttributeError(self.attr+' is read-only!')


# BASIC WRAPPER FOR A SEQUENCE.  LETS US ATTACH A NAME TO IT...
class NamedSequenceBase(SeqPath):
    start=0
    step=1
    orientation=1
    def __init__(self):
        self.path=self
        try: # USE ATTRIBUTE TO GET SEQ LENGTH DIRECTLY
            self.end=getattr(self,getattr(self,'_seq_len_attr'))
        except AttributeError:
            self.end=len(self.seq) # COMPUTE IT FROM THE SEQUENCE

    def strslice(self,start,end):
        return self.seq[start:end]


class NamedSequence(NamedSequenceBase):
    def __init__(self,s,id):
        self.id=id
        self.seq=s
        NamedSequenceBase.__init__(self)


def firstItem(aList):
    if hasattr(aList,'__iter__'):
        for i in aList:
            return i
    else:
        return aList


class IntervalTransform(object):
    "Represents coordinate transformation from one interval to another"
    def __init__(self,srcPath,destPath,edgeInfo=None):
        "MAP FROM srcPath -> destPath"
        ori=srcPath.orientation * destPath.orientation
        self.scale= ori * len(destPath)/float(len(srcPath))
        if ori>0: # MAP srcPath.start -> destPath.start
            self.offset=destPath.start-self.scale*srcPath.start
        else: # REVERSE ORI: MAP srcPath.start -> destPath.end-1
            self.offset=destPath.end-1-self.scale*srcPath.start
        self.srcPath=srcPath.path
        self.destPath=destPath.path
        if edgeInfo!=None:
            self.edgeInfo=edgeInfo

    def xform(self,i):
        "transform a single integer value"
        return int(self.scale*i+self.offset)
    def __call__(self,srcPath):
        "Apply this transformation to an interval"
        return SeqPath(self.destPath,self.xform(srcPath.start),\
                       self.xform(srcPath.end))
    def xformBack(self,i):
        "reverse transform a single integer value"
        scale=1.0/self.scale
        offset= -1.0*self.offset/self.scale
        return int(scale*i+offset)
    def reverse(self,destPath):
        "reverse transform an interval"
        return SeqPath(self.srcPath,self.xformBack(destPath.start),
                       self.xformBack(destPath.end))
    def __getitem__(self,srcPath): # PROVIDE DICT-LIKE INTERFACE
        return self(srcPath)
    def __iter__(self):
        yield self.srcPath
    def items(self):
        yield self.srcPath,self.destPath
    def __getattr__(self,attr):
        "provide transparent wrapper for edgeInfo attributes"
        try:
            return getattr(self.__dict__['edgeInfo'],attr)
        except (KeyError,AttributeError):
            raise AttributeError('%s does not have attribute %s'
                                 %(str(self),attr))

def clipUnalignedRegions(p):
    """p[-1] is the intersection of all alignment constraints,
       so reverse map it to find the actual aligned regions."""
    l=len(p)
    i=1
    while i<l:
        p[-i-1]=p.edge[-i].reverse(p[-i])
        i += 1


class ContainsList(list):
    def saveNode(self,p,p_contains,val):
        self.append((p,p_contains,val))
    def newNode(self,p,val):
        "SAVE AS TUPLE: interval,contains,mapped-to-interval"
        self.saveNode(p,None,[val])
    def newEdge(self,p,node,edge):
        "Store both a new node in graph, and edge information for it"
        self.saveNode(p,None,PathList((node,),(edge,)))


class TempIntervalList(object):
    "Temporary object provides iterator for TempIntervalDict.__getattr__"
    def __init__(self,pathDict,p,targetPath):
        self.pathDict=pathDict
        self.p=p
        self.targetPath=targetPath

    def __iter__(self):
        for (srcPath,destList) in self.pathDict.findIntervals(self.p):
            i=0
            for destPath in destList:
                d=self.targetPath*destPath
                if d!=None: # PASSES TARGET CONSTRAINT
                    if hasattr(destList,'edge'): # USE THE EDGE INFORMATION
                        xform=IntervalTransform(srcPath,destPath,destList.edge[i])
                    else: # NO EDGE INFORMATION TO BIND
                        xform=IntervalTransform(srcPath,destPath)
                    d2=d*xform(self.p * srcPath)
                    if d2!=None: # PASSES BOTH SOURCE AND TARGET CONSTRAINTS
                        s2=xform.reverse(d2)
                        xform.srcPath=s2 # SAVE ALIGNED INTERVALS
                        xform.destPath=d2
                        yield xform # RETURN XFORM AS EDGE-INFORMATION
                i += 1
        

class TempIntervalDict(object):
    "Temporary object acts as second layer dictionary for graph interface"
    def __init__(self,pathDict,p):
        self.pathDict=pathDict
        self.p=p

    def __iter__(self):
        "Get all intervals aligned with self.p"
        for (srcPath,destList) in self.pathDict.findIntervals(self.p):
            for destPath in destList:
                yield self.pathDict.xform(self.p,srcPath,destPath)

    def items(self):
        "Get both target intervals and edge information (transforms)"
        for (srcPath,destList) in self.pathDict.findIntervals(self.p):
            i=0
            for destPath in destList:
                if hasattr(destList,'edge'): # USE THE EDGE INFORMATION
                    xform=IntervalTransform(srcPath,destPath,destList.edge[i])
                else: # NO EDGE INFORMATION TO BIND
                    xform=IntervalTransform(srcPath,destPath)
                i += 1
                yield xform(self.p * srcPath),xform

    def __contains__(self,k):
        if not hasattr(self,'_map'): # TRY TO SPEED UP MULTIPLE MEMBERSHIP TESTS
            self._map={} # FIRST TIME, BUILD AN INDEX OF TARGET INTERVALS
            for i in self:
                self._map[i]=None
        return k in self._map

    def __getitem__(self,targetPath):
        "Get interval mapping(s) to a given target interval, as coord xforms"
        return TempIntervalList(self.pathDict,self.p,targetPath)
    
    def __setitem__(self,k,val):
        "Save both an aligned interval and edge information"
        self.pathDict.ivals.newEdge(self.p,k,val)
        
    def __repr__(self):
        s=''
        for i in self:
            s+='%s ' % repr(i)
        return s

    filter=newFilterPath
    __rshift__=newJoinPath



class PathDict(object):
    _containsListClass=ContainsList
    def __init__(self,g,s):
        self.graph=g
        self.path=s
        self.ivals=self._containsListClass()
        self.ready=False

    def buildList(self,ilist,tupleList,saveDict):
        myList=self._containsListClass()
        for i in ilist:
            if i in saveDict: # BUILD LIST OF INTERVALS CONTAINED IN THIS IVAL
                p_contains=self.buildList(saveDict[i],tupleList,saveDict)
            else:
                p_contains=None
            myList.saveNode(tupleList[i][0],p_contains,tupleList[i][1])
        return myList

    def mergeIntervals(self): # MERGES IDENTICAL INTERVALS INTO ONE ENTRY
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
                for k in leftSort[j][1]: # COPY j'S CONTENTS TO i
                    leftSort[i][1].append(k)
            else:
                i+=1
                if i<j:
                    leftSort[i]=leftSort[j]
            j+=1
        i+=1
        if i<l: # MERGED SOME INTERVALS, SO WE NEED TO COMPACT THE LIST
            del leftSort[i:]
        return leftSort

    def update(self): # BUILD SORTED CONTAINS-LIST
        if self.ready: # NO NEED TO UPDATE
            return
        leftSort=self.mergeIntervals() # SORT AND MERGE IDENTICAL INTERVALS
        rightSort=[(leftSort[i][0].end,i) for i in range(len(leftSort))]
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
        self.ivals=self.buildList(toplist,leftSort,saveDict)
        self.ready=True # DONE WITH UPDATE, CAN USE THIS NOW

    # WALK CONTAINS-LIST IN SEQUENCE-CONTAINS ORDER
    def walk(self,ivals=None,getItems=None): 
        if ivals==None:
            ivals=self.ivals
        for (p,p_contains,p_map) in ivals:
            if getItems==None: # iterkeys
                yield p
            elif getItems==True: # iteritems
                yield (p,p_map) # FIRST RETURN THIS INTERVAL
            else: # itervalues
                yield p_map
            if p_contains!=None and len(p_contains)>0:
                for p2 in self.walk(p_contains,getItems):
                    yield p2 # ALSO RETURN ALL INTERVALS CONTAINED IN IT

    def __iter__(self):
        self.update() # MAKE SURE CONTAINS-LIST PROPERLY SORTED
        return self.walk()
    def iterkeys(self):
        self.update() # MAKE SURE CONTAINS-LIST PROPERLY SORTED
        return self.walk()
    def itervalues(self):
        self.update() # MAKE SURE CONTAINS-LIST PROPERLY SORTED
        return self.walk(getItems=False)
    def iteritems(self):
        self.update() # MAKE SURE CONTAINS-LIST PROPERLY SORTED
        return self.walk(getItems=True)

    def generateSlice(self,i,ivals=None):
        if ivals==None:
            ivals=self.ivals
        l=len(ivals)
        #print 'generateSlice',i,l
        while i<l:
            yield ivals[i]
            i+=1

    def findInterval(self,pSeek,ivals=None):
        self.update() # MAKE SURE CONTAINS-LIST PROPERLY SORTED
        if ivals==None:
            ivals=self.ivals
        left=0
        right=len(ivals)
        visitDict={}
        foundMin=None
        while left<right:
            mid=(left+right)/2
            if mid in visitDict:
                break
            else:
                visitDict[mid]=1
            p=ivals[mid][0]
            if pSeek<p:
                right=mid
                if p.overlaps(pSeek) and (foundMin==None or mid<foundMin):
                    foundMin=mid
            else:
                left=mid
                if p.overlaps(pSeek) and (foundMin==None or mid<foundMin):
                    foundMin=mid
        if foundMin!=None:
            return self.generateSlice(foundMin,ivals)
        else:
            return ().__iter__()

    def findIntervals(self,p,ivals=None):
        if ivals==None:
            ivals=self.ivals
        for (q,q_contains,q_map) in self.findInterval(p,ivals):
            if p.overlaps(q):
                yield (q,q_map) # THIS INTERVAL OVERLAPS p
                if q_contains!=None and len(q_contains)>0:
                    for p2 in self.findIntervals(p,q_contains):
                        yield p2 # RETURN HITS TO INTERVALS CONTAINED IN IT
            else:
                break

    def xform(self,p,srcPath,destPath=None):
        intersection= p*srcPath # FIND INTERSECTION
        if destPath==None: # FOR INTERSECTION OF PathSet...
            return intersection
        else: # FOR PathMapping...
            xform=IntervalTransform(srcPath,destPath) # TRANSFORM TO TARGET
            return xform(intersection) # PATH COORDINATES

    def __getitem__(self,p): # FIND INTERVAL p IN SORTED CONTAINS-LIST
        # IF HITS GIVE MAPPING, RETURN MAPPING.
        # OTHERWISE JUST RETURN THE HITS THEMSELVES
        if self.path!=p.path:
            raise KeyError('Path not in this PathDict!')
        return TempIntervalDict(self,p) # PROVIDES DICT-LIKE INTERFACE TO MAPPED INTERVALS


    def __setitem__(self,p,val):
        # IF val IS AN INTERVAL, SAVE THIS AS A MAPPING.
        # OTHERWISE JUST SAVE THE INTERVAL p TO OUR LIST
        # APPEND A COPY OF p TO OUR ivals, AND MARK ready AS FALSE.
        self.ivals.newNode(p,val)
        self.ready=False # FORCE AN UPDATE NEXT TIME LIST IS READ

    def append(self,p): # CONVENIENCE METHOD FOR LIST-LIKE INTERFACE
        self[p]=None

    def __contains__(self,p): # CHECK FOR OVERLAP OF p VS STORED INTERVALS
        for (srcPath,destPath) in self.findIntervals(p):
            return True
        return False

    def joinPair(self,p,p_map,o,o_map): # RETURN APPROPRIATE RESULT FOR
        src=self.xform(o,p,p_map) # INTERSECTING TWO OVERLAPPING INTERVALS
        if p_map==None and o_map==None: # JUST THE INTERSECTION ITSELF
            return (src,None)
        dest=self.xform(p,o,o_map)
        if o_map==None:
            return (dest,src)
        else:
            return (src,dest)

    def intersect(self,other,result=None):
        if self.path!=other.path:
            raise KeyError('Path not in this PathDict!')
        if isinstance(other,SeqPath):
            return self[other]
        if isinstance(other,PathDict): # WALK BOTH IN ORDER
            if result==None:
                result=PathMapping(self.graph)
            p_iter=self.iteritems() # GET ITERATORS FOR self AND other
            o_iter=other.iteritems()
            overlapQueue=[] # LIST OF ALL p THAT OVERLAP o
            pNotDone=True # KEEP TRYING TO READ p UNTIL NO MORE...
            
            def getNextP(plist,p0,p1): # TRAP THE EXCEPTION PROPERLY
                try: # GET A NEW INTERVAL FROM ITERATOR
                    (p,p_map)=plist.next()
                    return (p,p_map,True) # STILL MORE p TO READ...
                except StopIteration: # NO MORE, SO HAND BACK SIGNAL
                    return (p0,p1,False)
                
            try:
                (o,o_map)=o_iter.next()
                (p,p_map)=p_iter.next()
                while pNotDone or o<p or p.overlaps(o):
                    # LINEAR SCAN OVER BOTH PathDicts
                    # SKIP PAST REGIONS OF NO OVERLAP
                    while pNotDone and p<o and not p.overlaps(o):
                        (p,p_map,pNotDone)=getNextP(p_iter,p,p_map)
                    while o<p and not o.overlaps(p):
                        (o,o_map)=o_iter.next()
                    while True: # PROCESS THIS BLOCK OF OVERLAP, IF ANY
                        i=0
                        while i<len(overlapQueue):
                            if overlapQueue[i][0]<o and \
                                   not o.overlaps(overlapQueue[i][0]):
                                overlapQueue.pop(i) # SKIP PAST NON-OVERLAPPING
                            else:
                                i+=1
                        while pNotDone and p.overlaps(o):
                            overlapQueue.append((p,p_map))
                            (p,p_map,pNotDone)=getNextP(p_iter,p,p_map)
                        if len(overlapQueue)==0:
                            break
                        for x in overlapQueue: # PROCESS ALL x VS. o
                            if o.overlaps(x[0]):
                                for xmap in x[1]:
                                    for ymap in o_map:
                                        (src,dest)=self.joinPair(x[0],xmap,o,ymap)
                                        result[src]=dest # SAVE NEW MAPPING
                        (o,o_map)=o_iter.next() # ADVANCE TO NEXT o
                return result
            except StopIteration: # NO MORE o, SO JUST RETURN THE RESULT
                return result
        raise TypeError('dont know how to do this intersection')

    def __mul__(self,other):
        return self.intersect(other)



class AlignPathGraph(GraphPathGraph):
    def __iter__(self):
        "Wrapper around GraphPathGraph iterator, designed for alignments"
        for i in GraphPathGraph.__iter__(self):
            clipUnalignedRegions(i) # RESTRICT TO ACTUAL REGION OF ALIGNMENT
            yield i


# REPRESENTS A SET OF PATHS OR AN ALIGNMENT OF PATHS
# NEED TO ADD SUPPORT FOR INTERNAL PATH THAT ACTS AS HUB FOR MSA
class PathMapping(object):
    _pathDictClass=PathDict
    def __init__(self):
        self.pathDict={}
        
    def __getitem__(self,p):
        try:
            return self.pathDict[p.path][p]
        except KeyError:
            raise KeyError('%s not in %s' % (repr(p),self))

    def savePath(self,p,val):
        if p.path not in self.pathDict: # CREATE A NEW PATH DICT IF NEEDED
            self.pathDict[p.path]=self._pathDictClass(self,p.path)
        self.pathDict[p.path][p]=val # SAVE IN PathDict

    def __setitem__(self,p,val):
        self.savePath(p,val)

    def __iadd__(self,p):
        """Make sure sequence p has an entry in this top level dict, so
           second-layer setitem will work..."""
        if isinstance(p,SeqPath):
            if p.path not in self.pathDict: # CREATE A NEW PATH DICT IF NEEDED
                self.pathDict[p.path]=self._pathDictClass(self,p.path)
            return self
        else:
            raise TypeError('Cannot add object of this type')
            

    def __mul__(self,other): # PERFORMS INTERSECTION OF PATHS
        if isinstance(other,SeqPath):
            if other.path in self.pathDict:
                return other*self.pathDict[other.path]
            else:
                return None
        elif isinstance(other,PathMapping): # INTERSECT THE TWO MAPPINGS
            result=PathMapping()
            for (s,pd) in self.pathDict.items():
                if s in other.pathDict:
                    pd.intersect(other.pathDict[s],result)
            return result

    def walk(self,getItems=None):
        for s in self.pathDict.values():
            s.update()
            for ival in s.walk(getItems=getItems):
                yield ival

    def __iter__(self):
        return self.walk()
    def iterkeys(self):
        return self.walk()
    def itervalues(self):
        return self.walk(getItems=False)
    def iteritems(self):
        return self.walk(getItems=True)
    filter=newFilterPath
    def __rshift__(self,graph):
        q=AlignPathGraph(self,self)
        return q >> graph

class PathMapping2(PathMapping): # STORES BIDIRECTIONAL INDEX
    def __setitem__(self,p,val):
        self.savePath(p,val)
        if isinstance(val,SeqPath):
            self.savePath(val,p)

    
