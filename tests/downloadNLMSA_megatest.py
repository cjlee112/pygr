import ConfigParser
import os.path
import shutil
import tempfile
import threading
import time
import unittest

from pygr import metabase
from pygr.downloader import SourceURL
from pygr.nlmsa_utils import NLMSABuilder
from testlib import megatest_utils, testutil, PygrTestProgram


def create_downloadable_resource(url, mdb, name, doc):
    dfile = SourceURL(url)
    nbuilder = NLMSABuilder(dfile)
    nbuilder.__doc__ = doc
    mdb.add_resource(name, nbuilder)
    mdb.commit()


class NLMSADownload_Test(unittest.TestCase):
    '''Try to download and build a relatively large alignment'''

    def setUp(self):
        config = ConfigParser.ConfigParser({'testOutputBaseDir': '.',
                                            'httpdPort': 28145})
        config.read([os.path.join(os.path.expanduser('~'), '.pygrrc'),
                     os.path.join(os.path.expanduser('~'), 'pygr.cfg'),
                     '.pygrrc', 'pygr.cfg'])
        httpdPort = config.get('megatests_download', 'httpdPort')
        httpdServedFile = config.get('megatests_download', 'httpdServedFile')
        testOutputBaseDir = config.get('megatests', 'testOutputBaseDir')

        self.resource_name = 'Test.NLMSA'

        server_addr = ('127.0.0.1', httpdPort) # FIXME: randomise the port?
        self.httpd = megatest_utils.HTTPServerLauncher(server_addr,
                                                       httpdServedFile)
        server_thread = threading.Thread(target=self.httpd.run)
        server_thread.setDaemon(True)
        server_thread.start()

        self.test_dir = tempfile.mkdtemp(dir=testOutputBaseDir,
                                         prefix='megatest')
        dl_dir = os.path.join(self.test_dir, 'dl')
        os.mkdir(dl_dir)
        if 'WORLDBASEDOWNLOAD' in os.environ:
            self.old_download = os.environ['WORLDBASEDOWNLOAD']
        else:
            self.old_download = None
        os.environ['WORLDBASEDOWNLOAD'] = self.test_dir
        if 'WORLDBASEBUILDDIR' in os.environ:
            self.old_builddir = os.environ['WORLDBASEBUILDDIR']
        else:
            self.old_builddir = None
        os.environ['WORLDBASEBUILDDIR'] = self.test_dir

        self.mdb = metabase.MetabaseList(self.test_dir)
        self.mdb_dl = metabase.MetabaseList(dl_dir)
        url = 'http://%s:%d/' % server_addr + os.path.basename(httpdServedFile)
        create_downloadable_resource(url, self.mdb_dl, self.resource_name,
                                     'An example downloadable NLMSA')

    def test_download(self):
        'Test downloading NLMSA data'
        t = time.time()
        msa_dl = self.mdb_dl(self.resource_name)  # download and build it!
        t1 = time.time() - t
        t = time.time()
        self.mdb.add_resource(self.resource_name, msa_dl)
        self.mdb.commit()
        del msa_dl
        msa = self.mdb(self.resource_name)  # already built
        t2 = time.time() - t
        assert t2 < t1/3., 'second request took too long!'
        chr4 = msa.seqDict['dm2.chr4']
        result = msa[chr4[:10000]]
        assert len(result) == 9

    def tearDown(self):
        # Just in case - the server thread is daemonic so it will get
        # terminated when the main one finishes.
        self.httpd.request_shutdown()
        if self.old_download is not None:
            os.environ['WORLDBASEDOWNLOAD'] = self.old_download
        else:
            del os.environ['WORLDBASEDOWNLOAD']
        if self.old_builddir is not None:
            os.environ['WORLDBASEBUILDDIR'] = self.old_builddir
        else:
            del os.environ['WORLDBASEBUILDDIR']
        shutil.rmtree(self.test_dir)


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)
