==========================================
Interfacing with Ensembl Databases at UCSC
==========================================

Purpose
^^^^^^^

The purpose of this tutorial is to show the users how to use Pygr to access
Ensembl data at the UCSC genome database.


Overview
^^^^^^^^

The module :mod:`apps.ucsc_ensembl_annot` provides Pygr with an inferface for
Ensembl data (transcript, gene and exon annotations as well as protein peptide
sequences) available from the UCSC database. It serves all the data in the form
of standard Pygr objects and provides mappings between transcripts, genes,
proteins and exons.

.. note::

    Due to the way Ensembl exon data is stored in the UCSC database - namely,
    exons only appear in that database as start-stop coordinates associated
    with transcripts, with no ID information - certain exon-related operations
    still communicate directly with Ensembl. This should happen transparently
    to the user, as should communication with the UCSC database as a matter
    of fact.


Getting Started
^^^^^^^^^^^^^^^

All the UCSC-Ensembl functionality is contained within the
:class:`UCSCEnsemblInterface` class of the module. To begin with, initialise
an interface object using the worldbase name of the genome of your choice:

.. doctest::

>>> from pygr.apps.ucsc_ensembl_annot import UCSCEnsemblInterface
>>> iface = UCSCEnsemblInterface('Bio.Seq.Genome.HUMAN.hg18')

An exception will be raised if the specified genome does not exist in
worldbase or doesn't have Ensembl data in the UCSC database.

It is possible to simultaneously use multiple :class:`UCSCEnsemblInterface`
objects.


Accessing the Databases
^^^^^^^^^^^^^^^^^^^^^^^

To obtain an :class:`annotation.AnnotationDB` of transcripts, call

.. doctest::

>>> trans_db = iface.trans_db

Keys of this database follow the standard Ensembl convention for stable
transcript idenitifiers, 'ENSTxxxxxxxxxxx'. For instance:

.. doctest::

>>> mrna = trans_db['ENST00000000233']

One difference between UCSC-Ensembl transcript annotations and standard Pygr
annotations is the presence of an additional sequence attribute,
:attr:`mrna_sequence`. Whereas the standard :attr:`sequence` attribute returns
a string representation of the whole transcript (i.e. containing both exons
and introns), :attr:`mrna_sequence` is a concatenation of exon sequences only.

.. doctest::

>>> mrna.sequence
chr7[127015694:127018989]
>>> mrna.mrna_sequence
ENST00000000233[0:1037]

To obtain an :class:`annotation.AnnotationDB` of genes, call

.. doctest::

>>> gene_db = iface.gene_db

Keys of this database follow the standard Ensembl convention for stable
gene idenitifiers, 'ENSGxxxxxxxxxxx'. For instance:

.. doctest::

>>> gene = gene_db['ENSG00000168958']

Annotations in this database possess two special attributes, :attr:`minTxStart`
and :attr:`maxTxEnd`. These return extreme coordinates of the coding region.
In case of genes corresponding to single transcripts in the Ensembl database,
these are of course equal to :attr:`start` (:attr:`txStart`) and :attr:`stop`
(:attr:`txEnd`), respectively.


To obtain an :class:`annotation.AnnotationDB` of exons, call

.. doctest::

>>> exon_db = iface.exon_db

Keys of this database follow the standard Ensembl convention for stable
exon idenitifiers, 'ENSExxxxxxxxxxx'. For instance:

.. doctest::

>>> exon = exon_db['ENSE00000720378']


To obtain an object (an :class:`sqlgraph.SQLTable` object, to be precise)
representing protein peptide sequences, call

.. doctest::

>>> prot_db = iface.prot_db

Keys of this database follow the standard Ensembl convention for stable
proten idenitifiers, 'ENSPxxxxxxxxxxx'. For instance:

.. doctest::

>>> prot = prot_db['ENSP00000372525']

The peptide sequences are then available through the standard sequence attribute

.. doctest::

>>> str(prot.sequence)[:50]
'MDEDEFELQPQEPNSFFDGIGADATHMDGDQIVVEIQEAVFVSNIVDSDI'


Mappings
^^^^^^^^

In addition to the databases themselves :class:`UCSCEnsemblInterface` provides mappings
between their objects.

To obtain the transcript associated in Ensembl with a particular protein or
vice versa, use the map *protein_transcript_id_map*,
an :class:`sqlgraph.MapView` object:

.. doctest::

>>> trans_of_prot = iface.protein_transcript_id_map[prot]
>>> trans.of_prot.id
'ENST00000383052'
>>> prot_of_mrna = (~iface.protein_transcript_id_map)[mrna]
>>> prot_of_mrna.id
'ENSP00000000233'


The map *transcripts_in_genes_map*, an :class:`sqlgraph.GraphView` object,
allows one to obtain a list of transcripts associated in Ensembl with
a particular gene, or the gene associated with a particular transcript.
In the both cases the map returns a dictionary whose keys are appropriate
transcript/gene objects.

.. doctest::

>>> trans_of_gene = iface.transcripts_in_genes_map[gene].keys()
>>> trans_of_gene
[annotENST00000353339[0:32595], annotENST00000409565[0:32541], annotENST00000409616[0:31890], annotENST00000354503[0:32560], annotENST00000349901[0:32560], annotENST00000337110[0:32560], annotENST00000304593[0:32560], annotENST00000392059[0:30316], annotENST00000392058[0:28082]]
>>> gene_of_mrna = (~iface.transcripts_in_genes_map)[mrna].keys()
>>> gene_of_mrna
[annotENSG00000004059[0:3295]]


Finally, the maps *ens_transcripts_of_exons_map* and
*ens_exons_in_transcripts_map*, both :class:`sqlgraph.GraphView` objects,
provide mapping between exons in transcripts. Note that as both of these
relations are of the many-to-many type, these two maps are not invertible.

The first map allows one to see in what transcripts a particular exon appears:

.. doctest::

>>> trans_of_exon = iface.ens_transcripts_of_exons_map[exon].keys()
>>> trans_of_exon
[annotENST00000000233[0:3295]]

The second does the opposite and has a special property of having its output
explicitly ordered, by `rank` as defined by Ensembl:

.. doctest::

>>> exons_of_mrna = iface.ens_exons_in_transcripts_map[mrna].keys()
>>> exons_of_mrna
[annotENSE00001123404[0:161], annotENSE00000720374[0:81], annotENSE00000720378[0:110], annotENSE00000720381[0:72], annotENSE00000720384[0:126], annotENSE00000882271[0:487]]


