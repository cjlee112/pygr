#! /usr/bin/env python
"""
Test runner for main pygr tests.

Collects all files ending in _test.py and executes them with
unittest.TextTestRunner.
"""

import os, sys, re, unittest, shutil, re, shutil
from testlib import testutil, testoptions
from pygr import logger

def all_tests():
    "Returns all file names that end in _test.py"
    patt = re.compile("_test.py$")
    mods = os.listdir(os.path.normpath(os.path.dirname(__file__)))
    mods = filter(patt.search, mods)
    mods = [ m.rstrip(".py") for m in mods ]

    # some predictable order...
    mods.sort() 
    return mods

def run(targets, options):
    "Imports and runs the modules names that are contained in the 'targets'"
    
    success = errors = 0

    # run the tests by importing the module and getting its test suite
    for name in targets:
        try:
            testutil.info( 'running tests for module %s' % name )
            mod = __import__( name )
            suite = mod.get_suite()

            runner = unittest.TextTestRunner(verbosity=options.verbosity,
                                             descriptions=0)
            results = runner.run( suite )
            
            # count tests and errors
            success += results.testsRun - \
                       len(results.errors) - len(results.failures)
            errors  += len(results.errors) + len(results.failures)

            # if we're in strict mode stop on errors
            if options.strict and errors:
                testutil.error( "strict mode stops on errors" )
                break

        except ImportError:
            testutil.error( "unable to import module '%s'" % name )

    # each skipped testsuite generates a message
    skipped = len(testutil.SKIP_MESSAGES)
    
    # generate warnings on skipped tests
    for message in testutil.SKIP_MESSAGES:
        testutil.warn(message)

    # summarize the run
    testutil.info('=' * 59)
    testutil.info('''\
%s tests passed, %s tests failed, %s suites skipped; %d total''' % \
                  (success, errors, skipped, success + errors + skipped))

    return (success, errors, skipped)

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

    if options.port:
        testutil.default_xmlrpc_port = options.port

    # exclusion mode
    if options.exclude:
        targets = [ name for name in all_tests() if name not in targets ]

    # disables debug messages at < 2 verbosity
    if options.verbosity != 2:
        logger.disable('DEBUG')
    
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
