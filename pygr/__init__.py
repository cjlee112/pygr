import sys
__version__ = "0.8.1"

try:
    worldbase
except NameError:
    import metabase
    mdb = metabase.MetabaseList() # use default WORLDBASEPATH
    worldbase = mdb.Data

if sys.version_info < (2, 6):

    def dir(obj):
        """provide Python 2.6+ style __dir__ support """
        try:
            get_dir = obj.__dir__
        except AttributeError:
            return __builtins__['dir'](obj)
        else:
            return get_dir()
else: # Python 2.6 or later, just use the builtin dir()
    dir = __builtins__['dir']

__all__ = ('__version__', 'worldbase', 'dir')
