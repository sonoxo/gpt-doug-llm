"""Offline verification and fail-closed regression cases for PeaceLab."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from peace_impact.core import assess, demo, facilitator_kit, review_brief, validated, verify

ROOT = Path(__file__).resolve().parents[1]


def real_impact():
    payload = demo()
    prog = payload["program"]
    prog.update(legal_name="Example Peace Charity", legal_verified=True,
                conflict_sensitivity_reviewed=True, eligible_nominator_identified=True)
    a = payload["activities"][0]
    a.update(status="completed", synthetic=False, participants_aggregate=12,
             consent=True, harm_monitoring=True, harm_incidents=0,
             evidence_urls=["https://research.example.org/evaluation"],
             external_review_urls=["https://independent.example.edu/report"],
             baseline=1, followup=2)
    return payload


class ModelTests(unittest.TestCase):
    def test_demo_zero_outcomes(self):
        r = assess(demo())
        self.assertEqual(r["nobel"]["eligibility_status"], "NOT_READY")
        self.assertEqual(r["counts"]["completed_real_activities_self_reported"], 0)
        self.assertEqual(r["counts"]["independently_verified_impact_by_software"], 0)
        self.assertFalse(r["nobel"]["self_nomination_valid"])
        self.assertTrue(verify(r))

    def test_deterministic_hash(self):
        self.assertEqual(assess(demo()), assess(demo()))
        self.assertEqual(len(assess(demo())["evidence_sha256"]), 64)

    def test_hash_tampering(self):
        r = assess(demo())
        r["counts"]["completed_real_activities_self_reported"] = 1000000
        self.assertFalse(verify(r))

    def test_modified_input_tampering(self):
        r = assess(demo())
        r["input"]["program"]["legal_verified"] = True
        self.assertFalse(verify(r))

    def test_invalid_report(self):
        self.assertFalse(verify(None))
        self.assertFalse(verify({}))

    def test_extra_top_field(self):
        p = demo(); p["unexpected"] = 1
        with self.assertRaises(ValueError): assess(p)

    def test_extra_activity_field(self):
        p = demo(); p["activities"][0]["personal_name"] = "somebody"
        with self.assertRaises(ValueError): assess(p)

    def test_duplicate_ids(self):
        p = demo(); p["activities"].append(copy.deepcopy(p["activities"][0]))
        with self.assertRaises(ValueError): assess(p)

    def test_type_restrictions(self):
        p = demo(); p["activities"][0]["kind"] = "military_targeting"
        with self.assertRaises(ValueError): assess(p)

    def test_invalid_date(self):
        p = demo(); p["activities"][0]["day"] = "2026-13-99"
        with self.assertRaises(ValueError): assess(p)

    def test_bad_consent(self):
        p = real_impact(); p["activities"][0]["consent"] = False
        with self.assertRaises(ValueError): assess(p)

    def test_no_overclaim_of_real_impact(self):
        r = assess(real_impact())
        self.assertEqual(r["counts"]["completed_real_activities_self_reported"], 1)
        self.assertEqual(r["counts"]["independently_verified_impact_by_software"], 0)
        self.assertTrue(r["records"][0]["external_review_links_provided_unchecked"])
        self.assertEqual(r["nobel"]["eligibility_status"], "DOCUMENTS_READY_FOR_HUMAN_REVIEW")
        self.assertTrue(verify(r))

    def test_incomplete_evaluation_blocked(self):
        p = real_impact(); p["activities"][0]["harm_incidents"] = None
        r = assess(p)
        self.assertEqual(r["nobel"]["eligibility_status"], "NOT_READY")
        self.assertEqual(r["counts"]["complete_evaluation_fields"], 0)

    def test_small_aggregate_rejected(self):
        p = real_impact(); p["activities"][0]["participants_aggregate"] = 3
        with self.assertRaises(ValueError): assess(p)

    def test_suppressed_aggregate_unknown(self):
        p = real_impact(); p["activities"][0]["participants_aggregate"] = None
        r = assess(p)
        self.assertIsNone(r["records"][0]["public_participant_count_self_reported"])

    def test_https_only(self):
        p = real_impact(); p["activities"][0]["evidence_urls"] = ["http://example.org/eval"]
        with self.assertRaises(ValueError): assess(p)

    def test_no_loopback(self):
        p = real_impact(); p["activities"][0]["evidence_urls"] = ["https://127.0.0.1/report"]
        with self.assertRaises(ValueError): assess(p)

    def test_no_local_hostname(self):
        p = real_impact(); p["activities"][0]["evidence_urls"] = ["https://server.local/report"]
        with self.assertRaises(ValueError): assess(p)

    def test_no_url_credentials(self):
        p = real_impact(); p["activities"][0]["evidence_urls"] = ["https://user:pass@example.org/"]
        with self.assertRaises(ValueError): assess(p)

    def test_no_personal_email(self):
        p = demo(); p["activities"][0]["method"] = "contact person@example.com"
        with self.assertRaises(ValueError): assess(p)

    def test_no_personal_phone(self):
        p = demo(); p["activities"][0]["method"] = "call +1 555 555 5555"
        with self.assertRaises(ValueError): assess(p)

    def test_no_bogus_completed_planning(self):
        p = demo(); p["activities"][0]["evidence_urls"] = ["https://example.org/a"]
        with self.assertRaises(ValueError): assess(p)

    def test_boolean_not_an_integer(self):
        p = real_impact(); p["activities"][0]["harm_incidents"] = False
        with self.assertRaises(ValueError): assess(p)

    def test_too_many_activities(self):
        p = demo(); p["activities"] = []
        for i in range(101):
            item = copy.deepcopy(demo()["activities"][0]); item["id"] = f"activity-{i:03}"
            p["activities"].append(item)
        with self.assertRaises(ValueError): assess(p)

    def test_unsubmitted_review_brief(self):
        text = review_brief(assess(demo()))
        self.assertIn("UNSUBMITTED", text)
        self.assertIn("NOT A NOBEL", text)
        self.assertIn("independently", text.lower())

    def test_tampered_review_brief_fails(self):
        r = assess(demo()); r["evidence_sha256"] = "0" * 64
        with self.assertRaises(ValueError): review_brief(r)

    def test_kit_human_led(self):
        text = facilitator_kit()
        self.assertIn("trained human", text)
        self.assertIn("consent", text.lower())
        self.assertIn("independent evaluator", text.lower())


class LauncherTests(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        return subprocess.run(["bash", str(ROOT / "run-GPT-Doug-PeaceLab.command"), *args],
                              cwd=cwd or ROOT, capture_output=True, text=True, timeout=12)

    def test_launch_from_elsewhere(self):
        with tempfile.TemporaryDirectory() as d:
            proc = self.run_cli("demo", cwd=d)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertTrue(json.loads(proc.stdout)["nobel"]["self_nomination_valid"] is False)

    def test_init_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "snapshot.json")
            first = self.run_cli("init", path)
            second = self.run_cli("init", path)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertNotEqual(second.returncode, 0)
            self.assertTrue(json.loads(Path(path).read_text())["activities"][0]["synthetic"])

    def test_roundtrip_replay(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "report.json"
            proc = self.run_cli("demo")
            f.write_text(proc.stdout)
            verify_result = self.run_cli("verify", str(f))
            self.assertEqual(verify_result.returncode, 0, verify_result.stderr)
            self.assertTrue(json.loads(verify_result.stdout)["local_report_replay_valid"])

    def test_nonexistent_file(self):
        p = self.run_cli("assess", "/this/file/does/not/exist.json")
        self.assertNotEqual(p.returncode, 0)

    def test_kit_one_shot(self):
        p = self.run_cli("kit")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("45-minute", p.stdout)


if __name__ == "__main__":
    unittest.main()
