import tempfile
import unittest
from pathlib import Path
from colony.biochip_cells import CellColony

class BiochipCellsTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.colony=CellColony(str(Path(self.temp.name)/"cells.sqlite3"))
    def tearDown(self):
        self.colony.close()
        self.temp.cleanup()
    def test_seed_and_persistence(self):
        self.assertEqual(self.colony.seed(4)["active"],4)
        self.assertEqual(self.colony.summary()["total"],4)
    def test_tick(self):
        self.colony.seed(2)
        result=self.colony.tick(.8,.2)
        self.assertEqual(result["total"],2)
        self.assertEqual(result["physical_cells_created"],0)
    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.colony.tick(2,0)
        with self.assertRaises(ValueError):
            self.colony.seed(-1)
    def test_abstract_state_bounded(self):
        self.colony.seed(3)
        for _ in range(10):
            self.colony.tick(1,1)
        for c in self.colony.cells():
            self.assertTrue(0<=c.energy<=1)
            self.assertTrue(0<=c.membrane<=1)
            self.assertTrue(0<=c.stress<=1)

if __name__=="__main__":
    unittest.main()
