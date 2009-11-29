#! /usr/bin/env python
"""
Test runner for main pygr tests.

Collects all files ending in _test.py and executes them.
"""

import os
import re
import shutil
import sys
import unittest

from testlib import testutil, testoptions
from testlib.unittest_extensions import PygrTestRunner
from pygr import logger

disable_threshold = 0                   # global logging override


def all_tests():
    "Returns all file names that end in _test.py"
    patt = re.compile("_test.py$")
    mods = os.listdir(os.path.normpath(os.path.dirname(__file__)))
    mods = filter(patt.search, mods)

    # some predictable order...
    mods.sort()
    return mods


def run(targets, options):
    "Imports and runs the modules names that are contained in the 'targets'"

    success = errors = skipped = 0

    # run the tests by importing the module and getting its test suite
    for name in targets:
        try:
            testutil.info('running tests for module %s' % name)
            l = unittest.TestLoader()
            suite = l.loadTestsFromName(name)

            runner = PygrTestRunner(verbosity=options.verbosity,
                                    descriptions=0)

            logger.disable(disable_threshold)  # set global override
            results = runner.run(suite)
            logger.disable(0)                  # clear global override

            # count tests and errors
            success += results.testsRun - \
                       len(results.errors) - \
                       len(results.failures) - \
                       len(results.skipped)

            errors += len(results.errors) + len(results.failures)
            skipped += len(results.skipped)

            # if we're in strict mode stop on errors
            if options.strict and errors:
                testutil.error("strict mode stops on errors")
                break

        except ImportError:
            testutil.error("unable to import module '%s'" % name)

    # summarize the run
    testutil.info('=' * 59)
    testutil.info('''\
%s tests passed, %s tests failed, %s tests skipped; %d total''' % \
                  (success, errors, skipped, success + errors + skipped))

    return (success, errors, skipped)

if __name__ == '__main__':
    # Make sure no messages are filtered out at first
    logger.disable(0)

    # gets the prebuild option parser
    parser = testoptions.option_parser()

    # parse the options
    options, args = parser.parse_args()

    # modules: from command line args or all modules
    targets = args or all_tests()

    # get rid of the .py ending in case full module names were passed in
    # the command line
    stripped_targets = []
    for t in targets:
        if t.endswith('.py'):
            t = t[:-3]
        stripped_targets.append(t)
    targets = stripped_targets

    if options.port:
        testutil.default_xmlrpc_port = options.port

    # exclusion mode
    if options.exclude:
        targets = [name for name in all_tests() if name not in targets]

    # disables debug messages at < 2 verbosity, debug+info at < 1
    if options.verbosity < 1:
        disable_threshold = 'INFO' # Should implicity disable DEBUG as well
    elif options.verbosity < 2:
        disable_threshold = 'DEBUG'

    # cleans full entire test directory
    if options.clean:
        testutil.TEMPROOT.reset()
        testutil.TEMPDIR = testutil.TEMPROOT.path # yikes!

        # list patterns matching files to be removed here
        patterns = [
            "*.seqlen", "*.pureseq", "*.nin", "*.pin", "*.psd",
            "*.psi", "*.psq", "*.psd", "*.nni", "*.nhr",
            "*.nsi", "*.nsd", "*.nsq", "*.nnd",
        ]
        testutil.remove_files(path=testutil.DATADIR, patterns=patterns)

    # run all the tests
    if options.coverage:
        good, bad, skip = testutil.generate_coverage(run, 'coverage',
                                                     targets=targets,
                                                     options=options)
    else:
        good, bad, skip = run(targets=targets, options=options)

    if bad:
        sys.exit(-1)

    sys.exit(0)
