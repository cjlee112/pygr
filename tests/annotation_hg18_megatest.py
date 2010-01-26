import unittest
from testlib import testutil, PygrTestProgram

import ConfigParser
import os
import string
import sys

from pygr.mapping import Collection
import pygr.Data

try:
    import hashlib
except ImportError:
    import md5 as hashlib

config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                    'smallSampleKey': ''})
config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
             os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
             '.pygrrc', 'pygr.cfg'])
msaDir = config.get('megatests_hg18', 'msaDir')
seqDir = config.get('megatests_hg18', 'seqDir')
smallSampleKey = config.get('megatests_hg18', 'smallSampleKey')
testInputDB = config.get('megatests', 'testInputDB')
testInputDir = config.get('megatests', 'testInputDir')
testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

if smallSampleKey:
    smallSamplePostfix = '_' + smallSampleKey
else:
    smallSamplePostfix = ''

## msaDir CONTAINS PRE-BUILT NLMSA
## seqDir CONTAINS GENOME ASSEMBLIES AND THEIR SEQDB FILES
## TEST INPUT/OUPTUT FOR COMPARISON, THESE FILES SHOULD BE IN THIS DIRECTORY
##        exonAnnotFileName = 'Annotation_ConservedElement_Exons_hg18.txt'
##        intronAnnotFileName = 'Annotation_ConservedElement_Introns_hg18.txt'
##        stopAnnotFileName = 'Annotation_ConservedElement_Stop_hg18.txt'
## testDir = os.path.join(testOutputBaseDir, 'TEST_' + ''.join(tmpList)) SHOULD
## BE DELETED IF YOU WANT TO RUN IN '.'

# DIRECTIONARY FOR DOC STRING OF SEQDB
docStringDict = {
    'anoCar1': 'Lizard Genome (January 2007)',
    'bosTau3': 'Cow Genome (August 2006)',
    'canFam2': 'Dog Genome (May 2005)',
    'cavPor2': 'Guinea Pig (October 2005)',
    'danRer4': 'Zebrafish Genome (March 2006)',
    'dasNov1': 'Armadillo Genome (May 2005)',
    'echTel1': 'Tenrec Genome (July 2005)',
    'eriEur1': 'European Hedgehog (Junuary 2006)',
    'equCab1': 'Horse Genome (January 2007)',
    'felCat3': 'Cat Genome (March 2006)',
    'fr2': 'Fugu Genome (October 2004)',
    'galGal3': 'Chicken Genome (May 2006)',
    'gasAcu1': 'Stickleback Genome (February 2006)',
    'hg18': 'Human Genome (May 2006)',
    'loxAfr1': 'Elephant Genome (May 2005)',
    'mm8': 'Mouse Genome (March 2006)',
    'monDom4': 'Opossum Genome (January 2006)',
    'ornAna1': 'Platypus Genome (March 2007)',
    'oryCun1': 'Rabbit Genome (May 2005)',
    'oryLat1': 'Medaka Genome (April 2006)',
    'otoGar1': 'Bushbaby Genome (December 2006)',
    'panTro2': 'Chimpanzee Genome (March 2006)',
    'rheMac2': 'Rhesus Genome (January 2006)',
    'rn4': 'Rat Genome (November 2004)',
    'sorAra1': 'Shrew (Junuary 2006)',
    'tetNig1': 'Tetraodon Genome (February 2004)',
    'tupBel1': 'Tree Shrew (December 2006)',
    'xenTro2': 'X. tropicalis Genome (August 2005)',
    }

# GENOME ASSEMBLY LIST FOR DM2 MULTIZ15WAY
msaSpeciesList = ['anoCar1', 'bosTau3', 'canFam2', 'cavPor2', 'danRer4',
                  'dasNov1', 'echTel1', 'equCab1', 'eriEur1', 'felCat3', 'fr2',
                  'galGal3', 'gasAcu1', 'hg18', 'loxAfr1', 'mm8', 'monDom4',
                  'ornAna1', 'oryCun1', 'oryLat1', 'otoGar1', 'panTro2',
                  'rheMac2', 'rn4', 'sorAra1', 'tetNig1', 'tupBel1', 'xenTro2']


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

    def test_collectionannot(self):
        'Test building an AnnotationDB from file'
        from pygr import seqdb, cnestedlist, sqlgraph
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS
        exon_slices = Collection(
            filename=os.path.join(self.path, 'refGene_exonAnnot_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        exon_db = seqdb.AnnotationDB(exon_slices, hg18,
                                     sliceAttrDict=dict(id=0, exon_id=1,
                                                        orientation=2,
                                                        gene_id=3, start=4,
                                                        stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_exonAnnot_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_exonAnnot%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            exon_slices[row[1]] = row
            exon = exon_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(exon) # SAVE IT TO GENOME MAPPING
        exon_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        exon_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        exon_db.__doc__ = 'Exon Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.hg18.exons', exon_db)
        msa.__doc__ = 'NLMSA Exon for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.hg18.exons', msa)
        exon_schema = pygr.Data.ManyToManyRelation(hg18, exon_db,
                                                   bindAttrs=('exon1', ))
        exon_schema.__doc__ = 'Exon Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.hg18.exons', exon_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ SPLICES
        splice_slices = Collection(
            filename=os.path.join(self.path, 'refGene_spliceAnnot_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        splice_db = seqdb.AnnotationDB(splice_slices, hg18,
                                       sliceAttrDict=dict(id=0, splice_id=1,
                                                          orientation=2,
                                                          gene_id=3, start=4,
                                                          stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_spliceAnnot_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_spliceAnnot%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            splice_slices[row[1]] = row
            # GET THE ANNOTATION OBJECT FOR THIS EXON
            splice = splice_db[row[1]]
            msa.addAnnotation(splice) # SAVE IT TO GENOME MAPPING
        splice_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        splice_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        splice_db.__doc__ = 'Splice Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.hg18.splices', splice_db)
        msa.__doc__ = 'NLMSA Splice for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.hg18.splices', msa)
        splice_schema = pygr.Data.ManyToManyRelation(hg18, splice_db,
                                                     bindAttrs=('splice1', ))
        splice_schema.__doc__ = 'Splice Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.hg18.splices',
                            splice_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS
        cds_slices = Collection(
            filename=os.path.join(self.path, 'refGene_cdsAnnot_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        cds_db = seqdb.AnnotationDB(cds_slices, hg18,
                                    sliceAttrDict=dict(id=0, cds_id=1,
                                                       orientation=2,
                                                       gene_id=3, start=4,
                                                       stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_cdsAnnot_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'refGene_cdsAnnot%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            cds_slices[row[1]] = row
            cds = cds_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(cds) # SAVE IT TO GENOME MAPPING
        cds_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        cds_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        cds_db.__doc__ = 'CDS Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.hg18.cdss', cds_db)
        msa.__doc__ = 'NLMSA CDS for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.hg18.cdss', msa)
        cds_schema = pygr.Data.ManyToManyRelation(hg18, cds_db,
                                                  bindAttrs=('cds1', ))
        cds_schema.__doc__ = 'CDS Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.hg18.cdss', cds_schema)
        # BUILD ANNOTATION DATABASE FOR MOST CONSERVED ELEMENTS FROM UCSC
        ucsc_slices = Collection(
           filename=os.path.join(self.path, 'phastConsElements28way_hg18.cdb'),
            intKeys=True, mode='cr', writeback=False)
        ucsc_db = seqdb.AnnotationDB(ucsc_slices, hg18,
                                     sliceAttrDict=dict(id=0, ucsc_id=1,
                                                        orientation=2,
                                                        gene_id=3, start=4,
                                                        stop=5))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'phastConsElements28way_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir,
                                       'phastConsElements28way%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            ucsc_slices[row[1]] = row
            ucsc = ucsc_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(ucsc) # SAVE IT TO GENOME MAPPING
        ucsc_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        ucsc_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        ucsc_db.__doc__ = 'Most Conserved Elements for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.hg18.mostconserved',
                              ucsc_db)
        msa.__doc__ = 'NLMSA for Most Conserved Elements for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.NLMSA.hg18.mostconserved',
                              msa)
        ucsc_schema = pygr.Data.ManyToManyRelation(hg18, ucsc_db,
                                                   bindAttrs=('element1', ))
        ucsc_schema.__doc__ = \
                'Schema for UCSC Most Conserved Elements for hg18'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.hg18.mostconserved',
                            ucsc_schema)
        # BUILD ANNOTATION DATABASE FOR SNP126 FROM UCSC
        snp_slices = Collection(filename=os.path.join(self.path,
                                                      'snp126_hg18.cdb'),
                                intKeys=True, protocol=2, mode='cr',
                                writeback=False)
        snp_db = seqdb.AnnotationDB(snp_slices, hg18,
                                    sliceAttrDict=dict(id=0, snp_id=1,
                                                       orientation=2,
                                                       gene_id=3, start=4,
                                                       stop=5, score=6,
                                                       ref_NCBI=7, ref_UCSC=8,
                                                       observed=9, molType=10,
                                                       myClass=11, myValid=12,
                                                       avHet=13, avHetSE=14,
                                                       myFunc=15, locType=16,
                                                       myWeight=17))
        msa = cnestedlist.NLMSA(os.path.join(self.path, 'snp126_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for lines in open(os.path.join(testInputDir, 'snp126%s_hg18.txt'
                                       % smallSamplePostfix),
                          'r').xreadlines():
            row = [x for x in lines.split('\t')] # CONVERT TO LIST SO MUTABLE
            row[1] = int(row[1]) # CONVERT FROM STRING TO INTEGER
            snp_slices[row[1]] = row
            snp = snp_db[row[1]] # GET THE ANNOTATION OBJECT FOR THIS EXON
            msa.addAnnotation(snp) # SAVE IT TO GENOME MAPPING
        snp_db.clear_cache() # not really necessary; cache should autoGC
        # SHELVE SHOULD BE EXPLICITLY CLOSED IN ORDER TO SAVE CURRENT CONTENTS
        snp_slices.close()
        msa.build() # FINALIZE GENOME ALIGNMENT INDEXES
        snp_db.__doc__ = 'SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.hg18.snp126', snp_db)
        msa.__doc__ = 'NLMSA for SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.NLMSA.hg18.snp126', msa)
        snp_schema = pygr.Data.ManyToManyRelation(hg18, snp_db,
                                                  bindAttrs=('snp1', ))
        snp_schema.__doc__ = 'Schema for UCSC SNP126 for hg18'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.hg18.snp126',
                            snp_schema)
        pygr.Data.save()
        pygr.Data.clear_cache()

        # QUERY TO EXON AND SPLICES ANNOTATION DATABASE
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        exonmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.hg18.exons')
        splicemsa = pygr.Data.getResource('TEST.Annotation.NLMSA.hg18.splices')
        conservedmsa = \
         pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.hg18.mostconserved')
        snpmsa = \
                pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.hg18.snp126')
        cdsmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.hg18.cdss')
        exons = pygr.Data.getResource('TEST.Annotation.hg18.exons')
        splices = pygr.Data.getResource('TEST.Annotation.hg18.splices')
        mostconserved = \
               pygr.Data.getResource('TEST.Annotation.UCSC.hg18.mostconserved')
        snp126 = pygr.Data.getResource('TEST.Annotation.UCSC.hg18.snp126')
        cdss = pygr.Data.getResource('TEST.Annotation.hg18.cdss')

        # OPEN hg18_MULTIZ28WAY NLMSA
        msa = cnestedlist.NLMSA(os.path.join(msaDir, 'hg18_multiz28way'), 'r',
                                trypath=[seqDir])

        exonAnnotFileName = os.path.join(testInputDir,
                                 'Annotation_ConservedElement_Exons%s_hg18.txt'
                                         % smallSamplePostfix)
        intronAnnotFileName = os.path.join(testInputDir,
                               'Annotation_ConservedElement_Introns%s_hg18.txt'
                                           % smallSamplePostfix)
        stopAnnotFileName = os.path.join(testInputDir,
                                  'Annotation_ConservedElement_Stop%s_hg18.txt'
                                         % smallSamplePostfix)
        newexonAnnotFileName = os.path.join(self.path, 'new_Exons_hg18.txt')
        newintronAnnotFileName = os.path.join(self.path,
                                              'new_Introns_hg18.txt')
        newstopAnnotFileName = os.path.join(self.path, 'new_stop_hg18.txt')
        tmpexonAnnotFileName = self.copyFile(exonAnnotFileName)
        tmpintronAnnotFileName = self.copyFile(intronAnnotFileName)
        tmpstopAnnotFileName = self.copyFile(stopAnnotFileName)

        if smallSampleKey:
            chrList = [smallSampleKey]
        else:
            chrList = hg18.seqLenDict.keys()
            chrList.sort()

        outfile = open(newexonAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # EXON ANNOTATION DATABASE
            try:
                ex1 = exonmsa[slice]
            except:
                continue
            else:
                exlist1 = [(ix.exon_id, ix) for ix in ex1.keys()]
                exlist1.sort()
                for ixx, exon in exlist1:
                    saveList = []
                    tmp = exon.sequence
                    tmpexon = exons[exon.exon_id]
                    tmpslice = tmpexon.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'EXON', chrid, tmpexon.exon_id, tmpexon.gene_id, \
                            tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpexonAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newexonAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newintronAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # SPLICE ANNOTATION DATABASE
            try:
                sp1 = splicemsa[slice]
            except:
                continue
            else:
                splist1 = [(ix.splice_id, ix) for ix in sp1.keys()]
                splist1.sort()
                for ixx, splice in splist1:
                    saveList = []
                    tmp = splice.sequence
                    tmpsplice = splices[splice.splice_id]
                    tmpslice = tmpsplice.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'INTRON', chrid, tmpsplice.splice_id, \
                            tmpsplice.gene_id, tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
                    # SNP IN SPLICE SITES
                    saveList = []
                    gt = tmpslice[:2]
                    ag = tmpslice[-2:]
                    try:
                        gtout = snpmsa[gt]
                        agout = snpmsa[ag]
                    except KeyError:
                        pass
                    else:
                        gtlist = gtout.keys()
                        aglist = agout.keys()
                        for snp in gtlist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP5', chrid, tmpsplice.gene_id,
                                      gt.start, gt.stop, str(gt)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(gt.start):\
                                                                abs(gt.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        for snp in aglist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP3', chrid, tmpsplice.gene_id,
                                      ag.start, ag.stop, str(ag)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(ag.start):\
                                                                abs(ag.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpintronAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newintronAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newstopAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # STOP ANNOTATION DATABASE
            try:
                cds1 = cdsmsa[slice]
            except:
                continue
            else:
                cdslist1 = [(ix.cds_id, ix) for ix in cds1.keys()]
                cdslist1.sort()
                for ixx, cds in cdslist1:
                    saveList = []
                    tmp = cds.sequence
                    tmpcds = cdss[cds.cds_id]
                    tmpslice = tmpcds.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'STOP', chrid, tmpcds.cds_id, tmpcds.gene_id, \
                            tmpslice.start, tmpslice.stop
                    if tmpslice.start < 0:
                        stopstart, stopend = -tmpslice.stop, -tmpslice.start
                        stop = -hg18[chrid][stopstart:stopstart+3]
                    else:
                        stopstart, stopend = tmpslice.start, tmpslice.stop
                        stop = hg18[chrid][stopend-3:stopend]
                    if str(stop).upper() not in ('TAA', 'TAG', 'TGA'):
                        continue
                    try:
                        snp1 = snpmsa[stop]
                    except KeyError:
                        pass
                    else:
                        snplist = [(ix.snp_id, ix) for ix in snp1.keys()]
                        snplist.sort()
                        for iyy, snp in snplist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = wlist1 + (str(stop), stop.start,
                                               stop.stop) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            if tmpslice.start < 0:
                                tmp1 = -msa.seqDict['hg18.' + chrid]\
                                        [stopstart:stopstart + 3]
                            else:
                                tmp1 = msa.seqDict['hg18.' + chrid]\
                                        [stopend - 3:stopend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 3 or \
                                   dest.stop - dest.start != 3:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                if str(dest).upper() not in ('TAA', 'TAG',
                                                             'TGA'):
                                    nonstr = 'NONSENSE'
                                else:
                                    nonstr = 'STOP'
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident,
                                                   nonstr)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpstopAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newstopAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

    def test_mysqlannot(self):
        'Test building an AnnotationDB from MySQL'
        from pygr import seqdb, cnestedlist, sqlgraph
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS: MYSQL VERSION
        exon_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_exonAnnot%s_hg18' % (testInputDB,
                                                  smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        exon_db = seqdb.AnnotationDB(exon_slices, hg18,
                                     sliceAttrDict=dict(id='chromosome',
                                                        gene_id='name',
                                                        exon_id='exon_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_exonAnnot_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in exon_db:
            msa.addAnnotation(exon_db[id])
        exon_db.clear_cache() # not really necessary; cache should autoGC
        exon_slices.clear_cache()
        msa.build()
        exon_db.__doc__ = 'SQL Exon Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.SQL.hg18.exons', exon_db)
        msa.__doc__ = 'SQL NLMSA Exon for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.hg18.exons', msa)
        exon_schema = pygr.Data.ManyToManyRelation(hg18, exon_db,
                                                   bindAttrs=('exon2', ))
        exon_schema.__doc__ = 'SQL Exon Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.hg18.exons',
                            exon_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ SPLICES: MYSQL VERSION
        splice_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_spliceAnnot%s_hg18' % (testInputDB,
                                                    smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        splice_db = seqdb.AnnotationDB(splice_slices, hg18,
                                       sliceAttrDict=dict(id='chromosome',
                                                          gene_id='name',
                                                        splice_id='splice_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_spliceAnnot_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in splice_db:
            msa.addAnnotation(splice_db[id])
        splice_db.clear_cache() # not really necessary; cache should autoGC
        splice_slices.clear_cache()
        msa.build()
        splice_db.__doc__ = 'SQL Splice Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.SQL.hg18.splices', splice_db)
        msa.__doc__ = 'SQL NLMSA Splice for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.hg18.splices', msa)
        splice_schema = pygr.Data.ManyToManyRelation(hg18, splice_db,
                                                     bindAttrs=('splice2', ))
        splice_schema.__doc__ = 'SQL Splice Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.hg18.splices',
                            splice_schema)
        # BUILD ANNOTATION DATABASE FOR REFSEQ EXONS: MYSQL VERSION
        cds_slices = sqlgraph.SQLTableClustered(
            '%s.pygr_refGene_cdsAnnot%s_hg18' % (testInputDB,
                                                 smallSamplePostfix),
            clusterKey='chromosome', maxCache=0)
        cds_db = seqdb.AnnotationDB(cds_slices, hg18,
                                    sliceAttrDict=dict(id='chromosome',
                                                       gene_id='name',
                                                       cds_id='cds_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                             'refGene_cdsAnnot_SQL_hg18'), 'w',
                                pairwiseMode=True, bidirectional=False)
        for id in cds_db:
            msa.addAnnotation(cds_db[id])
        cds_db.clear_cache() # not really necessary; cache should autoGC
        cds_slices.clear_cache()
        msa.build()
        cds_db.__doc__ = 'SQL CDS Annotation Database for hg18'
        pygr.Data.addResource('TEST.Annotation.SQL.hg18.cdss', cds_db)
        msa.__doc__ = 'SQL NLMSA CDS for hg18'
        pygr.Data.addResource('TEST.Annotation.NLMSA.SQL.hg18.cdss', msa)
        cds_schema = pygr.Data.ManyToManyRelation(hg18, cds_db,
                                                  bindAttrs=('cds2', ))
        cds_schema.__doc__ = 'SQL CDS Schema for hg18'
        pygr.Data.addSchema('TEST.Annotation.NLMSA.SQL.hg18.cdss', cds_schema)
        # BUILD ANNOTATION DATABASE FOR MOST CONSERVED ELEMENTS FROM UCSC:
        # MYSQL VERSION
        ucsc_slices = \
             sqlgraph.SQLTableClustered('%s.pygr_phastConsElements28way%s_hg18'
                                        % (testInputDB, smallSamplePostfix),
                                        clusterKey='chromosome', maxCache=0)
        ucsc_db = seqdb.AnnotationDB(ucsc_slices, hg18,
                                     sliceAttrDict=dict(id='chromosome',
                                                        gene_id='name',
                                                        ucsc_id='ucsc_id'))
        msa = cnestedlist.NLMSA(os.path.join(self.path,
                                            'phastConsElements28way_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in ucsc_db:
            msa.addAnnotation(ucsc_db[id])
        ucsc_db.clear_cache() # not really necessary; cache should autoGC
        ucsc_slices.clear_cache()
        msa.build()
        ucsc_db.__doc__ = 'SQL Most Conserved Elements for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.SQL.hg18.mostconserved',
                              ucsc_db)
        msa.__doc__ = 'SQL NLMSA for Most Conserved Elements for hg18'
        pygr.Data.addResource(
            'TEST.Annotation.UCSC.NLMSA.SQL.hg18.mostconserved', msa)
        ucsc_schema = pygr.Data.ManyToManyRelation(hg18, ucsc_db,
                                                   bindAttrs=('element2', ))
        ucsc_schema.__doc__ = \
                'SQL Schema for UCSC Most Conserved Elements for hg18'
        pygr.Data.addSchema(
            'TEST.Annotation.UCSC.NLMSA.SQL.hg18.mostconserved', ucsc_schema)
        # BUILD ANNOTATION DATABASE FOR SNP126 FROM UCSC: MYSQL VERSION
        snp_slices = sqlgraph.SQLTableClustered('%s.pygr_snp126%s_hg18'
                                                % (testInputDB,
                                                   smallSamplePostfix),
                                                clusterKey='clusterKey',
                                                maxCache=0)
        snp_db = seqdb.AnnotationDB(snp_slices, hg18,
                                    sliceAttrDict=dict(id='chromosome',
                                                       gene_id='name',
                                                       snp_id='snp_id',
                                                       score='score',
                                                       ref_NCBI='ref_NCBI',
                                                       ref_UCSC='ref_UCSC',
                                                       observed='observed',
                                                       molType='molType',
                                                       myClass='myClass',
                                                       myValid='myValid',
                                                       avHet='avHet',
                                                       avHetSE='avHetSE',
                                                       myFunc='myFunc',
                                                       locType='locType',
                                                       myWeight='myWeight'))
        msa = cnestedlist.NLMSA(os.path.join(self.path, 'snp126_SQL_hg18'),
                                'w', pairwiseMode=True, bidirectional=False)
        for id in snp_db:
            msa.addAnnotation(snp_db[id])
        snp_db.clear_cache() # not really necessary; cache should autoGC
        snp_slices.clear_cache()
        msa.build()
        snp_db.__doc__ = 'SQL SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.SQL.hg18.snp126', snp_db)
        msa.__doc__ = 'SQL NLMSA for SNP126 for hg18'
        pygr.Data.addResource('TEST.Annotation.UCSC.NLMSA.SQL.hg18.snp126',
                              msa)
        snp_schema = pygr.Data.ManyToManyRelation(hg18, snp_db,
                                                  bindAttrs=('snp2', ))
        snp_schema.__doc__ = 'SQL Schema for UCSC SNP126 for hg18'
        pygr.Data.addSchema('TEST.Annotation.UCSC.NLMSA.SQL.hg18.snp126',
                            snp_schema)
        pygr.Data.save()
        pygr.Data.clear_cache()

        # QUERY TO EXON AND SPLICES ANNOTATION DATABASE
        hg18 = pygr.Data.getResource('TEST.Seq.Genome.hg18')
        exonmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.hg18.exons')
        splicemsa = \
                pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.hg18.splices')
        conservedmsa = \
     pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.SQL.hg18.mostconserved')
        snpmsa = \
            pygr.Data.getResource('TEST.Annotation.UCSC.NLMSA.SQL.hg18.snp126')
        cdsmsa = pygr.Data.getResource('TEST.Annotation.NLMSA.SQL.hg18.cdss')
        exons = pygr.Data.getResource('TEST.Annotation.SQL.hg18.exons')
        splices = pygr.Data.getResource('TEST.Annotation.SQL.hg18.splices')
        mostconserved = \
           pygr.Data.getResource('TEST.Annotation.UCSC.SQL.hg18.mostconserved')
        snp126 = pygr.Data.getResource('TEST.Annotation.UCSC.SQL.hg18.snp126')
        cdss = pygr.Data.getResource('TEST.Annotation.SQL.hg18.cdss')

        # OPEN hg18_MULTIZ28WAY NLMSA
        msa = cnestedlist.NLMSA(os.path.join(msaDir, 'hg18_multiz28way'), 'r',
                                trypath=[seqDir])

        exonAnnotFileName = os.path.join(testInputDir,
                                 'Annotation_ConservedElement_Exons%s_hg18.txt'
                                         % smallSamplePostfix)
        intronAnnotFileName = os.path.join(testInputDir,
                               'Annotation_ConservedElement_Introns%s_hg18.txt'
                                           % smallSamplePostfix)
        stopAnnotFileName = os.path.join(testInputDir,
                                  'Annotation_ConservedElement_Stop%s_hg18.txt'
                                         % smallSamplePostfix)
        newexonAnnotFileName = os.path.join(self.path, 'new_Exons_hg18.txt')
        newintronAnnotFileName = os.path.join(self.path,
                                              'new_Introns_hg18.txt')
        newstopAnnotFileName = os.path.join(self.path, 'new_stop_hg18.txt')
        tmpexonAnnotFileName = self.copyFile(exonAnnotFileName)
        tmpintronAnnotFileName = self.copyFile(intronAnnotFileName)
        tmpstopAnnotFileName = self.copyFile(stopAnnotFileName)

        if smallSampleKey:
            chrList = [smallSampleKey]
        else:
            chrList = hg18.seqLenDict.keys()
            chrList.sort()

        outfile = open(newexonAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # EXON ANNOTATION DATABASE
            try:
                ex1 = exonmsa[slice]
            except:
                continue
            else:
                exlist1 = [(ix.exon_id, ix) for ix in ex1.keys()]
                exlist1.sort()
                for ixx, exon in exlist1:
                    saveList = []
                    tmp = exon.sequence
                    tmpexon = exons[exon.exon_id]
                    tmpslice = tmpexon.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'EXON', chrid, tmpexon.exon_id, tmpexon.gene_id, \
                            tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpexonAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newexonAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newintronAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # SPLICE ANNOTATION DATABASE
            try:
                sp1 = splicemsa[slice]
            except:
                continue
            else:
                splist1 = [(ix.splice_id, ix) for ix in sp1.keys()]
                splist1.sort()
                for ixx, splice in splist1:
                    saveList = []
                    tmp = splice.sequence
                    tmpsplice = splices[splice.splice_id]
                    tmpslice = tmpsplice.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'INTRON', chrid, tmpsplice.splice_id, \
                            tmpsplice.gene_id, tmpslice.start, tmpslice.stop
                    try:
                        out1 = conservedmsa[tmp]
                    except KeyError:
                        pass
                    else:
                        elementlist = [(ix.ucsc_id, ix) for ix in out1.keys()]
                        elementlist.sort()
                        for iyy, element in elementlist:
                            if element.stop - element.start < 100:
                                continue
                            score = int(string.split(element.gene_id, '=')[1])
                            if score < 100:
                                continue
                            tmp2 = element.sequence
                            tmpelement = mostconserved[element.ucsc_id]
                            # FOR REAL ELEMENT COORDINATE
                            tmpslice2 = tmpelement.sequence
                            wlist2 = wlist1 + (tmpelement.ucsc_id,
                                               tmpelement.gene_id,
                                               tmpslice2.start,
                                               tmpslice2.stop)
                            slicestart, sliceend = max(tmp.start, tmp2.start),\
                                    min(tmp.stop, tmp2.stop)
                            if slicestart < 0 or sliceend < 0:
                                sys.exit('wrong query')
                            tmp1 = msa.seqDict['hg18.' + chrid][slicestart:
                                                                sliceend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start < 100:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                if palign < 0.8 or pident < 0.8:
                                    continue
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
                    # SNP IN SPLICE SITES
                    saveList = []
                    gt = tmpslice[:2]
                    ag = tmpslice[-2:]
                    try:
                        gtout = snpmsa[gt]
                        agout = snpmsa[ag]
                    except KeyError:
                        pass
                    else:
                        gtlist = gtout.keys()
                        aglist = agout.keys()
                        for snp in gtlist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP5', chrid, tmpsplice.gene_id,
                                      gt.start, gt.stop, str(gt)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(gt.start):
                                                                abs(gt.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        for snp in aglist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = ('SNP3', chrid, tmpsplice.gene_id,
                                      ag.start, ag.stop, str(ag)) + \
                                    (annsnp.snp_id, tmpsnp.start, tmpsnp.stop,
                                     str(tmpsnp), annsnp.gene_id,
                                     annsnp.ref_NCBI, annsnp.ref_UCSC,
                                     annsnp.observed, annsnp.molType,
                                     annsnp.myClass, annsnp.myValid)
                            tmp1 = msa.seqDict['hg18.' + chrid][abs(ag.start):
                                                                abs(ag.stop)]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 2 or \
                                   dest.stop - dest.start != 2:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, \
                                        '%.2f' % pident
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpintronAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newintronAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()

        outfile = open(newstopAnnotFileName, 'w')
        for chrid in chrList:
            slice = hg18[chrid]
            # STOP ANNOTATION DATABASE
            try:
                cds1 = cdsmsa[slice]
            except:
                continue
            else:
                cdslist1 = [(ix.cds_id, ix) for ix in cds1.keys()]
                cdslist1.sort()
                for ixx, cds in cdslist1:
                    saveList = []
                    tmp = cds.sequence
                    tmpcds = cdss[cds.cds_id]
                    tmpslice = tmpcds.sequence # FOR REAL EXON COORDINATE
                    wlist1 = 'STOP', chrid, tmpcds.cds_id, tmpcds.gene_id, \
                            tmpslice.start, tmpslice.stop
                    if tmpslice.start < 0:
                        stopstart, stopend = -tmpslice.stop, -tmpslice.start
                        stop = -hg18[chrid][stopstart:stopstart+3]
                    else:
                        stopstart, stopend = tmpslice.start, tmpslice.stop
                        stop = hg18[chrid][stopend-3:stopend]
                    if str(stop).upper() not in ('TAA', 'TAG', 'TGA'):
                        continue
                    try:
                        snp1 = snpmsa[stop]
                    except KeyError:
                        pass
                    else:
                        snplist = [(ix.snp_id, ix) for ix in snp1.keys()]
                        snplist.sort()
                        for iyy, snp in snplist:
                            tmpsnp = snp.sequence
                            annsnp = snp126[snp.snp_id]
                            wlist2 = wlist1 + (str(stop), stop.start,
                                               stop.stop) + (annsnp.snp_id,
                                                             tmpsnp.start,
                                                             tmpsnp.stop,
                                                             str(tmpsnp),
                                                             annsnp.gene_id,
                                                             annsnp.ref_NCBI,
                                                             annsnp.ref_UCSC,
                                                             annsnp.observed,
                                                             annsnp.molType,
                                                             annsnp.myClass,
                                                             annsnp.myValid)
                            if tmpslice.start < 0:
                                tmp1 = -msa.seqDict['hg18.' + chrid]\
                                        [stopstart:stopstart + 3]
                            else:
                                tmp1 = msa.seqDict['hg18.' + chrid]\
                                        [stopend - 3:stopend]
                            edges = msa[tmp1].edges()
                            for src, dest, e in edges:
                                if src.stop - src.start != 3 or \
                                   dest.stop - dest.start != 3:
                                    continue
                                palign, pident = e.pAligned(), e.pIdentity()
                                palign, pident = '%.2f' % palign, '%.2f' \
                                        % pident
                                if str(dest).upper() not in ('TAA', 'TAG',
                                                             'TGA'):
                                    nonstr = 'NONSENSE'
                                else:
                                    nonstr = 'STOP'
                                wlist3 = wlist2 + ((~msa.seqDict)[src],
                                                   str(src), src.start,
                                                   src.stop,
                                                   (~msa.seqDict)[dest],
                                                   str(dest), dest.start,
                                                   dest.stop, palign, pident,
                                                   nonstr)
                                saveList.append('\t'.join(map(str, wlist3))
                                                + '\n')
                        saveList.sort()
                        for saveline in saveList:
                            outfile.write(saveline)
        outfile.close()
        md5old = hashlib.md5()
        md5old.update(open(tmpstopAnnotFileName, 'r').read())
        md5new = hashlib.md5()
        md5new.update(open(newstopAnnotFileName, 'r').read())
        assert md5old.digest() == md5new.digest()


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
