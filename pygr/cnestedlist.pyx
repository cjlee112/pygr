#from lpo import POMSANodeRef
import sequence

cdef class IntervalDBIterator:
  def __new__(self,int start,int end,IntervalDB db):
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
        self.subheader=build_nested_list(self.im,self.n,&(self.ntop),&(self.nlists))
      else:
        msg='could not open file %s' % filename
        raise IOError(msg)

  def save_tuples(self,l):
    cdef int i
    self.close() # DUMP OUR EXISTING MEMORY 
    self.n=len(l)
    self.im=interval_map_alloc(self.n)
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

  def write_binaries(self,filestem,div=32):
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
  def __new__(self,int start,int end,IntervalFileDB db,int nbuffer=1024):
    self.it=interval_iterator_alloc()
    self.it_alloc=self.it
    self.start=start
    self.end=end
    self.db=db
    self.im_buf=interval_map_alloc(nbuffer)
    self.nbuf=nbuffer

  def __iter__(self):
    return self

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

  cdef int nextBlock(self,int *pkeep):
    'load one more block of overlapping intervals'
    cdef int i
    if self.it==NULL: # ITERATOR IS EXHAUSTED
      return -1
    if pkeep and pkeep[0]>=0 and pkeep[0]<self.nhit: #MUST KEEP [ikeep:] SLICE
      i=self.extend(pkeep[0]) # MOVE SLICE TO THE FRONT
    else: # WE CAN USE THE WHOLE BUFFER
      i=0
    self.it=find_file_intervals(self.it,self.start,self.end,
                                self.db.db[0].ii,self.db.db[0].nii,
                                self.db.db[0].subheader,self.db.db[0].nlists,
                                self.db.db[0].ntop,self.db.db[0].div,
                                self.db.db[0].ifile_idb,
                                self.im_buf+i,self.nbuf-i,
                                &(self.nhit)) # GET NEXT BUFFER CHUNK
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

  cdef int loadAll(self):
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
    self.db=read_binary_files(filestem,err_msg)
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
      it=find_file_intervals(it,start,end,self.db[0].ii,self.db[0].nii,
                             self.db[0].subheader,self.db[0].nlists,
                             self.db[0].ntop,self.db[0].div,
                             self.db[0].ifile_idb,im_buf,1024,
                             &(nhit)) # GET NEXT BUFFER CHUNK
      for i from 0 <= i < nhit:
        l.append((im_buf[i].start,im_buf[i].end,im_buf[i].target_id,im_buf[i].target_start,im_buf[i].target_end))
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







cdef class NLMSASlice:
  def __new__(self,NLMSASequence ns,int start,int stop):
    cdef int i,j,n,start_max,end_min,start2,stop2,nseq,istart,istop
    cdef NLMSASequence ns_lpo
    cdef IntervalFileDBIterator it,it2
    cdef IntervalMap *im,*im2
    cdef IDInterval *iv
    self.nlmsaSequence=ns # SAVE BASIC INFO
    self.start=start
    self.stop=stop
    it=IntervalFileDBIterator(start,stop,ns.db)
    n=it.loadAll() # GET ALL OVERLAPPING INTERVALS
    if n<=0:
      raise KeyError('this interval is not aligned!')
    for i from 0 <= i < n: # CLIP INTERVALS TO FIT [start:stop]
      if stop<it.im_buf[i].end: # TRUNCATE TO FIT WITHIN [start:stop]
        it.im_buf[i].target_end= it.im_buf[i].target_end \
                                 +stop-it.im_buf[i].end # CALCULATE NEW ENDPOINT
        it.im_buf[i].end=stop
      if start>it.im_buf[i].start: # CALCULATE NEW STARTPOINT
        it.im_buf[i].target_start=it.im_buf[i].target_start \
                                 +start-it.im_buf[i].start
        it.im_buf[i].start=start
    nseq=len(ns.nlmsaLetters.seqlist)
    iv=interval_id_alloc(nseq) # BOUNDS RECORDING
    if ns.is_lpo: # LPO -> REAL SEQS MAPPING
      for i from 0 <= i < n: # GET EACH SEQ'S BOUNDS
        interval_id_union(it.im_buf[i].target_id,it.im_buf[i].target_start,
                          it.im_buf[i].target_end,iv,2*nseq) # RECORD BOUNDS
    else: # TARGET INTERVALS MUST BE LPO, MUST MAP TO REAL SEQUENCES
      ns_lpo=ns.nlmsaLetters.seqlist[ns.nlmsaLetters.lpo_id] # DEFAULT LPO
      for i from 0 <= i < n:
        if it.im_buf[i].target_id != ns_lpo.id: # SWITCHING TO A DIFFERENT LPO?
          ns_lpo=ns.nlmsaLetters.seqlist[it.im_buf[i].target_id]
          if not ns_lpo.is_lpo:
            raise ValueError('sequence mapped to non-LPO target??')
        it2=IntervalFileDBIterator(it.im_buf[i].target_start,
                                   it.im_buf[i].target_end,ns_lpo.db)
        it2.loadAll() # GET ALL OVERLAPPING INTERVALS
        im2=it2.getIntervalMap() # RELEASE ARRAY FROM THIS ITERATOR
        if im2==NULL: # NO HITS, SO TRY THE NEXT INTERVAL???
          continue
        for j from 0 <= j < it2.nhit: # MAP EACH INTERVAL BACK TO ns
          if im2[j].target_id==ns.id: # DISCARD SELF-MATCH
            continue
          if it.im_buf[i].target_start>im2[j].start: # GET INTERSECTION INTERVAL
            start_max=it.im_buf[i].target_start
          else:
            start_max=im2[j].start
          if it.im_buf[i].target_end<im2[j].end:
            end_min=it.im_buf[i].target_end
          else:
            end_min=im2[j].end
          istart=it.im_buf[i].start+start_max-it.im_buf[i].target_start # ns COORDS
          istop=it.im_buf[i].start+end_min-it.im_buf[i].target_start
          start2=im2[j].target_start+start_max-im2[j].start # COORDS IN TARGET
          stop2=im2[j].target_start+end_min-im2[j].start
          it.saveInterval(istart,istop,im2[j].target_id,start2,stop2) # SAVE IT!
          interval_id_union(im2[j].target_id,start2,stop2,iv,2*nseq) # RECORD BOUNDS
        free(im2) # FREE THE MAP OURSELVES, SINCE RELEASED FROM it2

    self.im=it.getIntervalMap() # RELEASE THIS ARRAY FROM THE ITERATOR
    self.n=it.nhit # TOTAL #INTERVALS SAVED FROM JOIN
    qsort(self.im,self.n,sizeof(IntervalMap),imstart_qsort_cmp) # ORDER BY start
    n=2*nseq
    self.seqBounds=interval_id_compact(iv,&n) # SHRINK THE LIST TO ELIMINATE EMPTY ENTRIES
    self.nseqBounds=n

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.im:
      free(self.im)
      self.im=NULL
    if self.seqBounds:
      free(self.seqBounds)
      self.seqBounds=NULL

  def findSeqEnds(self,seq):
    'get maximum interval of seq aligned in this interval'
    cdef int i,ori,i_ori
    cdef NLMSALetters nl
    cdef NLMSASequence ns
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    ns=nl.seqs[seq] # MAKE SURE THIS IS IN OUR ALIGNMENT
    ori=seq.orientation # GET ITS ORIENTATION
    for i from 0 <= i <self.nseqBounds:
      if self.seqBounds[i].id==ns.id: # FOUND OUR SEQUENCE
        if self.seqBounds[i].start<0:
          i_ori= -1
        else:
          i_ori=1
        if i_ori==ori: # AND THE ORIENTATIONS MATCH
          return nl.seqInterval(self.seqBounds[i].id,self.seqBounds[i].start,
                                self.seqBounds[i].stop)
    raise KeyError('seq not aligned in this interval')

  def __iter__(self):
    cdef int i
    cdef NLMSALetters nl
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i from 0 <= i <self.nseqBounds:
      l.append(nl.seqInterval(self.seqBounds[i].id,self.seqBounds[i].start,
                              self.seqBounds[i].stop))
    return iter(l)

  property letters:
    'interface to individual LPO letters in this interval'
    def __get__(self):
      return NLMSASliceIterator(self)

  def __len__(self):
    return self.nseqBounds # NUMBER OF SEQUENCE/ORIS ALIGNED HERE

  def generateIntervals(self):
    'generate all 1:1 match intervals in this region of alignment'
    cdef int i
    cdef NLMSALetters nl
    nl=self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i from 0 <= i <self.n:
      l.append(nl.seqInterval(self.im[i].target_id,self.im[i].target_start,
                              self.im[i].target_end))
    return iter(l)
    



 
cdef class NLMSANode:
  'interface to a node in NLMSA storage of LPO alignment'
  def __new__(self,int ipos,NLMSASlice nlmsaSlice,int istart,int istop):
    cdef int i,n
    self.nlmsaSlice=nlmsaSlice
    self.ipos=ipos
    self.istart=istart
    self.istop=istop
    self.id=ipos # DEFAULT: ASSUME SLICE IS IN LPO...
    for i from istart <= i < istop:
      if nlmsaSlice.im[i].start<=ipos and ipos<nlmsaSlice.im[i].end:
        if nlmsaSlice.nlmsaSequence.nlmsaLetters.is_lpo(nlmsaSlice.im[i].target_id):
          self.id=nlmsaSlice.im[i].target_start+ipos-nlmsaSlice.im[i].start #LPO ipos
        else: # DON'T COUNT THE LPO SEQUENCE
          self.n = self.n + 1
    
  def __iter__(self):
    cdef int i,j
    cdef NLMSASequence ns
    cdef NLMSALetters nl
    nl=self.nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l=[]
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].start<=self.ipos \
             and self.ipos<self.nlmsaSlice.im[i].end \
             and not nl.is_lpo(self.nlmsaSlice.im[i].target_id):
        j=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
        l.append(nl.seqInterval(self.nlmsaSlice.im[i].target_id,j,j+1))
    return iter(l)

  def getSeqPos(self,seq):
    'return seqpos for this seq at this node'
    cdef int i,j
    cdef NLMSASequence ns # FIRST LOOK UP THE SEQUENCE
    try:
      ns=self.nlmsaSlice.nlmsaSequence.nlmsaLetters.seqs[seq]
    except KeyError:
      raise KeyError('seq not in this alignment')
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].target_id==ns.id: # RETURN THE SEQUENCE INTERVAL
        j=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
        return sequence.absoluteSlice(ns.seq,j,j+1)
    raise KeyError('seq not in node')

  def __getitem__(self,seq):
    from lpo import POMSANodeRef # PROBABLY WONT NEED THIS AFTER RENAMING!!!
    try:
      s=self.getSeqPos(seq)
      return POMSANodeRef(self,seq.path)
    else:
      raise KeyError('seq not in node')

  def __len__(self):
    return self.n

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
    cdef NLMSASequence ns # FIRST LOOK UP THE SEQUENCE
    cdef NLMSALetters nl
    nl=self.nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    d={}
    if self.id+1==other.id: #other ADJACENT IN LPO
      for i from self.istart <= i < self.istop:
        if self.nlmsaSlice.im[i].start<=self.ipos+1 \
               and self.ipos+1<self.nlmsaSlice.im[i].end: # THIS INTERVAL CONTAINS other
          ns=nl.seqlist[self.nlmsaSlice.im[i].target_id]
          d[ns.seq]=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
        elif self.ipos+1==self.im[i].end \
                 and other.check_edge(self.nlmsaSlice.im[i].target_id,
                                      self.nlmsaSlice.im[i].target_end):
          ns=nl.seqlist[self.nlmsaSlice.im[i].target_id] # BRIDGE TO NEXT INTERVAL
          d[ns.seq]=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
    else: # other NOT ADJACENT, SO INTERVALS THAT END HERE MIGHT JUMP TO other
      for i from self.istart <= i < self.istop:
        if self.ipos+1==self.nlmsaSlice.im[i].end \
               and other.check_edge(self.nlmsaSlice.im[i].target_id,
                                    self.nlmsaSlice.im[i].target_end):
          ns=nl.seqlist[self.im[i].target_id] # BRIDGE TO NEXT INTERVAL
          d[ns.seq]=self.nlmsaSlice.im[i].target_start+self.ipos-self.nlmsaSlice.im[i].start
    return d



  

cdef class NLMSASequence:
  'sequence interface to NLMSA storage of an LPO alignment'
  def __new__(self,NLMSALetters nl,filestem,seq,mode='r'):
    self.nlmsaLetters=nl
    self.filestem=filestem
    if seq is not None: # REGULAR SEQUENCE
      seq= seq.pathForward # GET THE WHOLE SEQUENCE, IN FORWARD ORIENTATION
      try: # MAKE SURE seq HAS A UNIQUE NAME FOR INDEXING IT...
        tmp=str(seq.path.name)
      except AttributeError:
        try:
          tmp=str(seq.path.id)
        except AttributeError:
          raise AttributeError('NLMSASequence: seq must have name or id attribute')
      self.seq=seq
      self.is_lpo=0
    else: # LPO SEQUENCES EXPAND AUTOMATICALLY
      self.seq=None
      self.is_lpo=1
      self.length=0
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

  def close(self):
    'free memory and close files associated with this sequence index'
    self.db.close()
    if self.build_ifile:
      fclose(self.build_ifile)
      self.build_ifile=NULL

  def build(self):
    'build nested list from saved unsorted alignment data'
    cdef IntervalDB db
    if self.build_ifile==NULL:
      raise ValueError('not opened in write mode')
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
    
  def __setitem__(self,k,t): # SAVE TO .build FILE
    'save mapping [k.start:k.stop] --> (id,start,stop)'
    cdef int i
    cdef IntervalMap im_tmp
    if self.build_ifile==NULL:
      raise ValueError('not opened in write mode')
    if self.is_lpo: # AN LPO THAT EXPANDS AS WE ADD TO IT...
      if k.stop>self.length: # EXPAND IT...
        self.length=k.stop
    im_tmp.start,im_tmp.end=(k.start,k.stop)
    im_tmp.target_id,im_tmp.target_start,im_tmp.target_end=t
    im_tmp.sublist= -1
    i=write_padded_binary(&im_tmp,1,1,self.build_ifile)
    if i!=1:
      raise IOError('write_padded_binary failed???')
    self.nbuild=self.nbuild+1 # INCREMENT COUNTER OF INTERVALS SAVED

  def __getitem__(self,k):
    try:
      if k.pathForward is self.seq:
        return NLMSASlice(self,k.start,k.stop)
    except AttributeError: pass
    raise KeyError('key must be a sequene interval of this sequence')

  def __len__(self):
    'call len(self.seq) if we have a seq.  Otherwise self.length'
    if self.seq is None:
      return self.length
    else:
      return len(self.seq)
    



class NLMSASeqDict(dict):
  'index sequences by pathForward, and use list to keep reverse mapping'
  def __init__(self):
    dict.__init__(self)
    self.seqlist=[]

  def __getitem__(self,k):
    try:
      return dict.__getitem__(self,k.pathForward)
    except AttributeError:
      raise KeyError('key must be a sequence interval!')

  def __setitem__(self,k,NLMSASequence ns):
    if k is not None:
      dict.__setitem__(self,k.pathForward,ns)
    ns.id=len(self.seqlist)
    self.seqlist.append(ns)






cdef class NLMSALetters:
  'toplevel letter interface to NLMSA storage of an LPO alignment'
  def __new__(self,pathstem='',mode='r',seqDict=None):
    self.seqs=NLMSASeqDict()
    self.seqlist=self.seqs.seqlist
    self.pathstem=pathstem
    if mode=='r':
      if seqDict is None:
        raise ValueError('you must pass a seqDict, to open for reading')
      self.read_indexes(seqDict)
    elif mode=='w':
      self.do_build=1
      self.newSequence()
      self.lpo_id=0

  def read_indexes(self,seqDict):
    'open all nestedlist indexes in this LPO database for immediate use'
    cdef NLMSASequence ns
    ifile=file(self.pathstem+'NLMSAindex')
    for line in ifile:
      id,name=line.strip().split('\t')
      id=int(id)
      if id!=len(self.seqlist):
        raise IOError('corrupted NLMSAIndex???')
      filestem=self.pathstem+str(id)
      if name=='NLMSA_LPO_Internal': # AN LPO REFERENCE
        self.lpo_id=id
        seq=None # NO ACTUAL SEQUENCE ASSOCIATED WITH LPO
      else: # REGULAR SEQUENCE
        try:
          seq=seqDict[name]
        except KeyError:
          raise KeyError('unable to find sequence %s in seqDict!' % name)
      ns=NLMSASequence(self,filestem,seq) # OPEN THE IntervalDBFile
      self.seqs[seq]=ns # SAVE TO OUR INDEX
      
  def newSequence(self,seq=None):
    'create a new nestedlist index for sequence seq'
    cdef NLMSASequence ns
    i=len(self.seqlist) # USE ITS INDEX AS UNIQUE ID FOR THIS SEQUENCE
    filestem=self.pathstem+str(i)
    ns=NLMSASequence(self,filestem,seq,'w') # OPEN IN WRITING MODE
    self.seqs[seq]=ns # SAVE TO OUR INDEX
    return ns
    

  def __setitem__(self,k,seq):
    'save mapping of LPO slice [k.start:k.stop] --> seq interval'
    cdef int i,start,end
    cdef NLMSASequence ns,ns_lpo
    try:
      ns=self.seqs[seq] # LOOK UP IN INDEX
    except KeyError: # ADD THIS NEW SEQUENCE TO OUR INDEX
      ns=self.newSequence(seq)
    ns[seq]=(self.lpo_id,k.start,k.stop) # SAVE FORWARD MAPPING seq -> lpo
    ns_lpo=self.seqlist[self.lpo_id]
    ns_lpo[k]=(ns.id,seq.start,seq.stop) # SAVE REVERSE MAPPING lpo -> seq

  def __getitem__(self,k):
    'return a slice of the LPO'
    try: # TREAT k AS A SEQUENCE INTERVAL
      return NLMSASlice(self.seqs[k],k.start,k.stop)
    except KeyError: # TREAT k AS A PYTHON SLICE OBJECT
      return NLMSASlice(self.seqlist[self.lpo_id],k.start,k.stop)
    except AttributeError:
      raise KeyError('key must be a sequence interval or python slice object')
    
  def build(self):
    'build nestedlist databases from saved mappings and initialize for use'
    cdef NLMSASequence ns
    if self.do_build==0:
      raise ValueError('not opened in write mode')
    ifile=file(self.pathstem+'NLMSAindex','w')
    for ns in self.seqlist: # BUILD EACH IntervalFileDB ONE BY ONE
      ns.build()
      if ns.seq is not None:
        try:
          ifile.write('%d\t%s\n' %(ns.id,ns.seq.name))
        except AttributeError:
          ifile.write('%d\t%s\n' %(ns.id,ns.seq.id))
      else:
        ifile.write('%d\t%s\n' %(ns.id,'NLMSA_LPO_Internal'))
    ifile.close()
    self.do_build=0

  cdef int is_lpo(self,int id):
    if id==self.lpo_id:  # FIX THIS TO ALLOW MULTIPLE LPO!!!!
      return 1
    else:
      return 0

  def seqInterval(self,int iseq,int istart,int istop):
    'get specified interval in the target sequence'
    ns=self.seqlist[iseq]
    return sequence.absoluteSlice(ns.seq,istart,istop)






cdef class NLMSASliceIterator:
  'generate letters (nodes) in this LPO slice'
  def __new__(self,NLMSASlice nlmsaSlice):
    self.nlmsaSlice=nlmsaSlice
    self.ipos= nlmsaSlice.start - 1

  def __iter__(self):
    return self

  cdef int advanceStartStop(self):
    cdef int i
    for i from self.istop <= i < self.nlmsaSlice.n:
      if self.ipos>=self.nlmsaSlice.im[i].start: # ENTERS THIS INTERVAL
        self.istop = i + 1 # ADVANCE THE END MARKER
      else:
        break # BEYOND ipos, SEARCH NO FURTHR
    for i from self.istart <= i < self.istop: # FIND 1ST OVERLAP
      if self.ipos<self.nlmsaSlice.im[i].end:
        break
    self.istart=i
    return i

  def __next__(self):
    self.ipos = self.ipos + 1
    self.advanceStartStop() # ADJUST istart,istop TO OVERLAP ipos
    if self.istart>=self.istop: # HMM, NO OVERLAPS TO ipos
      if self.istop<self.nlmsaSlice.n: # ANY MORE INTERVALS?
        self.ipos=self.nlmsaSlice[self.istop].start # START OF NEXT INTERVAL
        self.advanceStartStop() # ADJUST istart,istop TO OVERLAP ipos
      else:
        raise StopIteration # NO MORE POSITIONS IN THIS SLICE
    return NLMSANode(self.ipos,self.nlmsaSlice,self.istart,self.istop)
