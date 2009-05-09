
__version__ = "0.8.0"

try:
    worldbase
except NameError:
    import metabase
    mdb = metabase.MetabaseList() # use default WORLDBASEPATH
    worldbase = mdb.Data

__all__ = ('__version__', 'worldbase')
