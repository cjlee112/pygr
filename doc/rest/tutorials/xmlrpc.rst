.. highlightlang:: python

.. XMLRPC Tutorial documentation master file, created by
   sphinx-quickstart on Thu Aug 13 13:53:05 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


Welcome to Pygr XMLRPC Tutorial's documentation!
================================================

Contents:

.. toctree::
   :maxdepth: 2

Introduction
------------

Often times, the size of the :func:`seqdb.SequenceFileDB` and :func:`cnestedlist.NLMSA` is too big to have in your servers. For example, we need about 400GB if we want to keep hg18 referenced MAF multiz44way alignments. In this case, pygr offers a very efficient way of sharing resources over XMLRPC without losing any significant loss of performance.
Other than giving a direct access via XMLRPC, pygr XMLRPC can be a resource distribution system. One can access the pygrdownloadable resources via XMLRPC and download all regarding resources just by one python line. This tutorial will give a glimpse of all XMLRPC features.

Let's assume user has pygr resource repository and registered a bunch of :func:`seqdb.SequenceFileDB` and :func:`cnestedlist.NLMSA`.

There are two paths used in this tutorial, :data:`/my/resource/path` as :data:`WORLDBASEPATH` for writing all XMLRPC resources and :data:`/my/downloadable/path` for saving downloadable resources. Downloadable resources should be written in other path because unpickling (by accessing resources via XMLRPC) will initiate instant downloading of resources.

Sharing :func:`seqdb.SequenceFileDB` & :func:`cnestedlist.NLMSA` via XMLRPC
---------------------------------------------------------------------------

Assume that you have your :data:`Bio` resources in :data:`/my/resource/path`. You can open your :data:`metabase` first and then open all the resources. By :data:`withIndex=True` option, pygr will collect all open resources and start your XMLRPC server. You need to choose log file name (:data:`biodb2_5000` in following example) and port number (:data:`5000` default). :data:`server.serve_forever()` will start your XMLRPC server::

    from pygr import metabase

    # open metabase from /my/resource/path
    mdb = metabase.MetabaseList('/my/resource/path')

    # open all 'Bio' resources to share
    for ix in mdb.dir('Bio'): mdb(ix)

    # create a XMLRPC server.
    # metabase path for this server is http://biodb2.bioinformatics.ucla.edu:5000
    # log file 'biodb2_5000.log' will be created in current directory
    server = metabase.ResourceServer(mdb, 'biodb2_5000', withIndex=True, port=5000, \
        host='biodb2.bioinformatics.ucla.edu')
    # start a XMLRPC server, running as a daemon, non-interactive Python process
    server.serve_forever()

:func:`annotation.AnnotationDB` can be served via XMLRPC, but not for downloadable resource because it is hardly bound to :func:`Collection`, :func:`SQLTable` or :func:`SQLTableClustered`.

Above example demonstrates standalone Pygr XMLRPC server, but you can interact with XMLRPC without running as a daemon::

    server.serve_forever(demonize=False)

By default, :data:`demonize=True`. If :data:`demonize=False`, note that XMLRPC server will stop working if you exit from interactive python prompt. You can have more information in `XMLRPC Resource Server <http://www.doe-mbi.ucla.edu/~leec/newpygrdocs/reference/metabase.html#xmlrpc-resource-server>`_.


Downloading :func:`seqdb.SequenceFileDB` & :func:`cnestedlist.NLMSA` via XMLRPC
-------------------------------------------------------------------------------

First thing is to get a list of resource URLs (FTP or HTTP). For example you can download :data:`bosTau4` genome via FTP, `ftp://hgdownload.cse.ucsc.edu/goldenPath/bosTau4/bigZips/bosTau4.fa.gz <ftp://hgdownload.cse.ucsc.edu/goldenPath/bosTau4/bigZips/bosTau4.fa.gz>`_. We provide with more than three hundreds pre-calculated NLMSA text filess for most of the pairwise and multigenome alignments available in `UCSC genome browser <http://genome.ucsc.edu>`_, `http://biodb.bioinformatics.ucla.edu/PYGRDATA <http://biodb.bioinformatics.ucla.edu/PYGRDATA>`_. Of course, you can make your NLMSA and share on the web for your downloadable resources. Let's pick one of them, :data:`bosTau4_multiz4way`, in `http://biodb.bioinformatics.ucla.edu/PYGRDATA/canFam2_multiz4way.txt.gz <http://biodb.bioinformatics.ucla.edu/PYGRDATA/canFam2_multiz4way.txt.gz>`_.

If you want to create your own downloadable NLMSA, you have to convert NLMSA into text files by :func:`cnestedlist.dump_textfile` function, and then compress by :data:`gzip`. You can have more information on NLMSA binary <-> text conversion here, `dump_textfile, textfile_to_binaries <http://www.doe-mbi.ucla.edu/~leec/newpygrdocs/reference/cnestedlist.html#dump-textfile-textfile-to-binaries>`_.

There are two very important things. First, your resource ID (:data:`Bio.Seq.Genome.COW.bosTau4` in this example) should be same as your downloadable resources. Second, you have to prepare another resource repository for downloadable resources. In this example, :data:`/my/downlodable/path`::

    from pygr import seqdb, metabase
    from pygr.downloader import SourceURL, GenericBuilder

    mdb = metabase.MetabaseList('/my/downloadable/path')
    newurl = 'ftp://hgdownload.cse.ucsc.edu/goldenPath/bosTau4/bigZips/bosTau4.fa.gz'
    filename = os.path.basename(newurl)
    if '.tar.gz' in filename: mytype = '.tar.gz'
    elif '.gz' in filename: mytype = '.gz'
    elif '.tgz' in filename: mytype = '.tar.gz'
    elif '.zip' in filename: mytype = '.zip'
    else:
        continue
    genoname = filename.replace(mytype, '') # bosTau4

    if mytype != '.gz': # pass singleFile=True option for .gz file (not .tar.gz)
        src = SourceURL(newurl, filename=genoname + mytype, singleFile=True)
    else:
        src = SourceURL(newurl, filename=genoname + mytype)
    # .fasta for SourceURL
    src.__doc__ = 'bosTau4 FASTA File'
    mdb.add_resource('Bio.Seq.Genome.COW.' + genoname + '.fasta', src)
    rsrc = GenericBuilder('BlastDB', src)
    # downloadable resource should have same resource ID as XMLRPC resource
    rsrc.__doc__ = 'bosTau4 downloadable genome'
    mdb.add_resource('Bio.Seq.Genome.COW.' + genoname, rsrc)
    mdb.commit()


For downloadable NLMSA, you have to use :func:`NLMSABuilder` instead of :func:`GenericBuilder`::

    from pygr import seqdb, metabase
    from pygr.downloader import SourceURL
    from pygr.nlmsa_utils import NLMSABuilder

    # mdb1 for XMLRPC resource
    mdb1 = metabase.MetabaseList(worldbasepath)
    # mdb2 for downloadable metabase
    mdb2 = metabase.MetabaseList(downloadablepath)

    genoname = 'bosTau4_multiz4way'
    pygrname = 'Bio.MSA.UCSC.bosTau4_multiz4way'
    srcUrl = 'http://biodb.bioinformatics.ucla.edu/PYGRDATA'

    newurl = '%s/%s.txt.gz' % (srcUrl, genoname)
    dfile = SourceURL(newurl)
    # .txt for NLMSA SourceURL
    dfile.__doc__ = genoname + '.txt in textfile dump format'
    mdb2.add_resource(pygrname + '.txt', dfile)
    nbuilder = NLMSABuilder(dfile)
    # downloadable resource should have same resource ID as XMLRPC resource
    nbuilder.__doc__ = genoname + ' multigenome alignment from UCSC genome browser'
    mdb2.add_resource(pygrname, nbuilder)
    mdb2.commit()

Note that :data:`__doc__` attribute is mandatory for all resources to be added to :data:`metabase/worldbase`.


Starting XMLRPC Server
----------------------

If you have downloadable resources in your XMLRPC server, you need to add :func:`downloadDB`. Pygr will register automatically all the downloadable resources::

    server = metabase.ResourceServer(mdb, 'biodb2_5000', withIndex=True, \
        port=5000, host='biodb2.bioinformatics.ucla.edu', \
        downloadDB='/my/downloadable/path/.pygr_data')
    server.serve_forever()

Note that you have to point out ``.pygr_data`` in :data:`/my/downloadable/path`


How to use
----------

By default, pygr will open :data:`WORLDBASEPATH` as ``.,http://biodb2.bioinformatics.ucla.edu:5000``. In order to save your pygr objects including downloadable resources, you have to have at least one `writable` directory in :data:`WORLDBASEPATH`. If you have more than one writable location in your :data:`WORLDBASEPATH`, it will search all the locations before dumping downloadable resources, and then generate :func:`seqdb.SequenceFileDB` and :func:`cnestedlist.NLMSA`. And, the resources will be written in your ``first`` writable location.

There are over three hundreds XMLRPC resources (genomes, pairwise and multigenome alignments) available at :data:`http://biodb2.bioinformatics.ucla.edu:5000`. See following example::

    import os
    # WORLDBASEPATH: '.,http://biodb2.bioinformatics.ucla.edu:5000'
    # WORLDBASEPATH has one writable location: '.', current directory
    os.environ['WORLDBASEPATH'] = '.,http://biodb2.bioinformatics.ucla.edu:5000'

    from pygr import metabase
    mdb = metabase.MetabaseList()

    print mdb.dir() # Print all XMLRPC resources
    print mdb.dir(download=True) # Print all downloadable resources


If you want to `use` :data:`bosTau4` genome and :data:`bosTau4_multiz4way` NLMSA::

    bosTau4 = mdb('Bio.Seq.Genome.COW.bosTau4')
    bosTau4_multiz4way = mdb('Bio.MSA.UCSC.bosTau4_multiz4way')

If you want to `download` :data:`bosTau4` genome and :data:`bosTau4_multiz4way` NLMSA::

    bosTau4 = mdb('Bio.Seq.Genome.COW.bosTau4', download=True)
    bosTau4_multiz4way = mdb('Bio.MSA.UCSC.bosTau4_multiz4way', downlad=True)

It will download :data:`bosTau4` and :data:`bosTau4_multiz4way` in your ``.`` directory.

If you want to save or build the downloadable resources to another directory, you have to set two environmental variables, ``WORLDBASEDOWNLOAD`` for downloading directory and ``WORLDBASEBUILDDIR`` for NLMSA building. Check `downloader - Remote data retrieval <http://www.doe-mbi.ucla.edu/~leec/newpygrdocs/reference/downloader.html>`_ for more details.



Examples
--------

All of the code examples are available at `biodb2_update branch <http://github.com/deepreds/pygr/tree/biodb2_update>`_, :data:`tests/biodb2_update` directory.



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`



