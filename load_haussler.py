#!/sw/bin/python

from maf2graph import *
from seqdb import *
import MySQLdb

db=MySQLdb.Connection('localhost','test')
cursor=db.cursor()

## p=MafParser()
## p.parse(open('test.txt','r'))

## createTableFromRepr(p.mAlign.repr_dict(),'test.test1_align',cursor,
##                     {'src_id':'varchar(30)','dest_id':'varchar(30)'})

## known=[]
## for key in p.sequences:
##     for entry in p.sequences[key].known_int():
##         known+=[entry]

## createTableFromRepr(iter(known),'test.test1_int',cursor,
##                     {'src_id':'varchar(30)'})

p=MafParser()
p.parseIntoDB(open('chrY.maf','r'),cursor,'test.chrY_align','test.chrY_int')
