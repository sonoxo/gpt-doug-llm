import tempfile
import unittest
from pathlib import Path

from colony.biochip_cells import CellColony, MAX_CELLS


class BiochipCellsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / "cells.sqlite3")
        self.colony = CellColony(self.path, max_cells=12)

    def tearDown(self):
        self.colony.close()
        self.temp.cleanup()

    def test_seed_and_persistence(self):
        self.assertEqual(self.colony.seed(4)["active"], 4)
        self.assertEqual(self.colony.summary()["total"], 4)

    def test_tick_preserves_abstract_state(self):
        self.colony.seed(2)
        result = self.colony.tick(0.8, 0.2)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["physical_cells_created"], 0)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.colony.tick(2, 0)
        with self.assertRaises(ValueError):
            self.colony.seed(-1)
        with self.assertRaises(ValueError):
            self.colony.seed(1.5)

    def test_seed_cannot_exceed_configured_limit(self):
        self.colony.seed(10)
        with self.assertRaises(ValueError):
            self.colony.seed(3)
        self.assertEqual(self.colony.summary()["total"], 10)

    def test_sustained_reproduction_stops_at_hard_limit(self):
        self.colony.seed(2)
        for _ in range(100):
            result = self.colony.tick(nutrition=1.0, stimulus=0.0)
            self.assertLessEqual(result["total"], 12)
        self.assertEqual(result["total"], 12)
        self.assertTrue(result["population_limit_reached"])

    def test_population_limit_configuration_is_validated(self):
        with self.assertRaises(ValueError):
            CellColony(self.path, max_cells=MAX_CELLS + 1)
        with self.assertRaises(ValueError):
            CellColony(self.path, max_cells=0)

    def test_all_state_values_remain_bounded(self):
        self.colony.seed(3)
        for _ in range(10):
            self.colony.tick(1, 1)
        for cell in self.colony.cells():
            self.assertTrue(0 <= cell.energy <= 1)
            self.assertTrue(0 <= cell.membrane <= 1)
            self.assertTrue(0 <= cell.stress <= 1)
            self.assertTrue(0 <= cell.signaling <= 1)

    def test_database_persists_across_instances(self):
        self.colony.seed(4)
        self.colony.close()
        self.colony = CellColony(self.path, max_cells=12)
        self.assertEqual(self.colony.summary()["total"], 4)


if __name__ == "__main__":
    unittest.main()
