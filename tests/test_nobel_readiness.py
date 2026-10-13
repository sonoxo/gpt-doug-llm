"""Nobel readiness test contract: truthful status even under optimistic inputs."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from peace_impact.nobel_readiness import (
    CANDIDATE_KINDS, DEADLINE, EVIDENCE_FIELDS, NOMINATOR_CATEGORIES,
    OFFICIAL_SOURCES, MIN_PUBLIC_COHORT, template, validate_inventory,
    review, verify_report, reviewer_brief, visual_html,
)

ROOT = Path(__file__).resolve().parents[1]


def submitted_claim():
    claim = template()
    claim["claims_are_synthetic"] = False
    claim["candidate_kind"] = "ACTIVE_ORGANIZATION"
    claim["candidate_label"] = "Example organization (test only)"
    for key in EVIDENCE_FIELDS:
        claim["evidence_urls"][key] = ["https://example.org/fictional-" + key]
    claim["proposed_nominator_category"] = "ELIGIBLE_UNIVERSITY_ACADEMIC_OR_RECTOR"
    claim["nominator_submission_status"] = "NOMINATOR_SELF_REPORT_ONLY"
    claim["completed_activities_self_reported"] = 2
    claim["aggregate_participants_self_reported"] = 25
    return claim


def run(*args, cwd=ROOT):
    return subprocess.run(["bash", str(ROOT / "scripts" / "doug-max"), "peace-lab", *args],
                          cwd=cwd, capture_output=True, text=True, timeout=20)


class PrizeProcessTests(unittest.TestCase):
    def test_default_has_no_proven_outcomes(self):
        report = review()
        self.assertEqual(report["status"], "NOT_A_NOMINATION_OR_AWARD")
        self.assertFalse(report["actual_nobel_nomination_submitted_by_this_software"])
        self.assertFalse(report["actual_nobel_award_by_this_software"])
        self.assertEqual(report["project_evidence"]["completed_real_activities_self_reported"], 0)
        self.assertEqual(report["project_evidence"]["independently_verified_impact_by_this_software"], 0)
        self.assertEqual(report["project_evidence"]["pending_gates_in_default_synthetic_pilot"], 8)

    def test_official_rules_distinguish_eligibility_from_award(self):
        report = review()["official_rules"]
        self.assertEqual(report["next_regular_deadline"], "2027-01-31")
        self.assertEqual(report["2026_prize_already_awarded_to"], "Navanethem (Navi) Pillay")
        self.assertFalse(report["self_application_valid"])
        self.assertFalse(report["software_repository_alone_eligible"])
        self.assertTrue(report["qualified_external_nominator_required"])
        self.assertTrue(report["nobel_committee_exclusive_selection"])

    def test_official_sources_are_public_original_sources(self):
        self.assertGreaterEqual(len(OFFICIAL_SOURCES), 4)
        self.assertTrue(all(x.startswith("https://www.nobelpeaceprize.org/") for x in OFFICIAL_SOURCES))

    def test_nominator_categories_are_declared_and_not_auto_confirmed(self):
        self.assertIn("ELIGIBLE_UNIVERSITY_ACADEMIC_OR_RECTOR", NOMINATOR_CATEGORIES)
        self.assertIn("NORWEGIAN_NOBEL_COMMITTEE_CURRENT_OR_FORMER_MEMBER", NOMINATOR_CATEGORIES)
        self.assertIsNone(review()["project_evidence"]["proposed_nominator_category_self_reported"])

    def test_report_replay_valid_for_template(self):
        r = review()
        self.assertTrue(verify_report(r))
        self.assertEqual(r, review())
        self.assertEqual(len(r["sha256"]), 64)

    def test_no_public_personal_candidate_identity_in_default(self):
        r = review()
        self.assertEqual(r["candidate"]["kind_self_reported"], "UNDETERMINED")
        self.assertFalse(r["candidate"]["legal_or_personal_eligibility_independently_verified"])

    def test_optimistic_self_report_never_becomes_official(self):
        r = review(submitted_claim())
        self.assertEqual(r["formal_nomination_process"], "INCOMPLETE_OR_NOT_AUTHENTICATED")
        self.assertEqual(r["peace_impact_evidence"], "NOT_INDEPENDENTLY_ESTABLISHED")
        self.assertFalse(r["actual_nobel_nomination_submitted_by_this_software"])
        self.assertEqual(r["project_evidence"]["independently_verified_impact_by_this_software"], 0)
        self.assertTrue(r["independent_human_and_community_review_needed"])
        self.assertTrue(verify_report(r))

    def test_submission_claim_must_stay_self_report(self):
        r = review(submitted_claim())
        self.assertTrue(any("not confirmation by the Nobel Institute" in x for x in r["blockers"]))

    def test_claimed_activities_count_is_not_impact(self):
        p = submitted_claim()
        p["completed_activities_self_reported"] = 1000
        r = review(p)
        self.assertEqual(r["project_evidence"]["completed_real_activities_self_reported"], 1000)
        self.assertEqual(r["project_evidence"]["independently_verified_impact_by_this_software"], 0)

    def test_reject_false_real_results_in_synthetic_demo(self):
        d = template()
        d["completed_activities_self_reported"] = 1
        with self.assertRaises(ValueError):
            review(d)

    def test_reject_false_nominator_claim_in_synthetic_demo(self):
        d = template()
        d["nominator_submission_status"] = "NOMINATOR_SELF_REPORT_ONLY"
        with self.assertRaises(ValueError):
            review(d)

    def test_boolean_is_not_a_real_activity_count(self):
        d = submitted_claim()
        d["completed_activities_self_reported"] = True
        with self.assertRaises(ValueError):
            review(d)

    def test_small_participant_cohort_cannot_be_public(self):
        d = submitted_claim()
        d["aggregate_participants_self_reported"] = 4
        with self.assertRaises(ValueError):
            review(d)

    def test_invalid_candidate_category_rejected(self):
        d = submitted_claim()
        d["candidate_kind"] = "SOFTWARE_AGENT"
        with self.assertRaises(ValueError):
            review(d)

    def test_fabricated_nominator_category_rejected(self):
        d = submitted_claim()
        d["proposed_nominator_category"] = "AI_SUPERINTELLIGENCE"
        with self.assertRaises(ValueError):
            review(d)

    def test_nominator_claim_without_category_rejected(self):
        d = submitted_claim()
        d["proposed_nominator_category"] = None
        with self.assertRaises(ValueError):
            review(d)

    def test_missing_candidate_identity_blocks(self):
        d = submitted_claim()
        d["candidate_kind"] = "UNDETERMINED"
        with self.assertRaises(ValueError):
            review(d)

    def test_fabricated_award_tampering_fails_replay(self):
        r = review()
        r["actual_nobel_award_by_this_software"] = True
        self.assertFalse(verify_report(r))

    def test_fabricated_nomination_tampering_fails_replay(self):
        r = review()
        r["actual_nobel_nomination_submitted_by_this_software"] = True
        self.assertFalse(verify_report(r))

    def test_tampered_sources_fails_replay(self):
        r = review()
        r["official_rules"]["next_regular_deadline"] = "2026-10-13"
        self.assertFalse(verify_report(r))

    def test_tampered_sha_fails_replay(self):
        r = review()
        r["sha256"] = "0" * 64
        self.assertFalse(verify_report(r))

    def test_unknown_field_rejected(self):
        d = template()
        d["official_winner"] = True
        with self.assertRaises(ValueError):
            review(d)

    def test_unsafe_evidence_url_rejected(self):
        d = submitted_claim()
        d["evidence_urls"]["community_partner_review"] = ["http://example.org/"]
        with self.assertRaises(ValueError):
            review(d)

    def test_local_secret_link_rejected(self):
        d = submitted_claim()
        d["evidence_urls"]["real_world_activities_report"] = ["https://localhost/token"]
        with self.assertRaises(ValueError):
            review(d)

    def test_duplicate_evidence_link_rejected(self):
        d = submitted_claim()
        d["evidence_urls"]["community_partner_review"].append("https://example.org/fictional-community_partner_review")
        with self.assertRaises(ValueError):
            review(d)

    def test_html_is_static_and_sandboxed(self):
        h = visual_html(review())
        self.assertIn("default-src 'none'", h)
        self.assertNotIn("<script", h)
        self.assertIn("NOT AN AWARD OR SUBMITTED NOMINATION", h)

    def test_reviewer_brief_does_not_fabricate_a_nomination(self):
        b = reviewer_brief(review())
        self.assertIn("NOT AN OFFICIAL NOMINATION", b)
        self.assertIn("Actual Nobel nomination submitted by this software: NO", b)
        self.assertIn("Independently", b)

    def test_broken_impact_dossier_rejected_for_brief(self):
        r = review()
        r["project_evidence"]["independently_verified_impact_by_this_software"] = 5
        with self.assertRaises(ValueError):
            reviewer_brief(r)

    def test_candidate_label_rejects_personal_phone(self):
        d = submitted_claim()
        d["candidate_label"] = "Call +1 555 000 1234"
        with self.assertRaises(ValueError):
            review(d)


class IntegrationTests(unittest.TestCase):
    def test_cli_default_report(self):
        p = run("nobel-demo")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(verify_report(json.loads(p.stdout)))

    def test_cli_audit_has_no_external_effect(self):
        p = run("nobel-audit")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertFalse(json.loads(p.stdout)["actual_nobel_nomination_submitted_by_this_software"])

    def test_cli_verify_roundtrip_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "audit.json"
            f.write_text(json.dumps(review()), encoding="utf-8")
            p = run("nobel-check", str(f), cwd=d)
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertTrue(json.loads(p.stdout)["local_readiness_replay_valid"])

    def test_cli_bad_report_fails(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "bad.json"
            f.write_text('{"false":true}',encoding="utf-8")
            p = run("nobel-check", str(f))
        self.assertNotEqual(p.returncode, 0)

    def test_cli_brief_output(self):
        p = run("nobel-brief")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("REQUIREMENTS", p.stdout.upper())

    def test_cli_visual_html(self):
        p = run("nobel-html")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("<!doctype html>", p.stdout)
        self.assertIn("NOMINATION",p.stdout.upper())

    def test_cli_init_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            path = str(Path(d) / "private.json")
            # Test Python CLI without modifying any original repo file.
            one = subprocess.run([sys.executable,"-m","peace_impact.cli","nobel-init",path],
                                 cwd=ROOT, capture_output=True,text=True,timeout=10)
            two = subprocess.run([sys.executable,"-m","peace_impact.cli","nobel-init",path],
                                 cwd=ROOT,capture_output=True,text=True,timeout=10)
        self.assertEqual(one.returncode,0,one.stderr)
        self.assertNotEqual(two.returncode,0)
    def test_preexisting_peacelab_pilot_command(self):
        p = run("pilot-demo")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(json.loads(p.stdout)["verified_real_world_outcomes"],0)


if __name__=="__main__":
    unittest.main()
