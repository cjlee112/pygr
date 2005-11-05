#from lpo import POMSANodeRef

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
    cdef int len,istart
    cdef IntervalMap *new_buf
    istart=self.nbuf-ikeep
    len=sizeof(IntervalMap)*(self.nbuf-ikeep)
    if ikeep<8: # RUNNING OUT OF ROOM, SO EXPAND BUFFER
      self.nbuf=2*self.nbuf
      new_buf=interval_map_alloc(self.nbuf)
      memcpy(new_buf,self.im_buf+ikeep,len)
      free(self.im_buf)
      self.im_buf=new_buf
    else: # JUST SHIFT [ikeep:] SLICE OF BUFFER TO FRONT [0:]
      memmove(self.im_buf,self.im_buf+ikeep,len)
    return istart # RETURN START OF EMPTY BLOCK WHERE WE CAN ADD NEW DATA

  cdef int cnext(self,int *pkeep): # C VERSION OF ITERATOR next METHOD
    cdef int i
    if self.ihit>=self.nhit: # TRY TO GET ONE MORE BUFFER CHUNK OF HITS
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
    self.close()


cdef class IFDBIteratorBuffer:
  def __new__(self,int start,int end,nlmsaSequence):
    # CREATE THE ITERATOR
    self.nlmsaSequence=nlmsaSequence
    self.it=IntervalFileDBIterator(start,end,nlmsaSequence.db)
    self.ipos= start-1
    self.ikeep=0
    self.imax= -1

  def __iter__(self):
    return self

  cdef int cnext(self):
    cdef int i,j
    self.ipos=self.ipos+1 # ADVANCE BY ONE LETTER
    # EXTEND THE BUFFER IF NEEDED
    while self.imax<0 or self.ipos>self.it.im_buf[self.imax].start:
      i=self.it.cnext(&(self.ikeep)) # GET ANOTHER INTERVAL
      if i<0: # EXHAUSTED ITERATOR
        break
      self.imax=i # EXTEND UNTIL INTERVAL imax DOES NOT OVERLAP ipos
    j=self.imax
    i=j
    while i>=self.ikeep: # COMPACT BUFFER TO ELIMINATE NON-OVERLAP 
      if self.ipos<self.it.im_buf[i].end: # ipos in INTERVAL, SO KEEP IT
        if j>i: # MOVE UP TO NEW LOCATION
          memcpy(self.it.im_buf+j,self.it.im_buf+i,sizeof(IntervalMap))
        j=j-1
      i=i-1
    self.ikeep=j+1 # START OF COMPACTED LIST OF OVERLAPPING INTERVALS

    if self.ikeep>self.imax:
      return -1

    if self.ipos<self.it.im_buf[self.ikeep].start: # ipos B4 INTERVAL
      self.ipos=self.it.im_buf[self.ikeep].start # SKIP TO START OF INTERVAL
    self.im= self.it.im_buf+self.ikeep # PTR TO START OF OVERLAPPING INTERVALS
    self.noverlap=self.imax-self.ikeep # #OVERLAPPING INTERVALS
    if self.ipos>=self.it.im_buf[self.imax].start: # ipos IN INTERVAL
      self.noverlap=self.noverlap+1 # imax ALSO OVERLAPS, SO COUNT IT TOO
    return self.ipos
  
  def __next__(self):
    cdef int i
    i=self.cnext()
    if i<0:
      raise StopIteration
    return NLMSANode(self)





cdef class NLMSANode:
  def __new__(self,IFDBIteratorBuffer it):
    self.nlmsaSequence=it.nlmsaSequence
    self.db=it.it.db
    self.ipos=it.ipos
    self.n=it.noverlap
    self.im=interval_map_alloc(it.noverlap)
    memcpy(self.im,it.im,it.noverlap*sizeof(IntervalMap))
    
  def __dealloc__(self):
    if self.im:
      free(self.im)

  def __iter__(self): # CORRECT THIS TO RETURN SEQPOS!!!
    cdef int i,j
    cdef NLMSASequence ns # FIRST LOOK UP THE SEQUENCE
    l=[]
    for i from 0 <= i < self.n:
      ns=self.nlmsaSequence.nlmsaLetters.seqlist[self.im[i].target_id]
      j=self.im[i].target_start+self.ipos-self.im[i].start
      l.append(ns.seq[j:j+1])
    return iter(l)

  def getSeqPos(self,seq):
    'return seqpos for this seq at this node'
    cdef int i,j,iseq
    cdef NLMSASequence ns # FIRST LOOK UP THE SEQUENCE
    try:
      ns=self.nlmsaSequence.nlmsaLetters.seqs[seq.path,seq.orientation]
    except KeyError:
      raise KeyError('seq not in this alignment')
    iseq=ns.id # THEN GET ITS ID
    for i from 0 <= i < self.n:
      if self.im[i].target_id==iseq:
        j=self.im[i].target_start+self.ipos-self.im[i].start
        return ns.seq[j:j+1] # RETURN THE SEQUENCE INTERVAL
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
    for i from 0 <= i < self.n:
      if self.im[i].target_id==iseq and self.im[i].target_start==ipos:
        return 1 # MATCH!
    return 0 # NO MATCH!

  def getEdgeSeqs(self,NLMSANode other):
    "return dict of sequences that traverse edge from self -> other"
    cdef int i
    cdef NLMSASequence ns # FIRST LOOK UP THE SEQUENCE
    d={}
    if self.id==other.id and self.ipos+1==other.ipos: #other ADJACENT IN LPO
      for i from 0 <= i < self.n:
        if other.ipos<self.im[i].end: # THIS INTERVAL CONTAINS other
          ns=self.nlmsaSequence.nlmsaLetters.seqlist[self.im[i].target_id]
          d[ns.seq]=self.im[i].target_start+self.ipos-self.im[i].start
        elif other.ipos==self.im[i].end \
                 and other.check_edge(self.im[i].target_id, # MIGHT JUMP TO NEXT INTERVAL
                                      self.im[i].target_end):
          ns=self.nlmsaSequence.nlmsaLetters.seqlist[self.im[i].target_id]
          d[ns.seq]=self.im[i].target_start+self.ipos-self.im[i].start
    else: # other NOT ADJACENT, SO INTERVALS THAT END HERE MIGHT JUMP TO other
      for i from 0 <= i < self.n:
        if self.ipos+1==self.im[i].end \
                 and other.check_edge(self.im[i].target_id, # MIGHT JUMP TO NEXT INTERVAL
                                      self.im[i].target_end):
          ns=self.nlmsaSequence.nlmsaLetters.seqlist[self.im[i].target_id]
          d[ns.seq]=self.im[i].target_start+self.ipos-self.im[i].start
    return d

  

cdef class NLMSASequence:
  'sequence interface to NLMSA storage of an LPO'
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
      self.length=len(seq)
      self.fixed_length=1
    else: # LPO SEQUENCES EXPAND AUTOMATICALLY
      self.seq=None
      self.fixed_length=0
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
    self.close()
  def close(self):
    'free memory and close files associated with this sequence index'
    self.db.close()
    if self.build_ifile:
      fclose(self.build_ifile)

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
    self.db.open(self.filestem) # NOW OPEN THE IntervalDBFile
    
  def __setitem__(self,k,t): # SAVE TO .build FILE
    'save mapping [k.start:k.stop] --> (id,start,stop)'
    cdef int i
    cdef IntervalMap im_tmp
    if self.build_ifile==NULL:
      raise ValueError('not opened in write mode')
    if not self.fixed_length: # AN LPO THAT EXPANDS AS WE ADD TO IT...
      if k.stop>self.length: # EXPAND IT...
        self.length=k.stop
    im_tmp.start,im_tmp.end=(k.start,k.stop)
    im_tmp.target_id,im_tmp.target_start,im_tmp.target_end=t
    im_tmp.sublist= -1
    i=write_padded_binary(&im_tmp,1,1,self.build_ifile)
    if i!=1:
      raise IOError('write_padded_binary failed???')
    self.nbuild=self.nbuild+1 # INCREMENT COUNTER OF INTERVALS SAVED
    

class NLMSASeqDict(dict):
  'index sequences by pathForward, and use list to keep reverse mapping'
  def __init__(self):
    dict.__init__(self)
    self.seqlist=[]

  def __getitem__(self,k):
    return dict.__getitem__(self,k.pathForward)

  def __setitem__(self,k,NLMSASequence ns):
    if k is not None:
      dict.__setitem__(self,k.pathForward,ns)
    ns.id=len(self.seqlist)
    self.seqlist.append(ns)


cdef class NLMSALetters:
  'toplevel letter interface to NLMSA storage of an LPO'
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
      id,name=line.split('\t')
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
    
  def build(self):
    'build nestedlist databases from saved mappings and initialize for use'
    cdef NLMSASequence ns
    if self.do_build==0:
      raise ValueError('not opened in write mode')
    ifile=file(self.pathstem+'NLMSAindex','w')
    for ns in self.seqlist: # BUILD EACH IntervalFileDB ONE BY ONE
      ns.build()
      if ns.seq is not None:
        ifile.write('%d\t%s\n' %(ns.id,ns.seq.name))
      else:
        ifile.write('%d\t%s\n' %(ns.id,'NLMSA_LPO_Internal'))
    ifile.close()
    self.do_build=0
      
