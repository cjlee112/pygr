import os, unittest
from testlib import testutil, logger
from pygr.sqlgraph import SQLTable,SQLTableNoCache,getNameCursor,\
     MapView,GraphView,DBServerInfo,import_sqlite

class SQLTable_Setup(unittest.TestCase):
    tableClass = SQLTable
    def setUp(self):
        self.load_data(writeable=self.writeable)
    def load_data(self, cursor=None, tableName='test.sqltable_test',
                  writeable=False):
        'create 3 tables and load 9 rows for our tests'
        self.tableName = tableName
        self.joinTable1 = joinTable1 = tableName + '1'
        self.joinTable2 = joinTable2 = tableName + '2'
        createTable = """\
        CREATE TABLE %s (primary_id INTEGER PRIMARY KEY %%(AUTO_INCREMENT)s, seq_id TEXT, start INTEGER, stop INTEGER)
        """ % tableName
        self.db = self.tableClass(tableName, cursor, dropIfExists=True,
                                  createTable=createTable,
                                  writeable=writeable)
        self.sourceDB = self.tableClass(joinTable1, cursor,
                                        dropIfExists=True, createTable="""\
        CREATE TABLE %s (my_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """ % joinTable1)
        self.targetDB = self.tableClass(joinTable2, cursor,
                                        dropIfExists=True, createTable="""\
        CREATE TABLE %s (third_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """ % joinTable2)
        sql = """
            INSERT INTO %s (seq_id, start, stop) VALUES ('seq1', 0, 10)
            INSERT INTO %s (seq_id, start, stop) VALUES ('seq2', 5, 15)
            INSERT INTO %s VALUES (2,'seq2')
            INSERT INTO %s VALUES (3,'seq3')
            INSERT INTO %s VALUES (4,'seq4')
            INSERT INTO %s VALUES (7, 'seq2')
            INSERT INTO %s VALUES (99, 'seq3')
            INSERT INTO %s VALUES (6, 'seq4')
            INSERT INTO %s VALUES (8, 'seq4')
        """ % tuple(([tableName]*2) + ([joinTable1]*3) + ([joinTable2]*4))
        for line in sql.strip().splitlines(): # insert our test data
            self.db.cursor.execute(line.strip())
    def tearDown(self):
        self.db.cursor.execute('drop table if exists %s' % self.tableName)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable1)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable2)

class SQLTable_Test(SQLTable_Setup):
    writeable = False # read-only database interface
    def test_keys(self):
        k = self.db.keys()
        k.sort()
        assert k == [1, 2]
    def test_contains(self):
        assert 1 in self.db
        assert 2 in self.db
        assert 'foo' not in self.db
    def test_has_key(self):
        assert self.db.has_key(1)
        assert self.db.has_key(2)
        assert not self.db.has_key('foo')
    def test_get(self):
        assert self.db.get('foo') is None
        assert self.db.get(1) == self.db[1]
        assert self.db.get(2) == self.db[2]
    def test_items(self):
        i = [ k for (k,v) in self.db.items() ]
        i.sort()
        assert i == [1, 2]
    def test_iterkeys(self):
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik
    def test_itervalues(self):
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv
    def test_iteritems(self):
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii
    def test_readonly(self):
        'test error handling of write attempts to read-only DB'
        try:
            self.db.new(seq_id='freddy', start=3000, stop=4500)
            raise AssertionError('failed to trap attempt to write to db')
        except ValueError:
            pass
        o = self.db[1]
        try:
            self.db[33] = o
            raise AssertionError('failed to trap attempt to write to db')
        except ValueError:
            pass
        try:
            del self.db[2]
            raise AssertionError('failed to trap attempt to write to db')
        except ValueError:
            pass

    ### @CTB need to test write access
    def test_mapview(self):
        'test MapView of SQL join'
        m = MapView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1,self.joinTable2), cursor=self.db.cursor)
        assert m[self.sourceDB[2]] == self.targetDB[7]
        assert m[self.sourceDB[3]] == self.targetDB[99]
        assert self.sourceDB[2] in m
        try:
            d = m[self.sourceDB[4]]
            raise AssertionError('failed to trap non-unique mapping')
        except KeyError:
            pass
    def test_graphview(self):
        'test GraphView of SQL join'
        m = GraphView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1,self.joinTable2), cursor=self.db.cursor)
        d = m[self.sourceDB[4]]
        assert len(d) == 2
        assert self.targetDB[6] in d and self.targetDB[8] in d
        assert self.sourceDB[2] in m

class SQLiteBase(testutil.SQLite_Mixin):
    def sqlite_load(self):
        self.load_data(self.cursor, 'sqltable_test', writeable=self.writeable)

class SQLiteTable_Test(SQLiteBase, SQLTable_Test):
    pass

class SQLTable_NoCache_Test(SQLTable_Test):
    tableClass = SQLTableNoCache

class SQLiteTable_NoCache_Test(SQLiteTable_Test):
    tableClass = SQLTableNoCache

class SQLTableRW_Test(SQLTable_Setup):
    'test write operations'
    writeable = True
    def test_new(self):
        'test row creation with auto inc ID'
        n = len(self.db)
        o = self.db.new(seq_id='freddy', start=3000, stop=4500)
        assert len(self.db) == n + 1
        t = self.tableClass(self.tableName, self.db.cursor) # requery the db
        result = t[o.id]
        assert result.seq_id == 'freddy' and result.start==3000 \
               and result.stop==4500
    def test_new2(self):
        'check row creation with specified ID'
        n = len(self.db)
        o = self.db.new(id=99, seq_id='jeff', start=3000, stop=4500)
        assert len(self.db) == n + 1
        assert o.id == 99
        t = self.tableClass(self.tableName, self.db.cursor) # requery the db
        result = t[99]
        assert result.seq_id == 'jeff' and result.start==3000 \
               and result.stop==4500
    def test_attr(self):
        'test changing an attr value'
        o = self.db[2]
        assert o.seq_id == 'seq2'
        o.seq_id = 'newval' # overwrite this attribute
        assert o.seq_id == 'newval' # check cached value
        t = self.tableClass(self.tableName, self.db.cursor) # requery the db
        result = t[2]
        assert result.seq_id == 'newval'
    def test_delitem(self):
        'test deletion of a row'
        n = len(self.db)
        del self.db[1]
        assert len(self.db) == n - 1
        try:
            result = self.db[1]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass
    def test_setitem(self):
        'test assigning new ID to existing object'
        o = self.db.new(id=17, seq_id='bob', start=2000, stop=2500)
        self.db[13] = o
        assert o.id == 13
        try:
            result = self.db[17]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass
        t = self.tableClass(self.tableName, self.db.cursor) # requery the db
        result = t[13]
        assert result.seq_id == 'bob' and result.start==2000 \
               and result.stop==2500
        try:
            result = t[17]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass
        

class SQLiteTableRW_Test(SQLiteBase, SQLTableRW_Test):
    pass

class SQLTableRW_NoCache_Test(SQLTableRW_Test):
    tableClass = SQLTableNoCache

class SQLiteTableRW_NoCache_Test(SQLiteTableRW_Test):
    tableClass = SQLTableNoCache

class Ensembl_Test(unittest.TestCase):
     
    def setUp(self):
        # test will be skipped if mysql module or ensembldb server unavailable

        logger.debug('accessing ensembldb.ensembl.org')
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
        self.assertEqual(result, correct) # make sure the exact order matches

def get_suite():
    "Returns the testsuite"

    tests = []

    # detect mysql
    if testutil.mysql_enabled():
        tests.append(SQLTable_Test)
        tests.append(SQLTableRW_Test)
        tests.append(SQLTable_NoCache_Test)
        tests.append(SQLTableRW_NoCache_Test)
        tests.append(Ensembl_Test) 
    else:
        testutil.info('*** skipping MySQL tests')
    if testutil.sqlite_enabled():
        tests.append(SQLiteTable_Test)
        tests.append(SQLiteTableRW_Test)
        tests.append(SQLiteTable_NoCache_Test)
        tests.append(SQLiteTableRW_NoCache_Test)

    return testutil.make_suite(tests)

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)
