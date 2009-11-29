import unittest
from testlib import testutil, PygrTestProgram

import ConfigParser
import glob
import os
import string
import sys

import pygr.Data

try:
    import hashlib
except ImportError:
    import md5 as hashlib

config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                    'smallSampleKey_nlmsa': ''})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
mafDir = config.get('megatests_dm2', 'mafDir')
seqDir = config.get('megatests_dm2', 'seqDir')
smallSampleKey = config.get('megatests_dm2', 'smallSampleKey_nlmsa')
testInputDir = config.get('megatests', 'testInputDir')
testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

if smallSampleKey:
    smallSamplePostfix = '_' + smallSampleKey
else:
    smallSamplePostfix = ''

## mafDir CONTAINS FOLLOWING DM2 MULTIZ15WAY MAF ALIGNMENTS
## seqDir CONTAINS FOLLOWING 15 GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        outfileName = 'splicesite_dm2.txt' # CHR4H TESTING
##        outputName = 'splicesite_dm2_multiz15way.txt' # CHR4H TESTING
## testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList)) SHOULD
## BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'anoGam1': 'A. gambiae Genome (February 2003)',
    'apiMel2': 'A. mellifera Genome (January 2005)',
    'dm2': 'D. melanogaster Genome (April 2004)',
    'dp4': 'D. pseudoobscura Genome (February 2006)',
    'droAna3': 'D. ananassae Genome (February 2006)',
    'droEre2': 'D. erecta Genome (February 2006)',
    'droGri2': 'D. grimshawi Genome (February 2006)',
    'droMoj3': 'D. mojavensis Genome (February 2006)',
    'droPer1': 'D. persimilis Genome (October 2005)',
    'droSec1': 'D. sechellia Genome (October 2005)',
    'droSim1': 'D. simulans Genome (April 2005)',
    'droVir3': 'D. virilis Genome (February 2006)',
    'droWil1': 'D. willistoni Genome (February 2006)',
    'droYak2': 'D. yakuba Genome (November 2005)',
    'triCas2': 'T. castaneum Genome (September 2005)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['anoGam1', 'apiMel2', 'dm2', 'dp4', 'droAna3', 'droEre2',
                  'droGri2', 'droMoj3', 'droPer1', 'droSec1', 'droSim1',
                  'droVir3', 'droWil1', 'droYak2', 'triCas2']


class PygrBuildNLMSAMegabase(unittest.TestCase):

    def setUp(self, testDir=None):
        '''restrict megatest to an initially empty directory, need
        large space to perform'''
        import random
        tmpList = [c for c in 'PygrBuildNLMSAMegabase']
        random.shuffle(tmpList)
        # Comment out the next line to run in current directory.
        testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList))
        if testDir is None:
            testDir = 'TEST_' + ''.join(tmpList)
        try:
            os.mkdir(testDir)
            testDir = os.path.realpath(testDir)
        except:
            raise IOError
        self.path = testDir
        try:
            tmpFileName = os.path.join(testDir, 'DELETE_THIS_TEMP_FILE')
            open(tmpFileName, 'w').write('A' * 1024 * 1024)
        except:
            raise IOError
        pygr.Data.update(self.path)
        from pygr import seqdb
        for orgstr in msaSpeciesList:
            genome = seqdb.BlastDB(os.path.join(seqDir, orgstr))
            genome.__doc__ = docStringDict[orgstr]
            pygr.Data.addResource('TEST.Seq.Genome.' + orgstr, genome)
        pygr.Data.save()

    def copyFile(self, filename): # COPY A FILE INTO TEST DIRECTORY
        newname = os.path.join(self.path, os.path.basename(filename))
        open(newname, 'w').write(open(filename, 'r').read())
        return newname

    def tearDown(self):
        'delete the temporary directory and files, restore pygr.Data path'
        # Delete them bottom-up for obvious reasons.
        for dirpath, subdirs, files in os.walk(self.path, topdown=False):
            # Note: this part may not work in directories on NFS due to
            # creation of lock files (.nfsXXXXXXXXX), which will only allow
            # deletion after pygr.Data has been closed.
            for filename in files:
                os.remove(os.path.join(dirpath, filename))
            os.rmdir(dirpath)
        # Restore original pygr.Data path to remedy lack of isolation
        # between tests from the same run
        pygr.Data.update(None)


class Build_Test(PygrBuildNLMSAMegabase):

    def test_seqdb(self):
        'Check pygr.Data contents'
        l = pygr.Data.dir('TEST')
        preList = ['TEST.Seq.Genome.' + orgstr for orgstr in msaSpeciesList]
        assert l == preList

    def test_build(self):
        'Test building an NLMSA and querying results'
        from pygr import seqdb, cnestedlist
        genomedict = {}
        for orgstr in msaSpeciesList:
            genomedict[orgstr] = pygr.Data.getResource('TEST.Seq.Genome.'
                                                       + orgstr)
        uniondict = seqdb.PrefixUnionDict(genomedict)
        if smallSampleKey:
            maflist = (os.path.join(mafDir, smallSampleKey + '.maf'), )
        else:
            maflist = glob.glob(os.path.join(mafDir, '*.maf'))
            maflist.sort()
        msaname = os.path.join(self.path, 'dm2_multiz15way')
        # 500MB VERSION
        msa1 = cnestedlist.NLMSA(msaname, 'w', uniondict, maflist,
                                 maxlen=536870912, maxint=22369620)
        msa1.__doc__ = 'TEST NLMSA for dm2 multiz15way'
        pygr.Data.addResource('TEST.MSA.UCSC.dm2_multiz15way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.dm2_multiz15way')
        outfileName = os.path.join(testInputDir, 'splicesite_dm2%s.txt'
                                   % smallSamplePostfix)
        outputName = os.path.join(testInputDir,
                                  'splicesite_dm2%s_multiz15way.txt'
                                  % smallSamplePostfix)
        newOutputName = os.path.join(self.path, 'splicesite_new1.txt')
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        outfile = open(newOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['dm2' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['dm2' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'dm2', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'dm2', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(newOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()

        # TEXT<->BINARY TEST
        msafilelist = glob.glob(msaname + '*')
        msa.save_seq_dict()
        cnestedlist.dump_textfile(msaname, os.path.join(self.path,
                                                       'dm2_multiz15way.txt'))
        for filename in msafilelist:
            os.remove(filename)
        runPath = os.path.realpath(os.curdir)
        os.chdir(self.path)
        cnestedlist.textfile_to_binaries('dm2_multiz15way.txt')
        os.chdir(runPath)

        msa1 = cnestedlist.NLMSA(msaname, 'r')
        msa1.__doc__ = 'TEST NLMSA for dm2 multiz15way'
        pygr.Data.addResource('TEST.MSA.UCSC.dm2_multiz15way', msa1)
        pygr.Data.save()
        msa = pygr.Data.getResource('TEST.MSA.UCSC.dm2_multiz15way')
        newOutputName = os.path.join(self.path, 'splicesite_new2.txt')
        tmpInputName = self.copyFile(outfileName)
        tmpOutputName = self.copyFile(outputName)
        outfile = open(newOutputName, 'w')
        for lines in open(tmpInputName, 'r').xreadlines():
            chrid, intstart, intend, nobs = string.split(lines.strip(), '\t')
            intstart, intend, nobs = int(intstart), int(intend), int(nobs)
            site1 = msa.seqDict['dm2' + '.' + chrid][intstart:intstart + 2]
            site2 = msa.seqDict['dm2' + '.' + chrid][intend - 2:intend]
            edges1 = msa[site1].edges()
            edges2 = msa[site2].edges()
            if len(edges1) == 0: # EMPTY EDGES
                wlist = str(site1), 'dm2', chrid, intstart, intstart + 2, \
                        '', '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            if len(edges2) == 0: # EMPTY EDGES
                wlist = str(site2), 'dm2', chrid, intend - 2, intend, '', \
                        '', '', '', ''
                outfile.write('\t'.join(map(str, wlist)) + '\n')
            saveList = []
            for src, dest, e in edges1:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            for src, dest, e in edges2:
                if len(str(src)) != 2 or len(str(dest)) != 2:
                    continue
                dotindex = (~msa.seqDict)[src].index('.')
                srcspecies, src1 = (~msa.seqDict)[src][:dotindex], \
                        (~msa.seqDict)[src][dotindex + 1:]
                dotindex = (~msa.seqDict)[dest].index('.')
                destspecies, dest1 = (~msa.seqDict)[dest][:dotindex], \
                        (~msa.seqDict)[dest][dotindex + 1:]
                wlist = str(src), srcspecies, src1, src.start, src.stop, \
                        str(dest), destspecies, dest1, dest.start, dest.stop
                saveList.append('\t'.join(map(str, wlist)) + '\n')
            saveList.sort() # SORTED IN ORDER TO COMPARE WITH PREVIOUS RESULTS
            for saveline in saveList:
                outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(newOutputName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(tmpOutputName, 'r').read())
        assert md5old.digest() == md5new.digest()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
