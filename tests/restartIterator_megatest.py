import unittest
from testlib import testutil, PygrTestProgram
from pygr import worldbase

class RestartIterator_Test(unittest.TestCase):
    def setUp(self):
        self.msa = worldbase("Bio.MSA.UCSC.dm3_multiz15way")
        genome = worldbase("Bio.Seq.Genome.DROME.dm3")
        self.seq = -genome['chr3L'][10959977:10959996]

    def test_restartIterator(self):
        try:
            self.msa[self.seq]
        except KeyError:
            # Shouldn't happen here but a valid response
            pass


if __name__ == '__main__':
    PygrTestProgram(verbosity=2)

