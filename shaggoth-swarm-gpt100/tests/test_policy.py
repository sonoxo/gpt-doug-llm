import unittest
from shaggoth_swarm.policy import CapabilityPolicy

class PolicyTests(unittest.TestCase):
    def test_default_allows_reasoning(self):
        ok,missing=CapabilityPolicy().check(frozenset({"reason","plan"}))
        self.assertTrue(ok); self.assertFalse(missing)
    def test_default_denies_shell_and_network(self):
        ok,missing=CapabilityPolicy().check(frozenset({"shell","network"}))
        self.assertFalse(ok); self.assertEqual(missing,frozenset({"shell","network"}))
