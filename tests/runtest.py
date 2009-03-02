#! /usr/bin/env python
"""
Test runner for main pygr tests.

Collects all files ending in _test.py and executes them with
unittest.TextTestRunner.
"""

import os, sys, re, unittest, shutil, re, shutil
from testlib import testutil, logger, testoptions

def all_tests():
    "Returns all file names that end in _test.py"
    patt = re.compile("_test.py$")
    mods = os.listdir(os.getcwd())
    mods = filter(patt.search, mods)
    mods = [ m.rstrip(".py") for m in mods ]

    # some predictable order...
    mods.sort() 
    return mods

def run(targets, options):
    "Imports and runs the modules names that are contained in the 'targets'"
    
    success = errors = 0

    entire_suite = unittest.TestSuite()
    
    # run the tests by importing the module and getting its test suite
    for name in targets:
        try:
            testutil.debug('loading tests for module %s' % name)
            mod = __import__(name)
            suite = mod.get_suite()

            if options.strict:
                result = unittest.TextTestRunner(verbosity=options.verbosity).\
                          run(suite)
            
                # count tests and errors
                success += result.testsRun
                errors  += len(result.errors) + len(result.failures)

                if errors:
                    testutil.error("strict mode stops on errors")
                    break
            else:
                entire_suite.addTest(suite)
        except (ImportError, SyntaxError):
            testutil.error("unable to import module '%s'" % name)

    if not options.strict:
        # run all tests at once
        tr = unittest.TextTestRunner(verbosity=options.verbosity)
        result = tr.run(entire_suite)
        success = result.testsRun
        errors = len(result.errors) + len(result.failures)

    # each skipped testsuite generates a message
    skipped = len(testutil.SKIP_MESSAGES)
    
    # generate warnings on skipped tests
    for message in testutil.SKIP_MESSAGES:
        testutil.warn(message)

    # summarize the run
    testutil.info('=' * 50)
    testutil.info('%s tests passed, %s tests failed, %s suites skipped' % \
                  (success, errors, skipped))

if __name__ == '__main__':
    # gets the prebuild option parser
    parser = testoptions.option_parser()

    # parse the options
    options, args = parser.parse_args()

    # modules: from command line args or all modules
    targets = args or all_tests()

    # get rid of the .py ending in case full module names were passed in
    # the command line
    targets = [ t.rstrip(".py") for t in targets ]

    # exclusion mode
    if options.exclude:
        targets = [ name for name in all_tests() if name not in targets ]

    # disables debug messages at < 2 verbosity
    if options.verbosity != 2:
        logger.disable('DEBUG')
    
    # run all the tests
    if options.coverage:
        testutil.generate_coverage(run, 'coverage', targets=targets,
                                   options=options)
    else:
        run(targets=targets, options=options)
