"""Tests for Kraken fleet simulator."""
import unittest
from research_lab.kraken_robot_sim import MAX_AGENTS, simulate

class KrakenTests(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(simulate(4, 5), simulate(4, 5))
    def test_no_actuation(self):
        data = simulate(8, 2)
        self.assertEqual(data["physical_devices"], 0)
        self.assertFalse(data["network_enabled"])
        self.assertFalse(data["weapons"])
    def test_reject_unbounded_counts(self):
        with self.assertRaises(ValueError):
            simulate(999999999999, 1)
        with self.assertRaises(ValueError):
            simulate(MAX_AGENTS, 1001)

if __name__ == "__main__":
    unittest.main()
