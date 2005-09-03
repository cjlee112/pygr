from pygr.poa import *
#from pathquery import *

class AnonSequence(NamedSequence):
    """Defines a sequence class with unknown sequence, but
    known length"""
    def __init__(self, len, id):
        s=''
        self.known=list()
        NamedSequence.__init__(self,s,id)
        self.end=len

    def seqsplice(self,s,start,end):
        (begin,stop,step)=slice(start,end).indices(self.end)
        
        if(start<end):
            self.known+=[(s,start,stop)]
        elif start>end:
            self.known+=[(s[::-1],start,stop)]

    def known_int(self):
        for u in self.known:
            yield {'src_id':self.id,'start':u[1],'end':u[2],'seq':u[0]}
                
 
class ReferenceSequence(NamedSequence):
    """Defines a reference sequence class that is subscriptable
    by other sequences. If sequence ids match the resulting sequnce
    will reference this class. This is useful for coordinate
    transforms when an unknown sequence intervals are transformed
    to known sequence"""
    
    def __init__(self, s,id):
        NamedSequence.__init__(self,s,id)

    def __getitem__(self,iv):
        if(isinstance(iv,SeqPath)):
            if(iv.id==self.id):
                s=self[iv.start:iv.end:iv.step]
                s.orientation=iv.orientation
                return s
        else:
            return SeqPath.__getitem__(self,iv)

    def mapCoordinates(self, obj):
        m=PathMapping2()
        for ival in obj:
            m[ival]=self[ival]
        return m

class UnkSequence(SeqPath):
    """Defines a sequence class for pure interval manipulation.
    No sequence information (i.e. length, or seq itself) is needed.
    """
    def __init__(self,id,start=0,end=0,step=1,orientation=1):
        self.id=id
        SeqPath.__init__(self,id)
        self.start=start
        self.end=end
        self.step=step
        self.orientation=orientation
        if(self.start!=None and self.end!=None and self.start>self.end):
            t=self.start
            if(self.end>=0):
                self.start=self.end+1
            else:
                self.start=self.end
            if(t>=0):
                self.end=t+1
            else:
                self.end=t
            self.orientation=-self.orientation
        
    def __getitem__(self,k):
        if isinstance(k,types.SliceType):
            (start,stop,step)=(k.start,k.stop,k.step)
            if k.step==None:
                step=1
        elif isinstance(k,types.IntType):
            start=k
            stop=k+1
            if(k==-1):
                stop=None
            step=1
            return self[start:stop:step]
        else:
            raise KeyError('requires a slice object or integer key')
        if self.step==1 and stop!=None:
            return UnkSequence(self.id,self.start+start*self.step,
                           self.start+stop*self.step,
                           self.step*step,self.orientation)
        else:
            return UnkSequence(self.id,start,stop,step,self.orientation)
