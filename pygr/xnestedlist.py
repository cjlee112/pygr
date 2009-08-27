import cnestedlist
from nlmsa_utils import EmptySliceError,EmptySlice
import sequence

class NLMSAServer(cnestedlist.NLMSA):
    'serves NLMSA via serializable method calls for XMLRPC'
    xmlrpc_methods={'getSlice':0,'getInfo':0}
    def getSlice(self,seqID,start,stop):
        'perform an interval query and return results as raw ivals'
        try:
            seq=self.seqDict[seqID]
            nlmsa_id,ns,offset=self.seqs[seq] # GET UNION INFO FOR THIS SEQ
        except KeyError:
            return '' # failure code
        ival=sequence.absoluteSlice(seq,start,stop) # GET THE INTERVAL
        try:
            myslice=self[ival] # DO THE QUERY
        except EmptySliceError:
            return 'EMPTY'
        except KeyError:
            return ''  # FAILURE CODE
        ivals=myslice.rawIvals() # GET RAW INTERVAL DATA
        d={}
        d[nlmsa_id]=self.seqs.IDdict[str(nlmsa_id)] # SAVE INDEX INFO FOR SOURCE SEQ
        for v in ivals: # SAVE INDEX INFO FOR TARGET SEQS
            id=v[2] # target_id NLMSA_ID
            if not self.seqlist.is_lpo(id): # ONLY NON-LPO SEQS STORED IN THIS INDEX
                d[id]=self.seqs.IDdict[str(id)]
        l=[(key,val) for key,val in d.items()] # XMLRPC CAN'T HANDLE int DICT, SO USE LIST
        return nlmsa_id,ivals,l # LIST OF ALIGNED IVALS, LIST OF (nlmsa_id,(seqID,nsID))
    def getInfo(self):
        'return list of tuples describing NLMSASequences in this NLMSA'
        l=[]
        for ns in self.seqlist:
            l.append((ns.id,ns.is_lpo,ns.length,ns.is_union))
        return l


class NLMSAClient(cnestedlist.NLMSA):
    'client for accessing NLMSAServer via XMLRPC'
    def __init__(self,url=None,name=None,idDictClass=dict,**kwargs):
        cnestedlist.NLMSA.__init__(self,mode='xmlrpc',idDictClass=idDictClass,**kwargs)
        import coordinator
        self.server=coordinator.get_connection(url,name) # GET CONNECTION TO THE SERVER
        self.url=url
        self.name=name
        l=self.server.getInfo() # READ NS INFO TABLE
        for nsID,is_lpo,nsLength,is_union in l:
            ns=cnestedlist.NLMSASequence(self,None,None,'onDemand',is_union,nsLength) # is_lpo AUTOMATIC
            self.addToSeqlist(ns) # ADD THIS TO THE INDEX
    def close(self):
        pass # required interface, but nothing to do
    def doSlice(self,seq):
        'getSlice from the server, and create an NLMSASlice object from results'
        result=self.server.getSlice(self.seqs.getSeqID(seq),seq.start,seq.stop)
        if result=='':
            raise KeyError('this interval is not aligned!')
        elif result == 'EMPTY':
            raise EmptySliceError
        id,l,d=result
        for nlmsaID,(seqID,nsID) in d: # SAVE SEQ INFO TO INDEX
            self.seqs.saveSeq(seqID,nsID,0,nlmsaID)
        return id,l # HAND BACK THE RAW INTEGER INTERVAL DATA
    def __getitem__(self,k):
        'directly call slice without any ID lookup -- will be done server-side'
        try:
            return cnestedlist.NLMSASlice(self.seqlist[0],k.start,k.stop,-1,-1,k)
        except EmptySliceError:
            return EmptySlice(k)
    def __getstate__(self):
        return dict(url=self.url,name=self.name,seqDict=self.seqDict)


