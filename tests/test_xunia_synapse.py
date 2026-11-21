"""CL1 Sensory Synapse: source truth, five channels, safety and integration contracts."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SYNAPSE = DOCS / "synapse"
APPROVED = {
    "pubchem.ncbi.nlm.nih.gov", "cdms.astro.uni-koeln.de",
    "nssdc.gsfc.nasa.gov", "ssd.jpl.nasa.gov",
    "www.palantir.com", "aws.amazon.com", "docs.aws.amazon.com",
    "www.anduril.com",
}


class SynapseContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.molecules = json.loads(
            (DOCS / "molecules/catalogs/seed.json").read_text()
        )["molecules"]
        cls.planets = json.loads(
            (DOCS / "cosmos/planets/catalog.json").read_text()
        )["planets"]
        cls.ontology = json.loads(
            (DOCS / "fusion/ontology.json").read_text()
        )["nodes"]

    def test_uses_the_existing_three_local_science_and_ontology_catalogs(self):
        self.assertEqual(len(self.molecules), 33)
        self.assertEqual(len(self.planets), 8)
        self.assertEqual(len(self.ontology), 21)
        ids = (
            ["molecule:" + i["id"] for i in self.molecules]
            + ["planet:" + i["id"] for i in self.planets]
            + ["ontology:" + i["id"] for i in self.ontology]
        )
        self.assertEqual(len(set(ids)), 62)
        js = (SYNAPSE / "synapse.js").read_text()
        for url in (
            "../molecules/catalogs/seed.json",
            "../cosmos/planets/catalog.json",
            "../fusion/ontology.json",
        ):
            self.assertIn(url, js)
        self.assertEqual(js.count("fetch("), 1)
        self.assertIn("SOURCE FILE NOT AVAILABLE", js)
        self.assertIn("SYNTHETIC", (SYNAPSE / "index.html").read_text())

    def test_source_boundaries_stay_source_qualified(self):
        for row in self.molecules:
            u = urlparse(row["source_url"])
            self.assertEqual(u.scheme, "https")
            self.assertIn(u.hostname, APPROVED)
        for row in self.planets:
            u = urlparse(row["physical_source"])
            self.assertEqual(u.scheme, "https")
            self.assertIn(u.hostname, APPROVED)
        for row in self.ontology:
            if row.get("source_url"):
                u = urlparse(row["source_url"])
                self.assertIn(u.hostname, APPROVED)

    def test_all_five_sensory_channels_have_real_UI_controls(self):
        html = (SYNAPSE / "index.html").read_text()
        js = (SYNAPSE / "synapse.js").read_text()
        css = (SYNAPSE / "style.css").read_text()
        for channel in ("vision", "sound", "touch", "smell", "taste"):
            self.assertIn('data-sense="' + channel + '"', html)
            self.assertIn('id="' + channel + 'Text"', html)
        for component in (
            "neuralCanvas", "sourceList", "sourceSearch", "sourceType",
            "fieldStatus", "intensity", "intensityValue", "pause", "pulse",
            "audioToggle", "speak", "silence", "audioStatus",
            "resetChannels", "objectSource", "objectName", "eventLog",
            "exportJson", "savePng", "selfTest", "commandInput",
        ):
            self.assertIn('id="' + component + '"', html)
        for view in ("synapse", "cortex", "field"):
            self.assertIn('data-view="' + view + '"', html)
        self.assertIn("prefers-reduced-motion", js)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("56", js)
        self.assertIn("112", js)
        self.assertIn("function selfTest(", js)
        self.assertIn("function silence(", js)
        self.assertIn("function speak(", js)
        self.assertIn("function exportJson(", js)
        self.assertIn('connect-src \'self\'', html)
        self.assertIn("This interface does not read thoughts", html)
        for forbidden in (
            "XMLHttpRequest", "WebSocket(", "navigator.bluetooth",
            "navigator.usb", "navigator.serial", "navigator.vibrate",
            "navigator.mediaDevices", "innerHTML", "eval(",
            "localStorage", "api.openai.com", "vercel",
        ):
            self.assertNotIn(forbidden, js)

    def test_route_registered_across_site(self):
        paths = {
            "index.html": './synapse/',
            "fusion/index.html": '../synapse/',
            "biological-data-center/index.html": '../synapse/',
            "molecules/index.html": '../synapse/',
        }
        for path, url in paths.items():
            self.assertIn('href="' + url + '"', (DOCS / path).read_text())
        registry = json.loads((DOCS / "resources.json").read_text())
        entries = [
            row for row in registry["items"]
            if row["id"] == "cl1-sensory-synapse"
        ]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["interactive"] and entries[0]["free"])
        index = json.loads((DOCS / "docs-index.json").read_text())
        self.assertEqual(
            index["publicSurfaces"]["sensorySynapse"],
            "https://xunia.org/synapse/",
        )


if __name__ == "__main__":
    unittest.main()
