"""Offline tests for the GPT-DOUG Dataset Civilization fleet."""
from __future__ import annotations
import copy
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from data_fleet import engine as fleet


class DatasetFleetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/"public").mkdir()
        (self.root/"public"/"items.json").write_text(json.dumps({"items":[{"id":"one","name":"alpha"},{"id":"two","name":"beta"}]}))
        self.source = {"id":"demo-data","name":"Demo Public Dataset","path":"public/items.json",
                       "format":"json","rows_key":"items","sensitivity":"public","approved":True,
                       "provenance":"https://github.com/sonoxo/gpt-doug-llm/blob/main/README.md",
                       "related_to":[]}
        self.manifest = self.root/"manifest.json"
        self.db = self.root/"index.sqlite"
        self.write_manifest()

    def write_manifest(self, sources=None):
        self.manifest.write_text(json.dumps({"schema":fleet.SCHEMA,"datasets":sources or [self.source]}))

    def test_governed_parse_and_row_count(self):
        result=fleet.run(self.root,self.manifest,self.db,workers=2)
        self.assertEqual(result["summary"]["datasets"],1)
        self.assertEqual(result["summary"]["rows"],2)
        self.assertEqual(result["statuses"],{"completed":1})
        self.assertEqual(len(result["agents"]),5)
        self.assertFalse(result["networkAccess"])

    def test_rerun_is_idempotent(self):
        fleet.run(self.root,self.manifest,self.db)
        result=fleet.run(self.root,self.manifest,self.db)
        self.assertEqual(result["statuses"],{"unchanged":1})
        with fleet.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT count(*) FROM records").fetchone()[0],2)
            self.assertEqual(con.execute("SELECT count(*) FROM audits WHERE event='idempotent_skip'").fetchone()[0],1)

    def test_mutation_refreshes_checksum_and_records(self):
        before=fleet.run(self.root,self.manifest,self.db)["datasets"][0]
        (self.root/"public"/"items.json").write_text(json.dumps({"items":[{"id":"changed"}]}))
        after=fleet.run(self.root,self.manifest,self.db)["datasets"][0]
        self.assertEqual(after["rows"],1)
        self.assertNotEqual(before["sha256"],after["sha256"])

    def test_local_search_and_literal_wildcards(self):
        fleet.run(self.root,self.manifest,self.db)
        with fleet.connect(self.db) as con:
            result=fleet.search(con,"alpha")
            self.assertEqual(len(result),1)
            self.assertEqual(result[0]["dataset"],"demo-data")
            self.assertFalse(fleet.search(con,"%_"))

    def test_reject_private_or_unapproved_dataset(self):
        for vals in ({"sensitivity":"private"},{"approved":False}):
            source={**self.source,**vals}
            self.write_manifest([source])
            with self.assertRaises(fleet.FleetError):
                fleet.run(self.root,self.manifest,self.db)

    def test_reject_directory_escape_and_local_secrets(self):
        for path in ("../outside.json","/tmp/file.json","public/../../private.json","private/foo.json",".env.json"):
            source={**self.source,"path":path}
            self.write_manifest([source])
            with self.assertRaises((fleet.FleetError,FileNotFoundError)):
                fleet.run(self.root,self.manifest,self.db)

    def test_symlink_escape_fails_closed(self):
        private=self.root/"external.json"
        private.write_text('{"items":[{"a":1}]}')
        (self.root/"public"/"link.json").symlink_to(private)
        self.write_manifest([{**self.source,"path":"public/link.json"}])
        with self.assertRaises(fleet.FleetError):
            fleet.run(self.root,self.manifest,self.db)

    def test_bad_json_quarantines_job_without_executing(self):
        (self.root/"public"/"items.json").write_text('{"items": [')
        result=fleet.run(self.root,self.manifest,self.db,max_attempts=2)
        self.assertEqual(result["statuses"],{"quarantined":1})
        self.assertEqual(result["summary"]["datasets"],0)
        with fleet.connect(self.db) as con:
            self.assertEqual(con.execute("SELECT last_error FROM jobs").fetchone()[0],"JSONDecodeError")

    def test_invalid_manifest_references_fail(self):
        src={**self.source,"related_to":["unknown"]}
        self.write_manifest([src])
        with self.assertRaises(fleet.FleetError):
            fleet.run(self.root,self.manifest,self.db)

    def test_record_size_limits(self):
        (self.root/"public"/"items.json").write_text(json.dumps({"items":[{"content":"x"*fleet.MAX_RECORD_BYTES}]}))
        result=fleet.run(self.root,self.manifest,self.db)
        self.assertEqual(result["statuses"],{"quarantined":1})

    def test_worker_and_retry_caps(self):
        for workers,retries in ((0,2),(9,2),(2,0),(2,6)):
            with self.assertRaises(fleet.FleetError):
                fleet.run(self.root,self.manifest,self.db,workers=workers,max_attempts=retries)

    def test_curated_relationship_graph(self):
        other_path=self.root/"public"/"extra.json"
        other_path.write_text(json.dumps({"items":[{"id":"x"}]}))
        extra={**self.source,"id":"extra-data","path":"public/extra.json","related_to":[]}
        parent={**self.source,"related_to":["extra-data"]}
        self.write_manifest([parent,extra])
        result=fleet.run(self.root,self.manifest,self.db)
        self.assertEqual(result["summary"]["related"],1)
        self.assertEqual(result["lineage"][0]["kind"],"curated-reference")

    def test_transient_read_failure_retries_with_budget(self):
        original=fleet._process
        calls={"n":0}
        def flaky(root,source):
            calls["n"]+=1
            if calls["n"]==1:
                raise OSError("transient error")
            return original(root,source)
        with patch.object(fleet,"_process",side_effect=flaky):
            result=fleet.run(self.root,self.manifest,self.db,max_attempts=2)
        self.assertEqual(result["statuses"],{"completed":1})
        self.assertEqual(calls["n"],2)

    def test_public_dashboard_assets_and_source_parity(self):
        repo=Path(__file__).resolve().parents[1]
        site=repo/"docs/dataset-fleet"
        for name in ("index.html","app.js","style.css","preview.json","glass-onion-15-public.json"):
            self.assertTrue((site/name).is_file(),name)
        preview=json.loads((site/"preview.json").read_text(encoding="utf-8"))
        manifest=fleet.manifest_from_file(repo/"data_fleet/manifest.json")
        self.assertEqual({x["id"] for x in preview["datasets"]},{x["id"] for x in manifest["datasets"]})
        self.assertEqual(preview["status"],"reference_only_not_executed")
        self.assertEqual(json.loads((site/"glass-onion-15-public.json").read_text(encoding="utf-8")),
                         json.loads((repo/"catalog/glass-onion-15.json").read_text(encoding="utf-8")))
        html=(site/"index.html").read_text(encoding="utf-8")
        script=(site/"app.js").read_text(encoding="utf-8")
        self.assertIn("id=\"webScan\"",html)
        self.assertIn("crypto.subtle.digest",script)
        self.assertIn("Scan public datasets",html)
        self.assertIn("connect-src 'self'",html)
        self.assertIn('href="./dataset-fleet/"',(repo/"docs/index.html").read_text(encoding="utf-8"))
        resources=json.loads((repo/"docs/resources.json").read_text(encoding="utf-8"))["items"]
        entries=[x for x in resources if x["id"]=="gpt-doug-dataset-civilization"]
        self.assertEqual(len(entries),1)
        self.assertTrue(entries[0]["free"])

    def test_actual_repository_public_sources(self):
        repo=Path(__file__).resolve().parents[1]
        mf=repo/"data_fleet/manifest.json"
        data=fleet.manifest_from_file(mf)
        self.assertEqual(len(data["datasets"]),4)
        result=fleet.run(repo,mf,self.root/"live-repo.sqlite",workers=4)
        self.assertEqual(result["statuses"],{"completed":4})
        self.assertGreaterEqual(result["summary"]["rows"],280)
        self.assertEqual(result["summary"]["related"],3)
        self.assertTrue(all(x["sha256"] and x["rows"] for x in result["datasets"]))


if __name__=="__main__":
    unittest.main()
