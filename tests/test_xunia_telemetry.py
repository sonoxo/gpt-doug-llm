"""Source-qualified linear and kinetic telemetry ontology contracts for XUNIA."""
from __future__ import annotations

import json
import unittest
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ATLAS = DOCS / "telemetry"


class CL1TelemetryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry = json.loads((ATLAS / "registry.json").read_text())
        cls.physarum = json.loads(
            (DOCS / "physarum" / "ontology.json").read_text()
        )

    def test_linear_signals_are_provenance_labeled_simulation(self):
        d = self.registry
        self.assertEqual(d["schema"], "xunia.cl1.telemetry-ontology.v1")
        self.assertEqual(d["source_model"], "../physarum/model.js")
        self.assertEqual(d["source_ontology"], "../physarum/ontology.json")
        self.assertFalse(d["physical_actuation"])
        self.assertFalse(d["network_credentials"])
        self.assertEqual(d["display"]["max_history"], 240)
        self.assertEqual(len(d["metrics"]), 7)
        self.assertEqual(
            {m["id"] for m in d["metrics"]},
            {"flux", "tubes", "conductance", "energy",
             "motion", "delta", "pressure"},
        )
        source_ids = {s["id"] for s in self.physarum["sources"]}
        for metric in d["metrics"]:
            self.assertIn(metric["evidence"], {"SIMULATED", "DERIVED_SIMULATION"})
            self.assertIn(metric["source_id"], source_ids)
            self.assertTrue(metric["unit"])
            self.assertTrue(metric["description"])
        for source in d["sources"]:
            url = urlsplit(source["url"])
            self.assertEqual(url.scheme, "https")
            self.assertIn(
                url.hostname,
                {"pubmed.ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov"},
            )

    def test_kinetic_display_distinguishes_relative_speed_from_velocity(self):
        d = self.registry
        boundaries = " ".join(d["boundaries"]).lower()
        self.assertIn("not physical velocity", boundaries)
        self.assertIn("live sensors", boundaries)
        self.assertIn("physical actuator", boundaries)
        self.assertEqual(
            d["display"]["modes"],
            ["kinetic", "linear", "ontology"],
        )
        self.assertEqual(d["display"]["default_metric"], "flux")
        script = (ATLAS / "atlas.js").read_text()
        engine = (ATLAS / "engine.js").read_text()
        self.assertIn("T.vectors(g,120)", script)
        self.assertIn("e.q>=0?e.a:e.b", engine)
        self.assertIn("function drawLinear()", script)
        self.assertIn("function drawOntology()", script)
        self.assertIn("function drawKinetic()", script)
        self.assertIn("function selfTest()", script)
        for forbidden in (
            "XMLHttpRequest", "WebSocket(", "navigator.usb",
            "navigator.serial", "navigator.mediaDevices",
            "navigator.vibrate", "innerHTML", "eval(",
            "localStorage", "api.openai.com",
        ):
            self.assertNotIn(forbidden, script)
            self.assertNotIn(forbidden, engine)

    def test_visual_controls_ontology_and_exports_exist(self):
        html = (ATLAS / "index.html").read_text()
        css = (ATLAS / "style.css").read_text()
        for id_ in (
            "kineticCanvas", "linearCanvas", "ontologyCanvas",
            "ontologyList", "selectedName", "selectedEvidence",
            "selectedSource", "metricSelect", "metricDescription",
            "metricEvidence", "tickValue", "fluxValue", "deltaValue",
            "vectorToggle", "particleToggle", "kineticSpeed",
            "growth", "decay", "playPause", "stepOne", "stepThirty",
            "resetSimulation", "exportCSV", "exportJSON", "exportPNG",
            "health", "commandForm", "commandInput", "commandStatus",
        ):
            self.assertIn('id="' + id_ + '"', html)
        for mode in ("all", "kinetic", "linear", "ontology"):
            self.assertIn('data-focus-mode="' + mode + '"', html)
        for brush in ("inspect", "food", "barrier", "erase"):
            self.assertIn('data-brush="' + brush + '"', html)
        self.assertIn("prefers-reduced-motion", css)
        self.assertIn("prefers-reduced-motion", (ATLAS / "atlas.js").read_text())
        self.assertIn("SIMULATION / NOT LIVE SENSORS.", html)
        self.assertIn("connect-src 'self'", html)
        self.assertIn('src="../physarum/model.js"', html)

    def test_ontology_links_are_current_scientific_ontology(self):
        o = self.physarum
        self.assertEqual(o["schema"], "xunia.cl1.physarum-ontology.v1")
        self.assertEqual(len(o["nodes"]), 16)
        self.assertEqual(len(o["links"]), 17)
        self.assertGreaterEqual(len(o["sources"]), 5)
        self.assertTrue(any(n["verified"] for n in o["nodes"]))
        self.assertTrue(any(not n["verified"] for n in o["nodes"]))

    def test_registered_in_five_existing_xunia_modules(self):
        for path, anchor in (
            ("index.html", "./telemetry/"),
            ("physarum/index.html", "../telemetry/"),
            ("synapse/index.html", "../telemetry/"),
            ("fusion/index.html", "../telemetry/"),
            ("biological-data-center/index.html", "../telemetry/"),
        ):
            self.assertIn(
                'href="' + anchor + '"',
                (DOCS / path).read_text(),
                path,
            )
        sources = json.loads((DOCS / "resources.json").read_text())
        entries = [
            item for item in sources["items"]
            if item["id"] == "cl1-linear-kinetic-telemetry-atlas"
        ]
        self.assertEqual(len(entries), 1)
        self.assertTrue(entries[0]["free"])
        self.assertTrue(entries[0]["interactive"])
        self.assertEqual(entries[0]["url"], "./telemetry/")
        index = json.loads((DOCS / "docs-index.json").read_text())
        self.assertEqual(
            index["publicSurfaces"]["telemetryAtlas"],
            "https://xunia.org/telemetry/",
        )


if __name__ == "__main__":
    unittest.main()
