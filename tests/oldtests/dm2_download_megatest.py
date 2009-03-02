# test via
# python protest.py dm2_download_megatest.py

from pygr import nlmsa_utils
from nosebase import get_pygr_data_path
import os

def rm_recursive(top):
    'recursively remove top and everything in it!'
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)

#'http://biodb.bioinformatics.ucla.edu/PYGRDATA/dm2_multiz9way.txt.gz',
class NLMSADownload_Test(object):
    '''try to save and build via download catalog auto-constructed from biodb site'''
    def __init__(self,url='http://biodb.bioinformatics.ucla.edu/PYGRDATA/',
                 testDir = '/tmp'):
        self.url = url
        import random
        self.testDir = os.path.join(testDir,'test%d' % random.randint(1,99999))
        self.pygrdatapath = ','.join([self.testDir,
                               'http://biodb2.bioinformatics.ucla.edu:5000'])
    def setup(self):
        'create pygr.Data entries for all NLMSAs on biodb/PYGRDATA site'
        os.mkdir(self.testDir)
        pygrData = get_pygr_data_path(self.pygrdatapath)
        from pygr.apps.catalog_downloads import save_NLMSA_downloaders
        save_NLMSA_downloaders(self.url)
    ## def setup(self):
    ##     'create pygr.Data entries for building the target NLMSA'
    ##     os.mkdir(self.testDir)
    ##     pygrData = get_pygr_data_path(self.pygrdatapath)
    ##     source = pygrData.SourceURL(self.url)
    ##     source.__doc__ = 'textdump of NLMSA to test'
    ##     pygrData.Bio.MSA.UCSC.dm2_multiz9way.txt = source
    ##     msaref = nlmsa_utils.NLMSABuilder(source)
    ##     msaref.__doc__ = 'NLMSA builder to test'
    ##     pygrData.Bio.MSA.UCSC.dm2_multiz9way = msaref
    ##     pygrData.save()
    def download_test(self):
        'test building the NLMSA, and a simple query'
        os.environ['PYGRDATADOWNLOAD'] = self.testDir
        os.environ['PYGRDATABUILDDIR'] = self.testDir
        pygrData = get_pygr_data_path(self.pygrdatapath) # reload rsrc db
        pygrData.Bio.MSA.UCSC.dm2_multiz9way() # build it!
        pygrData.save() # save the built resources
        pygrData = get_pygr_data_path(self.pygrdatapath) # reload rsrc db
        msa = pygrData.Bio.MSA.UCSC.dm2_multiz9way() # already built
        chr4 = msa.seqDict['dm2.chr4']
        result = msa[chr4[:10000]]
        assert len(result) == 9
    def teardown(self):
        'clean up our temporary directory'
        rm_recursive(self.testDir)
        
    
    
