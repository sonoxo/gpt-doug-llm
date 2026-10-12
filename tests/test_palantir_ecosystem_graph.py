"""Deterministic standard-library checks for the isolated ecosystem graph."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from zyrapalantir.ecosystem_intelligence import (
    CLAIM_STATUS,
    DiagramValidationError,
    graph_snapshot,
    load_diagram,
    ontology_export,
    validate_diagram,
)


ROOT = Path(__file__).resolve().parent.parent


class DiagramGraphTests(unittest.TestCase):
    def test_graph_has_stable_nodes_and_all_links_have_provenance(self):
        data = load_diagram()
        graph = graph_snapshot()
        self.assertGreater(graph["metrics"]["depicted_entities"], 40)
        self.assertEqual(graph["metrics"]["groups"], len(data["groups"]))
        self.assertEqual(graph["metrics"]["independently_verified_links"], 0)
        ids = [node["id"] for node in graph["nodes"]]
        self.assertEqual(len(ids), len(set(ids)))
        for link in graph["links"]:
            self.assertIn(link["source"], ids)
            self.assertIn(link["target"], ids)
            self.assertEqual(link["claim_status"], CLAIM_STATUS)
            self.assertEqual(link["source_id"], data["source"]["id"])

    def test_fail_closed_provenance_and_authority(self):
        data = load_diagram()
        for section, key, new_value in (
            ("controls", "external_writes", True),
            ("controls", "third_party_access", True),
            ("source", "verification_status", "verified"),
            ("source", "sha256", "not-a-sha256"),
        ):
            tampered = copy.deepcopy(data)
            tampered[section][key] = new_value
            with self.subTest(key=key), self.assertRaises(DiagramValidationError):
                validate_diagram(tampered)

    def test_duplicate_entity_is_rejected(self):
        data = load_diagram()
        tampered = copy.deepcopy(data)
        tampered["groups"][0]["members"].append(data["groups"][1]["members"][0])
        with self.assertRaises(DiagramValidationError):
            validate_diagram(tampered)

    def test_projection_is_explicitly_review_only(self):
        export = ontology_export()
        self.assertFalse(export["import_executed"])
        self.assertFalse(export["execution_authorized"])
        self.assertEqual(export["source"]["verification_status"], "unverified")
        self.assertTrue(all(edge["claim_status"] == CLAIM_STATUS for edge in export["links"]))

    def test_cli_runs_with_no_network_or_secrets(self):
        proc = subprocess.run(
            [sys.executable, "-m", "zyrapalantir.ecosystem_intelligence", "status"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        )
        result = json.loads(proc.stdout)
        self.assertFalse(result["controls"]["third_party_access"])
        self.assertGreater(result["metrics"]["depicted_links"], 40)

    def test_static_view_has_clear_disclaimer(self):
        page = (ROOT / "agency_cloud/static/palantir-ecosystem.html").read_text(encoding="utf8")
        script = (ROOT / "agency_cloud/static/palantir-ecosystem.js").read_text(encoding="utf8")
        self.assertIn("UNVERIFIED", page)
        self.assertIn("palantir-ecosystem-data.json", script)
        self.assertNotIn("innerHTML", script)


if __name__ == "__main__":
    unittest.main()
