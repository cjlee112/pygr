import pygrtest_common
from nosebase import skip_errors
from pygr import sqlgraph

class SQLTable_Test(object):
    @skip_errors(ImportError)
    def setup(self):
        # test will be skipped if unavailable
        import MySQLdb
        
        createTable = """\
        CREATE TABLE test.sqltable_test (primary_id INTEGER PRIMARY KEY AUTO_INCREMENT, seq_id TEXT, start INTEGER, stop INTEGER)
        """
        
        try:
            self.db = sqlgraph.SQLTable('test.sqltable_test',
                                             dropIfExists=True,
                                             createTable=createTable)
        except MySQLdb.MySQLError:
            tempcurs = sqlgraph.getNameCursor()[1]
            try: # hmm, maybe need to create the test database?
                tempcurs.execute('create database if not exists test')
                self.db = sqlgraph.SQLTable('test.sqltable_test',
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
    def teardown(self):
        self.db.cursor.execute('drop table if exists test.sqltable_test')

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
