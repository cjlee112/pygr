"""PygrUtils.py

Contains general classes and methods for working with Pygr data sets.

CLASSES
    Exon
    SimpleGraph
    AnnotationDBMapping

"""

from pygr import mapping
from pygr import worldbase
from pygr import metabase


class Exon:
    """Container class for exon information used by
    scripts/build_annotation_from_refseq_exons.py

    This class was copied from that script.
    """
    def __init__(self, id, name, start, stop, geneID):
        self.id, self.name, self.start, self.stop, self.geneID = (id, name, start, stop, geneID)
    def __str__(self):
        return 'Exon on %s with id %s in gene %s genomic coords [%s:%s]'%(self.id,self.name,self.geneID,self.start,self.stop)

class SimpleGraph(mapping.Graph):
    """A simplified version of a graph.

    It stores edges as themselves, instead of their ID.

    See: http://groups.google.com/group/pygr-dev/browse_thread/thread/54b329257e637721
    
    """

    def pack_edge(self, edge):
       return edge

    def unpack_edge(self, edge):
       return edge 
    
class AnnotationDBMapping(object):
    """Class for creating forward and/or backward mapping of between annotation databases.
    """
    def __init__(self, annotDB1, annotDB2, resourceString, filename,
                 forwardAttr, reverseAttr = None, inverseAttr = None,
                 mode = 'nr', multiValue = True, verbose = True):
        """Constructor.
            annotDB1 - pygr annotation db object containing the source
            annotDB2 - pygr annotation db object containing the target
            pathStem - complete file path to the physical mapping resource. The corresponding
                        'forward' and 'reverse' suffixes will be applied to individual
                        persistent storage pathstems.
            forwardAttr - label of attribute to bind to sourceDB
            reverseAttr - label of attribute to bind to targetDB for reverse mapping to sourceDB
        """
        if inverseAttr and reverseAttr:
            raise(Exception("Construction Error: Cannot use inverseAttr option with reverseAttr."))
        
        #Mapping objects
        self.Mf = mapping.Mapping(sourceDB=annotDB1,
                            targetDB=annotDB2,
                            filename=filename+"_forward",
                            inverseAttr=inverseAttr, # SPECIFYING WILL RESOLVE 'id' VALUE 
                                               # AND BIND THAT VALUE AS THE ATTRIBUTE
                            mode=mode,
                            multiValue=multiValue,
                            verbose=verbose)

        self.Mr = None
        if reverseAttr != None:
            self.Mr = mapping.Mapping(sourceDB=annotDB2,
                            targetDB=annotDB1,
                            filename=filename+"_reverse",
                            #inverseAttr=None, # SPECIFYING WILL RESOLVE 'id' VALUE 
                                               # AND BIND THAT VALUE AS THE ATTRIBUTE
                            mode=mode,
                            multiValue=multiValue,
                            verbose=verbose)
        
        # Flags
        self._closed = False
        
        # Attributes
        self.forwardAttr = forwardAttr
        self.reverseAttr = reverseAttr
        self.inverseAttr = inverseAttr
        self.resourceString = resourceString        
        
    def __call__(self, sourceObj, targetObj):
        """Wrapper to self.add() method."""
        self.add(sourceObj,targetObj)
    
    def __setitem__(self,sourceObj, targetObj):
        """Wrapper to self.add() method."""
        self.add(sourceObj,targetObj)
        
    def add(self, sourceObj, targetObj):
        """Convenience method to add a mapping between sourceObj and targetObj."""        
        targetList = self.Mf.get(sourceObj, []) # FORWARD
        targetList.append(targetObj)
        self.Mf[sourceObj] = targetList

        if self.Mr != None:        
            sourceList = self.Mr.get(targetObj, []) # REVERSE
            sourceList.append(sourceObj)
            self.Mr[targetObj] = sourceList

    def add_using_iter(self, iter):
        """Convenience method to call an iterator to obtain the source and target objects.
        Requires that the iterator returns a tuple of sourceObj,targetObj
        """
        for (sourceObj,targetObj) in iter:
            self.add(sourceObj,targetObj)

#    def __del__(self):
#        """Wrapper to close() to commit and close mapping resources."""
#        self.close()
        
    def save(self):
        """Wrapper to close() to commit and close mapping resources."""
        self.close()
        
    def commit(self):
        """Wrapper to close() to commit and close mapping resources."""
        self.close()

    def close(self,commitData=True):
        """Close method which performs updating the docstrings and creating the schema objects."""
        print "# Finalizing mapping schema(s)..."
        if self._closed == True:
            return
        
        # UPDATE DOC STRING FOR forward MAPPING
        self.Mf.__doc__ = "Mapping resource (forward) between annotations %s and %s" % (self.Mf.sourceDB._persistent_id,
                                                                                self.Mf.targetDB._persistent_id)
        
        #UPDATE OUR METABASE WITH THE RESOURCE STRING FOR THE MAPPING
        worldbase.add_resource(self.resourceString+"_forward", self.Mf)
        
        # FOR forward MAPPING
        forward_bindAttrs = (self.forwardAttr, self.inverseAttr) # self.inverseAttr is either None or set to an appropriate inverse attribute
        relationF = metabase.OneToManyRelation(self.Mf.sourceDB, self.Mf.targetDB, bindAttrs=forward_bindAttrs)
        relationF.__doc__ = "Mapping schema (forward) between annotations %s and %s" % (self.Mf.sourceDB._persistent_id,
                                                                                self.Mf.targetDB._persistent_id) 
        
        # UPDATE OUR SCHEMA WITH THE RESOURCE STRING FOR THE MAPPING
        worldbase.add_schema(self.resourceString+"_forward", relationF) 
        
        # HANDLE REVERSE MAPPING AND SCHEMA
        relationR = None
        if self.Mr != None:
            # UPDATE DOC STRING FOR reverse MAPPING
            self.Mr.__doc__ = "Mapping resource (reverse) between annotations %s and %s" % (self.Mr.sourceDB._persistent_id,
                                                                                            self.Mr.targetDB._persistent_id)
            
            #UPDATE OUR METABASE WITH THE RESOURCE STRING FOR THE MAPPING
            worldbase.add_resource(self.resourceString+"_reverse", self.Mr)
            
            # FOR reverse MAPPING
            reverse_bindAttrs = (self.reverseAttr, None)
            relationR = metabase.OneToManyRelation(self.Mr.sourceDB, self.Mr.targetDB, bindAttrs=reverse_bindAttrs)
            relationR.__doc__ = "Mapping schema (reverse) between annotations %s and %s" % (self.Mr.sourceDB._persistent_id, # Use self.Mf for consistent
                                                                                            self.Mr.targetDB._persistent_id) # doc strings with forward mapping
            
            # UPDATE OUR SCHEMA WITH THE RESOURCE STRING FOR THE MAPPING
            worldbase.add_schema(self.resourceString+"_reverse", relationR) 

        if(commitData==True):
            print "# Committing to worldbase: (1) %s (2) %s" % (str(self.Mf.__doc__),str(self.Mr.__doc__))
            worldbase.commit()
        
            print "# Closing mapping object(s)"
            # FLUSH MAPPING(S) TO PERSISTENT STORAGE
            self.Mf.close()
            if self.Mr:
                self.Mr.close()
        
            # Set closed flag
            self._closed = True

    
