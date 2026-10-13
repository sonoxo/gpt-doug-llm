"""Test pilot evidence gates and reject fabricated field or Nobel authorizations."""
from __future__ import annotations

import copy
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from peace_impact.pilot import (GATES, MIN_AGGREGATE, pilot_assess, pilot_dashboard_html,
                                pilot_demo, pilot_review_markdown, pilot_verify)

ROOT = Path(__file__).resolve().parents[1]


def documented():
    p = copy.deepcopy(pilot_demo())
    p["synthetic"] = False
    for row in p["gates"]:
        row.update(state="DOCUMENTED_UNVERIFIED", reviewed_on="2026-10-13",
                   evidence_urls=["https://example.org/public-document"])
    return p


class PilotEvidenceTests(unittest.TestCase):
    def test_all_initial_approvals_missing(self):
        x = pilot_assess(pilot_demo())
        self.assertEqual(x["gate_states"]["PENDING"], len(GATES))
        self.assertEqual(x["verified_real_world_outcomes"], 0)
        self.assertEqual(x["human_field_authorization"], "NEVER_GRANTED_BY_SOFTWARE")
        self.assertFalse(x["nobel"]["nomination_submitted"])
        self.assertTrue(pilot_verify(x))

    def test_proof_replay_and_digest(self):
        r = pilot_assess(pilot_demo())
        self.assertEqual(r, pilot_assess(pilot_demo()))
        self.assertEqual(len(r["sha256"]), 64)

    def test_tampered_report_rejected(self):
        r = pilot_assess(pilot_demo())
        r["verified_real_world_outcomes"] = 2000
        self.assertFalse(pilot_verify(r))

    def test_tampered_input_rejected(self):
        r = pilot_assess(pilot_demo())
        r["input"]["synthetic"] = False
        self.assertFalse(pilot_verify(r))

    def test_foreign_schema_fields_rejected(self):
        x = pilot_demo()
        x["award_claim"] = "winner"
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_duplicate_gate_rejected(self):
        x = pilot_demo()
        x["gates"][1]["id"] = x["gates"][0]["id"]
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_not_documented_without_link(self):
        x = pilot_demo()
        x["gates"][0].update(state="DOCUMENTED_UNVERIFIED", reviewed_on="2026-10-13")
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_not_documented_without_date(self):
        x = pilot_demo()
        x["gates"][0].update(state="DOCUMENTED_UNVERIFIED",
                             evidence_urls=["https://example.org/report"])
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_future_review_date_rejected(self):
        x = pilot_demo()
        x["gates"][0].update(state="DOCUMENTED_UNVERIFIED", reviewed_on="2026-11-01",
                             evidence_urls=["https://example.org/report"])
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_not_public_evidence_rejected(self):
        x = pilot_demo()
        x["gates"][0].update(state="DOCUMENTED_UNVERIFIED", reviewed_on="2026-10-13",
                             evidence_urls=["https://127.0.0.1/report"])
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_personal_contact_in_title_rejected(self):
        x = pilot_demo()
        x["program"] = "Contact alice@example.com about participation"
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_all_documents_do_not_grant_field_access(self):
        r = pilot_assess(documented())
        self.assertEqual(r["documentation_status"], "SELF_REPORTED_COMPLETE_REQUIRES_INDEPENDENT_REVIEW")
        self.assertEqual(r["human_field_authorization"], "NEVER_GRANTED_BY_SOFTWARE")
        self.assertEqual(r["external_truth_validation"], "NOT_PERFORMED")
        self.assertEqual(r["verified_real_world_outcomes"], 0)

    def test_blocked_gate_stops(self):
        x = documented()
        x["gates"][3].update(state="BLOCKED", reviewed_on=None, evidence_urls=[])
        self.assertEqual(pilot_assess(x)["documentation_status"], "STOP_AND_HUMAN_REVIEW")

    def test_adverse_incident_stops(self):
        x = documented()
        x["measurements"]["adverse_event_observed"] = True
        self.assertEqual(pilot_assess(x)["documentation_status"], "STOP_AND_HUMAN_REVIEW")

    def test_small_cohort_refused(self):
        x = documented()
        x["measurements"]["participants_aggregate"] = MIN_AGGREGATE - 1
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_boolean_cohort_refused(self):
        x = documented()
        x["measurements"]["participants_aggregate"] = True
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_non_finite_score_refused(self):
        x = documented()
        x["measurements"]["participants_aggregate"] = 11
        x["measurements"]["baseline_aggregate"] = float("nan")
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_score_without_cohort_refused(self):
        x = documented()
        x["measurements"]["baseline_aggregate"] = 2
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_synthetic_impact_fabrication_refused(self):
        x = pilot_demo()
        x["measurements"]["participants_aggregate"] = 15
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_reporting_complete_requires_sufficient_measurement(self):
        x = documented()
        x["measurements"]["reporting_complete"] = True
        with self.assertRaises(ValueError):
            pilot_assess(x)

    def test_descriptive_change_not_causal_claim(self):
        x = documented()
        x["measurements"].update(participants_aggregate=26, baseline_aggregate=2.1,
                                  post_aggregate=2.9, followup_aggregate=2.7,
                                  adverse_event_observed=False, reporting_complete=True)
        r = pilot_assess(x)
        self.assertAlmostEqual(r["descriptive_aggregate_change_self_reported"], 0.8)
        self.assertEqual(r["measurement_causality"], "NO_CAUSAL_PEACE_EFFECT_ESTABLISHED")
        self.assertEqual(r["verified_real_world_outcomes"], 0)

    def test_phases_risks_and_human_permission(self):
        r = pilot_assess(pilot_demo())
        self.assertEqual(len(r["phases"]), 4)
        self.assertGreaterEqual(len(r["risk_register"]), 5)
        self.assertEqual(r["phases"][2]["permission"], "EXTERNAL APPROVAL REQUIRED")

    def test_review_brief_disclaims_external_clearance(self):
        brief = pilot_review_markdown(pilot_assess(pilot_demo()))
        self.assertIn("NOT A FIELD PILOT APPROVAL", brief)
        self.assertIn("No actual pilot", brief)
        self.assertIn("Verified real-world peace outcomes: 0", brief)

    def test_html_sandboxed_and_escapes_title(self):
        x = pilot_demo()
        x["program"] = "Human dialogue <script>alert(1)</script>"
        dashboard = pilot_dashboard_html(pilot_assess(x))
        self.assertIn("default-src 'none'", dashboard)
        self.assertNotIn("<script>", dashboard)
        self.assertIn("&lt;script&gt;", dashboard)
        self.assertIn("REAL-WORLD PEACE OUTCOMES VERIFIED BY THIS TOOL", dashboard)

    def test_tampered_review_refused(self):
        r = pilot_assess(pilot_demo())
        r["sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            pilot_review_markdown(r)


class PilotCLITests(unittest.TestCase):
    def test_cli_demo_report_roundtrip(self):
        cmd = subprocess.run([sys.executable, "-m", "peace_impact.cli", "pilot-demo"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(cmd.returncode, 0, cmd.stderr)
        report = json.loads(cmd.stdout)
        self.assertTrue(pilot_verify(report))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "pilot.json"
            path.write_text(cmd.stdout)
            replay = subprocess.run([sys.executable, "-m", "peace_impact.cli", "pilot-verify", str(path)],
                                    cwd=ROOT, text=True, capture_output=True, timeout=30)
            self.assertEqual(replay.returncode, 0, replay.stderr)
            self.assertTrue(json.loads(replay.stdout)["local_pilot_replay_valid"])

    def test_pilot_init_does_not_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "private.json"
            command = [sys.executable, "-m", "peace_impact.cli", "pilot-init", str(path)]
            first = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
            second = subprocess.run(command, cwd=ROOT, capture_output=True, text=True, timeout=30)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 2)
            self.assertTrue(json.loads(path.read_text())["synthetic"])

    def test_legacy_demo_is_unchanged(self):
        cmd = subprocess.run([sys.executable, "-m", "peace_impact.cli", "demo"],
                             cwd=ROOT, capture_output=True, text=True, timeout=30)
        self.assertEqual(cmd.returncode, 0, cmd.stderr)
        self.assertEqual(json.loads(cmd.stdout)["counts"]["independently_verified_impact_by_software"], 0)


if __name__ == "__main__":
    unittest.main()
