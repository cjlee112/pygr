"""
Pygr XMLRPC server test. Recognized flags:

--port=PORT 
    the port for the server

--pygrdatapath=PYGRDATAPATH 
    the pygr.Data directory

--resources=RESOURCE1:RESOURCE2:RESOURCE3 
    a colon separated list of resource names

--downloadDB=DOWNLOADDB 
    the shelve used

"""
import new, sys, os
import pathfix, testoptions, testutil, logger

# same options for all tests (some flags may be ignored)
parser = testoptions.option_parser()

# parse the arguments
options, args = parser.parse_args()

# change the pygrdatapath if necessary
if options.pygrdatapath:
    testutil.change_pygrdatapath(options.pygrdatapath)

# disables debug messages at zero verbosity
if options.verbosity == 0:
    logger.disable('DEBUG')

# import after path change
import pygr.Data

# this is done for the side effects on pygr.Data
# the resources are listed as comma separated names
names = filter(None, options.resources.split(':'))
resources = map(pygr.Data.getResource, names)

# set it to None
options.downloadDB = options.downloadDB or None

# create a new server that will serve the resources we just loaded
xmlrpc = pygr.Data.getResource.newServer('testy',
                                         withIndex=True,
                                         downloadDB=options.downloadDB,
                                         host='localhost', port=options.port)

# main loop
def serve_forever(self):
    self.keepRunning = True
    while self.keepRunning:
        self.handle_request()

# exit handler
def exit_now(self):
    self.keepRunning = False
    return 0

# add and exit handler to the server
exit_handler = new.instancemethod(exit_now, xmlrpc.server,
                                  xmlrpc.server.__class__)

# register exit handler
xmlrpc.server.register_function(exit_handler) 

# starts the server and never returns...
serve_forever(xmlrpc.server) 
