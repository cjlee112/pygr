
from pygr import pygrData,pygrSchema
from metabase import ResourceServer, dumps, OneToManyRelation, \
     ManyToManyRelation, PygrDataNotPortableError, PygrDataNotFoundError, \
     PygrDataMismatchError, PygrDataEmptyError, PygrDataReadOnlyError, \
     PygrDataSchemaError, PygrDataNoModuleError

Bio = pygrData.Bio
schema = pygrSchema


getResource = pygrData._mdb # our metabase interface
addResource = pygrData._mdb.add_resource
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

__all__ = ('Bio', 'schema', 'getResource', 'addResource', 'addSchema',
           'deleteResource', 'dir', 'newServer', 'save', 'rollback',
           'list_pending', 'loads', 'dumps', 'update', 'clear_cache',
           'OneToManyRelation', 'ManyToManyRelation', 'PygrDataNotPortableError',
           'PygrDataNotFoundError', 'PygrDataMismatchError',
           'PygrDataEmptyError', 'PygrDataReadOnlyError',
           'PygrDataSchemaError', 'PygrDataNoModuleError')

