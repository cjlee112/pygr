
__version__ = "0.8.0"

try:
    worldbase
except NameError:
    import metabase
    mdb = metabase.MetabaseList() # use default PYGRDATAPATH
    worldbase = mdb.Data
    worldbaseSchema = mdb.Schema
    worldbaseZones = mdb.zones

__all__ = ('__version__', 'worldbase', 'worldbaseSchema', 'worldbaseZones')
