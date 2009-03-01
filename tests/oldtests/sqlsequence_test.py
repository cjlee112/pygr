import pygrtest_common
from pygr import sqlgraph, seqdb, classutil
from nosebase import *

class SQLSequence_Test(object):
    '''basic SQL sequence class tests
    
    This test setup uses the common (?) method of having the SQLSequece objects created by 
    a SQLTable object rather than instantiating the SQLSequece objects directly.
    '''
    @skip_errors(ImportError)
    def setup(self):
        # test will be skipped if unavailable
        import MySQLdb
        
        createTable = """\
        CREATE TABLE test.sqlsequence_test (primary_id INTEGER PRIMARY KEY AUTO_INCREMENT, sequence TEXT)
        """
        
        try:
            self.db = sqlgraph.SQLTable('test.sqlsequence_test',
                                             dropIfExists=True,
                                             createTable=createTable,
                                             attrAlias=dict(seq='sequence'))
        except MySQLdb.MySQLError:
            tempcurs = sqlgraph.getNameCursor()[1]
            try: # hmm, maybe need to create the test database?
                tempcurs.execute('create database if not exists test')
                self.db = sqlgraph.SQLTable('test.sqlsequence_test',
                                                 dropIfExists=True,
                                                 createTable=createTable,
                                                 attrAlias=dict(seq='sequence'))
            except MySQLdb.MySQLError: # no server, database or privileges?
                print """\
                The MySQL 'test' database doesn't exist and/or can't be
                created or accessed on this account. This test will be skipped.
                """
                raise ImportError #  skip tests.
        
        self.db.cursor.execute("""\
        INSERT INTO test.sqlsequence_test (sequence)
              VALUES ('CACCCTGCCCCATCTCCCCAGCCTGGCCCCTCGTGTCTCAGAACCCTCGGGGGGAGGCACAGAAGCCTTCGGGG')
        """)
        self.db.cursor.execute("""\
        INSERT INTO test.sqlsequence_test (sequence)
              VALUES ('GAAAGAAAGAAAGAAAGAAAGAAAGAGAGAGAGAGAGACAGAAG')
        """)
        
        class DNASeqRow(seqdb.DNASQLSequence):
            def __len__(self): # just speed optimization
                return self._select('length(sequence)') # SQL SELECT expression
        
        self.db.objclass(DNASeqRow) # force the table object to return DNASeqRow objects
        self.row1 = self.db[1]
        self.row2 = self.db[2]
    def teardown(self):
        self.db.cursor.execute('drop table if exists test.sqlsequence_test')
    def print_test(self):
        assert str(self.row2) == 'GAAAGAAAGAAAGAAAGAAAGAAAGAGAGAGAGAGAGACAGAAG'
        assert repr(self.row2) == '2[0:44]'
    def len_test(self):
        assert len(self.row2) == 44
    def strslice_test(self):
        assert self.row2.strslice(3,10) == 'AGAAAGA'
    def init_subclass_test(self):
        self.row2._init_subclass(self.db)

