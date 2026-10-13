"""Security and integration checks for the ontology-backed PeaceLab review model."""
from __future__ import annotations

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from peace_impact.ontology_graph import (ONTOLOGY, LEGACY, audit_ontology,
    graphviz_dot, load_ontology, standalone_html, text_map)
from peace_impact.pilot import GATES, PHASES, RISKS

ROOT = Path(__file__).resolve().parents[1]


def cli(*args, cwd=ROOT):
    return subprocess.run(["bash", str(ROOT / "scripts" / "doug-max"), "peace-lab", *args],
                          cwd=cwd, text=True, capture_output=True, timeout=15)


class SemanticOntologyTests(unittest.TestCase):
    def test_01_valid_jsonld_root_and_references(self):
        r = audit_ontology(load_ontology())
        self.assertEqual(r["status"], "VALID_REPOSITORY_ONTOLOGY")
        self.assertEqual(r["graph_nodes"], 54)
        self.assertEqual(r["safety_gates_pending"], 8)
        self.assertEqual(r["harm_risks"], 5)
        self.assertEqual(r["classes"], 11)
        self.assertEqual(r["relations"], 7)
        self.assertFalse(r["fieldwork_authorized"])

    def test_02_graph_binds_actual_pilot_definitions(self):
        doc = load_ontology()
        rows = {node["@id"]: node for node in doc["@graph"]}
        self.assertEqual(rows["pl:pilot-90-day"]["hasGate"],
                         ["pl:gate-" + g[0] for g in GATES])
        self.assertEqual(rows["pl:pilot-90-day"]["hasPhase"],
                         ["pl:phase-" + p["days"] for p in PHASES])
        self.assertEqual(rows["pl:pilot-90-day"]["hasRisk"],
                         ["pl:risk-" + r["id"] for r in RISKS])

    def test_03_provenance_not_automatically_trusted(self):
        r = audit_ontology(load_ontology())
        self.assertEqual(r["provenance_states"], 4)
        self.assertFalse(r["external_peace_impact_verified"])
        self.assertFalse(r["rdf_semantic_reasoning_performed"])
        self.assertFalse(r["nobel_nomination_submitted"])

    def test_04_sha_is_deterministic(self):
        self.assertEqual(audit_ontology(load_ontology())["ontology_sha256"],
                         audit_ontology(load_ontology())["ontology_sha256"])

    def test_05_gate_tamper_rejected(self):
        d = load_ontology()
        gates = [n for n in d["@graph"] if n["@type"] == "pl:SafetyGate"]
        gates[0]["pl:reviewState"] = "APPROVED"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_06_fake_external_review_rejected(self):
        d = load_ontology()
        for n in d["@graph"]:
            if n["@id"] == "pl:role-independent-evaluator":
                n["pl:identifiedOrApproved"] = True
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_07_field_authority_never_promoted(self):
        d = load_ontology()
        d["pl:authorityBoundary"] = "GRANTED"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_08_risk_stop_trigger_must_match_runtime(self):
        d = load_ontology()
        for n in d["@graph"]:
            if n["@id"] == "pl:risk-privacy":
                n["pl:stopTrigger"] = "IGNORE"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_09_phase_permission_cannot_drift(self):
        d = load_ontology()
        for n in d["@graph"]:
            if n["@id"] == "pl:phase-61-75":
                n["pl:permissionBoundary"] = "AUTO LAUNCH"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_10_nobel_claim_rejected(self):
        d = load_ontology()
        d["pl:nobelNominationSubmitted"] = True
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_11_number_as_boolean_rejected(self):
        d = load_ontology()
        d["pl:verifiedRealWorldOutcomes"] = False
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_12_missing_governance_node_rejected(self):
        d = load_ontology()
        d["@graph"] = [n for n in d["@graph"] if n["@id"] != "pl:policy-no-nobel-application"]
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_13_duplicate_node_rejected(self):
        d = load_ontology()
        d["@graph"].append(copy.deepcopy(d["@graph"][0]))
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_14_external_references_rejected(self):
        d = load_ontology()
        for n in d["@graph"]:
            if n["@id"] == "pl:program":
                n["hasPilot"] = "https://unknown.invalid/ontology"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_15_context_remap_rejected(self):
        d = load_ontology()
        d["@context"]["pl"] = "https://evil.invalid/"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_16_remote_context_rejected(self):
        d = load_ontology()
        d["@context"] = "https://evil.invalid/context.jsonld"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_17_unknown_node_field_rejected(self):
        d = load_ontology()
        for n in d["@graph"]:
            if n["@id"] == "pl:program":
                n["pl:secretRecipient"] = "someone"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_18_legacy_auto_nobel_must_stay_denied(self):
        legacy = json.loads(LEGACY.read_text())
        legacy["automatic_nobel_nomination"] = True
        with self.assertRaises(ValueError):audit_ontology(load_ontology(), legacy=legacy)

    def test_19_legacy_human_oversight_required(self):
        legacy = json.loads(LEGACY.read_text())
        legacy["human_oversight"] = False
        with self.assertRaises(ValueError):audit_ontology(load_ontology(), legacy=legacy)

    def test_20_legacy_trust_drift_rejected(self):
        legacy = json.loads(LEGACY.read_text())
        legacy["trust_states"] = ["SYNTHETIC"]
        with self.assertRaises(ValueError):audit_ontology(load_ontology(), legacy=legacy)

    def test_21_reject_symlinked_custom_file(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "ontology"
            p.symlink_to(ONTOLOGY)
            with self.assertRaises(ValueError):load_ontology(p)

    def test_22_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "graph.jsonld"
            p.write_text('{"@graph":[],"@graph":[]}', encoding="utf-8")
            with self.assertRaises(ValueError):load_ontology(p)

    def test_23_deny_policy_drift_rejected(self):
        d = load_ontology()
        for n in d["@graph"]:
            if n["@id"] == "pl:policy-no-autonomous-mediation":
                n["pl:effect"] = "ALLOW"
        with self.assertRaises(ValueError):audit_ontology(d)

    def test_24_html_self_contained_and_no_js(self):
        source = standalone_html(load_ontology())
        self.assertIn("default-src 'none'",source)
        self.assertNotIn("<script",source)
        self.assertNotIn("<iframe",source)
        self.assertIn("no-unverified-impact",source)
        self.assertIn("NO PILOT AUTHORIZATION",source)

    def test_25_ascii_console_map_has_all_gates(self):
        output = text_map(load_ontology())
        self.assertIn("8 PENDING",output)
        self.assertIn("NO NOBEL",output)
        for key, _, role in GATES:
            self.assertIn(key,output)
            self.assertIn(role,output)

    def test_26_graphviz_typed_edges(self):
        result = graphviz_dot(load_ontology())
        self.assertTrue(result.startswith("digraph GPTDougPeaceLab"))
        self.assertIn('"program" -> "pilot"',result)
        self.assertIn('"gate-consent_privacy"',result)
        self.assertIn('"policy-no-identity-tracking"',result)


class IntegratedLauncherTests(unittest.TestCase):
    def test_27_terminal_from_unrelated_directory(self):
        with tempfile.TemporaryDirectory() as folder:
            p = cli("ontology",cwd=folder)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("PEACELAB ONTOLOGY",p.stdout)

    def test_28_cli_validation(self):
        p=cli("ontology-check")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)["status"], "VALID_REPOSITORY_ONTOLOGY")

    def test_29_cli_jsonld_dump(self):
        p=cli("ontology-json")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)["@type"],"owl:Ontology")

    def test_30_cli_graphviz_export(self):
        p=cli("ontology-dot")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("digraph GPTDougPeaceLab",p.stdout)

    def test_31_cli_html_export(self):
        p=cli("ontology-html")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn("GPT-Doug PeaceLab Ontology Map",p.stdout)

    def test_32_cli_fail_closed_tampered_file(self):
        d=load_ontology()
        d["@graph"]=[]
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/"bad.jsonld"
            p.write_text(json.dumps(d),encoding="utf-8")
            r=cli("ontology-check",str(p))
            self.assertEqual(r.returncode,2,r.stderr)

    def test_33_original_pilot_still_works(self):
        p=cli("pilot-demo")
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertEqual(json.loads(p.stdout)["verified_real_world_outcomes"],0)


if __name__=="__main__":
    unittest.main()
