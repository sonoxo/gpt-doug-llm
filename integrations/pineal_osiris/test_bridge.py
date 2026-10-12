"""Offline regression tests for the OSIRIS -> PINEAL metadata boundary."""
from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from bridge import NAMESPACE, SAFE_ROUTES, records_from_snapshot, sync_records


class FakeStore:
    def __init__(self):
        self.items = {}
        self.calls = 0

    def search(self, *, namespace, subject, limit):
        assert namespace == NAMESPACE and limit <= 100
        return [self.items[subject]] if subject in self.items else []

    def put(self, **kwargs):
        self.calls += 1
        assert kwargs["namespace"] == NAMESPACE
        subject = kwargs["subject"]
        old = self.items.get(subject)
        if old:
            assert kwargs["expected_version"] == old["version"]
        self.items[subject] = {"id": subject, "subject": subject, "predicate": kwargs["predicate"],
                               "value": kwargs["value"], "version": (old["version"] + 1) if old else 1}
        return self.items[subject]


def sample():
    return {"schema": "gpt-doug.osiris-safe-mirror.v1",
            "source": {"mode": "authorized-public-safe-mirror"},
            "layers": {"earthquakes": {"events": [{"lat": 34.0, "lon": -118.0}]},
                       "flights": {"planes": [{"position": [3, 4]}]}},
            "layer_state": {
                "earthquakes": {"ok": True, "fetched_at": 1_000.0,
                                "sha256": "a" * 64, "latency_ms": 120},
                "live-news": {"ok": False, "fetched_at": 1_000.0,
                              "sha256": None, "latency_ms": 450},
                "flights": {"ok": True, "fetched_at": 1_000.0,
                            "sha256": "c" * 64, "latency_ms": 4},
                "cctv": {"ok": True, "fetched_at": 1_000.0,
                         "sha256": "b" * 64, "latency_ms": 10},
            }}


class BridgeTests(unittest.TestCase):
    def test_exact_allowlist(self):
        self.assertNotIn("cctv", SAFE_ROUTES)
        self.assertNotIn("flights", SAFE_ROUTES)
        self.assertNotIn("maritime", SAFE_ROUTES)
        self.assertIn("earthquakes", SAFE_ROUTES)

    def test_blocks_raw_locations_and_recon(self):
        records = records_from_snapshot(sample(), 1_010, 600)
        self.assertEqual([x["subject"] for x in records], ["osiris:earthquakes", "osiris:live-news"])
        all_values = " ".join(r["value"] for r in records)
        self.assertNotIn('"lat":', all_values)
        self.assertNotIn('"position":', all_values)
        self.assertNotIn("flights", all_values)
        self.assertEqual(json.loads(records[0]["value"])["status"], "ONLINE")
        self.assertEqual(json.loads(records[1]["value"])["status"], "DEGRADED")

    def test_staleness_and_clock_skew(self):
        snap = sample()
        snap["layer_state"].pop("live-news")
        out = records_from_snapshot(snap, 2_000, 600)
        self.assertEqual(json.loads(out[0]["value"])["status"], "STALE")
        out = records_from_snapshot(snap, 100, 600)
        self.assertEqual(json.loads(out[0]["value"])["status"], "CLOCK_SKEW")

    def test_rejects_untrusted_schema(self):
        snap = sample()
        snap["source"]["mode"] = "unverified-scraper"
        with self.assertRaises(ValueError):
            records_from_snapshot(snap, 1_000, 600)

    def test_upsert_and_idempotence(self):
        store = FakeStore()
        records = records_from_snapshot(sample(), 1_010, 600)
        self.assertEqual(sync_records(store, records), {"created": 2, "updated": 0, "unchanged": 0})
        self.assertEqual(sync_records(store, records), {"created": 0, "updated": 0, "unchanged": 2})
        new_records = records_from_snapshot(sample(), 2_000, 600)
        self.assertEqual(sync_records(store, new_records), {"created": 0, "updated": 2, "unchanged": 0})
        self.assertEqual(store.items["osiris:earthquakes"]["version"], 2)


if __name__ == "__main__":
    unittest.main()
