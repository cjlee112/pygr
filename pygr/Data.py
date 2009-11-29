
import warnings
warnings.warn('pygr.Data is deprecated.  Use "from pygr import worldbase" \
              instead!', DeprecationWarning, stacklevel=2)

from pygr import worldbase
from metabase import ResourceServer, dumps, OneToManyRelation,\
        OneToOneRelation, ManyToManyRelation, WorldbaseNotPortableError,\
        WorldbaseNotFoundError, WorldbaseMismatchError, WorldbaseEmptyError,\
        WorldbaseReadOnlyError, WorldbaseSchemaError, WorldbaseNoModuleError,\
        ResourceZone

schema = worldbase.schema # ROOT OF OUR SCHEMA NAMESPACE

# PROVIDE TOP-LEVEL NAMES IN OUR RESOURCE HIERARCHY
Bio = worldbase.Bio

getResource = worldbase._mdb # our metabase interface
addResource = worldbase._mdb.add_resource


def addResourceDict(d, layer=None):
    'queue a dict of name:object pairs for saving to specified db layer'
    if layer is not None: # use the named metabase specified by layer
        mdb = worldbase._mdb.zoneDict[layer] # KeyError if layer not found!
    else: # use default MetabaseList
        mdb = worldbase._mdb
    for k, v in d.items(): # queue each resource in the dictionary
        mdb.add_resource(k, v)

addSchema = worldbase._mdb.add_schema
deleteResource = worldbase._mdb.delete_resource
dir = worldbase._mdb.dir


def newServer(*args, **kwargs):
    return ResourceServer(worldbase._mdb, *args, **kwargs)

save = worldbase._mdb.commit
rollback = worldbase._mdb.rollback
list_pending = worldbase._mdb.list_pending
loads = worldbase._mdb.loads
update = worldbase._mdb.update
clear_cache = worldbase._mdb.clear_cache

# TOP-LEVEL NAMES FOR STANDARDIZED LAYERS
here = ResourceZone(getResource, 'here')
my = ResourceZone(getResource, 'my')
system = ResourceZone(getResource, 'system')
subdir = ResourceZone(getResource, 'subdir')
remote = ResourceZone(getResource, 'remote')
MySQL = ResourceZone(getResource, 'MySQL')

__all__ = ('Bio', 'schema', 'getResource', 'addResource', 'addSchema',
           'deleteResource', 'dir', 'newServer', 'save', 'rollback',
           'list_pending', 'loads', 'dumps', 'update', 'clear_cache',
           'OneToManyRelation', 'ManyToManyRelation',
           'OneToOneRelation', 'WorldbaseNotPortableError',
           'WorldbaseNotFoundError', 'WorldbaseMismatchError',
           'WorldbaseEmptyError', 'WorldbaseReadOnlyError',
           'WorldbaseSchemaError', 'WorldbaseNoModuleError',
           'here', 'my', 'system', 'subdir', 'remote', 'MySQL')
