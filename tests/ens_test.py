from pygr.apps.ucsc_ensembl_annot import UCSCEnsemblInterface


factory = UCSCEnsemblInterface('Bio.Seq.Genome.HUMAN.hg18')

#
# Transcript annotations
#
trans_db = factory.transcript_database()
print '\nExample transcript annotation:'
mrna = trans_db['ENST00000000233']
print 'ENST00000000233', repr(mrna), \
        repr(mrna.sequence), repr(mrna.mrna_sequence)

#
# Gene annotations
#
gene_db = factory.gene_database()
print '\nExample gene annotation:'
print 'ENSG00000000003', repr(gene_db['ENSG00000000003']), \
        repr(gene_db['ENSG00000000003'].sequence)
print 'ENSG00000168958', repr(gene_db['ENSG00000168958'])

#
# Protein annotations
#
prot_db = factory.protein_database()
print '\nExample protein annotation:'
print 'ENSP00000372525', repr(prot_db['ENSP00000372525'])

#
# Exon annotations
#
exon_db = factory.exon_database()
print '\nExample exon annotation:'
print 'ENSE00000720378', repr(exon_db['ENSE00000720378']), \
        repr(exon_db['ENSE00000720378'].sequence)

