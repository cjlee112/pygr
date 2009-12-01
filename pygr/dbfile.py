
import anydbm
import shelve
import sys
import UserDict
import logger


class WrongFormatError(IOError):
    'attempted to open db with the wrong format e.g. btree vs. hash'
    pass


class NoSuchFileError(IOError):
    'file does not exist!'
    pass


class PermissionsError(IOError):
    'inadequate permissions for requested file'
    pass


class ReadOnlyError(PermissionsError):
    'attempted to open a file for writing, but no write permission'
    pass


def open_anydbm(*args, **kwargs):
    'trap anydbm.error message and transform to our consistent exception types'
    try:
        return anydbm.open(*args, **kwargs)
    except ImportError, e:
        if str(e).endswith('bsddb') and bsddb:
            # This almost certainly means dbhash tried to import bsddb
            # on a system with only bsddb3 working correctly. In that case,
            # simply do ourselves what anydbm would have done.
            # FIXME: explicitly check if dbhash raised this exception?
            return bsddb.hashopen(*args, **kwargs)
        raise
    except anydbm.error, e:
        msg = str(e)
        if msg.endswith('new db'):
            raise NoSuchFileError(msg)
        elif msg.startswith('db type'):
            raise WrongFormatError(msg)
        raise


try: # detect whether bsddb module available and working...
    import bsddb
    try:
        bsddb.db
    except AttributeError:
        raise ImportError
except ImportError:
    try:    # maybe the external bsddb3 will work instead...
        import bsddb3
        try:
            bsddb3.db
        except AttributeError:
            raise ImportError
        bsddb = bsddb3
    except ImportError: # ...nope
        bsddb = None


def open_bsddb(filename, flag='r', useHash=False, mode=0666):
    """open bsddb index instead of hash by default.
    useHash=True forces it to use anydbm default (i.e. hash) instead.
    Also gives more meaningful error messages."""
    try: # 1ST OPEN AS BTREE
        if useHash: # FORCE IT TO USE HASH INSTEAD OF BTREE
            return open_anydbm(filename, flag)
        else:
            return bsddb.btopen(filename, flag, mode)
    except bsddb.db.DBAccessError: # HMM, BLOCKED BY PERMISSIONS
        if flag=='c' or flag=='w': # TRY OPENING READ-ONLY
            try:
                ifile = file(filename)
            except IOError:
                # Hmm, not even readable. Raise a generic permission error.
                raise PermissionsError('insufficient permissions \
to open file: ' + filename)
            ifile.close()
            # We can read the file, so raise a ReadOnlyError.
            raise ReadOnlyError('file is read-only: '+ filename)
        else: # r OR n FLAG: JUST RAISE EXCEPTION
            raise PermissionsError('insufficient permissions to open file: '
                                   + filename)
    except bsddb.db.DBNoSuchFileError:
        raise NoSuchFileError('no file named: ' + filename)
    except bsddb.db.DBInvalidArgError: # NOT A BTREE FILE...
        try:
            if useHash: # NO POINT IN TRYING HASH YET AGAIN...
                raise bsddb.db.DBInvalidArgError
            # fallback to using default: hash file
            return open_anydbm(filename, flag)
        except bsddb.db.DBInvalidArgError:
            raise WrongFormatError('file does not match expected \
shelve format: ' + filename)


def open_index(filename, flag='r', useHash=False, mode=0666):
    if bsddb is None:
        d = open_anydbm(filename, flag)
        if not useHash:
            logger.warn('Falling back to hash index: unable to import bsddb')
        return d
    return open_bsddb(filename, flag, useHash, mode)


def iter_gdbm(db):
    'iterator for gdbm objects'
    k = db.firstkey()
    while k is not None:
        yield k
        k = db.nextkey(k)


class _ClosedDict(UserDict.DictMixin):
    """This dummy class exists solely to raise a clear error msg if accessed.
    Copied from the Python 2.6 shelve.py """

    def closed(self, *args):
        raise ValueError('invalid operation on closed shelf')
    __getitem__ = __setitem__ = __delitem__ = keys = closed

    def __repr__(self):
        return '<Closed Dictionary>'


class BetterShelf(shelve.Shelf):
    """Shelf subclass that fixes its horrible iter implementation.
    """

    def __iter__(self):
        'avoid using iter provided by shelve/DictMixin, which loads all keys!'
        try:
            return iter(self.dict)
        except TypeError: # gdbm lacks __iter__ method, so try iter_gdbm()
            exc_type, exc_value, exc_traceback = sys.exc_info()
            try:
                self.dict.firstkey
            except AttributeError: # evidently not a gdbm dict
                raise TypeError('''cannot iterate over this dictionary.
This means that you do not have bsddb, bsddb3, or gdbm available for use by
the 'shelve' module in this Python install.  Please fix this!

Original error message was: %s''' % str(exc_value))
            else: # iterate using gdbm-specific method
                return iter_gdbm(self.dict)

    if sys.version_info < (2, 6): # Python finally added good err msg in 2.6

        def close(self):
            if isinstance(self.dict, _ClosedDict):
                return # if already closed, nothing further to do...
            shelve.Shelf.close(self) # close Shelf as usual
            self.dict = _ClosedDict() # raises sensible error msg if accessed


def shelve_open(filename, flag='c', protocol=None, writeback=False,
                useHash=False, mode=0666, *args, **kwargs):
    """improved implementation of shelve.open() that won't generate
bogus __del__ warning messages like Python's version does."""
    d = open_index(filename, flag, useHash, mode) # construct Shelf only if OK
    return BetterShelf(d, protocol, writeback, *args, **kwargs)
