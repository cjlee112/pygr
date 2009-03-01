import pygrtest_common
from nosebase import skip_errors
from pygr import mapping,graphquery


class Query_Test(object):
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
        assert len(l)==len(result),'length mismatch'
        l.sort()
        result.sort()
        for i in range(len(l)):
            assert l[i]==result[i],'incorrect result'
    def basicquery_test(self):  # Basic Query Test
        datagraph = {0: {1: None, 2: None, 3: None}, 1: {2:None}, 3: {4: None, 5: None},
                     4: {6: None}, 5: {6: None}, 2: {}, 6: {}}
        querygraph = {0: {1: None, 2: None, 3: None}, 3:{4: None},1:{},2:{},4:{}}
        result = [{0: 0, 1: 1, 2: 2, 3: 3, 4: 4}, {0: 0, 1: 1, 2: 2, 3: 3, 4: 5},
                  {0: 0, 1: 2, 2: 1, 3: 3, 4: 4}, {0: 0, 1: 2, 2: 1, 3: 3, 4: 5}]
        self.dqcmp(datagraph,querygraph,result) 
    def cyclicquery_test(self): # Test cyclic QG against cyclic DG 
        datagraph = {1:{2:None},2:{3:None},3:{4:None},4:{5:None},5:{2:None}}
        querygraph = {0:{1:None},1:{2:None},2:{4:None},3:{1:None},4:{3:None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 5, 4: 4}]
        self.dqcmp(datagraph,querygraph,result)
    def cyclicacyclicquery_test(self): # Test cyclic QG against acyclic DG 
        datagraph = {0:{1:None},1:{3:None},5:{3:None},4:{5:None},2:{4:None,1:None},3:{}}
        querygraph = {0:{1:None},1:{3:None},3:{5:None},5:{4:None},4:{2:None},2:{1:None}}
        result = []
        self.dqcmp(datagraph,querygraph,result)
    def symmetricquery_test(self): # Test symmetrical QG against symmetrical DG
        datagraph = {1:{2:None},2:{3:None,4:None},5:{2:None},3:{},4:{}}
        querygraph = {0:{1:None},1:{2:None},2:{}}
        result = [{0: 1, 1: 2, 2: 3}, {0: 1, 1: 2, 2: 4},
                  {0: 5, 1: 2, 2: 3}, {0: 5, 1: 2, 2: 4}]
        self.dqcmp(datagraph,querygraph,result)
    def filteredquery_test(self): # Test a filter against a query
        datagraph = {0: {1: None, 2: None, 3: None}, 1: {2: None, 3: None}, 3: {4: None}}
        querygraph = {0:{1:{'filter':lambda toNode,**kw:toNode == 3}},1:{}}
        result = [{0: 0, 1: 3},{0: 1, 1: 3}]
        self.dqcmp(datagraph,querygraph,result)
    def headlessquery_test(self): # Test a query with no head nodes
        datagraph = {0:{1:None},1:{2:None},2:{3:None},3:{4:None},4:{1:None}}
        querygraph = {0:{1:None},1:{2:None},2:{3:None},3:{0:None}}
        result = [{0: 1, 1: 2, 2: 3, 3: 4},
                  {0: 2, 1: 3, 2: 4, 3: 1},
                  {0: 3, 1: 4, 2: 1, 3: 2},
                  {0: 4, 1: 1, 2: 2, 3: 3}]
        self.dqcmp(datagraph,querygraph,result)

class Mapping_Test(Query_Test):
    def setup(self):
        self.datagraph = mapping.dictGraph()
    def graphdict_test(self):
        datagraph = self.datagraph
        datagraph += 1 
        datagraph[1] += 2
        results = {1: {2: None}, 2: {}}
        assert datagraph == results, 'incorrect result'
    def nodedel_test(self): 
        datagraph = self.datagraph
        datagraph += 1
        datagraph += 2 
        datagraph[2] += 3
        datagraph -= 1
        results = {2: {3: None}, 3: {}}
        assert datagraph == results, 'incorrect result'
    def delraise_test(self):
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
    def setitemraise_test(self):
        datagraph = self.datagraph
        datagraph += 1
        try:
            datagraph[1] = 2
            raise KeyError('failed to catch bad setitem attempt')
        except ValueError:
            pass # THIS IS THE CORRECT RESULT
    def graphedges_test(self): 
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
        assert edge_results == edge_list, 'incorrect result'        


class Graph_Test(Mapping_Test):
    'run same tests on mapping.Graph class'
    def setup(self):
        self.datagraph = mapping.Graph()

class GraphShelve_Test(Mapping_Test):
    'run same tests on mapping.Graph class'
    def setup(self):
        from nosebase import TempDir
        tmp = TempDir()
        self.datagraph = mapping.Graph(filename=tmp.subfile('mygraph'),
                                       intKeys=True)
        self.tempdir = tmp # KEEP BOUND SO NOT DELETED UNTIL THIS TEST COMPLETED
    def teardown(self):
        self.datagraph.close() # close shelve before deleting directory
        self.tempdir.__del__() # FORCE IT TO DELETE TEMPORARY DIRECTORY

class SQLGraph_Test(Mapping_Test):
    'run same tests on mapping.SQLGraph class'
    @skip_errors(ImportError)
    def setup(self):
        from pygr import sqlgraph
        import MySQLdb # test will be skipped if unavailable
        createOpts = dict(source_id='int', target_id='int', edge_id='int')
        try:
            self.datagraph = sqlgraph.SQLGraph('test.dumbo_foo_test',
                                               dropIfExists=True,
                                               createTable=createOpts)
        except MySQLdb.MySQLError:
            tempcurs = sqlgraph.getNameCursor()[1]
            try: # hmm, maybe need to create the test database
                tempcurs.execute('create database if not exists test')
                self.datagraph = sqlgraph.SQLGraph('test.dumbo_foo_test',
                                                   dropIfExists=True,
                                                   createTable=createOpts)
            except MySQLdb.MySQLError: # no server, database or privileges?
                print """The MySQL 'test' database doesn't exist and/or can't be
                created or accessed on this account. This test will be skipped
                """
                raise ImportError #  skip tests.
    def teardown(self):
        self.datagraph.cursor.execute('drop table if exists test.dumbo_foo_test')


class Splicegraph_Test(object):
    @skip_errors(KeyError)
    def setup(self):
        import pygr.Data
        self.sg = pygr.Data.Bio.Annotation.ASAP2.Isoform.HUMAN.hg17.splicegraph()
    def exonskip_megatest(self):
        'perform exon skip query'
        from pygr import graphquery
        query = {0:{1:None,2:None},1:{2:None},2:{}}
        gq = graphquery.GraphQuery(self.sg,query)
        l = list(gq)
        assert len(l)==11546,'test exact size of exonskip set'
