================================
Installation of Pygr from Source
================================


.. _install:

If for some reason you cannot use a binary package of Pygr, it can
always be installed from source. Installing pygr this way is quite simple::

   tar -xzvf pygr-0.3.tar.gz
   cd pygr
   python setup.py install


This will install pygr into python's respective site-packages directory.

If you don't want to install pygr into your system-wide site-packages,
replace the "python setup.py install" command with::

   python setup.py build

This will build pygr but not install it in site-packages.

Pygr contains several modules imported as follows::

   from pygr import seqdb # IMPORT SEQUENCE DATABASE MODULE


If you did not install pygr in your system-wide site-packages, you
must set your PYTHONPATH to the location of your pygr build.
For example, if your top-level pygr source directory is PYGRDIR then
you'd type something like::

   setenv PYTHONPATH PYGRDIR/build/lib.linux-i686-2.3

where the last directory name depends on your specific architecture.

