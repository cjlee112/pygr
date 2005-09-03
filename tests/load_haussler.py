#!/sw/bin/python

from pygr.apps.maf2VSgraph import *
from pygr.seqdb import *
import MySQLdb
from db_info import *
import os

db=MySQLdb.Connection(read_default_file='~/.my.cnf')
cursor=db.cursor()

DBINFO=db_info_load('db_info.def')
filelist=open(DBINFO['TODO'])


file=filelist.readline().strip()

while file:
    p=MafParser()
    s=DBINFO['GUNZIP']+' '+file+' >load.tmp'
##    print s;
    os.system(s)
    ofile=open('load.tmp')
    try:
        p.parseIntoDB(ofile,cursor,DBINFO['ALIGN_TABLE'],DBINFO['INTERVAL_TABLE'])
    except Exception, inst:
        print "Error while parsing:",file
        print "Debug information follows:"
        print type(inst)
        print inst.args
    ofile.close()
    os.system('rm load.tmp')
    file=filelist.readline().strip()
    
