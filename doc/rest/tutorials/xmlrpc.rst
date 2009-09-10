.. highlightlang:: python

.. XMLRPC Tutorial documentation master file, created by
   sphinx-quickstart on Thu Aug 13 13:53:05 2009.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.


===================================================
Making Data Available via XMLRPC or for Downloading
===================================================

Contents:

.. toctree::
   :maxdepth: 2

Purpose
-------

The purpose of this tutorial is to familiarize the user with Pygr's
resource-sharing service, commonly referred to as XMLRPC, after the
name of the protocol used by the service.  You will learn how to
establish a Pygr XMLRPC server and populate it with different types of
data, as well as how to take advantage of such servers and their
resources in your code.

Overview
--------

Often it is not practical to keep all one's data on the local
workstation. One reason for avoiding this could be the potentially large
size of :class:`seqdb.SequenceFileDB` and
:class:`cnestedlist.NLMSA` data (for example, about 400 GB of drive
space is needed to store the UCSC 44-way alignments);
another could be trying to maintain central storage of data rather
than keeping separate copies on multiple machines. Whatever the
reason, Pygr offers an elegant and efficient alternative:
resources can be shared over the network with no significant loss of
performance, using XMLRPC.  Moreover, in addition to providing remote
access to data, Pygr XMLRPC servers can also be used as a
resource-distribution system. In this mode, one can access
downloadable resources and fetch them to the local system with a
single line of Python code.

At present, Pygr XMLRPC offers full support for providing its sequence
(e.g. :class:`seqdb.SequenceFileDB`) and alignment
(:class:`cnestedlist.NLMSA`) objects. Annotation
(:class:`annotation.AnnotationDB`) objects can also be shared, however
they cannot yet be made available for downloading.

Also note that Pygr XMLRPC servers offer their resources in
*read-only* mode. Support for write mode is planned in a future
release of Pygr.

This tutorial will give you a glimpse of all the features offers by
the Pygr XMLRPC service, along with some working examples.


Sharing Resources via XMLRPC
----------------------------

Let us assume the user has already created a bunch of
:class:`seqdb.SequenceFileDB` and/or :class:`cnestedlist.NLMSA`
objects and committed them to a local metabase (FIXME: link?) under
the :data:`Bio` prefix , located in :data:`/my/resource/path` and
added to :data:`WORLDBASEPATH`. The recommended (as well as the
easiest) way of publishing such resources via XMLRPC is to open the
relevant metabase, load all the relevant resources into memory, then
start the resource server with the :data:`withIndex=True` option. A
few other options must be passed to the server's constructor: the base
of the log file name (:data:`worldbase-server` in following example,
resulting in a file named :data:`worldbase-server.log`) and the TCP port
number (the default port is :data:`port=5000`) for it to serve on. The
:data:`host` keyword is optional; the server defaults to serving on
the public server name, and you can use :data:`host=''` to serve on
all network interfaces including :data:`localhost`.
Finally, executing :meth:`server.serve_forever()`
will start your XMLRPC server::

    from pygr import metabase

    # open metabase from /my/resource/path
    mdb = metabase.MetabaseList('/my/resource/path')

    # open all 'Bio' resources to share
    for ix in mdb.dir('Bio'): mdb(ix)

    # create a XMLRPC server.
    # metabase path for this server is http://localhost:5000/
    server = metabase.ResourceServer(mdb, 'worldbase-server.log', withIndex=True, host='')
    # start a XMLRPC server
    server.serve_forever(daemonize=True)

The example above launches an XMLRPC server as a daemon: it detaches
itself from the Python interpreter shortly after start-up and will
continue running after you exit the interpreter. Should you for some
reason prefer to interact with a running server, you can launch it in
the foreground::

    server.serve_forever(daemonize=False)

Of course running in this mode means the server will die with the
Python interpreter that's spawned it.  To keep it running long-term,
use an external terminal manager such as :data:`screen`.

You can find more information in `XMLRPC Resource Server (FIXME: ReST
link!)
<http://www.doe-mbi.ucla.edu/~leec/newpygrdocs/reference/metabase.html#xmlrpc-resource-server>`_.


Publishing :class:`seqdb.SequenceFileDB` & :class:`cnestedlist.NLMSA` Data for Downloading
------------------------------------------------------------------------------------------

The download mode of Pygr XMLRPC works by publishing
appropriately-crafted links to resources downloadable using FTP or
HTTP. The first thing you will need here will therefore be
a list of FTP or HTTP links to the relevant data files: for example,
the :data:`bosTau4` genome can be downloaded via FTP `from UCSC
<ftp://hgdownload.cse.ucsc.edu/goldenPath/bosTau4/bigZips/bosTau4.fa.gz>`_. The
Pygr team provides more than three hundred pre-calculated NLMSA text
files for most of the pairwise and multigenome alignments available
from the `UCSC genome browser <http://genome.ucsc.edu>`_ on a
dedicated server: `http://biodb.bioinformatics.ucla.edu/PYGRDATA
<http://biodb.bioinformatics.ucla.edu/PYGRDATA>`_; one can
also publish one's own sequence and/or alignment resources as
necessary.

In the examples below we shall show how to publish both sequence (the
aforementioned :data:`bosTau4` genome) and alignment
(:data:`bosTau4_multiz4way`, from
`http://biodb.bioinformatics.ucla.edu/PYGRDATA/canFam2_multiz4way.txt.gz
<http://biodb.bioinformatics.ucla.edu/PYGRDATA/canFam2_multiz4way.txt.gz>`_)
data. Note that in order to make NLMSA data available for downloading one
needs to convert binary objects used by Pygr into text files using the
function by :func:`cnestedlist.dump_textfile`; we also recommend that you
compress the resulting text file using e.g. :data:`gzip`. Once the text
file is downloaded Pygr will automatically convert it into a
binary format. More information on the subject of NLMSA format
conversion can be found in the NLMSA reference guide: `dump_textfile,
textfile_to_binaries (FIXME: ReST link!)
<http://www.doe-mbi.ucla.edu/~leec/newpygrdocs/reference/cnestedlist.html#dump-textfile-textfile-to-binaries>`_.

There are two very important things to keep in mind while preparing
downloadable resources. To begin with, respective resource IDs
(:data:`Bio.Seq.Genome.COW.bosTau4` and
:data:`Bio.MSA.UCSC.bosTau4_multiz4way` in this example) of your
downloadable resources should be exactly the same as of their shared
counterparts. Secondly, a separate, dedicated resource repository
should be prepared for downloadable resources (in this example it is
in :data:`/my/downloadable/path`).

The following code populates the metabase with a downloadable
sequence-data resource::

    from pygr import seqdb, metabase
    from pygr.downloader import SourceURL, GenericBuilder

    mdb = metabase.MetabaseList('/my/downloadable/path')
    newurl = 'ftp://hgdownload.cse.ucsc.edu/goldenPath/bosTau4/bigZips/bosTau4.fa.gz'
    filename = os.path.basename(newurl)
    filename = filename[-3:]	# remove '.gz'

    src = SourceURL(newurl, filename=genoname + mytype, singleFile=True)
    # .fasta for SourceURL
    src.__doc__ = 'bosTau4 FASTA File'
    mdb.add_resource('Bio.Seq.Genome.COW.' + genoname + '.fasta', src)
    rsrc = GenericBuilder('SequenceFileDB', src)
    # downloadable resource should have same resource ID as XMLRPC resource
    rsrc.__doc__ = 'bosTau4 downloadable genome'
    mdb.add_resource('Bio.Seq.Genome.COW.' + genoname, rsrc)
    mdb.commit()


For downloadable NLMSAs, you have to use :class:`NLMSABuilder` instead
of :class:`GenericBuilder`::

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

Note that :data:`__doc__` attribute is mandatory for all resources to
be added to :data:`metabase/worldbase`.

Once the metabase in question has been populated with downloadable
resources, the resource server's constructor should be instructed of
its location with the *downloadDB* keyword. Pygr will then
automatically register all the available resources: ::

    server = metabase.ResourceServer(mdb, 'biodb2_5000', withIndex=True, \
        port=5000, host='biodb2.bioinformatics.ucla.edu', \
        downloadDB='/my/downloadable/path/.pygr_data')
    server.serve_forever()

Note that you have to specifically reference ``.pygr_data`` in
:data:`/my/downloadable/path`

.. @CTB why? why not do an isdir?

Client Use
----------

By default, Pygr will open :data:`WORLDBASEPATH` as
``.,http://biodb2.bioinformatics.ucla.edu:5000/``; biodb2 is a public
XMLRPC server operated by the Pygr team, containing over three hundred
data sets, including genomes as well as pairwise and multigenome
alignment resources. In order to save your pygr objects including
downloadable resources, you have to have at least one `writable`
directory in :data:`WORLDBASEPATH`. If more than one writable location
is present :data:`WORLDBASEPATH` the first one listed will be used for
registering obtained data. Moreover, Pygr will search all the
locations before dumping the downloadable resources, and then generate
:class:`seqdb.SequenceFileDB` and :class:`cnestedlist.NLMSA` (FIXME:
what does this mean?)

The following commands can be used to list all available via XMLRPC::

    import os
    # WORLDBASEPATH: '.,http://biodb2.bioinformatics.ucla.edu:5000'
    # WORLDBASEPATH has one writable location: '.', current directory
    os.environ['WORLDBASEPATH'] = '.,http://biodb2.bioinformatics.ucla.edu:5000'

    from pygr import metabase
    mdb = metabase.MetabaseList()

    print mdb.dir() # Print all XMLRPC resources
    print mdb.dir(download=True) # Print all downloadable resources

If you want to `use` :data:`bosTau4` genome and
:data:`bosTau4_multiz4way` NLMSA::

    bosTau4 = mdb('Bio.Seq.Genome.COW.bosTau4')
    bosTau4_multiz4way = mdb('Bio.MSA.UCSC.bosTau4_multiz4way')

If you want to `download` :data:`bosTau4` genome and
:data:`bosTau4_multiz4way` NLMSA::

    bosTau4 = mdb('Bio.Seq.Genome.COW.bosTau4', download=True)
    bosTau4_multiz4way = mdb('Bio.MSA.UCSC.bosTau4_multiz4way', download=True)

By default all files are downloaded to your current working directory,
it is also where binary NLMSA files are built. Should you want to
store any of these elsewhere you can use two environment variables:

* ``WORLDBASEDOWNLOAD`` to point at the destination for downloading;
* ``WORLDBASEBUILDDIR`` for where binary NLMSA will be saved.

Check `downloader - Remote data retrieval (FIXME: ReST link!) <http://www.doe-mbi.ucla.edu/~leec/newpygrdocs/reference/downloader.html>`_ for more details.


Examples
--------

All of the code examples are available at `biodb2_update branch
<http://github.com/deepreds/pygr/tree/biodb2_update>`_,
:data:`tests/biodb2_update` directory.

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
