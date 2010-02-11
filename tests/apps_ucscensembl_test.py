import unittest
from testlib import testutil, PygrTestProgram

from pygr.apps.ucsc_ensembl_annot import UCSCEnsemblInterface


class UCSCEnsembl_Test(unittest.TestCase):

    def setUp(self):
        self.iface = UCSCEnsemblInterface('Bio.Seq.Genome.HUMAN.hg18')

    def test_nonexistent(self):
        badname = 'Nonexistent.Fake.Bogus'
        try:
            badiface = UCSCEnsemblInterface(badname)
        except KeyError:
            return
        raise ValueError("Bad sequence name %s has failed to return an error" %
                         badname)

    def test_transcriptdb(self):
        trans_id = 'ENST00000000233'
        trans_db = self.iface.trans_db
        print '\nExample transcript annotation:'
        mrna = trans_db[trans_id]
        print trans_id, repr(mrna), repr(mrna.sequence), \
                repr(mrna.mrna_sequence)

    def test_genedb(self):
        gene_id = 'ENSG00000000003'
        gene_id_multitrans = 'ENSG00000168958'
        gene_db = self.iface.gene_db
        print '\nExample gene annotation:'
        print gene_id, repr(gene_db[gene_id]), repr(gene_db[gene_id].sequence)
        print gene_id_multitrans, repr(gene_db[gene_id_multitrans])

    def test_proteindb(self):
        prot_id = 'ENSP00000372525'
        prot_db = self.iface.prot_db
        print '\nExample protein sequence:'
        prot = prot_db[prot_id]
        print prot_id, repr(prot), repr(prot.sequence)

    def test_exondb(self):
        exon_id = 'ENSE00000720378'
        exon_db = self.iface.exon_db
        print '\nExample exon annotation:'
        print exon_id, repr(exon_db[exon_id]), repr(exon_db[exon_id].sequence)
        print 'total exons:', len(exon_db)

    def test_snp(self):
        snp130 = self.iface.get_annot_db('snp130')
        snp = snp130['rs58108140']
        print '\nSNP:',snp.name, repr(snp.sequence), snp.refUCSC, snp.observed


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
