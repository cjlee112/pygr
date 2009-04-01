
import shelve, anydbm
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

def open_index(filename, flag='r', useHash=False, mode=0666):
    """open bsddb index instead of hash by default.
    useHash=True forces it to use anydbm default (i.e. hash) instead.
    Also gives more meaningful error messages."""
    try:
        import bsddb
    except ImportError:
        d = anydbm.open(filename, flag)
        if not useHash:
            logger.warn('Falling back to hash index: unable to import bsddb')
        return d
    try: # 1ST OPEN AS BTREE
        if useHash: # FORCE IT TO USE HASH INSTEAD OF BTREE
            return anydbm.open(filename, flag)
        else:
            return bsddb.btopen(filename, flag, mode)
    except bsddb.db.DBAccessError: # HMM, BLOCKED BY PERMISSIONS
        if flag=='c' or flag=='w': # TRY OPENING READ-ONLY
            try:
                ifile = file(filename)
            except IOError: # HMM, NOT EVEN READABLE. RAISE GENERIC PERMISSIONS ERROR
                raise PermissionsError('insufficient permissions to open file: '
                                       +filename)
            ifile.close() # OK, WE CAN READ THE FILE, SO RAISE EXCEPTION WITH
            raise ReadOnlyError('file is read-only: '+filename) # VERY SPECIFIC MEANING!
        else: # r OR n FLAG: JUST RAISE EXCEPTION
            raise PermissionsError('insufficient permissions to open file: '
                                   +filename)
    except bsddb.db.DBNoSuchFileError:
        raise NoSuchFileError('no file named: '+filename)
    except bsddb.db.DBInvalidArgError: # NOT A BTREE FILE...
        try:
            if useHash: # NO POINT IN TRYING HASH YET AGAIN...
                raise bsddb.db.DBInvalidArgError
            # fallback to using default: hash file
            return anydbm.open(filename, flag)
        except bsddb.db.DBInvalidArgError:
            raise WrongFormatError('file does not match expected shelve format: '+filename)

class BetterShelf(shelve.Shelf):
    """Shelf subclass that fixes its horrible iter implementation.
    """
    def __iter__(self):
        'avoid using iter provided by shelve/DictMixin, which loads all keys!'
        return iter(self.dict)

def shelve_open(filename, flag='c', protocol=None, writeback=False,
                useHash=True, mode=0666, *args, **kwargs):
    """improved implementation of shelve.open() that won't generate
bogus __del__ warning messages like Python's version does."""
    d = open_index(filename, flag, useHash, mode) # construct Shelf only if OK
    return BetterShelf(d, protocol, writeback, *args, **kwargs)
