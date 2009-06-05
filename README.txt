Pygr README
===========

Introduction
------------

Pygr is an open source software project used to develop graph database 
interfaces for the popular Python language, with a strong emphasis 
on bioinformatics applications ranging from genome-wide analysis of 
alternative splicing patterns, to comparative genomics queries of 
multi-genome alignment data.

Latest Release
--------------

http://www.sourceforge.net/projects/pygr/

Documentation
-------------

doc/pygr/index.html is a good place to start. 

You can also check out:

http://bioinfo.mbi.ucla.edu/pygr/docs/

Core Prerequisites
-----------------

1) Python >= 2.1 

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
Pygr contains several modules imported as follows:
from pygr import seqdb # IMPORT SEQUENCE DATABASE MODULE

If you did not install pygr in your system-wide site-packages, you 
must set your PYTHONPATH to the location of your pygr build.
For example, if your top-level pygr source directory is PYGRDIR then
you'd type something like:
setenv PYTHONPATH PYGRDIR/build/lib.linux-i686-2.3
where the last directory name depends on your specific architecture.

Pygr has a myriad of applications, however, providing a comprehensive 
description of its utility is out of the scope of this document (see
Documentation). 

If you wish to test your install using the provided test scripts, 
or simply want to give pygr an initial whirl, follow these steps:

1) Flesh out ~/.my.cnf, like so:

------- cut here -------
[client]
socket = /var/lib/mysql/mysql.sock
user = zach
password = seaurchin007!
------ cut here -------

2) cd pygr/tests/ 
3) mysql < HUMAN_SPLICE_03
4) python test.py 

License
-------

GPL

Author
------
Chris Lee <clee@ucla.edu>

