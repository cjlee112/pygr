import unittest
from nosebase import skip_errors
from pygr import mapping,graphquery


class QuerySuite(unittest.TestCase):
    "Pygr Query tests..."
    def dqcmp(self,datagraph,querygraph,result):
        try:
            g = self.datagraph
        except AttributeError:
            pass
        else:
            g.update(datagraph)
            datagraph = g
        result_kounter = 0
        l = [d.copy() for d in graphquery.GraphQuery(datagraph,querygraph)]
        self.failUnless(len(l)==len(result),'length mismatch')
        l.sort()
        result.sort()
        for i in range(len(l)):
            self.failUnless(l[i]==result[i],'incorrect result')
    def testBasicQuery(self):  # Basic Query Test
        datagraph = {0: {1: None, 2: None, 3: None}, 1: {2:None}, 3: {4: None, 5: None},
                     4: {6: None}, 5: {6: None}, 2: {}, 6: {}}
        querygraph = {0: {1: None, 2: None, 3: None}, 3:{4: None},1:{},2:{},4:{}}
        result = [{0: 0, 1: 1, 2: 2, 3: 3, 4: 4}, {0: 0, 1: 1, 2: 2, 3: 3, 4: 5},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 4}, {0: 0, 1: 2, 2: 1, 3: 3, 4: 5}]
        self.dqcmp(datagraph,querygraph,result) 
    def testCyclicQuery(self): # Test cyclic QG against cyclic DG 
        datagraph = {1:{2:None},2:{3:None},3:{4:None},4:{5:None},5:{2:None}}
        querygraph = {0:{1:None},1:{2:None},2:{4:None},3:{1:None},4:{3:None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 5, 4: 4}]
        self.dqcmp(datagraph,querygraph,result)
    def testCyclicAcyclicQuery(self): # Test cyclic QG against acyclic DG 
        datagraph = {0:{1:None},1:{3:None},5:{3:None},4:{5:None},2:{4:None,1:None},3:{}}
        querygraph = {0:{1:None},1:{3:None},3:{5:None},5:{4:None},4:{2:None},2:{1:None}}
        result = []
        self.dqcmp(datagraph,querygraph,result)
    def testSymmetricQuery(self): # Test symmetrical QG against symmetrical DG
        datagraph = {1:{2:None},2:{3:None,4:None},5:{2:None},3:{},4:{}}
        querygraph = {0:{1:None},1:{2:None},2:{}}
        result = [{0: 1, 1: 2, 2: 3}, {0: 1, 1: 2, 2: 4},
                  {0: 5, 1: 2, 2: 3}, {0: 5, 1: 2, 2: 4}]
        self.dqcmp(datagraph,querygraph,result)
    def testFilteredQuery(self): # Test a filter against a query
        datagraph = {0: {1: None, 2: None, 3: None}, 1: {2: None, 3: None}, 3: {4: None}}
        querygraph = {0:{1:{'filter':lambda toNode,**kw:toNode == 3}},1:{}}
        result = [{0: 0, 1: 3},{0: 1, 1: 3}]
        self.dqcmp(datagraph,querygraph,result)
    def testHeadlessQuery(self): # Test a query with no head nodes
        datagraph = {0:{1:None},1:{2:None},2:{3:None},3:{4:None},4:{1:None}}
        querygraph = {0:{1:None},1:{2:None},2:{3:None},3:{0:None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 4},
                  {0: 2, 1: 3, 2: 4, 3: 1},
                  {0: 3, 1: 4, 2: 1, 3: 2},
                  {0: 4, 1: 1, 2: 2, 3: 3}]
        self.dqcmp(datagraph,querygraph,result)

class MappingSuite(QuerySuite):
    def setUp(self):
        self.datagraph = mapping.dictGraph()
    def testGraphDict(self):
        datagraph = self.datagraph
        datagraph += 1 
        datagraph[1] += 2
        results = {1: {2: None}, 2: {}}
        self.failUnless(datagraph == results, 'incorrect result')
    def testNodeDel(self): 
        datagraph = self.datagraph
        datagraph += 1
        datagraph += 2 
        datagraph[2] += 3
        datagraph -= 1
        results = {2: {3: None}, 3: {}}
        self.failUnless(datagraph == results, 'incorrect result')     
    def testDelRaise(self):
        datagraph = self.datagraph
        datagraph += 1
        datagraph += 2
        datagraph[2] += 3
        error = 0
        try:
            for i in range(0,2):
                datagraph -= 3
        except KeyError:
            error = 1 
        self.failUnless(error,'incorrect result')
    def testSetItemRaise(self):
        datagraph = self.datagraph
        datagraph += 1
        try:
            datagraph[1] = 2
        except ValueError:
            error = 1
        self.failUnless(error,'incorrect result')
    def testGraphEdges(self): 
        datagraph = self.datagraph
        graphvals = {1:{2:None},2:{3:None,4:None},5:{2:None},3:{},4:{}}
        edge_list = [[1, 2,None], [2, 3,None], [2, 4,None], [5, 2,None]]
        for i in graphvals:
            datagraph += i
            for n in graphvals[i].keys():
                datagraph[i] += n
        edge_results = []
        for e in datagraph.edges():
            edge_results.append(e)
        edge_results.sort()
        edge_results = [list(t) for t in edge_results]
        edge_list.sort()
        print 'edge_results:',edge_results
        self.failUnless(edge_results == edge_list, 'incorrect result')        


class GraphSuite(MappingSuite):
    'run same tests on mapping.Graph class'
    def setUp(self):
        self.datagraph = mapping.Graph()

class GraphShelveSuite(MappingSuite):
    'run same tests on mapping.Graph class'
    def setUp(self):
        from nosebase import TempDir
        tmp = TempDir()
        self.datagraph = mapping.Graph(filename=tmp.subfile('mygraph'),
                                       intKeys=True)
        self.tempdir = tmp # KEEP BOUND SO NOT DELETED UNTIL THIS TEST COMPLETED

class SQLGraphSuite(MappingSuite):
    'run same tests on mapping.SQLGraph class'
    @skip_errors(ImportError)
    def setUp(self):
        from pygr import sqlgraph
        import MySQLdb # TEST WILL BE SKIPPED IF UNAVAILABLE
        try:
            self.datagraph = sqlgraph.SQLGraph('test.dumbo_foo_test',
                                               createTable=dict(source_id='int',
                                                                target_id='int',
                                                                edge_id='int'))
        except MySQLdb.MySQLError:
            raise ImportError # NO SERVER, DATABASE OR PRIVILEGES? SKIP TESTS.
    def tearDown(self):
        self.datagraph.cursor.execute('drop table test.dumbo_foo_test')

