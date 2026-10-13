"""Tests for non-operational Lattice-preview serialization."""
import unittest
from research_lab.kraken_lattice_preview import make_snapshot

class LatticePreviewTests(unittest.TestCase):
    def test_preview_synthetic(self):
        data = make_snapshot(4, 2)
        self.assertFalse(data["compatible_with_lattice_api"])
        self.assertEqual(data["robot_count"], 4)
        self.assertTrue(all(x["synthetic"] for x in data["entity_previews"]))

    def test_repeatable(self):
        self.assertEqual(make_snapshot(3, 2), make_snapshot(3, 2))

    def test_unbounded_rejected(self):
        with self.assertRaises(ValueError):
            make_snapshot(999999999999, 1)

if __name__ == "__main__":
    unittest.main()
