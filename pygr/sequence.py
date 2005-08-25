
import types
from sequtil import *


NOT_ON_SAME_PATH= -2

class IntervalTransform(object):
    "Represents coordinate transformation from one interval to another"
    def __init__(self,srcPath,destPath,edgeInfo=None,
                 edgeAttr=None,edgeIndex=None):
        "MAP FROM srcPath -> destPath"
        ori=srcPath.orientation * destPath.orientation
        self.scale= ori * len(destPath)/float(len(srcPath))
        if ori>0: # MAP srcPath.start -> destPath.start
            self.offset=destPath.start-self.scale*srcPath.start
        else: # REVERSE ORI: MAP srcPath.start -> destPath.end-1
            self.offset=destPath.end-1-self.scale*srcPath.start
        self.srcPath=srcPath
        self.destPath=destPath
        if edgeInfo!=None and edgeAttr!=None:
            try: # GET EDGE INFO IF PRESENT
                edgeInfo=getattr(edgeInfo,edgeAttr)
            except AttributeError:
                edgeInfo=None
        if edgeInfo!=None:
            if edgeIndex!=None:
                edgeInfo=edgeInfo[edgeIndex]
            self.edgeInfo=edgeInfo

    def xform(self,i):
        "transform a single integer value"
        return int(self.scale*i+self.offset)
    def __call__(self,srcPath):
        """Apply this transformation to an interval
           NB: it is not restricted to the domain of this transform,
           and thus can extend BEYOND the boundaries of this transform.
           If you want it clipped use xform[] interface instead of xform()."""
        return SeqPath(self.destPath.path,self.xform(srcPath.start),\
                       self.xform(srcPath.end))
    def xformBack(self,i):
        "reverse transform a single integer value"
        scale=1.0/self.scale
        offset= -1.0*self.offset/self.scale
        return int(scale*i+offset)
    def reverse(self,destPath):
        "reverse transform an interval"
        return SeqPath(self.srcPath.path,self.xformBack(destPath.start),
                       self.xformBack(destPath.end))
    def __getitem__(self,srcPath): # PROVIDE DICT-LIKE INTERFACE
        """intersect srcPath with domain of this transform, then return
        transform to target domain coordinates"""
        return self(srcPath*self.srcPath)
    def __iter__(self):
        yield self.srcPath
    def items(self):
        yield self.srcPath,self.destPath
    def __getattr__(self,attr):
        "provide transparent wrapper for edgeInfo attributes"
        return getattr(self.edgeInfo,attr) # RAISE EXCEPTION IF NOT FOUND!

    def repr_dict(self):
        s=self.srcPath.repr_dict() # GET REPR OF BOTH INTERVALS
        d=self.destPath.repr_dict()
        out={}
        for k,val in s.items(): # ADD PREFIX TO EACH ATTR
            out['src_'+k]=val
            out['dest_'+k]=d[k]
        try: e=self.edgeInfo.repr_dict() # GET EDGE INFO IF PRESENT
        except AttributeError: pass
        else: out.update(e) # SAVE EDGE INFO DATA
        return out

    def nidentity(self):
        "calculate total #identity matches between srcPath and destPath"
        nid=0
        src=str(self.srcPath).upper()
        dest=str(self.destPath).upper()
        slen=len(src)
        i=0
        while i<slen:
            if src[i]==dest[i]:
                nid+=1
            i+=1
        return nid




# BASE CLASS FOR SPECIFYING A PATH, IE. SEQUENCE INTERVAL.
# THIS IMPLEMENTATION TAKES A SEQUENCE AS INITIALIZER
# AND SIMPLY REPRESENTS THE INTERVAL AS A SLICE OF THE SEQUENCE.
class SeqPath(object):
    #next=PathNextDescr()
    def __init__(self,s,start=0,end=None,step=1,orientation=1):
        self.path=s
        if start and end!=None and start>end: # DETECT REVERSED ORIENTATION
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
            if(k==-1):
                stop=None
            step=1
            return self[start:stop:step]
        else:
            raise KeyError('requires a slice object or integer key')
        if self.step==1 and not hasattr(self,'_next') and self.orientation>0:
            return SeqPath(self.path,self.start+start*self.step,
                           self.start+stop*self.step,
                           self.step*step)
        elif self.orientation<0 and not hasattr(self,'_next'):
            return SeqPath(self.path,self.end-1-start*self.step,
                           self.end-1-stop*self.step,
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

    def overlaps(self,p):
        "check whether two paths on same seq overlap"
        if self.path!=p.path:
            return False
        if (self.start<=p.start and p.start<self.end) or \
               (p.start<=self.start and self.start<p.end):
            return True
        else:
            return False

    def __mul__(self,other):
        "find intersection of two intervals"
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

    def __div__(self,other):
        "return transform from other -> self coordinate systems"
        return IntervalTransform(other,self)

    def __neg__(self):
        "return same interval in reverse orientation"
        return SeqPath(self.path,self.start,self.end,self.step,
                       -self.orientation)

    def __add__(self,other):
        "return merged interval spanning both self and other intervals"
        if self.path!=other.path or self.orientation!=other.orientation:
            raise ValueError('incompatible intervals cannot be merged.')
        if self.start<other.start:
            start=self.start
        else:
            start=other.start
        if self.end>other.end:
            end=self.end
        else:
            end=other.end
        return SeqPath(self.path,start,end,self.step,self.orientation)

    def __iadd__(self,other):
        "return merged interval spanning both self and other intervals"
        if self.path!=other.path or self.orientation!=other.orientation:
            raise ValueError('incompatible intervals cannot be merged.')
        if other.start<self.start:
            self.start=other.start
        if other.end>self.end:
            self.end=other.end
        return self # iadd MUST ALWAYS RETURN self!!
    
    def reverse_complement(self,s):
        compl={'a':'t', 'c':'g', 'g':'c', 't':'a', 'u':'a', 'n':'n',
               'A':'T', 'C':'G', 'G':'C', 'T':'A', 'U':'A', 'N':'N'}
        return ''.join([compl.get(c,c) for c in s[::-1]])

    def seqtype(self):
        "Get the sequence type for this sequence"
        obj=self
        while 1:
            if hasattr(obj,'_seqtype'):
                return obj._seqtype
            if hasattr(obj,'path') and obj.path!=obj:
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
        try: # USE id CONVENTION TO GET A NAME FOR THIS SEQUENCE
            id=self.path.id
        except AttributeError: # OTHERWISE JUST USE A DEFAULT, SHOWING THERE'S NO id
            id='@NONAME'
        return '%s%s[%s:%s]' % (ori,id,repr(self.start),repr(self.end))

    def repr_dict(self):
        "Return compact dictionary representing this interval"
        try:
            id=self.path.id
        except AttributeError:
            id=self.id
        return {'id':id,'start':self.start,'end':self.end,'ori':self.orientation}





# BASIC WRAPPER FOR A SEQUENCE.  LETS US ATTACH A NAME TO IT...
class NamedSequenceBase(SeqPath):
    start=0
    step=1
    orientation=1
    def __init__(self):
        self.path=self
        self.end=len(self)

    def update(self,seq):
        'change this sequence to the string <seq>'
        self.seq=seq
        self.end=len(self)

    def __len__(self):
        return len(self.seq) # COMPUTE IT FROM THE SEQUENCE

    def strslice(self,start,end):
        return self.seq[start:end]


class NamedSequence(NamedSequenceBase):
    def __init__(self,s,id):
        self.id=id
        self.seq=s
        NamedSequenceBase.__init__(self)





# CURRENTLY UNUSED

## class PathEdgeDict(dict):
##     def __init__(self,p):
##         self.path=p.path
##         self.pos=p.end-1
##         if p.end<len(p.path):
##             dict.__setitem__(self,p.path[p.end],1)
##         if hasattr(p.path,'_next') and self.pos in p.path._next:
##             dict.update(self,p.path._next[self.pos])
##     def __setitem__(self,k,val):
##         print 'entered PathEdgeDict.setitem'
##         if not hasattr(self.path,'_next'):
##             self.path._next={}
##         if self.pos not in self.path._next:
##             self.path._next[self.pos]={}
##         self.path._next[self.pos][k]=val
##         dict.__setitem__(self,k,val)
        


## class PathNextDescr(object):
##     def __init__(self,attrName='next'):
##         self.attrName=attrName

##     def __get__(self,obj,objtype):
##         return PathEdgeDict(obj)

##     def __set__(self,obj,val):
##         raise AttributeError(self.attrName+' is read-only!')

## class LengthDescriptor(object):
##     def __init__(self,attr):
##         self.attr=attr
##     def __get__(self,obj,objtype):
##         return len(getattr(obj,self.attr))
##     def __set__(self,obj,val):
##         raise AttributeError(self.attr+' is read-only!')


## def firstItem(aList):
##     if hasattr(aList,'__iter__'):
##         for i in aList:
##             return i
##     else:
##         return aList

