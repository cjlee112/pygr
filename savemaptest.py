from blasttest import *
import MySQLdb

db=MySQLdb.Connection('localhost','test','hedgehog')
cursor=db.cursor()

# SAVE ALIGNMENT m TO DATABASE TABLE test.mytable USING cursor
createTableFromRepr(m.repr_dict(),'test.mytable',cursor,
                    {'src_id':'varchar(12)','dest_id':'varchar(12)'})
