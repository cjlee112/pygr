Pygr README
===========

Introduction
------------

Pygr is an open source software project used to develop graph database 
interfaces for the popular Python language, with a strong emphasis 
on bioinformatics applications ranging from genome-wide analysis of 
alternative splicing patterns, to comparative genomics queries of 
multi-genome alignment data.

For more information see

http://pygr.org

Latest Release
--------------

http://code.google.com/p/pygr/downloads/list

Documentation
-------------

This distribution includes the full Pygr documentation source,
but you will need the Sphinx documentation tool to build the
formatted docs.  You can get Sphinx via:

easy_install -U Sphinx

To build HTML versions of the docs using Sphinx:
cd doc
make html

The docs are also available online:

http://pygr.org/docs/latest-release/

Core Prerequisites
-----------------

1) Python >= 2.3 

To build Pygr from source code, you need Pyrex

Apps Prerequiites
-----------------
	
MySQL-python >= 1.2.0
MySQL >= 3.23.x  

Note: While pygr's core functionality is solely dependent on a sane python environment, the aformentioned apps requirements must be installed if one wishes to utilize the apps modules and test code. 

Supported Platforms
-------------------

In theory, pygr should work on any platform that adequately supports python.

Here are the OS's we've successfully tested on:

o Linux 2.2.x/2.4.x
o OS X 
o OpenBSD
o Windows XP

Installation
------------

Installing pygr is quite simple. 

1) tar -xzvf pygr-0.3.tar.gz 
2) cd pygr
3) python setup.py install 

Once the test framework has completed successfully, the setup script
will install pygr into python's respective site-packages directory. 
If you don't want to install pygr into your system-wide site-packages,
replace the "python setup.py install" command with
"python setup.py build".  This will build pygr but not install it
in site-packages.

Using Pygr
----------
Check out the tutorials in the online docs!

Pygr contains several modules imported as follows:
from pygr import seqdb # IMPORT SEQUENCE DATABASE MODULE

If you did not install pygr in your system-wide site-packages, you 
must set your PYTHONPATH to the location of your pygr build.
For example, if your top-level pygr source directory is PYGRDIR then
you'd type something like:
setenv PYTHONPATH PYGRDIR/build/lib.linux-i686-2.3
where the last directory name depends on your specific architecture.


License
-------

New BSD license.

Author
------
Chris Lee <leec@chem.ucla.edu> and the rest of the Pygr developer team.
Please see http://code.google.com/p/pygr for a current list
of the participating developers.

Also see http://github.com/cjlee112/pygr/ for a list of other
developers who have created their own branches of the Pygr
git repository.


