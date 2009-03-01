from twisted.web import server, resource
from twisted.internet import reactor

from exonsvg import *
from test import *

class SVGServer(resource.Resource):
    "simple example of creating HTTP server"
    isLeaf = True
    def __init__(self):
        "load basic splice graph schema"
        self.header='<head>\n<META HTTP-EQUIV="pragma" CONTENT="no-cache">\n<title>Taz Project System</title></head>'
        (self.clusters,self.exons,self.splices,self.genomic_seq,
         self.spliceGraph,self.alt5Graph,self.alt3Graph,
         self.mrna,self.protein,
         self.clusterExons,self.clusterSplices)=loadTestJUN03() # USE OUR JUN03 DATABASE

    def html(self,stem):
        "generate an html document with an <embed> SVG link"
        html='<html>%s<body><h1>%s</h1><p><embed src="%s.svg" width=1000 height=400/></p></body>\n</html>\n' % (self.header,stem,stem)
        return html

    def svg(self,cluster_id):
        "get splice graph for the specific cluster if not already loaded, then generate basic SVG for it"
        c=self.clusters[cluster_id]
        if c not in self.clusterExons: # NOT BUILT YET, BETTER BUILD ITS SPLICE GRAPH
            loadCluster(c,self.exons,self.splices,self.clusterExons,self.clusterSplices,
                        self.spliceGraph,self.alt5Graph,self.alt3Graph)
        d=draw(c.exons,len(self.genomic_seq[c.id]),0) #CALL MEENAKSHI'S DRAWING FUNCTION
        return d.toXml() # HAND BACK THE XML AS A STRING

    def render(self,request):
        "handle an HTTP request, either for an HTML or SVG document"
        print 'postpath[-1]=',request.postpath[-1]
        if request.postpath[-1][-4:]=='.svg':
            return self.svg(request.postpath[-1][:-4])
        elif request.postpath[-1][-5:]=='.html':
            return self.html(request.postpath[-1][:-5])


site = server.Site(SVGServer()) # CREATE THE SERVER
reactor.listenTCP(8888, site) # BIND IT TO THE EVENT PROCESSOR
print 'Now running HTTP server on port',8888
reactor.run() # START THE SERVER
