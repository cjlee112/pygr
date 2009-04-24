"""
Provide support for test skipping.
"""

import unittest

try:
    from nose.plugins.skip import SkipTest
except ImportError: # no nose?
    class SkipTest(Exception):
        pass

class PygrTestResult(unittest._TextTestResult):
    def addError(self, test, err):
        exc_type, _, _ = err
        if issubclass(exc_type, SkipTest):
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
