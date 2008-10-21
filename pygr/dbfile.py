
import shelve

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

class BtreeShelf(shelve.Shelf):
    """Shelf implementation using bsddb btree index, wrapped in
    the "anydbm" generic dbm interface.

    This is initialized with the filename for the dbm database.
    See the module's __doc__ string for an overview of the interface.
    """

    def __init__(self, filename, flag='r', protocol=None, writeback=False, mode=0666,useHash=False):
        import bsddb
        try: # 1ST OPEN AS BTREE
            if useHash: # FORCE IT TO USE HASH INSTEAD OF BTREE
                import anydbm # FALLBACK TO USING DEFAULT: HASH FILE
                d = anydbm.open(filename, flag)
            else:
                d = bsddb.btopen(filename, flag, mode)
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
                import anydbm # FALLBACK TO USING DEFAULT: HASH FILE
                d = anydbm.open(filename, flag)
            except bsddb.db.DBInvalidArgError:
                raise WrongFormatError('file does not match expected shelve format: '+filename)
                
        shelve.Shelf.__init__(self, d, protocol, writeback)
    def __iter__(self):
        'avoid using iter provided by shelve/DictMixin, which loads all keys!'
        return iter(self.dict)
