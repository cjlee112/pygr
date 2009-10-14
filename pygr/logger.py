"""
Implements logging functionality

Upon import creates a module level log class (log) and
the following logging functions:

debug, info, warn and error

The default formatters will print out the function the log was triggered from.
"""

import logging
import sys

# python 2.5 the watershed release that introduced most changes since 2.1

PYTHON_25 = sys.version_info >= (2, 5)


def get_logger(name='pygr-log', stream=sys.stdout, formatter=None):
    """
    Returns a logger

    >>> disable('INFO')
    >>> info('logtest, this message SHOULD NOT be visible')
    >>> disable()
    >>> info('logtest, this message should be visible')
    >>> disable('DEBUG')
    >>> debug('logtest, this message SHOULD NOT be visible')
    >>> info('logtest, this message should be visible')
    """
    logger = logging.getLogger(name)

    # this is needed in case the process is
    # forked/multithreaded; loggers exist in a global scope
    # we don't want each import to duplocate this handler

    if not logger.handlers:
        console = logging.StreamHandler(stream)
        console.setLevel(logging.DEBUG)
        if PYTHON_25:
            format = '%(levelname)s %(module)s.%(funcName)s: %(message)s'
        else:
            format = '%(levelname)s %(module)s: %(message)s'

        formatter = formatter or logging.Formatter(format)
        console.setFormatter(formatter)
        logger.addHandler(console)
        logger.setLevel(logging.DEBUG)
    return logger


def disable(level=0):
    """
    Disables logging levels
    Levels: DEBUG, INFO, WARNING, ERROR

    >>> disable('INFO')
    >>> info('logtest, this message SHOULD NOT be visible')
    """
    level = str(level)
    value = dict(NOTSET=0, DEBUG=10, INFO=20, WARNING=30, ERROR=40)\
            .get(level.upper(), 0)
    logging.disable(value)


# populate some loggers by default
log = get_logger()
debug, info, warn, error = log.debug, log.info, log.warn, log.error


def test(verbose=0):
    "Performs module level testing"
    import doctest
    doctest.testmod(verbose=verbose)


if __name__ == "__main__":
    test()
