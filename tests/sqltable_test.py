import os
import random
import string
import unittest

from testlib import testutil, PygrTestProgram, SkipTest
from pygr.sqlgraph import SQLTable, SQLTableNoCache, SQLTableClustered,\
     MapView, GraphView, DBServerInfo, import_sqlite
from pygr import logger


def entrap(klass):
    'return a function to intercept any calls to generic_iterator() method'

    def catch_iterator(self, *args, **kwargs):
        try:
            assert not self.catchIter, 'this should not iterate!'
        except AttributeError:
            pass
        return klass.generic_iterator(self, *args, **kwargs)
    return catch_iterator


class SQLTableCatcher(SQLTable):
    generic_iterator = entrap(SQLTable)


class SQLTableNoCacheCatcher(SQLTableNoCache):
    generic_iterator = entrap(SQLTableNoCache)


class SQLTableClusteredCatcher(SQLTableClustered):
    generic_iterator = entrap(SQLTableClustered)


class SQLTable_Setup(unittest.TestCase):
    tableClass = SQLTableCatcher
    serverArgs = {}
    loadArgs = {}

    def __init__(self, *args, **kwargs):
        unittest.TestCase.__init__(self, *args, **kwargs)
        # share conn for all tests
        self.serverInfo = DBServerInfo(** self.serverArgs)

    def setUp(self):
        if not testutil.mysql_enabled():
            raise SkipTest("no MySQL installed")
        self.load_data(writeable=self.writeable, ** self.loadArgs)

    def load_data(self, tableName='test.sqltable_test', writeable=False,
                  dbargs={}, sourceDBargs={}, targetDBargs={}):
        'create 3 tables and load 9 rows for our tests'
        self.tableName = tableName
        self.joinTable1 = joinTable1 = tableName + '1'
        self.joinTable2 = joinTable2 = tableName + '2'
        createTable = 'CREATE TABLE %s (primary_id INTEGER PRIMARY KEY \
                %%(AUTO_INCREMENT)s, seq_id TEXT, start INTEGER, \
                stop INTEGER)' % tableName
        self.db = self.tableClass(tableName, dropIfExists=True,
                                  serverInfo=self.serverInfo,
                                  createTable=createTable,
                                  writeable=writeable, **dbargs)
        self.sourceDB = self.tableClass(joinTable1, serverInfo=self.serverInfo,
                                        dropIfExists=True, createTable="""\
        CREATE TABLE %s (my_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """ % joinTable1, **sourceDBargs)
        self.targetDB = self.tableClass(joinTable2, serverInfo=self.serverInfo,
                                        dropIfExists=True, createTable="""\
        CREATE TABLE %s (third_id INTEGER PRIMARY KEY,
              other_id VARCHAR(16))
        """ % joinTable2, **targetDBargs)
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

        # Another table, for the "ORDER BY" test
        self.orderTable = tableName + '_orderBy'
        self.db.cursor.execute('DROP TABLE IF EXISTS %s' % self.orderTable)
        self.db.cursor.execute('CREATE TABLE %s (id INTEGER PRIMARY KEY, \
                               number INTEGER, letter VARCHAR(1))'
                               % self.orderTable)
        for row in range(0, 10):
            self.db.cursor.execute('INSERT INTO %s VALUES (%d, %d, \'%s\')' %
                                   (self.orderTable, row,
                                    random.randint(0, 99),
                                    string.lowercase[random.randint(0,
                                                          len(string.lowercase)
                                                                    - 1)]))

    def tearDown(self):
        self.db.cursor.execute('drop table if exists %s' % self.tableName)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable1)
        self.db.cursor.execute('drop table if exists %s' % self.joinTable2)
        self.db.cursor.execute('drop table if exists %s' % self.orderTable)
        self.serverInfo.close()


class SQLTable_Test(SQLTable_Setup):
    writeable = False # read-only database interface

    def test_keys(self):
        k = self.db.keys()
        k.sort()
        assert k == [1, 2]

    def test_len(self):
        self.db.catchIter = True
        assert len(self.db) == len(self.db.keys())

    def test_contains(self):
        self.db.catchIter = True
        assert 1 in self.db
        assert 2 in self.db
        assert 'foo' not in self.db

    def test_has_key(self):
        self.db.catchIter = True
        assert 1 in self.db
        assert 2 in self.db
        assert 'foo' not in self.db

    def test_get(self):
        self.db.catchIter = True
        assert self.db.get('foo') is None
        assert self.db.get(1) == self.db[1]
        assert self.db.get(2) == self.db[2]

    def test_items(self):
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == [1, 2]

    def test_iterkeys(self):
        kk = self.db.keys()
        ik = list(self.db.iterkeys())
        assert kk == ik

    def test_pickle(self):
        kk = self.db.keys()
        import pickle
        s = pickle.dumps(self.db)
        db = pickle.loads(s)
        try:
            ik = list(db.iterkeys())
            assert kk == ik
        finally:
            db.serverInfo.close() # close extra DB connection

    def test_itervalues(self):
        kv = self.db.values()
        iv = list(self.db.itervalues())
        assert kv == iv

    def test_itervalues_long(self):
        """test iterator isolation from queries run inside iterator loop """
        sql = 'insert into %s (start) values (1)' % self.tableName
        for i in range(40000): # insert 40000 rows
            self.db.cursor.execute(sql)
        iv = []
        for o in self.db.itervalues():
            status = 99 in self.db # make it do a query inside iterator loop
            iv.append(o.id)
        kv = [o.id for o in self.db.values()]
        assert len(kv) == len(iv)
        assert kv == iv

    def test_iteritems(self):
        ki = self.db.items()
        ii = list(self.db.iteritems())
        assert ki == ii

    def test_readonly(self):
        'test error handling of write attempts to read-only DB'
        self.db.catchIter = True # no iter expected in this test!
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

    def test_orderBy(self):
        'test iterator with orderBy, iterSQL, iterColumns'
        self.targetDB.catchIter = True # should not iterate
        # Force it to use multiple queries to finish.
        self.targetDB.arraysize = 2
        result = self.targetDB.keys()
        assert result == [6, 7, 8, 99]
        self.targetDB.catchIter = False # next statement will iterate
        assert result == list(iter(self.targetDB))
        self.targetDB.catchIter = True # should not iterate
        self.targetDB.orderBy = 'ORDER BY other_id'
        result = self.targetDB.keys()
        assert result == [7, 99, 6, 8]
        self.targetDB.catchIter = False # next statement will iterate
        if self.serverInfo._serverType == 'mysql' \
               and self.serverInfo.custom_iter_keys: # only test this for mysql
            try:
                assert result == list(iter(self.targetDB))
                raise AssertionError('failed to trap missing iterSQL attr')
            except AttributeError:
                pass
        self.targetDB.iterSQL = 'WHERE other_id>%s' # tell it how to slice
        self.targetDB.iterColumns = ['other_id']
        assert result == list(iter(self.targetDB))
        result = self.targetDB.values()
        assert result == [self.targetDB[7], self.targetDB[99],
                          self.targetDB[6], self.targetDB[8]]
        assert result == list(self.targetDB.itervalues())
        result = self.targetDB.items()
        assert result == [(7, self.targetDB[7]), (99, self.targetDB[99]),
                          (6, self.targetDB[6]), (8, self.targetDB[8])]
        assert result == list(self.targetDB.iteritems())
        import pickle
        s = pickle.dumps(self.targetDB) # test pickling & unpickling
        db = pickle.loads(s)
        try:
            correct = self.targetDB.keys()
            result = list(iter(db))
            assert result == correct
        finally:
            db.serverInfo.close() # close extra DB connection

    def test_orderby_random(self):
        'test orderBy in SQLTable'
        if self.serverInfo._serverType == 'mysql' \
               and self.serverInfo.custom_iter_keys:
            try:
                byNumber = self.tableClass(self.orderTable, arraysize=2,
                                           serverInfo=self.serverInfo,
                                           orderBy='ORDER BY number')
                raise AssertionError('failed to trap orderBy without iterSQL!')
            except ValueError:
                pass
        byNumber = self.tableClass(self.orderTable, serverInfo=self.serverInfo,
                                   arraysize=2, orderBy='ORDER BY number,id',
                          iterSQL='WHERE number>%s or (number=%s and id>%s)',
                                   iterColumns=('number', 'number', 'id'))
        bv = [val.number for val in byNumber.values()]
        sortedBV = bv[:]
        sortedBV.sort()
        assert sortedBV == bv
        bv = [val.number for val in byNumber.itervalues()]
        assert sortedBV == bv

        byLetter = self.tableClass(self.orderTable, serverInfo=self.serverInfo,
                                   arraysize=2, orderBy='ORDER BY letter,id',
                            iterSQL='WHERE letter>%s or (letter=%s and id>%s)',
                                   iterColumns=('letter', 'letter', 'id'))
        bl = [val.letter for val in byLetter.values()]
        sortedBL = bl[:]
        assert sortedBL == bl
        bl = [val.letter for val in byLetter.itervalues()]
        assert sortedBL == bl

    ### @CTB need to test write access

    def test_mapview(self):
        'test MapView of SQL join'
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = MapView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo)
        assert m[self.sourceDB[2]] == self.targetDB[7]
        assert m[self.sourceDB[3]] == self.targetDB[99]
        assert self.sourceDB[2] in m
        try:
            d = m[self.sourceDB[4]]
            raise AssertionError('failed to trap non-unique mapping')
        except KeyError:
            pass
        try:
            r = ~m
            raise AssertionError('failed to trap non-invertible mapping')
        except ValueError:
            pass
        self.sourceDB.cursor.execute("INSERT INTO %s VALUES (5,'seq78')"
                                     % self.sourceDB.name)
        assert len(self.sourceDB) == 4
        self.sourceDB.catchIter = False # next step will cause iteration
        assert len(m) == 2
        l = m.keys()
        l.sort()
        correct = [self.sourceDB[2], self.sourceDB[3]]
        correct.sort()
        assert l == correct

    def test_mapview_inverse(self):
        'test inverse MapView of SQL join'
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = MapView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo,
                    inverseSQL="""\
        SELECT t1.my_id FROM %s t1, %s t2
           WHERE t2.third_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2))
        r = ~m # get the inverse
        assert self.sourceDB[2] == r[self.targetDB[7]]
        assert self.sourceDB[3] == r[self.targetDB[99]]
        assert self.targetDB[7] in r

        m = ~r # get the inverse of the inverse!
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
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = GraphView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo)
        d = m[self.sourceDB[4]]
        assert len(d) == 2
        assert self.targetDB[6] in d and self.targetDB[8] in d
        assert self.sourceDB[2] in m

        self.sourceDB.cursor.execute("INSERT INTO %s VALUES (5,'seq78')"
                                     % self.sourceDB.name)
        assert len(self.sourceDB) == 4
        self.sourceDB.catchIter = False # next step will cause iteration
        assert len(m) == 3
        l = m.keys()
        l.sort()
        correct = [self.sourceDB[2], self.sourceDB[3], self.sourceDB[4]]
        correct.sort()
        assert l == correct

    def test_graphview_inverse(self):
        'test inverse GraphView of SQL join'
        self.sourceDB.catchIter = self.targetDB.catchIter = True
        m = GraphView(self.sourceDB, self.targetDB, """\
        SELECT t2.third_id FROM %s t1, %s t2
           WHERE t1.my_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2), serverInfo=self.serverInfo,
                    inverseSQL="""\
        SELECT t1.my_id FROM %s t1, %s t2
           WHERE t2.third_id=%%s and t1.other_id=t2.other_id
        """ % (self.joinTable1, self.joinTable2))
        r = ~m # get the inverse
        assert self.sourceDB[2] in r[self.targetDB[7]]
        assert self.sourceDB[3] in r[self.targetDB[99]]
        assert self.targetDB[7] in r
        d = r[self.targetDB[6]]
        assert len(d) == 1
        assert self.sourceDB[4] in d

        m = ~r # get inverse of the inverse!
        d = m[self.sourceDB[4]]
        assert len(d) == 2
        assert self.targetDB[6] in d and self.targetDB[8] in d
        assert self.sourceDB[2] in m


class SQLTable_No_SSCursor_Test(SQLTable_Test):
    serverArgs = dict(serverSideCursors=False)


class SQLTable_OldIter_Test(SQLTable_Test):
    serverArgs = dict(serverSideCursors=False,
                      blockIterators=False)


class SQLiteBase(testutil.SQLite_Mixin):

    def sqlite_load(self):
        self.load_data('sqltable_test', writeable=self.writeable)


class SQLiteTable_Test(SQLiteBase, SQLTable_Test):
    pass


## class SQLitePickle_Test(SQLiteTable_Test):
##
##     def setUp(self):
##         """Pickle / unpickle our serverInfo before trying to use it """
##         SQLiteTable_Test.setUp(self)
##         self.serverInfo.close()
##         import pickle
##         s = pickle.dumps(self.serverInfo)
##         del self.serverInfo
##         self.serverInfo = pickle.loads(s)
##         self.db = self.tableClass(self.tableName, serverInfo=self.serverInfo)
##         self.sourceDB = self.tableClass(self.joinTable1,
##                                         serverInfo=self.serverInfo)
##         self.targetDB = self.tableClass(self.joinTable2,
##                                         serverInfo=self.serverInfo)


class SQLTable_NoCache_Test(SQLTable_Test):
    tableClass = SQLTableNoCacheCatcher


class SQLTableClustered_Test(SQLTable_Test):
    tableClass = SQLTableClusteredCatcher
    loadArgs = dict(dbargs=dict(clusterKey='seq_id', arraysize=2),
                    sourceDBargs=dict(clusterKey='other_id', arraysize=2),
                    targetDBargs=dict(clusterKey='other_id', arraysize=2))

    def test_orderBy(self): # neither of these tests useful in this context
        pass

    def test_orderby_random(self):
        pass


class SQLiteTable_NoCache_Test(SQLiteTable_Test):
    tableClass = SQLTableNoCache


class SQLTableRW_Test(SQLTable_Setup):
    'test write operations'
    writeable = True

    def test_new(self):
        'test row creation with auto inc ID'
        self.db.catchIter = True # no iter expected in this test
        n = len(self.db)
        o = self.db.new(seq_id='freddy', start=3000, stop=4500)
        assert len(self.db) == n + 1
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
        result = t[o.id]
        assert result.seq_id == 'freddy' and result.start==3000 \
               and result.stop==4500

    def test_new2(self):
        'check row creation with specified ID'
        self.db.catchIter = True # no iter expected in this test
        n = len(self.db)
        o = self.db.new(id=99, seq_id='jeff', start=3000, stop=4500)
        assert len(self.db) == n + 1
        assert o.id == 99
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
        result = t[99]
        assert result.seq_id == 'jeff' and result.start==3000 \
               and result.stop==4500

    def test_attr(self):
        'test changing an attr value'
        self.db.catchIter = True # no iter expected in this test
        o = self.db[2]
        assert o.seq_id == 'seq2'
        o.seq_id = 'newval' # overwrite this attribute
        assert o.seq_id == 'newval' # check cached value
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
        result = t[2]
        assert result.seq_id == 'newval'

    def test_delitem(self):
        'test deletion of a row'
        self.db.catchIter = True # no iter expected in this test
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
        self.db.catchIter = True # no iter expected in this test
        o = self.db.new(id=17, seq_id='bob', start=2000, stop=2500)
        self.db[13] = o
        assert o.id == 13
        try:
            result = self.db[17]
            raise AssertionError('old ID still exists!')
        except KeyError:
            pass
        t = self.tableClass(self.tableName,
                            serverInfo=self.serverInfo) # requery the db
        t.catchIter = True # no iter expected in this test
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
        try:
            translationDB = \
                    SQLTableCatcher('homo_sapiens_core_47_36i.translation',
                                    serverInfo=conn)
            translationDB.catchIter = True # should not iter in this test!
            exonDB = SQLTable('homo_sapiens_core_47_36i.exon', serverInfo=conn)
        except ImportError, e:
            raise SkipTest(e)

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
        correct = [95160, 95020, 95035, 95050, 95059, 95069, 95081, 95088,
                   95101, 95110, 95172]
        self.assertEqual(result, correct) # make sure the exact order matches


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
