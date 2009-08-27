:mod:`downloader` --- Remote data retrieval
===========================================

.. module:: downloader
   :synopsis: Remote data retrieval.
.. moduleauthor:: Christopher Lee <leec@chem.ucla.edu>
.. sectionauthor:: Christopher Lee <leec@chem.ucla.edu>

The downloader module supports automatic download of resources,
primarily for worldbase.  It consists of several pieces:

* :class:`SourceURL`: use this class to create a picklable reference
  to a resource that can be downloaded from a specific URL.
  
* download_unpickler: Unpickling the
  SourceURL object (e.g. when it is retrieved from worldbase) will trigger
  downloading of the resource from this URL, as a local file.  That means
  that the unpickled form of the SourceURL is simply the local filename
  where the resource is now stored.
  
* unzip, gunzip, untar support: If the downloaded resource
  is a zip archive, a gzip compressed file, or a tar archive (possibly
  with compression), it will by default be uncompressed / extracted.
  Currently, the following file suffixes are recognized automatically:
  ``.gz`` (gunzip); ``.zip`` (unzip); ``.tar``,
  ``.tar.gz``, ``.tar.bz2`` or ``.tgz`` (extract tar
  archive, with uncompression if appropriate).


SourceURL
---------
This class exists solely to be saved in worldbase (or any other
pickle-based persistence storage) so that unpickling the object
will trigger automatic download of a desired URL.

.. class:: SourceURL(path, filename=None, **kwargs)

   *path* must be a URL to a downloadable file.

   *filename*, if given, will be used as the local filename
   to save the file as.  A resource should be given a local
   filename that uniquely identifies this resource (e.g. "hg17"
   instead of "chromFa" as is often used by UCSC genome packages).
   Without a unique filename, there is no way to guarantee that
   name collisions will not occur, potentially over-writing other
   local resource files.

   Additional *kwargs* are simply passed on to the download
   unpickler.  Currently, the only useful option is *singleFile=True*,
   which forces extraction of a multi-file archive (zip or tar) to
   be concatenated into a single file (useful for a genome sequence
   database stored as a zip archive of multiple FASTA files, one for
   each chromosome).


Here is an example of saving a downloadable file reference to
worldbase::

   dfile = downloader.SourceURL('http://biodb.bioinformatics.ucla.edu/PYGRDATA/dm2_multiz9way.txt.gz')
   dfile.__doc__ = 'DM2 based nine genome alignment from UCSC in textfile dump format'
   worldbase.Bio.MSA.UCSC.dm2_multiz9way.txt = dfile # SAVE AS RESOURCE NAME
   nbuilder = NLMSABuilder(dfile) # will make NLMSA from this when unpickled
   nbuilder.__doc__ = 'DM2 based nine genome alignment from UCSC'
   worldbase.Bio.MSA.UCSC.dm2_multiz9way = nbuilder
   worldbase.commit()


When this object is retrieved from worldbase, that will trigger
construction of the binary indexes (in a location that can be
controlled by the PYGRDATABUILDDIR environment variable).  The product
of the unpickling will simply be a properly initialized NLMSA object
using these index files. i.e.::

   nlmsa = worldbase.Bio.MSA.UCSC.dm2_multiz9way(download=True) # get the download


NLMSABuilder
------------
This class is defined in the module :mod:`nlmsa_utils`, but its
sole purpose is to support auto-download of NLMSA alignments.
When unpickled, it triggers unpacking of NLMSA binary index files
from a NLMSA textdump file (usually provided using a :class:`SourceURL`
object).  For a usage example, see the previous section immediately
above.

.. class:: NLMSABuilder(filepath, **kwargs)

   *filepath* should be a :class:`SourceURL` object.  When an NLMSABuilder
   object is pickled, it saves its filepath in the pickle.  When
   the NLMSABuilder is unpickled, the filepath object is also unpickled,
   which will trigger downloading of the :class:`SourceURL` file,
   which in turn will be used by the nlmsa_textdump_unpickler
   to extract the binary index files for the NLMSA.  The final product
   of unpickling an NLMSABuilder object is simply the fully initialized
   NLMSA object that it constructed.

   *kwargs* can be any keyword arguments understood by the
   textdump_to_binaries() function (see :mod:`cnestedlist` module
   documentation for details).


GenericBuilder
--------------

.. class:: GenericBuilder(classname, *args, **kwargs)

   *classname* should be a string specifying the name of
   the class to be used for building the resource when this
   object is unpickled by worldbase.  As a security precaution,
   this class name is checked against the unpickler's list of
   allowed target classes.  Currently, the only
   allowed target class is 'BlastDB'.

   To build the target resource upon unpickling, the
   target class is simply called with the exact same list
   of arguments and keyword arguments (less the initial *classname*
   argument) as originally supplied to :class:`GenericBuilder`.


Environment Variables Controlling Downloads
-------------------------------------------
Two environment variables control where downloaded files will be
stored:

* ``PYGRDATADOWNLOAD``: sets the directory where files will
  be downloaded to.  If it is not set, files are downloaded to the current
  directory.
  
* ``PYGRDATABUILDDIR``: sets the directory where indexes will
  be saved in subsequent steps that may occur after download of
  a resource, e.g. NLMSA index files.  If not set, indexes will be
  saved in the current directory.


Performance and Platform Independence Issues
--------------------------------------------
Uncompression and archive extraction depend on tools such gunzip,
which create performance vs. platform-independence issues, as
summarized here:

* Python provides platform-independent modules :mod:`tarfile`,
  :mod:`gzip`, :mod:`zipfile`, so Pygr uses these, with the following
  caveats.
  
* The Python module :mod:`gzip` appears to be about half the
  speed of the command line program ``gunzip`` on UNIX.  Therefore,
  Pygr attempts first to run the ``gunzip`` program if available; if
  not, it uses the :mod:`gzip` module.
  
* The Python module :mod:`zipfile` only provides an interface
  to read an entire file from the archive into memory (!), which is
  impractical for very large datasets.  Instead, we just want to extract
  each archive file directly to disk.  We therefore use the UNIX
  program ``unzip`` to do this.  If that fails, we try using
  the :mod:`zipfile` module.

