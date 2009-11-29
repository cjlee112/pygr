"""
Option parser for all tests

Needs to be a separate module to avoid circular imports
"""

import optparse
import sys


def option_parser():
    """
    Returns the option parser for tests.

    This parser needs to be able to handle all flags that may be passed
    to any test

    Due to the optparse desing we cannot create a 'partial' option parser
    that would ignore extra parameters while allowing it to be later be
    extended. So it is either every flag goes the main option parser,
    or each module will have to implement almost identical parsers.

    Having one large option parser seemed the lesser of two bad choices.
    """

    parser = optparse.OptionParser()

    # passing -n will disable the pathfix, use it to test global pygr
    # distributions
    parser.add_option(
        '-n', '--nopath', action="store_true", dest="no_pathfix",
        default=False, help="do not alter the python import path")

    # add the regular build directory rather than the in place directory
    parser.add_option(
        '-b', '--buildpath', action="store_true", dest="builddir",
        default=False, help="use the platform specific build directory",
    )

    # stops testing immediately after a test suite fails
    parser.add_option(
        '-s', '--strict', action="store_true",
        dest="strict", default=False,
        help="stops testing after a test suite fails")

    # exclude the modules listed in arguments from all the tests
    parser.add_option(
        '-x', '--exclude', action="store_true",
        dest="exclude", default=False,
        help="excludes the files that are listed")

    # verbosity can be 0,1 and 2 (increasing verbosity)
    parser.add_option(
        '-v', '--verbosity', action="store",
        dest="verbosity", type="int", default=0,
        help="sets the verbosity (0, 1, or 2)",
    )

    # long options are typically used only within individual tests

    # executes figleaf to collect the coverage data
    parser.add_option(
        '--coverage', action="store_true", dest="coverage", default=False,
        help=
  "runs figleaf and collects the coverage information into the html directory")

    # adds the clean option to the testrunner
    parser.add_option(
        '--no-clean', action="store_false", dest="clean", default=True,
        help="does not reset the temporary directory and temp files")

    # runs the performance tests
    parser.add_option(
        '--performance', action="store_true", dest="performance",
        default=False,
        help="runs the performance tests (not implemented)")

    # port information for the pygrdata_test.py test; default is random
    parser.add_option(
        '--port', action="store", type="int",
        dest="port", default=0,
        help="sets the port information for the XMLRPC server")

    # where to write out the port information, for communication to test
    # runner.
    parser.add_option(
        '--port-file', action="store", type="string",
        dest="port_file",
        help="where to write the port information for the XMLRPC server")

    # set the pygraphdata path from command line
    parser.add_option(
        '--pygrdatapath', action="store", type="string",
        dest="pygrdatapath", default='',
        help="sets the pygraphdata path for the XMLRPC server")

    # add resources to the path colon separated
    # --downloadDB=database1
    parser.add_option(
        '--downloadDB', action="store", type="string",
        dest="downloadDB", default=None,
        help="sets the downloadDB shelve for the XMLRPC server")


    # add resources to the path colon separated
    # --resources=database1
    parser.add_option('--resources', action="store", type="string",
                      dest="resources", default='',
                      help=
     "sets the downloadable resources, separate multiple ones with a : symbol")

    return parser

if __name__ == '__main__':
    # list flags here
    flags = " --downloadDB=1234 "

    sys.argv.extend(flags.split())
    parser = option_parser()
    options, args = parser.parse_args()

    print options
