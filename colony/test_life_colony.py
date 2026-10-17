import tempfile
import unittest
from pathlib import Path
from colony.life_colony import Colony, Evidence

class ColonyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.colony = Colony(str(Path(self.temp.name) / "colony.db"))
    def tearDown(self):
        self.colony.close()
        self.temp.cleanup()
    def test_life_domains_and_agents(self):
        s = self.colony.status()
        self.assertEqual(len(s["agents"]), 5)
        self.assertEqual(len(s["life_domains"]), 8)
        self.assertFalse(s["wetlab_enabled"])
    def test_evidence_is_deduplicated(self):
        item = Evidence("cellular", "membrane", "Source-backed claim", "doi:example", confidence=.5)
        self.assertEqual(self.colony.ingest(item), self.colony.ingest(item))
        self.assertEqual(self.colony.status()["evidence_records"], 1)
    def test_proposals_remain_unapproved(self):
        result = self.colony.propose("gpt-organoid", "cellular", "Review published literature")
        self.assertEqual(result["status"], "needs_evidence")
        self.assertEqual(result["evidence_ids"], [])
    def test_agent_scoping(self):
        with self.assertRaises(ValueError):
            self.colony.propose("gpt-humanoid", "molecular", "Question")
    def test_reject_unverified_source(self):
        with self.assertRaises(ValueError):
            self.colony.ingest(Evidence("molecular", "DNA", "Claim", "", confidence=.4))

if __name__ == "__main__":
    unittest.main()
