"""Physarum amoebozoan science, local Brain provenance and site integration."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

from gpt_brain import physarum

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "docs" / "physarum"
APPROVED = {
    "pubmed.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov",
    "link.springer.com", "www.sciencedirect.com",
}


class CL1PhysarumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads((SITE / "ontology.json").read_text())

    def test_taxonomy_and_biology_are_source_qualified(self):
        d = self.data
        self.assertEqual(d["schema"], "xunia.cl1.physarum-ontology.v1")
        self.assertEqual(d["scientific_name"], "Physarum polycephalum")
        self.assertEqual(d["taxonomy"]["supergroup"], "Amoebozoa")
        self.assertFalse(d["taxonomy"]["fungus"])
        self.assertIn("single large cell", d["lifecycle_scope"])
        self.assertEqual(len(d["observational_facts"]), 5)
        self.assertGreaterEqual(len(d["sources"]), 5)
        self.assertGreaterEqual(len(d["nodes"]), 16)
        self.assertGreaterEqual(len(d["links"]), 15)
        ids = {n["id"] for n in d["nodes"]}
        self.assertEqual(len(ids), len(d["nodes"]))
        for edge in d["links"]:
            self.assertIn(edge["from"], ids)
            self.assertIn(edge["to"], ids)
            self.assertIn(edge["type"], d["link_types"])
        sources = {s["id"]: s for s in d["sources"]}
        for fact in d["observational_facts"]:
            self.assertIn(fact["source_id"], sources)
        for source in d["sources"]:
            parsed = urlsplit(source["url"])
            self.assertEqual(parsed.scheme, "https")
            self.assertIn(parsed.hostname, APPROVED)
        self.assertTrue(any("not a fungus" in s.lower() for s in d["boundaries"]))
        self.assertTrue(any("not a calibrated" in s.lower() for s in d["boundaries"]))

    def test_no_implant_and_export_has_explicit_physical_boundary(self):
        d = self.data
        self.assertFalse(d["simulation"]["production_ready"])
        self.assertFalse(d["simulation"]["experimental_predictions"])
        self.assertEqual(d["physicalization"]["format"], "SVG")
        self.assertEqual(d["physicalization"]["size_mm"], [180, 120])
        self.assertIn("no connected", d["physicalization"]["control"].lower())
        html = (SITE / "index.html").read_text()
        js = (SITE / "forge.js").read_text()
        css = (SITE / "style.css").read_text()
        model = (SITE / "model.js").read_text()
        for id_ in (
            "physarumCanvas", "telemetryCanvas", "fieldStatus", "sourceIndex",
            "facts", "growth", "decay", "trailToggle", "brushes",
            "playPause", "stepOne", "stepThirty", "resetNetwork",
            "exportSvg", "exportJson", "savePng", "health",
            "consoleInput", "consoleForm", "consoleStatus",
        ):
            self.assertIn('id="' + id_ + '"', html)
        for mode in ("food", "barrier", "erase", "origin"):
            self.assertIn('data-brush="' + mode + '"', html)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("prefers-reduced-motion", js)
        self.assertEqual(js.count("fetch("), 1)
        for forbidden in (
            "WebSocket(", "XMLHttpRequest", "innerHTML", "eval(",
            "navigator.mediaDevices", "navigator.serial",
            "navigator.usb", "navigator.vibrate", "localStorage",
        ):
            self.assertNotIn(forbidden, js)
            self.assertNotIn(forbidden, model)
        self.assertIn("width", model)
        self.assertIn("180mm", html)
        self.assertIn("no hardware", html.lower())
        self.assertIn("Flow", html)

    def test_brain_local_retrieval_references_scientific_sources(self):
        self.assertTrue(physarum.applies("Physarum polycephalum"))
        self.assertTrue(physarum.applies("the blob slime mold"))
        self.assertFalse(physarum.applies("Where is the nearest coffee shop?"))
        records = physarum.search("Physarum externalized memory", limit=4)
        self.assertGreaterEqual(len(records), 2)
        self.assertTrue(all(r["path"].startswith("cl1-bio:physarum:") for r in records))
        self.assertTrue(all(r["value"]["source_url"].startswith("https://") for r in records))
        self.assertTrue(all(
            r["value"]["evidence"] == "CURATED_SCIENTIFIC_LITERATURE"
            for r in records
        ))
        self.assertTrue(any("memory" in r["value"]["title"].lower() for r in records))
        self.assertEqual(physarum.search("weather forecast"), [])

    def test_physarum_retrieval_wired_into_brain_kernel(self):
        from gpt_brain.kernel import BrainKernel

        src = (ROOT / "gpt_brain" / "kernel.py").read_text()
        self.assertIn("search_physarum(task", src)
        self.assertIn("ontology_ctx.extend(", src)
        # Same mechanism preserves source URLs as provenance.
        self.assertIn('row["value"]["source_url"]', src)
        self.assertIsNotNone(BrainKernel)

    def test_xunia_portal_and_research_registry(self):
        paths = {
            "index.html": "./physarum/",
            "synapse/index.html": "../physarum/",
            "fusion/index.html": "../physarum/",
            "biological-data-center/index.html": "../physarum/",
        }
        for path, link in paths.items():
            self.assertIn(
                'href="' + link + '"',
                (ROOT / "docs" / path).read_text(),
                msg=path,
            )
        reg = json.loads((ROOT / "docs" / "resources.json").read_text())
        items = [
            r for r in reg["items"] if r["id"] == "cl1-physarum-network-forge"
        ]
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["free"] and items[0]["interactive"])
        self.assertEqual(items[0]["url"], "./physarum/")
        idx = json.loads((ROOT / "docs" / "docs-index.json").read_text())
        self.assertEqual(
            idx["publicSurfaces"]["physarumForge"],
            "https://xunia.org/physarum/",
        )


if __name__ == "__main__":
    unittest.main()
