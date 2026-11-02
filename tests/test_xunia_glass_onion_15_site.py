"""XUNIA Glass Onion 15-source site gate; standard library, no network."""
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ATLAS = ROOT / "docs/darkweb/15-source-atlas/index.html"
DARKWEB = ROOT / "docs/darkweb/index.html"
HQ = ROOT / "docs/index.html"
RESOURCES = ROOT / "docs/resources.json"
CATALOG = ROOT / "catalog/glass-onion-15.json"
JS = ROOT / "docs/darkweb/15-source-atlas/atlas.js"
CSS = ROOT / "docs/darkweb/15-source-atlas/atlas.css"

class XuniaGlassOnionAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = ATLAS.read_text(encoding="utf-8")
        cls.catalog = json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_15_source_slots(self):
        self.assertEqual(len(self.catalog["slots"]), 15)
        self.assertEqual(sum(len(x["selectedRepos"]) for x in self.catalog["slots"]), 16)

    def test_page_data_matches_catalog(self):
        match = re.search(r'<script id="inventory" type="application/json">(.*?)</script>', self.html, re.S)
        self.assertIsNotNone(match)
        self.assertEqual(json.loads(match.group(1)), self.catalog)

    def test_page_is_self_contained(self):
        self.assertIn('href="./atlas.css"', self.html)
        self.assertIn('src="./atlas.js"', self.html)
        self.assertTrue(JS.exists() and CSS.exists())
        self.assertNotIn('<script src="http', self.html)

    def test_homepage_link(self):
        self.assertIn('href="./darkweb/15-source-atlas/"', HQ.read_text(encoding="utf-8"))

    def test_glass_onion_workbench_link(self):
        self.assertIn('href="./15-source-atlas/"', DARKWEB.read_text(encoding="utf-8"))

    def test_resource_registry(self):
        items = json.loads(RESOURCES.read_text(encoding="utf-8"))["items"]
        matching = [x for x in items if x["id"] == "xunia-glass-onion-15-source-atlas"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0]["url"], "./darkweb/15-source-atlas/")
        self.assertTrue(matching[0]["free"])

    def test_no_source_execution(self):
        for slot in self.catalog["slots"]:
            policy = slot["policy"]
            self.assertFalse(policy["allowExecution"])
            self.assertFalse(policy["allowAutoCloning"])
            self.assertFalse(policy["allowCredentialCollection"])
            self.assertFalse(policy["allowTargetScanning"])
        self.assertIn("NO AUTO-CLONE", JS.read_text(encoding="utf-8"))

    def test_navigation(self):
        self.assertIn('href="../../"', self.html)
        self.assertIn('href="../"', self.html)

if __name__ == "__main__":
    unittest.main()
