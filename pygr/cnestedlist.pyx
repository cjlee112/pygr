import sequence
import nlmsa_utils
import logger


cdef class IntervalDBIterator:

  def __new__(self, int start, int end, IntervalDB db not None):
    self.it = interval_iterator_alloc()
    self.it_alloc = self.it
    self.start = start
    self.end = end
    self.db = db

  def __iter__(self):
    return self

  cdef int cnext(self): # C VERSION OF ITERATOR next METHOD RETURNS INDEX
    cdef int i
    if self.ihit >= self.nhit: # TRY TO GET ONE MORE BUFFER CHUNK OF HITS
      if self.it == NULL: # ITERATOR IS EXHAUSTED
        return -1
      find_intervals(self.it, self.start, self.end, self.db.im, self.db.ntop,
                     self.db.subheader, self.db.nlists, self.im_buf, 1024,
                     &(self.nhit), &(self.it)) # GET NEXT BUFFER CHUNK
      self.ihit = 0 # START ITERATING FROM START OF BUFFER
    if self.ihit < self.nhit: # RETURN NEXT ITEM FROM BUFFER
      i = self.ihit
      self.ihit = self.ihit + 1 # ADVANCE THE BUFFER COUNTER
      return i
    else: # BUFFER WAS EMPTY, NO HITS TO ITERATE OVER...
      return -1

  # PYTHON VERSION OF next RETURNS HIT AS A TUPLE
  def __next__(self): # PYREX USES THIS NON-STANDARD NAME INSTEAD OF next()!!!
    cdef int i
    i = self.cnext()
    if i >= 0:
      return (self.im_buf[i].start, self.im_buf[i].end, self.im_buf[i].target_id,
              self.im_buf[i].target_start, self.im_buf[i].target_end)
    else:
      raise StopIteration

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    free_interval_iterator(self.it_alloc)


cdef class IntervalDB:

  def __new__(self, filename='noname', nsize=0, **kwargs):
    cdef int i
    cdef FILE *ifile
    self.n = nsize
    if nsize > 0:
      ifile = fopen(filename, "r") # text file, one interval per line
      if ifile:
        self.im = read_intervals(self.n, ifile)
        fclose(ifile)
        if self.im != NULL:
          self.runBuildMethod(**kwargs)
      else:
        msg = 'could not open file %s' % filename
        raise IOError(msg)

  def save_tuples(self, l, **kwargs):
    'build in-memory NLMSA from list of alignment tuples'
    cdef int i
    self.close() # DUMP OUR EXISTING MEMORY
    self.n = len(l)
    self.im = interval_map_alloc(self.n)
    if self.im == NULL:
      raise MemoryError('unable to allocate IntervalMap[%d]' % self.n)
    i = 0
    for t in l:
      self.im[i].start = t[0]
      self.im[i].end = t[1]
      self.im[i].target_id = t[2]
      self.im[i].target_start = t[3]
      self.im[i].target_end = t[4]
      self.im[i].sublist = -1
      i = i + 1
    self.runBuildMethod(**kwargs)

  def runBuildMethod(self, buildInPlace=True):
    'build either in-place or using older build method'
    if buildInPlace:
      self.subheader = build_nested_list_inplace(self.im, self.n, &(self.ntop), &(self.nlists))
    else:
      self.subheader = build_nested_list(self.im, self.n, &(self.ntop), &(self.nlists))

  def buildFromUnsortedFile(self, filename, int n, **kwargs):
    'load unsorted binary data, and build nested list'
    cdef FILE *ifile
    cdef int i
    cdef IntervalMap *im_new
    self.close()
    ifile = fopen(filename, 'rb') # binary file
    if ifile == NULL:
      raise IOError('unable to open ' + filename)
    im_new = interval_map_alloc(n)
    if im_new == NULL:
      raise MemoryError('unable to allocate IntervalMap[%d]' % n)
    i = read_imdiv(ifile, im_new, n, 0, n)
    fclose(ifile)
    if i != n:
      raise IOError('IntervalMap file corrupted?')
    self.n = n
    self.im = im_new
    self.runBuildMethod(**kwargs)

  def find_overlap(self, int start, int end):
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    return IntervalDBIterator(start, end, self)

  def find_overlap_list(self, int start, int end):
    cdef int i, nhit
    cdef IntervalIterator *it, *it_alloc
    cdef IntervalMap im_buf[1024]
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    it = interval_iterator_alloc()
    it_alloc = it
    l = [] # LIST OF RESULTS TO HAND BACK
    while it:
      find_intervals(it, start, end, self.im, self.ntop,
                     self.subheader, self.nlists, im_buf, 1024,
                     &(nhit), &(it)) # GET NEXT BUFFER CHUNK
      for i from 0 <= i < nhit:
        l.append((im_buf[i].start, im_buf[i].end, im_buf[i].target_id, im_buf[i].target_start, im_buf[i].target_end))
    free_interval_iterator(it_alloc)
    return l

  def check_nonempty(self):
    if self.im:
      return True
    else:
      msg = 'empty IntervalDB, not searchable!'
      raise IndexError(msg)

  def write_binaries(self, filestem, div=256):
    cdef char *err_msg
    err_msg = write_binary_files(self.im, self.n, self.ntop, div,
                                 self.subheader, self.nlists, filestem)
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
    self.subheader = NULL
    self.im = NULL

    return None


cdef class IntervalFileDBIterator:

  def __new__(self, int start, int end, IntervalFileDB db=None,
              NLMSASequence ns=None,
              int nbuffer=1024, rawIvals=None):
    cdef int i
    self.it_alloc = interval_iterator_alloc()
    self.restart(start, end, db, ns)
    if rawIvals is not None and len(rawIvals) > nbuffer:
      nbuffer = len(rawIvals)
    self.im_buf = interval_map_alloc(nbuffer)
    self.nbuf = nbuffer
    if rawIvals is not None:
      i = 0
      for ival in rawIvals:
        self.im_buf[i].start = ival[0] # SAVE INTERVAL INFO
        self.im_buf[i].end = ival[1]
        self.im_buf[i].target_id = ival[2]
        self.im_buf[i].target_start = ival[3]
        self.im_buf[i].target_end = ival[4]
        i = i + 1
      self.nhit = i # TOTAL NUMBER OF INTERVALS STORED

  cdef int restart(self, int start, int end, IntervalFileDB db,
                   NLMSASequence ns) except -2:
    'reuse this iterator for another search without reallocing memory'
    self.nhit = 0 # FLUSH ANY EXISTING DATA
    self.start = start
    self.end = end
    self.db = db
    if ns is not None:
      if ns.idb is not None:
        self.idb = ns.idb
      elif ns.db is None:
        ns.forceLoad()
      self.db = ns.db
    self.it = self.it_alloc # REUSE OUR CURRENT ITERATOR
    reset_interval_iterator(self.it) # RESET IT FOR REUSE
    return 0

  cdef int reset(self) except -2:
    'flush the buffer so we can reuse this iterator'
    self.nhit = 0
    return 0

  cdef int extend(self, int ikeep):
    'expand the buffer if necessary, keeping elements [ikeep:nbuf]'
    cdef int length, istart
    cdef IntervalMap *new_buf
    istart = self.nbuf - ikeep
    length = sizeof(IntervalMap) * istart # #BYTES WE MUST KEEP
    if ikeep > 0 and length > 0: # SHIFT [ikeep:] SLICE OF BUFFER TO [0:istart]
      memmove(self.im_buf, self.im_buf + ikeep, length)
    if ikeep < 8: # RUNNING OUT OF ROOM, SO DOUBLE OUR BUFFER
      new_buf = <IntervalMap *>realloc(self.im_buf,
                                       sizeof(IntervalMap) * 2 * self.nbuf)
      if new_buf == NULL:
        raise MemoryError('out of memory')
      self.im_buf = new_buf
      self.nbuf = 2 * self.nbuf
    return istart # RETURN START OF EMPTY BLOCK WHERE WE CAN ADD NEW DATA

  cdef int saveInterval(self, int start, int end, int target_id,
                        int target_start, int target_end):
    'save an interval, expanding array if necessary'
    cdef int i
    if self.nhit >= self.nbuf: # EXPAND ARRAY IF NECESSARY
      self.extend(0)
    i = self.nhit
    self.im_buf[i].start = start # SAVE INTERVAL INFO
    self.im_buf[i].end = end
    self.im_buf[i].target_id = target_id
    self.im_buf[i].target_start = target_start
    self.im_buf[i].target_end = target_end
    self.nhit = i + 1
    return self.nhit

  cdef int nextBlock(self, int *pkeep) except -2:
    'load one more block of overlapping intervals'
    cdef int i
    if self.it == NULL: # ITERATOR IS EXHAUSTED
      return -1
    if pkeep and pkeep[0] >= 0 and pkeep[0] < self.nhit: #MUST KEEP [ikeep:] SLICE
      i = self.extend(pkeep[0]) # MOVE SLICE TO THE FRONT
    else: # WE CAN USE THE WHOLE BUFFER
      i = 0
    if self.db is not None: # ON-DISK DATABASE
      find_file_intervals(self.it, self.start, self.end,
                          self.db.db[0].ii, self.db.db[0].nii,
                          self.db.db[0].subheader, self.db.db[0].nlists,
                          &(self.db.db[0].subheader_file),
                          self.db.db[0].ntop, self.db.db[0].div,
                          self.db.db[0].ifile_idb,
                          self.im_buf + i, self.nbuf - i,
                          &(self.nhit), &(self.it)) # GET NEXT BUFFER CHUNK
    elif self.idb is not None: # IN-MEMORY DATABASE
      find_intervals(self.it, self.start, self.end, self.idb.im, self.idb.ntop,
                     self.idb.subheader, self.idb.nlists, self.im_buf + i, self.nbuf - i,
                     &(self.nhit), &(self.it)) # GET NEXT BUFFER CHUNK
    else:
      raise IOError('Iterator has no database!  Please provide a db argument.')
    self.nhit = self.nhit + i # TOTAL #HITS IN THE BUFFER
    self.ihit = i # START ITERATING FROM START OF NEW HITS
    if pkeep and pkeep[0] >= 0: # RESET ikeep INDEX TO START OF BUFFER
      pkeep[0] = 0
    return self.nhit - self.ihit # RETURN #NEW HITS IN NEXT BLOCK

  cdef IntervalMap *getIntervalMap(self):
    '''return the IntervalMap array loaded by iterator,
    and release it from iterator.  User must free the array!'''
    cdef int len
    cdef IntervalMap *im
    if self.nhit == 0: # NO HITS
      return NULL
    elif self.nhit < self.nbuf: # LARGER BUFFER THAN WE ACTUALLY NEED
      len = sizeof(IntervalMap) * self.nhit # COMPUTE FINAL SIZE
      im =< IntervalMap *>realloc(self.im_buf, len) # COMPACT TO FINAL SIZE
    else: # JUST HAND BACK OUR FULL BUFFER
      im=self.im_buf
    self.im_buf=NULL # RELEASE THIS STORAGE FROM ITERATOR; USER MUST FREE IT!
    return im # HAND BACK THE STORAGE

  cdef int loadAll(self) except -1:
    'load all overlapping interval hits, return count of hits'
    cdef int len, ikeep
    len = 1
    ikeep = 0 # DON'T LET extend DISCARD ANY HITS, KEEP THEM ALL!
    while len > 0: # LOAD BLOCKS UNTIL NO MORE...
      len = self.nextBlock(&ikeep) # LOAD ANOTHER BLOCK OF INTERVALS
    return self.nhit

  cdef int cnext(self, int *pkeep): # C VERSION OF ITERATOR next METHOD
    'get one more overlapping interval'
    cdef int i
    if self.ihit >= self.nhit: # TRY TO GET ONE MORE BUFFER CHUNK OF HITS
      self.nextBlock(pkeep) # LOAD THE NEXT BLOCK IF ANY
    if self.ihit < self.nhit: # RETURN NEXT ITEM FROM BUFFER
      i = self.ihit
      self.ihit = self.ihit + 1 # ADVANCE THE BUFFER COUNTER
      return i
    else: # BUFFER WAS EMPTY, NO HITS TO ITERATE OVER...
      return -1

  cdef int copy(self, IntervalFileDBIterator src):
    'copy items from src to this iterator buffer'
    cdef IntervalMap *new_buf
    if src is None:
      raise ValueError('src is None!  Debug!!')
    if src.nhit > self.nbuf: # NEED TO EXPAND OUR BUFFER
      new_buf = <IntervalMap *>realloc(self.im_buf, src.nhit * sizeof(IntervalMap))
      if new_buf == NULL:
        raise MemoryError('out of memory')
      self.im_buf = new_buf # RECORD NEW BUFFER LOCATION AND SIZE
      self.nbuf = src.nhit
    self.nhit = src.nhit # COPY ARRAY AND SET CORRECT SIZE
    if src.nhit > 0: # ONLY COPY IF NON-EMPTY
      memcpy(self.im_buf, src.im_buf, src.nhit * sizeof(IntervalMap))
    return 0

  def mergeSeq(self):
    'merge intervals into single interval per sequence orientation'
    cdef int i, j, n, id
    if self.nhit <= 0: # NOTHING TO MERGE, SO JUST RETURN
      return 0
    qsort(self.im_buf, self.nhit, sizeof(IntervalMap), target_qsort_cmp) # ORDER BY id,start
    n = 0
    id = -1
    for i from 0 <= i < self.nhit:
      if self.im_buf[i].target_id != id or (self.im_buf[j].target_start < 0 and
                                            self.im_buf[i].target_start >= 0):
        if id >= 0: # WE NEED TO SAVE PREVIOUS INTERVAL
          if n < j: # COPY MERGED INTERVAL TO COMPACTED LOCATION
            memcpy(self.im_buf + n, self.im_buf + j, sizeof(IntervalMap))
          n = n + 1
        j = i # RECORD THIS AS START OF THE NEW SEQUENCE / ORIENTATION
        id = self.im_buf[i].target_id
      elif self.im_buf[i].target_end > self.im_buf[j].target_end:
        self.im_buf[j].target_end = self.im_buf[i].target_end # EXPAND THIS INTERVAL
        self.im_buf[j].end = self.im_buf[i].end # COPY SOURCE SEQ COORDS AS WELL
    if n < j: # COPY LAST MERGED INTERVAL TO COMPACTED LOCATION
      memcpy(self.im_buf + n, self.im_buf + j, sizeof(IntervalMap))
    self.nhit = n + 1 # TOTAL #MERGED INTERVALS
    return self.nhit

  def __iter__(self):
    return self

  # PYTHON VERSION OF next RETURNS HIT AS A TUPLE
  def __next__(self): # PYREX USES THIS NON-STANDARD NAME INSTEAD OF next()!!!
    cdef int i
    i = self.cnext(NULL)
    if i >= 0:
      return (self.im_buf[i].start, self.im_buf[i].end, self.im_buf[i].target_id,
              self.im_buf[i].target_start, self.im_buf[i].target_end)
    else:
      raise StopIteration

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    free_interval_iterator(self.it_alloc)
    if self.im_buf:
      free(self.im_buf)


cdef class IntervalFileDB:

  def __new__(self, filestem=None, mode='r'):
    if filestem is not None and mode == 'r':
      self.open(filestem)

  def open(self, filestem):
    cdef char err_msg[1024]
    self.db = read_binary_files(filestem, err_msg, 1024)
    if self.db == NULL:
      raise IOError(err_msg)

  def find_overlap(self, int start, int end):
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    return IntervalFileDBIterator(start, end, self)

  def find_overlap_list(self, int start, int end):
    cdef int i, nhit
    cdef IntervalIterator *it, *it_alloc
    cdef IntervalMap im_buf[1024]
    self.check_nonempty() # RAISE EXCEPTION IF NO DATA
    it = interval_iterator_alloc()
    it_alloc = it
    l = [] # LIST OF RESULTS TO HAND BACK
    while it:
      find_file_intervals(it, start, end, self.db[0].ii, self.db[0].nii,
                          self.db[0].subheader, self.db[0].nlists,
                          &(self.db[0].subheader_file),
                          self.db[0].ntop, self.db[0].div,
                          self.db[0].ifile_idb, im_buf, 1024,
                          &(nhit), &(it)) # GET NEXT BUFFER CHUNK
      for i from 0 <= i < nhit:
        l.append((im_buf[i].start, im_buf[i].end, im_buf[i].target_id,
                  im_buf[i].target_start, im_buf[i].target_end))
    free_interval_iterator(it_alloc)
    return l

  def check_nonempty(self):
    if self.db == NULL:
      raise IndexError('empty IntervalFileDB, not searchable!')

  def close(self):
    if self.db:
      free_interval_dbfile(self.db)
    self.db = NULL

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.db:
      free_interval_dbfile(self.db)


cdef class NLMSASliceLetters:
  'graph interface to letter graph within this region'

  def __new__(self, NLMSASlice nlmsaSlice):
    self.nlmsaSlice = nlmsaSlice

  def __iter__(self):
    return NLMSASliceIterator(self.nlmsaSlice)

  def __getitem__(self, NLMSANode node):
    return node.nodeEdges()

  def items(self):
    'list of tuples (node,{target_node:edge})'
    l = []
    for node in self:
      l.append((node, node.nodeEdges()))
    return l

  def iteritems(self):
    return iter(self.items())


cdef class NLMSASlice:

  def __new__(self, NLMSASequence ns not None, int start, int stop,
              int id=-1, int offset=0, seq=None):
    cdef int i, j, n, start_max, end_min, start2, stop2, nseq, istart, istop, localQuery
    cdef NLMSASequence ns_lpo
    cdef IntervalFileDBIterator it, it2
    cdef IntervalMap *im, *im2
    cdef int cacheMax

    if seq is None: # GET FROM NLMSASequence
      seq = ns.seq
    self.nlmsaSequence = ns # SAVE BASIC INFO
    self.nlmsa = ns.nlmsaLetters
    self.start = start
    self.stop = stop
    self.offset = offset # ALWAYS STORE offset IN POSITIVE ORIENTATION
    self.seq = seq
    try: # USE PYTHON METHOD TO DO QUERY
      id, ivals = ns.nlmsaLetters.doSlice(seq) # doSlice() RETURNS RAW INTERVALS
      self.id = id # SAVE OUR SEQUENCE'S nlmsa_id
      it = IntervalFileDBIterator(start, stop, rawIvals=ivals) # STORE IN BINARY FMT
      it2 = IntervalFileDBIterator(start, stop) # HOLDER FOR SUBSEQUENT MERGE
      localQuery = 0 # DO NOT PERFORM LOCAL QUERY CODE BELOW!!
    except AttributeError:
      localQuery = 1
    if localQuery: ################################## PERFORM LOCAL QUERY
      if id < 0:
        id = ns.id
      self.id = id
      it2 = None
      if start < 0: # NEED TO TRANSLATE OFFSETS TO MINUS ORIENTATION
        offset = -offset
      if ns.nlmsaLetters.pairwiseMode == 1: # TRANSLATE SEQ DIRECTLY TO LPO
        it = IntervalFileDBIterator(start, stop, rawIvals=((start, stop, ns.id - 1,
                                                        start + offset, stop + offset), ))
        n = 1 # JUST THE SINGLE IDENTITY MAPPING FROM SEQ TO LPO
      else: # PERFORM NORMAL SEQ --> LPO QUERY
        it = IntervalFileDBIterator(start + offset, stop + offset, ns=ns)
        n = it.loadAll() # GET ALL OVERLAPPING INTERVALS
        if n <= 0:
          raise nlmsa_utils.EmptySliceError('this interval is not aligned!')
        for i from 0 <= i < n: # CLIP INTERVALS TO FIT [start:stop]
          it.im_buf[i].start = it.im_buf[i].start - offset # XLATE TO SRC SEQ COORDS
          it.im_buf[i].end = it.im_buf[i].end - offset
          if stop < it.im_buf[i].end: # TRUNCATE TO FIT WITHIN [start:stop]
            it.im_buf[i].target_end = it.im_buf[i].target_end \
                                     + stop - it.im_buf[i].end # CALCULATE NEW ENDPOINT
            it.im_buf[i].end = stop
          if start > it.im_buf[i].start: # CALCULATE NEW STARTPOINT
            it.im_buf[i].target_start = it.im_buf[i].target_start \
                                     + start - it.im_buf[i].start
            it.im_buf[i].start = start

      if ns.is_lpo: # TARGET INTERVALS MUST BE LPO, MUST MAP TO REAL SEQUENCES
        it2 = IntervalFileDBIterator(start, stop) # HOLDER FOR SUBSEQUENT MERGE
      else:
        ns_lpo =ns.nlmsaLetters.seqlist[ns.nlmsaLetters.lpo_id] # DEFAULT LPO
        for i from 0 <= i < n:
          if it.im_buf[i].target_id != ns_lpo.id: # SWITCHING TO A DIFFERENT LPO?
            ns_lpo = ns.nlmsaLetters.seqlist[it.im_buf[i].target_id]
            if not ns_lpo.is_lpo:
              raise ValueError('sequence mapped to non-LPO target??')
          if it2 is None: # NEED TO ALLOCATE NEW ITERATOR
            it2=IntervalFileDBIterator(it.im_buf[i].target_start,
                                       it.im_buf[i].target_end, ns = ns_lpo)
          else: # JUST REUSE THIS ITERATOR WITHOUT REALLOCING MEMORY
            it2.restart(it.im_buf[i].target_start,
                        it.im_buf[i].target_end, None, ns_lpo)
          it2.loadAll() # GET ALL OVERLAPPING INTERVALS
          if it2.nhit <= 0: # NO HITS, SO TRY THE NEXT INTERVAL???
            continue
          im2 = it2.im_buf # ARRAY FROM THIS ITERATOR
          for j from 0 <= j < it2.nhit: # MAP EACH INTERVAL BACK TO ns
            if it.im_buf[i].target_start > im2[j].start: # GET INTERSECTION INTERVAL
              start_max = it.im_buf[i].target_start
            else:
              start_max = im2[j].start
            if it.im_buf[i].target_end < im2[j].end:
              end_min = it.im_buf[i].target_end
            else:
              end_min = im2[j].end
            istart = it.im_buf[i].start + start_max - it.im_buf[i].target_start # SRC COORDS
            istop = it.im_buf[i].start + end_min - it.im_buf[i].target_start
            start2 = im2[j].target_start + start_max - im2[j].start # COORDS IN TARGET
            stop2 = im2[j].target_start + end_min - im2[j].start
            if im2[j].target_id != id or istart != start2 or \
               ns.nlmsaLetters.pairwiseMode == 1: # DISCARD SELF-MATCH
              it.saveInterval(istart, istop, im2[j].target_id, start2, stop2) # SAVE IT!
            assert ns_lpo.id != im2[j].target_id

    if it.nhit <= 0:
      raise nlmsa_utils.EmptySliceError('this interval is not aligned!')
    it2.copy(it) # COPY FULL SET OF SAVED INTERVALS
    self.nseqBounds = it2.mergeSeq() # MERGE TO ONE INTERVAL PER SEQUENCE ORIENTATION
    self.seqBounds = it2.getIntervalMap() # SAVE SORTED ARRAY & DETACH FROM ITERATOR

    self.im = it.getIntervalMap() # RELEASE THIS ARRAY FROM THE ITERATOR
    self.n = it.nhit # TOTAL #INTERVALS SAVED FROM JOIN
    qsort(self.im, self.n, sizeof(IntervalMap), imstart_qsort_cmp) # ORDER BY start

    n = 0
    for i from 0 <= i < self.nseqBounds: # COUNT NON-LPO SEQUENCES
      if not ns.nlmsaLetters.seqlist.is_lpo(self.seqBounds[i].target_id):
        n = n + 1
    self.nrealseq = n # SAVE THE COUNT

    try: # _cache_max=0 TURNS OFF CACHING...
      cacheMax = ns.nlmsaLetters.seqDict._cache_max
    except AttributeError:
      cacheMax = 1 # ALLOW CACHING...
    try:  # SAVE OUR COVERING INTERVALS AS CACHE HINTS IF POSSIBLE...
      saveCache = ns.nlmsaLetters.seqDict.cacheHint
    except AttributeError:
      cacheMax = 0 # TURN OFF CACHING
    if cacheMax > 0: # CONSTRUCT & SAVE DICT OF CACHE HINTS: COVERING INTERVALS
      cacheDict = {}
      if seq is not None:
        try: # ADD A CACHE HINT FOR QUERY SEQ IVAL
          seqID = ns.nlmsaLetters.seqs.getSeqID(seq) # GET FULL-LENGTH ID
          cacheDict[seqID] = (self.start, self.stop)
        except KeyError:
          pass
      for i from 0 <= i < self.nseqBounds: # ONLY SAVE NON-LPO SEQUENCES
        if not ns.nlmsaLetters.seqlist.is_lpo(self.seqBounds[i].target_id):
          cacheDict[ns.nlmsaLetters.seqlist.getSeqID(self.seqBounds[i].target_id)] = (self.seqBounds[i].target_start, self.seqBounds[i].target_end)

      if cacheDict:
        self.weakestLink = nlmsa_utils.SeqCacheOwner()
        saveCache(cacheDict, self.weakestLink) # SAVE COVERING IVALS AS CACHE HINT

  def __hash__(self):
    return id(self)

  def __repr__(self):
    return "<NLMSASlice object at 0x%x (seq=%s)>" % (id(self), self.seq.id, )

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.im:
      free(self.im)
      self.im = NULL
    if self.seqBounds:
      free(self.seqBounds)
      self.seqBounds = NULL

  cdef object get_seq_interval(self, NLMSA nl, int targetID,
                               int start, int stop):
    'get seq interval and ensure cache owner keeps it in the cache'
    if start < stop:
      ival = nl.seqInterval(targetID, start, stop)
    else:  # GET THE SEQUENCE OBJECT
      ival = nl.seqlist.getSeq(targetID)
    try: # tell owner to keep it in the cache
      self.weakestLink.cache_reference(ival.pathForward)
    except AttributeError:
      pass
    return ival

  ########################################### ITERATOR METHODS
  def edges(self, mergeAll=False, **kwargs):
    'get list of tuples (srcIval, destIval, edge) aligned in this slice'
    seqIntervals = self.groupByIntervals(mergeAll=mergeAll, **kwargs)
    ivals = self.groupBySequences(seqIntervals, **kwargs)
    l = []
    for ival1, ival2, mergeIntervals in ivals:
      l.append((ival1, ival2, sequence.Seq2SeqEdge(self, ival2, ival1, mergeIntervals)))
    return l

  def items(self, **kwargs):
    'get list of tuples (ival2,edge) aligned to this slice'
    l = []
    for ival1, ival2, edge in self.edges(**kwargs):
      l.append((ival2, edge))
    return l

  def iteritems(self, **kwargs):
    return iter(self.items(**kwargs))

  def keys(self, mergeAll=False, **kwargs):
    'get list of intervals aligned to this slice according to groupBy options'
    seqIntervals = self.groupByIntervals(mergeAll=mergeAll, **kwargs)
    ivals = self.groupBySequences(seqIntervals, **kwargs)
    l = []
    for ival1, ival2, mergeIntervals in ivals:
      l.append(ival2)
    return l

  def __iter__(self): # PYREX DOESNT ALLOW ARGS TO __iter__ !
    return iter(self.keys())

  def __getitem__(self, k):
    return sequence.Seq2SeqEdge(self, k)

  def __setitem__(self, k, v):
    raise ValueError('''this NLMSA is read-only!  Currently, you cannot add new
alignment intervals to an NLMSA after calling its build() method.''')

  def __len__(self):
    return self.nrealseq # NUMBER OF NON-LPO SEQUENCE/ORIS ALIGNED HERE

  ##################################### 1:1 INTERVAL METHODS
  def matchIntervals(self, seq=None):
    '''get all 1:1 match intervals in this region of alignment
    as list of tuples.  if seq argument not None, only match intervals
    for that sequence will be included.  No clipping is performed.'''
    cdef int i, target_id
    cdef NLMSA nl
    nl = self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    if seq is not None:
      target_id = nl.seqs.getID(seq) # CHECK IF IN OUR ALIGNMENT
    else:
      target_id = -1
    l = []
    for i from 0 <= i < self.n: # GET ALL STORED INTERVALS
      if not nl.seqlist.is_lpo(self.im[i].target_id) and \
               (target_id < 0 or self.im[i].target_id == target_id):
        ival2 = nl.seqInterval(self.im[i].target_id, self.im[i].target_start,
                               self.im[i].target_end)
        if seq is None or ival2.orientation == seq.orientation:
          ival1 = sequence.absoluteSlice(self.seq,
                                        self.im[i].start, self.im[i].end)
          l.append((ival1, ival2)) # SAVE THE INTERVAL MATCH
    return l

  ############################## MAXIMUM INTERVAL METHODS
  cdef int findSeqBounds(self, int id, int ori):
    'find the specified sequence / orientation using binary search'
    cdef int left, right, mid
    left = 0
    right = self.nseqBounds
    while left < right:
      mid = (left + right) / 2
      if self.seqBounds[mid].target_id < id:
        left = mid + 1
      elif self.seqBounds[mid].target_id > id:
        right = mid
      elif ori > 0 and seqBounds[mid].target_start < 0:
        left = mid + 1
      elif ori < 0 and seqBounds[mid].target_start >= 0:
        right = mid
      else: # MATCHES BOTH id AND ori
        return mid
    return -1 # FAILED TO FIND id,ori MATCH

  def findSeqEnds(self, seq):
    'get maximum interval of seq aligned in this interval'
    cdef int i, id
    cdef NLMSA nl
    nl = self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    id = nl.seqs.getID(seq) # CHECK IF IN OUR ALIGNMENT
    i = self.findSeqBounds(id, seq.orientation) # FIND THIS id,ORIENTATION
    if i < 0: # NOT FOUND!
      raise KeyError('seq not aligned in this interval')
    return self.get_seq_interval(nl, self.seqBounds[i].target_id,
                                 self.seqBounds[i].target_start,
                                 self.seqBounds[i].target_end)

  def generateSeqEnds(self):
    'get list of tuples (ival1,ival2,edge)'
    cdef int i
    cdef NLMSA nl
    nl = self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l = []
    for i from 0 <= i < self.nseqBounds:
      if nl.seqlist.is_lpo(self.seqBounds[i].target_id):
        continue  # DON'T RETURN EDGES TO LPO
      #ival1 = sequence.absoluteSlice(self.seq, self.seqBounds[i].start,
      #                               self.seqBounds[i].end)
      ival2 = self.get_seq_interval(nl, self.seqBounds[i].target_id,
                                    self.seqBounds[i].target_start,
                                    self.seqBounds[i].target_end)
      #l.append((ival1,ival2,sequence.Seq2SeqEdge(self,ival2,ival1)))
      edge = self[ival2] # LET edge FIGURE OUT sourcePath FOR US
      l.append((edge.sourcePath, ival2, edge))
    return l

  ############################################## GROUP-BY METHODS
  def groupByIntervals(self, int maxgap=0, int maxinsert=0,
                       int mininsert=0, filterSeqs=None, filterList=None,
                       mergeMost=False, maxsize=500000000,
                       mergeAll=True, ivalMethod=None, **kwargs):
    '''merge alignment intervals using "horizontal" group-by rules:
      - maxgap (=0): longest gap allowed within a region
      - maxinsert (=0): longest insert allowed within a region
      - mininsert (=0): should be 0, to prevent cycles within a region
        use negative values to allow some overlap / cycles.
      - maxsize: upper bound on maximum size for interval merging
      - mergeMost: merge, but with limits (10000, 10000, -10, 50000)
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
    cdef int i, j, n, gap, insert, targetStart, targetEnd, start, end, maskStart, maskEnd
    cdef NLMSA nl
    nl = self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    if mergeMost: # BE REASONABLE: DON'T MERGE A WHOLE CHROMOSOME
      maxgap = 10000
      maxinsert = 10000
      mininsert = -10 # ALLOW SOME OVERLAP IN INTERVAL ALIGNMENTS
      maxsize = 50000
    if filterList is not None:
      targetDict = {}
      for seq in filterList: # CREATE AN INDEX OF SEQUENCE IDs TO KEEP
        t = nl.seqs.getIDcoords(seq)
        targetDict[t[0]] = t[1:] # SAVE START,STOP
    seqIntervals = {}
    for i from 0 <= i < self.n: # LIST INTERVALS FOR EACH TARGET
      if nl.seqlist.is_lpo(self.im[i].target_id):
        continue # IT IS AN LPO, SO SKIP IT
      start = self.im[i].start
      end = self.im[i].end
      targetStart = self.im[i].target_start
      targetEnd = self.im[i].target_end
      if filterList is not None:
        try: # CHECK IF SEQUENCE IS IN MASKING DICTIONARY
          maskStart, maskEnd = targetDict[self.im[i].target_id]
        except KeyError:
          continue # FILTER THIS SEQUENCE OUT OF THE RESULT SET
        if start >= maskEnd or end <= maskStart: # NO OVERLAP
          continue
        if start < maskStart: # CLIP START TO MASKED REGION
          targetStart = targetStart+maskStart-start
          start = maskStart
        if end > maskEnd:# CLIP END TO MASKED REGION
          targetEnd = targetEnd+maskEnd-end
          end = maskEnd
      elif filterSeqs is not None: # CLIP TARGET SEQ INTERVAL
        target = self.get_seq_interval(nl, self.im[i].target_id,
                                       targetStart, targetEnd)
        try:
          target = filterSeqs[target] # PERFORM CLIPPING
        except KeyError: # NO OVERLAP IN filterSeqs, SO SKIP
          continue
        start = start + target.start - targetStart # CLIP SOURCE SEQUENCE
        end = end + target.stop - targetEnd
        targetStart = target.start  # GET COORDS OF CLIPPED TARGET
        targetEnd = target.stop
      try: # ADD INTERVAL TO EXISTING LIST
        seqIntervals[self.im[i].target_id] \
             .append([start, end, targetStart, targetEnd, None])
      except KeyError: # CREATE A NEW LIST FOR THIS TARGET
        seqIntervals[self.im[i].target_id] = \
           [[start, end, targetStart, targetEnd, None]]

    for i, l in seqIntervals.iteritems(): # MERGE INTERVALS FOR EACH SEQ
      if ivalMethod is not None: # USER-SUPPLIED GROUPING FUNCTION
        ivalMethod(l, nl.seqlist.getSeq(i), msaSlice=self, maxgap=maxgap,
                   maxinsert=maxinsert, mininsert=mininsert,
                   filterSeqs=filterSeqs, mergeAll=mergeAll, **kwargs)
        continue # NO NEED TO APPLY GENERIC MERGING OPERATION BELOW
      n = 0
      for j from 1 <= j < len(l): # MERGE BY INDEL LENGTH RULES
        gap = l[j][0] - l[n][1] # current.start - last.end
        insert = l[j][2] - l[n][3] # current.target_start - last.target_end
        if not mergeAll and \
               (gap > maxgap or insert > maxinsert or insert < mininsert or
                l[j][1] - l[n][0] > maxsize or
                l[j][3] - l[n][2] > maxsize):
          n = n + 1 # SPLIT, SO START A NEW INTERVAL
          if n < j: # COPY START COORDS TO NEW SLOT
            l[n][0] = l[j][0]
            l[n][2] = l[j][2]
        else: # INTERVALS MERGED: SAVE ORIGINAL 1:1 INTERVAL LIST
          try:
            lastIval = l[n][4][-1] # GET LAST 1:1 INTERVAL
          except TypeError: # EMPTY LIST: CREATE ONE
            if l[n][1] == l[j][0] and l[n][3] == l[j][2]: # NO GAP, SO MERGE
              l[n][4] = [(l[n][0], l[j][1], l[n][2], l[j][3])]
            else: # TWO SEPARATE 1:1 INTERVALS
              l[n][4] = [tuple(l[n][:4]), tuple(l[j][:4])]
          else: # SEE IF WE CAN FUSE TO LAST 1:1 INTERVAL
            if lastIval[1] == l[j][0] and lastIval[3] == l[j][2]:
              l[n][4][-1] = (lastIval[0], l[j][1], lastIval[2], l[j][3])
            else: # GAP, SO JUST APPEND THIS 1:1 INTERVAL
              l[n][4].append(tuple(l[j][:4]))
        if n < j: # COPY END COORDS TO CURRENT SLOT
          l[n][1] = l[j][1]
          l[n][3] = l[j][3]
      del l[n+1:] # DELETE REMAINING UNMERGED INTERVALS
      for m in l: # CULL SINGLETON 1:1 INTERVAL LISTS (DUE TO FUSION)
        try:
          if len(m[4]) == 1: # TWO INTERVALS MUST HAVE BEEN FUSED
            m[4] = None # NO NEED TO KEEP SINGLETON!
        except TypeError:
          pass
    # SEQUENCE MASKING BY CONSERVATION OR %ALIGNED CONSTRAINT
    if 'pAlignedMin' in kwargs or 'pIdentityMin' in kwargs or \
           'minAlignSize' in kwargs or 'maxAlignSize' in kwargs:
      self.filterIvalConservation(seqIntervals, **kwargs)
    return seqIntervals

  def conservationFilter(self, seq, m, pIdentityMin=None,
                         minAlignSize=None, maxAlignSize=None, **kwargs):
    if minAlignSize is not None and m[1] - m[0] < minAlignSize:
      return None
    if maxAlignSize is not None and m[1] - m[0] > maxAlignSize:
      return None
    if pIdentityMin is not None:
      seqEdge = sequence.Seq2SeqEdge(self, sequence.relativeSlice(seq, m[2], m[3]),
                                     sequence.absoluteSlice(self.seq, m[0], m[1]), m[4])
      t = seqEdge.conservedSegment(pIdentityMin=pIdentityMin, # GET CLIPPED INTERVAL
                                   minAlignSize=minAlignSize, **kwargs)
      if t is None:
        return None
      mergeIntervals = self.clip_interval_list(t[0], t[1], m[4]) # CLIP mergeIntervals
      return list(t) + [mergeIntervals] # RECOMBINE
    else:
      return m
##     if pAlignedMin is not None and seqEdge.pAligned()<pAlignedMin:
##       return False # INTERVAL FAILED ALIGNMENT THRESHOLD, SO REMOVE IT
##     if pIdentityMin is not None and seqEdge.pIdentity()<pIdentityMin:
##       return False # INTERVAL FAILED CONSERVATION THRESHOLD, SO REMOVE IT
##     return True

  def filterIvalConservation(self, seqIntervals, pIdentityMin=None,
                             filterFun=None, **kwargs):
    cdef int i, j
    cdef NLMSA nl
    import types
    if filterFun is None:
      filterFun = self.conservationFilter
    nl = self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    pIdentityMin0 = pIdentityMin
    for targetID, l in seqIntervals.items(): # MERGE INTERVALS FOR EACH SEQ
      seq = self.get_seq_interval(nl, targetID, 0, 0) # GET THE SEQUENCE OBJECT
      if pIdentityMin0 is not None and not isinstance(pIdentityMin0, types.FloatType):
        try:
          pIdentityMin = pIdentityMin0[seq] # LOOK UP DESIRED IDENTITY FOR THIS SEQ
        except KeyError:
          del seqIntervals[targetID] # SO REMOVE TARGET ENTIRELY
          continue # NO NEED TO PROCESS THIS TARGET ANY FURTHER
      j = 0
      for i from 0 <= i < len(l): # CHECK EACH INTERVAL FOR CONSERVATION THRESHOLD
        newIval = filterFun(seq, l[i], pIdentityMin=pIdentityMin, **kwargs)
        if newIval is None:
          continue # l[i] FAILED FILTER CRITERIA, SO SKIP IT
        l[j] = newIval # COMPACT THE ARRAY: KEEP newIval IN LOCATION j
        j = j + 1 # KEEP THIS ARRAY ENTRY, SO INCREMENT COUNT OF ENTRIES
      if j == 0: # NO INTERVALS FOR THIS SEQUENCE SURVIVED MASKING
        del seqIntervals[targetID] # SO REMOVE TARGET ENTIRELY
      elif j < i: # SOME INTERVALS REMOVED, SO SHRINK ITS LIST
        del l[j:] # JUST TRUNCATE THE LIST TO ENTRIES THAT PASSED

  def groupBySequences(self, seqIntervals, sourceOnly=False,
                       indelCut=False, seqGroups=None, minAligned=1,
                       pMinAligned=0., seqMethod=None, **kwargs):
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
    cdef int i, j, start, end, targetStart, targetEnd, ipos, id
    cdef float f
    cdef NLMSA nl
    nl = self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    if seqGroups is None:
      seqGroups = [seqIntervals] # JUST USE THE WHOLE SET
    result = []
    import mapping # GET ACCESS TO DictQueue CLASS
    for seqs in seqGroups: # PROCESS EACH SEQ GROUP
      bounds = []
      j = 0
      for seq in seqs: # CONSTRUCT INTERVAL BOUNDS LIST
        if isinstance(seq, int): # seqIntervals USES INT INDEX VALUES
          id = seq # SAVE THE ID
          seq = self.get_seq_interval(nl, id, 0, 0) # GET THE SEQUENCE OBJECT
        else: # EXPECT USER TO SUPPLY ACTUAL SEQUENCE OBJECTS
          id = nl.seqs.getID(seq)
          seq = seq.pathForward # ENSURE WE HAVE TOP-LEVEL SEQ OBJECT
        try:
          ivals = seqIntervals[id]
        except KeyError: # SEQUENCE NOT IN THIS ALIGNMENT REGION, SO SKIP
          continue
        isIndel = False
        for ival in ivals:
          bounds.append((ival[1], False, j, seq, isIndel, ival))
          bounds.append((ival[0], True, j, seq, isIndel, ival))
          isIndel = True
        j = j + 1 # SEQUENCE COUNTER ENSURES ORDER OF SEQS IN SORTED LIST
      bounds.sort() # ASCENDING ORDER OF source_pos, SORT stop B4 start
      if seqMethod is not None:
        result = result + seqMethod(bounds, seqs, sourceOnly=sourceOnly,
                                    msaSlice=self, minAligned=minAligned,
                                    pMinAligned=pMinAligned,
                                    indelCut=indelCut, **kwargs)
        continue # DON'T USE GENERIC GROUPING METHOD BELOW
      seqStart = mapping.DictQueue() # setitem PUSHES, delitem POPS
      maskStart = None
      for bound in bounds: # GENERIC GROUPING: APPLY MASKING, sourceOnly
        ipos, isStart, j, seq, isIndel = bound[0:5]
        if isStart: # INTERVAL START
          seqStart[seq] = bound[5] # JUST RECORD START OF INTERVAL
        else: # INTERVAL STOP
          start, end, targetStart, targetEnd, mergeIntervals = bound[5]
          if maskStart is not None and not sourceOnly: # SAVE TARGET IVAL
            if maskStart > start: # TRUNCATE TARGET IVAL START
              targetStart = targetStart + maskStart - start
              start = maskStart
              mergeIntervals = self.clip_interval_list(maskStart, None, mergeIntervals)
            result.append((sequence.absoluteSlice(self.seq, start, end),
                           sequence.relativeSlice(seq, targetStart,
                                                  targetEnd), mergeIntervals))
          del seqStart[seq] # POP THIS SEQ FROM START DICT

        f = len(seqStart) # #ALIGNED SEQS IN THIS REGION
        if f < minAligned or f / len(seqs) < pMinAligned: # APPLY MASKING
          if maskStart is not None:
            if sourceOnly: # JUST SAVE MERGED SOURCE INTERVAL
              result.append(sequence.absoluteSlice(self.seq, maskStart, end))
            else: # REPORT TARGET IVALS WITHIN (maskStart,end) REGION
              for seq in seqStart: # CANNOT USE items() BECAUSE THIS IS A QUEUE!
                (start, i, targetStart, targetEnd, mergeIntervals) = seqStart[seq]
                pleaseClip = False
                if maskStart > start: # TRUNCATE TARGET IVAL START
                  targetStart = targetStart + maskStart - start
                  start = maskStart
                  pleaseClip = True
                if end < i: # TRUNCATE TARGET IVAL END
                  targetEnd = targetEnd + end - i
                  pleaseClip = True
                if pleaseClip:
                  mergeIntervals = self.clip_interval_list(maskStart, end, mergeIntervals)
                result.append((sequence.absoluteSlice(self.seq, start, end),
                               sequence.relativeSlice(seq, targetStart,
                                                      targetEnd), mergeIntervals))
            maskStart = None # REGION NOW BELOW THRESHOLD
        elif maskStart is None:
          maskStart = ipos # START OF REGION ABOVE THRESHOLD
        if maskStart is not None and sourceOnly and indelCut and \
           isIndel and maskStart < ipos:
          result.append(sequence.absoluteSlice(self.seq, maskStart, ipos))
          maskStart = ipos
    return result

  def clip_interval_list(self, start, end, l):
    'truncate list of 1:1 intervals using start,end'
    if l is None:
      return None
    result = []
    for srcStart, srcEnd, destStart, destEnd in l:
      if (start is not None and start >= srcEnd) or (end is not None and end <= srcStart):
        continue
      if start is not None and start > srcStart:
        destStart = destStart + start - srcStart
        srcStart = start
      if end is not None and end < srcEnd:
        destEnd = destEnd + end - srcEnd
        srcEnd = end
      result.append((srcStart, srcEnd, destStart, destEnd))
    if len(result) < 2:
      return None
    else:
      return result

  ############################################## LPO REGION METHODS
  def split(self, minAligned=0, **kwargs):
    '''Use groupByIntervals() and groupBySequences() methods to
    divide this slice into subslices using indel rules etc.'''
    seqIntervals = self.groupByIntervals(**kwargs)
    kwargs['sourceOnly'] = True
    kwargs['indelCut'] = True
    ivals = self.groupBySequences(seqIntervals, minAligned=minAligned,
                                  **kwargs)
    l = []
    for ival in ivals:
      if ival.start == self.start and ival.stop == self.stop:
        l.append(self) # SAME INTERVAL, SO JUST RETURN self
      else:
        subslice = NLMSASlice(self.nlmsaSequence, ival.start, ival.stop,
                            self.id, self.offset, self.seq)
        l.append(subslice)
    return l

  def regions(self, dummyArg=None, **kwargs):
    '''get LPO region(s) corresponding to this interval
    Same group-by rules apply here as for the split() method.'''
    cdef int i
    cdef NLMSA nl
    cdef NLMSASequence ns_lpo
    if self.nlmsaSequence.is_lpo: # ALREADY AN LPO REGION!
      return self.split(**kwargs) # JUST APPLY GROUP-BY RULES TO  self
    nl = self.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l = []
    for i from 0 <= i < self.nseqBounds:
      ns_lpo = nl.seqlist[self.seqBounds[i].target_id]
      if ns_lpo.is_lpo: # ADD ALL LPO INTERVALS ALIGNED HERE
        subslice = NLMSASlice(ns_lpo, self.seqBounds[i].target_start,
                              self.seqBounds[i].target_end)
        l = l + subslice.split(**kwargs) # APPLY GROUP-BY RULES
    if len(l) > 0:
      return l
    raise ValueError('no LPO in nlmsaSlice.seqBounds?  Debug!')


  ########################################### LETTER METHODS
  property letters:
    'interface to individual LPO letters in this interval'

    def __get__(self):
      return NLMSASliceLetters(self)

  def __cmp__(self, other):
    if isinstance(other, NLMSASlice):
      return cmp(self.nlmsaSequence, other.nlmsaSequence)
    else:
      return -1

  def rawIvals(self):
    'return list of raw numeric intervals in this slice'
    cdef int i
    l = []
    for i from 0 <= i < self.n:
      l.append((self.im[i].start, self.im[i].end, self.im[i].target_id,
                self.im[i].target_start, self.im[i].target_end))
    return l


def advanceStartStop(int ipos, NLMSASlice nlmsaSlice not None,
                     int istart, int istop):
  cdef int i
  if istop >= nlmsaSlice.n:
    raise IndexError('out of bounds')
  for i from istop <= i < nlmsaSlice.n:
    if ipos >= nlmsaSlice.im[i].start: # ENTERS THIS INTERVAL
      istop = i + 1 # ADVANCE THE END MARKER
    else:
      break # BEYOND ipos, SEARCH NO FURTHR
  for i from istart <= i < istop: # FIND 1ST OVERLAP
    if ipos < nlmsaSlice.im[i].end:
      break
  return i, istop


cdef class NLMSASliceIterator:
  'generate letters (nodes) in this LPO slice'

  def __new__(self, NLMSASlice nlmsaSlice not None):
    self.nlmsaSlice = nlmsaSlice
    self.ipos = nlmsaSlice.start - 1

  def __iter__(self):
    return self

  def __next__(self):
    self.ipos = self.ipos + 1
    # ADJUST istart,istop TO OVERLAP ipos
    self.istart, self.istop = \
      advanceStartStop(self.ipos, self.nlmsaSlice, self.istart, self.istop)
    if self.istart >= self.istop: # HMM, NO OVERLAPS TO ipos
      if self.istop < self.nlmsaSlice.n: # ANY MORE INTERVALS?
        self.ipos = self.nlmsaSlice.im[self.istop].start # START OF NEXT INTERVAL
        # ADJUST istart,istop TO OVERLAP ipos
        self.istart, self.istop = \
          advanceStartStop(self.ipos, self.nlmsaSlice, self.istart, self.istop)
      else:
        raise StopIteration # NO MORE POSITIONS IN THIS SLICE
    return NLMSANode(self.ipos, self.nlmsaSlice, self.istart, self.istop)


cdef class NLMSANode:
  'interface to a node in NLMSA storage of LPO alignment'

  def __new__(self, int ipos, NLMSASlice nlmsaSlice not None,
              int istart=0, int istop=-1):
    cdef int i, n
    cdef NLMSA nl
    self.nlmsaSlice = nlmsaSlice
    nl = nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    self.ipos = ipos
    if istop < 0:
      istart, istop = \
        advanceStartStop(ipos, nlmsaSlice, istart, istart) # COMPUTE PROPER BOUNDS
    self.istart = istart # SAVE BOUNDS
    self.istop = istop
    self.id = ipos # DEFAULT: ASSUME SLICE IS IN LPO...
    for i from istart <= i < istop:
      if nlmsaSlice.im[i].start<=ipos and ipos<nlmsaSlice.im[i].end:
        if nl.seqlist.is_lpo(nlmsaSlice.im[i].target_id):
          self.id = nlmsaSlice.im[i].target_start + ipos - nlmsaSlice.im[i].start #LPO ipos
        else: # DON'T COUNT THE LPO SEQUENCE
          self.n = self.n + 1

  ############################################# ALIGNED LETTER METHODS
  def __len__(self):
    return self.n

  def __iter__(self):
    cdef int i, j
    cdef NLMSA nl
    nl = self.nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    l = []
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].start <= self.ipos and \
         self.ipos < self.nlmsaSlice.im[i].end and \
         not nl.seqlist.is_lpo(self.nlmsaSlice.im[i].target_id):
        j = self.nlmsaSlice.im[i].target_start + self.ipos - self.nlmsaSlice.im[i].start
        l.append(nl.seqInterval(self.nlmsaSlice.im[i].target_id, j, j + 1))
    return iter(l)

  def getSeqPos(self, seq):
    'return seqpos for this seq at this node'
    cdef int i, j, id
    try:
      id = self.nlmsaSlice.nlmsaSequence.nlmsaLetters.seqs.getID(seq)
    except KeyError:
      raise KeyError('seq not in this alignment')
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].target_id == id: # RETURN THE SEQUENCE INTERVAL
        j = self.nlmsaSlice.im[i].target_start + self.ipos - self.nlmsaSlice.im[i].start
        return sequence.absoluteSlice(seq, j, j + 1)
    raise KeyError('seq not in node')

  property edges:
    "get this node's edges as list of tuples (ival1, ival2, edge)"

    def __get__(self):
      l = []
      ival1 = sequence.absoluteSlice(self.nlmsaSlice.seq,
                                     self.ipos, self.ipos + 1) # OUR SEQ INTERVAL
      for ival2 in self:
        l.append((ival1, ival2, None)) # GET EDGE INFO!!!
      return l

  def __getitem__(self, seq):
    raise NotImplementedError('hey! write some code here!')
##     from lpo import POMSANodeRef # PROBABLY WONT NEED THIS AFTER RENAMING!!!
##     try:
##       s = self.getSeqPos(seq)
##       return POMSANodeRef(self, seq.path)
##     else:
##       raise KeyError('seq not in node')

  def __cmp__(self, other):
    if isinstance(other, NLMSANode):
      return cmp((self.nlmsaSlice, ipos), (other.nlmsaSlice, ipos))
    else:
      return -1

  ########################################## NODE-TO-NODE EDGE METHODS
  cdef int check_edge(self, int iseq, int ipos):
    cdef int i
    for i from self.istart <= i < self.istop:
      if self.nlmsaSlice.im[i].start <= self.ipos and \
         self.ipos < self.nlmsaSlice.im[i].end and \
         self.nlmsaSlice.im[i].target_id == iseq and \
         self.nlmsaSlice.im[i].target_start == ipos:
        return 1 # MATCH!
    return 0 # NO MATCH!

  def getEdgeSeqs(self, NLMSANode other):
    "return dict of sequences that traverse edge from self -> other"
    cdef int i
    cdef NLMSA nl
    nl = self.nlmsaSlice.nlmsaSequence.nlmsaLetters # GET TOPLEVEL LETTERS OBJECT
    d = {}
    if self.id + 1 == other.id: #other ADJACENT IN LPO
      for i from self.istart <= i < self.istop:
        if self.nlmsaSlice.im[i].start <= self.ipos + 1 and \
           self.ipos + 1 < self.nlmsaSlice.im[i].end: # INTERVAL CONTAINS other
          seq = nl.seqlist.getSeq(self.nlmsaSlice.im[i].target_id)
          d[seq] = self.nlmsaSlice.im[i].target_start + self.ipos - self.nlmsaSlice.im[i].start
        elif self.ipos + 1 == self.im[i].end and \
                other.check_edge(self.nlmsaSlice.im[i].target_id,
                                 self.nlmsaSlice.im[i].target_end):
          seq = nl.seqlist.getSeq(self.nlmsaSlice.im[i].target_id) # BRIDGE TO NEXT INTERVAL
          d[seq] = self.nlmsaSlice.im[i].target_start + self.ipos - self.nlmsaSlice.im[i].start
    else: # other NOT ADJACENT, SO INTERVALS THAT END HERE MIGHT JUMP TO other
      for i from self.istart <= i < self.istop:
        if self.ipos + 1 == self.nlmsaSlice.im[i].end and \
           other.check_edge(self.nlmsaSlice.im[i].target_id,
                            self.nlmsaSlice.im[i].target_end):
          seq = nl.seqlist.getSeq(self.nlmsaSlice.im[i].target_id) # BRIDGE TO NEXT INTERVAL
          d[seq] = self.nlmsaSlice.im[i].target_start + self.ipos - self.nlmsaSlice.im[i].start
    return d

  def nodeEdges(self):
    'get all outgoing edges from this node'
    cdef int i, has_continuation
    has_continuation = -1
    d = {}
    nodes = {} # LIST OF TARGET NODES WE HAVE AN EDGE TO
    for i from self.istart <= i < self.nlmsaSlice.n:
      if i >= self.istop and len(d) == 0: # NO FURTHER CHECKS TO DO
        break
      if self.nlmsaSlice.im[i].start <= self.ipos and \
         self.ipos < self.nlmsaSlice.im[i].end - 1:
        has_continuation = i # ipos INSIDE THIS INTERVAL, SO HAS EDGE TO ipos+1
      elif self.ipos == self.nlmsaSlice.im[i].end - 1: # END OF THIS INTERVAL
        d[self.nlmsaSlice.im[i].target_id] = self.nlmsaSlice.im[i].target_end
      else:
        try: # CHECK FOR START OF AN "ADJACENT" INTERVAL
          if d[self.nlmsaSlice.im[i].target_id] == self.nlmsaSlice.im[i].target_start:
            nodes[self.nlmsaSlice.im[i].start] = i
            del d[self.nlmsaSlice.im[i].target_id] # REMOVE FROM ADJACENCY LIST
        except KeyError:
          pass
    if has_continuation >= 0:
      nodes[self.ipos + 1] = has_continuation
    result = {}
    for i in nodes:
      node = NLMSANode(i, self.nlmsaSlice, self.istart)
      result[node] = sequence.LetterEdge(self, node) # EDGE OBJECT
    return result


cdef class NLMSASequence:
  'sequence interface to NLMSA storage of an LPO alignment'

  def __init__(self, NLMSA nl not None, filestem, seq, mode='r', is_union=0,
               length=None):
    self.nlmsaLetters = nl
    self.filestem = filestem
    self.is_union = is_union
    self.is_lpo = 0 # DEFAULT: NOT AN LPO
    self.seq = seq
    if length is not None: # ALLOW USER TO SUPPLY A LENGTH FOR THIS COORD SYSTEM
      self.length = length
    import types
    if isinstance(seq, types.StringType):
      self.name = seq # ALLOW USER TO BUILD INDEXES WITH A STRING NAME
    elif seq is not None: # REGULAR SEQUENCE
      seq = seq.pathForward # GET THE WHOLE SEQUENCE, IN FORWARD ORIENTATION
      try: # MAKE SURE seq HAS A UNIQUE NAME FOR INDEXING IT...
        self.name = str(seq.path.name)
      except AttributeError:
        try:
          self.name = str(seq.path.id)
        except AttributeError:
          raise AttributeError('NLMSASequence: seq must have name or id attribute')
    else:
      self.length = 0 # LPO AND UNION SEQUENCES EXPAND AUTOMATICALLY
      if not is_union:
        self.is_lpo = 1
        if len(nl.lpoList) > 0:  # CALCULATE OFFSET OF NEW LPO, BASED ON LAST LPO
          lastLPO = nl.lpoList[-1]
          self.offset = lastLPO.offset + lastLPO.length
        else:
          self.offset = 0
        nl.lpoList.append(self) # ADD TO THE LPO LIST
    self.idb = None # DEFAULT: NOT USING IN-MEMORY DATABASE.
    self.db = None # DEFAULT: WAIT TO OPEN DB UNTIL ACTUALLY NEEDED
    if mode == 'r': # IMMEDIATELY OPEN DATABASE, UNLIKE onDemand MODE
      self.db = IntervalFileDB(filestem, mode)
    elif mode == 'memory': # OPEN IN-MEMORY DATABASE
      self.idb = IntervalDB()
    elif mode == 'w': # WRITE .build FILE
      filename = filestem + '.build'
      self.build_ifile = fopen(filename, 'wb') # binary file
      if self.build_ifile == NULL:
        errmsg = 'unable to open in write mode: ' + filename
        raise IOError(errmsg)
      self.nbuild = 0

  def __dealloc__(self):
    'remember: dealloc cannot call other methods!'
    if self.build_ifile:
      fclose(self.build_ifile)

  def forceLoad(self):
    'force database to be initialized, if not already open'
    self.db = IntervalFileDB(self.filestem, 'r')

  def close(self):
    'free memory and close files associated with this sequence index'
    if self.db is not None:
      self.db.close() # CLOSE THE DATABASE, RELEASE MEMORY
      self.db = None # DISCONNECT FROM DATABASE
    if self.idb is not None:
      self.idb.close() # CLOSE THE DATABASE, RELEASE MEMORY
      self.idb = None # DISCONNECT FROM DATABASE
    if self.build_ifile:
      fclose(self.build_ifile)
      self.build_ifile = NULL

  def buildFiles(self, **kwargs):
    'build nested list from saved unsorted alignment data'
    cdef IntervalDB db
    if self.build_ifile == NULL:
      raise IOError('not opened in write mode')
    fclose(self.build_ifile)
    self.build_ifile = NULL
    filename = self.filestem + '.build'
    db = IntervalDB() # CREATE EMPTY NL IN MEMORY
    if self.nbuild > 0:
      db.buildFromUnsortedFile(filename, self.nbuild, **kwargs) # BUILD FROM .build
    db.write_binaries(self.filestem) # SAVE AS IntervalDBFile
    db.close() # DUMP NESTEDLIST FROM MEMORY
    import os
    os.remove(filename) # REMOVE OUR .build FILE, NO LONGER NEEDED
    self.db = IntervalFileDB(self.filestem) # NOW OPEN THE IntervalFileDB
    return self.nbuild # return count of intervals

  def buildInMemory(self, **kwargs):
    try:
      n = len(self.buildList)
    except TypeError:
      return 0
    else:
      self.idb.save_tuples(self.buildList, **kwargs)
      self.buildList = None
      return n

  cdef int saveInterval(self, IntervalMap im[], int n, int expand_self, FILE *ifile):
    cdef int i
    if ifile == NULL:
      raise IOError('not opened in write mode')
    if expand_self: # AN LPO THAT EXPANDS AS WE ADD TO IT...
      for i from 0 <= i < n:
        if im[i].start >= 0:
          if im[i].end > self.length: # EXPAND IT...
            self.length = im[i].end
        elif -(im[i].start) > self.length:
          self.length= -(im[i].start) # THIS HANDLES NEGATIVE ORI CASE
    i = write_padded_binary(im, n, 1, ifile)
    if i != n:
      raise IOError('write_padded_binary failed???')
    return i

  def __setitem__(self, k, t): # SAVE TO .build FILE
    'save mapping [k.start:k.stop] --> (id,start,stop)'
    cdef int i
    cdef IntervalMap im_tmp
    if self.build_ifile: # SAVE TO BUILD FILE
      im_tmp.start, im_tmp.end = (k.start, k.stop)
      im_tmp.target_id, im_tmp.target_start, im_tmp.target_end = t
      im_tmp.sublist = -1
      i = self.saveInterval(&im_tmp, 1, self.is_lpo, self.build_ifile)
      #logger.debug('saveInterval: %s %s %s  %s %s %s' % (self.id, im_tmp.start, im_tmp.end,
      #             im_tmp.target_id, im_tmp.target_start, im_tmp.target_end))
      self.nbuild = self.nbuild + i # INCREMENT COUNTER OF INTERVALS SAVED
    elif self.nlmsaLetters.in_memory_mode:
      t = (k.start, k.stop) + t
      try:
        self.buildList.append(t)
      except AttributeError:
        self.buildList = [t]
    else:
      raise ValueError('not opened in write mode')

  def __getitem__(self, k):
    try:
      if k.pathForward is self.seq:
        return NLMSASlice(self, k.start, k.stop)
    except AttributeError:
      pass
    raise KeyError('key must be a sequence interval of this sequence')

  def __len__(self):
    'call len(self.seq) if we have a seq.  Otherwise self.length'
    if self.seq is None:
      return self.length
    else:
      return len(self.seq)

  def __iadd__(self, seq):
    'add sequence to our union'
    try: # CHECK WHETHER THIS IS ALREADY IN THE INDEX
      x = self.nlmsaLetters.seqs[seq]
      return self # ALREADY IN THE INDEX, NO NEED TO ANYTHING
    except KeyError: # OK, WE REALLY DO NEED TO ADD IT...
      pass
    # CHECK FOR OVERFLOW... CREATE A NEW UNION IF NEEDED
    seq = seq.pathForward # GET THE ENTIRE SEQUENCE
    if self.length + len(seq) > self.nlmsaLetters.maxlen: # TOO BIG!
      if self.nlmsaLetters.pairwiseMode: # NEED TO CREATE CORRESPONDING LPO
        ns = self.nlmsaLetters.newSequence(None) # CREATE NEW LPO
      ns = self.nlmsaLetters.newSequence(None, is_union=1) # NEW UNION
      ns.__iadd__(seq) # ADD seq TO BRAND-NEW UNION
      return ns # RETURN THE NEW UNION COORDINATE SYSTEM
    # USE OUR EXISTING UNION
    self.nlmsaLetters.seqs.saveSeq(seq, self.id, self.length)
    self.length = self.length + len(seq) # EXPAND COORDINATE SYSTEM
    return self # iadd MUST ALWAYS RETURN self!!!


cdef class NLMSA:
  'toplevel interface to NLMSA storage of an LPO alignment'

  def __init__(self, pathstem='', mode='r', seqDict=None, mafFiles=None, axtFiles=None,
               maxOpenFiles=1024, maxlen=None, nPad=1000000, maxint=41666666,
               trypath=None, bidirectional=True, pairwiseMode=-1,
               bidirectionalRule=nlmsa_utils.prune_self_mappings,
               use_virtual_lpo=None, maxLPOcoord=None,
               inverseDB=None, alignedIvals=None, **kwargs):
    try:
      import resource # WE MAY NEED TO OPEN A LOT OF FILES...
      resource.setrlimit(resource.RLIMIT_NOFILE, (maxOpenFiles, -1))
    except: # BUT THIS IS OPTIONAL...
      pass
    self.lpoList = [] # EMPTY LIST OF LPO
    self.seqs = nlmsa_utils.NLMSASeqDict(self, pathstem, mode, **kwargs)
    self.seqlist = self.seqs.seqlist
    self.pathstem = pathstem
    self.inverseDB = inverseDB
    if maxlen is None:
      maxlen = C_int_max - 65536 # C_int_max MAXIMUM VALUE REPRESENTABLE BY int
      if axtFiles is not None:
        maxlen = maxlen / 2
    self.maxlen = maxlen
    self.inlmsa = nPad
    self._ignoreShadowAttr = {'sourceDB': None, 'targetDB': None} # SCHEMA INFO
    self.seqDict = seqDict # SAVE FOR USER TO ACCESS...
    self.in_memory_mode = 0
    if bidirectional:
      self.is_bidirectional = 1
    else:
      self.is_bidirectional = 0
    if use_virtual_lpo is not None: # DEPRECATED: MUST HAVE COME FROM PICKLE...
      pairwiseMode = use_virtual_lpo # USE SETTING FROM PICKLE...
    if pairwiseMode is True:
      self.pairwiseMode = 1
    elif pairwiseMode is False:
      self.pairwiseMode = 0
    else:
      self.pairwiseMode = pairwiseMode
    if maxLPOcoord is not None: # SIZE OF THE ENTIRE LPO COORD SYSTEM
      self.maxLPOcoord = maxLPOcoord
      if self.pairwiseMode == 1:
        raise ValueError('maxLPOcoord and pairwiseMode options incompatible!')
      self.pairwiseMode = 0
    else: # DEFAULT: RESTRICT USER TO A SINGLE LPO
      self.maxLPOcoord = self.maxlen
    if mode == 'r': # OPEN FROM DISK FILES
      if self.seqDict is None:
        self.seqDict = nlmsa_utils.read_seq_dict(pathstem, trypath)
      self.read_indexes(self.seqDict)
      self.read_attrs()
    elif mode == 'w': # WRITE TO DISK FILES
      self.do_build = 1
      self.lpo_id = 0
      if mafFiles is not None:
        self.newSequence() # CREATE INITIAL LPO
        self.readMAFfiles(mafFiles, maxint)
      elif axtFiles is not None:
        self.newSequence() # CREATE INITIAL LPO
        self.readAxtNet(axtFiles, bidirectionalRule)
      else: # USER WILL ADD INTERVAL MAPPINGS HIMSELF...
        if self.seqDict is None:
          import seqdb
          self.seqDict = seqdb.SeqPrefixUnionDict(addAll=True)
        self.initLPO() # CREATE AS MANY LPOs AS WE NEED
        self.newSequence(is_union=1) # SO HE NEEDS AN INITIAL UNION
      if alignedIvals is not None:
        self.add_aligned_intervals(alignedIvals)
        self.build()
    elif mode == 'memory': # CONSTRUCT IN-MEMORY
      if self.seqDict is None:
        import seqdb
        self.seqDict = seqdb.SeqPrefixUnionDict(addAll=True)
      self.in_memory_mode = 1
      self.do_build = 1
      self.initLPO() # CREATE AS MANY LPOs AS WE NEED
      self.newSequence(is_union=1) # CREATE INITIAL UNION
      self.lpo_id = 0
      if alignedIvals is not None:
        self.add_aligned_intervals(alignedIvals)
        self.build()
    elif mode != 'xmlrpc':
      raise ValueError('unknown mode %s' % mode)

  def close(self):
    'close our shelve index files'
    cdef NLMSASequence ns
    for ns in self.seqlist: # tell each seq to close its index files
      ns.close()
    self.seqs.close()

  def __reduce__(self): ############################# SUPPORT FOR PICKLING
    import classutil
    return (classutil.ClassicUnpickler, (self.__class__, self.__getstate__()))

  def __getstate__(self):
    if self.in_memory_mode:
      raise ValueError("can't pickle NLMSA.in_memory_mode")
    return dict(pathstem=self.pathstem, seqDict=self.seqDict,
                inverseDB=self.inverseDB)

  def __setstate__(self, state):
    self.__init__(**state) #JUST PASS KWARGS TO CONSTRUCTOR

  def read_indexes(self, seqDict):
    'open all nestedlist indexes in this LPO database for immediate use'
    cdef NLMSASequence ns
    try:
      ifile = file(self.pathstem + '.NLMSAindex', 'rU') # text file
    except IOError:
      ifile = file(self.pathstem + 'NLMSAindex', 'rU') # FOR BACKWARDS COMPATIBILITY
    try:
      for line in ifile:
        id, name, is_union, length = line.strip().split('\t')
        id = int(id)
        is_union = int(is_union)
        if id != len(self.seqlist):
          raise IOError('corrupted NLMSAIndex???')
        filestem = self.pathstem + str(id)
        seq = None # DEFAULT: NO ACTUAL SEQUENCE ASSOCIATED WITH LPO OR UNION
        if name == 'NLMSA_LPO_Internal': # AN LPO REFERENCE
          self.lpo_id = id
        elif not is_union: # REGULAR SEQUENCE
          try:
            seq = seqDict[name]
          except KeyError:
            raise KeyError('unable to find sequence %s in seqDict!' % name)
        # CREATE THE SEQ INTERFACE, BUT DELAY OPENING THE IntervalDBFile
        ns = NLMSASequence(self, filestem, seq, 'onDemand', is_union) # UNTIL NEEDED
        ns.length = int(length) # SAVE STORED LENGTH
        self.addToSeqlist(ns, seq)
    finally:
      ifile.close()

  def read_attrs(self):
    'read pickled attribute dictionary from file and apply to self'
    import pickle
    try:
      ifile = file(self.pathstem + '.attrDict', 'rb') # pickle is binary file!
    except IOError: # BACKWARDS COMPATIBILITY: OLD NLMSA HAS NOT ATTRDICT
      return
    try:
      d = pickle.load(ifile)
      for k, v in d.items():
        if k == 'is_bidirectional':
          self.is_bidirectional = v
        elif k == 'pairwiseMode':
          self.pairwiseMode = v
        else:
          setattr(self, k, v)
    finally:
      ifile.close()

  def addToSeqlist(self, NLMSASequence ns, seq=None):
    'add an NLMSASequence to our seqlist, and set its id'
    ns.id = self.seqlist.nextID()
    self.seqs[seq] = ns # SAVE TO OUR INDEX

  def newSequence(self, seq=None, is_union=0):
    'create a new nestedlist index for sequence seq'
    cdef NLMSASequence ns
    id = self.seqlist.nextID() # USE ITS INDEX AS UNIQUE ID FOR THIS SEQUENCE
    if self.pairwiseMode == 1 and is_union and id > 1: # NEED A VIRTUAL_LPO FOR THIS UNION
      self.newSequence() # CREATE AN LPO
      id = self.seqlist.nextID() # NOW GET ID FOR THE UNION
    filestem = self.pathstem + str(id)
    if self.in_memory_mode:
      mode = 'memory'
    else:
      mode = 'w'
    ns = NLMSASequence(self, filestem, seq, mode, is_union=is_union) #OPEN FOR WRITING
    if is_union: # RECORD THIS AS OUR CURRENT UNION OBJECT
      self.currentUnion = ns
    self.addToSeqlist(ns, seq) # SAVE TO OUR INDEX
    #logger.debug('Opened build file for ns_id %s, is_union %s' % (ns.id,
    #                                                              ns.is_union))
    return ns

  def nextID(self):
    'get a unique nlmsaID and advance counter'
    nlmsaID = self.inlmsa # USE THE NEXT FREE ID
    self.inlmsa = self.inlmsa + 1 # ADVANCE THE COUNTER
    return nlmsaID

  def initLPO(self):
    'create LPOs for this alignment'
    cdef NLMSASequence ns
    offset = 0
    while offset < self.maxLPOcoord:
      ns = self.newSequence() # CREATE AN LPO
      ns.offset = offset # FORCE OUR DESIRED OFFSET... EVEN THOUGH ALL LPOs EMPTY
      offset = offset + self.maxlen

  def init_pairwise_mode(self):
    'turn on use of virtual LPO mapping (i.e. no actual LPO is present!)'
    if self.pairwiseMode == 0:
      raise ValueError('this alignment is already using an LPO!')
    elif self.pairwiseMode != 1: # NOT ALREADY SET TO PAIRWISE MODE
      logger.info('''
Because you are aligning a pair of sequence intervals,
the pairwiseMode=True option is automatically being applied.
To avoid this message in the future, pass the pairwiseMode=True
option to the NLMSA constructor.
See the NLMSA documentation for more details.\n''')
    self.pairwiseMode = 1 # TURN ON THE VIRTUAL LPO FEATURE

  def __setitem__(self, k, v): # THIS METHOD EXISTS ONLY FOR nlmsa[s1]+=s2
    if isinstance(v, nlmsa_utils.BuildMSASlice):
      if v.seq is not None and v.seq == k: # CASE WHERE k IS A SEQ INTERVAL
        return # MATCHES += USAGE: NO NEED TO DO ANYTHING!
      elif v.is_lpo and isinstance(k, slice) and \
              k.start == v.start and k.stop == v.stop: # CASE: k IS A slice
        return # MATCHES += USAGE: NO NEED TO DO ANYTHING!
    raise KeyError('Usage only nlmsa[s1]+=s2 allowed. nlmsa[s1]=s2 forbidden!')

  def __getitem__(self, k):
    'return a slice of the LPO'
    if isinstance(k, sequence.SeqPath): # TREAT k AS A SEQUENCE INTERVAL
      id, ns, offset = self.seqs[k] # GET UNION INFO FOR THIS SEQ
      if self.do_build:
        return nlmsa_utils.BuildMSASlice(ns, k.start, k.stop, id, offset, 0, k)
      else: # QUERY THE ALIGNMENT
        try:
          return NLMSASlice(ns, k.start, k.stop, id, offset, k)
        except nlmsa_utils.EmptySliceError:
          return nlmsa_utils.EmptySlice(k)
    try: # TREAT k AS A PYTHON SLICE OBJECT
      i = k.start
    except AttributeError:
      raise KeyError('key must be a sequence interval or python slice object')
    if self.do_build:
      return nlmsa_utils.BuildMSASlice(self.lpoList[0], k.start, k.stop, -1, 0, 1, None)
    else: # QUERY THE ALIGNMENT
      l = nlmsa_utils.splitLPOintervals(self.lpoList, k) # MAP TO LPO(S)
      if len(l) > 1:
        raise ValueError('Sorry!  Query interval spans multiple LPOs!')
      for ns, myslice in l: # ONLY RETURN ONE SLICE OBJECT
          return NLMSASlice(ns, myslice.start, myslice.stop)

  def __iter__(self):
    raise NotImplementedError('you cannot iterate over NLMSAs')

  def edges(self, *args, **kwargs):
    return nlmsa_utils.generate_nlmsa_edges(self, *args, **kwargs)

  def __iadd__(self, seq):
    'add seq to our union'
    self.seqs.saveSeq(seq)
    return self  # iadd MUST ALWAYS RETURN self!

  def addAnnotation(self, a):
    'save alignment of sequence interval --> an annotation object'
    ival = a.sequence # GET PURE SEQUENCE INTERVAL
    self.__iadd__(ival) # ADD SEQ AS A NODE IN OUR ALIGNMENT
    self[ival].__iadd__(a) # ADD ALIGNMENT BETWEEN ival AND ANNOTATION

  def add_aligned_intervals(self, alignedIvals):
    'add alignedIvals to this alignment'
    nlmsa_utils.add_aligned_intervals(self, alignedIvals)

  cdef void free_seqidmap(self, int nseq0, SeqIDMap *seqidmap):
    cdef int i
    for i from 0 <= i < nseq0: # DUMP STRING STORAGE FOR SEQUENCE IDENTIFIERS
      free(seqidmap[i].id)
    free(seqidmap) # WE CAN NOW FREE THE SEQUENCE LOOKUP ARRAY

  cdef void save_nbuild(self, int nbuild[]):
    cdef NLMSASequence ns
    for ns in self.seqlist: # SAVE INTERVAL COUNTS BACK TO EACH SEQUENCE
      if not ns.is_lpo or self.pairwiseMode==1:
        ns.nbuild=nbuild[ns.id]  # SAVE INTERVAL COUNTS BACK TO REGULAR SEQUENCES
        #logger.debug('nbuild[%d] = %s' % (i, ns.nbuild))

  def readMAFfiles(self, mafFiles, maxint):
    'read alignment from a set of MAF files'
    cdef int i, j, nseq0, nseq1, n, nseq, block_len
    cdef SeqIDMap *seqidmap
    cdef char tmp[32768], *p, a_header[4]
    cdef FILE *ifile
    cdef IntervalMap im[4096], im_tmp
    cdef NLMSASequence ns_lpo, ns # ns IS OUR CURRENT UNION
    cdef FILE *build_ifile[4096]
    cdef int nbuild[4096], has_continuation
    cdef long long linecode_count[256]

    ns_lpo = self.seqlist[self.lpo_id] # OUR INITIAL LPO
    self.pairwiseMode = 0 # WE ARE USING A REAL LPO!
    memset(<void *>linecode_count, 0, sizeof(linecode_count))
    has_continuation = 0

    nseq0 = len(self.seqDict) # GET TOTAL #SEQUENCES IN ALL DATABASES
    seqidmap = <SeqIDMap *>calloc(nseq0, sizeof(SeqIDMap)) # ALLOCATE ARRAY
    i = 0
    for pythonStr, seqInfo in self.seqDict.seqInfoDict.iteritems():
      seqidmap[i].id = strdup(pythonStr)
      try:
        seqidmap[i].length = seqInfo.length
      except OverflowError:
        raise OverflowError('''Sequence too long for 32 bit int: %s, %d
Something is probably wrong with creation / reading of this sequence.
Check the input!''' % (pythonStr, seqInfo.length))
      i = i + 1
    qsort(seqidmap, nseq0, sizeof(SeqIDMap), seqidmap_qsort_cmp) # SORT BY id
    ns = None

    im_tmp.sublist = -1 # DEFAULT
    strcpy(a_header, "a ") # MAKE C STRING
    for filename in mafFiles:
      logger.info('Processing MAF file: ' + filename)
      ifile = fopen(filename, 'r') # text file
      if ifile == NULL:
        self.free_seqidmap(nseq0, seqidmap)
        self.save_nbuild(nbuild)
        raise IOError('unable to open file %s' % filename)
      if fgets(tmp, 32767, ifile) == NULL or strncmp(tmp, "##maf", 4): # HEADER LINE
        self.free_seqidmap(nseq0, seqidmap)
        self.save_nbuild(nbuild)
        raise IOError('%s: not a MAF file? Bad format.' % filename)
      p = fgets(tmp, 32767, ifile) # READ 1ST DATA LINE OF THE MAF FILE
      while p: # GOT ANOTHER LINE TO PROCESS
        if has_continuation or 0 == strncmp(tmp, a_header, 2): # ALIGNMENT HEADER: READ ALIGNMENT
          n = readMAFrecord(im, 0, seqidmap, nseq0, ns_lpo.length, # READ ONE MAF BLOCK
                            &block_len, ifile, 4096, linecode_count, &has_continuation)
          if n < 0: # UNRECOVERABLE ERROR OCCURRED...
            self.free_seqidmap(nseq0, seqidmap)
            self.save_nbuild(nbuild)
            raise ValueError('MAF block too long!  Increase max size')
          elif n == 0:
            continue

          if self.maxlen - ns_lpo.length <= block_len or \
             ns_lpo.nbuild > maxint: # TOO BIG! MUST CREATE A NEW LPO
            j = ns_lpo.length # RECORD THE OLD OFFSET
            ns_lpo = self.newSequence() # CREATE A NEW LPO SEQUENCE
            for i from 0 <= i < n: # TRANSLATE THESE INTERVALS BACK TO ZERO OFFSET
              if im[i].start >= 0: # FORWARD INTERVAL
                im[i].start = im[i].start - j
                im[i].end = im[i].end - j
              else: # REVERSE INTERVAL
                im[i].start = im[i].start + j
                im[i].end = im[i].end + j

          for i from 0 <= i < n: # SAVE EACH INTERVAL IN UNION -> LPO MAP
            j = im[i].target_id
            if seqidmap[j].nlmsa_id <= 0: # NEW SEQUENCE, NEED TO ADD TO UNION
              if ns is None or self.maxlen - ns.length <= seqidmap[j].length:
                ns = self.newSequence(None, is_union=1) # CREATE NEW UNION TO HOLD IT
                build_ifile[ns.id] = ns.build_ifile # KEEP PTR SO WE CAN WRITE DIRECTLY!
                nbuild[ns.id] = 0
              seqidmap[j].ns_id = ns.id # SET IDs TO ADD THIS SEQ TO THE UNION
              seqidmap[j].nlmsa_id = self.inlmsa
              seqidmap[j].offset = ns.length
              self.inlmsa = self.inlmsa + 1 # ADVANCE SEQUENCE ID COUNTER
              ns.length = ns.length + seqidmap[j].length # EXPAND UNION SIZE

            im[i].target_id = seqidmap[j].nlmsa_id # USE THE CORRECT ID
            if im[i].target_start < 0: # OFFSET REVERSE ORI
              im_tmp.start = -seqidmap[j].offset + im[i].target_start
              im_tmp.end = -seqidmap[j].offset + im[i].target_end
            else: # OFFSET FORWARD ORI
              im_tmp.start = seqidmap[j].offset + im[i].target_start
              im_tmp.end = seqidmap[j].offset + im[i].target_end
            im_tmp.target_id = ns_lpo.id
            im_tmp.target_start = im[i].start
            im_tmp.target_end = im[i].end
            j=seqidmap[j].ns_id # USE NLMSA ID OF THE UNION
            ns_lpo.saveInterval(&im_tmp, 1, 0, build_ifile[j]) # SAVE SEQ -> LPO
            nbuild[j] = nbuild[j] + 1

          ns_lpo.saveInterval(im, n, 1, ns_lpo.build_ifile) # SAVE LPO -> SEQ
          ns_lpo.nbuild = ns_lpo.nbuild+n # INCREMENT COUNT OF SAVED INTERVALS
        if not has_continuation:
          p = fgets(tmp, 32767, ifile) # TRY TO READ ANOTHER LINE...
      fclose(ifile) # CLOSE THIS MAF FILE
      #logger.debug('nbuild[0] = ' + ns_lpo.nbuild)
    for i from 0 <= i < 256: # PRINT WARNINGS ABOUT NON-ALIGNMENT LINES
      if linecode_count[i] > 0:
        logger.warn("Non-alignment text lines ignored: prefix %s, count %d" %
                    (chr(i), linecode_count[i]))
    for i from 0 <= i < nseq0: # INDEX SEQUENCES THAT WERE ALIGNED
      if seqidmap[i].nlmsa_id > 0: # ALIGNED, SO RECORD IT
        self.seqs.saveSeq(seqidmap[i].id, seqidmap[i].ns_id, seqidmap[i].offset,
                          seqidmap[i].nlmsa_id)
    self.free_seqidmap(nseq0, seqidmap)
    self.save_nbuild(nbuild)
    self.build() # WILL TAKE CARE OF CLOSING ALL build_ifile STREAMS

  cdef NLMSASequence add_seqidmap_to_union(self, int j, SeqIDMap seqidmap[],
                                           NLMSASequence ns, FILE *build_ifile[],
                                           int nbuild[]):
    cdef NLMSASequence ns_lpo
    if ns is None or self.maxlen - ns.length <= seqidmap[j].length:
      ns = self.newSequence(None, is_union=1) # CREATE NEW UNION TO HOLD IT
      build_ifile[ns.id] = ns.build_ifile # KEEP PTR SO WE CAN WRITE DIRECTLY!
      nbuild[ns.id] = 0
      if self.pairwiseMode == 1: # ALSO BIND INFO FOR VIRTUAL LPO FOR THIS UNION
        ns_lpo = self.seqs.seqlist[ns.id - 1]
        build_ifile[ns_lpo.id] = ns_lpo.build_ifile
        nbuild[ns_lpo.id] = 0
    seqidmap[j].ns_id = ns.id # SET IDs TO ADD THIS SEQ TO THE UNION
    seqidmap[j].nlmsa_id = self.inlmsa
    seqidmap[j].offset = ns.length
    self.inlmsa = self.inlmsa + 1 # ADVANCE SEQUENCE ID COUNTER
    ns.length = ns.length + seqidmap[j].length # EXPAND UNION SIZE
    return ns

  def readAxtNet(self, axtFiles, bidirectionalRule):
    'read alignment from a set of axtnet files'
    cdef int i, j, nseq0, n, isrc, is_bidirectional
    cdef SeqIDMap *seqidmap
    cdef char tmp[32768], *p, comment[4], src_prefix[64], dest_prefix[64]
    cdef FILE *ifile
    cdef IntervalMap im[4096], im_tmp
    cdef NLMSASequence ns_src # SOURCE UNION VS DEST UNION
    cdef FILE *build_ifile[4096]
    cdef int nbuild[4096], has_continuation

    self.pairwiseMode = 1 # WE ARE USING pairwiseMode

    nseq0 = len(self.seqDict) # GET TOTAL #SEQUENCES IN ALL DATABASES
    seqidmap = <SeqIDMap *>calloc(nseq0, sizeof(SeqIDMap)) # ALLOCATE ARRAY
    i = 0
    for pythonStr, seqInfo in self.seqDict.seqInfoDict.iteritems():
      seqidmap[i].id = strdup(pythonStr)
      seqidmap[i].length = seqInfo.length
      i = i + 1
    qsort(seqidmap, nseq0, sizeof(SeqIDMap), seqidmap_qsort_cmp) # SORT BY id
    ns_src = None

    im_tmp.sublist = -1 # DEFAULT
    strcpy(comment, "#") # MAKE C STRING
    import string
    import os.path
    for filename in axtFiles:
      logger.info('Processing axtnet file: ' + filename)
      try:
        if filename[-8:] == '.net.axt':
          t = string.split(os.path.basename(filename)[:-8], '.')[-2:]
        elif filename[-4:] == '.axt':
          t = string.split(os.path.basename(filename)[:-4], '.')[-2:]
      except:
        raise IOError('%s is not correct axtNet file name. Correct name is (chrid.)source.target.net.axt.' % filename)
      #t = prefix_fun(filename) # CALL PYTHON FUNCTION TO OBTAIN PREFIXES
      if bidirectionalRule is None: # DETERMINE IF UNI- VS. BI-DIRECTIONAL
        is_bidirectional = self.is_bidirectional # JUST USE GLOBAL SETTING
      else: # GET SETTING FROM USER-SUPPLIED FUNCTION
        is_bidirectional = bidirectionalRule(t[0], t[1], self.is_bidirectional)
      strcpy(src_prefix, t[0]) # KEEP THEM IN STATIC C STRINGS FOR SPEED
      strcpy(dest_prefix, t[1])
      ifile = fopen(filename, 'r') # text file
      if ifile == NULL:
        self.free_seqidmap(nseq0, seqidmap)
        self.save_nbuild(nbuild)
        raise IOError('unable to open file %s' % filename)
      while True:
        n = read_axtnet(im, seqidmap, nseq0, ifile, 4096, &isrc, src_prefix, dest_prefix)
        if n < 0: # UNRECOVERABLE ERROR OCCURRED...
          self.free_seqidmap(nseq0, seqidmap)
          self.save_nbuild(nbuild)
          raise ValueError('axtNet block too long!  Increase max size')
        elif n == 0: # NO MORE DATA TO READ
          break

        if seqidmap[isrc].nlmsa_id <= 0: # NEW SEQUENCE, NEED TO ADD TO UNION
          ns_src = self.add_seqidmap_to_union(isrc, seqidmap, ns_src, build_ifile, nbuild)

        for i from 0 <= i < n: # SAVE EACH INTERVAL IN SRC -> DEST MAP
          j = im[i].target_id
          #logger.debug('A: %s %s %s %s %s %s' % (im[i].start, im[i].end,
          #                                       im[i].target_id,
          #                                       im[i].target_start,
          #                                       im[i].target_end,
          #                                       im_tmp.sublist))
          #logger.debug('B: %s %s %s %s %s %s %s' % (seqidmap[isrc].nlmsa_id, i,
          #                                          j, seqidmap[j].id,
          #                                          seqidmap[j].ns_id,
          #                                          seqidmap[j].offset,
          #                                          seqidmap[j].nlmsa_id))
          if seqidmap[j].nlmsa_id <= 0: # NEW SEQUENCE, NEED TO ADD TO UNION
            ns_src = self.add_seqidmap_to_union(j, seqidmap, ns_src, build_ifile, nbuild)
          im[i].target_id = seqidmap[j].nlmsa_id # USE THE CORRECT ID
          if is_bidirectional: # SAVE DEST -> SRC ALIGNMENT MAPPING
            if im[i].target_start < 0: # OFFSET REVERSE ORI
              im_tmp.start = -seqidmap[j].offset + im[i].target_start
              im_tmp.end = -seqidmap[j].offset + im[i].target_end
            else: # OFFSET FORWARD ORI
              im_tmp.start = seqidmap[j].offset + im[i].target_start
              im_tmp.end = seqidmap[j].offset + im[i].target_end
            im_tmp.target_id = seqidmap[isrc].nlmsa_id
            im_tmp.target_start = im[i].start
            im_tmp.target_end = im[i].end
            #logger.debug('C: %s %s %s %s %s' % (im_tmp.target_id,
            #                                    im_tmp.target_start,
            #                                    im_tmp.target_end,
            #                                    seqidmap[j].ns_id, j))
            j = seqidmap[j].ns_id - 1 # SAVE ALL ALIGNMENTS TO THE VIRTUAL LPO
            ns_src.saveInterval(&im_tmp, 1, 0, build_ifile[j]) # SAVE DEST -> SRC
            nbuild[j] = nbuild[j] + 1
          if im[i].start < 0: # OFFSET FORWARD ORI
            im[i].start = -seqidmap[isrc].offset + im[i].start
            im[i].end = -seqidmap[isrc].offset + im[i].end
          else: # OFFSET FORWARD ORI
            im[i].start = seqidmap[isrc].offset + im[i].start
            im[i].end = seqidmap[isrc].offset + im[i].end
          #logger.debug('D: %s %s %s %s %s %s' % (im_tmp.start, im_tmp.end,
          #                                       im_tmp.target_id,
          #                                       im_tmp.target_start,
          #                                       im_tmp.target_end,
          #                                       im_tmp.sublist))

        # SAVE THE RECORD. read_axtnet FUNCTION READS SRC/DEST AT THE SAME TIME
        j = seqidmap[isrc].ns_id - 1 # SAVE ALL ALIGNMENTS TO THE VIRTUAL LPO
        ns_src.saveInterval(im, n, 0, build_ifile[j]) # SAVE SRC -> DEST
        nbuild[j] = nbuild[j] + n # INCREMENT COUNT OF SAVED INTERVALS

      fclose(ifile) # CLOSE THIS AXTNET FILE

    for i from 0 <= i <nseq0: # INDEX SEQUENCES THAT WERE ALIGNED
      if seqidmap[i].nlmsa_id > 0: # ALIGNED, SO RECORD IT
        self.seqs.saveSeq(seqidmap[i].id, seqidmap[i].ns_id, seqidmap[i].offset,
                          seqidmap[i].nlmsa_id)
    self.free_seqidmap(nseq0, seqidmap)
    self.save_nbuild(nbuild)
    self.build() # WILL TAKE CARE OF CLOSING ALL build_ifile STREAMS

  def buildFiles(self, saveSeqDict=False, **kwargs):
    'build nestedlist databases on-disk, and .seqDict index if desired'
    cdef NLMSASequence ns
    self.seqs.reopenReadOnly() # SAVE INDEXES AND OPEN READ-ONLY
    ntotal = 0
    ifile=file(self.pathstem + '.NLMSAindex', 'w') # text file
    try:
      for ns in self.seqlist: # BUILD EACH IntervalFileDB ONE BY ONE
        ntotal = ntotal + ns.buildFiles(**kwargs)
        if ns.is_lpo:
          ifile.write('%d\t%s\t%d\t%d\n' % (ns.id, 'NLMSA_LPO_Internal', 0, ns.length))
        elif ns.is_union:
          ifile.write('%d\t%s\t%d\t%d\n' % (ns.id, 'NLMSA_UNION_Internal', 1, ns.length))
        else:
          ifile.write('%d\t%s\t%d\t%d\n' % (ns.id, ns.name, 0, ns.length))
    finally:
      ifile.close()
    if ntotal == 0:
      raise nlmsa_utils.EmptyAlignmentError('empty alignment!')
    import pickle
    import sys
    ifile = file(self.pathstem + '.attrDict', 'wb') # pickle is binary file!
    try:
      pickle.dump(dict(is_bidirectional=self.is_bidirectional,
                       pairwiseMode=self.pairwiseMode), ifile)
    finally:
      ifile.close()
    logger.info('Index files saved.')
    if saveSeqDict:
      self.save_seq_dict()
    else:
      logger.info('''Note: the NLMSA.seqDict was not saved to a file.
This is not necessary if you intend to save the NLMSA to worldbase.
But if you wish to open this NLMSA independently of worldbase,
you should call NLMSA.save_seq_dict() to save the seqDict info to a file,
or in the future pass the saveSeqDict=True option to NLMSA.build().''')

  def save_seq_dict(self):
    'save seqDict to a worldbase-aware pickle file'
    nlmsa_utils.save_seq_dict(self.pathstem, self.seqDict)

  def build(self, **kwargs):
    'build nestedlist databases from saved mappings and initialize for use'
    if self.do_build == 0:
      raise ValueError('not opened in write mode')
    try: # TURN OFF AUTOMATIC ADDING OF SEQUENCES TO OUR SEQDICT...
      self.seqDict.addAll = False
    except AttributeError: # THAT WAS PURELY OPTIONAL...
      pass
    if self.in_memory_mode:
      ntotal = 0
      for ns in self.seqlist: # BUILD EACH IntervalDB ONE BY ONE
        ntotal = ntotal + ns.buildInMemory(**kwargs)
      if ntotal == 0:
        raise nlmsa_utils.EmptyAlignmentError('empty alignment!')
    else:
      self.buildFiles(**kwargs)
    self.do_build = 0

  def seqInterval(self, int iseq, int istart, int istop):
    'get specified interval in the target sequence'
    seq=self.seqlist.getSeq(iseq) # JUST THE SEQ OBJECT
    return sequence.relativeSlice(seq, istart, istop)

  def __invert__(self):
    if self.inverseDB is not None: # use the specified inverseDB
      return self.inverseDB
    elif self.is_bidirectional: # provides mapping both directions
      return self
    else:
      raise ValueError('this mapping is not invertible')


def dump_textfile(pathstem, outfilename=None):
  'dump NLMSA binary files to a text file'
  cdef int n, nlmsaID, nsID, offset, is_bidirectional, pairwiseMode, nprefix
  cdef FILE *outfile
  cdef char err_msg[2048], tmp[2048], seqDictID[256]
  err_msg[0] = 0 # ENSURE STRING IS EMPTY
  if outfilename is None:
    outfilename = pathstem + '.txt' # DEFAULT TEXTFILE NAME
  import classutil # NEED TO COPY THE WHOLE seqIDdict
  import pickle
  import sys
  seqIDdict = classutil.open_shelve(pathstem + '.seqIDdict', 'r')
  n = len(seqIDdict)
  seqDict = nlmsa_utils.read_seq_dict(pathstem)
  try: # OBTAIN PREFIX INFO FOR SEQDICT
    prefixDict = seqDict.prefixDict
    nprefix = len(prefixDict)
    strcpy(seqDictID, "None")
  except AttributeError: # NO PREFIXUNION.  TRY TO GET ID OF seqDict
    nprefix = 0
    prefixDict = {}
    try:
      strcpy(seqDictID, seqDict._persistent_id)
    except AttributeError:
      strcpy(seqDictID, "unknown")
      logger.info('''Warning: Because your seqDict has no worldbase ID, there
is no host-independent way to save it to a textfile for transfer
to another machine.  Therefore, when loading this textfile
on the destination machine, you will have to provide the
seqDict argument to textfile_to_binaries() on the destination machine.''')
  try:
    ifile = file(pathstem + '.attrDict', 'rb') # pickle is binary file!
    d = pickle.load(ifile)
    ifile.close()
  except IOError:
    d = {}
  is_bidirectional = d.get('is_bidirectional', -1)
  pairwiseMode = d.get('pairwiseMode', -1)
  outfile = fopen(outfilename, "w") # text file
  import os.path
  basestem = os.path.basename(pathstem) # GET RID OF PATH INFO
  strcpy(tmp, basestem) # COPY TO C STRING SO WE CAN fprintf
  if outfile == NULL:
    raise IOError('unable to open file %s' % outfilename)
  try:
    if fprintf(outfile, "PATHSTEM\t%s\t%d\t%d\t%d\t%d\t%s\n", tmp, n,
               is_bidirectional, pairwiseMode, nprefix, seqDictID) < 0:
      raise IOError('error writing to file %s' % outfilename)
    pleaseWarn = True
    for id, d in prefixDict.items(): # SAVE seqDict PREFIX ENTRIES
      strcpy(tmp, id) # CONVERT TO C DATA TYPES FOR fprintf
      try:
        strcpy(seqDictID, d._persistent_id) # try to get worldbase ID
      except AttributeError:
        strcpy(seqDictID, "None")
        if pleaseWarn:
          pleaseWarn = False
          logger.info('''Warning: Because one or more of the sequence
databases in the seqDict have no worldbase ID, there is no
host-independent way to save it to a textfile for transfer
to another machine.  Therefore, when loading this textfile
on the destination machine, you will have to provide a dictionary
for these sequence database(s) as the prefixDict argument
to textfile_to_binaries() on the destination machine.''')
      if fprintf(outfile, "PREFIXUNION\t%s\t%s\n", tmp, seqDictID) < 0:
        raise IOError('error writing to file %s' % outfilename)
    for id, t in seqIDdict.iteritems(): # SAVE seqIDdict
      strcpy(tmp, id) # CONVERT TO C DATA TYPES FOR fprintf
      nlmsaID = t[0]
      nsID = t[1]
      offset = t[2]
      if fprintf(outfile, "SEQID\t%s\t%d\t%d\t%d\n", tmp,
                 nlmsaID, nsID, offset) < 0:
        raise IOError('error writing to file %s' %outfilename)
    try:
      ifile = file(pathstem + '.NLMSAindex', 'rU') # text file
    except IOError:
      ifile = file(pathstem + 'NLMSAindex', 'rU')
  except:
    fclose(outfile)
    raise
  try:
    for line in ifile:  # NOW SAVE THE NLMSA DATA
      id, name, is_union, length = line.strip().split('\t')
      strcpy(tmp, line) # COPY TO C STRING SO WE CAN fprintf
      if fprintf(outfile, "NLMSASequence\t%s", tmp) < 0:
        raise IOError('error writing file %s' % outfilename)
      mypath = pathstem + id
      mybase = basestem + id
      if save_text_file(mypath, mybase, err_msg, outfile) != 0:
        raise IOError(err_msg)
  finally:
    fclose(outfile)
    ifile.close()


def textfile_to_binaries(filename, seqDict=None, prefixDict=None, buildpath=''):
  'convert pathstem.txt textfile to NLMSA binary files'
  cdef int i, n, nlmsaID, nsID, offset, is_bidirectional, pairwiseMode, nprefix
  cdef FILE *infile
  cdef char err_msg[2048], line[32768], tmp[2048], basestem[2048], seqDictID[2048]
  if seqDict is not None:
    ignorePrefix = True
  else:
    ignorePrefix = False
  err_msg[0] = 0 # ENSURE STRING IS EMPTY
  infile = fopen(filename, "r") # text file
  if infile == NULL:
    raise IOError('unable to open file %s' % filename)
  try:
    if fgets(line, 32767, infile) == NULL:
      raise IOError('error or EOF reading %s'%filename)
    is_bidirectional = -1 # INVALID INITIAL SETTING
    pairwiseMode = -1
    nprefix = 0
    strcpy(tmp, "None")
    if 2 > sscanf(line, "PATHSTEM\t%s\t%d\t%d\t%d\t%d\t%s", basestem, &n,
                &is_bidirectional, &pairwiseMode, &nprefix, tmp):
      raise IOError('bad format in %s' % filename)
    if buildpath != '': # USER-SPECIFIED PATH FOR BINARIES
      import os
      buildpath1 = os.path.join(buildpath, basestem) # CONSTRUCT FILE PATH
      strcpy(basestem, buildpath1) # COPY BACK TO C STRING USABLE IN C FUNCTIONS
    else: # JUST USE PATH IN CURRENT DIRECTORY
      buildpath1 = basestem
    if 0 == strcmp(tmp, "unknown"):
      if seqDict is None:
        raise ValueError('You must provide a seqDict for this NLMSA!')
    elif 0 != strcmp(tmp, "None"): # try obtaining as worldbase ID
      from pygr import worldbase
      seqDict = worldbase(tmp)
    import classutil # CREATE THE seqIDdict
    import pickle
    seqIDdict = classutil.open_shelve(basestem + '.seqIDdict', 'n')
    IDdict = classutil.open_shelve(basestem + '.idDict', 'n')
    d = {}
    if is_bidirectional != -1:
      d['is_bidirectional'] = is_bidirectional
    if pairwiseMode != -1:
      d['pairwiseMode'] = pairwiseMode
    ifile = file(basestem + '.attrDict', "wb") # pickle is binary file!
    try:
      pickle.dump(d, ifile)
    finally:
      ifile.close()
    if prefixDict is None or ignorePrefix:
      prefixDict = {}
    missing = []
    for i from 0 <= i < nprefix: # READ seqDICT PREFIX ENTRIES
      if fgets(line, 32767, infile) == NULL:
        raise IOError('error or EOF reading %s' % filename)
      if 2 != sscanf(line, "PREFIXUNION\t%s\t%s", tmp, seqDictID):
        raise IOError('bad format in %s'%filename)
      if ignorePrefix: # JUST IGNORE THE PREFIX INFO WE READ
        continue
      if 0 == strcmp(seqDictID, "None"):
        if tmp not in prefixDict:
          missing.append(tmp) # MISSING A SEQDICT DICTIONARY ENTRY!
      else: # load it from worldbase
        from pygr import worldbase
        prefixDict[tmp] = worldbase(seqDictID)
    if len(missing)>0:
      raise KeyError('''You must supply sequence database(s) for the
following prefixes, by passing them in the prefixDict optional
dictionary argument: %s''' % missing)
    if len(prefixDict) > 0: # CREATE A PREFIX UNION
      import seqdb
      seqDict = seqdb.PrefixUnionDict(prefixDict)
    nlmsa_utils.save_seq_dict(basestem, seqDict) # SAVE SEQDICT
    for i from 0 <= i <n: # seqIDDict READING
      if fgets(line, 32767, infile) == NULL:
        raise IOError('error or EOF reading %s' % filename)
      if 4 != sscanf(line, "SEQID\t%s\t%d %d %d", tmp,
                   &nlmsaID, &nsID, &offset):
        raise IOError('bad format in %s' % filename)
      seqIDdict[tmp] = (nlmsaID, nsID, offset) # SAVE THIS ENTRY
      IDdict[str(nlmsaID)] = (tmp, nsID)
    seqIDdict.close() # DONE WRITING THE seqIDdict
    IDdict.close() # DONE WRITING THE seqIDdict

    NLMSAindexText = ''
    if buildpath != '': # USER-SPECIFIED PATH FOR BINARIES
      import os
      buildpath2 = os.path.join(buildpath, '') # ENSURE THIS ENDS IN DIRECTORY SEPARATOR
      strcpy(basestem, buildpath2) # COPY BACK TO C STRING USABLE IN C FUNCTIONS
    else:
      strcpy(basestem, '') # JUST USE BLANK STRING TO SAVE IN CURRENT DIRECTORY
    import sys
    while fgets(line, 32767, infile) != NULL:
      s = line # CONVERT STRING TO PYTHON OBJECT
      if not s.startswith('NLMSASequence'):
        raise IOError('bad format in file %s' % filename)
      NLMSAindexText = NLMSAindexText + s[14:] # JUST SAVE THE DATA FIELDS
      logger.info('Saving NLMSA binary index: ' + s[14:] + '...')
      if text_file_to_binaries(infile, basestem, err_msg) < 0:
        raise IOError(err_msg)
    ifile = file(buildpath1 + '.NLMSAindex', "w") # text file
    ifile.write(NLMSAindexText) # LAST, WRITE TOP INDEX FILE
    ifile.close()
  finally:
    fclose(infile)
  return buildpath1 # ACTUAL PATH TO NLMSA INDEX FILESET
