
DNA_SEQTYPE=0
RNA_SEQTYPE=1
PROTEIN_SEQTYPE=2

def guess_seqtype(s):
    dna_letters='AaTtUuGgCcNn'
    ndna=0
    nU=0
    nT=0
    for l in s:
        if l in dna_letters:
            ndna += 1
        if l=='U' or l=='u':
            nU += 1
        elif l=='T' or l=='t':
            nT += 1
    ratio=ndna/float(len(s))
    if ratio>0.85:
        if nT>nU:
            return DNA_SEQTYPE
        else:
            return RNA_SEQTYPE
    else:
        return PROTEIN_SEQTYPE

