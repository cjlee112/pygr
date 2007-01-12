import cnestedlist
import sequence

class NLMSAServer(cnestedlist.NLMSA):
    'serves NLMSA via serializable method calls for XMLRPC'
    xmlrpc_methods={'getSlice':0,'getInfo':0}
    def getSlice(self,seqID,start,stop):
        'perform an interval query and return results as raw ivals'
        seq=self.seqDict[seqID]
        nlmsa_id,ns,offset=self.seqs[seq] # GET UNION INFO FOR THIS SEQ
        ival=sequence.absoluteSlice(seq,start,stop) # GET THE INTERVAL
	try:
	    myslice=self[ival] # DO THE QUERY
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
    def __init__(self,url,name,**kwargs):
        cnestedlist.NLMSA.__init__(self,mode='xmlrpc',**kwargs)
        import coordinator
        self.server=coordinator.get_connection(url) # GET CONNECTION TO THE SERVER
        self.url=url
        self.name=name
        l=self.server.methodCall(self.name,'getInfo',[]) # READ NS INFO TABLE
        for nsID,is_lpo,nsLength,is_union in l:
            ns=cnestedlist.NLMSASequence(self,None,None,'onDemand',is_union,nsLength) # is_lpo AUTOMATIC
            self.seqs[None]=ns # ADD THIS TO THE INDEX
    def doSlice(self,seq):
        'getSlice from the server, and create an NLMSASlice object from results'
        result=self.server.methodCall(self.name,'getSlice',[self.seqs.getSeqID(seq),
                                      seq.start,seq.stop])
        if result=='':
            raise KeyError('this interval is not aligned!')
        id,l,d=result
        for nlmsaID,(seqID,nsID) in d: # SAVE SEQ INFO TO INDEX
            self.seqs.saveSeq(seqID,nsID,0,nlmsaID)
        return id,l # HAND BACK THE RAW INTEGER INTERVAL DATA
    def __getitem__(self,k):
        'directly call slice without any ID lookup -- will be done server-side'
        return cnestedlist.NLMSASlice(self.seqlist[0],k.start,k.stop,-1,-1,k)


