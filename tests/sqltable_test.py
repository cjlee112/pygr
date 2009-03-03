import unittest, string
from testlib import testutil, logger
from pygr.sqlgraph import SQLTable,getNameCursor,MapView,GraphView,DBServerInfo

class SQLTable_Test( unittest.TestCase ):

    def setUp(self):
        
        createTable = """\
        CREATE TABLE test.sqltable_test (primary_id INTEGER PRIMARY KEY AUTO_INCREMENT, seq_id TEXT, start INTEGER, stop INTEGER)
        """
        
        self.db = SQLTable('test.sqltable_test', dropIfExists=True, createTable=createTable)
        
        self.sourceDB = SQLTable('test.sqltable_join1',
                                 dropIfExists=True, createTable="""\
        CREATE TABLE test.sqltable_join1 (my_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """)

        self.targetDB = SQLTable('test.sqltable_join2',
                                 dropIfExists=True, createTable="""\
        CREATE TABLE test.sqltable_join2 (third_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """)

        sql = """
            INSERT INTO test.sqltable_test (seq_id, start, stop) VALUES ('seq1', 0, 10)
            INSERT INTO test.sqltable_test (seq_id, start, stop) VALUES ('seq2', 5, 15)
            INSERT INTO test.sqltable_join1 VALUES (2,'seq2')
            INSERT INTO test.sqltable_join1 VALUES (3,'seq3')
            INSERT INTO test.sqltable_join1 VALUES (4,'seq4')
            INSERT INTO test.sqltable_join2 VALUES (7, 'seq2')
            INSERT INTO test.sqltable_join2 VALUES (99, 'seq3')
            INSERT INTO test.sqltable_join2 VALUES (6, 'seq4')
            INSERT INTO test.sqltable_join2 VALUES (8, 'seq4')
        """
        
        # strip and filter into lines
        lines = map(string.strip, sql.splitlines() )
        lines = filter(None, lines)
        
        # insert sql lines into the database
        for line in lines:
            self.db.cursor.execute( line )

        self.EQ = self.assertEqual

    def tearDown(self):
        "Drop test tables"
        tables = [ 'sqltable_test', 'sqltable_join1', 'sqltable_join2' ]
        for table in tables:
            self.db.cursor.execute('drop table if exists test.%s' % table )    
        
    def test_keys(self):
        "Test keys"

        k = self.db.keys()
        k.sort()
        self.EQ( k, [1, 2])

    def test_contains(self):
        "Test dictionary interface"

        # contains
        self.assertTrue( 1 in self.db )
        self.assertTrue( 2 in self.db )
        self.assertTrue( 'foo' not in self.db )

        # has key
        self.assertTrue( self.db.has_key(1) )
        self.assertTrue( self.db.has_key(2) )
        self.assertTrue( not self.db.has_key('foo') )

        # get tests            
        self.assertTrue( self.db.get('foo') is None )
        self.EQ ( self.db.get(1), self.db[1] )
        self.EQ ( self.db.get(2), self.db[2] )

    def test_iteration(self):
        "Test iteration"
        # iteration
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        self.EQ( i, [1, 2] )

        # iterkeys
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        self.EQ( kk, ik )

        # itervalues
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        self.EQ( kv, iv)

        # iteritems
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        self.EQ( ki, ii )

    ### @CTB need to test write access
    def test_mapview(self):
        "Mapview test"

        m = MapView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM test.sqltable_join1 t1, test.sqltable_join2 t2
           WHERE t1.my_id=%s and t1.other_id=t2.other_id
        """, cursor=self.db.cursor)
        self.EQ( m[self.sourceDB[2]], self.targetDB[7] )
        self.EQ( m[self.sourceDB[3]], self.targetDB[99] )
        self.assertTrue ( self.sourceDB[2] in m )
    
    def test_graphview(self):
        "Basic Graphview test"
        m = GraphView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM test.sqltable_join1 t1, test.sqltable_join2 t2
           WHERE t1.my_id=%s and t1.other_id=t2.other_id
        """, cursor=self.db.cursor)
        d = m[self.sourceDB[4]]
        self.EQ(  len(d), 2 )
        self.assertTrue( self.targetDB[6] in d and self.targetDB[8] in d )
        self.assertTrue( self.sourceDB[2] in m )
        
        
class Ensembl_Test(unittest.TestCase):
     
    def setUp(self):
        # test will be skipped if mysql module or ensembldb server unavailable

        logger.info('accessing ensebledb.ensembl.org')
        conn = DBServerInfo(host='ensembldb.ensembl.org', user='anonymous',
                                passwd='')
        translationDB = SQLTable('homo_sapiens_core_47_36i.translation',
                                     serverInfo=conn)
        exonDB = SQLTable('homo_sapiens_core_47_36i.exon', serverInfo=conn)
        
        sql_statement = '''SELECT t3.exon_id FROM
homo_sapiens_core_47_36i.translation AS tr,
homo_sapiens_core_47_36i.exon_transcript AS t1,
homo_sapiens_core_47_36i.exon_transcript AS t2,
homo_sapiens_core_47_36i.exon_transcript AS t3 WHERE tr.translation_id = %s
AND tr.transcript_id = t1.transcript_id AND t1.transcript_id =
t2.transcript_id AND t2.transcript_id = t3.transcript_id AND t1.exon_id =
tr.start_exon_id AND t2.exon_id = tr.end_exon_id AND t3.rank >= t1.rank AND
t3.rank <= t2.rank ORDER BY t3.rank
            '''
        self.translationExons = GraphView(translationDB, exonDB,
                                              sql_statement, serverInfo=conn)
        self.translation = translationDB[15121]
    
    def test_orderBy(self):
        "Ensemble access, test order by"
        'test issue 53: ensure that the ORDER BY results are correct'
        exons = self.translationExons[self.translation] # do the query
        result = [e.id for e in exons]
        correct = [95160,95020,95035,95050,95059,95069,95081,95088,95101,
                   95110,95172]
        self.assertEqual( result, correct) # make sure the exact order matches

def get_suite():
    "Returns the testsuite"

    tests = []

    # detect mysql
    if testutil.mysql_enabled():
        tests.append(  SQLTable_Test ) 
        tests.append(  Ensembl_Test ) 
    else:
        testutil.info('*** skipping SQLTable_Test' )

    return testutil.make_suite( tests )

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run( suite )
