#!/sw/bin/python

from maf2graph import *
from seqdb import *
import MySQLdb

db=MySQLdb.Connection('localhost','test')
cursor=db.cursor()

p=MafParser()
p.parse(open('test.txt','r'))

createTableFromRepr(p.mAlign.repr_dict(),'test.haussler',cursor,
                    {'src_id':'varchar(30)','dest_id':'varchar(30)'})
