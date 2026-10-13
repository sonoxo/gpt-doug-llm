"""No-token, no-network regression suite for governed sensor swarm."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sensor_swarm.core import (
    SCHEMA, POLICY_PATH, Store, collect_one, demo_specs, digest, load_manifest,
    load_policy, observation, safe_path, snapshot, timestamp, validate_specs,
)
from sensor_swarm.dashboard import HTML
from sensor_swarm.ontology import export_graph, verify_export

ROOT = Path(__file__).resolve().parents[1]

def example(kind="json", path="events.json"):
    return {"id": "approved-observer", "kind": kind,
            "source_id": "approved-lab", "object_type": "environmental_sensor",
            "authorization_scope": "operator-approved", "purpose": "bounded-observability",
            "classification": "authorized_local", "path": path}

def row(value=24):
    return {"metric": "ambient_reading", "value": value, "unit": "units",
            "observed_at": "2026-10-13T00:00:00Z"}

class SensorSwarmTests(unittest.TestCase):
    def test_policy_fail_closed(self):
        p = load_policy()
        self.assertEqual(p["mode"], "AUTHORIZED_SENSORS_ONLY")
        self.assertIn("research_evidence", p["allowed_object_types"])
        self.assertIn("person", p["prohibited_object_types"])
    def test_reject_relaxed_policy(self):
        p = load_policy()
        p["controls"]["covert_person_tracking"] = True
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "policy.json"
            f.write_text(json.dumps(p))
            with self.assertRaises(ValueError):
                load_policy(f)
    def test_biopineal_fixture_is_unverified(self):
        s = snapshot(demo_specs())
        self.assertEqual(s["rejected_sensors"], 0)
        metrics = {e["metric"]: e["value"] for e in s["events"]}
        self.assertTrue(metrics["atom_balance_confirmed"])
        self.assertFalse(metrics["official_patent_record_verified"])
        self.assertFalse(metrics["patent_rights_verified"])
        self.assertGreater(metrics["evidence_graph_node_count"], 0)
    def test_nonphysical_scoping(self):
        s = snapshot(demo_specs())
        self.assertFalse(s["network_scanning"])
        self.assertFalse(s["autonomous_external_action"])
        self.assertTrue(s["read_only"])
    def test_reject_person(self):
        s = example(); s["object_type"] = "person"
        with self.assertRaises(ValueError): snapshot([s], root=".", authorized_local=True)
    def test_reject_live_military_unit(self):
        s = example(); s["object_type"] = "live_military_unit"
        with self.assertRaises(ValueError): snapshot([s], root=".", authorized_local=True)
    def test_reject_unknown_kind(self):
        s = example(); s["kind"] = "network-discovery"
        with self.assertRaises(ValueError): validate_specs([s], load_policy())
    def test_reject_duplicate_ids(self):
        with self.assertRaises(ValueError): validate_specs([example(), example()], load_policy())
    def test_reject_undeclared_fields(self):
        s = example(); s["command"] = "execute"
        with self.assertRaises(ValueError): validate_specs([s], load_policy())
    def test_local_approval_required(self):
        with self.assertRaises(PermissionError): snapshot([example()])
    def test_file_root_required(self):
        with self.assertRaises(PermissionError): snapshot([example()], authorized_local=True)
    def test_json_sensor(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.json").write_text(json.dumps({"observations": [row()]}))
            s = snapshot([example()], root=d, authorized_local=True)
            self.assertEqual(s["accepted"], 1)
            self.assertEqual(s["events"][0]["value"], 24)
            self.assertEqual(s["events"][0]["classification"], "authorized_local")
    def test_jsonl_sensor(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.jsonl").write_text(json.dumps(row(7)) + "\n" + json.dumps(row(8)) + "\n")
            s = snapshot([example("jsonl", "events.jsonl")], root=d, authorized_local=True)
            self.assertEqual(s["accepted"], 2)
    def test_csv_sensor(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.csv").write_text(
                "metric,value,unit,observed_at\nambient_reading,19,units,2026-10-13T00:00:00Z\n")
            s = snapshot([example("csv", "events.csv")], root=d, authorized_local=True)
            self.assertEqual(s["accepted"], 1)
            self.assertEqual(s["events"][0]["value"], 19)
    def test_bad_row_rejects_all_source_data(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.json").write_text(json.dumps([row(), {"metric": "secret", "value": "foo"}]))
            s = snapshot([example()], root=d, authorized_local=True)
            self.assertEqual(s["accepted"], 0)
            self.assertEqual(s["rejected_sensors"], 1)
    def test_reject_external_path(self):
        with tempfile.TemporaryDirectory() as d:
            s = snapshot([example("json", "../outside.json")], root=d, authorized_local=True)
            self.assertEqual(s["rejected_sensors"], 1)
    def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            other = Path(d).parent / (Path(d).name + "_external.json")
            try:
                other.write_text(json.dumps([row()]))
                Path(d, "events.json").symlink_to(other)
                s = snapshot([example()], root=d, authorized_local=True)
                self.assertEqual(s["accepted"], 0)
                self.assertEqual(s["rejected_sensors"], 1)
            finally:
                other.unlink(missing_ok=True)
    def test_reject_oversize(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.json").write_bytes(b" " * 262145)
            s = snapshot([example()], root=d, authorized_local=True)
            self.assertEqual(s["rejected_sensors"], 1)
    def test_reject_secret_text(self):
        s = demo_specs()[1]
        with self.assertRaises(ValueError):
            observation(s, {"metric": "thing", "value": "sk-abcdefghijklmnopqrst"},
                        locator="test", sha=digest("example"))
    def test_reject_email_text(self):
        s = demo_specs()[1]
        with self.assertRaises(ValueError):
            observation(s, {"metric": "thing", "value": "someone@example.com"},
                        locator="test", sha=digest("example"))
    def test_reject_nested_values(self):
        s = demo_specs()[1]
        with self.assertRaises(ValueError):
            observation(s, {"metric": "thing", "value": {"nested": "data"}},
                        locator="test", sha=digest("example"))
    def test_reject_nan_and_inf(self):
        s = demo_specs()[1]
        for v in (float("nan"), float("inf")):
            with self.subTest(v=v), self.assertRaises(ValueError):
                observation(s, {"metric": "thing", "value": v},
                            locator="test", sha=digest("example"))
    def test_reject_unbounded_rows(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.json").write_text(json.dumps([row(i) for i in range(129)]))
            s = snapshot([example()], root=d, authorized_local=True)
            self.assertEqual(s["accepted"], 0)
    def test_iso_dates_require_timezone(self):
        with self.assertRaises(ValueError): timestamp("2026-10-13T00:00:00")
    def test_future_date_rejected(self):
        future = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        with self.assertRaises(ValueError): timestamp(future)
    def test_store_deduplicates(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "events.db"
            s = snapshot(demo_specs())
            db = Store(path)
            try:
                db.write(s)
                db.write(s)
                result = db.status()
                self.assertEqual(result["stored_count"], s["accepted"])
                self.assertEqual(len(result["sensors"]), len(demo_specs()))
            finally:
                db.close()
    def test_event_reproducible(self):
        s = demo_specs()[1]
        r = {"metric": "fixture_heartbeat", "value": True, "observed_at": "2026-10-13T00:00:00Z"}
        a = observation(s, r, locator="fixture", sha=digest("fixture"))
        b = observation(s, r, locator="fixture", sha=digest("fixture"))
        self.assertEqual(a["id"], b["id"])
    def test_malformed_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "manifest.json"
            f.write_text('{"schema":"wrong","sensors":[]}')
            with self.assertRaises(ValueError): load_manifest(f)
    def test_cli_demo(self):
        p = subprocess.run([sys.executable, "-m", "sensor_swarm", "demo"], cwd=ROOT,
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["rejected_sensors"], 0)
    def test_local_dashboard_no_external_assets(self):
        self.assertIn("/api/status", HTML)
        self.assertIn("textContent", HTML)
        self.assertNotIn("http://", HTML)
        self.assertNotIn("https://", HTML)
    def test_host_health_requires_approval(self):
        s = {"id": "host-health", "kind": "host-health", "source_id": "local-host",
             "object_type": "infrastructure_asset", "authorization_scope": "operator-approved",
             "purpose": "health-observability", "classification": "authorized_local"}
        with self.assertRaises(PermissionError): snapshot([s])
        r = snapshot([s], authorized_local=True)
        self.assertEqual(r["accepted"], 2)

    def test_enum_allowlist_prevents_free_text(self):
        s = demo_specs()[1]
        for value in ("John Smith", "192.168.0.1", "password123"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                observation(s, {"metric": "status", "value": value}, locator="fixture", sha=digest("fixture"))
        self.assertEqual(observation(s, {"metric": "status", "value": "HEALTHY"},
                                     locator="fixture", sha=digest("fixture"))["value"], "HEALTHY")
    def test_huge_integer_does_not_crash_swarm(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.json").write_text(json.dumps([row(10**2000)]))
            result = snapshot([example()], root=d, authorized_local=True)
            self.assertEqual(result["rejected_sensors"], 1)
    def test_missing_file_timestamp_replay_stable(self):
        with tempfile.TemporaryDirectory() as d:
            Path(d, "events.json").write_text(json.dumps([{"metric": "count", "value": 1}]))
            a = snapshot([example()], root=d, authorized_local=True)
            b = snapshot([example()], root=d, authorized_local=True)
            self.assertEqual(a["events"][0]["id"], b["events"][0]["id"])
    def test_ontology_export_linkage(self):
        with tempfile.TemporaryDirectory() as d:
            db = Store(Path(d) / "events.db")
            try:
                db.write(snapshot(demo_specs()))
                graph = export_graph(db)
                self.assertTrue(verify_export(graph))
                nodes = {x["id"] for x in graph["nodes"]}
                self.assertTrue(all(edge["from"] in nodes and edge["to"] in nodes for edge in graph["edges"]))
                self.assertFalse(graph["automatically_promoted"])
                self.assertFalse(graph["official_patent_verified"])
                self.assertIn("DERIVED_FROM", {edge["type"] for edge in graph["edges"]})
            finally:
                db.close()
    def test_ontology_digest_tampering(self):
        with tempfile.TemporaryDirectory() as d:
            db = Store(Path(d) / "events.db")
            try:
                db.write(snapshot(demo_specs()))
                graph = export_graph(db)
                graph["sha256"] = "0" * 64
                self.assertFalse(verify_export(graph))
            finally:
                db.close()
    def test_ontology_rejects_bad_limit(self):
        with tempfile.TemporaryDirectory() as d:
            db = Store(Path(d) / "events.db")
            try:
                with self.assertRaises(ValueError):
                    export_graph(db, 0)
            finally:
                db.close()

    def test_classification_scope_participates_in_event_id(self):
        first = demo_specs()[1]
        altered = copy.deepcopy(first)
        altered["authorization_scope"] = "separately-approved"
        event = {"metric": "test_heartbeat", "value": True,
                 "observed_at": "2026-10-13T00:00:00Z"}
        a = observation(first, event, locator="fixture", sha=digest("fixture"))
        b = observation(altered, event, locator="fixture", sha=digest("fixture"))
        self.assertNotEqual(a["id"], b["id"])
    def test_required_denials_cannot_be_removed_from_policy(self):
        policy = load_policy()
        policy["prohibited_object_types"].remove("person")
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "relaxed.json"
            path.write_text(json.dumps(policy))
            with self.assertRaises(ValueError): load_policy(path)
    def test_journal_rejects_unbounded_retention(self):
        with tempfile.TemporaryDirectory() as d:
            db = Store(Path(d) / "events.db")
            try:
                with self.assertRaises(ValueError):
                    db.write(snapshot(demo_specs()), retention_days=3650)
            finally:
                db.close()

if __name__ == "__main__":
    unittest.main()
