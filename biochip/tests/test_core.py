"""Unit tests: python -m unittest discover -s biochip/tests -v"""
import tempfile
import time
import unittest
from pathlib import Path
from biochip.core import BioChip

class BioChipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.chip = BioChip(str(Path(self.temp.name) / "memory.sqlite3"))

    def tearDown(self):
        self.temp.cleanup()

    def test_persistence_and_provenance(self):
        self.chip.remember("project", {"name":"doug"}, actor="doug", provenance="user")
        self.assertEqual(self.chip.recall("project", actor="doug")["value"], {"name":"doug"})
        self.assertEqual(BioChip(self.chip.database).recall("project", actor="doug")["provenance"], "user")

    def test_private_memory_rejects_other_agent(self):
        self.chip.remember("secret", 1, actor="doug", provenance="user")
        with self.assertRaises(PermissionError):
            self.chip.recall("secret", actor="other")
        with self.assertRaises(PermissionError):
            self.chip.remember("secret", 2, actor="other", provenance="other")

    def test_shared_memory(self):
        self.chip.remember("public", [1, 2], actor="doug", provenance="test", visibility="shared")
        self.assertEqual(self.chip.recall("public", actor="other")["value"], [1,2])

    def test_ttl_and_heartbeat(self):
        self.chip.remember("temporary", 1, actor="doug", provenance="test", ttl_seconds=0.01)
        time.sleep(0.025)
        self.assertIsNone(self.chip.recall("temporary", actor="doug"))
        self.assertEqual(self.chip.heartbeat()["purged"], 1)

    def test_deletion_and_audit(self):
        self.chip.remember("erase", 1, actor="doug", provenance="test")
        self.assertTrue(self.chip.forget("erase", actor="doug"))
        self.assertIsNone(self.chip.recall("erase", actor="doug"))
        self.assertGreaterEqual(len(self.chip.audit_trail(actor="doug")), 3)

    def test_invalid_inputs(self):
        with self.assertRaises(ValueError):
            self.chip.remember("x", 1, actor="doug", provenance="test", confidence=2)
        with self.assertRaises(ValueError):
            self.chip.remember("x", 1, actor="doug", provenance="test", ttl_seconds=0)

if __name__ == "__main__":
    unittest.main()
