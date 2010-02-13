import unittest
from testlib import testutil, PygrTestProgram

from pygr.apps.ucsc_ensembl_annot import UCSCEnsemblInterface


class UCSCEnsembl_Test(unittest.TestCase):

    def setUp(self):
        self.iface = UCSCEnsemblInterface('Bio.Seq.Genome.HUMAN.hg18')

    def test_nonexistent(self):
        'Test trying to use a genome with no Ensembl data at UCSC'
        badname = 'Nonexistent.Fake.Bogus'
        try:
            badiface = UCSCEnsemblInterface(badname)
        except KeyError:
            return
        raise ValueError("Bad sequence name %s has failed to return an error" %
                         badname)

    def test_transcriptdb(self):
        'Test interfacing with the transcript annotation database'
        trans_db = self.iface.trans_db
        mrna = trans_db['ENST00000000233']
        self.assertEqual(repr(mrna), 'annotENST00000000233[0:3295]')
        self.assertEqual(repr(mrna.sequence), 'chr7[127015694:127018989]')
        self.assertEqual(repr(mrna.mrna_sequence), 'ENST00000000233[0:1037]')

    def test_genedb(self):
        'Test interfacing with the gene annotation database'
        gene_db = self.iface.gene_db
        gene = gene_db['ENSG00000000003']
        self.assertEqual(repr(gene), 'annotENSG00000000003[0:8000]')
        self.assertEqual(repr(gene.sequence), '-chrX[99770450:99778450]')
        self.assertEqual(repr(gene_db['ENSG00000168958']),
                         'annotENSG00000168958[0:32595]')

    def test_proteindb(self):
        'Test interfacing with the protein peptide-sequence database'
        prot_db = self.iface.prot_db
        prot = prot_db['ENSP00000372525']
        self.assertEqual(repr(prot), 'ENSP00000372525')
        self.assertEqual(repr(prot.sequence), 'ENSP00000372525[0:801]')

    def test_exondb(self):
        'Test interfacing with the exon annotation database'
        exon_db = self.iface.exon_db
        exon = exon_db['ENSE00000720378']
        self.assertEqual(repr(exon), 'annotENSE00000720378[0:110]')
        self.assertEqual(repr(exon.sequence), 'chr7[127016774:127016884]')
        self.assertEqual(len(exon_db), 297956)

    def test_snp(self):
        'Test interfacing with an SNP annotation database'
        snp130 = self.iface.get_annot_db('snp130')
        snp = snp130['rs58108140']
        self.assertEqual(snp.name, 'rs58108140')
        self.assertEqual(repr(snp.sequence), 'chr1[582:583]')
        self.assertEqual(snp.refUCSC, 'G')
        self.assertEqual(snp.observed, 'A/G')

    def test_maps(self):
        'Test mapping between different databases'
        mrna = self.iface.trans_db['ENST00000000233']
        gene = self.iface.gene_db['ENSG00000168958']
        prot = self.iface.prot_db['ENSP00000372525']
        exon = self.iface.exon_db['ENSE00000720378']
        trans_of_prot = self.iface.protein_transcript_id_map[prot]
        self.assertEqual(repr(trans_of_prot.id), "'ENST00000383052'")
        prot_of_mrna = (~self.iface.protein_transcript_id_map)[mrna]
        self.assertEqual(repr(prot_of_mrna.id), "'ENSP00000000233'")
        trans_of_gene = self.iface.transcripts_in_genes_map[gene].keys()
        self.assertEqual(repr(trans_of_gene),
                         '''[annotENST00000353339[0:32595], \
annotENST00000409565[0:32541], annotENST00000409616[0:31890], \
annotENST00000354503[0:32560], annotENST00000349901[0:32560], \
annotENST00000337110[0:32560], annotENST00000304593[0:32560], \
annotENST00000392059[0:30316], annotENST00000392058[0:28082]]''')
        gene_of_mrna = (~self.iface.transcripts_in_genes_map)[mrna].keys()
        self.assertEqual(repr(gene_of_mrna), '[annotENSG00000004059[0:3295]]')
        trans_of_exon = self.iface.ens_transcripts_of_exons_map[exon].keys()
        self.assertEqual(repr(trans_of_exon), '[annotENST00000000233[0:3295]]')
        exons_of_mrna = self.iface.ens_exons_in_transcripts_map[mrna].keys()
        self.assertEqual(repr(exons_of_mrna),
                         '''[annotENSE00001123404[0:161], \
annotENSE00000720374[0:81], annotENSE00000720378[0:110], \
annotENSE00000720381[0:72], annotENSE00000720384[0:126], \
annotENSE00000882271[0:487]]''')


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
