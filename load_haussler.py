#!/sw/bin/python

from maf2graph import *
from seqdb import *
import MySQLdb
from db_info import *

db=MySQLdb.Connection(read_default_file='~/.my.cnf')
cursor=db.cursor()

DBINFO=db_info_load('db_info.def')
filelist=open(DBINFO['TODO'])


file=filelist.readline()

while file:
    p=MafParser()
    ofile=os.popen(DBINFO['GUNZIP']+' '+file)
    try:
        p.parseIntoDB(ofile,cursor,DBINFO['ALIGN_TABLE'],DBINFO['INTERVAL_TABLE'])
    except Exception, inst:
        print "Error while parsing:",file
        print "Debug information follows:"
        print type(inst)
        print inst.args
    ofile.close()
    file=filelist.readline()
    
