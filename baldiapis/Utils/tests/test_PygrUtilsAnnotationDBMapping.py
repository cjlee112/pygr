"""Unittests for SequenceSearching module.

"""

import unittest

from pygr import worldbase
from pygr import cnestedlist
from pygr import annotation

from Utils import PygrUtils # AnnotationDBMapping

class Test(unittest.TestCase):
    """Test AnnotationDBMapping functions.

    """

    def setUp(self):
        """Set up some testing sequences and features.
        
        """
        print "# Setting annotation databases, nlmsa and committing to worldbase"

        tuple_attrdict = dict(id=0, start=1, stop=2, orientation=3)
        self.genome = worldbase("Bio.Seq.Genome.HUMAN.hg18")
        
        # annotation db1
        self.annodb1 = annotation.AnnotationDB({}, self.genome,
                                              sliceAttrDict=tuple_attrdict)
        self.annodb1._persistent_id = 'foo1_db'
        
        # set up some test slices in an AnnotationDB
        self.seq_id = "chr1"
        self.annot1 = self.annodb1.new_annotation('A1', (self.seq_id, 200, 300, 1))
        self.annot2 = self.annodb1.new_annotation('B1', (self.seq_id, 100, 150, 1))
        self.annot3 = self.annodb1.new_annotation('C1', (self.seq_id, 50, 75, -1))
        self.annot4 = self.annodb1.new_annotation('D1', (self.seq_id, 400, 500, 1))
        self.annot5 = self.annodb1.new_annotation('E1', (self.seq_id, 600, 700, 1))
        
        # create a nested list from our AnnotationDB
        # these are our "features"
        self.nlmsa1 = cnestedlist.NLMSA(pathstem='test.mapping.foo1', mode='w', pairwiseMode=True)
        
        for k in self.annodb1:
            self.nlmsa1.addAnnotation(self.annodb1[k])
            
        self.nlmsa1.build()

        # annotation db2
        self.annodb2 = annotation.AnnotationDB({}, self.genome,
                                              sliceAttrDict=tuple_attrdict)
        self.annodb2._persistent_id = 'foo2_db'
        
        # set up some test slices in an AnnotationDB
        self.seq_id2 = "chr2"
        self.annot6 = self.annodb2.new_annotation('A2', (self.seq_id2, 200, 300, 1))
        self.annot7 = self.annodb2.new_annotation('B2', (self.seq_id2, 100, 150, 1))
        self.annot8 = self.annodb2.new_annotation('C2', (self.seq_id2, 50, 75, -1))
        self.annot9 = self.annodb2.new_annotation('D2', (self.seq_id2, 400, 500, 1))
        self.annot10 = self.annodb2.new_annotation('E2', (self.seq_id2, 600, 700, 1))
        
        # create a nested list from our AnnotationDB
        # these are our "features"
        self.nlmsa2 = cnestedlist.NLMSA(pathstem='test.mapping.foo2', mode='w', pairwiseMode=True)
        
        for k in self.annodb2:
            self.nlmsa2.addAnnotation(self.annodb2[k])
            
        self.nlmsa2.build()

        # update WORLDBASEPATH
        self.annodb1.__doc__ = 'annodb1 db'
        self.nlmsa1.__doc__ = 'annodb1 nlmsa'

        self.annodb2.__doc__ = 'annodb2 db'
        self.nlmsa2.__doc__ = 'annodb2 nlmsa'

        worldbase.add_resource('Test.Annotations.annodb1_db',self.annodb1)
        worldbase.add_resource('Test.Annotations.annodb2_db',self.annodb2)

        worldbase.add_resource('Test.Annotations.annodb1',self.nlmsa1)
        worldbase.add_resource('Test.Annotations.annodb2',self.nlmsa2)

        worldbase.commit()


    def test_mapping_FR(self):
        """Test the forward mapping.

        >>> from pygr import worldbase
        >>> adb = worldbase('Test.Annotations.annodb1_db')
        >>> a1 = adb['A1']
        >>> adb2 = worldbase('Test.Annotations.annodb2_db')
        >>> a2 = adb2['E2']
        >>> a1 == a2.annotdb1[0]
        True
        
        """

        print '# Create mapping'
        M = PygrUtils.AnnotationDBMapping(self.annodb1,self.annodb2,'test.mapping','test.mapping','annotdb2','annotdb1',mode='nr')        
        M[self.annot1]=self.annot10
        M.close(commitData=True)
        
        print '# Reload recently committed data, eg, mapping'
        worldbase.clear_cache()

        print '# Test forward mapping'
        annodb2 = worldbase('Test.Annotations.annodb2_db')
        a10 = annodb2['E2']
        self.assertEqual(repr(self.annot1), repr(a10.annotdb1[0]))

        print '# Test reverse mapping'
        annodb1 = worldbase('Test.Annotations.annodb1_db')
        a1 = annodb1['A1']
        self.assertEqual(repr(self.annot10), repr(a1.annotdb2[0]))

if __name__ == '__main__':
    unittest.main()
