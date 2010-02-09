import unittest
from testlib import testutil, PygrTestProgram

from pygr.apps.ucsc_ensembl_annot import UCSCEnsemblInterface


class UCSCEnsembl_Test(unittest.TestCase):

    def setUp(self):
        self.iface = UCSCEnsemblInterface('Bio.Seq.Genome.HUMAN.hg18')

    def test_transcriptdb(self):
        trans_db = self.iface.trans_db
        print '\nExample transcript annotation:'
        mrna = trans_db['ENST00000000233']
        print 'ENST00000000233', repr(mrna), \
                repr(mrna.sequence), repr(mrna.mrna_sequence)

    def test_genedb(self):
        gene_db = self.iface.gene_db
        print '\nExample gene annotation:'
        print 'ENSG00000000003', repr(gene_db['ENSG00000000003']), \
                repr(gene_db['ENSG00000000003'].sequence)
        print 'ENSG00000168958', repr(gene_db['ENSG00000168958'])

    def test_proteindb(self):
        prot_db = self.iface.prot_db
        print '\nExample protein sequence:'
        prot = prot_db['ENSP00000372525']
        print 'ENSP00000372525', repr(prot), repr(prot.sequence)

    def test_exondb(self):
        exon_db = self.iface.exon_db
        print '\nExample exon annotation:'
        print 'ENSE00000720378', repr(exon_db['ENSE00000720378']), \
                repr(exon_db['ENSE00000720378'].sequence)
        print 'total exons:', len(exon_db)

    def test_snp(self):
        snp130 = self.iface.get_annot_db('snp130')
        snp = snp130['rs58108140']
        print '\nSNP:',snp.name, repr(snp.sequence), snp.refUCSC, snp.observed


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
