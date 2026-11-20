"""CL1 Fusion — source/provenance/ontology/browser security contracts."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
FUSION = DOCS / "fusion"
DOMAINS = {"cloud": 7, "ops": 7, "ontology": 7}
TRUST = {"cloud": "proposed", "ops": "synthetic", "ontology": "schema"}


class FusionAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ontology = json.loads((FUSION / "ontology.json").read_text(encoding="utf-8"))
        cls.planet_data = json.loads(
            (DOCS / "cosmos" / "planets" / "catalog.json").read_text(encoding="utf-8")
        )

    def test_distinguishes_real_nasa_from_vendor_designs(self):
        d = self.ontology
        self.assertEqual(d["schema"], "xunia.cl1.fusion-ontology.v1")
        self.assertEqual(len(d["nodes"]), 21)
        self.assertEqual(len(d["links"]), 27)
        self.assertEqual(self.planet_data["schema"], "xunia.cl1.planet-twins.v1")
        self.assertEqual(len(self.planet_data["planets"]), 8)
        self.assertIn("no AWS account", d["boundaries"]["cloud"])
        self.assertIn("no Lattice credentials", d["boundaries"]["operations"])
        self.assertIn("not a Foundry instance", d["boundaries"]["ontology"])
        for group, count in DOMAINS.items():
            nodes = [n for n in d["nodes"] if n["group"] == group]
            self.assertEqual(len(nodes), count)
            self.assertTrue(all(n["status"] == TRUST[group] for n in nodes))
        self.assertIn("ssd.jpl.nasa.gov", d["sources"]["jpl"])
        self.assertIn("palantir.com", d["sources"]["palantir"])
        self.assertIn("anduril.com", d["sources"]["anduril"])

    def test_links_are_typed_and_resolvable(self):
        d = self.ontology
        ids = {n["id"] for n in d["nodes"]}
        nasa_ids = {"nasa-" + p["id"] for p in self.planet_data["planets"]}
        self.assertEqual(len(ids), 21)
        self.assertEqual(len(nasa_ids), 8)
        self.assertEqual(len(ids | nasa_ids), 29)
        self.assertEqual(len({(e["source"], e["target"], e["type"]) for e in d["links"]}), 27)
        for edge in d["links"]:
            self.assertIn(edge["source"], ids | nasa_ids)
            self.assertIn(edge["target"], ids | nasa_ids)
            self.assertIn(edge["type"], d["link_types"])
            self.assertTrue(edge["basis"])
        self.assertIn("instanceOf", d["link_types"])
        self.assertIn("derivedFrom", d["link_types"])

    def test_source_boundary_and_ui_controls(self):
        html = (FUSION / "index.html").read_text(encoding="utf-8")
        js = (FUSION / "fusion.js").read_text(encoding="utf-8")
        css = (FUSION / "style.css").read_text(encoding="utf-8")
        for identifier in (
            "atlas", "emblem", "viewModes", "domainControls", "search",
            "entityName", "related", "officialSource", "epoch", "advance",
            "trace", "exportJson", "savePng", "selfTest", "commandForm",
            "actionStatus", "eventLog", "planetFacts",
        ):
            self.assertIn('id="' + identifier + '"', html)
        for view in ("fusion", "orbits", "architecture", "operations"):
            self.assertIn('data-view="' + view + '"', html)
        for domain in ("nasa", "cloud", "ops", "ontology"):
            self.assertIn('data-domain="' + domain + '"', html)
        for fragment in (
            "function validateLocal(", "function positionAt(",
            "function drawOrbits(", "function draw(", "function inspect(",
            "function trace(", "function exportJson(", "function selfTest(",
            "function sourceAllowed(", "function command(",
        ):
            self.assertIn(fragment, js)
        self.assertIn('fetch("./ontology.json"', js)
        self.assertIn('fetch("../cosmos/planets/catalog.json"', js)
        self.assertEqual(js.count("fetch("), 2)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("NON-KINETIC", html)
        for forbidden in (
            "eval(", "new Function(", "innerHTML", "WebSocket(",
            "navigator.usb", "navigator.serial", "navigator.bluetooth",
            "localStorage", "api.openai.com", "vercel",
        ):
            self.assertNotIn(forbidden, js)

    def test_existing_public_surfaces_discover_fusion(self):
        hq = (DOCS / "index.html").read_text(encoding="utf-8")
        cosmos = (DOCS / "cosmos" / "index.html").read_text(encoding="utf-8")
        bio = (DOCS / "biological-data-center" / "index.html").read_text(
            encoding="utf-8"
        )
        registry = json.loads((DOCS / "resources.json").read_text(encoding="utf-8"))
        index = json.loads((DOCS / "docs-index.json").read_text(encoding="utf-8"))
        self.assertIn('href="./fusion/"', hq)
        self.assertIn('href="../fusion/"', cosmos)
        self.assertIn('href="../fusion/"', bio)
        self.assertEqual(
            index["publicSurfaces"]["fusionAtlas"],
            "https://xunia.org/fusion/",
        )
        items = [x for x in registry["items"] if x["id"] == "cl1-fusion-intelligence-atlas"]
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["free"] and items[0]["interactive"])


if __name__ == "__main__":
    unittest.main()
