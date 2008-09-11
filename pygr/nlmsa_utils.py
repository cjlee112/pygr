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
      mode='n'
    if idDictClass is None: # USE PERSISTENT ID DICTIONARY STORAGE
      from classutil import open_shelve
      self.seqIDdict = open_shelve(filename+'.seqIDdict',mode)
      self.IDdict = open_shelve(filename+'.idDict',mode)
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
    from classutil import open_shelve
    self.seqIDdict = open_shelve(self.filename+'.seqIDdict',mode)
    self.IDdict = open_shelve(self.filename+'.idDict',mode)
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



def read_seq_dict(pathstem,trypath=None):
  'read seqDict for NLMSA'
  import seqdb,os
  if os.access(pathstem+'.seqDictP',os.R_OK):
    from pygr.Data import loads
    ifile = file(pathstem+'.seqDictP')
    try: # LOAD FROM pygr.Data-AWARE PICKLE FILE
      seqDict = loads(ifile.read())
    finally:
      ifile.close()
  elif os.access(pathstem+'.seqDict',os.R_OK): # OLD-STYLE UNION HEADER
    seqDict = seqdb.PrefixUnionDict(filename=pathstem+'.seqDict',
                                         trypath=trypath)
  else:
    raise ValueError('''Unable to find seqDict file
%s.seqDictP or %s.seqDict
and no seqDict provided as an argument''' % (pathstem,pathstem))
  return seqDict


def save_seq_dict(pathstem,seqDict):
  'save seqDict to a pygr.Data-aware pickle file'
  from pygr.Data import dumps
  ofile = file(pathstem+'.seqDictP','w')
  try:
    ofile.write(dumps(seqDict))
  finally:
    ofile.close()


def prune_self_mappings(src_prefix,dest_prefix,is_bidirectional):
  '''return is_bidirectional flag according to whether source and
  target are the same genome.  This handles axtNet reading, in which
  mappings between genomes are given in only one direction, whereas
  mappings between the same genome are given in both directions.'''
  if src_prefix == dest_prefix:
    return 0
  else:
    return 1

def nlmsa_textdump_unpickler(filepath,kwargs):
  from classutil import get_env_or_cwd 
  from cnestedlist import textfile_to_binaries,NLMSA
  import sys
  print >>sys.stderr,'Saving NLMSA indexes from textdump',filepath
  path = textfile_to_binaries(filepath,buildpath=get_env_or_cwd('PYGRDATABUILDDIR'),
                              **kwargs)
  o = NLMSA(path) # NOW OPEN IN READ MODE FROM THE SAVED INDEX FILESET
  o._saveLocalBuild = True # MARK THIS FOR SAVING IN LOCAL PYGR.DATA
  return o
nlmsa_textdump_unpickler.__safe_for_unpickling__ = 1
  
class NLMSABuilder(object):
  'when unpickled triggers construction of NLMSA from textdump'
  def __init__(self,filepath,**kwargs):
    self.filepath = filepath
    self.kwargs = kwargs
  def __reduce__(self):
    return (nlmsa_textdump_unpickler,(self.filepath,self.kwargs))
    
class SeqCacheOwner(object):
    'weak referenceable object: workaround for pyrex extension classes'
    def __init__(self):
      self.cachedSeqs = {}
    def cache_reference(self, seq):
      'keep a ref to seqs cached on our behalf'
      self.cachedSeqs[seq.id] = seq

