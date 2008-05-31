from __future__ import generators
import os
from sqlgraph import *
from poa import *
from parse_blast import *
import classutil

def tryPathList(filepath,pathlist,mode='r'):
    'return successful path based on trying pathlist locations'
    def tryopen(mypath):
        myfile=file(mypath,mode)
        myfile.close()
        return mypath
    try: # JUST TRY filepath
        return tryopen(filepath)
    except IOError:
        pass
    if pathlist is None: # TREAT AS EMPTY LIST
        pathlist=[]
    import os.path
    b=os.path.basename(filepath)
    for s in pathlist: # NOW TRY EACH DIRECTORY IN pathlist
        try:
            return tryopen(os.path.join(s,b))
        except IOError:
            pass
    raise IOError('unable to open %s from any location in %s'
                  %(filepath,pathlist))


class SQLSequence(SQLRow,SequenceBase):
    "Transparent access to a DB row representing a sequence; no caching."
    def __init__(self,table,id):
        SQLRow.__init__(self,table,id)
        SequenceBase.__init__(self)
    def strslice(self,start,end):
        "Efficient access to slice of a sequence, useful for huge contigs"
        return self._select('substring(%s FROM %d FOR %d)'
                            %(self.db._attrSQL('seq'),start+1,end-start))
    def __getattr__(self,attr):
        'both parent classes have getattr, so have to call both'
        try:
            return SQLRow.__getattr__(self,attr)
        except AttributeError:
            return SequenceBase.__getattr__(self,attr)

class DNASQLSequence(SQLSequence):
    _seqtype=DNA_SEQTYPE

class RNASQLSequence(SQLSequence):
    _seqtype=RNA_SEQTYPE

class ProteinSQLSequence(SQLSequence):
    _seqtype=PROTEIN_SEQTYPE


# NCBI HAS THE NASTY HABIT OF TREATING THE IDENTIFIER AS A BLOB INTO
# WHICH THEY STUFF FIELD AFTER FIELD... E.G. gi|1234567|foobarU|NT_1234567|...
# THIS JUST YANKS OUT THE SECOND ARGUMENT SEPARATED BY |
NCBI_ID_PARSER=lambda id:id.split('|')[1]


seq_id_counter=0
def new_seq_id():
    global seq_id_counter
    seq_id_counter += 1
    return str(seq_id_counter-1)


def write_fasta(ofile,s,chunk=60,id=None,reformatter=None):
    "Trivial FASTA output"
    if id is None:
        try:
            id=str(s.id)
        except AttributeError:
            id=new_seq_id()

    ofile.write('>'+id+'\n')
    seq=str(s)
    if reformatter is not None: # APPLY THE DESIRED REFORMATTING
        seq = reformatter(seq)
    end=len(seq)
    pos=0
    while 1:
        ofile.write(seq[pos:pos+chunk]+'\n')
        pos += chunk
        if pos>=end:
            break
    return id # IN CASE CALLER WANTS TEMP ID WE MAY HAVE ASSIGNED

def read_fasta(ifile):
    "iterate over id,title,seq from stream ifile"
    id=None
    isEmpty = True
    for line in ifile:
        if '>'==line[0]:
            if id is not None and len(seq)>0:
                yield id,title,seq
                isEmpty = False
            id=line[1:].split()[0]
            title=line[len(id)+2:]
            seq = ''
        elif id is not None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seq += word
    if id is not None and len(seq)>0:
        yield id,title,seq
    elif isEmpty:
        raise IOError('no readable sequence in FASTA file!')

def read_fasta_one_line(ifile):
    "read a single sequence line, return id,title,seq"
    id=None
    seq=''
    while True:
        line = ifile.readline(1024) # READ AT MOST 1KB
        if line=='': # EOF
            break
        elif '>'==line[0]:
            id = line[1:].split()[0]
            title = line[len(id)+2:]
        elif id is not None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seq += word
            if len(seq)>0:
                return id,title,seq
    raise IOError('no readable sequence in FASTA file!')

def read_fasta_lengths(ifile):
    "Generate sequence ID,length from stream ifile"
    id=None
    seqLength=0
    isEmpty = True
    for line in ifile:
        if '>'==line[0]:
            if id is not None and seqLength>0:
                yield id,seqLength
                isEmpty = False
            id=line[1:].split()[0]
            seqLength=0
        elif id is not None: # READ SEQUENCE
            for word in line.split(): # GET RID OF WHITESPACE
                seqLength += len(word)
    if id is not None and seqLength>0:
        yield id,seqLength
    elif isEmpty:
        raise IOError('no readable sequence in FASTA file!')


def store_seqlen_dict(d,ifile,filename,idFilter=None):
    "store sequence lengths in a dictionary"
    try: # TRY TO USE OUR FAST COMPILED PARSER
        import seqfmt
    except ImportError:
        import sys
        raise ImportError('''
Unable to import extension module pygr.seqfmt that should be part of this package.
Either you are working with an incomplete install, or an installation of pygr
compiled with an incompatible Python version.  Please check your PYTHONPATH
setting and make sure it is compatible with this Python version (%d.%d).
When in doubt, rebuild your pygr installation using the
python setup.py build --force
option to force a clean install''' % sys.version_info[:2])
    if idFilter is None: # LET C FUNC WRITE DIRECTLY TO d
        return seqfmt.read_fasta_lengths(d,filename)
    class dictwrapper(object):
        def __init__(self,idFilter,d):
            self.d=d
            self.idFilter=idFilter
        def __setitem__(self,k,v):
            id=self.idFilter(k)
            self.d[id]=v
    dw=dictwrapper(idFilter,d) # FORCE C FUNC TO WRITE TO WRAPPER...
    return seqfmt.read_fasta_lengths(dw,filename)
    
##     if idFilter is not None: # HAVE TO CLEAN UP BLAST'S MESSY IDs
##         for id,seqLength in read_fasta_lengths(ifile):
##             d[idFilter(id)] = (seqLength,) # SAVE TO DICTIONARY
##     else: # JUST USE id AS-IS
##         for id,seqLength in read_fasta_lengths(ifile):
##             d[id] = (seqLength,) # SAVE TO DICTIONARY
        

def fastacmd_seq(filepath,id,start=None,end=None):
    "Get complete sequence or slice from a BLAST formatted database"
    maxlen=None
    if start is not None: # USE ABILITY TO GRAB A SLICE OF THE SEQUENCE
        if start==0 and end==1: # fastacmd FAILS ON -L 1,1: RETURNS WHOLE SEQ! UGH!
            cmd='fastacmd -d %s -s "%s" -L %d,%d' % (filepath,id,start+1,end+1)
            maxlen=1 # GOT 2 LETTERS, SO HAVE TO SLICE DOWN TO 1... UGH!
        else: # NORMAL USAGE... AT LEAST fastacmd WORKS SOME OF THE TIME...
            cmd='fastacmd -d %s -s "%s" -L %d,%d' % (filepath,id,start+1,end)
    else:
        cmd='fastacmd -d %s -s "%s"' % (filepath,id)
    ofile=os.popen(cmd)
    ofile.readline() # SKIP TITLE LINE
    s=''
    for line in ofile:
        for word in line.split(): # GET RID OF WHITESPACE...
            s += word
    exitstatus=ofile.close()
    if exitstatus==768:
        raise KeyError('sequence %s not found in %s' %(id,filepath))
    elif exitstatus is not None:
        raise OSError('command %s failed. Not in PATH?' % cmd)
    if maxlen is None:
        return s
    else: # PROTECT AGAINST fastacmd SCREWUPS
        return s[:maxlen]


class FastacmdIntervalCache(object):
    """caches a single interval of sequence:
       expandable by self+=slice
       get sequence strslice by self[slice]"""
    maxlen=20000 # DEFAULT MAXIMUM WIDTH
    def __init__(self,start,end,strslice,path):
        "strslice must be callable as strslice(i,j) to get seq[i:j]"
        self.start=start
        self.end=end
        self.strslice=strslice # SAVE METHOD FOR GETTING SUBSEQUENCE
        self.path=path

    def delseq(self):
        "drop our cached sequence"
        try:
            del self.seq
        except AttributeError:
            pass

    def __iadd__(self,k):
        "expand our interval by merging with slice k"
        if k.stop-self.start>self.maxlen or self.end-k.start>self.maxlen:
            raise ValueError('interval is beyond max extension radius')
        if k.start<self.start:
            self.start=k.start
            self.delseq() # IF INTERVAL CHANGED, BETTER REFRESH CACHED SEQ
        if k.stop>self.end:
            self.end=k.stop
            self.delseq() # IF INTERVAL CHANGED, BETTER REFRESH CACHED SEQ
        return self # iadd METHOD MUST ALWAYS RETURN self!!!

    def __getitem__(self,k):
        "return seq slice corresponding to slice given by argument k"
        if k.start<self.start or k.stop>self.end:
            self+=k # TRY EXTENDING OUR INTERVAL TO CONTAIN k
        if not hasattr(self,'seq'):
            self.seq=self.strslice(self.start,self.end) # USE SAVED METHOD
        return self.seq[k.start-self.start:k.stop-self.start]


class BlastSeqDescriptor(object):
    "Get sequence from a blast formatted database for obj.id"
    def __get__(self,obj,objtype):
        return fastacmd_seq(obj.db.filepath,obj.id)

class BlastSequenceBase(SequenceBase):
    "Represents a sequence in a blast database, w/o keeping seq in memory"
    seq=BlastSeqDescriptor()
    def __init__(self,db,id):
        self.db=db
        self.id=id
        SequenceBase.__init__(self)
        self.checkID() # RAISE KeyError IF THIS SEQ NOT IN db
    def checkID(self):
        'check whether this seq ID actually present in the DB, KeyError if not'
        return self.strslice(0,2) # TRY TO GET TINY PIECE OF SEQUENCE
    def strslice(self,start,end,useCache=True):
        "Efficient access to slice of a sequence, useful for huge contigs"
        if useCache:
            try:
                return self.db.strsliceCache(self,start,end)
            except IndexError: # NOT FOUND IN CACHE
                pass # JUST USE OUR REGULAR METHOD
        return fastacmd_seq(self.db.filepath,self.id,start,end)

class BlastSequence(BlastSequenceBase):
    "Rely on seqLenDict to give fast access to sequence lengths"
    def __len__(self):
        "Use persistent storage of sequence lengths to avoid reading whole sequence"
        return self.db.seqLenDict[self.id][0]
    def checkID(self):
        'check whether this seq ID actually present in the DB, KeyError if not'
        return self.db.seqLenDict[self.id][0]

class FileDBSeqDescriptor(object):
    "Get sequence from a concatenated pureseq database for obj.id"
    def __get__(self,obj,objtype):
        return obj.strslice(0,obj.db.seqLenDict[obj.id][0])

class FileDBSequence(BlastSequence):
    seq=FileDBSeqDescriptor()
    __reduce__ = classutil.item_reducer
    def strslice(self,start,end,useCache=True):
        "Efficient access to slice of a sequence, useful for huge contigs"
        if useCache:
            try:
                return self.db.strsliceCache(self,start,end)
            except IndexError: # NOT FOUND IN CACHE
                pass # JUST USE OUR REGULAR METHOD
        try:
            ifile=self.db._pureseq
        except AttributeError:
            ifile=file(self.db.filepath+'.pureseq')
            self.db._pureseq=ifile
        ifile.seek(self.db.seqLenDict[self.id][1]+start)
        return ifile.read(end-start)
    

class BlastSequenceCache(BlastSequence):
    """represents a sequence, with interval caching
    slicing operations are recorded, and merged into one or more cache intervals
    Subsequent requests for subsequence will use these cached intervals."""
    def __init__(self,db,id):
        super(BlastSequenceCache,self).__init__(db,id)
        self.cache=[]
    def __getitem__(self,k):
        "record all slices taken of this sequence, constructing a cache for fast access"
        ival=super(BlastSequenceCache,self).__getitem__(k) # GET THE INTERVAL OBJECT AS USUAL
        for i in self.cache:
            try:
                i+=ival # TRY TO EXTEND THIS INTERVAL CACHE TO CONTAIN ival
                return ival # SUCCESS.  JUST RETURN ival AS USUAL
            except ValueError:
                pass
        # HAVE TO ADD ival AS A NEW INTERVAL CACHE OBJECT
        self.cache.append(FastacmdIntervalCache(ival.start,ival.stop,
                                                super(BlastSequenceCache,self).strslice,self))
        return ival
    def strslice(self,start,end):
        "get sequence from our interval cache"
        s=slice(start,end)
        for i in self.cache:
            try:
                return i[s] # TRY TO GET SEQUENCE FROM INTERVAL CACHE
            except ValueError: # NOT IN THIS CACHE ITEM, SO KEEP TRYING
                pass
        return str(self[s]) # FORCE __getitem__ TO LOAD s INTO THE CACHE


def blast_program(query_type,db_type):
    progs= {DNA_SEQTYPE:{DNA_SEQTYPE:'blastn', PROTEIN_SEQTYPE:'blastx'},
            PROTEIN_SEQTYPE:{DNA_SEQTYPE:'tblastn', PROTEIN_SEQTYPE:'blastp'}}
    if query_type==RNA_SEQTYPE:
        query_type=DNA_SEQTYPE
    if db_type==RNA_SEQTYPE:
        db_type=DNA_SEQTYPE
    return progs[query_type][db_type]


class BlastIval(TupleO):
    "Wrap a tuple with same attribute names as poa.IntervalTransform.repr_dict"
    _attrcol={'hit_id':0, 'src_id':1, 'dest_id':2, 'blast_score':3, 'e_value':4,
              'percent_id':5, 'src_ori':6,'dest_ori':7,
              'src_start':8, 'src_end':9,'dest_start':10,'dest_end':11}

class BlastHitInfo(TupleO):
    _attrcol={'blast_score':0,'e_value':1,'percent_id':2}
    def __init__(self,ival):
        "save edge info from ival onto our TupleO"
        ei=len(self._attrcol)*[None] # RIGHT LENGTH LIST
        for a,i in self._attrcol.items():
            try:
                ei[i]=getattr(ival,a) # CONSTRUCT ATTRS IN RIGHT ORDER
            except AttributeError:
                pass # OK FOR ival TO LACK SOME ATTRIBUTES...
        TupleO.__init__(self,ei)
        
    def repr_dict(self):
        return {'blast_score':self.data[0],'e_value':self.data[1],
                'percent_id':self.data[2]}

def get_interval(seq,start,end,ori):
    "trivial function to get the interval seq[start:end] with requested ori"
    ival=seq[start:end]
    if ori== -1:
        ival= -ival
    return ival

def save_interval_alignment(m,ival,srcSet,destSet=None,edgeClass=BlastHitInfo,
                            ivalXform=get_interval):
    "Add ival to alignment m, with edge info if requested"
    if destSet is None:
        destSet=srcSet
    srcSeq=srcSet[ival.src_id]
    srcPath=ivalXform(srcSeq,ival.src_start,ival.src_end,ival.src_ori)
    destPath=ivalXform(destSet[ival.dest_id],ival.dest_start,ival.dest_end,ival.dest_ori)
    if edgeClass is not None:
        m+=srcSeq # MAKE SURE THIS SEQUENCE IS IN THE MAPPING TOP-LEVEL INDEX
        m[srcPath][destPath]=edgeClass(ival) # SAVE ALIGNMENT WITH EDGE INFO
    else:
        m+=srcSeq # MAKE SURE THIS SEQUENCE IS IN THE MAPPING TOP-LEVEL INDEX
        m[srcPath][destPath]=None # JUST SAVE ALIGNMENT, NO EDGE INFO
    return srcPath,destPath # HAND BACK IN CASE CALLER WANTS TO KNOW THE INTERVALS


def read_interval_alignment(ofile,srcSet,destSet,al=None,edgeClass=None):
    "Read tab-delimited interval mapping between seqs from the 2 sets of seqs"
    needToBuild=False
    if al is None:
        try:
            import cnestedlist
            al=cnestedlist.NLMSA('blasthits','memory',pairwiseMode=True)
            edgeClass=None
            needToBuild=True
        except ImportError:
            print 'WARNING: import cnestedlist failed. Using old-style PathMapping()'
            al=PathMapping()
            edgeClass=BlastHitInfo
    p=BlastHitParser()
    for t in p.parse_file(ofile):
        save_interval_alignment(al,BlastIval(t),srcSet,destSet,edgeClass)
    if p.nline==0: # NO BLAST OUTPUT??
        raise IOError('no BLAST output.  Check that blastall is in your PATH')
    if needToBuild:
        al.build()
    return al

def process_blast(cmd,seq,seqDB,al=None,seqString=None):
    "run blast, pipe in sequence, pipe out aligned interval lines, return an alignment"
    ifile,ofile=os.popen2(cmd)
    if seqString is None:
        seqString=seq
    id=write_fasta(ifile,seqString)
    ifile.close()
    al=read_interval_alignment(ofile,{id:seq},seqDB,al)
    if ofile.close() is not None:
        raise OSError('command %s failed' % cmd)
    return al


def repeat_mask(seq,progname='RepeatMasker',opts=''):
    'Run RepeatMasker on a sequence, return lowercase-masked string'
    temppath=os.tempnam()
    ofile=file(temppath,'w')
    write_fasta(ofile,seq,reformatter=lambda x:x.upper()) # SAVE IN UPPERCASE!
    ofile.close()
    cmd=progname+' '+opts+' '+temppath
    if os.system(cmd)!=0:
        raise OSError('command %s failed' % cmd)
    ofile=file(temppath+'.masked')
    for id,title,seq_masked in read_fasta(ofile):
        break # JUST READ ONE SEQUENCE
    ofile.close()
    cmd='rm -f %s %s.*' % (temppath,temppath)
    if os.system(cmd)!=0:
        raise OSError('command '+cmd+' failed')
    return seq_masked # ONLY THE REPEATS ARE IN LOWERCASE NOW


class BlastDBinverse(object):
    'implements trivial inverse mapping seq --> id'
    def __init__(self,db):
        self.db=db
    def __getitem__(self,seq):
        return seq.pathForward.id
    def __contains__(self,seq):
        try:
            return seq.pathForward.db is self.db
        except AttributeError:
            return False

class SeqDBbase(dict):
    def __reduce__(self): ############################# SUPPORT FOR PICKLING
        return (classutil.ClassicUnpickler, (self.__class__,self.__getstate__()))
    def __setstate__(self,state):
        self.__init__(**state) #JUST PASS KWARGS TO CONSTRUCTOR
    def __invert__(self):
        'keep a reference to an inverse mapping'
        try:
            return self._inverse
        except AttributeError:
            self._inverse=BlastDBinverse(self)
            return self._inverse
    def __hash__(self):
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)
    _cache_max=10000
    def cacheHint(self,owner,ivalDict):
        'save a cache hint dict of {id:(start,stop)} associated with owner'
        d={}
        for id,ival in ivalDict.items(): # BUILD THE CACHE DICTIONARY FOR owner
            if ival[0]<0: # FORCE IVAL INTO POSITIVE ORIENTATION
                ival=(-ival[1],-ival[0])
            if ival[1]-ival[0]>self._cache_max: # TRUNCATE EXCESSIVE LENGTH
                ival=(ival[0],ival[0]+self._cache_max)
            d[id]=[ival[0],ival[1]]
        try:
            self._cache[owner]=d # ADD TO EXISTING CACHE
        except AttributeError:
            import weakref # AUTOMATICALLY REMOVE FROM CACHE IF owner
            self._cache=weakref.WeakKeyDictionary() # GOES OUT OF SCOPE
            self._cache[owner]=d
    def strsliceCache(self,seq,start,stop):
        'get strslice using cache hints, if any'
        try:
            cacheList=self._cache.values()
        except AttributeError:
            raise IndexError('no cache present')
        for d in cacheList:
            try:
                ival=d[seq.id]
            except KeyError:
                continue # NOT IN THIS CACHE, SO SKIP
            if start>=ival[0] and stop<=ival[1]: # CONTAINED IN ival
                try:
                    s=ival[2] # GET SEQ STRING FROM OUR CACHE
                except IndexError: # NEED TO CACHE ival SEQ STRING
                    s=seq.strslice(ival[0],ival[1],useCache=False)
                    ival.append(s)
                return s[start-ival[0]:stop-ival[0]]
        raise IndexError('interval not found in cache')

class SeqDBDescriptor(object):
    'forwards attribute requests to self.pathForward'
    def __init__(self,attr):
        self.attr=attr
    def __get__(self,obj,objtype):
        return getattr(obj.pathForward,self.attr) # RAISES AttributeError IF NONE

class SeqDBSlice(SeqPath):
    'JUST A WRAPPER FOR SCHEMA TO HANG SHADOW ATTRIBUTES ON...'
    id=SeqDBDescriptor('id')
    db=SeqDBDescriptor('db')

class BlastDBbase(SeqDBbase):
    "Container representing Blast database"
    itemClass=FileDBSequence # CLASS TO USE FOR SAVING EACH SEQUENCE
    itemSliceClass=SeqDBSlice # CLASS TO USE FOR SLICES OF SEQUENCE
    def __init__(self,filepath=None,skipSeqLenDict=False,ifile=None,idFilter=None,
                 blastReady=False,blastIndexPath=None,blastIndexDirs=None,**kwargs):
        "format database and build indexes if needed. Provide filepath or file object"
        if filepath is None:
            try:
                filepath=ifile.name
            except AttributeError:
                raise  TypeError("unable to obtain a filename")
        self.filepath = classutil.SourceFileName(str(filepath)) # MARKS AS A FILE PATH
        dict.__init__(self)
        self.set_seqtype()
        self.skipSeqLenDict=skipSeqLenDict
        if blastIndexPath is not None:
            self.blastIndexPath = blastIndexPath
        if blastIndexDirs is not None:
            self.blastIndexDirs = blastIndexDirs
        if skipSeqLenDict:
            self.itemClass=BlastSequenceBase # DON'T USE seqLenDict
        else:
            from dbfile import NoSuchFileError
            try: # THIS WILL FAIL IF SHELVE NOT ALREADY PRESENT...
                self.seqLenDict = classutil.open_shelve(filepath+'.seqlen','r') # READ-ONLY
            except NoSuchFileError: # BUILD: READ ALL SEQ LENGTHS, STORE IN PERSIST DICT
                self.seqLenDict = classutil.open_shelve(filepath+'.seqlen','n') # NEW EMPTY FILE
                ifile,idFilter=self.raw_fasta_stream(ifile,idFilter)
                import sys
                print >>sys.stderr,'Building sequence length index...'
                store_seqlen_dict(self.seqLenDict,ifile,filepath,idFilter)
                self.seqLenDict.close() # FORCE IT TO WRITE DATA TO DISK
                self.seqLenDict = classutil.open_shelve(filepath+'.seqlen','r') # READ-ONLY
        
        self.checkdb() # CHECK WHETHER BLAST INDEX FILE IS PRESENT...
        if not self.blastReady and blastReady: # FORCE CONSTRUCTION OF BLAST DB
            self.formatdb()
        if ifile is not None: # NOW THAT WE'RE DONE CONSTRUCTING, CLOSE THE FILE OBJECT
            ifile.close() # THIS SIGNALS WE'RE COMPLETELY DONE CONSTRUCTING THIS RESOURCE
        classutil.apply_itemclass(self,kwargs)

    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    _pickleAttrs = dict(filepath=0,skipSeqLenDict=0,blastIndexPath=0)

    def test_db_location(self,filepath):
        'check whether BLAST index files ready for use; return self.blastReady status'
        if not os.access(filepath+'.nsd',os.R_OK) \
               and not os.access(filepath+'.psd',os.R_OK) \
               and not os.access(filepath+'.00.nsd',os.R_OK) \
               and not os.access(filepath+'.00.psd',os.R_OK):
            return False
        else: # FOUND INDEX FILES IN THIS LOCATION
            if filepath!=self.filepath:
                self.blastIndexPath = filepath
            return True
    def checkdb(self):
        'look for blast index files in blastIndexPath, standard list of locations'
        for filepath in self.blast_index_paths():
            self.blastReady = self.test_db_location(filepath)
            if self.blastReady:
                break
        return self.blastReady
    def run_formatdb(self,filepath):
        'ATTEMPT TO BUILD BLAST DATABASE INDEXES at filepath'
        dirname = classutil.file_dirpath(filepath)
        if not os.access(dirname,os.W_OK): # CHECK WHETHER DIRECTORY IS WRITABLE
            raise IOError('run_formatdb: directory %s is not writable!' % dirname)
        cmd='formatdb -i "%s" -n "%s" -o T' % (self.filepath,filepath)
        if self._seqtype!=PROTEIN_SEQTYPE:
            cmd += ' -p F' # SPECIAL FLAG REQUIRED FOR NUCLEOTIDE SEQS
        import sys
        print >>sys.stderr,'Building index:',cmd
        if os.system(cmd)!=0: # BAD EXIT CODE, SO COMMAND FAILED
            raise OSError('command %s failed' % cmd)
        self.blastReady=True
        if filepath!=self.filepath:
            self.blastIndexPath = filepath
    def get_blast_index_path(self):
        'get path to base name for BLAST index files'
        try:
            return self.blastIndexPath
        except AttributeError:
            return self.filepath
    # DEFAULT: BUILD INDEX FILES IN self.filepath . HOME OR /tmp 
    blastIndexDirs = ['FILEPATH',os.getcwd,os.path.expanduser,
                      classutil.default_tmp_path]
    def blast_index_paths(self):
        'iterate over possible blast index directories'
        try: # 1ST TRY ACTUAL SAVED LOCATION IF ANY
            yield self.blastIndexPath
        except AttributeError:
            pass
        for m in self.blastIndexDirs: # NOW TRY STANDARD LOCATIONS
            if m=='FILEPATH':
                yield self.filepath
                continue
            elif m == os.path.expanduser:
                s = m('~') # GET HOME DIRECTORY
            elif callable(m):
                s = m()
            else: # TREAT AS STRING
                s = str(m)
            yield os.path.join(s,os.path.basename(self.filepath))
    def formatdb(self,filepath=None):
        'try to build BLAST index files in an appropriate location'
        if filepath is not None: # JUST USE THE SPECIFIED PATH
            return self.run_formatdb(filepath)
        notFirst = False
        for filepath in self.blast_index_paths():
            if notFirst:
                import sys
                print >>sys.stderr,'Trying next entry in self.blastIndexDirs...'
            notFirst = True
            try: # BUILD IN TARGET DIRECTORY
                return self.run_formatdb(filepath)
            except (IOError,OSError): # BUILD FAILED 
                classutil.report_exception() # REPORT IT AND CONTINUE
            
    def set_seqtype(self):
        "Determine whether this database is DNA or protein"
        if os.path.isfile(self.get_blast_index_path()+'.psd') \
               or os.path.isfile(self.get_blast_index_path()+'.00.psd'):
            self._seqtype=PROTEIN_SEQTYPE
            return
        elif os.path.isfile(self.get_blast_index_path()+'.nsd') \
                 or os.path.isfile(self.get_blast_index_path()+'.00.nsd'):
            self._seqtype=DNA_SEQTYPE
            return
        else:
            ifile = file(self.filepath) # READ ONE SEQUENCE TO CHECK ITS TYPE
            try:
                id,title,seq = read_fasta_one_line(ifile)
                self._seqtype = guess_seqtype(seq) # RECORD PROTEIN VS. DNA...
            finally:
                ifile.close()

    def raw_fasta_stream(self,ifile=None,idFilter=None):
        'return a stream of fasta-formatted sequences, and ID filter function if needed'
        if ifile is not None: # JUST USE THE STREAM WE ALREADY HAVE OPEN
            return ifile,idFilter
        try: # DEFAULT: JUST READ THE FASTA FILE, IF IT EXISTS
            return file(self.filepath),idFilter
        except IOError: # TRY READING FROM FORMATTED BLAST DATABASE
            cmd='fastacmd -D -d "%s"' % self.get_blast_index_path()
            return os.popen(cmd),NCBI_ID_PARSER #BLAST ADDS lcl| TO id


    def __iter__(self):
        'generate all IDs in this database'
        for id in self.seqLenDict:
            yield id

    def iteritems(self):
        'generate all IDs in this database'
        for id in self.seqLenDict:
            yield id,self[id]

    def __len__(self):
        "number of total entries in this database"
        return len(self.seqLenDict)

    def __getitem__(self,id):
        "Get sequence matching this ID, using dict as local cache"
        try:
            return dict.__getitem__(self,id)
        except KeyError: # NOT FOUND IN DICT, SO CREATE A NEW OBJECT
            s=self.itemClass(self,id)
            s.db=self # LET IT KNOW WHAT DATABASE IT'S FROM...
            dict.__setitem__(self,id,s) # CACHE IT
            return s

    def warn_about_self_masking(self,seq,methodname='blast'):
        try:
            if seq.db is self:
                import sys
                print >>sys.stderr,'''
WARNING: your query sequence is part of this database.  Pygr alignments
normally do not report self-matches, i.e. the alignment of a sequence interval
to itself, so only homologies to OTHER sequences in the database
(or other intervals of the query sequence, if they are homologous) will be
reported (or an empty query result if no such homologies are found).
To report ALL homologies, including the self-match, simply create a new
sequence object and use that as your query, e.g.
query = sequence.Sequence(str(seq),"myquery")
results = db.%s(query)

To turn off this message, use the verbose=False option''' % methodname
        except AttributeError:
            pass

    def blast(self,seq,al=None,blastpath='blastall',
              blastprog=None,expmax=0.001,maxseq=None,verbose=True,opts='',**kwargs):
        "Run blast search for seq in database, return aligned intervals"
        if verbose:
            self.warn_about_self_masking(seq)
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        if blastprog is None:
            blastprog = blast_program(seq.seqtype(),self._seqtype)
        cmd = '%s -d "%s" -p %s -e %e %s'  \
              %(blastpath,self.get_blast_index_path(),blastprog,float(expmax),opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ' -b %d -v %d' % (maxseq,maxseq)
        return process_blast(cmd,seq,self,al)

    def megablast(self,seq,al=None,blastpath='megablast',expmax=1e-20,
                  maxseq=None,minIdentity=None,maskOpts='-U T -F m',
                  rmPath='RepeatMasker',rmOpts='-xsmall',
                  verbose=True,opts='',**kwargs):
        "Run megablast search with repeat masking."
        if verbose:
            self.warn_about_self_masking(seq,'megablast')
        if not self.blastReady: # HAVE TO BUILD THE formatdb FILES...
            self.formatdb()
        masked_seq = repeat_mask(seq,rmPath,rmOpts)  # MASK REPEATS TO lowercase
        cmd = '%s %s -d "%s" -D 2 -e %e -i stdin %s' \
             % (blastpath,maskOpts,self.get_blast_index_path(),float(expmax),opts)
        if maxseq is not None: # ONLY TAKE TOP maxseq HITS
            cmd += ' -b %d -v %d' % (maxseq,maxseq)
        if minIdentity is not None:
            cmd += ' -p %f' % float(minIdentity)
        return process_blast(cmd,seq,self,al,seqString=masked_seq)


class BlastDB(BlastDBbase):
    """Since NCBI treats FASTA ID as a blob into which they like to stuff
    many fields... and then NCBI BLAST mangles those IDs when it reports
    hits, so they no longer match the true ID... we are forced into
    contortions to rescue the true ID from mangled IDs.  If you dont want
    these extra contortions, use the base class BlastDBbase instead.

    Our workaround strategy: since NCBI packs the FASTA ID with multiple
    IDs (GI, GB, RefSeq ID etc.), we can use any of these identifiers
    that are found in a mangled ID, by storing a mapping of these
    sub-identifiers to the true FASTA ID."""
    id_delimiter='|' # FOR UNPACKING NCBI IDENTIFIERS AS WORKAROUND FOR BLAST ID CRAZINESS
    def unpack_id(self,id):
        "NCBI packs identifier like gi|123456|gb|A12345|other|nonsense. Return as list"
        return id.split(self.id_delimiter)

    def index_unpacked_ids(self,unpack_f=None):
        """Build an index of sub-IDs (unpacked from NCBI nasty habit
        of using the FASTA ID as a blob); you can customize the unpacking
        by overriding the unpack_id function or changing the id_delimiter.
        The index maps each sub-ID to the real ID, so that when BLAST
        hands back a mangled, fragmentary ID, we can unpack that mangled ID
        and look up the true ID in this index.  Any sub-ID that is found
        to map to more than one true ID will be mapped to None (so that
        random NCBI garbage like gnl or NCBI_MITO wont be treated as
        sub-IDs).  
        """
        if unpack_f is None:
            unpack_f=self.unpack_id
        t={}
        for id in self:
            for s in unpack_f(id):
                if s==id: continue # DON'T STORE TRIVIAL MAPPINGS!!
                s=s.upper() # NCBI FORCES ID TO UPPERCASE?!?!
                try:
                    if t[s]!=id and t[s] is not None: 
                        t[s]=None # s NOT UNIQUE, CAN'T BE AN IDENTIFIER!!
                except KeyError:
                    t[s]=id # s UNIQUE, TRY USING s AS AN IDENTIFIER
        for id in t.itervalues():
            if id is not None: # OK THERE ARE REAL MAPPINGS STORED, SO USE THIS
                self._unpacked_dict=t # SAVE THE MAPPING TO REAL IDENTIFIERS
                return
        self._unpacked_dict={} # NO NON-TRIVIAL MAPPINGS, SO JUST SAVE EMPTY MAPPING

    def get_real_id(self,bogusID,unpack_f=None):
        "try to translate an id that NCBI has mangled to the real sequence id"
        if unpack_f is None:
            unpack_f=self.unpack_id
        if not hasattr(self,'_unpacked_dict'):
            self.index_unpacked_ids(unpack_f)
        for s in unpack_f(bogusID):
            s=s.upper() # NCBI FORCES ID TO UPPERCASE?!?!
            try:
                id=self._unpacked_dict[s]
                if id is not None:
                    return id # OK, FOUND A MAPPING TO REAL ID
            except KeyError:
                pass # KEEP TRYING...
        raise KeyError # FOUND NO MAPPING, SO RAISE EXCEPTION

    def __getitem__(self,id):
        "Get sequence matching this ID, using dict as local cache"
        if hasattr(self,'_unpacked_dict'): # TRY USING ID MAPPING
            try:
                id=self.get_real_id(id)
            except KeyError:
                pass
        try:
            return dict.__getitem__(self,id)
        except KeyError: # NOT FOUND IN DICT, SO CREATE A NEW OBJECT
            try:
                s=self.itemClass(self,id)
            except KeyError:
                id=self.get_real_id(id)
                s=self.itemClass(self,id)
            s.db=self # LET IT KNOW WHAT DATABASE IT'S FROM...
            dict.__setitem__(self,id,s) # CACHE IT
            return s



class StoredPathMapping(PathMapping):
    _edgeClass=BlastHitInfo
    def __init__(self,table,srcSet,destSet,edgeClass=None):
        PathMapping.__init__(self)
        self.table=table
        self.srcSet=srcSet
        self.destSet=destSet
        if edgeClass is not None:
            self._edgeClass=edgeClass

    def __getitem__(self,p):
        "Get mapping of a path, using stored table if necessary"
        try: # RETURN STORED MAPPING
            return PathMapping.__getitem__(self,p)
        except KeyError: # TRY TO GET IT FROM THE STORED TABLE
            for ival in self.table[p.path.id]: # READ INTERVAL MAPPINGS ONE BY ONE
                save_interval_alignment(self,ival,self.srcSet,self.destSet,
                                        self._edgeClass) # SAVE IT
            return PathMapping.__getitem__(self,p) # RETURN TOTAL RESULT

    def all_paths(self):
        "Get all source sequences in this mapping"
        for id in self.table:
            p=self.srcSet[id]
            yield p

    # NEED TO ADD APPROPRIATE HOOKS FOR __iter__, items(), ETC.

def getAnnotationAttr(self,attr):
    'forward attributes from slice object if available'
    try:
        return SeqPath.__getattr__(self,attr)
    except AttributeError:
        try:
            return self.db.getSliceAttr(self.db.sliceDB[self.id],attr)
        except KeyError:
            raise AttributeError

def annotation_repr(self):
    if self.annotationType is not None:
        title = self.annotationType
    else:
        title = 'annot'
    if self.orientation>0:
        return '%s%s[%d:%d]' % (title,self.id,self.start,self.stop)
    else:
        return '-%s%s[%d:%d]' % (title,self.id,-self.stop,-self.start)

class AnnotationSeqDescr(object):
    'get the sequence interval corresponding to this annotation'
    def __get__(self,obj,objtype):
        return absoluteSlice(obj._anno_seq,obj._anno_start,obj._anno_start+obj.stop)
class AnnotationSliceDescr(object):
    'get the sequence interval corresponding to this annotation'
    def __get__(self,obj,objtype):
        return relativeSlice(obj.pathForward.sequence,obj.start,obj.stop)
class AnnotationSeqtypeDescr(object):
    'get seqtype of the sequence interval corresponding to this annotation'
    def __get__(self,obj,objtype):
        return obj._anno_seq.seqtype()

class AnnotationSeq(SeqPath):
    'base class representing an annotation'
    start=0
    step=1
    orientation=1
    def __init__(self,id,db,parent,start,stop):
        self.id = id
        self.db = db
        self.stop = stop-start
        self._anno_seq = parent
        self._anno_start = start
        self.path = self
    __getattr__ = getAnnotationAttr
    sequence = AnnotationSeqDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    _seqtype = AnnotationSeqtypeDescr()
    __repr__ =  annotation_repr
    def strslice(self,start,stop):
        raise ValueError('''this is an annotation, and you cannot get a sequence string from it.
Use its sequence attribute to get a sequence object representing this interval.''')


class AnnotationSlice(SeqDBSlice):
    'represents subslice of an annotation'
    __getattr__=getAnnotationAttr
    sequence = AnnotationSliceDescr()
    annotationType = classutil.DBAttributeDescr('annotationType')
    __repr__ =  annotation_repr

class AnnotationDB(dict):
    'container of annotations as specific slices of db sequences'
    def __init__(self,sliceDB,seqDB,annotationType=None,itemClass=AnnotationSeq,
                 itemSliceClass=AnnotationSlice,
                 itemAttrDict=None, # GET RID OF THIS BACKWARDS-COMPATIBILITY KLUGE!!
                 sliceAttrDict=None,maxCache=None,**kwargs):
        '''sliceDB must map identifier to a sliceInfo object;
sliceInfo must have name,start,stop,ori attributes;
seqDB must map sequence ID to a sliceable sequence object;
sliceAttrDict gives optional dict of item attributes that
should be mapped to sliceDB item attributes.
maxCache specfies the maximum number of annotation objects to keep in the cache.'''
        dict.__init__(self)
        if sliceAttrDict is None:
            sliceAttrDict = {}
        if sliceDB is not None:
            self.sliceDB = sliceDB
        else: # NEED TO CREATE / OPEN A DATABASE FOR THE USER
            self.sliceDB = classutil.get_shelve_or_dict(**kwargs)
        self.seqDB = seqDB
        self.annotationType = annotationType
        self.itemClass=itemClass
        self.itemSliceClass=itemSliceClass
        self.sliceAttrDict=sliceAttrDict # USER-PROVIDED ALIASES
        if maxCache is not None:
            self.maxCache = maxCache
    def __reduce__(self): ############################# SUPPORT FOR PICKLING
        return (classutil.ClassicUnpickler, (self.__class__,self.__getstate__()))
    __getstate__ = classutil.standard_getstate ############### PICKLING METHODS
    __setstate__ = classutil.standard_setstate
    _pickleAttrs = dict(sliceDB=0,seqDB=0,annotationType=0,
                        itemClass=0,itemSliceClass=0,sliceAttrDict=0,maxCache=0)
    def __hash__(self):
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)
    def __getitem__(self,k):
        'get annotation object by its ID'
        try: # GET FROM OUR CACHE
            return dict.__getitem__(self,k)
        except KeyError:
            pass
        return self.sliceAnnotation(k,self.sliceDB[k])
    def __setitem__(self,k,v):
        raise KeyError('''you cannot save annotations directly using annoDB[k] = v
Instead, use annoDB.new_annotation(k,sliceInfo) where sliceInfo provides
a sequence ID, start, stop (and any additional info desired), and will be
saved directly to the sliceDB.''')
    def getSliceAttr(self,sliceInfo,attr):
        try:
            k = self.sliceAttrDict[attr] # USE ALIAS IF PROVIDED
        except KeyError:
            return getattr(sliceInfo,attr) # GET ATTRIBUTE AS USUAL
        try: # REMAP TO ANOTHER ATTRIBUTE NAME
            return getattr(sliceInfo,k)
        except TypeError: # TREAT AS int INDEX INTO A TUPLE
            return sliceInfo[k]
    def sliceAnnotation(self,k,sliceInfo,limitCache=True):
        'create annotation and cache it'
        start = int(self.getSliceAttr(sliceInfo,'start'))
        stop = int(self.getSliceAttr(sliceInfo,'stop'))
        try:
            if int(self.getSliceAttr(sliceInfo,'orientation'))<0 and start>=0:
                start,stop = (-stop,-start) # NEGATIVE ORIENTATION COORDINATES
        except AttributeError:
            pass
        if start>=stop:
            raise IndexError('annotation %s has zero or negative length [%s:%s]!'
                             %(k,start,stop))
        a = self.itemClass(k,self,self.seqDB[self.getSliceAttr(sliceInfo,'id')],start,stop)
        try: # APPLY CACHE SIZE LIMIT IF ANY
            if limitCache and self.maxCache<dict.__len__(self):
                self.clear()
        except AttributeError:
            pass
        dict.__setitem__(self,k,a) # CACHE THIS IN OUR DICT
        return a
    def new_annotation(self,k,sliceInfo):
        'save sliceInfo to the annotation database and return annotation object'
        a = self.sliceAnnotation(k,sliceInfo) # 1st CHECK IT GIVES A VALID ANNOTATION
        try:
            self.sliceDB[k] = sliceInfo # NOW SAVE IT TO THE SLICE DATABASE
        except:
            dict.__delitem__(self,k) # DELETE FROM CACHE
            raise
        self._wroteSliceDB = True
        return a
    def foreignKey(self,attr,k):
        'iterate over items matching specified foreign key'
        for t in self.sliceDB.foreignKey(attr,k):
            try:
                yield dict.__getitem__(self,t.id)
            except KeyError:
                yield self.sliceAnnotation(t.id,t)
    def __contains__(self, k): return k in self.sliceDB
    def __len__(self): return len(self.sliceDB)
    def __iter__(self): return iter(self.sliceDB) ########## ITERATORS
    def keys(self): return self.sliceDB.keys()
    def iteritems(self):
        'uses maxCache to manage caching of annotation objects'
        for k,sliceInfo in self.sliceDB.iteritems():
            yield k,self.sliceAnnotation(k,sliceInfo)
    def itervalues(self):
        'uses maxCache to manage caching of annotation objects'
        for k,v in self.iteritems():
            yield v
    def items(self):
        'forces load of all annotation objects into cache'
        return [(k,self.sliceAnnotation(k,sliceInfo,limitCache=False))
                for (k,sliceInfo) in self.sliceDB.items()]
    def values(self):
        'forces load of all annotation objects into cache'
        return [self.sliceAnnotation(k,sliceInfo,limitCache=False)
                for (k,sliceInfo) in self.sliceDB.items()]
    def add_homology(self,seq,search='blast',id=None,idFormat='%s_%d',
                     autoIncrement=False,maxAnnot=999999,
                     maxLoss=None,sliceInfo=None,**kwargs):
        'find homology in our seq db and add as annotations'
        try: # ENSURE THAT sliceAttrDict COMPATIBLE WITH OUR TUPLE FORMAT
            if self.sliceAttrDict['id'] != 0:
                raise KeyError
        except KeyError:
            sliceAttrDict['id'] = 0 # USE TUPLE AS OUR INTERNAL STANDARD FORMAT
            sliceAttrDict['start'] = 1
            sliceAttrDict['stop'] = 2
        if autoIncrement:
            id = len(self.sliceDB)
        elif id is None:
            id = seq.id
        if isinstance(search,str): # GET SEARCH METHOD
            search = getattr(self.seqDB,search)
        if isinstance(seq,str): # CREATE A SEQ OBJECT
            seq = Sequence(seq,str(id))
        al = search(seq,**kwargs) # RUN THE HOMOLOGY SEARCH
        if maxLoss is not None: # REQUIRE HIT BE AT LEAST A CERTAIN LENGTH
            kwargs['minAlignSize'] = len(seq)-maxLoss
        hits = al[seq].keys(**kwargs) # OBTAIN LIST OF HIT INTERVALS
        if len(hits)>maxAnnot:
            raise ValueError('too many hits for %s: %d' %(id,len(hits)))
        out = []
        i = 0
        k = id
        for ival in hits: # CREATE ANNOTATION FOR EACH HIT
            if len(hits)>1: # NEED TO CREATE AN ID FOR EACH HIT
                if autoIncrement:
                    k = len(self.sliceDB)
                else:
                    k = idFormat %(id,i)
                i += 1
            if sliceInfo is not None: # SAVE SLICE AS TUPLE WITH INFO
                a = self.new_annotation(k, (ival.id,ival.start,ival.stop)+sliceInfo)
            else:
                a = self.new_annotation(k, (ival.id,ival.start,ival.stop))
            out.append(a) # RETURN THE ANNOTATION
        return out
    def close(self):
        'if sliceDB needs to be closed, do it and return True, otherwise False'
        try:
            if self._wroteSliceDB:
                self.sliceDB.close()
                self._wroteSliceDB = False # DISK FILE IS UP TO DATE
                return True
        except AttributeError:
            pass
        return False
    def __del__(self):
        if self.close():
            import sys
            print >>sys.stderr,'''
WARNING: you forgot to call AnnotationDB.close() after writing
new annotation data to it.  This could result in failure to properly
store the data in the associated disk file.  To avoid this, we
have automatically called AnnotationDB.sliceDB.close() to write the data
for you, when the AnnotationDB was deleted.'''

class AnnotationServer(AnnotationDB):
    'XMLRPC-ready server for AnnotationDB'
    xmlrpc_methods={'get_slice_tuple':0,'get_slice_items':0,
                    'get_annotation_attr':0, 'keys':0,
                    '__len__':0, '__contains__':0}
    def get_slice_tuple(self, k):
        'get (seqID,start,stop) for a given key'
        try:
            sliceInfo = self.sliceDB[k]
        except KeyError:
            return '' # XMLRPC-acceptable failure code
        start = int(self.getSliceAttr(sliceInfo,'start'))
        stop = int(self.getSliceAttr(sliceInfo,'stop'))
        try:
            if int(self.getSliceAttr(sliceInfo,'orientation'))<0 and start>=0:
                start,stop = (-stop,-start) # NEGATIVE ORIENTATION COORDINATES
        except AttributeError:
            pass
        return (self.getSliceAttr(sliceInfo, 'id'), start, stop)
    def get_slice_items(self):
        'get all (key,tuple) pairs in one query'
        l = []
        for k in self.sliceDB:
            l.append((k,self.get_slice_tuple(k)))
        return l
    def get_annotation_attr(self, k, attr):
        'get the requested attribute of the requested key'
        try:
            sliceInfo = self.sliceDB[k]
        except KeyError:
            return ''
        try:
            return self.getSliceAttr(sliceInfo, attr)
        except AttributeError:
            return ''

class AnnotationClientSliceDB(dict):
    'proxy just queries the server'
    def __init__(self, db):
        self.db = db
        dict.__init__(self)
    def __getitem__(self, k):
        try:
            return dict.__getitem__(self, k)
        except KeyError:
            t = self.db.server.get_slice_tuple(k)
            if t == '':
                raise KeyError('no such annotation: ' + str(k))
            dict.__setitem__(self, k, t)
            return t
    def __setitem__(self, k, v): raise ValueError('XMLRPC client is read-only')
    def keys(self): return self.db.server.keys()
    def __iter__(self): return iter(self.keys())
    def items(self): return self.db.server.get_slice_items()
    def iteritems(self): return iter(self.items())
    def __len__(self): return self.db.server.__len__()
    def __contains__(self, k): return self.db.server.__contains__(k)

class AnnotationClient(AnnotationDB):
    'XMLRPC AnnotationDB client'
    def __init__(self, url, name, seqDB,itemClass=AnnotationSeq,
                 itemSliceClass=AnnotationSlice, **kwargs):
        dict.__init__(self)
        import coordinator
        self.server = coordinator.get_connection(url, name)
        self.url = url
        self.name = name
        self.seqDB = seqDB
        self.sliceDB = AnnotationClientSliceDB(self)
        self.itemClass = itemClass
        self.itemSliceClass = itemSliceClass
    def __getstate__(self):
        return dict(url=self.url,name=self.name,seqDB=self.seqDB)
    def getSliceAttr(self, sliceInfo, attr):
        if attr=='id': return sliceInfo[0]
        elif attr=='start': return sliceInfo[1]
        elif attr=='stop': return sliceInfo[2]
        elif attr=='orientation': raise AttributeError('ori not saved')
        else:
            v = self.server.get_annotation_attr(sliceInfo[0], attr)
            if v=='':
                raise AttributeError('this annotation has no attr: ' + attr)
            return v


class SliceDB(dict):
    'associates an ID with a specific slice of a specific db sequence'
    def __init__(self,sliceDB,seqDB,leftOffset=0,rightOffset=0):
        '''sliceDB must map identifier to a sliceInfo object;
        sliceInfo must have name,start,stop,ori attributes;
        seqDB must map sequence ID to a sliceable sequence object'''
        dict.__init__(self)
        self.sliceDB=sliceDB
        self.seqDB=seqDB
        self.leftOffset=leftOffset
        self.rightOffset=rightOffset
    def __getitem__(self,k):
        try:
            return dict.__getitem__(self,k)
        except KeyError:
            pass
        sliceInfo=self.sliceDB[k]
        seq=self.seqDB[sliceInfo.name]
        myslice=seq[sliceInfo.start-self.leftOffset:sliceInfo.stop+self.rightOffset]
        if sliceInfo.ori<0:
            myslice= -myslice
        self[k]=myslice
        return myslice



"""
class SliceDB(dict):
    'associates an ID with a specific slice of a specific db sequence'
    def __init__(self,sliceDB,seqDB):
        '''sliceDB must map identifier to a sliceInfo object;
        sliceInfo must have name,start,stop,ori attributes;
        seqDB must map sequence ID to a sliceable sequence object'''
        dict.__init__(self)
        self.sliceDB=sliceDB
        self.seqDB=seqDB
    def __getitem__(self,k):
        try:
            return dict.__getitem__(self,k)
        except KeyError:
            sliceInfo=self.sliceDB[k]
            seq=self.seqDB[sliceInfo.name]
            myslice=seq[sliceInfo.start:sliceInfo.stop]
            if sliceInfo.ori<0:
                myslice= -myslice
            self[k]=myslice
            return myslice

"""


class VirtualSeq(SeqPath):
    """Empty sequence object acts purely as a reference system.
    Automatically elongates if slice extends beyond current stop.
    This class avoids setting the stop attribute, taking advantage
    of SeqPath's mechanism for allowing a sequence to grow in length."""
    start=0
    step=1 # JUST DO OUR OWN SIMPLE INIT RATHER THAN CALLING SeqPath.__init__
    _seqtype=DNA_SEQTYPE # ALLOW THIS VIRTUAL COORD SYSTEM TO BE REVERSIBLE
    def __init__(self,id,length=1):
        self.path=self # DANGEROUS TO CALL SeqPath.__init__ WITH path=self!
        self._current_length=length # SO LET'S INIT OURSELVES TO AVOID THOSE PROBLEMS
        self.id=id
    def __getitem__(self,k):
        "Elongate if slice extends beyond current self.stop"
        if isinstance(k,types.SliceType):
            if k.stop>self._current_length:
                self._current_length=k.stop
        return SeqPath.__getitem__(self,k)
    def __len__(self):
        return self._current_length
    def strslice(self,start,end):
        "NO sequence access!  Raise an exception."
        raise ValueError('VirtualSeq has no actual sequence')

class VirtualSeqDB(dict):
    "return a VirtualSeq for any ID requested"
    def __getitem__(self,k):
        try: # IF WE ALREADY CREATED A SEQUENCE FOR THIS ID, RETURN IT
            return dict.__getitem__(self,k)
        except KeyError: # CREATE A VirtualSeq FOR THIS NEW ID
            s=VirtualSeq(k)
            self[k]=s
            return s


class TempMAFIntervalDict(object):
    "placeholder for generating edges that map a given interval to its targets"
    def __init__(self,map,ival):
        self.map=map
        self.ival=ival
    def edges(self):
        "get all mappings of this interval"
        return self.map.edges(self.ival)

def MAF_get_interval(seq,start,end,ori):
    "Alex's reverse intervals are shifted by one, so correct them..."
    if ori== -1:
        return get_interval(seq,start-1,end-1,ori)
    else:
        return get_interval(seq,start,end,ori)

class MAFStoredPathMapping(PathMapping):
    def __init__(self,ival,table,dbset,vdbset=None):
        """Load all alignments that overlap ival, from the database table,
        using dbset as the interface to all of the sequences.
        """
        if vdbset is None: # CREATE A VIRTUAL SEQ DB FOR REFERENCE SEQUENCES
            vdbset=VirtualSeqDB()
        PathMapping.__init__(self)
        self.ival=ival
        self.table=table
        self.dbset=dbset
        vseqs={}
        self.vseqs=vseqs
        id=dbset.getName(ival.path)
        start,stop=ival._abs_interval # GET ABSOLUTE COORDINATES
        for i in table.select('where src_id=%s and src_start<%s and src_end>%s',
                              (id,stop,start)):  # SAVE MAPPING TO vdbset
            save_interval_alignment(self,i,dbset,vdbset,None,MAF_get_interval)
            vseqs[i.dest_id]=None # KEEP TRACK OF ALL OUR VIRTUAL SEQUENCES...
        for vseqID in vseqs: # GET EVERYTHING THAT OUR vseqs MAP TO...
            for i in table.select('where src_id=%s',(vseqID,)): # SAVE MAPPING TO dbset
                if i.src_id==vseqID: # FILTER OUT MYSQL'S CASE-INSENSITIVE MATCHES!!!
                    save_interval_alignment(self,i,vdbset,dbset,None,MAF_get_interval)

# THIS VERSION FAILS IF vseqs HAS TOO MANY ENTRIES!!
##         for i in table.select('where src_id in %s'%(str(tuple(vseqs.keys()+['None'])))): # SAVE MAPPING TO dbset
##             if vseqs.has_key(i.src_id): # FILTER OUT MYSQL'S CASE-INSENSITIVE MATCHES!!!
##                 save_interval_alignment(self,i,vdbset,dbset,None,MAF_get_interval)

    def __getitem__(self,k):
        return TempMAFIntervalDict(self,k)

    def edges(self,ival=None):
        "get all mappings of self.ival, as edges"
        if ival is None:
            ival=self.ival
        try:
            edgeset=PathMapping.__getitem__(self,ival)
        except KeyError: # OK, ACTUALLY NO RESULTS
            print 'KeyError: no results?'
            return # SO NOTHING TO YIELD...
        for e in edgeset.edges():
            for e2 in PathMapping.__getitem__(self,e.destPath).edges():
                if e2.destPath.path!=ival.path: # IGNORE SELF-MATCH
                    yield IntervalTransform(e.reverse(e2.srcPath),e2.destPath)


class KeepUniqueDict(dict):
    'dict that blocks attempts to overwrite an existing key'
    def __setitem__(self,k,v):
        try:
            if self[k] is v:
                return # ALREADY SAVED.  NOTHING TO DO!
        except KeyError: # NOT PRESENT, SO JUST SAVE THE VALUE
            dict.__setitem__(self,k,v)
            return
        raise KeyError('attempt to overwrite existing key!')
    def __hash__(self):
        'ALLOW THIS OBJECT TO BE USED AS A KEY IN DICTS...'
        return id(self)


class PrefixDictInverse(object):
    def __init__(self,db):
        self.db=db
    def __getitem__(self,seq):
        try: # INSTEAD GET FROM seq.pathForward
            return self.db.dicts[seq.pathForward.db] \
                   +self.db.separator+str(seq.pathForward.id)
        except KeyError:
            try:
                if seq.pathForward._anno_seq in self:
                    raise KeyError('this annotation is not in the PrefixUnion, but its sequence is.  You ccan get that using its sequence attribute.')
            except AttributeError:
                pass
            raise KeyError('seq not in PrefixUnionDict')
    def __contains__(self,seq):
        try:
            return seq.pathForward.db in self.db.dicts
        except AttributeError:
            return False


class PrefixUnionMemberDict(dict):
    'd[prefix]=value; d[k] returns value if k is a member of prefix'
    def __init__(self,puDict,default=None,attrMethod=lambda x:x.pathForward.db):
        dict.__init__(self)
        self.puDict=puDict
        self._attrMethod=attrMethod
        if default is not None:
            self.default=default
    def possibleKeys(self):
        for k in self.puDict.prefixDict:
            yield k
    def __setitem__(self,k,v):
        try:
            dict.__setitem__(self,self.puDict.prefixDict[k],v)
        except KeyError:
            raise KeyError('key must be a valid union prefix string!')
    def __getitem__(self,k):
        try:
            return dict.__getitem__(self,self._attrMethod(k))
        except AttributeError:
            raise TypeError('wrong key type? _attrMethod() failed.')
        except KeyError:
            try: # RETURN A DEFAULT VALUE IF WE HAVE ONE
                return self.default
            except AttributeError:
                raise KeyError('key not a member of this union!')

class PrefixUnionDict(object):
    """union interface to a series of dicts, each assigned a unique prefix
       ID 'foo.bar' --> ID 'bar' in dict f associated with prefix 'foo'."""
    def __init__(self,prefixDict=None,separator='.',filename=None,
                 dbClass=BlastDB,trypath=None):
        '''can either be created using prefixDict, or a header file
        for a previously created PrefixUnionDict'''
        if filename is not None: # READ UNION HEADER FILE
            if trypath is None: # DEFAULT: LOOK IN SAME DIRECTORY AS UNION HEADER
                trypath=[os.path.dirname(filename)]
            ifile=file(filename)
            it=iter(ifile)
            separator=it.next().strip('\r\n') # DROP TRAILING CR
            prefixDict={}
            for line in it:
                prefix,filepath=line.strip().split('\t')[:2]
                try:
                    prefixDict[prefix]=dbClass(tryPathList(filepath,trypath))
                except IOError:
                    raise IOError('''unable to open database %s: check path or privileges.
Set trypath to give a list of directories to search.'''
                                  % filepath)
            ifile.close()
        self.separator=separator
        if prefixDict is not None:
            self.prefixDict=prefixDict
        else:
            self.prefixDict={}
        d={}
        for k,v in self.prefixDict.items():
            d[v]=k # CREATE A REVERSE MAPPING
        self.dicts=d

    def __getitem__(self,k):
        "for ID 'foo.bar', return item 'bar' in dict f associated with prefix 'foo'"
        try:
            (prefix,id) = k.split(self.separator)
        except ValueError: # id CONTAINS separator CHARACTER?
            t = k.split(self.separator)
            if len(t)<2:
                raise ValueError('invalid id format; no prefix: '+k)
            prefix = t[0] # ASSUME PREFIX DOESN'T CONTAIN separator
            id = k[len(prefix)+1:] # SKIP PAST PREFIX
        d=self.prefixDict[prefix]
        try: # TRY TO USE int KEY FIRST
            return d[int(id)]
        except (ValueError,KeyError,TypeError): # USE DEFAULT str KEY
            return d[id]

    def __contains__(self,k):
        "test whether ID in union; also check whether seq key in one of our DBs"
        if isinstance(k,str):
            (prefix,id) =k.split(self.separator)
            return id in self.prefixDict[prefix]
        else: # TREAT KEY AS A SEQ, CHECK IF IT IS FROM ONE OF OUR DB
            try:
                db=k.pathForward.db
            except AttributeError:
                raise AttributeError('key must be a sequence with db attribute!')
            return db in self.dicts

    def __iter__(self):
        "generate union of all dicts IDs, each with appropriate prefix."
        for p,d in self.prefixDict.items():
            for id in d:
                yield p+self.separator+id
    
    def iteritems(self):
        "generate union of all dicts items, each id with appropriate prefix."
        for p,d in self.prefixDict.items():
            for id,seq in d.iteritems():
                yield p+self.separator+id,seq

    def iteritemlen(self):
        "generate union of all dicts item lengths, each id with appropriate prefix."
        for p,d in self.prefixDict.items():
            for id,l in d.seqLenDict.iteritems():
                yield p+self.separator+id,l[0]

    def getName(self,path):
        "return fully qualified ID i.e. 'foo.bar'"
        path=path.pathForward
        return self.dicts[path.db]+self.separator+path.id

    def newMemberDict(self,**kwargs):
        'return a new member dictionary (empty)'
        return PrefixUnionMemberDict(self,**kwargs)

    def writeHeaderFile(self,filename):
        'save a header file for this union, to reopen later'
        ifile=file(filename,'w')
        print >>ifile,self.separator
        for k,v in self.prefixDict.items():
            try:
                print >>ifile,'%s\t%s\t' %(k,v.filepath)
            except AttributeError:
                raise AttributeError('seq db %s has no filepath; you can save this to pygr.Data but not to a text HeaderFile!' % k)
        ifile.close()

    def __invert__(self):
        try:
            return self._inverse
        except AttributeError:
            self._inverse=PrefixDictInverse(self)
            return self._inverse
    def __len__(self):
        "number of total entries in this database"
        n=0
        for db in self.dicts:
            n+=len(db)
        return n
    def cacheHint(self,owner,ivalDict):
        'save a cache hint dict of {id:(start,stop)} associated with owner'
        d={}
        for id,ival in ivalDict.items(): # EXTRACT SEPARATE SUBDICT FOR EACH prefix
            prefix=id.split(self.separator)[0] # EXTRACT PREFIX, SEQID
            seqID=id[len(prefix)+1:]
            try: # SAVE TO SEPARATE DICTIONARY FOR EACH prefix
                d[prefix][seqID]=ival
            except KeyError:
                d[prefix]={seqID:ival}
        for prefix,seqDict in d.items():
            try:
                m=self.prefixDict[prefix].cacheHint
            except AttributeError: # CAN'T cacheHint, SO JUST IGNORE
                pass
            else:
                m(owner,seqDict) # PASS CACHE HINT DOWN TO SUBDICTIONARY


class PrefixDictInverseAdder(PrefixDictInverse):
    def getName(self,seq):
        'also handle seq with no db attribute...'
        try:
            return PrefixDictInverse.__getitem__(self,seq)
        except AttributeError: # NO db?  THEN TREAT AS A user SEQUENCE
            userID='user'+self.db.separator+seq.pathForward.id
            s=self.db[userID] # MAKE SURE ALREADY IN user SEQ DICTIONARY
            return userID # ALREADY THERE
                
    def __getitem__(self,seq):
        'handles optional mode that adds seq if not already present'
        try:
            return self.getName(seq)
        except KeyError:
            if self.db.addAll:
                self.db+=seq # FORCE self.db TO ADD THIS TO ITS INDEX
                return self.getName(seq) # THIS SHOULD SUCCEED NOW...
            else: # OTHERWISE JUST RE-RAISE THE ORIGINAL EXCEPTION
                raise


class SeqPrefixUnionDict(PrefixUnionDict):
    'adds method for easily adding a seq or its database to the PUD'
    def __init__(self,addAll=False,**kwargs):
        PrefixUnionDict.__init__(self,**kwargs)
        self._inverse=PrefixDictInverseAdder(self)
        self.addAll=addAll # FORCE AUTOMATIC ADDING

    def __iadd__(self,k):
        'add a sequence or database to prefix-union, with a unique prefix'
        if k in (~self): # k ALREADY IN ONE OF OUR DATABASES
            return self
        try: # OK, JUST ADD ITS DATABASE!
            db=k.db # GET DB DIRECTLY FROM SeqPath object
        except AttributeError:
            try:
                db=k.pathForward.db # GET DB FROM pathForward
            except AttributeError: # USER SEQUENCE, NOT FROM ANY CONTAINER?!
                try: # SAVE TO user SEQUENCE DICT
                    d=self.prefixDict['user']
                except KeyError: # NEED TO CREATE A user DICT
                    d=KeepUniqueDict()
                    self.prefixDict['user']=d
                    self.dicts[d]='user'
                d[k.pathForward.id]=k.pathForward # ADD TO user DICTIONARY
                return self
        # db MUST BE A SEQ DATABASE STYLE DICT...
        if db in self.dicts: # ALREADY IS ONE OF OUR DATABASES
            return self # NOTHING FURTHER TO DO
        try: # USE LAST FIELD OF ITS persistent_id
            id=db._persistent_id.split('.')[-1]
        except AttributeError:
            try: # TRY TO GET THE NAME FROM filepath ATTRIBUTE
                id = os.path.basename(db.filepath).split('.')[0]
                if id in self.prefixDict:
                    raise ValueError('''
It appears that two different sequence databases are being
assigned the same prefix ("%s", based on the filepath)!
For this reason, the attempted automatic construction of
a PrefixUnionDict for you cannot be completed!
You should instead construct a PrefixUnionDict that assigns
a unique prefix to each sequence database, and supply it
directly as the seqDict argument to the NLMSA constructor.''' % id)
            except AttributeError:
                id = 'noname%d'%len(self.dicts) # CREATE AN ARBITRARY UNIQUE ID
        self.prefixDict[id]=db
        self.dicts[db]=id
        return self # IADD MUST RETURN SELF!
        

class DummyProxy(object):
    pass
class DummyProxyDict(dict):
    def __init__(self):
        dict.__init__(self)
        self.n=0
    def __call__(self):
        a=DummyProxy()
        i=self.n
        self[i]=a
        self.n+=1
        return i,a
cacheProxyDict=DummyProxyDict()

class BlastDBXMLRPC(BlastDB):
    'XMLRPC server wrapper around a standard BlastDB'
    xmlrpc_methods={"getSeqLen":0,"strslice":0,"getSeqLenDict":0}
    def getSeqLen(self,id):
        'get sequence length, or -1 if not found'
        try:
            return len(self[id]) 
        except KeyError:
            return -1  # SEQUENCE OBJECT DOES NOT EXIST
    def getSeqLenDict(self):
        'return seqLenDict over XMLRPC'
        d = {}
        for k,v in self.seqLenDict.items():
            d[k] = v[0],str(v[1]) # CONVERT TO STR TO ALLOW OFFSET>2GB
        return d # XML-RPC CANNOT HANDLE INT > 2 GB, SO FORCED TO CONVERT...
    def strslice(self,id,start,stop):
        'return string sequence for specified interval in the specified sequence'
        if start<0: # HANDLE NEGATIVE ORIENTATION
            return str((-(self[id]))[-stop:-start])
        else: # POSITIVE ORIENTATION
            return str(self[id][start:stop])



    
class XMLRPCSequence(SequenceBase):
    "Represents a sequence in a blast database, accessed via XMLRPC"
    def __init__(self,db,id,length):
        self.db=db
        self.id=id
        self.length=length
        SequenceBase.__init__(self)
    def strslice(self,start,end,useCache=True):
        "XMLRPC access to slice of a sequence"
        if useCache:
            try:
                return self.db.strsliceCache(self,start,end)
            except IndexError: # NOT FOUND IN CACHE
                pass # JUST USE OUR REGULAR XMLRPC METHOD
        return self.db.server.strslice(self.id,start,end) # GET FROM XMLRPC
    def __len__(self):
        return self.length

class XMLRPCSeqLenDict(object):
    'descriptor that returns dictionary of remote server seqLenDict'
    def __init__(self,attr):
        self.attr = attr
    def __get__(self,obj,objtype):
        'only called if attribute does not already exist. Saves result as attribute'
        d = obj.server.getSeqLenDict()
        for k,v in d.items():
            d[k] = v[0],int(v[1]) # CONVERT OFFSET STR BACK TO INT
        obj.__dict__[self.attr] = d # PROVIDE DIRECTLY TO THE __dict__
        return d


class XMLRPCSequenceDB(SeqDBbase):
    'XMLRPC client: access sequence database over XMLRPC'
    itemClass = XMLRPCSequence # CLASS TO USE FOR SAVING EACH SEQUENCE
    itemSliceClass = SeqDBSlice # CLASS TO USE FOR SLICES OF SEQUENCE
    seqLenDict = XMLRPCSeqLenDict('seqLenDict') # INTERFACE TO SEQLENDICT
    def __init__(self,url=None,name=None):
        dict.__init__(self)
        import coordinator
        self.server = coordinator.get_connection(url,name)
        self.url = url
        self.name = name
    def __getstate__(self): ################ SUPPORT FOR UNPICKLING
        return dict(url=self.url,name=self.name)
    def __getitem__(self,id):
        try:
            return dict.__getitem__(self,id)
        except:
            pass
        l = self.server.getSeqLen(id)
        if l>0:
            s = self.itemClass(self,id,l)
            self[id] = s
            return s
        raise KeyError('%s not in this database' % id)
    def __iter__(self):
        'generate all IDs in this database'
        for id in self.seqLenDict:
            yield id

    def iteritems(self):
        'generate all IDs in this database'
        for id in self.seqLenDict:
            yield id,self[id]

    def __len__(self):
        "number of total entries in this database"
        return len(self.seqLenDict)


def fastaDB_unpickler(klass,srcfile,kwargs):
    o = klass(srcfile,**kwargs) # INITIALIZE, BUILD INDEXES, ETC.
    o._saveLocalBuild = True # MARK FOR LOCAL PYGR.DATA SAVE
    return o
fastaDB_unpickler.__safe_for_unpickling__ = 1
class FastaDB(object):
    'unpickling this object will attempt to construct BlastDB from filepath'
    def __init__(self,filepath,klass=BlastDB,**kwargs):
        self.filepath = filepath
        self.klass = klass
        self.kwargs = kwargs
    def __reduce__(self):
        return (fastaDB_unpickler,(self.klass,self.filepath,self.kwargs))
