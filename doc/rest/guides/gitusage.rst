Using Git
=========

Why Git?
--------

Git is the front-runner of a new generation of "distributed source code management" 
tools that make it much easier for a dispersed group of developers to collaborate 
on a complex open source project like the Linux kernel.  The first thing to 
understand is that git dumps the previously universal assumption of a 
centralized repository, which developers check out files (from) and check in changes (to).
Instead, with git, *every* developer has the complete repository, storing the complete 
revision history.  That makes it much easier for each developer to work independently 
-- s/he doesn't even need a net connection to make commits.  Developers 
can clone a repository from each other, pull changes from each other, email 
patches to each other, push changes to a public site etc.  Second, git makes 
it spectacularly easy to work with branches: at any moment, you can create a new 
branch off your current code, make experimental changes as a series of commits on 
that branch -- without in any way affecting your "master" branch or any other branch 
-- and switch instantly between different branches.  Merging in changes from one branch 
to another is amazingly easy and powerful in git, so if you decide you like your 
experimental changes, you can apply them to your "master" branch easily -- typically with just a single command "git merge".  Git has great momentum now, and it has already been a terrific boost to Pygr development.

Git Usage Examples
-------------------

The Pygr project is tiny in comparison with Linux kernel, so we can get away with 
a pretty simple development model:

* I own the "master" branch; i.e. all proposed changes pass through me.
* I make changes in my git repository.
* I push changes to the public git repository.
* Anyone else can get their own copy of the repository by using "git clone" from the public repository.
* Anyone else can create their own branch (in their own git repository), to try out changes that they want to make.  *Don't make changes in the master branch* as this will complicate your ability to pull from the public repository in the future; instead always create a separate branch in which to make your changes.  In doing so, you just commit your changes as usual, but in your branch, not in the "master" branch.
* If you have finalized changes that you want incorporated into the master branch, send them to me as email patches.  I will then examine them (typically as a temporary branch in my repository), and if I see no problems, will merge them into the master branch.
* We can create separate branches for a specific release cycle.  E.g. I created a branch v0_7 for bug fixes to version 0.7.  It's trivial to pull bug fixes from the master branch into the v0_7 branch, and vice versa.

Get a copy of the public repository::

    git clone git://repo.or.cz/pygr.git

Get the latest changes from the public repository. The first command 
is only necessary if you were previously working on a different 
branch than "master"::

    git checkout master
    git pull --rebase

Make an experimental branch and commit changes there::

    git branch trythis
    git checkout trythis
    
    # edit one or more files, test your changes...
    git add pygr/sqlgraph.py tests/nosebase.py # whatever files you changed
    git add tests/new_test.py # you can also add new files to the repository
    git rm tests/old_test.py # and even delete a file (from this branch)
    git commit -m 'put a meaningful explanation of your changes here'
    
    # edit some more files...
    git add some_more_files.py
    git commit -m 'explain your new changes here'
    # and so on...

The basic process for making changes in git is:

* first, just edit whatever files you want.  You don't have to do anything to "check out" those files!
* use *git add* on your changed files, to "stage" these changes for committing.
* use *git commit* to commit all those changes as a single atomic revision.  Note that every commit has a unique ID (long hexadecimal code).  You can generally use this ID (or just its first few digits as long as it's unique) to specify a specific commit in any git command.

See a list of branches in your repository (the current branch is marked with an asterisk)::

    git branch

Switch to a different branch::

    git checkout master

Substitute the name of the branch you want for "master".

Go back to an old version::

    git checkout 1a413b3

You can use the first few digits of a commit ID, or a tag name.  This jumps
you back to that specific commit, which can be very useful for testing purposes.
Note that this puts you in effect on an "unnamed branch" whose HEAD is at the 
commit you specified.  To go back to the current HEAD of your master branch::

    git checkout master


See the current state of any edits you may have made, but not yet committed::

    git status


See the history and branch structure of the repository with a graphical tool 
(requires X windows and Tk)::

    gitk --all

See repository history as text::

    git log

Merge new changes from one branch to another::

    git checkout trythis
    git merge master

This example automatically applies any changes from the master branch that 
have been made after you created your *trythis* branch.  Git is able to do 
most merges completely automatically; only if the changes overlap the same 
lines of code will it ask you to sort out the conflict (it puts diff markers 
in the relevant file; your job is to edit that file to be the way you want it).

Apply a single commit from one branch to another::

    git checkout trythis
    git cherry-pick 37d1f89

Here we switch to the branch we want to change (in case we're not already on that branch).
Then you specify the commit you want to apply via its SHA1 hash code, 
or in this case just its first few digits.

Abandon any uncommitted changes, returning to last commit::

    git reset --hard HEAD

If you want to get rid of the last two *commits* as well::

    git reset --hard HEAD-2

.. note::
    Don't do the latter if you have already exposed those commits to other people!!!

Push updates from one machine to another

Say you have a test machine that currently has just the master branch 
cloned from the public repository.  Now suppose you have made a bunch 
of new changes on a new branch called "seqdb_refactor" on your main 
development machine, and want to test these changes on the test machine. 
Instead of having to push the new changes to the public repository, and 
then pull them to the test machine, you can push them directly to the test 
machine over ssh.  From your development machine, in your development repository::

    git push 'ssh://my.test.machine.address/~/projects/pygr/.git' seqdb_refactor

If the test machine repository doesn't have the seqdb_refactor branch, it will 
be created automatically.

Generate patch output for emailing me your changes::

    git format patch master >my_patches.txt

This outputs patches for all commits in the current branch not in the master branch

Apply someone else's patch file to your repository::

    git checkout -b titus_temp # create & switch to temporary branch
    git am <titus_patches.txt # apply the patch file

    # inspect changes to see if you like them
    # alter as you see fit, make additional commits until you're happy
    git checkout master # switch back to master
    git merge titus_temp # apply all our approved changes to master
    git branch -d titus_temp # don't need this temporary branch any more

Note that here the net effect was I applied the patches to my master 
branch.  But of course I could have applied to any branch I wanted.  
Note also that I adopt the cautious approach of first testing out all 
the patches in a temporary branch, rather than directly applying them 
to master.  This way, if I don't manage to finish this job in one sitting, 
it is kept separate from my master branch.  Indeed, I could switch back to 
the master branch and do urgent bug fixes, before switch back to titus_temp 
to finish my evaluation of the patch(es).

Pull from someone else's staging branch to your repository::

    git checkout -b titus_temp # create & switch to temporary branch
    git pull git://iorich.caltech.edu/git/public/pygr-ctb staging # get his changes

    # inspect changes to see if you like them
    # alter as you see fit, make additional commits until you're happy
    git checkout master # switch back to master
    git merge titus_temp # apply all our approved changes to master
    git branch -d titus_temp # don't need this temporary branch any more

The only difference from the previous method is that this pulls in all the 
commits from a particular branch of someone else's git repository, in this 
case the branch called "staging".

Push master branch to the public git repository::

    git push ssh://cjlee112@repo.or.cz/srv/git/pygr.git master

Replace the username with your own repo.or.cz username:

Tag a release::

    git tag v0.7.1

to tag the current HEAD of the current branch.  You can also tag a specific previous commit::

    git tag v0.7.5 78ac23bb

Additional Tutorials
--------------------

There are a *lot* of tutorials on how to use git.  Here are some I've found useful:

* http://www.kernel.org/pub/software/scm/git/docs/gittutorial.html standard git tutorial
* http://www-cs-students.stanford.edu/~blynn/gitmagic/ Stanford student git tutorial
* http://git.or.cz/course/svn.html Git - SVN Crash Course] for developers used to Subversion.
* http://rails.lighthouseapp.com/projects/8994/sending-patches Rails project git tutorial very similar to the usage pattern I'm recommending for Pygr development
* http://random-state.net/log/3410431842.html Getting Git]: a condensed view of git internals
* http://www.advogato.org/person/apenwarr/diary/371.html Git is the next Unix