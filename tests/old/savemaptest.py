from blasttest import *
import MySQLdb
import os

db=MySQLdb.Connection(db='test',read_default_file=os.environ['HOME']+'/.my.cnf')
cursor=db.cursor()

# SAVE ALIGNMENT m TO DATABASE TABLE test.mytable USING cursor
createTableFromRepr(m.repr_dict(),'test.mytable',cursor,
                    {'src_id':'varchar(12)','dest_id':'varchar(12)'})
