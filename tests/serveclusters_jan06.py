from lldb_jan06 import *
import idservice

cursor=getUserCursor('SPLICE_JAN06')
t=SQLTable('SPLICE_JAN06.splice_cluster_hg17',cursor)
server=idservice.IDServer(t,host='leelab.mbi.ucla.edu')
server()
