import pygrtest_common
from pygr.sqlgraph import SQLTable,SQLTableNoCache,getNameCursor,\
     MapView,GraphView,DBServerInfo
import MySQLdb

class SQLTable_Setup(unittest.TestCase):
    tableClass = SQLTable
    def setup(self):
        # test will be skipped if unavailable
        self.load_data(dbError=MySQLdb.MySQLError, writeable=self.writeable)
    def load_data(self, cursor=None, tableName='test.sqltable_test',
                  dbError=NotImplementedError, autoInc='AUTO_INCREMENT',
                  writeable=False):
        joinTable1 = tableName + '1'
        joinTable2 = tableName + '2'
        self.tableName = tableName
        self.joinTable1 = joinTable1
        self.joinTable2 = joinTable2
        createTable = """\
        CREATE TABLE %s (primary_id INTEGER PRIMARY KEY %s, seq_id TEXT, start INTEGER, stop INTEGER)
        """ % (tableName,autoInc)
        
        try:
            self.db = self.tableClass(tableName, cursor, dropIfExists=True,
                                      createTable=createTable,
                                      writeable=writeable)
        except dbError:
            tempcurs = getNameCursor()[1]
            try: # hmm, maybe need to create the test database?
                tempcurs.execute('create database if not exists test')
                self.db = self.tableClass(tableName, cursor,
                                          dropIfExists=True,
                                          createTable=createTable,
                                          writeable=writeable)
            except dbError: # no server, database or privileges?
                print """\
                The MySQL 'test' database doesn't exist and/or can't be
                created or accessed on this account. This test will be skipped.
                """
                raise ImportError #  skip tests.

        self.db.cursor.execute("""\
        INSERT INTO %s (seq_id, start, stop)
              VALUES ('seq1', 0, 10)
        """ % tableName)
        self.db.cursor.execute("""\
        INSERT INTO %s (seq_id, start, stop)
              VALUES ('seq2', 5, 15)
        """ % tableName)
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
        self.db.cursor.execute("""\
        INSERT INTO %s VALUES (2,'seq2')
        """ % joinTable1)
        self.db.cursor.execute("""\
        INSERT INTO %s VALUES (3,'seq3')
        """ % joinTable1)
        self.db.cursor.execute("""\
        INSERT INTO %s VALUES (4,'seq4')
        """ % joinTable1)
        self.db.cursor.execute("""\
        INSERT INTO %s VALUES (7, 'seq2')
        """ % joinTable2)
        self.db.cursor.execute("""\
        INSERT INTO %s VALUES (99, 'seq3')
        """ % joinTable2)
        self.db.cursor.execute("""\
        INSERT INTO %s VALUES (6, 'seq4')
        """ % joinTable2)
        self.db.cursor.execute("""\
        INSERT INTO %s VALUES (8, 'seq4')
        """ % joinTable2)
    def teardown(self):
        self.db.cursor.execute('drop table if exists %s' % self.tableName)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable1)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable2)

class SQLTable_Test(SQLTable_Setup):
    writeable = False # read-only database interface
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
    def readonly_test(self):
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
    def mapview_test(self):
        m = MapView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1,self.joinTable2), cursor=self.db.cursor)
        assert m[self.sourceDB[2]] == self.targetDB[7]
        assert m[self.sourceDB[3]] == self.targetDB[99]
        assert self.sourceDB[2] in m
    def graphview_test(self):
        m = GraphView(self.sourceDB, self.targetDB,"""\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1,self.joinTable2), cursor=self.db.cursor)
        d = m[self.sourceDB[4]]
        assert len(d) == 2
        assert self.targetDB[6] in d and self.targetDB[8] in d
        assert self.sourceDB[2] in m

def sqlite_setup(self):
    # test will be skipped if unavailable
    import sqlite3
    db = sqlite3.connect('test_sqlite.db')
    c = db.cursor()
    self.load_data(c, 'sqltable_test', autoInc='', writeable=self.writeable)
        
class SQLiteTable_Test(SQLTable_Test):
    setup = sqlite_setup

class SQLTableRW_Test(SQLTable_Setup):
    'test write operations'
    writeable = True
    def new_test(self):
        'test row creation with auto inc ID'
        n = len(self.db)
        o = self.db.new(seq_id='freddy', start=3000, stop=4500)
        assert len(self.db) == n + 1
        t = self.tableClass(self.tableName, self.db.cursor) # requery the db
        result = t[o.id]
        assert result.seq_id == 'freddy' and result.start==3000 \
               and result.stop==4500
    def new2_test(self):
        'check row creation with specified ID'
        n = len(self.db)
        o = self.db.new(id=99, seq_id='jeff', start=3000, stop=4500)
        assert len(self.db) == n + 1
        assert o.id == 99
        t = self.tableClass(self.tableName, self.db.cursor) # requery the db
        result = t[99]
        assert result.seq_id == 'jeff' and result.start==3000 \
               and result.stop==4500
    def attr_test(self):
        'test changing an attr value'
        o = self.db[2]
        assert o.seq_id == 'seq2'
        o.seq_id = 'newval' # overwrite this attribute
        assert o.seq_id == 'newval' # check cached value
        t = self.tableClass(self.tableName, self.db.cursor) # requery the db
        result = t[2]
        assert result.seq_id == 'newval'
    def delitem_test(self):
        'test deletion of a row'
        n = len(self.db)
        del self.db[1]
        assert len(self.db) == n - 1
        try:
            result = self.db[1]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass
    def setitem_test(self):
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
        

class SQLiteTableRW_Test(SQLTableRW_Test):
    setup = sqlite_setup

class SQLTableRW_NoCache_Test(SQLTableRW_Test):
    tableClass = SQLTableNoCache

class SQLiteTableRW_NoCache_Test(SQLTableRW_NoCache_Test):
    setup = sqlite_setup

class Ensembl_Test(unittest.TestCase):
     
    def setUp(self):
        # test will be skipped if mysql module or ensembldb server unavailable

        logger.debug('accessing ensebledb.ensembl.org')
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
        tests.append(SQLiteTable_Test)
        tests.append(SQLTableRW_Test)
        tests.append(SQLiteTableRW_Test)
        tests.append(SQLTableRW_NoCacheTest)
        tests.append(SQLiteTableRW_NoCacheTest)
        tests.append(Ensembl_Test) 
    else:
        testutil.info('*** skipping SQLTable_Test')

    return testutil.make_suite(tests)

if __name__ == '__main__':
    suite = get_suite()
    unittest.TextTestRunner(verbosity=2).run(suite)
