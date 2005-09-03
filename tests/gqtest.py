from pygr.graphquery import *


dataGraph={'a':{'b':None,'c':None,'d':None},'b':{'c':None},'c':{},'d':{}}
queryGraph={1:{2:None,3:None},2:{3:None},3:{}}

for d in GraphQuery(dataGraph,queryGraph):
    print 'match:',d
