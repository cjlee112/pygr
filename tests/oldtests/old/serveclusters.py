
from pygr.apps.leelabdb import *
import idservice

cursor=getUserCursor('HUMAN_SPLICE_03')
t=SQLTable('HUMAN_SPLICE_03.alternative_clusters_JUN03',cursor)
server=idservice.IDServer(t,host='leelab.mbi.ucla.edu')
server()
