"""XUNIA COSMOS source-backed 3D ontology and bounded NASA/ESA importer tests."""
from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("xunia_cosmos_import", ROOT/"scripts"/"xunia_cosmos_import.py")
assert SPEC is not None and SPEC.loader
imp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(imp)


class CosmosTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ROOT/"docs"/"cosmos"
        cls.seed = json.loads((cls.root/"catalogs"/"seed.json").read_text(encoding="utf-8"))

    def test_curated_objects_have_valid_containment_and_links(self):
        data=self.seed
        self.assertEqual(data["schema"],"xunia.cosmos.catalog.v1")
        self.assertGreaterEqual(len(data["nodes"]),50)
        self.assertEqual(len(data["edges"]),len(data["nodes"])-1)
        ids={n["id"] for n in data["nodes"]}
        self.assertEqual(len(ids),len(data["nodes"]))
        self.assertTrue(all(e["source"] in ids and e["target"] in ids for e in data["edges"]))
        self.assertEqual(data["coordinate_system"],
                         "illustrative-spatial-layout-not-measured-positions-or-distances")
        sectors={n["sector"] for n in data["nodes"]}
        self.assertTrue({"SOLAR_SYSTEM","EXOPLANETS","GALAXIES","NEBULAE",
                         "STARS","BLACK_HOLES","STRUCTURES","MISSIONS"}.issubset(sectors))
        for n in data["nodes"]:
            self.assertEqual(len(n["layout"]),3)
            self.assertTrue(all(isinstance(v,(float,int)) and math.isfinite(v) for v in n["layout"]))
            self.assertTrue(n["source_url"].startswith("https://"))
            self.assertIn("schematic", n["evidence"])

    def test_nasa_exoplanet_host_relations(self):
        rows=[
            {"pl_name":"Test b","hostname":"Test","ra":15.0,"dec":-24.0,
             "sy_dist":4.1,"pl_rade":1.3,"disc_year":2022},
            {"pl_name":"Test c","hostname":"Test","ra":15.0,"dec":-24.0,
             "sy_dist":4.1,"pl_rade":2.1,"disc_year":2023},
            {"pl_name":"Test b","hostname":"Test","ra":15.0,"dec":-24.0,
             "sy_dist":4.1}
        ]
        nodes,edges=imp.nasa_rows(rows,100)
        self.assertEqual(len(nodes),3)
        self.assertEqual(len(edges),2)
        hosts=[x for x in nodes if x["sector"]=="STARS"]
        planets=[x for x in nodes if x["sector"]=="EXOPLANETS"]
        self.assertEqual(len(hosts),1)
        self.assertEqual(len(planets),2)
        self.assertTrue(all(x["parent"]==hosts[0]["id"] for x in planets))
        self.assertEqual(planets[0]["distance_pc"],4.1)
        self.assertTrue(all(x["source_url"]==imp.SOURCE_HOME["nasa"] for x in nodes))
        self.assertEqual({e["relation"] for e in edges},{"hosts"})
        artifact=imp.build("nasa",rows,100)
        self.assertEqual(len(artifact["nodes"]),3)
        self.assertIn("not true scale",artifact["coordinate_system"])

    def test_gaia_dr3_stellar_sources_and_parallax(self):
        rows=[{"source_id":"123456789","ra":"42.1","dec":"-3.9","parallax":"40",
               "phot_g_mean_mag":"8.7"},
              {"source_id":"123456789","ra":"42.1","dec":"-3.9","parallax":"40"},
              {"source_id":"bad","ra":"", "dec":"", "parallax":"-1"}]
        nodes,edges=imp.gaia_rows(rows,100)
        self.assertEqual(len(nodes),1)
        self.assertEqual(edges,[])
        self.assertEqual(nodes[0]["id"],"gaia-dr3-123456789")
        self.assertEqual(nodes[0]["distance_pc_estimate"],25.0)
        self.assertEqual(nodes[0]["g_magnitude"],8.7)
        self.assertTrue(all(math.isfinite(x) for x in nodes[0]["layout"]))

    def test_numeric_validation_and_bounded_sky_projection(self):
        self.assertIsNone(imp.numeric("NaN"))
        self.assertIsNone(imp.numeric("Infinity"))
        self.assertIsNone(imp.numeric("not-number"))
        self.assertEqual(imp.sky_layout(None,None,None),[0.0,0.0,0.0])
        for ra,dec,d in ((1,91,100),(360,0,1),(2,0,"nan"),
                         (12,20,300000),("???",20,4)):
            values=imp.sky_layout(ra,dec,d)
            self.assertEqual(len(values),3)
            self.assertTrue(all(math.isfinite(x) and abs(x)<=8 for x in values))

    def test_offline_cli_writes_only_selected_json(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            seed=root/"input.json";out=root/"nasa.json"
            seed.write_text(json.dumps([{"pl_name":"Offline b","hostname":"Offline",
                "ra":10,"dec":20,"sy_dist":14}]),encoding="utf-8")
            with patch.object(imp,"download_rows",side_effect=AssertionError("network forbidden")):
                self.assertEqual(imp.main(["nasa","--input",str(seed),
                                           "--output",str(out),"--limit","5"]),0)
            data=json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(len(data["nodes"]),2)
            self.assertFalse(list(root.glob(".cosmos-*")))

    def test_reject_empty_data_without_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            dest=Path(temp)/"gaia.json"
            dest.write_text("original",encoding="utf-8")
            with self.assertRaises(ValueError):
                imp.build("gaia",[{"source_id":"broken"}],100)
            self.assertEqual(dest.read_text(),"original")

    def test_public_site_integrates_bio_center_and_main_hq(self):
        html=(self.root/"index.html").read_text(encoding="utf-8")
        js=(self.root/"cosmos.js").read_text(encoding="utf-8")
        css=(self.root/"style.css").read_text(encoding="utf-8")
        for text in (html,js,css):
            self.assertNotIn("vercel",text.lower())
            self.assertNotIn("api.openai.com",text.lower())
        self.assertIn("BIOLOGICAL DATA CENTER",html)
        self.assertIn("NOT TO SCALE",html)
        self.assertIn('fetch("./catalogs/seed.json"',js)
        self.assertIn('fetch(url,',js)
        self.assertIn("pointerdown",js)
        self.assertIn("pointermove",js)
        self.assertIn("wheel",js)
        self.assertIn("Number.isFinite(px)",js)
        self.assertNotIn("innerHTML",js)

    def test_biological_data_center_links_to_cosmos_without_sharing_private_telemetry(self):
        bio=json.loads((ROOT/"docs"/"biological-data-center"/"ontology.json").read_text(encoding="utf-8"))
        ext=[x for x in bio.get("externalOntologies",[]) if x["id"]=="xunia-cosmos"]
        self.assertEqual(len(ext),1)
        self.assertEqual(ext[0]["reference"],"../cosmos/catalogs/seed.json")
        self.assertFalse(ext[0]["telemetry_shared"])
        links=self.seed["ecosystem_links"]
        self.assertEqual(links[0]["id"],"xunia-cl1-biological-data-center")
        self.assertFalse(links[0]["telemetry_shared"])

    def test_source_allowlist_no_arbitrary_navigation(self):
        script=(self.root/"cosmos.js").read_text(encoding="utf-8")
        self.assertIn("safeSource",script)
        self.assertIn("science.nasa.gov",script)
        self.assertIn("exoplanetarchive.ipac.caltech.edu",script)
        self.assertIn("gea.esac.esa.int",script)

if __name__=="__main__":
    unittest.main()
