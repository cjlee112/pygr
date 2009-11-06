"""
Provide support for test skipping.
"""

import unittest
from pygr import logger


try:
    from nose.plugins.skip import SkipTest
except ImportError: # no nose?

    class SkipTest(Exception):
        pass


class PygrTestResult(unittest._TextTestResult):

    def __init__(self, *args, **kwargs):
        unittest._TextTestResult.__init__(self, *args, **kwargs)
        self.skipped = []

        # by default, support dots at lowest verbosity.
        verbosity = kwargs.get('verbosity', 0)
        show_dots = kwargs.get('show_dots', 1)
        if verbosity == 0 and show_dots:
            self.dots = 1

    def addError(self, test, err):
        exc_type, val, _ = err
        if issubclass(exc_type, SkipTest):
            self.skipped.append((self, val))
            if self.showAll:                         # report skips: SKIP/S
                self.stream.writeln("SKIP")
            elif self.dots:
                self.stream.write('S')
        else:
            unittest._TextTestResult.addError(self, test, err)


class PygrTestRunner(unittest.TextTestRunner):
    """
    Support running tests that understand SkipTest.
    """

    def _makeResult(self):
        return PygrTestResult(self.stream, self.descriptions,
                              self.verbosity)


class PygrTestProgram(unittest.TestProgram):

    def __init__(self, **kwargs):
        verbosity = kwargs.pop('verbosity', 1)
        if verbosity < 1:
            logger.disable('INFO')  # Should implicity disable DEBUG as well
        elif verbosity < 2:
            logger.disable('DEBUG')
        if kwargs.get('testRunner') is None:
            kwargs['testRunner'] = PygrTestRunner(verbosity=verbosity)

        unittest.TestProgram.__init__(self, **kwargs)
