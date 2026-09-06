import copy
import json
import unittest
from pathlib import Path

from tools.validate_cyber_ontology import validate


class CyberOntologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(Path("kraken_jutsu/cyber_ontology.json").read_text(encoding="utf-8"))

    def test_repository_ontology_is_valid(self):
        self.assertEqual(validate(self.data), [])

    def test_network_sources_require_authorization(self):
        data = copy.deepcopy(self.data)
        source = next(item for item in data["sources"] if item["id"] == "nuclei-runtime")
        source["authorization_required"] = False
        errors = validate(data)
        self.assertTrue(any("explicit authorization" in error for error in errors))

    def test_default_posture_cannot_become_autonomous(self):
        data = copy.deepcopy(self.data)
        data["default_posture"] = "autonomous_execute"
        self.assertIn("default_posture must remain analyze_only", validate(data))

    def test_egress_must_remain_deny_by_default(self):
        data = copy.deepcopy(self.data)
        data["guardrails"]["network_egress"] = "allow"
        errors = validate(data)
        self.assertTrue(any("network_egress" in error for error in errors))

    def test_relation_endpoints_must_exist(self):
        data = copy.deepcopy(self.data)
        data["relation_types"].append({"name": "BAD", "from": "Unknown", "to": "Asset"})
        errors = validate(data)
        self.assertTrue(any("unknown source type" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
