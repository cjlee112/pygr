class NLMSASeqList(list):
  def __init__(self,nlmsaSeqDict):
    list.__init__(self)
    self.nlmsaSeqDict=nlmsaSeqDict
  def __getitem__(self,nlmsaID):
    'return NLMSASequence for a given nlmsa_id'
    try:
      return list.__getitem__(self,nlmsaID)
    except IndexError:
      seqID,nsID=self.nlmsaSeqDict.IDdict[str(nlmsaID)]
      return list.__getitem__(self,nsID)
  def getSeq(self,nlmsaID):
    'return seq for a given nlmsa_id'
    seqID,nsID=self.nlmsaSeqDict.IDdict[str(nlmsaID)]
    return self.nlmsaSeqDict.nlmsa.seqDict[seqID]
  def getSeqID(self,nlmsaID):
    'return seqID for a given nlmsa_id'
    seqID,nsID=self.nlmsaSeqDict.IDdict[str(nlmsaID)]
    return seqID
  def is_lpo(self,id):
    if id>=len(self):
      return False
    ns=self[id]
    if ns.is_lpo:
      return True
    else:
      return False
  def nextID(self):
      return len(self)

class EmptySliceError(KeyError):
  pass
  

class EmptySlice:
  'Empty slice for use by NLMSASlice'
  def __init__(self, seq):
    self.seq = seq
  def edges(self,**kwargs):
    return []
  def items(self, **kwargs):
    return []
  def iteritems(self, **kwargs):
    return iter([])
  def keys(self, **kwargs):
    return []
  def __iter__(self):
    return iter([])
  def __getitem__(self, k):
    raise KeyError
  def __len__(self):
    return 0
  def matchIntervals(self, seq=None):
    return []
  def findSeqEnds(self, seq):
    raise KeyError('seq not aligned in this interval')
  def generateSeqEnds(self):
    return []
  def groupByIntervals(self,**kwargs):
    return {}
  def groupBySequences(self,**kwargs):
    return []
  def split(self, **kwargs):
    return []
  def regions(self, **kwargs):
    return []
  def __cmp__(self,other):
    return cmp(self.seq, other.seq)
  def rawIvals(self):
    return []
    


class NLMSASeqDict(dict):
  'index sequences by pathForward, and use list to keep reverse mapping'
  def __init__(self,nlmsa,filename,mode,maxID=1000000,idDictClass=None):
    dict.__init__(self)
    self.seqlist=NLMSASeqList(self)
    self.maxID=maxID
    self.nlmsa=nlmsa
    self.filename=filename
    if mode=='memory': # JUST USE PYTHON DICTIONARY
      idDictClass=dict
    elif mode=='w': # NEW DATABASE
      mode='c'
    if idDictClass is None: # USE PERSISTENT ID DICTIONARY STORAGE
      import shelve
      self.seqIDdict=shelve.open(filename+'.seqIDdict',mode)
      self.IDdict=shelve.open(filename+'.idDict',mode)
    else: # USER SUPPLIED CLASS FOR ID DICTIONARY STORAGE
      self.seqIDdict=idDictClass()
      self.IDdict=idDictClass()

  def saveSeq(self,seq,nsID= -1,offset=0,nlmsaID=None):
    'save mapping of seq to specified (nlmsaID,ns,offset)'
    if nsID<0: # LET THE UNION FIGURE IT OUT
      self.nlmsa.currentUnion.__iadd__(seq)
      return # THE UNION ADDED IT FOR US, NO NEED TO DO ANYTHING
    import types
    if isinstance(seq,types.StringType):
      id=seq # TREAT THIS AS FULLY QUALIFIED IDENTIFIER
    else: # GET THE IDENTFIER FROM THE SEQ / DATABASE
      id=self.getSeqID(seq)
    if nlmsaID is None: # ALLOCATE A NEW UNIQUE ID
      nlmsaID=self.nlmsa.nextID()
    self.seqIDdict[id]=nlmsaID,nsID,offset
    self.IDdict[str(nlmsaID)]=id,nsID

  def getIDcoords(self,seq):
    'return nlmsaID,start,stop for a given seq ival.'
    nlmsaID=self.getID(seq)
    return nlmsaID,seq.start,seq.stop # STANDARD COORDS
  def getID(self,seq):
    'return nlmsa_id for a given seq'
    return self[seq][0]
  def __getitem__(self,seq):
    'return nlmsaID,NLMSASequence,offset for a given seq'
    if not hasattr(seq,'annotationType'): # DON'T CACHE ANNOTATIONS
      try: # LOOK IN OUR SEQUENCE CACHE
        return dict.__getitem__(self,seq.pathForward)
      except AttributeError:
        raise KeyError('key must be a sequence interval!')
      except KeyError:
        pass
    seqID=self.getSeqID(seq) # USE SEQ ID TO LOOK UP...
    try:
      nlmsaID,nsID,offset=self.seqIDdict[seqID]
    except KeyError:
      raise KeyError('seq not found in this alignment')
    v=nlmsaID,self.seqlist[nsID],offset
    if not hasattr(seq,'annotationType'): # DON'T CACHE ANNOTATIONS
      dict.__setitem__(self,seq.pathForward,v) # CACHE THIS RESULT
    return v

  def getSeqID(self,seq):
    'return fully qualified sequence ID for this seq'
    return (~(self.nlmsa.seqDict))[seq]

  def __setitem__(self,k,ns):
    'save mapping of seq to the specified NLMSASequence'
    self.seqlist.append(ns)
    import types
    if isinstance(k,types.StringType):
      dict.__setitem__(self,k,(ns.id,ns,0)) # ALLOW BUILD WITH A STRING OBJECT
    elif k is not None:
      dict.__setitem__(self,k.pathForward,(ns.id,ns,0))
  def __iadd__(self,ns):
    'add coord system ns to the alignment'
    self[None]=ns
    return self # iadd MUST RETURN self!!!
  def close(self):
    'finalize and close shelve indexes'
    self.seqIDdict.close()
    self.IDdict.close()
  def reopenReadOnly(self,mode='r'):
    'save existing data and reopen in read-only mode'
    self.close()
    import shelve
    self.seqIDdict=shelve.open(self.filename+'.seqIDdict',mode)
    self.IDdict=shelve.open(self.filename+'.idDict',mode)
  def getUnionSlice(self,seq):
    'get union coords for this seq interval, adding seq to index if needed'
    try:
      id,ns,offset=self[seq] # LOOK UP IN INDEX
    except KeyError:
      self.saveSeq(seq) # ADD THIS NEW SEQUENCE TO OUR CURRENT UNION
      id,ns,offset=self[seq] # LOOK UP IN INDEX
    i,start,stop=self.getIDcoords(seq) # MAKE SURE TO HANDLE ANNOTS RIGHT
    if start<0: # REVERSE ORIENTATION
      return ns,slice(start-offset,stop-offset) # USE UNION COORDS
    else: # FORWARD ORIENTATION
      return ns,slice(start+offset,stop+offset) # USE UNION COORDS





def splitLPOintervals(lpoList,ival,targetIval=None):
    'return list of intervals split to different LPOs'
    if ival.start<0: # REVERSE ORIENTATION: FORCE INTO FORWARD ORI
        start= -(ival.stop)
        stop= -(ival.start)
    else: # FORWARD ORIENTATION
        start=ival.start
        stop=ival.stop
    l=[]
    i=len(lpoList)-1
    while i>=0:
        offset=lpoList[i].offset
        if offset<stop: # APPEARS TO BE IN THIS
            if offset<=start: # FITS COMPLETELY IN THIS LPO
                if ival.start<0: # REVERSE ORI
                    myslice=slice(offset-stop,offset-start)
                else: # FORWARD ORI
                    myslice=slice(start-offset,stop-offset)
                if targetIval is not None:
                    l.append((lpoList[i],myslice,targetIval))
                else:
                    l.append((lpoList[i],myslice))
                return l # DONE
            else: # CONTINUES PAST START OF THIS LPO
                if ival.start<0: # REVERSE ORI
                    myslice=slice(offset-stop,0)
                else: # FORWARD ORI
                    myslice=slice(0,stop-offset)
                if targetIval is not None:
                    l.append((lpoList[i],myslice,targetIval[offset-start:]))
                    targetIval=targetIval[:offset-start] #REMOVE PART ALREADY APPENDED
                else:
                    l.append((lpoList[i],myslice))
                stop=offset
        i-=1 # CONTINUE TO PREVIOUS LPO
    raise ValueError('empty lpoList or offset not starting at 0?  Debug!')

        
class BuildMSASlice(object):
    def __init__(self,ns,start,stop,id,offset,is_lpo=0,seq=None):
        self.ns=ns
        self.start=start
        self.stop=stop
        self.id=id
        self.offset=offset
        self.is_lpo=is_lpo
        self.seq=seq
    def offsetSlice(self,ival):
        if ival.orientation<0:
            return slice(ival.start-self.offset,ival.stop-self.offset)
        else:
            return slice(ival.start+self.offset,ival.stop+self.offset)
    def __iadd__(self,targetIval):
        'save an alignment edge between self and targetIval'
        import types
        if self.is_lpo: # ASSIGN TO CORRECT LPO(S)
            if isinstance(targetIval,types.SliceType):
                raise ValueError('you attempted to map LPO --> LPO?!?')
            self.ns.nlmsaLetters.__iadd__(targetIval)
            splitList=splitLPOintervals(self.ns.nlmsaLetters.lpoList,
                                        slice(self.start,self.stop),targetIval)
            for ns,src,target in splitList: # SAVE INTERVALS TO RESPECTIVE LPOs
                ns[src]=self.ns.nlmsaLetters.seqs.getIDcoords(target) #LPO-->TARGET
                if self.ns.nlmsaLetters.is_bidirectional:
                    nsu,myslice=self.ns.nlmsaLetters.seqs.getUnionSlice(target)
                    nsu[myslice]=(ns.id,src.start,src.stop) # SAVE TARGET --> LPO
        else:
            if isinstance(targetIval,types.SliceType): # TARGET IS LPO
                splitList=splitLPOintervals(self.ns.nlmsaLetters.lpoList,
                                            targetIval,self.seq)
                for ns,target,src in splitList:
                    self.ns[self.offsetSlice(src)]=(ns.id,target.start,target.stop)
                    if self.ns.nlmsaLetters.is_bidirectional:
                        ns[target]=(self.id,src.start,src.stop) # SAVE LPO --> SRC
            else: # BOTH SRC AND TARGET ARE NORMAL SEQS.  use_virtual_lpo!!
                self.ns.nlmsaLetters.__iadd__(targetIval)
                self.ns.nlmsaLetters.init_pairwise_mode(verbose=True)
                ns_lpo=self.ns.nlmsaLetters.seqlist[self.ns.id -1] # OUR VIRTUAL LPO
                ns_lpo[self.offsetSlice(self.seq)]=self.ns.nlmsaLetters.seqs \
                     .getIDcoords(targetIval) # SAVE SRC --> TARGET
                if self.ns.nlmsaLetters.is_bidirectional:
                    nsu,myslice=self.ns.nlmsaLetters.seqs.getUnionSlice(targetIval)
                    ns_lpo=self.ns.nlmsaLetters.seqlist[nsu.id -1] # OUR VIRTUAL LPO
                    ns_lpo[myslice]=(self.id,self.start,self.stop) # SAVE TARGET --> SRC
        return self # iadd MUST ALWAYS RETURN self
    def __setitem__(self,k,v):
        if v is not None:
            raise ValueError('NLMSA cannot save edge-info. Only nlmsa[s1][s2]=None allowed')
        self+=k
