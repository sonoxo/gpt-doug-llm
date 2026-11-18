"""Offline CL1 Planetary Forge provenance, reference preservation and browser-surface tests."""
from __future__ import annotations
import json
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORGE = ROOT / "docs" / "cosmos" / "planets"
PLANETS = ["mercury", "venus", "earth", "mars", "jupiter", "saturn", "uranus", "neptune"]


class PlanetForgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((FORGE/"catalog.json").read_text(encoding="utf-8"))
        cls.planets = cls.catalog["planets"]
        cls.byid = {p["id"]: p for p in cls.planets}

    def test_source_record_schema_and_provenance(self):
        self.assertEqual(self.catalog["schema"], "xunia.cl1.planet-twins.v1")
        self.assertEqual(list(self.byid), PLANETS)
        self.assertEqual(len(self.planets), 8)
        self.assertEqual(self.catalog["valid_from"], "1800-01-01")
        self.assertEqual(self.catalog["valid_through"], "2050-12-31")
        self.assertIn("nssdc.gsfc.nasa.gov", self.catalog["sources"]["physical"])
        self.assertIn("ssd.jpl.nasa.gov", self.catalog["sources"]["orbital"])
        self.assertIn("barycenter", self.catalog["coordinate_frame"].lower())

    def test_sourced_physical_properties_and_retrograde_spin(self):
        self.assertEqual(self.byid["earth"]["diameter_km"], 12756)
        self.assertEqual(self.byid["jupiter"]["diameter_km"], 142984)
        self.assertEqual(self.byid["neptune"]["gravity_ms2"], 11.0)
        self.assertEqual(self.byid["saturn"]["ring_system"], True)
        self.assertLess(self.byid["venus"]["rotation_hours"], 0)
        self.assertLess(self.byid["uranus"]["rotation_hours"], 0)
        for p in self.planets:
            self.assertGreater(p["diameter_km"], 2000)
            self.assertGreater(p["mass_1e24_kg"], 0)
            self.assertGreater(p["gravity_ms2"], 0)
            self.assertEqual(len(p["render_palette"]), 2)
            self.assertEqual(p["physical_source"], self.catalog["sources"]["physical"])
            self.assertEqual(p["orbital_source"], self.catalog["sources"]["orbital"])

    def test_jpl_keplerian_elements_and_century_rates(self):
        self.assertAlmostEqual(self.byid["mercury"]["elements_j2000"][0], .38709927, places=8)
        self.assertAlmostEqual(self.byid["earth"]["elements_j2000"][0], 1.00000261, places=8)
        self.assertAlmostEqual(self.byid["neptune"]["elements_j2000"][0], 30.06992276, places=8)
        self.assertAlmostEqual(self.byid["jupiter"]["rates_per_century"][3], 3034.74612775, places=6)
        for p in self.planets:
            e=p["elements_j2000"]; rates=p["rates_per_century"]
            self.assertEqual(len(e), 6)
            self.assertEqual(len(rates), 6)
            self.assertTrue(all(isinstance(v, (int,float)) and math.isfinite(v) for v in e+rates))
            self.assertGreater(e[0], 0)
            self.assertGreaterEqual(e[1], 0)
            self.assertLess(e[1], 1)
            self.assertLess(abs(e[2]), 15)
            self.assertTrue(all(.0 < e[0]+rates[0]*T for T in (-2, .5)))

    def test_public_controls_and_nonkinetic_boundary(self):
        html=(FORGE/"index.html").read_text(encoding="utf-8")
        js=(FORGE/"planets.js").read_text(encoding="utf-8")
        css=(FORGE/"style.css").read_text(encoding="utf-8")
        for el in ("planetList","orrery","globe","createClone","removeClone",
                   "cloneRadius","cloneSpin","cloneGlow","exportClone",
                   "epochDate","playPause","timeSpeed","commandInput","commandStatus"):
            self.assertIn('id="'+el+'"',html)
        for logic in ("orbitalCoords(","elementsAt(","renderOrbits(",
                      "renderGlobe(","clonePlanet(","dispatch(raw)",
                      "function setDate(","state.clones.length>=4"):
            self.assertIn(logic,js)
        self.assertIn("getContext(\"2d\")",js)
        self.assertIn("prefers-reduced-motion",css)
        self.assertIn("hypothetical",html.lower())
        self.assertIn("NON-KINETIC",html)
        self.assertIn('fetch("./catalog.json"',js)
        self.assertEqual(js.count("fetch("),1)
        for forbidden in ("eval(", "new Function(", "innerHTML", "WebSocket(",
                          "navigator.bluetooth","navigator.serial","navigator.usb",
                          "api.openai.com","vercel"):
            self.assertNotIn(forbidden,js)

    def test_integrated_navigation_from_cosmos_bio_and_hq(self):
        cosmos=(ROOT/"docs"/"cosmos"/"index.html").read_text(encoding="utf-8")
        bio=(ROOT/"docs"/"biological-data-center"/"index.html").read_text(encoding="utf-8")
        hq=(ROOT/"docs"/"index.html").read_text(encoding="utf-8")
        resources=json.loads((ROOT/"docs"/"resources.json").read_text(encoding="utf-8"))
        self.assertIn("./planets/",cosmos)
        self.assertIn("../cosmos/planets/",bio)
        self.assertIn("./cosmos/planets/",hq)
        entry=[x for x in resources["items"] if x["id"]=="cl1-planetary-forge"]
        self.assertEqual(len(entry),1)
        self.assertTrue(entry[0]["free"] and entry[0]["interactive"])
        self.assertEqual(entry[0]["url"],"./cosmos/planets/")


if __name__ == "__main__":
    unittest.main()
