import unittest
from shaggoth_swarm.registry import build_registry

class RegistryTests(unittest.TestCase):
    def test_builds_100_unique_agents(self):
        agents=build_registry(100)
        self.assertEqual(len(agents),100)
        self.assertEqual(len({a.id for a in agents}),100)
    def test_rejects_out_of_range_counts(self):
        with self.assertRaises(ValueError): build_registry(0)
        with self.assertRaises(ValueError): build_registry(101)
