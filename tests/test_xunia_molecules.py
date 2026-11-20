"""Offline scientific provenance, structural graph and app boundaries for CL1 Molecular Observatory."""
from __future__ import annotations

import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MOL = ROOT / "docs" / "molecules"
PERMITTED = {"H", "C", "N", "O", "S", "P", "Cl", "F"}


class MolecularAtlasTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((MOL / "catalogs" / "seed.json").read_text(encoding="utf-8"))
        cls.imported = json.loads(
            (MOL / "catalogs" / "pubchem.json").read_text(encoding="utf-8")
        )
        cls.rows = cls.catalog["molecules"]

    def test_curated_records_are_exact_and_scientifically_bounded(self):
        self.assertEqual(self.catalog["schema"], "xunia.cl1.molecules.v1")
        self.assertEqual(len(self.rows), 33)
        self.assertIn("not exhaustive", self.catalog["scope"])
        self.assertIn("NOT geometry-optimized", self.catalog["geometry_disclaimer"])
        self.assertEqual(self.imported["status"], "not-imported")
        self.assertEqual(self.imported["molecules"], [])
        self.assertEqual(len({row["id"] for row in self.rows}), len(self.rows))
        self.assertEqual(sum(len(m["atoms"]) for m in self.rows), 180)
        self.assertEqual(sum(len(m["bonds"]) for m in self.rows), 148)
        by_name = {m["name"]: m for m in self.rows}
        for name, formula in {
            "Water": "H2O", "Methane": "CH4", "Benzene": "C6H6",
            "Glycine": "C2H5NO2", "Carbon monoxide": "CO",
            "Acetylene": "C2H2", "Formamide": "CH3NO",
        }.items():
            self.assertEqual(by_name[name]["formula"], formula)
        self.assertEqual(by_name["Glycine"]["status"], "chemistry-reference")
        self.assertIn("no astronomical", by_name["Glycine"]["astro_claim"].lower())
        for rec in self.rows:
            self.assertIn(rec["status"], ("chemistry-reference", "astronomical-reference"))
            self.assertTrue(
                rec["source_url"].startswith(
                    ("https://pubchem.ncbi.nlm.nih.gov/",
                     "https://cdms.astro.uni-koeln.de/")
                )
            )
            atoms = {a["id"]: a for a in rec["atoms"]}
            self.assertEqual(len(atoms), len(rec["atoms"]))
            self.assertTrue(all(a["element"] in PERMITTED for a in rec["atoms"]))
            self.assertGreater(rec["molar_mass_gmol"], 0)
            for b in rec["bonds"]:
                self.assertIn(b["a"], atoms)
                self.assertIn(b["b"], atoms)
                self.assertNotEqual(b["a"], b["b"])
                self.assertIn(b["order"], (1, 2, 3))

    def test_pubchem_parser_supports_implicit_hydrogens_and_refuses_bad_bonds(self):
        path = ROOT / "scripts" / "xunia_molecules_import.py"
        spec = importlib.util.spec_from_file_location("xunia_molecules_import", path)
        assert spec is not None and spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for malicious_url in (
            "file:///etc/passwd",
            "http://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/cid/962/JSON",
            "https://evil.example/rest/pug/compound/cid/962/JSON",
        ):
            with self.assertRaisesRegex(ValueError, "non-PubChem"):
                module.fetch_json(malicious_url)
        with self.assertRaisesRegex(ValueError, "redirected"):
            module.RejectRedirects().redirect_request(
                None, None, 302, "Found", {}, "https://evil.example/"
            )
        props = {"PropertyTable": {"Properties": [{
            "CID": 962, "MolecularFormula": "H2O",
            "MolecularWeight": "18.015", "IUPACName": "oxidane",
        }]}}
        structure = {"PC_Compounds": [{
            "atoms": {"aid": [1], "element": [8]},
            "coords": [{"aid": [1], "conformers": [{"x": [0.0], "y": [0.0]}]}],
        }]}
        record = module.parse_cid(962, props, structure)
        self.assertEqual(record["formula"], "H2O")
        self.assertEqual(record["id"], "pubchem-962")
        self.assertEqual(record["atoms"][0]["element"], "O")
        self.assertEqual(record["source_url"], "https://pubchem.ncbi.nlm.nih.gov/compound/962")
        self.assertIn("implicit", record["description"])
        structure["PC_Compounds"][0]["atoms"] = {
            "aid": [1, 2], "element": [6, 6],
        }
        structure["PC_Compounds"][0]["bonds"] = {
            "aid1": [1], "aid2": [2], "order": [4],
        }
        with self.assertRaisesRegex(ValueError, "Unsupported bond order"):
            module.parse_cid(962, props, structure)

    def test_ui_controls_are_real_browser_workflows(self):
        html = (MOL / "index.html").read_text(encoding="utf-8")
        js = (MOL / "molecules.js").read_text(encoding="utf-8")
        css = (MOL / "style.css").read_text(encoding="utf-8")
        for item in (
            "moleculeCanvas", "bondGraph", "moleculeList", "query",
            "sourceLink", "sourceType", "composition", "atomDetails",
            "savePng", "exportJson", "selfTest", "consoleForm",
            "consoleInput", "importState", "speed", "pause",
        ):
            self.assertIn('id="' + item + '"', html)
        for function in (
            "function validate(", "function mapAtoms(", "function draw(",
            "function drawBondGraph(", "function selfTest(",
            "function exportJson(", "function savePng(", "function command(",
        ):
            self.assertIn(function, js)
        self.assertEqual(js.count("fetch("), 2)
        self.assertIn("prefers-reduced-motion", css)
        for prohibited in (
            "innerHTML", "eval(", "new Function(", "WebSocket(",
            "navigator.usb", "navigator.serial", "navigator.bluetooth",
            "localStorage", "vercel",
        ):
            self.assertNotIn(prohibited, js)

    def test_linked_from_all_major_xunia_surfaces(self):
        html_files = {
            "index.html": './molecules/',
            "fusion/index.html": '../molecules/',
            "cosmos/index.html": '../molecules/',
            "biological-data-center/index.html": '../molecules/',
        }
        for path, link in html_files.items():
            self.assertIn(
                'href="' + link + '"',
                (ROOT / "docs" / path).read_text(encoding="utf-8"),
            )
        docs = json.loads((ROOT / "docs" / "docs-index.json").read_text())
        resources = json.loads((ROOT / "docs" / "resources.json").read_text())
        self.assertEqual(
            docs["publicSurfaces"]["molecularObservatory"],
            "https://xunia.org/molecules/",
        )
        matches = [
            item for item in resources["items"]
            if item["id"] == "cl1-molecular-observatory"
        ]
        self.assertEqual(len(matches), 1)
        self.assertTrue(matches[0]["free"] and matches[0]["interactive"])


if __name__ == "__main__":
    unittest.main()
