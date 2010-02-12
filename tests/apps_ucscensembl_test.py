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
        mrna = trans_db[trans_id]
        self.assertEqual(repr(mrna), 'annotENST00000000233[0:3295]')
        self.assertEqual(repr(mrna.sequence), 'chr7[127015694:127018989]')
        self.assertEqual(repr(mrna.mrna_sequence), 'ENST00000000233[0:1037]')

    def test_genedb(self):
        gene_id = 'ENSG00000000003'
        gene_id_multitrans = 'ENSG00000168958'
        gene_db = self.iface.gene_db
        gene = gene_db[gene_id]
        self.assertEqual(repr(gene), 'annotENSG00000000003[0:8000]')
        self.assertEqual(repr(gene.sequence), '-chrX[99770450:99778450]')
        self.assertEqual(repr(gene_db[gene_id_multitrans]),
                         'annotENSG00000168958[0:32595]')

    def test_proteindb(self):
        prot_id = 'ENSP00000372525'
        prot_db = self.iface.prot_db
        prot = prot_db[prot_id]
        self.assertEqual(repr(prot), 'ENSP00000372525')
        self.assertEqual(repr(prot.sequence), 'ENSP00000372525[0:801]')

    def test_exondb(self):
        exon_id = 'ENSE00000720378'
        exon_db = self.iface.exon_db
        exon = exon_db[exon_id]
        self.assertEqual(repr(exon), 'annotENSE00000720378[0:110]')
        self.assertEqual(repr(exon.sequence), 'chr7[127016774:127016884]')
        self.assertEqual(len(exon_db), 297956)

    def test_snp(self):
        snp130 = self.iface.get_annot_db('snp130')
        snp = snp130['rs58108140']
        self.assertEqual(snp.name, 'rs58108140')
        self.assertEqual(repr(snp.sequence), 'chr1[582:583]')
        self.assertEqual(snp.refUCSC, 'G')
        self.assertEqual(snp.observed, 'A/G')


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
