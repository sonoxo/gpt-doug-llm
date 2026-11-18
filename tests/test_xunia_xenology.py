"""Offline tests for the CL1 xenology/UAP/Shaggoth evidence-separated atlas."""
from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/"docs"/"cosmos"/"xenology"
GROUPS={"aliens":16,"uap":10,"shaggoth":7,"records":3}
CLASS={"fictional","speculative","illustrative","documented","resolved"}

class XenologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((BASE/"catalog.json").read_text(encoding="utf-8"))
        cls.records=cls.catalog["records"]

    def test_catalog_scope_and_qualified_sources(self):
        d=self.catalog
        self.assertEqual(d["schema"],"xunia.cl1.xenology-archive.v1")
        self.assertEqual(len(self.records),36)
        self.assertIn("NOT all",d["coverage"])
        self.assertIn("No verified extraterrestrial",d["truth"])
        self.assertEqual(len({r["id"] for r in self.records}),36)
        for group,count in GROUPS.items():
            self.assertEqual(len([r for r in self.records if r["group"]==group]),count)
        for r in self.records:
            self.assertIn(r["group"],GROUPS)
            self.assertIn(r["evidence"],CLASS)
            self.assertTrue(r["name"] and r["description"])
            self.assertIn(r["group"],d["classifications"])
            self.assertTrue(r["source_url"] is None or
                            r["source_url"].startswith(("https://science.nasa.gov/",
                                                         "https://www.aaro.mil/")))
            if r["group"] in ("aliens","shaggoth"):
                self.assertIn(r["evidence"],("fictional","speculative"))
            if r["group"]=="records":
                self.assertIn(r["evidence"],("documented","resolved"))
                self.assertIn("www.aaro.mil",r["source_url"])

    def test_app_provides_working_local_commands_and_graph(self):
        html=(BASE/"index.html").read_text(encoding="utf-8")
        js=(BASE/"app.js").read_text(encoding="utf-8")
        css=(BASE/"style.css").read_text(encoding="utf-8")
        for x in ["query","groupFilters","evidenceFilters","alienGrid","uapGrid",
                  "reportGrid","shoggothGrid","creatureCanvas","graphCanvas",
                  "tabs","tabBody","intensity","pauseScene","consoleForm",
                  "consoleInput","exportData","runSimulation","saveScene","shareView",
                  "viewUrl","actionStatus","runSelfTest"]:
            self.assertIn('id="'+x+'"',html)
        for x in ["function renderCards(", "function drawViewer(", "function drawGraph(",
                  "function command(raw)", "function choose(", "function exportData(",
                  "function updateMapMode(", "function togglePause(",
                  "function buildRelations(", "function safeOfficial(",
                  "function restoreSharedView(", "function shareView(",
                  "function saveScene(", "function runSelfTest(",
                  "function currentShareUrl("]:
            self.assertIn(x,js)
        self.assertIn('fetch("./catalog.json"',js)
        self.assertEqual(js.count("fetch("),1)
        self.assertIn("prefers-reduced-motion",css)
        self.assertIn("Fictional",html)
        self.assertIn("AARO",html)
        for x in ["innerHTML","eval(","new Function(","WebSocket(",
                  "navigator.bluetooth","navigator.serial","navigator.usb",
                  "localStorage","vercel"]:
            self.assertNotIn(x,js)

    def test_ecosystem_links_are_present_and_free(self):
        cosmos=(ROOT/"docs"/"cosmos"/"index.html").read_text(encoding="utf-8")
        hq=(ROOT/"docs"/"index.html").read_text(encoding="utf-8")
        bio=(ROOT/"docs"/"biological-data-center"/"index.html").read_text(encoding="utf-8")
        resources=json.loads((ROOT/"docs"/"resources.json").read_text(encoding="utf-8"))
        index=json.loads((ROOT/"docs"/"docs-index.json").read_text(encoding="utf-8"))
        self.assertIn('./xenology/',cosmos)
        self.assertIn('./cosmos/xenology/',hq)
        self.assertIn('../cosmos/xenology/',bio)
        self.assertEqual(index["publicSurfaces"]["xenologyUapShaggoth"],"https://xunia.org/cosmos/xenology/")
        records=[r for r in resources["items"] if r["id"]=="cl1-xenology-uap-shaggoth"]
        self.assertEqual(len(records),1)
        self.assertTrue(records[0]["free"])
        self.assertTrue(records[0]["interactive"])
        self.assertEqual(records[0]["url"],"./cosmos/xenology/")

if __name__=="__main__":
    unittest.main()
