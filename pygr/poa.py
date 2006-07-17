
from __future__ import generators
import types
from mapping import *
from sequence import *
from nestedlist import *



        
class AlignmentSummary(object):
    "combine one or more interval alignments for a pair of sequences, to calc %id etc."
    def __init__(self,e):
        #print 'creating AlignmentSummary for %s:%s' % (e.srcPath.path.id,e.destPath.path.id)
        self.srcMin=e.srcPath.start
        self.srcMax=e.srcPath.stop
        self.destMin=e.destPath.start
        self.destMax=e.destPath.stop
        self.edges=[e]
        self.srcPath=e.srcPath.path
        self.destPath=e.destPath.path
    def __iadd__(self,e):
        "add another alignment interval edge"
        if e.srcPath.start<self.srcMin:
            self.srcMin=e.srcPath.start
        if e.srcPath.stop>self.srcMax:
            self.srcMax=e.srcPath.stop
        if e.destPath.start<self.destMin:
            self.destMin=e.destPath.start
        if e.destPath.stop>self.destMax:
            self.destMax=e.destPath.stop
        self.edges.append(e)
        return self

    def percent_id(self,minLength=0):
        "calculate fractional identity for this pairwise alignment"
        nid=0
        for e in self.edges:
            nid+=e.nidentity()
        srcLen=self.srcMax-self.srcMin
        destLen=self.destMax-self.destMin
        if srcLen>minLength:
            minLength=srcLen
        if destLen>minLength:
            minLength=destLen
        return nid/float(minLength)



def clipUnalignedRegions(p):
    """p[-1] is the intersection of all alignment constraints,
       so reverse map it to find the actual aligned regions."""
    l=len(p)
    i=1
    while i<l:
        p[-i-1]=p.edge[-i].reverse(p[-i])
        i += 1


class Path2PathMap(object):
    "Temporary object provides iterator for TempIntervalDict.__getitem__"
    def __init__(self,pathDict,p,targetPath,pleaseReverse=False):
        self.pathDict=pathDict
        self.p=p
        self.targetPath=targetPath
        self.pleaseReverse=pleaseReverse

    def __iter__(self):
        for (srcPath,destList) in self.pathDict.findIntervals(self.p):
            i=0
            for destPath in destList:
                d=self.targetPath*destPath
                if d!=None: # PASSES TARGET CONSTRAINT
                    xform=IntervalTransform(srcPath,destPath,destList,'edge',i)
                    d2=d*xform[self.p]
                    if d2 is not None: # PASSES BOTH SOURCE AND TARGET CONSTRAINTS
                        if self.pleaseReverse:
                            d2 = -d2
                        s2=xform.reverse(d2)
                        xform=IntervalTransform(s2,d2,destList,'edge',i)
                        yield xform # RETURN XFORM AS EDGE-INFORMATION
                i += 1
        
class TempIntervalDict(object):
    "Temporary object acts as second layer dictionary for graph interface"
    def __init__(self,pathDict,p,pleaseReverse=False):
        self.pathDict=pathDict
        self.p=p
        self.pleaseReverse=pleaseReverse

    def __iter__(self):
        "Get all intervals aligned with self.p"
        for (srcPath,destList) in self.pathDict.findIntervals(self.p):
            for destPath in destList:
                yield self.pathDict.xform(self.p,srcPath,destPath,self.pleaseReverse)

    def items(self,getItems=True):
        "Get both target intervals and edge information (transforms)"
        for (srcPath,destList) in self.pathDict.findIntervals(self.p):
            i=0
            for destPath in destList:
                xform=IntervalTransform(srcPath,destPath,destList,'edge',i)
                s=self.p * srcPath # FIND ALIGNED PART OF OUR INTERVAL
                if self.pleaseReverse:
                    s = -s
                d=xform(s) # MAP TO THE TARGET SEQUENCE
                xform=IntervalTransform(s,d,destList,'edge',i)
                i += 1
                if getItems==True: # RETURN TARGET INTERVAL AND EDGE INFO
                    yield d,xform
                else: # JUST RETURN EDGE INFO
                    yield xform
    def edges(self):
        "Get edges for this source interval to all its target intervals"
        return self.items(False)

    def seq_dict(self):
        "make a dict of {seq:AlignmentSummary}"
        d={}
        for e in self.edges():
            try:
                d[e.destPath.path]+=e
            except KeyError:
                d[e.destPath.path]=AlignmentSummary(e)
        return d

    def __contains__(self,k):
        if not hasattr(self,'_map'): # TRY TO SPEED UP MULTIPLE MEMBERSHIP TESTS
            self._map={} # FIRST TIME, BUILD AN INDEX OF TARGET INTERVALS
            for i in self:
                self._map[i]=None
        return k in self._map

    def __getitem__(self,targetPath):
        "Get interval mapping(s) to a given target interval, as coord xforms"
        return Path2PathMap(self.pathDict,self.p,targetPath,self.pleaseReverse)
    
    def __setitem__(self,k,val):
        "Save both an aligned interval and edge information"
        self.pathDict.ivals.newEdge(self.p,k,val)
        
    def __repr__(self):
        s=''
        for i in self:
            s+='%s ' % repr(i)
        return s



class PathDict(object):
    _containsListClass=NestedList
    def __init__(self,g,s):
        self.graph=g
        self.path=s
        self.ivals=self._containsListClass()
        self.ready=False

    def findIntervals(self,p):
        self.update() # MAKE SURE CONTAINS-LIST PROPERLY SORTED
        return self.ivals.findIntervals(p)

    def update(self): # BUILD SORTED CONTAINS-LIST
        if not self.ready: # NO NEED TO UPDATE
            self.ivals=self.ivals.rebuild()
            self.ready=True # DONE WITH UPDATE, CAN USE THIS NOW

    def walk(self,getItems=None):
        return self.ivals.walk(getItems)

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

    def xform(self,p,srcPath,destPath=None,pleaseReverse=False):
        intersection= p*srcPath # FIND INTERSECTION
        if pleaseReverse:
            intersection= -intersection
        if destPath is None: # FOR INTERSECTION OF PathSet...
            return intersection
        else: # FOR PathMapping...
            xform=IntervalTransform(srcPath,destPath) # TRANSFORM TO TARGET
            return xform(intersection) # PATH COORDINATES

    def __getitem__(self,p): # FIND INTERVAL p IN SORTED CONTAINS-LIST
        # IF HITS GIVE MAPPING, RETURN MAPPING.
        # OTHERWISE JUST RETURN THE HITS THEMSELVES
        if self.path is p.path:
            return TempIntervalDict(self,p) # PROVIDES DICT-LIKE INTERFACE TO MAPPED INTERVALS
        try:
            if p.path._reverse is self.path: # SWITCH ORI TO MATCH self.path
                return TempIntervalDict(self,-p,True) # BUT MAKE IT REVERSE RESULT
        except AttributeError: pass
        raise KeyError('Path not in this PathDict!')


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



GET_EDGE_INFO= 2 # CONSTANT FOR PASSING TO VARIOUS getItems ARGUMENTS
# MEANS: GET EDGE INFORMATION AS TRANSFORM FROM ONE INTERVAL TO ANOTHER


# REPRESENTS A SET OF PATHS OR AN ALIGNMENT OF PATHS
# NEED TO ADD SUPPORT FOR INTERNAL PATH THAT ACTS AS HUB FOR MSA
class PathMapping(object):
    _pathDictClass=PathDict
    def __init__(self):
        self.pathDict={}
        
    def __getitem__(self,p):
        try:
            return self.pathDict[p.pathForward][p]
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

    def itervalues(self,getItems=False):
        "Get all values, items or edgeInfo for this mapping"
        for s in self.pathDict.values():
            s.update()
            for ivals in s.walk(getItems=getItems):
                if getItems:
                    j=0
                    for i in ivals[1]:
                        if getItems==GET_EDGE_INFO: #RETURN XFORM
                            yield IntervalTransform(ivals[0],i,
                                                    ivals[1],'edge',j)
                            j += 1
                        else: # RETURN PAIR OF ALIGNED INTERVALS
                            yield ivals[0],i
                else: # JUST RETURN TARGET INTERVAL
                    for i in ivals:
                        yield i

    def iteritems(self):
        "Get all pairs of aligned intervals for this mapping"
        return self.itervalues(getItems=True)
    def edges(self):
        "Get all edges representing aligned intervals in this mapping"
        return self.itervalues(getItems=GET_EDGE_INFO)
    __iter__=walk
    iterkeys=walk
    keys=walk
    values=itervalues
    items=iteritems

    def repr_dict(self):
        "Generate compact dict representation of this mapping"
        for e in self.edges():
            yield e.repr_dict()

    def seq_dict(self):
        "make a 2-level dict of {seq:{seq:AlignmentSummary}}"
        d={}
        for e in self.edges():
            if e.srcPath.path not in d:
                d[e.srcPath.path]={}
            try:
                d[e.srcPath.path][e.destPath.path]+=e
            except KeyError:
                as=AlignmentSummary(e)
                #print 'assigning to seq_dict:',e.srcPath.path.id,e.destPath.path.id,as
                d[e.srcPath.path][e.destPath.path]=as
        #print 'seq_dict is',d
        return d

class PathMapping2(PathMapping): # STORES BIDIRECTIONAL INDEX
    def __setitem__(self,p,val):
        self.savePath(p,val)
        if isinstance(val,SeqPath):
            self.savePath(val,p)

    
