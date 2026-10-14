import math
import tempfile
import unittest
from pathlib import Path

from research_lab.orca_neurocloud import NeuroGraph, NeuroCloud, BrainMemory


class NeuroCloudTests(unittest.TestCase):
    def test_deterministic_graph(self):
        a, b = NeuroGraph(8), NeuroGraph(8)
        for _ in range(5):
            self.assertEqual(a.tick([0.3] * 8), b.tick([0.3] * 8))

    def test_rejects_invalid_stimuli(self):
        graph = NeuroGraph(4)
        for values in ([float("nan")] * 4, [2.0] * 4, [0.0]):
            with self.assertRaises(ValueError):
                graph.tick(values)

    def test_simulated_pose_and_memory(self):
        cloud = NeuroCloud(12)
        outcome = cloud.cycle()
        self.assertTrue(outcome["humanoid"]["simulation"])
        self.assertEqual(len(outcome["humanoid"]["joint_angles_degrees"]), 9)
        self.assertEqual(outcome["neural"]["neurons"], 12)
        self.assertEqual(len(cloud.memory.recent()), 1)

    def test_persistent_memory_dedup(self):
        with tempfile.TemporaryDirectory() as path:
            db = str(Path(path) / "mem.sqlite3")
            store = BrainMemory(db)
            first = store.add("sample", {"value": 1})
            second = store.add("sample", {"value": 1})
            self.assertEqual(first, second)
            self.assertEqual(len(BrainMemory(db).recent()), 1)

    def test_bounds(self):
        with self.assertRaises(ValueError):
            NeuroGraph(1000)


if __name__ == "__main__":
    unittest.main()
