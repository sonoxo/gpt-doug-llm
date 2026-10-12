"""Offline checks for the PINEAL x OSIRIS launcher and status supervision."""
from __future__ import annotations

import io
import json
import os
import sqlite3
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import URLError

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import stack


class FakeHTTP:
    def __init__(self, payload: dict, mime: str = "application/json"):
        self.stream = io.BytesIO(json.dumps(payload).encode())
        self.status = 200
        self.headers = {"Content-Type": mime}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.stream.close()

    def __iter__(self):
        return iter(self.stream)

    def read(self, *args):
        return self.stream.read(*args)


class StackTests(unittest.TestCase):
    def test_process_health_not_feed_health(self):
        payload = {"platform": "OSIRIS", "status": "serving", "scope": "process"}
        with patch.object(stack, "urlopen", return_value=FakeHTTP(payload)):
            value = stack.check_process(3000)
        self.assertTrue(value["serving"])
        self.assertIn("not checked", value["scope"])

    def test_fails_closed_on_unavailable_process(self):
        with patch.object(stack, "urlopen", side_effect=URLError("offline")):
            self.assertFalse(stack.check_process(3000)["serving"])

    def test_safe_status_no_raw_tracking_data(self):
        with tempfile.TemporaryDirectory() as folder:
            snap = {"schema": "gpt-doug.osiris-safe-mirror.v1",
                    "source": {"mode": "authorized-public-safe-mirror"},
                    "generated_at": 123, "health": {"status": "DEGRADED"},
                    "layer_state": {"earthquakes": {"ok": True, "fetched_at": 123.0,
                                                    "payload": {"lat": 2}},
                                    "flights": {"ok": True, "fetched_at": 123.0}}}
            (Path(folder) / "snapshot.json").write_text(json.dumps(snap))
            with patch.dict(os.environ, {"OSIRIS_MIRROR_OUT": folder}):
                with patch.object(stack, "check_process", return_value={"serving": False}):
                    result = stack.status(3000)
            self.assertEqual(list(result["safe_routes"]), ["earthquakes"])
            self.assertEqual(result["safe_routes"]["earthquakes"]["status"], "STALE")
            self.assertNotIn('"lat": 2', json.dumps(result))
            self.assertNotIn('"payload":', json.dumps(result))
            self.assertNotIn("flights", json.dumps(result))

    def test_freshness_is_recomputed_not_copied_from_cached_health(self):
        with tempfile.TemporaryDirectory() as folder:
            snap = {"schema": "gpt-doug.osiris-safe-mirror.v1",
                    "source": {"mode": "authorized-public-safe-mirror"},
                    "generated_at": 2000.0,
                    "layer_state": {"earthquakes": {
                        "ok": True, "fetched_at": 2000.0,
                        "sha256": "a" * 64, "latency_ms": 33}}}
            (Path(folder) / "snapshot.json").write_text(json.dumps(snap))
            with patch.dict(os.environ, {"OSIRIS_MIRROR_OUT": folder}):
                with patch.object(stack, "check_process", return_value={"serving": True}):
                    with patch.object(stack.time, "time", return_value=2050):
                        fresh = stack.status(3000)
                    with patch.object(stack.time, "time", return_value=4000):
                        stale = stack.status(3000)
        self.assertEqual(fresh["safe_routes"]["earthquakes"]["status"], "ONLINE")
        self.assertEqual(stale["safe_routes"]["earthquakes"]["status"], "STALE")
        self.assertEqual(stale["snapshot"]["health"]["fresh_successful_routes"], 0)

    def test_pineal_counts_query_is_read_only(self):
        with tempfile.TemporaryDirectory() as folder:
            dbfile = Path(folder) / "pineal.sqlite3"
            with sqlite3.connect(dbfile) as db:
                db.execute("CREATE TABLE memories (namespace TEXT NOT NULL)")
                db.execute("CREATE TABLE audit (id INTEGER PRIMARY KEY)")
                db.execute("INSERT INTO memories(namespace) VALUES ('osiris_feed')")
                db.execute("INSERT INTO memories(namespace) VALUES ('unrelated')")
                db.execute("INSERT INTO audit(id) VALUES (1)")
            with patch.dict(os.environ, {"PINEAL_HOME": folder}):
                counts = stack.pineal_counts()
        self.assertEqual(counts["state"], "LOCAL")
        self.assertEqual(counts["feed_health_records"], 1)
        self.assertEqual(counts["audit_entries"], 1)
        self.assertFalse(counts["audit_integrity_verified"])

    def test_launcher_url_from_foreign_working_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            p = subprocess.run(["sh", str(HERE / "run.sh"), "url"], cwd=folder,
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("sdk_naval", p.stdout)
        self.assertIn("http://127.0.0.1:3000/", p.stdout)

    def test_bootstrap_dry_check_from_foreign_cwd(self):
        with tempfile.TemporaryDirectory() as folder:
            p = subprocess.run(["sh", str(HERE / "bootstrap.sh"), "--check"], cwd=folder,
                               capture_output=True, text=True, timeout=10)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("gpt-doug-llm-osiris", p.stdout)


if __name__ == "__main__":
    unittest.main()
