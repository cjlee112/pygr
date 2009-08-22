#from lpo import POMSANodeRef
import sequence
import nlmsa_utils

class IntervalMap(object): # <CJL
  def __init__(self,ival,im=None):
    if im is not None:
      self.copy(im)
    else:
      self.start = ival[0] # SAVE INTERVAL INFO
      self.end = ival[1]
      self.target_id = ival[2]
      self.target_start = ival[3]
      self.target_end = ival[4]
  def copy(self,im):
      self.start = im.start
      self.end = im.end
      self.target_id = im.target_id
      self.target_start = im.target_start
      self.target_end = im.target_end


def target_qsort_cmp(a,b):
  'SORT IN target_id ORDER, SECONDARILY BY target_start'
  if a.target_id < b.target_id:
    return -1
  elif a.target_id > b.target_id:
    return 1
  elif a.target_start < b.target_start:
    return -1
  elif a.target_start > b.target_start:
    return 1
  else:
    return 0 # CJL/>




class IntervalFileDBIterator(object):
  def __init__(self, start, end, db=None, ns=None, nbuffer=1024, rawIvals=None):
    self.start=start
    self.end=end
    self.db=db
    if ns is not None:
      if ns.idb is not None:
        self.idb=ns.idb
      elif ns.db is None:
        ns.forceLoad()
      self.db=ns.db
    if rawIvals is not None:
      im = [] # <CJL
      for ival in rawIvals:
        im.append(IntervalMap(ival))
      self.im_buf = im # CJL/>
      self.nhit=len(im) # TOTAL NUMBER OF INTERVALS STORED

  def copy(self,src):
    'copy items from src to this iterator buffer'
    if src is None:
      raise ValueError('src is None!  Debug!!')
    im = []
    for ival in src.im_buf:
      im.append(IntervalMap(None,im=ival))
    self.nhit=src.nhit # COPY ARRAY AND SET CORRECT SIZE
    self.im_buf = im

  def mergeSeq(self):
    'merge intervals into single interval per sequence orientation'
    if self.nhit<=0: # NOTHING TO MERGE, SO JUST RETURN
      return 0
    self.im_buf.sort(target_qsort_cmp) # ORDER BY id,start
    id = -1
    im = []
    for ival in self.im_buf:
      if ival.target_id!=id or (im[-1].target_start<0 and
                                ival.target_start>=0):
        im.append(ival) # RECORD THIS AS START OF THE NEW SEQUENCE / ORIENTATION
        id = ival.target_id
      elif ival.target_end>im[-1].target_end:
        im[-1].target_end = ival.target_end # EXPAND THIS INTERVAL
        im[-1].end = ival.end # COPY SOURCE SEQ COORDS AS WELL
    self.nhit = len(im) # TOTAL #MERGED INTERVALS
    self.im_buf = im
    return self.nhit

  def getIntervalMap(self):
    return self.im_buf

  def __iter__(self):
    return iter(self.im_buf)




class NLMSASlice(object):
  def __init__(self, ns, start, stop, id= -1, offset=0,seq=None):
    if seq is None: # GET FROM NLMSASequence
      seq=ns.seq
    self.nlmsaSequence=ns # SAVE BASIC INFO
    self.start=start
    self.stop=stop
    self.offset=offset # ALWAYS STORE offset IN POSITIVE ORIENTATION
    self.deallocID= -1
    self.seq=seq
    # USE PYTHON METHOD TO DO QUERY
    id,ivals=ns.nlmsaLetters.doSlice(seq) # doSlice() RETURNS RAW INTERVALS
    self.id=id # SAVE OUR SEQUENCE'S nlmsa_id
    it=IntervalFileDBIterator(start,stop,rawIvals=ivals) # STORE IN BINARY FMT
    it2=IntervalFileDBIterator(start,stop) # HOLDER FOR SUBSEQUENT MERGE

    if it.nhit<=0:
      raise nlmsa_utils.EmptySliceError('this interval is not aligned!')
    it2.copy(it) # COPY FULL SET OF SAVED INTERVALS
    self.nseqBounds=it2.mergeSeq() # MERGE TO ONE INTERVAL PER SEQUENCE ORIENTATION
    self.seqBounds=it2.getIntervalMap() # SAVE SORTED ARRAY & DETACH FROM ITERATOR

    self.im=it.getIntervalMap() # RELEASE THIS ARRAY FROM THE ITERATOR
    self.n=it.nhit # TOTAL #INTERVALS SAVED FROM JOIN
    #qsort(self.im,self.n,sizeof(IntervalMap),imstart_qsort_cmp) # ORDER BY start

    n=0
    for i in range(self.nseqBounds): # COUNT NON-LPO SEQUENCES
      if not ns.nlmsaLetters.seqlist.is_lpo(self.seqBounds[i].target_id):
        n=n+1
    self.nrealseq=n # SAVE THE COUNT

    try: # _cache_max=0 TURNS OFF CACHING...
      cacheMax=ns.nlmsaLetters.seqDict._cache_max
    except AttributeError:
      cacheMax=1 # ALLOW CACHING...
    try:  # SAVE OUR COVERING INTERVALS AS CACHE HINTS IF POSSIBLE...
      saveCache=ns.nlmsaLetters.seqDict.cacheHint
    except AttributeError:
      cacheMax=0 # TURN OFF CACHING
    if cacheMax>0: # CONSTRUCT & SAVE DICT OF CACHE HINTS: COVERING INTERVALS
      from seqdb import cacheProxyDict
      self.deallocID,cacheProxy=cacheProxyDict()
      cacheDict={}
      try: # ADD A CACHE HINT FOR QUERY SEQ IVAL
        seqID=ns.nlmsaLetters.seqs.getSeqID(seq) # GET FULL-LENGTH ID
        cacheDict[seqID]=(self.start,self.stop)
      except KeyError:
        pass
      for i in range(self.nseqBounds): # ONLY SAVE NON-LPO SEQUENCES
        if not ns.nlmsaLetters.seqlist.is_lpo(self.seqBounds[i].target_id):
          cacheDict[ns.nlmsaLetters.seqlist.getSeqID(self.seqBounds[i].target_id)]=(self.seqBounds[i].target_start,self.seqBounds[i].target_end)
      saveCache(cacheProxy,cacheDict) # SAVE COVERING IVALS AS CACHE HINT

  def __del__(self):
    if self.deallocID>=0: # REMOVE OUR ENTRY FROM CACHE...
      from seqdb import cacheProxyDict
      try: # WORKAROUND weakref - PYREX PROBLEMS...
        del cacheProxyDict[self.deallocID]
      except KeyError:
        pass


  ########################################### ITERATOR METHODS
  def edges(self,mergeAll=False,**kwargs):
    'get list of tuples (srcIval,destIval,edge) aligned in this slice'
    seqIntervals=self.groupByIntervals(mergeAll=mergeAll,**kwargs)
    ivals=self.groupBySequences(seqIntervals,**kwargs)
    l=[]
    for ival1,ival2,mergeIntervals in ivals:
      l.append((ival1,ival2,sequence.Seq2SeqEdge(self,ival2,ival1,mergeIntervals)))
    return l
  def items(self,**kwargs):
    'get list of tuples (ival2,edge) aligned to this slice'
    l=[]
    for ival1,ival2,edge in self.edges(**kwargs):
      l.append((ival2,edge))
    return l
  def iteritems(self,**kwargs):
    return iter(self.items(**kwargs))
  def keys(self,mergeAll=False,**kwargs):
    'get list of intervals aligned to this slice according to groupBy options'
    seqIntervals=self.groupByIntervals(mergeAll=mergeAll,**kwargs)
    ivals=self.groupBySequences(seqIntervals,**kwargs)
    l=[]
    for ival1,ival2,mergeIntervals in ivals:
      l.append(ival2)
    return l
  def __iter__(self): # PYREX DOESNT ALLOW ARGS TO __iter__ !
    return iter(self.keys())
  def __getitem__(self,k):
    return sequence.Seq2SeqEdge(self,k)
  def __setitem__(self,k,v):
    raise ValueError('''this NLMSA is read-only!  Currently, you cannot add new
alignment intervals to an NLMSA after calling its build() method.''')
  def __len__(self):
    return self.nrealseq # NUMBER OF NON-LPO SEQUENCE/ORIS ALIGNED HERE


  ##################################### 1:1 INTERVAL METHODS
  def matchIntervals(self,seq=None):
    '''get all 1:1 match intervals in this region of alignment
    as list of tuples.  if seq argument not None, only match intervals
    for that sequence will be included.  No clipping is performed.'''
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    if seq is not None:
      target_id=nl.seqs.getID(seq) # CHECK IF IN OUR ALIGNMENT
    else:
      target_id= -1
    l=[]
    for i in range(self.n): # GET ALL STORED INTERVALS
      if not nl.seqlist.is_lpo(self.im[i].target_id) and \
               (target_id<0 or self.im[i].target_id==target_id):
        ival2=nl.seqInterval(self.im[i].target_id,self.im[i].target_start,
                             self.im[i].target_end)
        if seq is None or ival2.orientation==seq.orientation:
          ival1=sequence.absoluteSlice(self.seq,
                                       self.im[i].start,self.im[i].end)
          l.append((ival1,ival2)) # SAVE THE INTERVAL MATCH
    return l

  ############################## MAXIMUM INTERVAL METHODS
  def findSeqBounds(self, id, ori):
    'find the specified sequence / orientation using binary search'
    left=0
    right=self.nseqBounds
    while left<right:
      mid=(left+right)/2
      if self.seqBounds[mid].target_id<id:
        left=mid+1
      elif self.seqBounds[mid].target_id>id:
        right=mid
      elif ori>0 and seqBounds[mid].target_start<0:
        left=mid+1
      elif ori<0 and seqBounds[mid].target_start>=0:
        right=mid
      else: # MATCHES BOTH id AND ori
        return mid
    return -1 # FAILED TO FIND id,ori MATCH
  
  def findSeqEnds(self,seq):
    'get maximum interval of seq aligned in this interval'
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    id=nl.seqs.getID(seq) # CHECK IF IN OUR ALIGNMENT
    i=self.findSeqBounds(id,seq.orientation) # FIND THIS id,ORIENTATION
    if i<0: # NOT FOUND!
      raise KeyError('seq not aligned in this interval')
    return nl.seqInterval(self.seqBounds[i].target_id,
                          self.seqBounds[i].target_start,
                          self.seqBounds[i].target_end)

  def generateSeqEnds(self):
    'get list of tuples (ival1,ival2,edge)'
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i in range(self.nseqBounds):
      if nl.seqlist.is_lpo(self.seqBounds[i].target_id):
        continue  # DON'T RETURN EDGES TO LPO
      #ival1=sequence.absoluteSlice(self.seq,self.seqBounds[i].start,
      #                             self.seqBounds[i].end)
      ival2=nl.seqInterval(self.seqBounds[i].target_id,
                           self.seqBounds[i].target_start,
                           self.seqBounds[i].target_end)
      #l.append((ival1,ival2,sequence.Seq2SeqEdge(self,ival2,ival1)))
      edge = self[ival2] # LET edge FIGURE OUT sourcePath FOR US
      l.append((edge.sourcePath,ival2,edge))
    return l

  ############################################## GROUP-BY METHODS
  def groupByIntervals(self, maxgap=0, maxinsert=0,
                       mininsert= 0,filterSeqs=None,filterList=None,
                       mergeMost=False,maxsize=500000000,
                       mergeAll=True,ivalMethod=None,**kwargs):
    '''merge alignment intervals using "horizontal" group-by rules:
      - maxgap (=0): longest gap allowed within a region
      - maxinsert (=0): longest insert allowed within a region
      - mininsert (=0): should be 0, to prevent cycles within a region
        use negative values to allow some overlap / cycles.
      - maxsize: upper bound on maximum size for interval merging
      - mergeMost: merge, but with limits (10000,10000,-10,50000)
      - mergeAll: merge everything without any limits
      - filterSeqs (=None): dict of sequences to apply these rules to;
        other sequences alignment will be ignored if
        filterSeqs not None.  Slower than the filterList option.
      - filterList (=None): list of sequence intervals to mask the
        result set by.  Note: a single sequence should not be
        represented by more than one interval in filterList, as only
        one interval for each sequence will be used as the clipping region.
        Significantly faster than filterSeqs.
      - ivalMethod: a function to process the list of intervals
        for each sequence (it can merge or split them in any way
        it wants)
      - pAlignedMin: a fractional minimum alignment threshold e.g. (0.9)
      - pIdentityMin: a fractional minimum identity threshold e.g. (0.9)
      '''
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    if mergeMost: # BE REASONABLE: DON'T MERGE A WHOLE CHROMOSOME
      maxgap=10000
      maxinsert=10000
      mininsert=-10 # ALLOW SOME OVERLAP IN INTERVAL ALIGNMENTS
      maxsize=50000
    if filterList is not None:
      targetDict = {}
      for seq in filterList: # CREATE AN INDEX OF SEQUENCE IDs TO KEEP
        t = nl.seqs.getIDcoords(seq)
        targetDict[t[0]] = t[1:] # SAVE START,STOP
    seqIntervals={}
    for i in range(self.n): # LIST INTERVALS FOR EACH TARGET
      if nl.seqlist.is_lpo(self.im[i].target_id):
        continue # IT IS AN LPO, SO SKIP IT
      start=self.im[i].start
      end=self.im[i].end
      targetStart=self.im[i].target_start
      targetEnd=self.im[i].target_end
      if filterList is not None:
        try: # CHECK IF SEQUENCE IS IN MASKING DICTIONARY
          maskStart,maskEnd = targetDict[self.im[i].target_id]
        except KeyError:
          continue # FILTER THIS SEQUENCE OUT OF THE RESULT SET
        if start>=maskEnd or end<=maskStart: # NO OVERLAP
          continue
        if start<maskStart: # CLIP START TO MASKED REGION
          targetStart = targetStart+maskStart-start
          start = maskStart
        if end>maskEnd:# CLIP END TO MASKED REGION
          targetEnd = targetEnd+maskEnd-end
          end = MaskEnd
      elif filterSeqs is not None: # CLIP TARGET SEQ INTERVAL
        target=nl.seqInterval(self.im[i].target_id,targetStart,targetEnd)
        try:
          target=filterSeqs[target] # PERFORM CLIPPING
        except KeyError: # NO OVERLAP IN filterSeqs, SO SKIP
          continue
        start=start+target.start-targetStart # CLIP SOURCE SEQUENCE
        end=end+target.stop-targetEnd
        targetStart=target.start  # GET COORDS OF CLIPPED TARGET
        targetEnd=target.stop
      try: # ADD INTERVAL TO EXISTING LIST
        seqIntervals[self.im[i].target_id] \
             .append([start,end,targetStart,targetEnd,None])
      except KeyError: # CREATE A NEW LIST FOR THIS TARGET
        seqIntervals[self.im[i].target_id]= \
           [[start,end,targetStart,targetEnd,None]]

    for i,l in seqIntervals.iteritems(): # MERGE INTERVALS FOR EACH SEQ
      if ivalMethod is not None: # USER-SUPPLIED GROUPING FUNCTION
        ivalMethod(l,nl.seqlist.getSeq(i),msaSlice=self,maxgap=maxgap,
                   maxinsert=maxinsert,mininsert=mininsert,
                   filterSeqs=filterSeqs,mergeAll=mergeAll,**kwargs)
        continue # NO NEED TO APPLY GENERIC MERGING OPERATION BELOW
      n=0
      for j in range(len(l)): # MERGE BY INDEL LENGTH RULES
        gap=l[j][0]-l[n][1] # current.start - last.end
        insert=l[j][2]-l[n][3] # current.target_start - last.target_end
        if not mergeAll and \
               (gap>maxgap or insert>maxinsert or insert<mininsert
                or l[j][1]-l[n][0]>maxsize
                or l[j][3]-l[n][2]>maxsize):
          n=n+1 # SPLIT, SO START A NEW INTERVAL
          if n<j: # COPY START COORDS TO NEW SLOT
            l[n][0]=l[j][0]
            l[n][2]=l[j][2]
        else: # INTERVALS MERGED: SAVE ORIGINAL 1:1 INTERVAL LIST
          try:
            lastIval = l[n][4][-1] # GET LAST 1:1 INTERVAL
          except TypeError: # EMPTY LIST: CREATE ONE
            if l[n][1]==l[j][0] and l[n][3]==l[j][2]: # NO GAP, SO MERGE
              l[n][4] = [(l[n][0],l[j][1],l[n][2],l[j][3])]
            else: # TWO SEPARATE 1:1 INTERVALS
              l[n][4] = [tuple(l[n][:4]),tuple(l[j][:4])]
          else: # SEE IF WE CAN FUSE TO LAST 1:1 INTERVAL
            if lastIval[1]==l[j][0] and lastIval[3]==l[j][2]:
              l[n][4][-1] = (lastIval[0],l[j][1],lastIval[2],l[j][3])
            else: # GAP, SO JUST APPEND THIS 1:1 INTERVAL
              l[n][4].append(tuple(l[j][:4]))
        if n<j: # COPY END COORDS TO CURRENT SLOT
          l[n][1]=l[j][1]
          l[n][3]=l[j][3]
      del l[n+1:] # DELETE REMAINING UNMERGED INTERVALS
      for m in l: # CULL SINGLETON 1:1 INTERVAL LISTS (DUE TO FUSION)
        try:
          if len(m[4])==1: # TWO INTERVALS MUST HAVE BEEN FUSED
            m[4] = None # NO NEED TO KEEP SINGLETON!
        except TypeError:
          pass
    # SEQUENCE MASKING BY CONSERVATION OR %ALIGNED CONSTRAINT
    if 'pAlignedMin' in kwargs or 'pIdentityMin' in kwargs or \
           'minAlignSize' in kwargs or 'maxAlignSize' in kwargs:
      self.filterIvalConservation(seqIntervals,**kwargs)
    return seqIntervals

  def conservationFilter(self,seq,m,pIdentityMin=None,
                         minAlignSize=None,maxAlignSize=None,**kwargs):
    if minAlignSize is not None and m[1]-m[0]<minAlignSize:
      return None
    if maxAlignSize is not None and m[1]-m[0]>maxAlignSize:
      return None
    if pIdentityMin is not None:
      seqEdge=sequence.Seq2SeqEdge(self,sequence.relativeSlice(seq,m[2],m[3]),
                                   sequence.absoluteSlice(self.seq,m[0],m[1]),m[4])
      t = seqEdge.conservedSegment(pIdentityMin=pIdentityMin, # GET CLIPPED INTERVAL
                                   minAlignSize=minAlignSize,**kwargs)
      if t is None:
        return None
      mergeIntervals = self.clip_interval_list(t[0],t[1],m[4]) # CLIP mergeIntervals
      return list(t)+[mergeIntervals] # RECOMBINE
    else:
      return m
##     if pAlignedMin is not None and seqEdge.pAligned()<pAlignedMin:
##       return False # INTERVAL FAILED ALIGNMENT THRESHOLD, SO REMOVE IT
##     if pIdentityMin is not None and seqEdge.pIdentity()<pIdentityMin:
##       return False # INTERVAL FAILED CONSERVATION THRESHOLD, SO REMOVE IT
##     return True

  def filterIvalConservation(self,seqIntervals,pIdentityMin=None,
                             filterFun=None,**kwargs):
    import types
    if filterFun is None:
      filterFun=self.conservationFilter
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    pIdentityMin0=pIdentityMin
    for targetID,l in seqIntervals.items(): # MERGE INTERVALS FOR EACH SEQ
      seq=nl.seqlist.getSeq(targetID) # GET THE SEQUENCE OBJECT
      if pIdentityMin0 is not None and not isinstance(pIdentityMin0,types.FloatType):
        try:
          pIdentityMin=pIdentityMin0[seq] # LOOK UP DESIRED IDENTITY FOR THIS SEQ
        except KeyError:
          del seqIntervals[targetID] # SO REMOVE TARGET ENTIRELY
          continue # NO NEED TO PROCESS THIS TARGET ANY FURTHER
      j=0
      for i in range(len(l)): # CHECK EACH INTERVAL FOR CONSERVATION THRESHOLD
        newIval=filterFun(seq,l[i],pIdentityMin=pIdentityMin,**kwargs)
        if newIval is None:
          continue # l[i] FAILED FILTER CRITERIA, SO SKIP IT
        l[j]=newIval # COMPACT THE ARRAY: KEEP newIval IN LOCATION j
        j=j+1 # KEEP THIS ARRAY ENTRY, SO INCREMENT COUNT OF ENTRIES
      if j==0: # NO INTERVALS FOR THIS SEQUENCE SURVIVED MASKING
        del seqIntervals[targetID] # SO REMOVE TARGET ENTIRELY
      elif j<i: # SOME INTERVALS REMOVED, SO SHRINK ITS LIST
        del l[j:] # JUST TRUNCATE THE LIST TO ENTRIES THAT PASSED

  def groupBySequences(self,seqIntervals,sourceOnly=False,
                       indelCut=False,seqGroups=None,minAligned=1,
                       pMinAligned=0.,seqMethod=None,**kwargs):
    '''merge groups of sequences using "vertical" group-by rules:
    - seqGroups: a list of one or more lists of sequences to group.
      Each group will be analyzed separately, as follows:
    - sourceOnly: output intervals will be reported giving only
      the corresponding interval on the source sequence; redundant
      output intervals (mapping to the same source interval) are
      culled.  Has the effect of giving a single interval traversal
      of each group.
    - indelCut: for sourceOnly mode, do not merge separate 
      intervals as reported by seqIntervals (in other words,
      that the groupByIntervals analysis separated due to an indel).
    - minAligned: the minimum #sequences that must be aligned to
      the source sequence for masking the output.  Regions below
      this threshold are masked out; no intervals will be reported
      in these regions.
    - pMinAligned: the minimum fraction of sequences (out of the
      total in the group) that must be aligned to the source
      sequence for masking the output.
    - seqMethod: you may supply your own function for grouping.
      Called as seqMethod(bounds,seqs,**kwargs), where
      bounds is a sorted list of
      (ipos,isStart,i,ns,isIndel,(start,end,targetStart,targetEnd))
      seqs is a list of sequences in the group.
      Must return a list of (sourceIval,targetIval).  See the docs.
    '''
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    if seqGroups is None:
      seqGroups=[seqIntervals] # JUST USE THE WHOLE SET
    result=[]
    import mapping # GET ACCESS TO DictQueue CLASS
    for seqs in seqGroups: # PROCESS EACH SEQ GROUP
      bounds=[]
      j=0
      for seq in seqs: # CONSTRUCT INTERVAL BOUNDS LIST
        if isinstance(seq,int): # seqIntervals USES INT INDEX VALUES
          id=seq # SAVE THE ID
          seq=nl.seqlist.getSeq(id) # GET THE SEQUENCE OBJECT
        else: # EXPECT USER TO SUPPLY ACTUAL SEQUENCE OBJECTS
          id=nl.seqs.getID(seq)
          seq=seq.pathForward # ENSURE WE HAVE TOP-LEVEL SEQ OBJECT
        try:
          ivals=seqIntervals[id]
        except KeyError: # SEQUENCE NOT IN THIS ALIGNMENT REGION, SO SKIP
          continue
        isIndel=False
        for ival in ivals:
          bounds.append((ival[1],False,j,seq,isIndel,ival))
          bounds.append((ival[0],True,j,seq,isIndel,ival))
          isIndel=True
        j=j+1 # SEQUENCE COUNTER ENSURES ORDER OF SEQS IN SORTED LIST
      bounds.sort() # ASCENDING ORDER OF source_pos, SORT stop B4 start
      if seqMethod is not None:
        result=result+seqMethod(bounds,seqs,sourceOnly=sourceOnly,
                                msaSlice=self,minAligned=minAligned,
                                pMinAligned=pMinAligned,
                                indelCut=indelCut,**kwargs)
        continue # DON'T USE GENERIC GROUPING METHOD BELOW
      seqStart=mapping.DictQueue() # setitem PUSHES, delitem POPS
      maskStart=None
      for bound in bounds: # GENERIC GROUPING: APPLY MASKING, sourceOnly
        ipos,isStart,j,seq,isIndel=bound[0:5]
        if isStart: # INTERVAL START
          seqStart[seq]=bound[5] # JUST RECORD START OF INTERVAL
        else: # INTERVAL STOP
          start,end,targetStart,targetEnd,mergeIntervals=bound[5]
          if maskStart is not None and not sourceOnly: # SAVE TARGET IVAL
            if maskStart>start: # TRUNCATE TARGET IVAL START
              targetStart=targetStart+maskStart-start
              start=maskStart
              mergeIntervals = self.clip_interval_list(maskStart,None,mergeIntervals)
            result.append((sequence.absoluteSlice(self.seq,start,end),
                           sequence.relativeSlice(seq,targetStart,
                                                  targetEnd),mergeIntervals))
          del seqStart[seq] # POP THIS SEQ FROM START DICT

        f=len(seqStart) # #ALIGNED SEQS IN THIS REGION
        if f<minAligned or f/len(seqs)<pMinAligned: # APPLY MASKING
          if maskStart is not None:
            if sourceOnly: # JUST SAVE MERGED SOURCE INTERVAL
              result.append(sequence.absoluteSlice(self.seq,maskStart,end))
            else: # REPORT TARGET IVALS WITHIN (maskStart,end) REGION
              for seq in seqStart: # CANNOT USE items() BECAUSE THIS IS A QUEUE!
                (start,i,targetStart,targetEnd,mergeIntervals)=seqStart[seq]
                pleaseClip = False
                if maskStart>start: # TRUNCATE TARGET IVAL START
                  targetStart=targetStart+maskStart-start
                  start=maskStart
                  pleaseClip = True
                if end<i: # TRUNCATE TARGET IVAL END
                  targetEnd=targetEnd+end-i
                  pleaseClip = True
                if pleaseClip:
                  mergeIntervals = self.clip_interval_list(maskStart,end,mergeIntervals)
                result.append((sequence.absoluteSlice(self.seq,start,end),
                               sequence.relativeSlice(seq,targetStart,
                                                      targetEnd),mergeIntervals))
            maskStart=None # REGION NOW BELOW THRESHOLD
        elif maskStart is None:
          maskStart=ipos # START OF REGION ABOVE THRESHOLD
        if maskStart is not None and sourceOnly and indelCut \
               and isIndel and maskStart<ipos:
          result.append(sequence.absoluteSlice(self.seq,maskStart,ipos))
          maskStart=ipos
    return result
  def clip_interval_list(self,start,end,l):
    'truncate list of 1:1 intervals using start,end'
    if l is None:
      return None
    result = []
    for srcStart,srcEnd,destStart,destEnd in l:
      if (start is not None and start>=srcEnd) or (end is not None and end<=srcStart):
        continue
      if start is not None and start>srcStart:
        destStart = destStart+start-srcStart
        srcStart = start
      if end is not None and end<srcEnd:
        destEnd = destEnd+end-srcEnd
        srcEnd = end
      result.append((srcStart,srcEnd,destStart,destEnd))
    if len(result)<2:
      return None
    else:
      return result

  ############################################## LPO REGION METHODS
  def split(self,minAligned=0,**kwargs):
    '''Use groupByIntervals() and groupBySequences() methods to
    divide this slice into subslices using indel rules etc.'''
    seqIntervals=self.groupByIntervals(**kwargs)
    kwargs['sourceOnly']=True
    kwargs['indelCut']=True
    ivals=self.groupBySequences(seqIntervals,minAligned=minAligned,
                                **kwargs)
    l=[]
    for ival in ivals:
      if ival.start==self.start and ival.stop==self.stop:
        l.append(self) # SAME INTERVAL, SO JUST RETURN self
      else:
        subslice=NLMSASlice(self.nlmsaSequence,ival.start,ival.stop,
                            self.id,self.offset,self.seq)
        l.append(subslice)
    return l
            
      
  def regions(self,dummyArg=None,**kwargs):
    '''get LPO region(s) corresponding to this interval
    Same group-by rules apply here as for the split() method.'''
    if self.nlmsaSequence.is_lpo: # ALREADY AN LPO REGION!
      return self.split(**kwargs) # JUST APPLY GROUP-BY RULES TO  self
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i in range(self.nseqBounds):
      ns_lpo=nl.seqlist[self.seqBounds[i].target_id]
      if ns_lpo.is_lpo: # ADD ALL LPO INTERVALS ALIGNED HERE
        subslice=NLMSASlice(ns_lpo,self.seqBounds[i].target_start,
                            self.seqBounds[i].target_end)
        l=l+subslice.split(**kwargs) # APPLY GROUP-BY RULES
    if len(l)>0:
      return l
    raise ValueError('no LPO in nlmsaSlice.seqBounds?  Debug!')

  def __cmp__(self,other):
    if isinstance(other,NLMSASlice):
      return cmp(self.nlmsaSequence,other.nlmsaSequence)
    else:
      return -1

  def rawIvals(self):
    'return list of raw numeric intervals in this slice'
    l=[]
    for i in range(self.n):
      l.append((self.im[i].start,self.im[i].end,self.im[i].target_id,
                self.im[i].target_start,self.im[i].target_end))
    return l





class NLMSASequence(object):
  'sequence interface to NLMSA storage of an LPO alignment'
  def __init__(self,nl,filestem,seq,mode='r',is_union=0,length=None):
    self.nlmsaLetters=nl
    self.filestem=filestem
    self.is_union=is_union
    self.is_lpo=0 # DEFAULT: NOT AN LPO
    self.seq=seq
    if length is not None: # ALLOW USER TO SUPPLY A LENGTH FOR THIS COORD SYSTEM
      self.length=length
    import types
    if isinstance(seq,types.StringType):
      self.name=seq # ALLOW USER TO BUILD INDEXES WITH A STRING NAME
    elif seq is not None: # REGULAR SEQUENCE
      seq= seq.pathForward # GET THE WHOLE SEQUENCE, IN FORWARD ORIENTATION
      try: # MAKE SURE seq HAS A UNIQUE NAME FOR INDEXING IT...
        self.name=str(seq.path.name)
      except AttributeError:
        try:
          self.name=str(seq.path.id)
        except AttributeError:
          raise AttributeError('NLMSASequence: seq must have name or id attribute')
    else:
      self.length=0 # LPO AND UNION SEQUENCES EXPAND AUTOMATICALLY
      if not is_union:
        self.is_lpo=1
        if len(nl.lpoList)>0:  # CALCULATE OFFSET OF NEW LPO, BASED ON LAST LPO
          lastLPO=nl.lpoList[-1]
          self.offset=lastLPO.offset+lastLPO.length
        else:
          self.offset=0
        nl.lpoList.append(self) # ADD TO THE LPO LIST
    self.idb=None # DEFAULT: NOT USING IN-MEMORY DATABASE.
    self.db=None # DEFAULT: WAIT TO OPEN DB UNTIL ACTUALLY NEEDED
    if mode=='r': # IMMEDIATELY OPEN DATABASE, UNLIKE onDemand MODE
      self.db=IntervalFileDB(filestem,mode)
    elif mode=='memory': # OPEN IN-MEMORY DATABASE
      self.idb=IntervalDB()
    elif mode=='w': # WRITE .build FILE
      filename=filestem+'.build'
      self.build_ifile=fopen(filename,'w')
      if self.build_ifile==NULL:
        errmsg='unable to open in write mode: '+filename
        raise IOError(errmsg)
      self.nbuild=0

  def forceLoad(self):
    'force database to be initialized, if not already open'
    self.db=IntervalFileDB(self.filestem,'r')

  def close(self):
    'free memory and close files associated with this sequence index'
    if self.db is not None:
      self.db.close() # CLOSE THE DATABASE, RELEASE MEMORY
      self.db=None # DISCONNECT FROM DATABASE
    if self.idb is not None:
      self.idb.close() # CLOSE THE DATABASE, RELEASE MEMORY
      self.idb=None # DISCONNECT FROM DATABASE
    if self.build_ifile:
      fclose(self.build_ifile)
      self.build_ifile=NULL

  def buildFiles(self,**kwargs):
    'build nested list from saved unsorted alignment data'
    if self.build_ifile==NULL:
      raise IOError('not opened in write mode')
    fclose(self.build_ifile)
    self.build_ifile=NULL
    filename=self.filestem+'.build'
    db=IntervalDB() # CREATE EMPTY NL IN MEMORY
    if self.nbuild>0:
      db.buildFromUnsortedFile(filename,self.nbuild,**kwargs) # BUILD FROM .build
    db.write_binaries(self.filestem) # SAVE AS IntervalDBFile
    db.close() # DUMP NESTEDLIST FROM MEMORY
    import os
    os.remove(filename) # REMOVE OUR .build FILE, NO LONGER NEEDED
    self.db=IntervalFileDB(self.filestem) # NOW OPEN THE IntervalFileDB

  def buildInMemory(self,verbose=False,**kwargs):
    if self.buildList is not None:
      self.idb.save_tuples(self.buildList,**kwargs)
    self.buildList=None

  def __getitem__(self,k):
    try:
      if k.pathForward is self.seq:
        return NLMSASlice(self,k.start,k.stop)
    except AttributeError: pass
    raise KeyError('key must be a sequence interval of this sequence')

  def __len__(self):
    'call len(self.seq) if we have a seq.  Otherwise self.length'
    if self.seq is None:
      return self.length
    else:
      return len(self.seq)

  def __iadd__(self,seq):
    'add sequence to our union'
    try: # CHECK WHETHER THIS IS ALREADY IN THE INDEX
      x=self.nlmsaLetters.seqs[seq]
      return self # ALREADY IN THE INDEX, NO NEED TO ANYTHING
    except KeyError: # OK, WE REALLY DO NEED TO ADD IT...
      pass
    # CHECK FOR OVERFLOW... CREATE A NEW UNION IF NEEDED
    seq=seq.pathForward # GET THE ENTIRE SEQUENCE
    if self.length+len(seq)>self.nlmsaLetters.maxlen: # TOO BIG!
      if self.nlmsaLetters.pairwiseMode: # NEED TO CREATE CORRESPONDING LPO
        ns=self.nlmsaLetters.newSequence(None) # CREATE NEW LPO
      ns=self.nlmsaLetters.newSequence(None,is_union=1) # NEW UNION
      ns.__iadd__(seq) # ADD seq TO BRAND-NEW UNION
      return ns # RETURN THE NEW UNION COORDINATE SYSTEM
    # USE OUR EXISTING UNION
    self.nlmsaLetters.seqs.saveSeq(seq,self.id,self.length)
    self.length=self.length+len(seq) # EXPAND COORDINATE SYSTEM
    return self # iadd MUST ALWAYS RETURN self!!!






class NLMSA(object):
  'toplevel interface to NLMSA storage of an LPO alignment'
  def __init__(self,pathstem='',mode='r',seqDict=None,mafFiles=None,axtFiles=None,
               maxOpenFiles=1024,maxlen=None,nPad=1000000,maxint=41666666,
               trypath=None,bidirectional=True,pairwiseMode= -1,
               bidirectionalRule=nlmsa_utils.prune_self_mappings,
               use_virtual_lpo=None,maxLPOcoord=None,**kwargs):
    self.lpoList=[] # EMPTY LIST OF LPO
    self.seqs=nlmsa_utils.NLMSASeqDict(self,pathstem,mode,**kwargs)
    self.seqlist=self.seqs.seqlist
    self.pathstem=pathstem
    if maxlen is None:
      import sys
      maxlen=sys.maxint-65536 # C_int_max MAXIMUM VALUE REPRESENTABLE BY int
      if axtFiles is not None:
        maxlen = maxlen/2
    self.maxlen=maxlen
    self.inlmsa=nPad
    self._ignoreShadowAttr={'sourceDB':None,'targetDB':None} # SCHEMA INFO
    self.seqDict=seqDict # SAVE FOR USER TO ACCESS...
    self.in_memory_mode=0
    if bidirectional:
      self.is_bidirectional=1
    else:
      self.is_bidirectional=0
    if use_virtual_lpo is not None: # DEPRECATED: MUST HAVE COME FROM PICKLE...
      pairwiseMode = use_virtual_lpo # USE SETTING FROM PICKLE...
    if pairwiseMode is True:
      self.pairwiseMode=1
    elif pairwiseMode is False:
      self.pairwiseMode=0
    else:
      self.pairwiseMode=pairwiseMode
    if maxLPOcoord is not None: # SIZE OF THE ENTIRE LPO COORD SYSTEM
      self.maxLPOcoord=maxLPOcoord
      if self.pairwiseMode==1:
        raise ValueError('maxLPOcoord and pairwiseMode options incompatible!')
      self.pairwiseMode=0
    else: # DEFAULT: RESTRICT USER TO A SINGLE LPO
      self.maxLPOcoord=self.maxlen
    if mode=='r': # OPEN FROM DISK FILES
      if self.seqDict is None:
        self.seqDict = nlmsa_utils.read_seq_dict(pathstem,trypath)
      self.read_indexes(self.seqDict)
      self.read_attrs()
    elif mode=='w': # WRITE TO DISK FILES
      self.do_build=1
      self.lpo_id=0
      if mafFiles is not None:
        self.newSequence() # CREATE INITIAL LPO
        self.readMAFfiles(mafFiles,maxint)
      elif axtFiles is not None:
        self.newSequence() # CREATE INITIAL LPO
        self.readAxtNet(axtFiles,bidirectionalRule)
      else: # USER WILL ADD INTERVAL MAPPINGS HIMSELF...
        if self.seqDict is None:
          import seqdb
          self.seqDict=seqdb.SeqPrefixUnionDict(addAll=True)
        self.initLPO() # CREATE AS MANY LPOs AS WE NEED
        self.newSequence(is_union=1) # SO HE NEEDS AN INITIAL UNION
    elif mode=='memory': # CONSTRUCT IN-MEMORY
      if self.seqDict is None:
        import seqdb
        self.seqDict=seqdb.SeqPrefixUnionDict(addAll=True)
      self.in_memory_mode=1
      self.do_build=1
      self.initLPO() # CREATE AS MANY LPOs AS WE NEED
      self.newSequence(is_union=1) # CREATE INITIAL UNION
      self.lpo_id=0
    elif mode!='xmlrpc':
      raise ValueError('unknown mode %s' % mode)

  def __reduce__(self): ############################# SUPPORT FOR PICKLING
    import seqdb
    return (seqdb.ClassicUnpickler, (self.__class__,self.__getstate__()))
  def __getstate__(self):
    if self.in_memory_mode:
      raise ValueError("can't pickle NLMSA.in_memory_mode")
    return dict(pathstem=self.pathstem,seqDict=self.seqDict)
  def __setstate__(self,state):
    self.__init__(**state) #JUST PASS KWARGS TO CONSTRUCTOR

  def read_indexes(self,seqDict):
    'open all nestedlist indexes in this LPO database for immediate use'
    try:
      ifile=file(self.pathstem+'.NLMSAindex')
    except IOError:
      ifile=file(self.pathstem+'NLMSAindex') # FOR BACKWARDS COMPATIBILITY
    try:
      for line in ifile:
        id,name,is_union,length=line.strip().split('\t')
        id=int(id)
        is_union=int(is_union)
        if id!=len(self.seqlist):
          raise IOError('corrupted NLMSAIndex???')
        filestem=self.pathstem+str(id)
        seq=None # DEFAULT: NO ACTUAL SEQUENCE ASSOCIATED WITH LPO OR UNION
        if name=='NLMSA_LPO_Internal': # AN LPO REFERENCE
          self.lpo_id=id
        elif not is_union: # REGULAR SEQUENCE
          try:
            seq=seqDict[name]
          except KeyError:
            raise KeyError('unable to find sequence %s in seqDict!' % name)
        # CREATE THE SEQ INTERFACE, BUT DELAY OPENING THE IntervalDBFile
        ns=NLMSASequence(self,filestem,seq,'onDemand',is_union) # UNTIL NEEDED
        ns.length=int(length) # SAVE STORED LENGTH
        self.addToSeqlist(ns,seq)
    finally:
      ifile.close()
  def read_attrs(self):
    'read pickled attribute dictionary from file and apply to self'
    import pickle
    try:
      ifile = file(self.pathstem+'.attrDict')
    except IOError: # BACKWARDS COMPATIBILITY: OLD NLMSA HAS NOT ATTRDICT
      return
    try:
      d = pickle.load(ifile)
      for k,v in d.items():
        if k=='is_bidirectional':
          self.is_bidirectional = v
        elif k=='pairwiseMode':
          self.pairwiseMode = v
        else:
          setattr(self,k,v)
    finally:
      ifile.close()
  def addToSeqlist(self,ns,seq=None):
    'add an NLMSASequence to our seqlist, and set its id'
    ns.id=self.seqlist.nextID()
    self.seqs[seq]=ns # SAVE TO OUR INDEX
      
  def newSequence(self,seq=None,is_union=0):
    'create a new nestedlist index for sequence seq'
    id=self.seqlist.nextID() # USE ITS INDEX AS UNIQUE ID FOR THIS SEQUENCE
    if self.pairwiseMode==1 and is_union and id>1: # NEED A VIRTUAL_LPO FOR THIS UNION
      self.newSequence() # CREATE AN LPO
      id=self.seqlist.nextID() # NOW GET ID FOR THE UNION
    filestem=self.pathstem+str(id)
    if self.in_memory_mode:
      mode='memory'
    else:
      mode='w'
    ns=NLMSASequence(self,filestem,seq,mode,is_union=is_union) #OPEN FOR WRITING
    if is_union: # RECORD THIS AS OUR CURRENT UNION OBJECT
      self.currentUnion=ns
    self.addToSeqlist(ns,seq) # SAVE TO OUR INDEX
    #print 'Opened build file for ns_id',ns.id,ns.is_union
    return ns

  def nextID(self):
    'get a unique nlmsaID and advance counter'
    nlmsaID=self.inlmsa # USE THE NEXT FREE ID
    self.inlmsa=self.inlmsa+1 # ADVANCE THE COUNTER
    return nlmsaID
    
  def initLPO(self):
    'create LPOs for this alignment'
    offset=0
    while offset<self.maxLPOcoord:
      ns=self.newSequence() # CREATE AN LPO
      ns.offset=offset # FORCE OUR DESIRED OFFSET... EVEN THOUGH ALL LPOs EMPTY
      offset=offset+self.maxlen
  def init_pairwise_mode(self,verbose=False):
    'turn on use of virtual LPO mapping (i.e. no actual LPO is present!)'
    if self.pairwiseMode==0:
      raise ValueError('this alignment is already using an LPO!')
    elif self.pairwiseMode!=1 and verbose: # NOT ALREADY SET TO PAIRWISE MODE
      import sys
      sys.stderr.write('''
Because you are aligning a pair of sequence intervals,
the pairwiseMode=True option is automatically being applied.
To avoid this message in the future, pass the pairwiseMode=True
option to the NLMSA constructor.
See the NLMSA documentation for more details.\n''')
    self.pairwiseMode=1 # TURN ON THE VIRTUAL LPO FEATURE
    

  def __setitem__(self,k,v): # THIS METHOD EXISTS ONLY FOR nlmsa[s1]+=s2
    if isinstance(v,nlmsa_utils.BuildMSASlice):
      if v.seq is not None and v.seq==k: # CASE WHERE k IS A SEQ INTERVAL
        return # MATCHES += USAGE: NO NEED TO DO ANYTHING!
      elif v.is_lpo and isinstance(k,slice) \
               and k.start==v.start and k.stop==v.stop: # CASE: k IS A slice
        return # MATCHES += USAGE: NO NEED TO DO ANYTHING!
    raise KeyError('Usage only nlmsa[s1]+=s2 allowed. nlmsa[s1]=s2 forbidden!')
  def __getitem__(self,k):
    'return a slice of the LPO'
    if isinstance(k,sequence.SeqPath): # TREAT k AS A SEQUENCE INTERVAL
      id,ns,offset=self.seqs[k] # GET UNION INFO FOR THIS SEQ
      if self.do_build:
        return nlmsa_utils.BuildMSASlice(ns,k.start,k.stop,id,offset,0,k)
      else: # QUERY THE ALIGNMENT
        try:
          return NLMSASlice(ns,k.start,k.stop,id,offset,k)
        except nlmsa_utils.EmptySliceError:
          return nlmsa_utils.EmptySlice(k)
    try: # TREAT k AS A PYTHON SLICE OBJECT
      i=k.start
    except AttributeError:
      raise KeyError('key must be a sequence interval or python slice object')
    if self.do_build:
      return nlmsa_utils.BuildMSASlice(self.lpoList[0],k.start,k.stop,-1,0,1,None)
    else: # QUERY THE ALIGNMENT
      l=nlmsa_utils.splitLPOintervals(self.lpoList,k) # MAP TO LPO(S)
      if len(l)>1:
        raise ValueError('Sorry!  Query interval spans multiple LPOs!')
      for ns,myslice in l: # ONLY RETURN ONE SLICE OBJECT
          return NLMSASlice(ns,myslice.start,myslice.stop)

  def __iadd__(self,seq):
    'add seq to our union'
    self.seqs.saveSeq(seq)
    return self  # iadd MUST ALWAYS RETURN self!
  def addAnnotation(self,a):
    'save alignment of sequence interval --> an annotation object'
    ival = a.sequence # GET PURE SEQUENCE INTERVAL
    self.__iadd__(ival) # ADD SEQ AS A NODE IN OUR ALIGNMENT
    self[ival].__iadd__(a) # ADD ALIGNMENT BETWEEN ival AND ANNOTATION

  def seqInterval(self, iseq, istart, istop):
    'get specified interval in the target sequence'
    seq=self.seqlist.getSeq(iseq) # JUST THE SEQ OBJECT
    return sequence.relativeSlice(seq,istart,istop)




