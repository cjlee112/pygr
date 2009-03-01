
import sys, os, string, glob

axtDir = '/result/pygr_megatest/axt_data'
seqDir = '/result/pygr_megatest/seq_data3'

## axtDir CONTAINS: hg18_canFam2  hg18_mm8  hg18_panTro2  hg18_rn4  hg18_self
## seqDir CONTAINS FOLLOWING 15 GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        outfileName = 'splicesite_hg18.txt' # CHR4H TESTING
##        outputName = 'splicesite_hg18_pairwise5way.txt' # CHR4H TESTING
## testDir = os.path.join('/usr/tmp/deepreds', 'TEST_' + ''.join(tmpList)) SHOULD BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'canFam2':'Dog Genome (May 2005)',
    'hg18':'Human Genome (May 2006)',
    'mm8':'Mouse Genome (March 2006)',
    'panTro2':'Chimpanzee Genome (March 2006)',
    'rn4':'Rat Genome (November 2004)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['canFam2', 'hg18', 'mm8', 'panTro2', 'rn4']

class PygrBuildNLMSAMegabase(object):
    'restrict megatest to an initially empty directory, need large space to perform'
    def __init__(self, testDir = None):
        import random
        tmpList = [c for c in 'PygrBuildNLMSAMegabase']
        random.shuffle(tmpList)
        testDir = os.path.join('/usr/tmp/deepreds', 'TEST_' + ''.join(tmpList)) # FOR TEST, SHOULD BE DELETED
        if testDir is None: testDir = 'TEST_' + ''.join(tmpList) # NOT SPECIFIED, USE CURRENT DIRECTORY
        try:
            os.mkdir(testDir)
            testDir = os.path.realpath(testDir)
        except:
            raise IOError
        self.path = testDir
        try:
            tmpFileName = os.path.join(testDir, 'DELETE_THIS_TEMP_FILE')
            open(tmpFileName, 'w').write('A'*1024*1024) # WRITE 1MB FILE FOR TESTING
        except:
            raise IOError
        os.environ['PYGRDATAPATH'] = self.path
        import pygr.Data
        from pygr import seqdb
        for orgstr in msaSpeciesList:
            genome = seqdb.BlastDB(os.path.join(seqDir, orgstr))
            genome.__doc__ = docStringDict[orgstr]
            pygr.Data.getResource.addResource('TEST.Seq.Genome.' + orgstr, genome)
        pygr.Data.save()
    def copyFile(self, filename): # COPY A FILE INTO TEST DIRECTORY
        newname = os.path.join(self.path, os.path.basename(filename))
        open(newname, 'w').write(open(filename, 'r').read())
        return newname
    def teardown(self):
        'delete the temporary directory and files'
        for dirpath, subdirs, files in os.walk(self.path, topdown = False): # SHOULD BE DELETED BOTTOM-UP FASHION
            # THIS PART MAY NOT WORK IN NFS MOUNTED DIRECTORY DUE TO .nfsXXXXXXXXX CREATION
            # IN NFS MOUNTED DIRECTORY, IT CANNOT BE DELETED UNTIL CLOSING PYGRDATA
            for filename in files:
                os.remove(os.path.join(dirpath, filename))
            os.rmdir(dirpath)

class Build_Test(PygrBuildNLMSAMegabase):
    def seqdb_test(self): # CHECK PYGR.DATA CONTENTS
        os.environ['PYGRDATAPATH'] = self.path
        import pygr.Data
        l = pygr.Data.dir('TEST')
        preList = ['TEST.Seq.Genome.' + orgstr for orgstr in msaSpeciesList]
        assert l == preList
    def build_test(self): # BUILD NLMSA AND QUERY RESULT COMPARISON
        os.environ['PYGRDATAPATH'] = self.path
        import pygr.Data
        from pygr import seqdb, cnestedlist
        genomedict = {}
        for orgstr in msaSpeciesList:
            genomedict[orgstr] = pygr.Data.getResource('TEST.Seq.Genome.' + orgstr)
        uniondict = seqdb.PrefixUnionDict(genomedict)
        import glob
        axtlist = glob.glob(os.path.join(axtDir, '*/chrY.*.net.axt')) # CHRY TESTING
        axtlist.sort()
        msaname = os.path.join(self.path, 'hg18_pairwise5way')
        # 500MB VERSION
        msa1 = cnestedlist.NLMSA(msaname, 'w', uniondict, axtFiles = axtlist, maxlen = 536870912, maxint = 22369620)
        msa1.save_seq_dict()
        msa1.__doc__ = 'TEST NLMSA for hg18 pairwise5way'
        pygr.Data.getResource.addResource('TEST.MSA.UCSC.hg18_pairwise5way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.hg18_pairwise5way')
        outfileName = 'splicesite_hg18_chrY.txt' # CHRY TESTING
        outputName = 'splicesite_hg18_chrY_pairwise5way.txt' # CHRY TESTING
        newOutputName = 'splicesite_new1.txt'
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        tmpNewOutputName = os.path.join(self.path, newOutputName)
        outfile = open(tmpNewOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['hg18' + '.' + chrid][intstart:intstart+2]
            site2 = msa.seqDict['hg18' + '.' + chrid][intend-2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'hg18', chrid, intstart, intstart+2, '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'hg18', chrid, intend-2, intend, '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2: continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], (~msa.seqDict)[src][dotindex+1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], (~msa.seqDict)[dest][dotindex+1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, str(dest), \
                    destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2: continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], (~msa.seqDict)[src][dotindex+1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], (~msa.seqDict)[dest][dotindex+1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, str(dest), \
                    destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        import md5
        md5old = md5.new()
        md5old.update(open(tmpNewOutputName, 'r').read())
        md5new = md5.new()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest() # MD5 COMPARISON INSTEAD OF COMPARING EACH CONTENTS

        # TEXT<->BINARY TEST
        msafilelist = glob.glob(msaname + '*')
        cnestedlist.dump_textfile(msaname, os.path.join(self.path, 'hg18_pairwise5way.txt'))
        for filename in msafilelist: os.remove(filename)
        runPath = os.path.realpath(os.curdir)
        os.chdir(self.path)
        cnestedlist.textfile_to_binaries('hg18_pairwise5way.txt')
        os.chdir(runPath)

        msa1 = cnestedlist.NLMSA(msaname, 'r')
        msa1.__doc__ = 'TEST NLMSA for hg18 pairwise5way'
        pygr.Data.getResource.addResource('TEST.MSA.UCSC.hg18_pairwise5way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.hg18_pairwise5way')
        newOutputName = 'splicesite_new2.txt'
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        tmpNewOutputName = os.path.join(self.path, newOutputName)
        outfile = open(tmpNewOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['hg18' + '.' + chrid][intstart:intstart+2]
            site2 = msa.seqDict['hg18' + '.' + chrid][intend-2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'hg18', chrid, intstart, intstart+2, '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'hg18', chrid, intend-2, intend, '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2: continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], (~msa.seqDict)[src][dotindex+1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], (~msa.seqDict)[dest][dotindex+1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, str(dest), \
                    destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2: continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], (~msa.seqDict)[src][dotindex+1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], (~msa.seqDict)[dest][dotindex+1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, str(dest), \
                    destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        import md5
        md5old = md5.new()
        md5old.update(open(tmpNewOutputName, 'r').read())
        md5new = md5.new()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest() # MD5 COMPARISON INSTEAD OF COMPARING EACH CONTENTS

