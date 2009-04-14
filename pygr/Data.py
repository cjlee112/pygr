
from pygr import pygrData,pygrSchema
from metabase import ResourceServer, dumps, OneToManyRelation, OneToOneRelation,\
     ManyToManyRelation, PygrDataNotPortableError, PygrDataNotFoundError, \
     PygrDataMismatchError, PygrDataEmptyError, PygrDataReadOnlyError, \
     PygrDataSchemaError, PygrDataNoModuleError, ResourceZone

schema = pygrSchema # ROOT OF OUR SCHEMA NAMESPACE

# PROVIDE TOP-LEVEL NAMES IN OUR RESOURCE HIERARCHY
Bio = pygrData.Bio

getResource = pygrData._mdb # our metabase interface
addResource = pygrData._mdb.add_resource
def addResourceDict(d, layer=None):
    'queue a dict of name:object pairs for saving to specified db layer'
    if layer is not None: # use the named metabase specified by layer
        mdb = pygrData._mdb.zoneDict[layer] # KeyError if layer not found!
    else: # use default MetabaseList
        mdb = pygrData._mdb
    for k,v in d.items(): # queue each resource in the dictionary
        mdb.add_resource(k, v)

addSchema = pygrData._mdb.add_schema
deleteResource = pygrData._mdb.delete_resource
dir = pygrData._mdb.dir
def newServer(*args, **kwargs):
    return ResourceServer(pygrData._mdb, *args, **kwargs)
save = pygrData._mdb.commit
rollback = pygrData._mdb.rollback
list_pending = pygrData._mdb.list_pending
loads = pygrData._mdb.loads
update = pygrData._mdb.update
clear_cache = pygrData._mdb.clear_cache

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
           'OneToOneRelation', 'PygrDataNotPortableError',
           'PygrDataNotFoundError', 'PygrDataMismatchError',
           'PygrDataEmptyError', 'PygrDataReadOnlyError',
           'PygrDataSchemaError', 'PygrDataNoModuleError',
           'here', 'my', 'system', 'subdir', 'remote', 'MySQL')

