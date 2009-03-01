
import sys

def serve_forever(self):
    self.keepRunning = True
    while self.keepRunning:
        self.handle_request()

def exit_now(self):
    self.keepRunning = False
    return 0

port = int(sys.argv[1]) # GET THE PORT NUMBER TO USE
if sys.argv[2] != 'PYGRDATAPATH': # SET PYGRDATAPATH FROM COMMAND-LINE ARG
    import os
    os.environ['PYGRDATAPATH'] = sys.argv[2]
i = 3
if sys.argv[i].startswith('downloadDB='): # NAME OF SHELVE RESOURCE DB
    downloadDB = sys.argv[i][11:]
    i += 1
else:
    downloadDB = None
# LOAD THE SPECIFIED RESOURCES FROM PYGR.DATA
import pygr.Data
l = [pygr.Data.getResource(name) for name in sys.argv[i:]]
# CREATE A NEW SERVER THAT WILL SERVE THE RESOURCES WE JUST LOADED
server=pygr.Data.getResource.newServer('testy',withIndex=True,
                                       downloadDB=downloadDB,
                                       host='localhost',port=port)
import new
m = new.instancemethod(exit_now,server.server,server.server.__class__)
server.server.register_function(m) # PROVIDE A WAY TO FORCE SERVER TO EXIT
serve_forever(server.server) # STARTS THE SERVER AND NEVER RETURNS...
