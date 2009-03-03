"""
Test some of the basics underpinning the graph system.
"""

import os, unittest
from testlib import testutil
from pygr import mapping, graphquery, sqlgraph
import pygr.Data

class Query_Test(unittest.TestCase):
    "Pygr Query tests"

    def dqcmp(self, datagraph, querygraph, result):
        try:
            g = self.datagraph
        except AttributeError:
            pass
        else:
            g.update(datagraph)
            datagraph = g
            
        l = [ d.copy() for d in graphquery.GraphQuery(datagraph, querygraph) ]
        assert len(l) == len(result), 'length mismatch'
        l.sort()
        result.sort()
        for i in range(len(l)):
            assert l[i] == result[i], 'incorrect result'
    
    def test_basicquery_test(self):
        "Basic query"
        datagraph = {0: {1: None, 2: None, 3: None},
                     1: {2: None}, 3: {4: None, 5: None},
                     4: {6: None}, 5: {6: None}, 2: {}, 6: {}}
        querygraph = {0: {1: None, 2: None, 3: None},
                      3:{4: None},1:{},2:{},4:{}}
        result = [{0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
                  {0: 0, 1: 1, 2: 2, 3: 3, 4: 5},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 4},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 5}]
        
        self.dqcmp(datagraph, querygraph, result) 
    
    def test_cyclicquery(self): 
        "Cyclic QG against cyclic DG @CTB comment?"
        datagraph = { 1 :{2:None}, 2:{3:None}, 3:{4:None}, 4:{5:None},
                      5:{2:None}}
        querygraph = {0:{1:None}, 1:{2:None}, 2:{4:None}, 3:{1:None},
                      4:{3:None}}
        result = [ {0: 1, 1: 2, 2: 3, 3: 5, 4: 4} ]
        self.dqcmp(datagraph, querygraph, result)
    
    def test_cyclicacyclicquery(self):
        "Cyclic QG against acyclic DG"
        datagraph = {0:{1:None}, 1:{3:None}, 5:{3:None}, 4:{5:None},
                     2:{4:None,1:None}, 3:{}}
        querygraph = {0:{1:None}, 1:{3:None}, 3:{5:None}, 5:{4:None},
                      4:{2:None}, 2:{1:None}}
        result = []
        self.dqcmp(datagraph,querygraph,result)
    
    def test_symmetricquery_test(self):
        "Symmetrical QG against symmetrical DG"
        datagraph = {1:{2:None},2:{3:None,4:None},5:{2:None},3:{},4:{}}
        querygraph = {0:{1:None},1:{2:None},2:{}}
        result = [{0: 1, 1: 2, 2: 3}, {0: 1, 1: 2, 2: 4},
                  {0: 5, 1: 2, 2: 3}, {0: 5, 1: 2, 2: 4}]
        self.dqcmp(datagraph,querygraph,result)

    def test_filteredquery(self):
        "Test a filter against a query"
        datagraph = {0: {1: None, 2: None, 3: None}, 1: {2: None, 3: None},
                     3: {4: None}}
        querygraph = {0:{1:{'filter':lambda toNode,**kw:toNode == 3}},1:{}}
        result = [{0: 0, 1: 3},{0: 1, 1: 3}]
        self.dqcmp(datagraph,querygraph,result)

    def test_headlessquery(self):
        "Test a query with no head nodes"
        datagraph = {0:{1:None},1:{2:None},2:{3:None},3:{4:None},4:{1:None}}
        querygraph = {0:{1:None},1:{2:None},2:{3:None},3:{0:None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 4},
                  {0: 2, 1: 3, 2: 4, 3: 1},
                  {0: 3, 1: 4, 2: 1, 3: 2},
                  {0: 4, 1: 1, 2: 2, 3: 3}]
        self.dqcmp(datagraph,querygraph,result)

class Mapping_Test(Query_Test):
    "Tests mappings"

    def setUp(self):
        self.datagraph = mapping.dictGraph()

    def test_graphdict(self):
        "Graph dictionary"
        datagraph = self.datagraph
        datagraph += 1 
        datagraph[1] += 2
        results = {1: {2: None}, 2: {}}
        assert datagraph == results, 'incorrect result'
    
    def test_nodedel(self): 
        "Node deletion"
        datagraph = self.datagraph
        datagraph += 1
        datagraph += 2 
        datagraph[2] += 3
        datagraph -= 1
        results = {2: {3: None}, 3: {}}
        assert datagraph == results, 'incorrect result'
    
    def test_delraise(self):
        "Delete raise"
        datagraph = self.datagraph
        datagraph += 1
        datagraph += 2
        datagraph[2] += 3
        try:
            for i in range(0,2):
                datagraph -= 3
            raise ValueError('failed to catch bad node deletion attempt')
        except KeyError:
            pass # THIS IS THE CORRECT RESULT

    def test_setitemraise(self):
        "Setitemraise"
        datagraph = self.datagraph
        datagraph += 1
        try:
            datagraph[1] = 2
            raise KeyError('failed to catch bad setitem attempt')
        except ValueError:
            pass # THIS IS THE CORRECT RESULT

    def test_graphedges(self): 
        "Graphedges"
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
        #print 'edge_results:',edge_results
        assert edge_results == edge_list, 'incorrect result'        

class Graph_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):
        self.datagraph = mapping.Graph()

class GraphShelve_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):
        
        tmp = testutil.TempDir('graphshelve-test')
        filename = tmp.subfile() # needs a random name each time
        self.datagraph = mapping.Graph(filename=filename, intKeys=True)
        
    def tearDown(self):
        self.datagraph.close()

 
class SQLGraph_Test(Mapping_Test):
    "Runs the same tests on mapping.SQLGraph class"
    dbname = 'test.dumbo_foo_test'

    def setUp(self):
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph(self.dbname, dropIfExists=True,
                                           createTable=createOpts)
    
    def tearDown(self):
        self.datagraph.cursor.execute('drop table if exists %s' % self.dbname)

class SQLiteGraph_Test(Mapping_Test):
    'run same tests on mapping.SQLGraph class'
    def setUp(self):
        from pygr import sqlgraph
        import sqlite3 # test will be skipped if unavailable
        self.dbfile = testutil.tempdatafile('sqlitegraph_test.db')
        self.tearDown(False) # make sure db file not already present
        self.sqlite_db = sqlite3.connect(self.dbfile)
        self.cursor = self.sqlite_db.cursor()
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph('testgraph',
                                           cursor=self.cursor,
                                           dropIfExists=True,
                                           createTable=createOpts)
    def tearDown(self, closeConnection=True):
        if closeConnection:
            self.cursor.close() # close the cursor
            self.sqlite_db.close() # close the connection
        try:
            os.remove(self.dbfile)
        except OSError:
            pass

class Splicegraph_Test(unittest.TestCase):
    
    def setUp(self):
        self.sg = pygr.Data.Bio.Annotation.ASAP2.Isoform.HUMAN.\
                  hg17.splicegraph()
    
    def exonskip_megatest(self):
        'perform exon skip query'
        query = {0:{1:None,2:None},1:{2:None},2:{}}
        gq = graphquery.GraphQuery(self.sg, query)
        l = list(gq)
        assert len(l) == 11546, 'test exact size of exonskip set'

def get_suite():
    "Returns the testsuite"

    tests  = [ 
        Query_Test, 
        Mapping_Test,
        Graph_Test, 
        GraphShelve_Test,
    ]

    # deal with the mysql tests
    if testutil.mysql_enabled():
        tests.append(SQLGraph_Test)    
    else:
        testutil.info('*** skipping MySql version of SQLGraph test')
    if testutil.sqlite_enabled():
        tests.append(SQLiteGraph_Test)
        
    return testutil.make_suite(tests)

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)
