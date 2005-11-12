
import types
from sequtil import *


NOT_ON_SAME_PATH= -2

class ReadOnlyAttribute(object):
    def __init__(self,attr):
        self.attr=attr
    def __get__(self,obj,klass):
        return getattr(obj,self.attr)

class IntervalTransform(object):
    "Represents coordinate transformation from one interval to another"
    srcPath=ReadOnlyAttribute('_srcPath') # PREVENT USER FROM MODIFYING THESE!
    destPath=ReadOnlyAttribute('_destPath')
    def __init__(self,srcPath,destPath,edgeInfo=None,
                 edgeAttr=None,edgeIndex=None):
        "MAP FROM srcPath -> destPath"
        self.scale= len(destPath)/float(len(srcPath))
        self._srcPath=srcPath
        self._destPath=destPath
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
        'transform int srcPath local coord to destPath local coord'
        return int(i*self.scale)
    def xformBack(self,i):
        'transform int destPath local coord to srcPath local coord'
        return int(i/self.scale)
    def getStartStop(self,srcPath,ourPath):
        'compute srcPath start,stop in ourPath local coords'
        if srcPath.path is ourPath.path:
            return srcPath.start-ourPath.start,srcPath.stop-ourPath.start
        try:
            if srcPath.path._reverse is ourPath.path:
                return -(srcPath.start)-ourPath.start,\
                       -(srcPath.stop)-ourPath.start
        except AttributeError:pass
        raise ValueError('sequence mismatch: argument not from this seq')
    def __call__(self,srcPath):
        """Apply this transformation to an interval
           NB: it is not restricted to the domain of this transform,
           and thus can extend BEYOND the boundaries of this transform.
           If you want it clipped use [] interface instead of ()."""
        start,stop=self.getStartStop(srcPath,self.srcPath)
        return SeqPath(self.destPath,self.xform(start),self.xform(stop),
                       relativeToStart=True)
    def reverse(self,destPath):
        "reverse transform an interval"
        start,stop=self.getStartStop(destPath,self.destPath)
        return SeqPath(self.srcPath,self.xformBack(start),
                       self.xformBack(stop),relativeToStart=True)
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
        try:
            return getattr(self.__dict__['edgeInfo'],attr)
        except (KeyError,AttributeError): # RAISE EXCEPTION IF NOT FOUND!
            raise AttributeError('neither IntervalTransform nor edgeinfo has attr '
                                 +attr)

    def repr_dict(self):
        "Return compact dictionary representing this interval mapping"
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



def absoluteSlice(seq,start,stop):
    '''get slice of top-level sequence object, in absolute coordinates.
    This method calls getitem on the top-level sequence object
    i.e. seq.pathForward'''
    if start<0: # REVERSE ORIENTATION
        return -(seq.pathForward[-stop:-start])
    else: # FORWARD ORIENTATION
        return seq.pathForward[start:stop]

def sumSliceIndex(i,myslice,relativeToStart):
    '''Adjust index value either relative to myslice.start (positive indexes)
    or relative to myslice.stop (negative indexes).  Handle the case where
    index value is None or myslice is None appropriately.
    '''
    if myslice is None: # NO OBJECT, SO NOTHING TO DO...
        return i
    if relativeToStart:
        attr='start'
    else:
        attr='stop'
    _attr='_'+attr
    if i is not None:
        i *= myslice.step
    try:
        return i+getattr(myslice,_attr)
    except AttributeError: # attr MUST NOT EXIST...
        if i is None:
            return None
        else: # FORCE getattr
            return i+getattr(myslice,attr)
    except TypeError:
        if i is None:
            return getattr(myslice,_attr)
        raise


class ShadowAttribute(object):
    '''get an attribute if it exists, but if not, do NOT trigger
    getattr on it (as hasattr does), just raise AttributeError.'''
    def __init__(self,attr):
        self.attr=attr
    def __get__(self,obj,klass):
        try: # 1ST LOOK IN THE OBJECT __dict__
            return obj.__dict__[self.attr]
        except (AttributeError,KeyError): # NOW TRY CLASS ATTRIBUTE...
            return getattr(klass,self.attr)

class SeqOriDescriptor(object):
    "Get orientation of sequence interval"
    def __get__(self,seq,objtype):
        try:
            if seq._start>=0:
                return 1 # FORWARD ORIENTATION
        except AttributeError:
            try:
                if seq._stop>0:
                    return 1 # FORWARD ORIENTATION
            except AttributeError: # BOTH ATTRIBUTES MISSING!
                raise AttributeError('SeqPath object has no start or stop!')
        return -1 # REVERSE ORIENTATION

class PathForwardDescr(object):
    'get the top-level forward sequence object'
    def __get__(self,seq,objtype):
        if seq.orientation>0:
            return seq.path
        else:
            return seq.path._reverse

class AbsIntervalDescr(object):
    'get the top-level forward sequence object'
    def __get__(self,seq,objtype):
        if seq.orientation>0:
            return seq.start,seq.stop
        else:
            return -(seq.stop),-(seq.start)


class SeqPath(object):
    '''Base class for specifying a path, ie. sequence interval.
    This implementation takes a sequence object as initializer
    and simply represents the interval as a slice of the sequence.'''
    orientation=SeqOriDescriptor()  # COMPUTE ORIENTATION AUTOMATICALLY
    _start=ShadowAttribute('start') # SHADOW start, stop WITHOUT TRIGGERING
    _stop=ShadowAttribute('stop')   #  getattr IF THEY ARE ABSENT
    pathForward=PathForwardDescr()  # GET THE TOP-LEVEL FORWARD SEQUENCE OBJ
    _abs_interval=AbsIntervalDescr()
    def __init__(self,path,start=0,stop=None,step=None,reversePath=None,
                 relativeToStart=False,absoluteCoords=False):
        '''Return slice of path[start:stop:step].
        NB: start>stop means reverse orientation, i.e. (-path)[-stop:-start]
        start/stop are LOCAL coordinates relative to the specified path
        By default, start/stop are interpreted in the usual Python slicing way,
        i.e. a negative start value is interpreted as len(path)-start.
        The relativeToStart option turns off this behavior, so that negative
        values are interpreted as negative coordinates in the local coordinate
        system of path.

        absoluteCoords option allows intervals to be created using Pygrs internal
        coordinate convention i.e. -20,-10 --> -(path.pathForward[10:20])
        '''
        if reversePath is not None:
            try: # IF reversePath.stop KNOWN, USE IT
                start= -(reversePath._stop)
            except AttributeError: pass
        if absoluteCoords: # THIS OPTION PROVIDES TRANSPARENT WAY TO CREATE
            if start>=0:   # INTERVALS USING start,stop PAIRS THAT FOLLOW
                path=path.pathForward # OUR INTERNAL SIGN CONVENTION
            else: # i.e. start<0 MEANS REVERSE ORIENTATION!
                path= - (path.pathForward)
        else: # ADJUST start,stop ACCORDING TO path.start / path.stop
            start=sumSliceIndex(start,path,relativeToStart or start is None or start>=0)
            stop=sumSliceIndex(stop,path,relativeToStart or (stop is not None and stop>=0))
        if start is not None and stop is not None and start>stop:
            start= -start # start>stop MEANS REVERSE ORIENTATION!
            stop= -stop
            if path is not None:
                path= -path
        start=self.check_bounds(start,path) # PERFORM BOUNDS CHECKING
        stop=self.check_bounds(stop,path,'stop') # IF POSSIBLE...
        if start is not None and stop is not None and start>=stop:
            raise IndexError('cannot create empty sequence interval!')
        if start is not None:
            self.start=start
        if stop is not None:
            self.stop=stop
        if step is None:
            step=1
        if path is None:
            self.path=self
            self.step=step
        else: # STORE TOP-LEVEL SEQUENCE PATH...
            self.path=path.path
            self.step=step*path.step

    def check_bounds(self,start,path,attr='start',forceBounds=False,
                     direction= -1,prefix='_'):
        '''check that the specified attribute is in bounds.
        If that cant be checked now (due to missing path.start or path.stop)
        save the attribute as _raw_attr to force a check later on.'''
        if attr=='stop':
            direction= -direction
        if not forceBounds:
            attr=prefix+attr
        if path is not None: # CHECK IF start OR stop GOES OUT OF BOUNDS.
            try: # ONLY USE BOUNDS IF PRESENT
                if start is not None and \
                       cmp(start,getattr(path.path,attr))*direction>0:
                    start=getattr(path.path,attr)
            except AttributeError: # start>stop CHECK DONE BELOW...
                setattr(self,'_raw'+attr,start)
                start=None
        return start # RETURN THE PROPERLY CHECKED VALUE...

    def __getitem__(self,k):
        if isinstance(k,types.IntType):
            k=slice(k,k+1,1)
        if isinstance(k,types.SliceType):
            return SeqPath(self,k.start,k.stop,k.step)
        raise KeyError('requires a slice object or integer key')

    def __getattr__(self,attr):
        'automatically generate start and stop if needed'
        if self.__dict__['path'] is self: # TOP-LEVEL SEQUENCE OBJECT
            if attr=='start':
                if self.orientation>0:
                    return 0 # FORWARD ORI
                else:
                    return -len(self._reverse) # REVERSE ORI
            elif attr=='stop': 
                if self.orientation<0:
                    return 0 # REVERSE ORI
                else:
                    return len(self) # FORWARD ORI
        elif attr=='start' or attr=='stop': # A SEQUENCE SLICE
            if '_raw_'+attr in self.__dict__: # HAVE A RAW VALUE, MUST CHECK IT!
                i=self.check_bounds(getattr(self,'_raw_'+attr),self.path,attr,True)
                setattr(self,attr,i) # SAVE THE TRUNCATED VALUE
                try: # SEE IF NEW INTERVAL BOUNDS ARE EMPTY...
                    if self._start>=self._stop: # AVOIDS INFINITE getattr LOOP!
                        raise IndexError('caught empty sequence interval!')
                except AttributeError: pass # OTHER ATTRIBUTE MISSING... IGNORE.
                delattr(self,'_raw_'+attr) # GET RID OF THE RAW VALUE
                return i
            else:
                return getattr(self.path,attr) # GET FROM TOP-LEVEL SEQUENCE
        raise AttributeError('SeqPath object has no attribute '+attr)

    def __len__(self):
        if self.path is self and self.orientation<0:
            return len(self._reverse) # GET LENGTH FROM FORWARD SEQUENCE
        return (self.stop-self.start)/self.step

    def __iter__(self):
        for i in range(len(self)):
            yield self[i]

    def __cmp__(self,other):
        if not isinstance(other,SeqPath):
            return -1
        if self.path is other.path:
            return cmp((self.start,self.stop),(other.start,other.stop))
        else:
            return NOT_ON_SAME_PATH
            #raise TypeError('SeqPath not comparable, not on same path: %s,%s'
            #                % (self.path,other.path))
    
    def __contains__(self,k):
        # PUT OTHER LOGIC HERE FOR CHECKING WHETHER INTERVAL IS CONTAINED...
        if isinstance(k,SeqPath):
            if k.path==self.path and self.start<=k.start and k.stop<=self.stop:
                return True
            else:
                return False
        elif isinstance(k,types.IntType):
            return self.start<=k and k<self.stop

    def overlaps(self,p):
        "check whether two paths on same seq overlap"
        if self.path is not p.path:
            return False
        if (self.start<=p.start and p.start<self.stop) or \
               (p.start<=self.start and self.start<p.stop):
            return True
        else:
            return False

    def __mul__(self,other):
        "find intersection of two intervals"
        if isinstance(other,SeqPath):
            if self.path!=other.path:
                return None
            start=max(self.start,other.start)
            stop=min(self.stop,other.stop)
            if start<stop:
                return SeqPath(self.path,start,stop)
            else:
                return None
        else:
            raise TypeError('SeqPath can only intersect SeqPath')

    def __div__(self,other):
        "return transform from other -> self coordinate systems"
        return IntervalTransform(other,self)

    def __neg__(self):
        "return same interval in reverse orientation"
        try:
            if self.seqtype()==PROTEIN_SEQTYPE:
                raise ValueError('protein sequence has no reverse orientation!')
        except AttributeError: pass # ALLOW UNTYPED SEQ OBJECTS TO BE REV-COMPD
        if self is self.path: # TOP-LEVEL SEQUENCE OBJECT
            try:
                return self._reverse # USE EXISTING RC OBJECT FOR THIS SEQ
            except AttributeError: #  CREATE ONLY ONE RC FOR THIS SEQUENCE
                self._reverse=SeqPath(None,None,stop=0,reversePath=self)
                self._reverse._reverse=self
                return self._reverse
        elif self.orientation>0: # FORWARD ORI: JUST REVERSE INDICES
            return SeqPath(self.path,self.stop,self.start,self.step) #SWAP ==> RC
        else: # REVERSE ORI: BECAUSE OF stop=0 POSSIBILITY, USE POSITIVE COORDS
            return SeqPath(self.path._reverse,-(self.stop),-(self.start),self.step)

    def __add__(self,other):
        "return merged interval spanning both self and other intervals"
        if self.path is not other.path:
            raise ValueError('incompatible intervals cannot be merged.')
        if self.start<other.start:
            start=self.start
        else:
            start=other.start
        if self.stop>other.stop:
            stop=self.stop
        else:
            stop=other.stop
        return SeqPath(self.path,start,stop,self.step)

    def __iadd__(self,other):
        "return merged interval spanning both self and other intervals"
        if self.path is not other.path:
            raise ValueError('incompatible intervals cannot be merged.')
        if other.start<self.start:
            self.start=other.start
        if other.stop>self.stop:
            self.stop=other.stop
        return self # iadd MUST ALWAYS RETURN self!!
    
    _complement={'a':'t', 'c':'g', 'g':'c', 't':'a', 'u':'a', 'n':'n',
                 'A':'T', 'C':'G', 'G':'C', 'T':'A', 'U':'A', 'N':'N'}
    def reverse_complement(self,s):
        'get reverse complement of a string s'
        return ''.join([self._complement.get(c,c) for c in s[::-1]])

    def seqtype(self):
        "Get the sequence type for this sequence"
        path=self.pathForward
        try: # TRY GETTING IT FROM TOP-LEVEL SEQUENCE OBJECT?
            return path._seqtype
        except AttributeError:
            try: # TRY TO GET IT FROM DB THIS SEQ IS ASSOCIATED WITH, IF ANY
                return path.db._seqtype
            except AttributeError:# GUESS IT FROM 1ST 40 LETTERS OF SEQUENCE
                path._seqtype=guess_seqtype(str(self[0:40]))
                return path._seqtype

    def __str__(self):
        'string for this sequence interval; use reverse complement if necessary...'
        if self.orientation>0:
            return self.path.strslice(self.start,self.stop)
        else:
            s=self.path._reverse.strslice(-(self.stop),-(self.start))
            return self.reverse_complement(s)
    def __repr__(self):
        if self.orientation<0: # INDICATE NEGATIVE ORIENTATION
            ori='-'
        else:
            ori=''
        try: # USE id CONVENTION TO GET A NAME FOR THIS SEQUENCE
            id=self.path.id
        except AttributeError:
            try: # TRY TO GET FROM TOP-LEVEL FORWARD SEQUENCE
                id=self.path._reverse.id
            except AttributeError: # OTHERWISE JUST USE A DEFAULT, SHOWING THERE'S NO id
                id='@NONAME'
        return '%s%s[%s:%s]' % (ori,id,repr(self.start),repr(self.stop))

    def repr_dict(self):
        "Return compact dictionary representing this interval"
        try:
            id=self.path.id
        except AttributeError:
            id=self.id
        return {'id':id,'start':self.start,'end':self.stop,'ori':self.orientation}




# BASIC WRAPPER FOR A SEQUENCE.  LETS US ATTACH A NAME TO IT...
class SequenceBase(SeqPath):
    'base sequence type assumes there will be a seq attribute providing sequence'
    start=0
    step=1
    orientation=1
    def __init__(self):
        self.path=self
        #self.stop=len(self) # NOW HANDLED AUTOMATICALLY BY SeqPath.__getattr__

    def update(self,seq):
        'change this sequence to the string <seq>'
        self.seq=seq
        #self.stop=len(self) # NOW HANDLED AUTOMATICALLY BY SeqPath.__getattr__

    def __len__(self):
        'default: get the whole self.seq and compute its length'
        return len(self.seq) # COMPUTE IT FROM THE SEQUENCE

    def strslice(self,start,stop):
        'default method assumes self.seq yields string slices representing sequence'
        return self.seq[start:stop]


class Sequence(SequenceBase):
    'default sequence class initialized with a sequence string and ID'
    def __init__(self,s,id):
        SequenceBase.__init__(self)
        self.id=id
        self.seq=s
        self.stop=len(self)





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

