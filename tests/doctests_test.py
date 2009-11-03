"""
Run all of the doctests in the doc/*.rest files.
"""
import os.path
import doctest
import unittest

from testlib import testutil


def codetest():
    "Test the code here before adding to doctest @CTB"
    import pygr
    from pygr.seqdb import SequenceFileDB
    db = SequenceFileDB(os.path.join('data', 'partial-yeast.fasta'))
    chr02 = db['chr02']
    start, stop = (87787, 86719)
    x = chr02[start:stop]


def get_suite():
    suite = unittest.TestSuite()

    names = [
#        'contents.rst',
#        'sequences.rst',
#        'contrib%sfetch.rst' % os.path.sep,   @CTB does not work on my system?
#        'recipes%spygrdata_recipes.rst' % os.path.sep,
#        'recipes%salignment_recipes.rst' % os.path.sep,
    ]

    # needs relative paths for some reason
    doctestpath = os.path.join('..', 'doc', 'rest')
    paths = [os.path.join(doctestpath, name) for name in names]

    for path in paths:
        docsuite = doctest.DocFileSuite(path)
        suite.addTest(docsuite)

    return suite


if __name__ == '__main__':
    #codetest()
    suite = get_suite()
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite)
