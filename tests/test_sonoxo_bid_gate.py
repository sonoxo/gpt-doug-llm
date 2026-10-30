"""Regression tests for conservative, read-only procurement review."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("sonoxo_bid_gate", ROOT / "tools" / "sonoxo_bid_gate.py")
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

class TestGate(unittest.TestCase):
    def setUp(self):
        self.op = {
            "id":"trial", "deadline":"2026-11-01", "timezone":"UTC",
            "official_url":"https://example.org/official",
            "requirements":[
                {"id":"a", "label":"Confirmed rule", "source_status":"official_notice", "blocking":True,
                 "bidder_status":"missing", "evidence_ref":""},
                {"id":"b", "label":"Unknown annex", "source_status":"annex_unavailable", "blocking":True,
                 "bidder_status":"missing", "evidence_ref":""}
            ]
        }

    def test_unknown_evidence_does_not_pass(self):
        self.assertEqual(gate.assess(self.op)["decision"], "blocked_do_not_submit")

    def test_annex_without_source_still_blocked(self):
        result = gate.assess(self.op, {
            "a":{"bidder_status":"verified", "evidence_ref":"local-proof-A"},
            "b":{"bidder_status":"verified", "evidence_ref":"local-proof-B"},
        })
        self.assertEqual(result["decision"], "blocked_do_not_submit")
        self.assertTrue(any(x["reason"].startswith("Governing") for x in result["blockers"]))

    def test_ready_means_manual_review_only(self):
        result = gate.assess(self.op, {
            "a":{"bidder_status":"verified", "evidence_ref":"local-proof-A"},
            "b":{"bidder_status":"verified", "evidence_ref":"local-proof-B",
                 "official_annex_url":"https://example.org/official-annex"},
        })
        self.assertEqual(result["decision"], "ready_for_manual_bid_review")
        self.assertIn("Independent human", result["note"])

    def test_unknown_requirement_rejected(self):
        with self.assertRaises(ValueError):
            gate.assess(self.op, {"unknown":{"bidder_status":"verified"}})

    def test_marking_verified_without_evidence_is_blocked(self):
        result = gate.assess(self.op, {"a":{"bidder_status":"verified"}})
        self.assertTrue(any(x["id"]=="a" for x in result["blockers"]))

    def test_invalid_status_rejected(self):
        with self.assertRaises(ValueError):
            gate.assess(self.op, {"a":{"bidder_status":"completed"}})

if __name__=="__main__":
    unittest.main()
