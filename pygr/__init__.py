
# empty __init__.py to mark this as a package
# does not support: from pygr import *

__version__ = "0.8.0"

try:
    pygrData
except NameError:
    import metabase
    mdb = metabase.MetabaseList() # use default PYGRDATAPATH
    pygrData = mdb.Data
    pygrSchema = mdb.Schema
    pygrZones = mdb.zones

__all__ = ('__version__', 'pygrData', 'pygrSchema', 'pygrZones')
