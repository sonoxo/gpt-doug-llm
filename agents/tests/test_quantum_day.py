"""Regression tests for Q-Day scope, evidence checks, and asset prioritization."""
import json
import tempfile
import unittest
from pathlib import Path

from agents.quantum_day import (AGENCIES, CONTROLS, DEADLINES, assess, assess_asset,
                                main, ontology, template, validate)


class QuantumDayTests(unittest.TestCase):
    def test_all_24_agencies_seeded_without_assumed_compliance(self):
        payload = template()
        self.assertEqual(len(AGENCIES), 24)
        self.assertEqual(len({a for a, _ in AGENCIES}), 24)
        self.assertEqual(len(payload["agencies"]), 24)
        self.assertEqual(payload["agencies"]["USAID"]["controls"], {})
        report = assess(payload)
        self.assertEqual(report["verified_ready_agencies"], 0)
        self.assertTrue(all(x["readiness"] == "NOT_INDEPENDENTLY_VERIFIED" for x in report["agencies"].values()))

    def test_omb_2026_milestones_preserved(self):
        self.assertEqual(DEADLINES["plan_submission"], "2026-10-22")
        self.assertEqual(DEADLINES["tls13_support"], "2030-01-02")
        self.assertEqual(DEADLINES["priority_key_establishment"], "2030-12-31")
        self.assertEqual(DEADLINES["priority_digital_signatures"], "2031")
        self.assertEqual(DEADLINES["remaining_migration"], "2035")

    def test_non_nss_scope_fail_closed(self):
        payload = template()
        payload["policy_scope"] = "all_systems_including_classified"
        with self.assertRaises(ValueError):
            assess(payload)

    def test_reject_unrecognized_agency_or_control(self):
        payload = template()
        payload["agencies"]["CIA"] = {"name": "CIA", "controls": {}, "assets": []}
        with self.assertRaises(ValueError):
            validate(payload)
        payload = template()
        payload["agencies"]["NASA"]["controls"]["we_are_compliant"] = {}
        with self.assertRaises(ValueError):
            validate(payload)

    def test_evidence_requires_provenance_and_never_certifies(self):
        payload = template()
        payload["agencies"]["NASA"]["controls"]["pqc_lead"] = {
            "reference": "agency-local:opaque-proof-id", "reviewer": "appointed-reviewer",
            "reviewed_at": "2026-10-14T12:00:00Z", "source_type": "agency_attestation"
        }
        report = assess(payload)
        nasa = report["agencies"]["NASA"]
        self.assertEqual(nasa["documented_controls"], 1)
        self.assertIn("roadmap", nasa["missing_controls"])
        self.assertFalse(nasa["agency_authorization_claimed"])
        self.assertEqual(report["verified_ready_agencies"], 0)

    def test_reject_unsupported_evidence_or_missing_timezone(self):
        payload = template()
        payload["agencies"]["DOE"]["controls"]["pqc_lead"] = {
            "reference": "x", "reviewer": "y", "reviewed_at": "2026-10-14T12:00:00",
            "source_type": "agency_attestation"
        }
        with self.assertRaises(ValueError):
            assess(payload)
        payload["agencies"]["DOE"]["controls"]["pqc_lead"]["reviewed_at"] = "2026-10-14T12:00:00Z"
        payload["agencies"]["DOE"]["controls"]["pqc_lead"]["source_type"] = "anonymous"
        with self.assertRaises(ValueError):
            assess(payload)

    def test_high_impact_vulnerable_crypto_is_urgent(self):
        asset = {"token": "SYSTEM_0001", "algorithms": ["RSA-2048", "ECDH-P256"],
                 "purposes": ["key_establishment"], "high_value_asset": True,
                 "impact": "high", "sensitivity": "high", "protect_until_year": 2036,
                 "crypto_agile": False}
        payload = template()
        payload["agencies"]["DHS"]["assets"].append(asset)
        r = assess(payload)["agencies"]["DHS"]["priority_assets"][0]
        self.assertEqual(r["priority"], "P0")
        self.assertEqual(len(r["vulnerable_algorithms_reported"]), 2)
        self.assertEqual(r["targets"], ["2030-12-31"])

    def test_unknown_crypto_not_claimed_quantum_safe(self):
        r = assess_asset({"token": "DEVICE_0001", "algorithms": ["future-mystery-kex"],
                          "purposes": ["logical_access"], "high_value_asset": False,
                          "impact": "low", "sensitivity": "low", "crypto_agile": True})
        self.assertEqual(r["priority"], "P1")
        self.assertEqual(r["unclassified_algorithms"], ["FUTURE-MYSTERY-KEX"])

    def test_pqc_name_not_cryptographic_module_certification(self):
        asset = {"token": "SYSTEM_0002", "algorithms": ["ML-KEM-768", "ML-DSA-65"],
                 "purposes": ["key_establishment", "digital_signature"], "high_value_asset": True,
                 "impact": "high", "sensitivity": "high", "crypto_agile": True}
        r = assess_asset(asset)
        self.assertEqual(r["priority"], "P2")
        self.assertEqual(r["finding"], "implementation_validation_required")

    def test_rejects_forged_policy_deadlines_and_source_urls(self):
        payload = template()
        payload["deadlines"]["plan_submission"] = "2100-01-01"
        with self.assertRaises(ValueError):
            validate(payload)
        payload = template()
        payload["sources"]["omb_m26_15"] = "https://untrusted.example/policy"
        with self.assertRaises(ValueError):
            validate(payload)

    def test_refuses_sensitive_host_field(self):
        p = template()
        p["agencies"]["VA"]["assets"].append({
            "token": "ASSET_0001", "hostname": "internal.example", "algorithms": ["RSA"],
            "purposes": ["key_establishment"], "high_value_asset": False,
            "impact": "low", "sensitivity": "low"})
        with self.assertRaises(ValueError):
            validate(p)

    def test_ontology_has_24_agency_nodes_and_control_links(self):
        graph = ontology(template())
        self.assertEqual(len([n for n in graph["nodes"] if n["kind"] == "CFOActAgency"]), 24)
        self.assertEqual(len(graph["edges"]), len(CONTROLS) * 24)
        self.assertTrue(all(e["evidence_state"] == "not_provided" for e in graph["edges"]))

    def test_cli_offline_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            seed = Path(td) / "seed.json"
            self.assertEqual(main(["seed", "--output", str(seed)]), 0)
            self.assertEqual(len(json.loads(seed.read_text())["agencies"]), 24)
            self.assertEqual(main(["seed", "--output", str(seed)]), 2)
            report = Path(td) / "report.json"
            self.assertEqual(main(["assess", "--input", str(seed), "--output", str(report)]), 0)
            self.assertEqual(json.loads(report.read_text())["agency_count"], 24)


if __name__ == "__main__":
    unittest.main()
