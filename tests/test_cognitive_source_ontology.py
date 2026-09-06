import json
import unittest
from pathlib import Path


class CognitiveSourceOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(
            Path("kraken_jutsu/cognitive_sources/darren_kitchen_hak5_2026.json").read_text(encoding="utf-8")
        )

    def test_source_is_public_and_traceable(self):
        provenance = self.data["provenance"]
        self.assertEqual(provenance["classification"], "public")
        self.assertTrue(provenance["primary_source"].startswith("https://www.youtube.com/"))
        self.assertGreaterEqual(provenance["confidence"], 0.70)

    def test_no_literal_mind_copy_claim(self):
        claims = set(self.data["source_identity"]["not_a_claim_of"])
        self.assertIn("literal mind copy", claims)
        self.assertIn("private mental state access", claims)
        self.assertTrue(self.data["inference_policy"]["forbid_identity_claims"])

    def test_active_execution_stays_authorization_gated(self):
        self.assertEqual(
            self.data["inference_policy"]["active_tool_execution"],
            "approval_gated_authorized_targets_only",
        )
        safety_nodes = {
            node["id"]: node for node in self.data["neural_graph"]["nodes"] if node["type"] == "SafetyInvariant"
        }
        self.assertEqual(safety_nodes["guard-authorized-scope"]["weight"], 1.0)

    def test_weighted_edges_reference_known_nodes(self):
        nodes = {node["id"] for node in self.data["neural_graph"]["nodes"]}
        for edge in self.data["neural_graph"]["edges"]:
            self.assertIn(edge["from"], nodes)
            self.assertIn(edge["to"], nodes)
            self.assertGreaterEqual(edge["weight"], 0.0)
            self.assertLessEqual(edge["weight"], 1.0)


if __name__ == "__main__":
    unittest.main()
