"""Regression checks for the BioIntel atlas."""
import unittest
from research_lab.biointel_atlas import ENTRIES, query

class BioIntelAtlasTests(unittest.TestCase):
    def test_every_record_has_provenance(self):
        for entry in ENTRIES:
            self.assertTrue(entry.source_title)
            self.assertTrue(entry.source_url.startswith("https://"))
            self.assertTrue(entry.caveat)
    def test_topics_are_filterable(self):
        self.assertEqual(len(query("atlantis")), 1)
        self.assertTrue(query("UAP"))
        self.assertEqual(query("unlisted"), [])
    def test_unknown_hypotheses_not_facts(self):
        for entry in ENTRIES:
            if "extraterrestrial origin" in entry.proposition.lower():
                self.assertEqual(entry.classification, "hypothesis")
                self.assertTrue(entry.caveat)

if __name__ == "__main__":
    unittest.main()
