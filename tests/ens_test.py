from pygr.apps.ucsc_ensembl_annot import UCSCEnsemblInterface


factory = UCSCEnsemblInterface('Bio.Seq.Genome.HUMAN.hg18')

#
# Transcript annotations
#
trans_db = factory.trans_db
print '\nExample transcript annotation:'
mrna = trans_db['ENST00000000233']
print 'ENST00000000233', repr(mrna), \
        repr(mrna.sequence), repr(mrna.mrna_sequence)

#
# Gene annotations
#
gene_db = factory.gene_db
print '\nExample gene annotation:'
print 'ENSG00000000003', repr(gene_db['ENSG00000000003']), \
        repr(gene_db['ENSG00000000003'].sequence)
print 'ENSG00000168958', repr(gene_db['ENSG00000168958'])

#
# Protein annotations
#
prot_db = factory.prot_db
print '\nExample protein annotation:'
prot = prot_db['ENSP00000372525']
print 'ENSP00000372525', repr(prot), repr(prot.sequence)

#
# Exon annotations
#
exon_db = factory.exon_db
print '\nExample exon annotation:'
print 'ENSE00000720378', repr(exon_db['ENSE00000720378']), \
        repr(exon_db['ENSE00000720378'].sequence)

print 'total exons:', len(exon_db)

snp130 = factory.get_annot_db('snp130')
snp = list(snp130.query('WHERE name=%s', ('rs58108140',)))[0]
print '\nSNP:',snp.id, repr(snp.sequence), snp.refUCSC, snp.observed

ival = factory.genome_seq['chr1'][10000:11000]
snps = list(snp130.query_interval(ival))
print '\nquery:', repr(ival), len(snps), 'snps'
snp = snps[0]
print '\nSNP:',snp.id, repr(snp.sequence), snp.refUCSC, snp.observed

it = iter(snp130)
s = it.next()
snp = snp130[s]
print '\nFirst SNP:',snp.id, repr(snp.sequence), snp.refUCSC, snp.observed
