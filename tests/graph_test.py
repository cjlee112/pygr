"""
Test some of the basics underpinning the graph system.
"""

import os
import unittest

from testlib import testutil, PygrTestProgram, SkipTest
from pygr import mapping, graphquery, sqlgraph


class Node(object):

    def __init__(self, id):
        self.id = id


class Query_Test(unittest.TestCase):
    "Pygr Query tests"

    def get_node(self, k):
        try:
            db = self.nodeDB
        except AttributeError:
            return k
        else:
            try:
                return db[k]
            except KeyError:
                db[k] = Node(k)
                return db[k]

    def node_graph(self, g):
        try:
            db = self.nodeDB
        except AttributeError:
            return g
        out = {}
        for k, e in g.items():
            k = self.get_node(k)
            d = out.setdefault(k, {})
            for dest, edge in e.items():
                d[self.get_node(dest)] = edge
        return out

    def node_list(self, l):
        try:
            db = self.nodeDB
        except AttributeError:
            return l
        out = []
        for k in l:
            out.append(self.get_node(k))
        return out

    def node_result(self, r):
        try:
            db = self.nodeDB
        except AttributeError:
            return r
        l = []
        for d in r:
            d2 = {}
            for k, v in d.items():
                d2[k] = self.get_node(v)
            l.append(d2)
        return l

    def update_graph(self, datagraph):
        try:
            g = self.datagraph
        except AttributeError:
            return datagraph
        else:
            g.update(datagraph)
            return g

    def dqcmp(self, datagraph, querygraph, result):
        datagraph = self.update_graph(self.node_graph(datagraph))
        l = [d.copy() for d in graphquery.GraphQuery(datagraph, querygraph)]
        assert len(l) == len(result), 'length mismatch'
        l.sort()
        result = self.node_result(result)
        result.sort()
        for i in range(len(l)):
            assert l[i] == result[i], 'incorrect result'

    def test_basicquery_test(self):
        "Basic query"
        datagraph = {0: {1: None, 2: None, 3: None},
                     1: {2: None}, 3: {4: None, 5: None},
                     4: {6: None}, 5: {6: None}, 2: {}, 6: {}}
        querygraph = {0: {1: None, 2: None, 3: None},
                      3: {4: None}, 1: {}, 2: {}, 4: {}}
        result = [{0: 0, 1: 1, 2: 2, 3: 3, 4: 4},
                  {0: 0, 1: 1, 2: 2, 3: 3, 4: 5},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 4},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 5}]

        self.dqcmp(datagraph, querygraph, result)

    def test_iter(self):
        'test basic iteration'
        g = {0: {1: None, 2: None, 3: None},
             1: {2: None}, 3: {4: None, 5: None},
             4: {6: None}, 5: {6: None}, 2: {}, 6: {}}
        datagraph = self.update_graph(self.node_graph(g))
        l = list(iter(datagraph))
        l.sort()
        result = self.node_list([0, 1, 2, 3, 4, 5, 6])
        result.sort()
        assert l == result

    def test_cyclicquery(self):
        "Cyclic QG against cyclic DG @CTB comment?"
        datagraph = {1: {2: None}, 2: {3: None}, 3: {4: None}, 4: {5: None},
                      5: {2: None}}
        querygraph = {0: {1: None}, 1: {2: None}, 2: {4: None}, 3: {1: None},
                      4: {3: None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 5, 4: 4}]
        self.dqcmp(datagraph, querygraph, result)

    def test_cyclicacyclicquery(self):
        "Cyclic QG against acyclic DG"
        datagraph = {0: {1: None}, 1: {3: None}, 5: {3: None}, 4: {5: None},
                     2: {4: None, 1: None}, 3: {}}
        querygraph = {0: {1: None}, 1: {3: None}, 3: {5: None}, 5: {4: None},
                      4: {2: None}, 2: {1: None}}
        result = []
        self.dqcmp(datagraph, querygraph, result)

    def test_symmetricquery_test(self):
        "Symmetrical QG against symmetrical DG"
        datagraph = {1: {2: None}, 2: {3: None, 4: None}, 5: {2: None},
                     3: {}, 4: {}}
        querygraph = {0: {1: None}, 1: {2: None}, 2: {}}
        result = [{0: 1, 1: 2, 2: 3}, {0: 1, 1: 2, 2: 4},
                  {0: 5, 1: 2, 2: 3}, {0: 5, 1: 2, 2: 4}]
        self.dqcmp(datagraph, querygraph, result)

    def test_filteredquery(self):
        "Test a filter against a query"
        datagraph = {0: {1: None, 2: None, 3: None}, 1: {2: None, 3: None},
                     3: {4: None}}
        querygraph = {0: {1: {'filter': lambda toNode, **kw:
                              toNode == self.get_node(3)}}, 1: {}}
        result = [{0: 0, 1: 3}, {0: 1, 1: 3}]
        self.dqcmp(datagraph, querygraph, result)

    def test_headlessquery(self):
        "Test a query with no head nodes"
        datagraph = {0: {1: None}, 1: {2: None}, 2: {3: None}, 3: {4: None},
                     4: {1: None}}
        querygraph = {0: {1: None}, 1: {2: None}, 2: {3: None}, 3: {0: None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 4},
                  {0: 2, 1: 3, 2: 4, 3: 1},
                  {0: 3, 1: 4, 2: 1, 3: 2},
                  {0: 4, 1: 1, 2: 2, 3: 3}]
        self.dqcmp(datagraph, querygraph, result)


class Mapping_Test(Query_Test):
    "Tests mappings"

    def setUp(self):
        self.datagraph = mapping.dictGraph()

    def test_graphdict(self):
        "Graph dictionary"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        datagraph[self.get_node(1)] += self.get_node(2)
        results = {1: {2: None}, 2: {}}
        results = self.node_graph(results)
        assert datagraph == results, 'incorrect result'

    def test_nodedel(self):
        "Node deletion"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        datagraph += self.get_node(2)
        datagraph[self.get_node(2)] += self.get_node(3)
        datagraph -= self.get_node(1)
        results = {2: {3: None}, 3: {}}
        results = self.node_graph(results)
        assert datagraph == results, 'incorrect result'

    def test_delraise(self):
        "Delete raise"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        datagraph += self.get_node(2)
        datagraph[self.get_node(2)] += self.get_node(3)
        try:
            for i in range(0, 2):
                datagraph -= self.get_node(3)
            raise ValueError('failed to catch bad node deletion attempt')
        except KeyError:
            pass # THIS IS THE CORRECT RESULT

    def test_setitemraise(self):
        "Setitemraise"
        datagraph = self.datagraph
        datagraph += self.get_node(1)
        try:
            datagraph[self.get_node(1)] = self.get_node(2)
            raise KeyError('failed to catch bad setitem attempt')
        except ValueError:
            pass # THIS IS THE CORRECT RESULT

    def test_graphedges(self):
        "Graphedges"
        datagraph = self.datagraph
        graphvals = {1: {2: None}, 2: {3: None, 4: None}, 5: {2: None},
                     3: {}, 4: {}}
        graphvals = self.node_graph(graphvals)
        edge_list = [[self.get_node(1), self.get_node(2), None],
                     [self.get_node(2), self.get_node(3), None],
                     [self.get_node(2), self.get_node(4), None],
                     [self.get_node(5), self.get_node(2), None]]
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
        #print 'edge_results:', edge_results
        assert edge_results == edge_list, 'incorrect result'


class Graph_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):
        self.datagraph = mapping.Graph()


class Graph_DB_Test(Mapping_Test):
    "test mapping.Graph with sourceDB, targetDB but no edgeDB"

    def setUp(self):
        self.nodeDB = {1: Node(1), 2: Node(2)}
        self.datagraph = mapping.Graph(sourceDB=self.nodeDB,
                                       targetDB=self.nodeDB)

    def test_no_edge_db(self):
        'test behavior with no edgeDB'
        self.datagraph += self.nodeDB[1] # add node
        self.datagraph[self.nodeDB[1]][self.nodeDB[2]] = 3 # add edge

        assert self.datagraph[self.nodeDB[1]][self.nodeDB[2]] == 3


class GraphShelve_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):

        tmp = testutil.TempDir('graphshelve-test')
        filename = tmp.subfile() # needs a random name each time
        self.datagraph = mapping.Graph(filename=filename, intKeys=True)

    def tearDown(self):
        self.datagraph.close()


class GraphShelve_DB_Test(Mapping_Test):
    "Run same tests on mapping.Graph class"

    def setUp(self):
        self.nodeDB = {}
        tmp = testutil.TempDir('graphshelve-test')
        filename = tmp.subfile() # needs a random name each time
        self.datagraph = mapping.Graph(sourceDB=self.nodeDB,
                                       targetDB=self.nodeDB,
                                       filename=filename, intKeys=True)

    def tearDown(self):
        self.datagraph.close()


class SQLGraph_Test(Mapping_Test):
    "Runs the same tests on mapping.SQLGraph class"
    dbname = 'test.dumbo_foo_test'

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL")

        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph(self.dbname, dropIfExists=True,
                                           createTable=createOpts)

    def tearDown(self):
        self.datagraph.cursor.execute('drop table if exists %s' % self.dbname)


class SQLGraph_DB_Test(Mapping_Test):
    "Runs the same tests on mapping.SQLGraph class"
    dbname = 'test.dumbo_foo_test'

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL")

        self.nodeDB = {}
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph(self.dbname, dropIfExists=True,
                                           createTable=createOpts,
                                           sourceDB=self.nodeDB,
                                           targetDB=self.nodeDB)

    def tearDown(self):
        self.datagraph.cursor.execute('drop table if exists %s' % self.dbname)


class SQLiteGraph_Test(testutil.SQLite_Mixin, Mapping_Test):
    'run same tests on mapping.SQLGraph class using sqlite'

    def sqlite_load(self):
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph('testgraph',
                                           serverInfo=self.serverInfo,
                                           dropIfExists=True,
                                           createTable=createOpts)


class SQLiteGraph_DB_Test(testutil.SQLite_Mixin, Mapping_Test):
    'run same tests on mapping.SQLGraph class using sqlite'

    def sqlite_load(self):
        self.nodeDB = {}
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        self.datagraph = sqlgraph.SQLGraph('testgraph',
                                           serverInfo=self.serverInfo,
                                           dropIfExists=True,
                                           createTable=createOpts,
                                           sourceDB=self.nodeDB,
                                           targetDB=self.nodeDB)

# test currently unused, requires access to leelab data
## from pygr import worldbase
## class Splicegraph_Test(unittest.TestCase):

##     def setUp(self):
##         self.sg = worldbase.Bio.Annotation.ASAP2.Isoform.HUMAN.\
##                   hg17.splicegraph()

##     def exonskip_megatest(self):
##         'perform exon skip query'
##         query = {0:{1:None,2:None},1:{2:None},2:{}}
##         gq = graphquery.GraphQuery(self.sg, query)
##         l = list(gq)
##         assert len(l) == 11546, 'test exact size of exonskip set'

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
