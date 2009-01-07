import pygrtest_common
from nosebase import skip_errors
from pygr.sqlgraph import SQLTable,getNameCursor,MapView,GraphView,DBServerInfo

class SQLTable_Test(object):
    @skip_errors(ImportError)
    def setup(self):
        # test will be skipped if unavailable
        import MySQLdb
        
        createTable = """\
        CREATE TABLE test.sqltable_test (primary_id INTEGER PRIMARY KEY AUTO_INCREMENT, seq_id TEXT, start INTEGER, stop INTEGER)
        """
        
        try:
            self.db = SQLTable('test.sqltable_test',
                               dropIfExists=True,
                               createTable=createTable)
        except MySQLdb.MySQLError:
            tempcurs = getNameCursor()[1]
            try: # hmm, maybe need to create the test database?
                tempcurs.execute('create database if not exists test')
                self.db = SQLTable('test.sqltable_test',
                                   dropIfExists=True,
                                   createTable=createTable)
            except MySQLdb.MySQLError: # no server, database or privileges?
                print """\
                The MySQL 'test' database doesn't exist and/or can't be
                created or accessed on this account. This test will be skipped.
                """
                raise ImportError #  skip tests.

        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_test (seq_id, start, stop)
              VALUES ('seq1', 0, 10)
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_test (seq_id, start, stop)
              VALUES ('seq2', 5, 15)
        """)
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
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_join1 VALUES (2,'seq2')
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_join1 VALUES (3,'seq3')
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_join1 VALUES (4,'seq4')
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_join2 VALUES (7, 'seq2')
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_join2 VALUES (99, 'seq3')
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_join2 VALUES (6, 'seq4')
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqltable_join2 VALUES (8, 'seq4')
        """)
    def teardown(self):
        self.db.cursor.execute('drop table if exists test.sqltable_test')
        self.db.cursor.execute('drop table if exists test.sqltable_join1')
        self.db.cursor.execute('drop table if exists test.sqltable_join2')

    def keys_test(self):
        k = self.db.keys()
        k.sort()
        assert k == [1, 2]
    def contains_test(self):
        assert 1 in self.db
        assert 2 in self.db
        assert 'foo' not in self.db
    def has_key_test(self):
        assert self.db.has_key(1)
        assert self.db.has_key(2)
        assert not self.db.has_key('foo')
    def get_test(self):
        assert self.db.get('foo') is None
        assert self.db.get(1) == self.db[1]
        assert self.db.get(2) == self.db[2]
    def items_test(self):
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == [1, 2]
    def iterkeys_test(self):
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik
    def itervalues_test(self):
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv
    def iteritems_test(self):
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii

    ### @CTB need to test write access
    def mapview_test(self):
        m = MapView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM test.sqltable_join1 t1, test.sqltable_join2 t2
           WHERE t1.my_id=%s and t1.other_id=t2.other_id
        """, cursor=self.db.cursor)
        assert m[self.sourceDB[2]] == self.targetDB[7]
        assert m[self.sourceDB[3]] == self.targetDB[99]
        assert self.sourceDB[2] in m
    def graphview_test(self):
        m = GraphView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM test.sqltable_join1 t1, test.sqltable_join2 t2
           WHERE t1.my_id=%s and t1.other_id=t2.other_id
        """, cursor=self.db.cursor)
        d = m[self.sourceDB[4]]
        assert len(d) == 2
        assert self.targetDB[6] in d and self.targetDB[8] in d
        assert self.sourceDB[2] in m
        
        
class GraphView_Test(object):
    @skip_errors(ImportError)
    def setup(self):
        # test will be skipped if mysql module or ensembldb server unavailable
        import MySQLdb
        try:
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
        except MySQLdb.MySQLError:
            raise ImportError
    def orderBy_test(self):
        'test issue 53: ensure that the ORDER BY results are correct'
        exons = self.translationExons[self.translation] # do the query
        result = [e.id for e in exons]
        correct = [95160,95020,95035,95050,95059,95069,95081,95088,95101,
                   95110,95172]
        assert result == correct # make sure the exact order matches
