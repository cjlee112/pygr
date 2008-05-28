from xmlrpclib import *
import time

class IDServer(object):
    'serve iterator it via XMLRPC on designated port'
    def __init__(self,it,host='localhost',port=8888):
        import SimpleXMLRPCServer
        self.it=iter(it)
        self.n=0
        server=SimpleXMLRPCServer.SimpleXMLRPCServer((host,port))
        server.register_instance(self)
        self.server=server

    def __call__(self,*l,**kwargs):
        'start the service -- this will run forever'
        self.server.serve_forever()

    def next(self):
        'return next ID from iterator to the XMLRPC caller'
        try:
            id=self.it.next()
            self.n+=1
            self.lastID=id
            return id
        except StopIteration:
            return ''


class IDClient(object):
    'provides an iterator interface to an XMLRPC ID server'
    def __init__(self,url="http://localhost:8888"):
        import xmlrpclib
        self.server=xmlrpclib.ServerProxy(url)

    def __iter__(self):
        return self

    def next(self):
        id=self.server.next()
        if id=='':
            raise StopIteration
        else:
            return id 
