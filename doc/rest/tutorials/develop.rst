

========================================
Working With the Pygr Code and Community
========================================

Use the Source, Luke...
-----------------------

A few recommendations:

* If you're going to do *anything* with Pygr's source code (even just 
  look at it), you should get it using `git <http://git-scm.com/>`_.
  Specifically, we recommend you register on `github <http://github.com>`_
  and create your own fork of the
  `Pygr repository <http://github.com/cjlee112/pygr/tree/master>`_.
  This just takes a minute, and makes it easy for you to exchange
  ideas and patches with everyone else working on Pygr.

  To get started just clone the public repository (if you created
  your own fork on github, substitute its URL here)::

     git clone git://github.com/cjlee112/pygr.git

  You can then build Pygr::

     cd pygr
     python setup.py build_ext -i

  And run the test suite::

     cd tests
     python runtest.py

  You can get lots of information about using ``git`` from our 
  `Git cheat sheet <http://code.google.com/p/pygr/wiki/UsingGit>`_.

How to Report Problems and Get Answers
--------------------------------------

* Consider joining the 
  `Pygr Dev Group <http://groups.google.com/group/pygr-dev?hl=en>`_
  just to listen in or get your questions answered.
  We *really* want to hear people's feedback and problems, so we
  can try to solve them.

* If you encounter a problem, feel free to ask for help on the Pygr Dev
  Group. 

* If it becomes clear that it's a bug in Pygr, *please*
  submit it to the `Issue Tracker <http://code.google.com/p/pygr/issues/list>`_
  as a bug report.  In particular,
  we need a *reproducible sequence of steps that will cause the bug*,
  a test that unambiguously indicates the bug has occurred (could be
  something as simple as "you get a KeyError"), and any data files
  required to reproduce the bug.  Make your reproducible steps
  "as simple as possible but no simpler".

* If at all possible, add your reproducible as a new test to the Pygr
  test suite, and push this on a well-named branch (e.g. "issue139"
  if you entered this as Issue 139 in the Issue Tracker) to your
  github repository::

    git push origin issue139

* If you make any changes to the Pygr source and want to propose
  them for inclusion in a future Pygr release (or otherwise invite
  discussion about what you're doing), push them in a
  branch (whose name gives some idea of what useful feature it
  contains) to your github repository, and then send mail to the
  `Pygr Developer discussion group <http://groups.google.com/group/pygr-dev?hl=en>`_::

    git push origin mycoolfeature

  (assuming that you made your changes in a local branch called
  ``mycoolfeature``).

More Info on Building and Installing
------------------------------------

To install Pygr to your Python install's ``site-packages``, 
cd to the top level of your pygr git repository and type::

   sudo python setup.py install

(assuming your Python install is only writable by ``root``,
and that you are on the ``sudo`` list of users with root privileges;
otherwise omit the ``sudo``).

Importing pygr Directly From Your Source Directory
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you don't want to install pygr into your system-wide site-packages,
replace the "python setup.py install" command with::

   python setup.py build_ext -i

This will build pygr but not install it in site-packages.

If you did not install pygr in your system-wide site-packages, you
must set your PYTHONPATH to the location of your pygr source.
For example, if your top-level pygr source directory is PYGRDIR then
you'd type something like::

   setenv PYTHONPATH /path/to/your/pygr

where the path should be to the top-level directory of your Pygr
repository.  You should then be able to import modules inside
its pygr source directory using::

   from pygr import seqdb

Building the Docs
^^^^^^^^^^^^^^^^^

To build the docs, you need the 
`Sphinx Documentation tool <>`
installed.

