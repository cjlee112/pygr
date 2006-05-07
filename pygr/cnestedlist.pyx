#from lpo import POMSANodeRef
import sequence

cdef class IntervalDBIterator:
  def __new__(self,int start,int end,IntervalDB db not None):
    self.it=interval_iterator_alloc()
    self.it_alloc=self.it
    self.start=start
    self.end=end
    self.db=db

  def __iter__(self):
    return self 

  cdef int cnext(self): # C VERSION OF ITERATOR next METHOD RETURNS INDEX
    cdef int i
    if self.ihit>=self.nhit: # TRY TO GET ONE MORE BUFFER CHUNK OF HITS
      if self.it==NULL: # ITERATOR IS EXHAUSTED
        return -1
      self.it=find_intervals(self.it,self.start,self.end,self.db.im,self.db.ntop,
                             self.db.subheader,self.db.nlists,self.im_buf,1024,
                             &(self.nhit)) # GET NEXT BUFFER CHUNK
      self.ihit=0 # START ITERATING FROM START OF BUFFER
    if self.ihit<self.nhit: # RETURN NEXT ITEM FROM BUFFER
      i=self.ihit
      self.ihit = self.ihit+1 # ADVANCE THE BUFFER COUNTER
      return i
    else: # BUFFER WAS EMPTY, NO HITS TO ITERATE OVER...
      return -1

  # PYTHON VERSION OF next RETURNS HIT AS A TUPLE
  def __next__(self): # PYREX USES THIS NON-STANDARD NAME INSTEAD OF next()!!!
    cdef int i
    i=self.cnext()
    if i>=0:
      return (self.im_buf[i].start,self.im_buf[i].end,self.im_buf[i].target_id,
              self.im_buf[i].target_start,self.im_buf[i].target_end)
    else:
      raise StopIteration

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    free_interval_iterator(self.it_alloc)




cdef class IntervalDB:
  def __new__(self,filename='noname',nsize=0):
    cdef int i
    cdef FILE *ifile
    self.n=nsize
    if nsize>0:
      ifile=fopen(filename,"r")
      if ifile:
        self.im=read_intervals(self.n,ifile)
        fclose(ifile)
        if self.im!=NULL:
          self.subheader=build_nested_list(self.im,self.n,
                                           &(self.ntop),&(self.nlists))
      else:
        msg='could not open file %s' % filename
        raise IOError(msg)

  def save_tuples(self,l):
    cdef int i
    self.close() # DUMP OUR EXISTING MEMORY 
    self.n=len(l)
    self.im=interval_map_alloc(self.n)
    if self.im==NULL:
      raise MemoryError('unable to allocate IntervalMap[%d]' % self.n)
    i=0
    for t in l:
      self.im[i].start=t[0]
      self.im[i].end=t[1]
      self.im[i].target_id=t[2]
      self.im[i].target_start=t[3]
      self.im[i].target_end=t[4]
      self.im[i].sublist= -1
      i=i+1
    self.subheader=build_nested_list(self.im,self.n,&(self.ntop),&(self.nlists))

  def buildFromUnsortedFile(self,filename,int n):
    'load unsorted binary data, and build nested list'
    cdef FILE *ifile
    cdef int i
    cdef IntervalMap *im_new
    self.close()
    ifile=fopen(filename,'r')
    if ifile==NULL:
      raise IOError('unable to open '+filename)
    im_new=interval_map_alloc(n)
    if im_new==NULL:
      raise MemoryError('unable to allocate IntervalMap[%d]' % n)
    i=read_imdiv(ifile,im_new,n,0,n)
    fclose(ifile)
    if i!=n:
      raise IOError('IntervalMap file corrupted?')
    self.n=n
    self.im=im_new
    self.subheader=build_nested_list(self.im,self.n,&(self.ntop),&(self.nlists))

  def find_overlap(self,int start,int end):
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    return IntervalDBIterator(start,end,self)

  def find_overlap_list(self,int start,int end):
    cdef int i,nhit
    cdef IntervalIterator *it,*it_alloc
    cdef IntervalMap im_buf[1024]
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    it=interval_iterator_alloc()
    it_alloc=it
    l=[] # LIST OF RESULTS TO HAND BACK
    while it:
      it=find_intervals(it,start,end,self.im,self.ntop,
                        self.subheader,self.nlists,im_buf,1024,
                        &(nhit)) # GET NEXT BUFFER CHUNK
      for i from 0 <= i < nhit:
        l.append((im_buf[i].start,im_buf[i].end,im_buf[i].target_id,im_buf[i].target_start,im_buf[i].target_end))
    free_interval_iterator(it_alloc)
    return l
        
  def check_nonempty(self):
    if self.im:
      return True
    else:
      msg='empty IntervalDB, not searchable!'
      raise IndexError(msg)

  def write_binaries(self,filestem,div=256):
    cdef char *err_msg
    err_msg=write_binary_files(self.im,self.n,self.ntop,div,
                               self.subheader,self.nlists,filestem)
    if err_msg:
      raise IOError(err_msg)

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.subheader:
      free(self.subheader)
    if self.im:
      free(self.im)
    
  def close(self):
    if self.subheader:
      free(self.subheader)
    if self.im:
      free(self.im)
    self.subheader=NULL
    self.im=NULL

    



cdef class IntervalFileDBIterator:
  def __new__(self,int start,int end,IntervalFileDB db=None,
              int nbuffer=1024):
    self.it=interval_iterator_alloc()
    self.it_alloc=self.it
    self.start=start
    self.end=end
    self.db=db
    self.im_buf=interval_map_alloc(nbuffer)
    self.nbuf=nbuffer

  cdef int restart(self,int start,int end,IntervalFileDB db) except -2:
    'reuse this iterator for another search without reallocing memory'
    self.nhit=0 # FLUSH ANY EXISTING DATA
    self.start=start
    self.end=end
    self.db=db
    return 0

  cdef int reset(self) except -2:
    'flush the buffer so we can reuse this iterator'
    self.nhit=0
    return 0

  cdef int extend(self,int ikeep):
    'expand the buffer if necessary, keeping elements [ikeep:nbuf]'
    cdef int len,istart
    cdef IntervalMap *new_buf
    istart=self.nbuf-ikeep
    len=sizeof(IntervalMap)*istart # #BYTES WE MUST KEEP
    if ikeep==0: # KEEPING THE WHOLE BUFFER, SO MUST ALLOCATE NEW SPACE
      new_buf=<IntervalMap *>realloc(self.im_buf,2*len) # DOUBLE OUR BUFFER
      if new_buf==NULL:
        raise MemoryError('out of memory')
      self.im_buf=new_buf
      self.nbuf=2*self.nbuf
    elif ikeep<8: # RUNNING OUT OF ROOM, SO EXPAND BUFFER
      self.nbuf=2*self.nbuf
      new_buf=interval_map_alloc(self.nbuf)
      memcpy(new_buf,self.im_buf+ikeep,len)
      free(self.im_buf)
      self.im_buf=new_buf
    else: # JUST SHIFT [ikeep:] SLICE OF BUFFER TO FRONT [0:istart]
      memmove(self.im_buf,self.im_buf+ikeep,len)
    return istart # RETURN START OF EMPTY BLOCK WHERE WE CAN ADD NEW DATA

  cdef int saveInterval(self,int start,int end,int target_id,
                        int target_start,int target_end):
    'save an interval, expanding array if necessary'
    cdef int i
    if self.nhit>=self.nbuf: # EXPAND ARRAY IF NECESSARY
      self.extend(0)
    i=self.nhit
    self.im_buf[i].start=start # SAVE INTERVAL INFO
    self.im_buf[i].end=end
    self.im_buf[i].target_id=target_id
    self.im_buf[i].target_start=target_start
    self.im_buf[i].target_end=target_end
    self.nhit = i+1
    return self.nhit

  cdef int nextBlock(self,int *pkeep) except -2:
    'load one more block of overlapping intervals'
    cdef int i
    if self.db is None:
      raise IOError('Iterator has no database!  Please provide a db argument.')
    if self.it==NULL: # ITERATOR IS EXHAUSTED
      return -1
    if pkeep and pkeep[0]>=0 and pkeep[0]<self.nhit: #MUST KEEP [ikeep:] SLICE
      i=self.extend(pkeep[0]) # MOVE SLICE TO THE FRONT
    else: # WE CAN USE THE WHOLE BUFFER
      i=0
    find_file_intervals(self.it,self.start,self.end,
                        self.db.db[0].ii,self.db.db[0].nii,
                        self.db.db[0].subheader,self.db.db[0].nlists,
                        &(self.db.db[0].subheader_file),
                        self.db.db[0].ntop,self.db.db[0].div,
                        self.db.db[0].ifile_idb,
                        self.im_buf+i,self.nbuf-i,
                        &(self.nhit),&(self.it)) # GET NEXT BUFFER CHUNK
    self.nhit=self.nhit+i # TOTAL #HITS IN THE BUFFER
    self.ihit=i # START ITERATING FROM START OF NEW HITS
    if pkeep and pkeep[0]>=0: # RESET ikeep INDEX TO START OF BUFFER
      pkeep[0]=0
    return self.nhit-self.ihit # RETURN #NEW HITS IN NEXT BLOCK

  cdef IntervalMap *getIntervalMap(self):
    '''return the IntervalMap array loaded by iterator,
    and release it from iterator.  User must free the array!'''
    cdef int len
    cdef IntervalMap *im
    if self.nhit==0: # NO HITS
      return NULL
    elif self.nhit<self.nbuf: # LARGER BUFFER THAN WE ACTUALLY NEED
      len=sizeof(IntervalMap)*self.nhit # COMPUTE FINAL SIZE
      im=<IntervalMap *>realloc(self.im_buf,len) # COMPACT TO FINAL SIZE
    else: # JUST HAND BACK OUR FULL BUFFER
      im=self.im_buf
    self.im_buf=NULL # RELEASE THIS STORAGE FROM ITERATOR; USER MUST FREE IT!
    return im # HAND BACK THE STORAGE

  cdef int loadAll(self) except -1:
    'load all overlapping interval hits, return count of hits'
    cdef int len,ikeep
    len=1
    ikeep=0 # DON'T LET extend DISCARD ANY HITS, KEEP THEM ALL!
    while len>0: # LOAD BLOCKS UNTIL NO MORE...
      len=self.nextBlock(&ikeep) # LOAD ANOTHER BLOCK OF INTERVALS
    return self.nhit

  cdef int cnext(self,int *pkeep): # C VERSION OF ITERATOR next METHOD
    'get one more overlapping interval'
    cdef int i
    if self.ihit>=self.nhit: # TRY TO GET ONE MORE BUFFER CHUNK OF HITS
      self.nextBlock(pkeep) # LOAD THE NEXT BLOCK IF ANY
    if self.ihit<self.nhit: # RETURN NEXT ITEM FROM BUFFER
      i=self.ihit
      self.ihit = self.ihit+1 # ADVANCE THE BUFFER COUNTER
      return i
    else: # BUFFER WAS EMPTY, NO HITS TO ITERATE OVER...
      return -1

  cdef int copy(self,IntervalFileDBIterator src):
    'copy items from src to this iterator buffer'
    cdef IntervalMap *new_buf
    if src is None:
      raise ValueError('src is None!  Debug!!')
    if src.nhit>self.nbuf: # NEED TO EXPAND OUR BUFFER
      new_buf=<IntervalMap *>realloc(self.im_buf,src.nhit*sizeof(IntervalMap))
      if new_buf==NULL:
        raise MemoryError('out of memory')
      self.im_buf=new_buf # RECORD NEW BUFFER LOCATION AND SIZE
      self.nbuf=src.nhit
    self.nhit=src.nhit # COPY ARRAY AND SET CORRECT SIZE
    if src.nhit>0: # ONLY COPY IF NON-EMPTY
      memcpy(self.im_buf,src.im_buf,src.nhit*sizeof(IntervalMap))
    return 0

  def mergeSeq(self):
    'merge intervals into single interval per sequence orientation'
    cdef int i,j,n,id
    if self.nhit<=0: # NOTHING TO MERGE, SO JUST RETURN
      return 0
    qsort(self.im_buf,self.nhit,sizeof(IntervalMap),target_qsort_cmp) # ORDER BY id,start
    n=0
    id= -1
    for i from 0 <= i < self.nhit:
      if self.im_buf[i].target_id!=id or (self.im_buf[j].target_start<0 and
                                          self.im_buf[i].target_start>=0):
        if id>=0: # WE NEED TO SAVE PREVIOUS INTERVAL
          if n<j: # COPY MERGED INTERVAL TO COMPACTED LOCATION
            memcpy(self.im_buf+n,self.im_buf+j,sizeof(IntervalMap))
          n=n+1
        j=i # RECORD THIS AS START OF THE NEW SEQUENCE / ORIENTATION
        id=self.im_buf[i].target_id
      elif self.im_buf[i].target_end>self.im_buf[j].target_end:
        self.im_buf[j].target_end=self.im_buf[i].target_end # EXPAND THIS INTERVAL
        self.im_buf[j].end=self.im_buf[i].end # COPY SOURCE SEQ COORDS AS WELL
    if n<j: # COPY LAST MERGED INTERVAL TO COMPACTED LOCATION
      memcpy(self.im_buf+n,self.im_buf+j,sizeof(IntervalMap))
    self.nhit=n+1 # TOTAL #MERGED INTERVALS
    return self.nhit

  def __iter__(self):
    return self

  # PYTHON VERSION OF next RETURNS HIT AS A TUPLE
  def __next__(self): # PYREX USES THIS NON-STANDARD NAME INSTEAD OF next()!!!
    cdef int i
    i=self.cnext(NULL)
    if i>=0:
      return (self.im_buf[i].start,self.im_buf[i].end,self.im_buf[i].target_id,
              self.im_buf[i].target_start,self.im_buf[i].target_end)
    else:
      raise StopIteration

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    free_interval_iterator(self.it_alloc)
    if self.im_buf:
      free(self.im_buf)




      
cdef class IntervalFileDB:
  def __new__(self,filestem=None,mode='r'):
    if filestem is not None and mode=='r':
      self.open(filestem)

  def open(self,filestem):
    cdef char err_msg[1024]
    self.db=read_binary_files(filestem,err_msg,1024)
    if self.db==NULL:
      raise IOError(err_msg)

  def find_overlap(self,int start,int end):
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    return IntervalFileDBIterator(start,end,self)

  def find_overlap_list(self,int start,int end):
    cdef int i,nhit
    cdef IntervalIterator *it,*it_alloc
    cdef IntervalMap im_buf[1024]
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    it=interval_iterator_alloc()
    it_alloc=it
    l=[] # LIST OF RESULTS TO HAND BACK
    while it:
      find_file_intervals(it,start,end,self.db[0].ii,self.db[0].nii,
                          self.db[0].subheader,self.db[0].nlists,
                          &(self.db[0].subheader_file),
                          self.db[0].ntop,self.db[0].div,
                          self.db[0].ifile_idb,im_buf,1024,
                          &(nhit),&(it)) # GET NEXT BUFFER CHUNK
      for i from 0 <= i < nhit:
        l.append((im_buf[i].start,im_buf[i].end,im_buf[i].target_id,
                  im_buf[i].target_start,im_buf[i].target_end))
    free_interval_iterator(it_alloc)
    return l

  def check_nonempty(self):
    if self.db==NULL:
      raise IndexError('empty IntervalFileDB, not searchable!')

  def close(self):
    if self.db:
      free_interval_dbfile(self.db)
    self.db=NULL

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.db:
      free_interval_dbfile(self.db)




cdef class NLMSASliceLetters:
  'graph interface to letter graph within this region'
  def __new__(self,NLMSASlice nlmsaSlice):
    self.nlmsaSlice=nlmsaSlice
  def __iter__(self):
    return NLMSASliceIterator(self.nlmsaSlice)
  def __getitem__(self,NLMSANode node):
    return node.nodeEdges()
  def items(self):
    'list of tuples (node,{target_node:edge})'
    l=[]
    for node in self:
      l.append((node,node.nodeEdges()))
    return l
  def iteritems(self):
    return iter(self.items())




cdef class NLMSASlice:
  def __new__(self,NLMSASequence ns not None,int start,int stop,
              int id= -1,int offset=0,seq=None):
    cdef int i,j,n,start_max,end_min,start2,stop2,nseq,istart,istop
    cdef NLMSASequence ns_lpo
    cdef IntervalFileDBIterator it,it2
    cdef IntervalMap *im,*im2

    if seq is None: # GET FROM NLMSASequence
      seq=ns.seq
    if id<0:
      id=ns.id
    self.nlmsaSequence=ns # SAVE BASIC INFO
    self.start=start
    self.stop=stop
    self.id=id
    self.offset=offset
    self.seq=seq
    if ns.db is None:
      ns.forceLoad()
    it2=None
    it=IntervalFileDBIterator(start+offset,stop+offset,ns.db)
    n=it.loadAll() # GET ALL OVERLAPPING INTERVALS
    if n<=0:
      raise KeyError('this interval is not aligned!')
    for i from 0 <= i < n: # CLIP INTERVALS TO FIT [start:stop]
      it.im_buf[i].start=it.im_buf[i].start-offset # XLATE TO SRC SEQ COORDS
      it.im_buf[i].end=it.im_buf[i].end-offset
      if stop<it.im_buf[i].end: # TRUNCATE TO FIT WITHIN [start:stop]
        it.im_buf[i].target_end= it.im_buf[i].target_end \
                                 +stop-it.im_buf[i].end # CALCULATE NEW ENDPOINT
        it.im_buf[i].end=stop
      if start>it.im_buf[i].start: # CALCULATE NEW STARTPOINT
        it.im_buf[i].target_start=it.im_buf[i].target_start \
                                 +start-it.im_buf[i].start
        it.im_buf[i].start=start
        
    if not ns.is_lpo: # TARGET INTERVALS MUST BE LPO, MUST MAP TO REAL SEQUENCES
      ns_lpo=ns.nlmsaLetters.seqlist[ns.nlmsaLetters.lpo_id] # DEFAULT LPO
      if ns_lpo.db is None:
        ns_lpo.forceLoad()
      for i from 0 <= i < n:
        if it.im_buf[i].target_id != ns_lpo.id: # SWITCHING TO A DIFFERENT LPO?
          ns_lpo=ns.nlmsaLetters.seqlist[it.im_buf[i].target_id]
          if not ns_lpo.is_lpo:
            raise ValueError('sequence mapped to non-LPO target??')
          if ns_lpo.db is None:
            ns_lpo.forceLoad()
        if it2 is None: # NEED TO ALLOCATE NEW ITERATOR
          it2=IntervalFileDBIterator(it.im_buf[i].target_start,
                                     it.im_buf[i].target_end,ns_lpo.db)
        else: # JUST REUSE THIS ITERATOR WITHOUT REALLOCING MEMORY
          it2.restart(it.im_buf[i].target_start,
                      it.im_buf[i].target_end,ns_lpo.db)
        it2.loadAll() # GET ALL OVERLAPPING INTERVALS
        if it2.nhit<=0: # NO HITS, SO TRY THE NEXT INTERVAL???
          continue
        im2=it2.im_buf # ARRAY FROM THIS ITERATOR
        for j from 0 <= j < it2.nhit: # MAP EACH INTERVAL BACK TO ns
          if im2[j].target_id==id: # DISCARD SELF-MATCH
            continue
          if it.im_buf[i].target_start>im2[j].start: # GET INTERSECTION INTERVAL
            start_max=it.im_buf[i].target_start
          else:
            start_max=im2[j].start
          if it.im_buf[i].target_end<im2[j].end:
            end_min=it.im_buf[i].target_end
          else:
            end_min=im2[j].end
          istart=it.im_buf[i].start+start_max-it.im_buf[i].target_start # SRC COORDS
          istop=it.im_buf[i].start+end_min-it.im_buf[i].target_start
          start2=im2[j].target_start+start_max-im2[j].start # COORDS IN TARGET
          stop2=im2[j].target_start+end_min-im2[j].start
          it.saveInterval(istart,istop,im2[j].target_id,start2,stop2) # SAVE IT!
          assert ns_lpo.id!=im2[j].target_id

    it2.copy(it) # COPY FULL SET OF SAVED INTERVALS
    self.nseqBounds=it2.mergeSeq() # MERGE TO ONE INTERVAL PER SEQUENCE ORIENTATION
    self.seqBounds=it2.getIntervalMap() # SAVE SORTED ARRAY & DETACH FROM ITERATOR

    self.im=it.getIntervalMap() # RELEASE THIS ARRAY FROM THE ITERATOR
    self.n=it.nhit # TOTAL #INTERVALS SAVED FROM JOIN
    qsort(self.im,self.n,sizeof(IntervalMap),imstart_qsort_cmp) # ORDER BY start

    n=0
    for i from 0 <= i < self.nseqBounds: # COUNT NON-LPO SEQUENCES
      if not ns.nlmsaLetters.seqlist.is_lpo(self.seqBounds[i].target_id):
        n=n+1
    self.nrealseq=n # SAVE THE COUNT

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.im:
      free(self.im)
      self.im=NULL
    if self.seqBounds:
      free(self.seqBounds)
      self.seqBounds=NULL


  ########################################### ITERATOR METHODS
  def edges(self,mergeAll=False,**kwargs):
    seqIntervals=self.groupByIntervals(mergeAll=mergeAll,**kwargs)
    ivals=self.groupBySequences(seqIntervals,**kwargs)
    l=[]
    for ival1,ival2 in ivals:
      l.append((ival1,ival2,sequence.Seq2SeqEdge(self,ival2,ival1)))
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
    seqIntervals=self.groupByIntervals(mergeAll=mergeAll,**kwargs)
    ivals=self.groupBySequences(seqIntervals,**kwargs)
    l=[]
    for ival1,ival2 in ivals:
      l.append(ival2)
    return l
  def __iter__(self): # PYREX DOESNT ALLOW ARGS TO __iter__ !
    return iter(self.keys())
  def __getitem__(self,k):
    return sequence.Seq2SeqEdge(self,k)
  def __len__(self):
    return self.nrealseq # NUMBER OF NON-LPO SEQUENCE/ORIS ALIGNED HERE


  ##################################### 1:1 INTERVAL METHODS
  def matchIntervals(self,seq=None):
    '''get all 1:1 match intervals in this region of alignment
    as list of tuples.  if seq argument not None, only match intervals
    for that sequence will be included.  No clipping is performed.'''
    cdef int i,target_id
    cdef NLMSA nl
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    if seq is not None:
      target_id=nl.seqs.getID(seq) # CHECK IF IN OUR ALIGNMENT
    else:
      target_id= -1
    l=[]
    for i from 0 <= i <self.n: # GET ALL STORED INTERVALS
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
  cdef int findSeqBounds(self,int id,int ori):
    'find the specified sequence / orientation using binary search'
    cdef int left,right,mid
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
    cdef int i,id
    cdef NLMSA nl
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
    cdef int i
    cdef NLMSA nl
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i from 0 <= i <self.nseqBounds:
      if nl.seqlist.is_lpo(self.seqBounds[i].target_id):
        continue  # DON'T RETURN EDGES TO LPO
      ival1=sequence.absoluteSlice(self.seq,self.seqBounds[i].start,
                                   self.seqBounds[i].end)
      ival2=nl.seqInterval(self.seqBounds[i].target_id,
                           self.seqBounds[i].target_start,
                           self.seqBounds[i].target_end)
      l.append((ival1,ival2,sequence.Seq2SeqEdge(self,ival2,ival1)))
    return l

  ############################################## GROUP-BY METHODS
  def groupByIntervals(self,int maxgap=0,int maxinsert=0,
                       int mininsert= 0,filterSeqs=None,
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
        filterSeqs not None
      - ivalMethod: a function to process the list of intervals
        for each sequence (it can merge or split them in any way
        it wants)'''
    cdef int i,j,n,gap,insert,targetStart,targetEnd
    cdef NLMSA nl
    if mergeMost: # BE REASONABLE: DON'T MERGE A WHOLE CHROMOSOME
      maxgap=10000
      maxinsert=10000
      mininsert=-10 # ALLOW SOME OVERLAP IN INTERVAL ALIGNMENTS
      maxsize=50000
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    seqIntervals={}
    for i from 0 <= i < self.n: # LIST INTERVALS FOR EACH TARGET
      if nl.seqlist.is_lpo(self.im[i].target_id):
        continue # IT IS AN LPO, SO SKIP IT
      targetStart=self.im[i].target_start
      targetEnd=self.im[i].target_end
      if filterSeqs is not None: # CLIP TARGET SEQ INTERVAL
        target=nl.seqInterval(self.im[i].target_id,targetStart,targetEnd)
        try:
          target=filterSeqs[target] # PERFORM CLIPPING
          targetStart=target.start  # GET COORDS OF CLIPPED REGION
          targetEnd=target.stop
        except KeyError: # NO OVERLAP IN filterSeqs, SO SKIP
          continue
      try: # ADD INTERVAL TO EXISTING LIST
        seqIntervals[self.im[i].target_id] \
             .append([self.im[i].start,self.im[i].end,
                      targetStart,targetEnd])
      except KeyError: # CREATE A NEW LIST FOR THIS TARGET
        seqIntervals[self.im[i].target_id]= \
           [[self.im[i].start,self.im[i].end,targetStart,targetEnd]]

    for i,l in seqIntervals.iteritems(): # MERGE INTERVALS FOR EACH SEQ
      if ivalMethod is not None: # USER-SUPPLIED GROUPING FUNCTION
        ivalMethod(l,nl.seqlist.getSeq(i),msaSlice=self,maxgap=maxgap,
                   maxinsert=maxinsert,mininsert=mininsert,
                   filterSeqs=filterSeqs,mergeAll=mergeAll,**kwargs)
        continue # NO NEED TO APPLY GENERIC MERGING OPERATION BELOW
      n=0
      for j from 1 <= j < len(l): # MERGE BY INDEL LENGTH RULES
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
        if n<j: # COPY END COORDS TO CURRENT SLOT
          l[n][1]=l[j][1]
          l[n][3]=l[j][3]
      del l[n+1:] # DELETE REMAINING UNMERGED INTERVALS
    return seqIntervals

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
    cdef int i,j,start,end,targetStart,targetEnd,ipos,id
    cdef float f
    cdef NLMSA nl
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
      seqStart=mapping.DictQueue()
      maskStart=None
      for bound in bounds: # GENERIC GROUPING: APPLY MASKING, sourceOnly
        ipos,isStart,j,seq,isIndel=bound[0:5]
        if isStart: # INTERVAL START
          seqStart[seq]=bound[5] # JUST RECORD START OF INTERVAL
        else: # INTERVAL STOP
          start,end,targetStart,targetEnd=bound[5]
          if maskStart is not None and not sourceOnly: # SAVE TARGET IVAL
            if maskStart>start: # TRUNCATE TARGET IVAL START
              targetStart=targetStart+maskStart-start
              start=maskStart
            result.append((sequence.absoluteSlice(self.seq,start,end),
                           sequence.absoluteSlice(seq,targetStart,
                                                  targetEnd)))
          del seqStart[seq] # REMOVE THIS SEQ FROM START DICT

        f=len(seqStart) # #ALIGNED SEQS IN THIS REGION
        if f<minAligned or f/len(seqs)<pMinAligned: # APPLY MASKING
          if maskStart is not None:
            if sourceOnly: # JUST SAVE MERGED SOURCE INTERVAL
              result.append(sequence.absoluteSlice(self.seq,maskStart,end))
            else: # REPORT TARGET IVALS WITHIN (maskStart,end) REGION
              for seq,(start,i,targetStart,targetEnd) \
                      in seqStart.iteritems():
                if maskStart>start: # TRUNCATE TARGET IVAL START
                  targetStart=targetStart+maskStart-start
                  start=maskStart
                if end<i: # TRUNCATE TARGET IVAL END
                  targetEnd=targetEnd+end-i
                result.append((sequence.absoluteSlice(self.seq,start,end),
                               sequence.absoluteSlice(seq,targetStart,
                                                      targetEnd)))
            maskStart=None # REGION NOW BELOW THRESHOLD
        elif maskStart is None:
          maskStart=ipos # START OF REGION ABOVE THRESHOLD
        if maskStart is not None and sourceOnly and indelCut \
               and isIndel and maskStart<ipos:
          result.append(sequence.absoluteSlice(self.seq,maskStart,ipos))
          maskStart=ipos
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
    cdef int i
    cdef NLMSA nl
    cdef NLMSASequence ns_lpo
    if self.nlmsaSequence.is_lpo: # ALREADY AN LPO REGION!
      return self.split(**kwargs) # JUST APPLY GROUP-BY RULES TO  self
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i from 0 <= i <self.nseqBounds:
      ns_lpo=nl.seqlist[self.seqBounds[i].target_id]
      if ns_lpo.is_lpo: # ADD ALL LPO INTERVALS ALIGNED HERE
        subslice=NLMSASlice(ns_lpo,self.seqBounds[i].target_start,
                            self.seqBounds[i].target_end)
        l=l+subslice.split(**kwargs) # APPLY GROUP-BY RULES
    if len(l)>0:
      return l
    raise ValueError('no LPO in nlmsaSlice.seqBounds?  Debug!')


  ########################################### LETTER METHODS
  property letters:
    'interface to individual LPO letters in this interval'
    def __get__(self):
      return NLMSASliceLetters(self)

  def __cmp__(self,other):
    if isinstance(other,NLMSASlice):
      return cmp(self.nlmsaSequence,other.nlmsaSequence)
    else:
      return -1





def advanceStartStop(int ipos,NLMSASlice nlmsaSlice not None,
                     int istart,int istop):
  cdef int i
  if istop>=nlmsaSlice.n:
    raise IndexError('out of bounds')
  for i from istop <= i < nlmsaSlice.n:
    if ipos>=nlmsaSlice.im[i].start: # ENTERS THIS INTERVAL
      istop = i + 1 # ADVANCE THE END MARKER
    else:
      break # BEYOND ipos, SEARCH NO FURTHR
  for i from istart <= i < istop: # FIND 1ST OVERLAP
    if ipos<nlmsaSlice.im[i].end:
      break
  return i,istop






cdef class NLMSASliceIterator:
  'generate letters (nodes) in this LPO slice'
  def __new__(self,NLMSASlice nlmsaSlice not None):
    self.nlmsaSlice=nlmsaSlice
    self.ipos= nlmsaSlice.start - 1

  def __iter__(self):
    return self

  def __next__(self): 
    self.ipos = self.ipos + 1
    # ADJUST istart,istop TO OVERLAP ipos
    self.istart,self.istop= \
      advanceStartStop(self.ipos,self.nlmsaSlice,self.istart,self.istop)
    if self.istart>=self.istop: # HMM, NO OVERLAPS TO ipos
      if self.istop<self.nlmsaSlice.n: # ANY MORE INTERVALS?
        self.ipos=self.nlmsaSlice.im[self.istop].start # START OF NEXT INTERVAL
        # ADJUST istart,istop TO OVERLAP ipos
        self.istart,self.istop= \
          advanceStartStop(self.ipos,self.nlmsaSlice,self.istart,self.istop)
      else:
        raise StopIteration # NO MORE POSITIONS IN THIS SLICE
    return NLMSANode(self.ipos,self.nlmsaSlice,self.istart,self.istop)


 




cdef class NLMSANode:
  'interface to a node in NLMSA storage of LPO alignment'
  def __new__(self,int ipos,NLMSASlice nlmsaSlice not None,
              int istart=0,int istop= -1):
    cdef int i,n
    cdef NLMSA nl
    self.nlmsaSlice=nlmsaSlice
    nl=nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    self.ipos=ipos
    if istop<0:
      istart,istop= \
        advanceStartStop(ipos,nlmsaSlice,istart,istart) # COMPUTE PROPER BOUNDS
    self.istart=istart # SAVE BOUNDS
    self.istop=istop
    self.id=ipos # DEFAULT: ASSUME SLICE IS IN LPO...
    for i from istart <= i < istop:
      if nlmsaSlice.im[i].start<=ipos and ipos<nlmsaSlice.im[i].end:
        if nl.seqlist.is_lpo(nlmsaSlice.im[i].target_id):
          self.id=nlmsaSlice.im[i].target_start+ipos-nlmsaSlice.im[i].start #LPO ipos
        else: # DON'T COUNT THE LPO SEQUENCE
          self.n = self.n + 1

  ############################################# ALIGNED LETTER METHODS
  def __len__(self):
    return self.n
  def __iter__(self):
    cdef int i,j
    cdef NLMSA nl
    nl=self.nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].start<=self.ipos \
             and self.ipos<self.nlmsaSlice.im[i].end \
             and not nl.seqlist.is_lpo(self.nlmsaSlice.im[i].target_id):
        j=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
        l.append(nl.seqInterval(self.nlmsaSlice.im[i].target_id,j,j+1))
    return iter(l)

  def getSeqPos(self,seq):
    'return seqpos for this seq at this node'
    cdef int i,j,id
    try:
      id=self.nlmsaSlice.nlmsaSequence.nlmsaLetters.seqs.getID(seq)
    except KeyError:
      raise KeyError('seq not in this alignment')
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].target_id==id: # RETURN THE SEQUENCE INTERVAL
        j=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
        return sequence.absoluteSlice(seq,j,j+1)
    raise KeyError('seq not in node')

  property edges:
    "get this node's edges as list of tuples (ival1,ival2,edge)"
    def __get__(self):
      l=[]
      ival1=sequence.absoluteSlice(self.nlmsaSlice.seq,
                                   self.ipos,self.ipos+1) # OUR SEQ INTERVAL
      for ival2 in self:
        l.append((ival1,ival2,None)) # GET EDGE INFO!!!
      return l

  def __getitem__(self,seq):
    raise NotImplementedError('hey! write some code here!')
##     from lpo import POMSANodeRef # PROBABLY WONT NEED THIS AFTER RENAMING!!!
##     try:
##       s=self.getSeqPos(seq)
##       return POMSANodeRef(self,seq.path)
##     else:
##       raise KeyError('seq not in node')

  def __cmp__(self,other):
    if isinstance(other,NLMSANode):
      return cmp((self.nlmsaSlice,ipos),(other.nlmsaSlice,ipos))
    else:
      return -1

  ########################################## NODE-TO-NODE EDGE METHODS
  cdef int check_edge(self,int iseq,int ipos):
    cdef int i
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].start<=self.ipos \
         and self.ipos<self.nlmsaSlice.im[i].end \
         and self.nlmsaSlice.im[i].target_id==iseq \
         and self.nlmsaSlice.im[i].target_start==ipos:
        return 1 # MATCH!
    return 0 # NO MATCH!

  def getEdgeSeqs(self,NLMSANode other):
    "return dict of sequences that traverse edge from self -> other"
    cdef int i
    cdef NLMSA nl
    nl=self.nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    d={}
    if self.id+1==other.id: #other ADJACENT IN LPO
      for i from self.istart <= i < self.istop:
        if self.nlmsaSlice.im[i].start<=self.ipos+1 \
               and self.ipos+1<self.nlmsaSlice.im[i].end: # INTERVAL CONTAINS other
          seq=nl.seqlist.getSeq(self.nlmsaSlice.im[i].target_id)
          d[seq]=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
        elif self.ipos+1==self.im[i].end \
                 and other.check_edge(self.nlmsaSlice.im[i].target_id,
                                      self.nlmsaSlice.im[i].target_end):
          seq=nl.seqlist.getSeq(self.nlmsaSlice.im[i].target_id) # BRIDGE TO NEXT INTERVAL
          d[seq]=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
    else: # other NOT ADJACENT, SO INTERVALS THAT END HERE MIGHT JUMP TO other
      for i from self.istart <= i < self.istop:
        if self.ipos+1==self.nlmsaSlice.im[i].end \
               and other.check_edge(self.nlmsaSlice.im[i].target_id,
                                    self.nlmsaSlice.im[i].target_end):
          seq=nl.seqlist.getSeq(self.nlmsaSlice.im[i].target_id) # BRIDGE TO NEXT INTERVAL
          d[seq]=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
    return d

  def nodeEdges(self):
    'get all outgoing edges from this node'
    cdef int i,has_continuation
    has_continuation= -1
    d={}
    nodes={} # LIST OF TARGET NODES WE HAVE AN EDGE TO
    for i from self.istart <= i < self.nlmsaSlice.n:
      if i>=self.istop and len(d)==0: # NO FURTHER CHECKS TO DO
        break
      if self.nlmsaSlice.im[i].start<=self.ipos and \
         self.ipos<self.nlmsaSlice.im[i].end-1:
        has_continuation=i # ipos INSIDE THIS INTERVAL, SO HAS EDGE TO ipos+1
      elif self.ipos==self.nlmsaSlice.im[i].end-1: # END OF THIS INTERVAL
        d[self.nlmsaSlice.im[i].target_id]=self.nlmsaSlice.im[i].target_end
      else:
        try: # CHECK FOR START OF AN "ADJACENT" INTERVAL
          if d[self.nlmsaSlice.im[i].target_id]==self.nlmsaSlice.im[i].target_start:
            nodes[self.nlmsaSlice.im[i].start]=i
            del d[self.nlmsaSlice.im[i].target_id] # REMOVE FROM ADJACENCY LIST
        except KeyError:
          pass
    if has_continuation>=0:
      nodes[self.ipos+1]=has_continuation
    result={}
    for i in nodes:
      node=NLMSANode(i,self.nlmsaSlice,self.istart)
      result[node]=sequence.LetterEdge(self,node) # EDGE OBJECT
    return result

  




cdef class NLMSASequence:
  'sequence interface to NLMSA storage of an LPO alignment'
  def __new__(self,NLMSA nl not None,filestem,seq,mode='r',is_union=0):
    self.nlmsaLetters=nl
    self.filestem=filestem
    self.is_union=is_union
    import types
    if isinstance(seq,types.StringType):
      self.name=seq # ALLOW USER TO BUILD INDEXES WITH A STRING NAME
      self.seq=seq
      self.is_lpo=0
    elif seq is not None: # REGULAR SEQUENCE
      seq= seq.pathForward # GET THE WHOLE SEQUENCE, IN FORWARD ORIENTATION
      try: # MAKE SURE seq HAS A UNIQUE NAME FOR INDEXING IT...
        self.name=str(seq.path.name)
      except AttributeError:
        try:
          self.name=str(seq.path.id)
        except AttributeError:
          raise AttributeError('NLMSASequence: seq must have name or id attribute')
      self.seq=seq
      self.is_lpo=0
    else: # LPO SEQUENCES EXPAND AUTOMATICALLY
      self.seq=None
      self.is_lpo=1
      self.length=0
    if mode=='onDemand': # WAIT TO OPEN DB UNTIL ACTUALLY NEEDED
      self.db=None
    else:
      self.db=IntervalFileDB(filestem,mode)
    if mode=='w':
      filename=filestem+'.build'
      self.build_ifile=fopen(filename,'w')
      if self.build_ifile==NULL:
        errmsg='unable to open in write mode: '+filename
        raise IOError(errmsg)
      self.nbuild=0

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.build_ifile:
      fclose(self.build_ifile)

  def forceLoad(self):
    'force database to be initialized, if not already open'
    self.db=IntervalFileDB(self.filestem,'r')

  def close(self):
    'free memory and close files associated with this sequence index'
    if self.db is not None:
      self.db.close() # CLOSE THE DATABASE, RELEASE MEMORY
      self.db=None # DISCONNECT FROM DATABASE
    if self.build_ifile:
      fclose(self.build_ifile)
      self.build_ifile=NULL

  def build(self):
    'build nested list from saved unsorted alignment data'
    cdef IntervalDB db
    if self.build_ifile==NULL:
      raise ValueError('not opened in write mode')
    if self.nbuild<=0:
      raise ValueError('No alignment data for this sequence.  Nothing to build!')
    fclose(self.build_ifile)
    self.build_ifile=NULL
    filename=self.filestem+'.build'
    db=IntervalDB() # CREATE EMPTY NL IN MEMORY
    db.buildFromUnsortedFile(filename,self.nbuild) # BUILD FROM .build
    db.write_binaries(self.filestem) # SAVE AS IntervalDBFile
    db.close() # DUMP NESTEDLIST FROM MEMORY
    import os
    os.remove(filename) # REMOVE OUR .build FILE, NO LONGER NEEDED
    self.db.open(self.filestem) # NOW OPEN THE IntervalDBFile

  cdef int saveInterval(self,IntervalMap im[],int n,int expand_self,FILE *ifile):
    cdef int i
    if expand_self: # AN LPO THAT EXPANDS AS WE ADD TO IT...
      for i from 0 <= i < n:
        if im[i].start>=0:
          if im[i].end>self.length: # EXPAND IT...
            self.length=im[i].end
        elif -(im[i].start)>self.length:
          self.length= -(im[i].start) # THIS HANDLES NEGATIVE ORI CASE
    i=write_padded_binary(im,n,1,ifile)
    if i!=n:
      raise IOError('write_padded_binary failed???')
    return i
    
  def __setitem__(self,k,t): # SAVE TO .build FILE
    'save mapping [k.start:k.stop] --> (id,start,stop)'
    cdef int i
    cdef IntervalMap im_tmp
    if self.build_ifile==NULL:
      raise ValueError('not opened in write mode')
    im_tmp.start,im_tmp.end=(k.start,k.stop)
    im_tmp.target_id,im_tmp.target_start,im_tmp.target_end=t
    im_tmp.sublist= -1
    i=self.saveInterval(&im_tmp,1,self.is_lpo,self.build_ifile)
##     print 'saveInterval:',self.id,im_tmp.start,im_tmp.end,im_tmp.target_id,\
##           im_tmp.target_start,im_tmp.target_end
    self.nbuild=self.nbuild+i # INCREMENT COUNTER OF INTERVALS SAVED

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
    'add sequence to union'
    # CHECK FOR OVERFLOW... CREATE A NEW UNION IF NEEDED
    if self.length+len(seq.path)>self.nlmsaLetters.maxlen:
      ns=self.nlmsaLetters.newSequence(None,is_union=1)
      ns.__iadd__(seq) # ADD seq TO BRAND-NEW UNION
      return ns # RETURN THE NEW UNION COORDINATE SYSTEM
    self.nlmsaLetters.seqs.saveSeq(seq,self.id,self.length)
    self.length=self.length+len(seq.path) # EXPAND COORDINATE SYSTEM
    return self # iadd MUST ALWAYS RETURN self!!!






class NLMSASeqList(list):
  def __init__(self):
    list.__init__(self,nlmsaSeqDict)
    self.nlmsaSeqDict=nlmsaSeqDict
  def __getitem__(self,nlmsaID):
    'return NLMSASequence for a given nlmsa_id'
    try:
      return list.__getitem__(self,nlmsaID)
    except IndexError:
      seqID,nsID=self.nlmsaSeqDict.IDdict[nlmsaID]
      return list.__getitem__(self,nsID)
  def getSeq(self,nlmsaID):
    'return NLMSASequence, seq for a given nlmsa_id'
    seqID,nsID=self.nlmsaSeqDict.IDdict[nlmsaID]
    return self.nlmsaSeqDict.nlmsa.seqDict[seqID]
  def is_lpo(self,id):
    cdef NLMSASequence ns
    if id>=len(self):
      return False
    ns=self[id]
    if ns.is_lpo:
      return True
    else:
      return False



class NLMSASeqDict(dict):
  'index sequences by pathForward, and use list to keep reverse mapping'
  def __init__(self,nlmsa,filename,mode,maxID=1000000):
    dict.__init__(self)
    self.seqlist=NLMSASeqList(self)
    self.maxID=maxID
    self.nlmsa=nlmsa
    self.filename=filename
    import shelve
    if mode=='w': # NEW DATABASE
      mode='c'
    self.seqIDdict=shelve.open(filename+'.seqIDdict',mode)
    self.IDdict=shelve.open(filename+'.idDict',mode)

  def saveSeq(self,seq,nsID,offset,nlmsaID=None):
    'save mapping of seq to specified (nlmsaID,ns,offset)'
    if isinstance(seq,types.StringType):
      id=seq # TREAT THIS AS FULLY QUALIFIED IDENTIFIER
    else: # GET THE IDENTFIER FROM THE SEQ / DATABASE
      id=self.getSeqID(seq)
    if nlmsaID is None: # ALLOCATE A NEW UNIQUE ID
      nlmsaID=len(self.seqlist)+len(self.seqIDdict)+self.nlmsa.nPad
    self.seqIDdict[id]=nlmsaID,nsID,offset
    self.IDdict[str(nlmsaID)]=id,nsID

  def getID(self,seq):
    'return nlmsa_id for a given seq'
    return self[seq][0]
  def __getitem__(self,seq):
    'return nlmsaID,NLMSASequence,offset for a given seq'
    try:
      return dict.__getitem__(self,seq.pathForward)
    except AttributeError:
      raise KeyError('key must be a sequence interval!')
    except KeyError:
      pass
    seqID=self.getSeqID(seq)
    try:
      nlmsaID,nsID,offset=self.seqIDdict[seqID]
    except KeyError:
      raise KeyError('seq not found in this alignment')
    v=nlmsaID,self.seqlist[nsID],offset
    dict.__setitem__(self,seq.pathForward,v) # CACHE THIS RESULT
    return v

  def getSeqID(self,seq):
    'return fully qualified sequence ID for this seq'
    return (~(self.nlmsa.seqDict))[seq]

  def __setitem__(self,k,NLMSASequence ns):
    'save mapping of seq to the specified NLMSASequence'
    import types
    if isinstance(k,types.StringType):
      dict.__setitem__(self,k,ns) # ALLOW BUILD WITH A STRING OBJECT
    elif k is not None:
      dict.__setitem__(self,k.pathForward,ns)
    ns.id=len(self.seqlist)
    self.seqlist.append(ns)
  def __iadd__(self,ns):
    'add coord system ns to the alignment'
    self[None]=ns
    return self # iadd MUST RETURN self!!!
  def close(self):
    'finalize and close shelve indexes'
    self.seqIDdict.close()
    self.idDict.close()
  def reopenReadOnly(self,mode='r'):
    'save existing data and reopen in read-only mode'
    self.close()
    self.seqIDdict=shelve.open(self.filename+'.seqIDdict',mode)
    self.IDdict=shelve.open(self.filename+'.idDict',mode)





cdef class FilePtrPool:
  def __new__(self,char *mode='r',int maxfile=1024,int nalloc=4096):
    self.maxfile=maxfile
    self.nalloc=nalloc
    self.npool=0
    self.pool=<FilePtrRecord *>calloc(nalloc,sizeof(FilePtrRecord))
    self.mode=strdup(mode)
    if self.pool==NULL or self.mode==NULL:
      raise MemoryError
    self.head= -1
    self.tail= -1

  cdef int open(self,int id,char *filename):
    if id>=self.nalloc: # NEED TO EXPAND STORAGE
      pass
    if self.pool[id].filename:
      raise KeyError('already opened this pool ID!  debug!')
    self.pool[id].filename=strdup(filename)
    if self.pool[id].filename==NULL:
      raise MemoryError
    self.pool[id].left= -1 # INITIALLY NOT IN POOL LINK LIST
    self.pool[id].right= -1
    return 0

  cdef FILE *ifile(self,int id):
    if id<0 or id>=self.npool or self.pool[id].filename==NULL:
      raise IndexError('invalid ID: no such FilePoolRecord')
    if self.pool[id].ifile==NULL: # NEED TO OPEN THIS RECORD
      if self.npool>=self.maxfile: # NEED TO CLOSE tail FilePtrRecord
        if self.tail<=0:
          raise IndexError('bad tail value!  debug!')
        fclose(self.pool[self.tail].ifile)
        self.pool[self.tail].ifile=NULL
        self.tail=self.pool[self.tail].left
      self.pool[id].ifile=fopen(self.pool[id].filename,self.mode)
    if self.head==id: # ALREADY AT THE HEAD, SO NO NEED TO MOVE IT
      return self.pool[id].ifile
    if self.pool[id].left>=0:
      self.pool[self.pool[id].left].right=self.pool[id].right # UNLINK
    if self.pool[id].right>=0:
      self.pool[self.pool[id].right].left=self.pool[id].left # UNLINK
    if self.tail==id: # UPDATE NEW tail
      self.tail=self.pool[id].left
    elif self.tail<0: # THERE IS NO TAIL
      self.tail=id # SO THIS BECOMES THE NEW TAIL
    self.pool[id].right=self.head  # PLACE IN FRONT OF head
    self.pool[id].left= -1
    if self.head>=0:
      self.pool[head].left=id
    self.head=id # IT BECOMES THE NEW head
    return self.pool[id].ifile

  cdef int close(self,int id):
    return -1 # THIS IS JUST A STUB!  PUT REAL CODE HERE!!!

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    cdef int i
    if self.pool:
      for i from 0 <= i < self.npool:
        if self.pool[i].ifile: # CLOSE FILE DESCRIPTOR
          fclose(self.pool[i].ifile)
        if self.pool[i].filename: # DUMP FILE STRINGS
          free(self.pool[i].filename)
      free(self.pool)
      self.pool=NULL
    if self.mode:
      free(self.mode)


cdef class NLMSA:
  'toplevel interface to NLMSA storage of an LPO alignment'
  def __new__(self,pathstem='',mode='r',seqDict=None,mafFiles=None,
              maxOpenFiles=1024,maxlen=None,nPad=1000000):
    try:
      import resource # WE MAY NEED TO OPEN A LOT OF FILES...
      resource.setrlimit(resource.RLIMIT_NOFILE,(maxOpenFiles,-1))
    except: # BUT THIS IS OPTIONAL...
      pass
    self.seqs=NLMSASeqDict(self,pathstem,mode)
    self.seqlist=self.seqs.seqlist
    self.pathstem=pathstem
    import sys
    if maxlen is None:
      maxlen=sys.maxint-65536 # MAXIMUM VALUE REPRESENTABLE BY int
    self.maxlen=maxlen
    self.inlmsa=nPad
    if mode=='r':
      if seqDict is None:
        import seqdb
        try: # SEE IF THERE IS A UNION HEADER FILE FOR pathstem.seqDict
          seqDict=seqdb.PrefixUnionDict(filename=pathstem+'.seqDict')
          self.seqDict=seqDict # SAVE FOR USER TO ACCESS...
        except IOError:
          raise ValueError('you must pass a seqDict, or valid header file %s'
                           % (pathstem+'.seqDict'))
      self.read_indexes(seqDict)
    elif mode=='w':
      self.do_build=1
      self.newSequence()
      self.lpo_id=0
      if mafFiles is not None:
        self.readMAFfiles(mafFiles,maxlen)

  def read_indexes(self,seqDict):
    'open all nestedlist indexes in this LPO database for immediate use'
    cdef NLMSASequence ns
    ifile=file(self.pathstem+'NLMSAindex')
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
      ns.length=length # SAVE STORED LENGTH
      self.seqs[seq]=ns # SAVE TO OUR INDEX
      
  def newSequence(self,seq=None,is_union=0):
    'create a new nestedlist index for sequence seq'
    cdef NLMSASequence ns
    i=len(self.seqlist) # USE ITS INDEX AS UNIQUE ID FOR THIS SEQUENCE
    filestem=self.pathstem+str(i)
    ns=NLMSASequence(self,filestem,seq,'w',is_union=is_union) #OPEN FOR WRITING
    self.seqs[seq]=ns # SAVE TO OUR INDEX
    return ns
    
  def __setitem__(self,k,seq):
    'save mapping of LPO slice [k.start:k.stop] --> seq interval'
    cdef int i,start,end
    cdef NLMSASequence ns,ns_lpo
    try:
      id,ns,offset=self.seqs[seq] # LOOK UP IN INDEX
      if seq.orientation<0: # REVERSE ORIENTATION
        seqSlice=slice(seq.start-offset,seq.stop-offset) # USE UNION COORDS
      else: # FORWARD ORIENTATION
        seqSlice=slice(seq.start+offset,seq.stop+offset) # USE UNION COORDS
    except KeyError: # ADD THIS NEW SEQUENCE TO OUR INDEX
      ns=self.newSequence(seq)
      id=ns.id
      seqSlice=seq
    ns[seqSlice]=(self.lpo_id,k.start,k.stop) # FORWARD MAPPING seq -> lpo
    ns_lpo=self.seqlist[self.lpo_id]
    ns_lpo[k]=(id,seq.start,seq.stop) # SAVE REVERSE MAPPING lpo -> seq

  def __getitem__(self,k):
    'return a slice of the LPO'
    if isinstance(k,sequence.SeqPath): # TREAT k AS A SEQUENCE INTERVAL
      id,ns,offset=self.seqs[k] # GET UNION INFO FOR THIS SEQ
      return NLMSASlice(ns,k.start,k.stop,id,offset,k)
    try: # TREAT k AS A PYTHON SLICE OBJECT
      return NLMSASlice(self.seqlist[self.lpo_id],k.start,k.stop)
    except AttributeError:
      raise KeyError('key must be a sequence interval or python slice object')

  cdef void seqname_alloc(self,SeqNameID_T *seqnames,int lpo_id):
    seqnames[0].p=<char *>malloc(32)
    strcpy(seqnames[0].p,"NLMSA_LPO_Internal")
    seqnames[0].id=lpo_id

  def readMAFfiles(self,mafFiles,maxint=None):
    'read alignment from a set of MAF files'
    cdef int i,j,nseq0,nseq1,n,nseq,block_len
    cdef SeqNameID_T seqnames[4096]
    cdef SeqIDMap *seqidmap
    cdef char tmp[32768],*p,a_header[4]
    cdef FILE *ifile
    cdef IntervalMap im[4096],im_tmp
    cdef NLMSASequence ns_lpo,ns # ns IS OUR CURRENT UNION
    cdef FILE *build_ifile[4096]
    cdef int nbuild[4096]

    ns_lpo=self.seqlist[self.lpo_id] # OUR INITIAL LPO
    self.seqname_alloc(seqnames,ns_lpo.id)
    nseq=1
    nseq0=1
    nseq1=1

    nseq0=len(self.seqDict) # GET TOTAL #SEQUENCES IN ALL DATABASES
    seqidmap=<SeqIDMap *>calloc(nseq0,sizeof(SeqIDMap)) # ALLOCATE ARRAY
    i=0
    for pythonStr,j in self.seqDict.iteritemlen():
      seqidmap[i].id=strdup(pythonStr)
      seqidmap[i].length=j
      i=i+1
    qsort(seqidmap,nseq0,sizeof(SeqIDMap),seqidmap_qsort_cmp) # SORT BY id
    ns=self.newSequence(None,is_union=1) # CREATE NEW UNION SEQUENCE

    im_tmp.sublist= -1 # DEFAULT
    strcpy(a_header,"a ") # MAKE C STRING 
    for filename in mafFiles:
      ifile=fopen(filename,'r')
      if ifile==NULL:
        raise IOError('unable to open file %s' % filename)
      if fgets(tmp,32767,ifile)==NULL or strncmp(tmp,"##maf",4):
        raise IOError('%s: not a MAF file? Bad format.' % filename)
      p=fgets(tmp,32767,ifile) # READ THE FIRST LINE OF THE MAF FILE
      while p: # GOT ANOTHER LINE TO PROCESS
        if 0==strncmp(tmp,a_header,2): # ALIGNMENT HEADER: READ ALIGNMENT
          n=readMAFrecord(im,0,seqidmap,nseq0,ns_lpo.length, # READ ONE MAF BLOCK
                          &block_len,ifile,4096)
          if n<0: # UNRECOVERABLE ERROR OCCURRED...
            raise ValueError('MAF block too long!  Increase max size')

          if maxint-ns_lpo.length<=block_len: # TOO BIG! MUST CREATE A NEW LPO
            j=ns_lpo.length # RECORD THE OLD OFFSET
            ns_lpo=self.newSequence() # CREATE A NEW LPO SEQUENCE
            for i from 0<= i < n: # TRANSLATE THESE INTERVALS BACK TO ZERO OFFSET
              if im[i].start>=0: # FORWARD INTERVAL
                im[i].start = im[i].start - j
                im[i].end = im[i].end - j
              else: # REVERSE INTERVAL
                im[i].start = im[i].start + j
                im[i].end = im[i].end + j

          for i from 0 <= i < n: # SAVE EACH INTERVAL IN UNION -> LPO MAP
            j=im[i].target_id
            if seqidmap[j].nlmsa_id<=0: # NEW SEQUENCE, NEED TO ADD TO UNION
              if ns.length+seqidmap[j].length>self.maxlen: # OUT OF SPACE!!
                ns=self.newSequence(None,is_union=1) # CREATE NEW UNION TO HOLD IT
                build_ifile[ns.id]=ns.build_ifile # KEEP PTR SO WE CAN WRITE DIRECTLY!
                nbuild[ns.id]=0
              seqidmap[j].ns_id=ns.id # SET IDs TO ADD THIS SEQ TO THE UNION
              seqidmap[j].nlmsa_id=self.inlmsa
              seqidmap[j].offset=ns.length
              self.inlmsa=self.inlmsa+1 # ADVANCE SEQUENCE ID COUNTER
              ns.length=ns.length+seqidmap[j].length # EXPAND UNION SIZE
            im_ns[i]=seqidmap[j].ns_id # RECORD THE NLMSA ID OF THE UNION 
            im[i].target_id=seqidmap[j].nlmsa_id # USE THE CORRECT
              
            if im[i].target_start<0: # OFFSET REVERSE ORI
              im_tmp.start= -seqidmap[j].offset+im[i].target_start
              im_tmp.end=   -seqidmap[j].offset+im[i].target_end
            else: # OFFSET FORWARD ORI
              im_tmp.start= seqidmap[j].offset+im[i].target_start
              im_tmp.end=   seqidmap[j].offset+im[i].target_end
            im_tmp.target_id=ns_lpo.id
            im_tmp.target_start=im[i].start
            im_tmp.target_end=im[i].end
            j=seqidmap[j].ns_id # USE NLMSA ID OF THE UNION
            ns_lpo.saveInterval(&im_tmp,1,0,build_ifile[j]) # SAVE SEQ -> LPO
            nbuild[j]=nbuild[j]+1

          ns_lpo.saveInterval(im,n,1,ns_lpo.build_ifile) # SAVE LPO -> SEQ
          ns_lpo.nbuild=ns_lpo.nbuild+n # INCREMENT COUNT OF SAVED INTERVALS
        p=fgets(tmp,32767,ifile) # TRY TO READ ANOTHER LINE...
      fclose(ifile) # CLOSE THIS MAF FILE
##     print 'nbuild[0]',ns_lpo.nbuild
    for i from 0 <= i <nseq0: # INDEX SEQUENCES THAT WERE ALIGNED
      if seqidmap[i].nlmsa_id>0: # ALIGNED, SO RECORD IT
        self.seqs.saveSeq(seqidmap[i].id,seqidmap[i].ns_id,seqidmap[i].offset,
                          seqidmap[i].nlmsa_id)
    for i from 0 <= i <nseq0: # DUMP STRING STORAGE FOR SEQUENCE IDENTIFIERS
      free(seqidmap[i].id)
    free(seqidmap) # WE CAN NOW FREE THE SEQUENCE LOOKUP ARRAY
    for ns in self.seqlist: # SAVE INTERVAL COUNTS BACK TO EACH SEQUENCE
      if not ns.is_lpo: # SAVE INTERVAL COUNTS BACK TO REGULAR SEQUENCES
        ns.nbuild=nbuild[ns.id]
##       print 'nbuild[%d]' % i,ns.nbuild
    self.build() # WILL TAKE CARE OF CLOSING ALL build_ifile STREAMS

    
  def build(self):
    'build nestedlist databases from saved mappings and initialize for use'
    cdef NLMSASequence ns
    if self.do_build==0:
      raise ValueError('not opened in write mode')
    self.seqs.reopenReadOnly() # SAVE INDEXES AND OPEN READ-ONLY
    ifile=file(self.pathstem+'NLMSAindex','w')
    for ns in self.seqlist: # BUILD EACH IntervalFileDB ONE BY ONE
      ns.build()
      if ns.seq is not None:
        ifile.write('%d\t%s\t%d\t%d\n' %(ns.id,ns.name,ns.is_union,ns.length))
      else:
        ifile.write('%d\t%s\t%d\t%d\n' %(ns.id,'NLMSA_LPO_Internal',0,ns.length))
    ifile.close()
    self.do_build=0

  def seqInterval(self,int iseq,int istart,int istop):
    'get specified interval in the target sequence'
    seq=self.seqlist.getSeq(iseq) # JUST THE SEQ OBJECT
    return sequence.absoluteSlice(seq,istart,istop)




