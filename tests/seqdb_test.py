"""
Tests for the pygr.seqdb module.
"""

import os
import unittest

from testlib import testutil, PygrTestProgram
from pygr.seqdb import SequenceDB, SequenceFileDB, PrefixUnionDict, \
     AnnotationDB, SeqPrefixUnionDict
from pygr.sequence import Sequence
from pygr.cnestedlist import NLMSA
import gc
from pygr.annotation import AnnotationDB, AnnotationSeq, AnnotationSlice, \
    AnnotationServer, AnnotationClient

# utility classes for the SequenceDB tests

_fake_seq = "ATCGAGAGCCAGAATGACGGGACCATTAG"


class _SimpleFakeSequence(Sequence):

    def __init__(self, db, id):
        assert id == "foo"
        Sequence.__init__(self, _fake_seq, "foo")

    def __len__(self):
        return len(self.seq)

    def strslice(self, start, end):
        return self.seq[start:end]


class _SimpleFakeInfoObj(object):

    def __init__(self, length):
        self.length = length


class _SimpleFakeSeqDB(SequenceDB):

    def __init__(self, *args, **kwargs):
        self.seqInfoDict = dict(foo=_SimpleFakeInfoObj(len(_fake_seq)))
        SequenceDB.__init__(self, *args, **kwargs)

###

class SequenceDB_Test(unittest.TestCase):

    def test_repr(self):
        "test the __repr__ function."

        db = _SimpleFakeSeqDB(itemClass=_SimpleFakeSequence)
        repr(db)

    def test_create_no_itemclass(self):
        # must supply an itemclass to SequenceDB!
        try:
            db = SequenceDB()
            assert 0, "should not reach this point"
        except TypeError:
            pass


class SequenceFileDB_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'SequenceFileDB',
    among other things.
    """

    def setUp(self):
        "Test setup"
        dnaseq = testutil.datafile('dnaseq.fasta')
        self.db = SequenceFileDB(dnaseq) # contains 'seq1', 'seq2'

        self.db._weakValueDict.clear()   # clear the cache

    def tearDown(self):
        self.db.close() # must close SequenceFileDB!

    def test_len(self):
        assert len(self.db) == 2

    def test_seqInfoDict_len(self):
        assert len(self.db.seqInfoDict) == 2

    def test_no_file_given(self):
        "Make sure that a TypeError is raised when no file is available"
        try:
            db = SequenceFileDB()
            assert 0, "should not reach this point"
        except TypeError:
            pass

    def test_seq_descriptor(self):
        "Check the '.seq' attribute (tied to a descriptor)"
        s = self.db['seq1']
        assert str(s) == str(s.seq)

    def test_cache(self):
        "SequenceDB cache test"
        assert len(self.db._weakValueDict) == 0
        seq1 = self.db['seq1']

        # cache populated?
        assert len(self.db._weakValueDict) == 1
        assert 'seq1' in self.db._weakValueDict

        # cache functions?
        seq1_try2 = self.db['seq1']
        assert seq1 is seq1_try2

    def test_clear_cache(self):
        "SequenceDB clear_cache test"
        assert len(self.db._weakValueDict) == 0
        seq1 = self.db['seq1']

        # cache populated?
        assert len(self.db._weakValueDict) == 1
        assert 'seq1' in self.db._weakValueDict

        # clear_cache functions?
        self.db.clear_cache()
        seq1_try3 = self.db['seq1']
        assert seq1 is not seq1_try3

    def test_keys(self):
        "SequenceFileDB keys"
        k = self.db.keys()
        k.sort()
        assert k == ['seq1', 'seq2']

    def test_contains(self):
        "SequenceFileDB contains"
        assert 'seq1' in self.db, self.db.keys()
        assert 'seq2' in self.db
        assert 'foo' not in self.db

    def test_invert_class(self):
        "SequenceFileDB __invert__"
        seq = self.db['seq1']
        inversedb = ~self.db
        assert inversedb[seq] == 'seq1'
        assert seq in inversedb
        assert 'foo' not in inversedb

    def test_keys_info(self):
        "SequenceFileDB keys info"
        k = self.db.seqInfoDict.keys()
        k.sort()
        assert k == ['seq1', 'seq2']

    def test_contains_info(self):
        "SequenceFileDB contains info"
        assert 'seq1' in self.db.seqInfoDict
        assert 'seq2' in self.db.seqInfoDict
        assert 'foo' not in self.db.seqInfoDict

    def test_has_key(self):
        "SequenceFileDB has key"
        assert 'seq1' in self.db
        assert 'seq2' in self.db
        assert 'foo' not in self.db

    def test_get(self):
        "SequenceFileDB get"
        assert self.db.get('foo') is None
        assert self.db.get('seq1') is not None
        assert str(self.db.get('seq1')).startswith('atggtgtca')
        assert self.db.get('seq2') is not None
        assert str(self.db.get('seq2')).startswith('GTGTTGAA')

    def test_items(self):
        "SequenceFileDB items"
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == ['seq1', 'seq2']

    def test_iterkeys(self):
        "SequenceFileDB iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "SequenceFileDB itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv

    def test_iteritems(self):
        "SequenceFileDB iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii

    def test_readonly(self):
        "SequenceFileDB readonly"
        try:
            self.db.copy()          # what should 'copy' do on SequenceFileDB?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass

    # test some things other than dict behavior
    def test_keyerror(self):
        """SequenceFileDB keyerror.
        Make sure that the SequenceFileDB KeyError is informative."""
        try:
            self.db['foo']
        except KeyError, e:
            assert "no key 'foo' in database <SequenceFileDB" in str(e), str(e)

    def test_close(self):
        """SequenceFileDB close.
        Check closing behavior; access after close() --> ValueError """
        self.db.close()
        self.db.close() # closing twice should not raise an error
        try:
            len(self.db)
            assert 0, 'Failed to catch invalid shelve access!'
        except ValueError:
            pass
        try:
            self.db['seq1']
            assert 0, 'Failed to catch invalid shelve access!'
        except ValueError:
            pass


class SequenceFileDB_Creation_Test(unittest.TestCase):
    """
    Test some of the nastier / more polluting creation code in an
    isolated (and slower...) class that cleans up after itself.
    """

    def trash_intermediate_files(self):
        seqlen = testutil.datafile('dnaseq.fasta.seqlen')
        pureseq = testutil.datafile('dnaseq.fasta.pureseq')
        try:
            os.unlink(seqlen)
            os.unlink(pureseq)
        except OSError:
            pass

    def setUp(self):
        "Test setup"
        self.trash_intermediate_files()
        self.dbfile = testutil.datafile('dnaseq.fasta')

    def tearDown(self):
        self.trash_intermediate_files()

    def test_basic_construction(self):
        db = SequenceFileDB(self.dbfile)
        try:
            assert str(db.get('seq1')).startswith('atggtgtca')
            assert str(db.get('seq2')).startswith('GTGTTGAA')
        finally:
            db.close()

    def test_build_seqLenDict_with_reader(self):
        "Test that building things works properly when specifying a reader."

        class InfoBag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first, load the db & save the sequence info in a list
        l = []
        db = SequenceFileDB(self.dbfile)
        try:
            for k, v in db.items():
                info = InfoBag(id=k, length=len(v), sequence=str(v))
                l.append(info)
        finally:
            # now, erase the existing files, and recreate the db.
            db.close()
        self.trash_intermediate_files()

        # create a fake reader with access to the saved info
        def my_fake_reader(fp, filename, info_list=l):
            return info_list

        # now try creating with the fake reader
        db = SequenceFileDB(self.dbfile, reader=my_fake_reader)

        # did it work?
        try:
            assert str(db.get('seq1')).startswith('atggtgtca')
            assert str(db.get('seq2')).startswith('GTGTTGAA')
        finally:
            db.close()

    def test_build_seqLenDict_with_bad_reader(self):
        "Test that building things fails properly with a bad reader."

        class InfoBag(object):

            def __init__(self, **kw):
                self.__dict__.update(kw)

        # first, load the db & save the sequence info in a list
        l = []
        db = SequenceFileDB(self.dbfile)
        try:
            for k, v in db.items():
                info = InfoBag(id=k, length=0, sequence=str(v))
                l.append(info)
        finally:
            # now, erase the existing files, and recreate the db.
            db.close()
        self.trash_intermediate_files()

        # create a fake reader with access to the saved info
        def my_fake_reader(fp, filename, info_list=l):
            return info_list

        # now try creating with the fake reader
        try:
            db = SequenceFileDB(self.dbfile, reader=my_fake_reader)
            try:
                assert 0, "should not reach here; db construction should fail!"
            finally:
                db.close()
        except ValueError:
            pass                        # ValueError is expected


def close_pud_dicts(pud):
    """Close all seq dbs indexed in a PrefixUnionDict """
    for db in pud.dicts:
        db.close()


class PrefixUnionDict_Creation_Test(unittest.TestCase):
    """
    Test PUD creation options.
    """

    def setUp(self):
        self.dbfile = testutil.datafile('dnaseq.fasta')

    def test_empty_create(self):
        db = PrefixUnionDict()
        assert len(db) == 0

    def test_headerfile_create(self):
        header = testutil.datafile('prefixUnionDict-1.txt')
        db = PrefixUnionDict(filename=header)
        try:
            assert len(db) == 2
            assert 'a.seq1' in db
        finally:
            close_pud_dicts(db)

    def test_headerfile_create_conflict(self):
        "test non-empty prefixDict with a passed in PUD header file: conflict"
        subdb = SequenceFileDB(self.dbfile)
        try:
            header = testutil.datafile('prefixUnionDict-1.txt')
            try:
                db = PrefixUnionDict(filename=header,
                                     prefixDict={'foo': subdb})
                assert 0, "should not get here"
            except TypeError:
                pass
        finally:
            subdb.close()

    def test_multiline_headerfile_create(self):
        header = testutil.datafile('prefixUnionDict-2.txt')
        db = PrefixUnionDict(filename=header)
        try:
            assert len(db) == 4
            assert 'a.seq1' in db
            assert 'b.seq1' in db
        finally:
            close_pud_dicts(db)

    def test_headerfile_create_with_trypath(self):
        header = testutil.datafile('prefixUnionDict-1.txt')
        db = PrefixUnionDict(filename=header,
                             trypath=[os.path.dirname(header)])
        try:
            assert len(db) == 2, db.prefixDict
        finally:
            close_pud_dicts(db)

    def test_headerfile_create_fail(self):
        header = testutil.datafile('prefixUnionDict-3.txt')
        try:
            db = PrefixUnionDict(filename=header)
            assert 0, "should not reach this point"
        except IOError:
            pass
        except AssertionError:
            close_pud_dicts(db)
            raise

    def test_headerfile_write(self):
        header = testutil.datafile('prefixUnionDict-2.txt')
        db = PrefixUnionDict(filename=header)
        try:
            assert len(db) == 4
            assert 'a.seq1' in db
            assert 'b.seq1' in db

            output = testutil.tempdatafile('prefixUnionDict-write.txt')
            db.writeHeaderFile(output)
        finally:
            close_pud_dicts(db)

        db2 = PrefixUnionDict(filename=output,
                               trypath=[os.path.dirname(header)])
        try:
            assert len(db2) == 4
            assert 'a.seq1' in db2
            assert 'b.seq1' in db2
        finally:
            close_pud_dicts(db2)

    def test_headerfile_write_fail(self):
        subdb = SequenceFileDB(self.dbfile)
        try:
            del subdb.filepath  # remove 'filepath' attribute for test
            db = PrefixUnionDict({'prefix': subdb})

            assert len(db) == 2
            assert 'prefix.seq1' in db

            output = testutil.tempdatafile('prefixUnionDict-write-fail.txt')
            try:
                db.writeHeaderFile(output)
            except AttributeError:
                pass
        finally:
            subdb.close() # closes both db and subdb


class PrefixUnionDict_Test(unittest.TestCase):
    """
    Test for all of the basic dictionary functions on 'PrefixUnionDict'.
    """

    def setUp(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        self.db = PrefixUnionDict({'prefix': seqdb})

    def tearDown(self):
        close_pud_dicts(self.db)

    def test_keys(self):
        "PrefixUnionDict keys"
        k = self.db.keys()
        k.sort()
        assert k == ['prefix.seq1', 'prefix.seq2']

    def test_contains(self):
        "PrefixUnionDict contains"
        # first, check "is this sequence name in the PUD?"-style contains.
        assert 'prefix.seq1' in self.db
        assert 'prefix.seq2' in self.db
        assert 'foo' not in self.db
        assert 'prefix.foo' not in self.db

        # now, check "is this sequence in the PUD?"
        seq = self.db['prefix.seq1']
        assert seq in self.db

        # finally, check failure: "is something other than str/seq in db"
        try:
            12345 in self.db
            assert 0, "should not get to this point"
        except AttributeError:
            pass

    def test_invert_class(self):
        "PrefixUnionDict __invert__"
        seq = self.db['prefix.seq1']
        inversedb = ~self.db
        assert inversedb[seq] == 'prefix.seq1'
        assert seq in inversedb
        assert 'foo' not in inversedb

    def test_funny_key(self):
        "check handling of ID containing multiple separators"
        dnaseq = testutil.datafile('funnyseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        try:
            pudb = PrefixUnionDict({'prefix': seqdb})
            seq = pudb['prefix.seq.1.more']
        finally:
            seqdb.close()

    def test_funny_key2(self):
        "check handling of ID containing multiple separators"
        dnaseq = testutil.datafile('funnyseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        try:
            pudb = PrefixUnionDict({'prefix': seqdb})
            seq = pudb['prefix.seq.2.even.longer']
        finally:
            seqdb.close()

    def test_has_key(self):
        "PrefixUnionDict has key"
        assert 'prefix.seq1' in self.db
        assert 'prefix.seq2' in self.db
        assert 'prefix.foo' not in self.db
        assert 'foo' not in self.db

    def test_get(self):
        "PrefixUnionDict get"
        assert self.db.get('foo') is None
        assert self.db.get('prefix.foo') is None
        assert self.db.get('prefix.seq1') is not None
        assert str(self.db.get('prefix.seq1')).startswith('atggtgtca')
        assert self.db.get('prefix.seq2') is not None
        assert str(self.db.get('prefix.seq2')).startswith('GTGTTGAA')
        assert self.db.get('foo.bar') is None
        assert self.db.get(12345) is None

    def test_get_prefix_id(self):
        try:
            self.db.get_prefix_id(12345)
            assert 0, "should not get here"
        except KeyError:
            pass

    def test_getName(self):
        seq1 = self.db['prefix.seq1']
        name = self.db.getName(seq1)
        assert name == 'prefix.seq1'

    def test_items(self):
        "PrefixUnionDict items"
        i = [k for (k, v) in self.db.items()]
        i.sort()
        assert i == ['prefix.seq1', 'prefix.seq2']

    def test_iterkeys(self):
        "PrefixUnionDict iterkeys"
        kk = self.db.keys()
        kk.sort()
        ik = list(self.db.iterkeys())
        ik.sort()
        assert kk == ik

    def test_itervalues(self):
        "PrefixUnionDict itervalues"
        kv = self.db.values()
        kv.sort()
        iv = list(self.db.itervalues())
        iv.sort()
        assert kv == iv

    def test_iteritems(self):
        "PrefixUnionDict iteritems"
        ki = self.db.items()
        ki.sort()
        ii = list(self.db.iteritems())
        ii.sort()
        assert ki == ii

    # test some things other than dict behavior
    def test_keyerror(self):
        "PrefixUnionDict keyerror"
        "Make sure that the PrefixUnionDict KeyError is informative."
        try:
            self.db['prefix.foo']
        except KeyError, e:
            assert "no key 'foo' in " in str(e), str(e)
        try:
            self.db['foo']
        except KeyError, e:
            assert "invalid id format; no prefix: foo" in str(e), str(e)

    def test_readonly(self):
        "PrefixUnionDict readonly"
        try:
            self.db.copy()              # what should 'copy' do on PUD?
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'setdefault' do on PUD?
            self.db.setdefault('foo')
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:                           # what should 'update' do on PUD?
            self.db.update({})
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.clear()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.pop()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass
        try:
            self.db.popitem()
            assert 0, 'this method should raise NotImplementedError'
        except NotImplementedError:
            pass

    def test_seqInfoDict(self):
        seqInfoDict = self.db.seqInfoDict

        keylist = seqInfoDict.keys()
        keylist.sort()

        keylist2 = list(seqInfoDict)
        keylist2.sort()

        assert keylist == ['prefix.seq1', 'prefix.seq2']
        assert keylist2 == ['prefix.seq1', 'prefix.seq2']

        itemlist = list(seqInfoDict.iteritems())
        itemlist.sort()
        ((n1, i1), (n2, i2)) = itemlist

        ii1, ii2 = list(seqInfoDict.itervalues())

        s1i = seqInfoDict['prefix.seq1']
        s2i = seqInfoDict['prefix.seq2']

        assert n1 == 'prefix.seq1'
        assert (i1.id, i1.db) == (s1i.id, s1i.db)
        assert (ii1.id, ii1.db) == (s1i.id, s1i.db)
        assert n2 == 'prefix.seq2'
        assert (i2.id, i2.db) == (s2i.id, s2i.db)
        assert (ii2.id, ii2.db) == (s2i.id, s2i.db)

        assert 'prefix.seq1' in seqInfoDict


class PrefixUnionMemberDict_Test(unittest.TestCase):

    def setUp(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        self.db = PrefixUnionDict({'prefix': seqdb})
        self.mdb = self.db.newMemberDict()

    def tearDown(self):
        close_pud_dicts(self.db)

    def test_basic(self):
        self.mdb['prefix'] = 'this is from seqdb dnaseq.fasta'
        seq = self.db['prefix.seq1']
        assert self.mdb[seq] == 'this is from seqdb dnaseq.fasta'

    def test_possible_keys(self):
        assert list(self.mdb.possibleKeys()) == ['prefix']

    def test_bad_prefix(self):
        try:
            self.mdb['foo'] = "xyz"
            assert 0, "should fail before this"
        except KeyError:
            pass

    def test_bad_keytype(self):
        try:
            self.mdb['some non-seq-obj']
            assert 0, "should fail before this"
        except TypeError:
            pass

    def test_default_val(self):
        self.mdb = self.db.newMemberDict(default='baz')
        seq = self.db['prefix.seq1']
        assert self.mdb[seq] == 'baz'

    def test_no_default_val(self):
        self.mdb = self.db.newMemberDict()
        seq = self.db['prefix.seq1']
        try:
            self.mdb[seq]
            assert 0, "should fail before this"
        except KeyError:
            pass


class SeqPrefixUnionDict_Test(unittest.TestCase):
    """
    Test SeqPrefixUnionDict.
    """

    def setUp(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        self.seqdb = SequenceFileDB(dnaseq)     # contains 'seq1', 'seq2'
        self.db = SeqPrefixUnionDict({'prefix': self.seqdb})

    def tearDown(self):
        self.seqdb.close()

    def test_basic_iadd(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            new_seq = seqdb['seq1']

            self.db += new_seq

            assert new_seq in self.db
            name = (~self.db)[new_seq]
            assert name == 'dnaseq.seq1', name

            ###

            seqdb2 = SequenceFileDB(dnaseq)
            try:
                # Munge the filepath for testing.
                seqdb2.filepath = 'foo'
                new_seq2 = seqdb2['seq1']

                self.db += new_seq2
                name2 = (~self.db)[new_seq2]
                assert name2 == 'foo.seq1', name2
            finally:
                seqdb2.close()
        finally:
            seqdb.close()
        # NOTE, the important thing here is less the specific names that
        # are given (which are based on filepath) but that different names
        # are created for the various sequences when they are added.

    def test_iadd_db_twice(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            new_seq = seqdb['seq1']

            self.db += new_seq
            name1 = (~self.db)[new_seq]

            self.db += new_seq              # should do nothing...
            name2 = (~self.db)[new_seq]
            assert name1 == name2           # ...leaving seq with same name.
        finally:
            seqdb.close()

    def test_iadd_user_seq(self):
        seq = Sequence('ATGGCAGG', 'foo')
        self.db += seq

        name = (~self.db)[seq]
        assert name == 'user.foo'       # created a new 'user' db.

        # ok, make sure it doesn't wipe out the old 'user' db...
        seq2 = Sequence('ATGGCAGG', 'foo2')
        self.db += seq2

        name = (~self.db)[seq2]
        assert name == 'user.foo2'

        first_name = (~self.db)[seq]
        assert first_name == 'user.foo'

    def test_iadd_duplicate_seqdb(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            seqdb2 = SequenceFileDB(dnaseq)
            try:
                new_seq = seqdb['seq1']
                new_seq2 = seqdb2['seq1']

                self.db += new_seq
                try:
                    self.db += new_seq2
                    assert 0, "should never reach this point"
                except ValueError:
                    pass
            finally:
                seqdb2.close()
        finally:
            seqdb.close()

    def test_no_db_info(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            new_seq = seqdb['seq1']

            assert getattr(seqdb, '_persistent_id', None) is None
            del seqdb.filepath

            self.db += new_seq
            name = (~self.db)[new_seq]
            assert name == 'noname0.seq1'
        finally:
            seqdb.close()

    def test_inverse_add_behavior(self):
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            seq = seqdb['seq1']

            name = (~self.db)[seq]
        finally:
            seqdb.close() # only need to close if exception occurs

    def test_inverse_noadd_behavior(self):
        # compare with test_inverse_add_behavior...
        db = SeqPrefixUnionDict(addAll=False)
        dnaseq = testutil.datafile('dnaseq.fasta')
        seqdb = SequenceFileDB(dnaseq)
        try:
            seq = seqdb['seq1']

            try:
                name = (~db)[seq]
                assert 0, "should not get here"
            except KeyError:
                pass
        finally:
            seqdb.close()


class SeqDBCache_Test(unittest.TestCase):

    def test_cache(self):
        "Sequence slice cache mechanics."

        dnaseq = testutil.datafile('dnaseq.fasta')
        db = SequenceFileDB(dnaseq)

        try:
            # create cache components
            cacheDict = {}
            cacheHint = db.cacheHint

            # get seq1
            seq1 = db['seq1']

            # _cache is only created on first cache attempt
            assert not hasattr(db, '_cache')

            # build an 'owner' object
            class AnonymousOwner(object):
                pass
            owner = AnonymousOwner()

            # save seq1 in cache
            cacheDict['seq1'] = (seq1.start, seq1.stop)
            cacheHint(cacheDict, owner)
            del cacheDict                   # 'owner' now holds reference

            # peek into _cache and assert that only the ival coordinates
            # are stored
            v = db._cache.values()[0]
            assert len(v['seq1']) == 2
            del v

            # force a cache access & check that now we've stored actual string
            ival = str(seq1[5:10])
            v = db._cache.values()[0]
            # ...check that we've stored actual string
            assert len(v['seq1']) == 3

            # again force cache access, this time to the stored sequence string
            ival = str(seq1[5:10])

            # now, eliminate all references to the cache proxy dict
            del owner

            # trash unused objects - not strictly necessary, because there are
            # no islands of circular references & so all objects are already
            # deallocated, but that's implementation dependent.
            gc.collect()

            # ok, cached values should now be gone.
            v = db._cache.values()
            assert len(v) == 0
        finally:
            db.close()

    def test_nlmsaslice_cache(self):
        "NLMSASlice sequence caching & removal"

        # set up sequences
        dnaseq = testutil.datafile('dnaseq.fasta')

        db = SequenceFileDB(dnaseq, autoGC=-1) # use pure WeakValueDict...
        try:
            gc.collect()
            assert len(db._weakValueDict)==0, '_weakValueDict should be empty'
            seq1, seq2 = db['seq1'], db['seq2']
            assert len(db._weakValueDict)==2, \
                    '_weakValueDict should have 2 seqs'

            # build referencing NLMSA
            mymap = NLMSA('test', 'memory', db, pairwiseMode=True)
            mymap += seq1
            mymap[seq1] += seq2
            mymap.build()

            # check: no cache
            assert not hasattr(db, '_cache'), 'should be no cache yet'

            seq1, seq2 = db['seq1'], db['seq2'] # re-retrieve
            # now retrieve a NLMSASlice, forcing entry of seq into cache
            ival = seq1[5:10]
            x = mymap[ival]

            assert len(db._cache.values()) != 0

            n1 = len(db._cache)
            assert n1 == 1, "should be exactly one cache entry, not %d" % \
                    (n1, )

            # ok, now trash referencing arguments & make sure of cleanup
            del x
            gc.collect()

            assert len(db._cache.values()) == 0


            n2 = len(db._cache)
            assert n2 == 0, '%d objects remain; cache memory leak!' % n2
            # FAIL because of __dealloc__ error in cnestedlist.NLMSASlice.

            # Drop our references, the cache should empty.
            del mymap, ival, seq1, seq2
            gc.collect()
            # check that db._weakValueDict cache is empty
            assert len(db._weakValueDict)==0, '_weakValueDict should be empty'
        finally:
            db.close()

if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
