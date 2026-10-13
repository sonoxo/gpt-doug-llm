"""Exercise all 50 offline tools; no external API credentials required."""
import argparse
import json
import unittest
from unittest.mock import patch

from research_lab.lattice_50_tools import TOOLS, dataset, invoke, privacy_audit


class Lattice50Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sample = dataset(16, 20)
        cls.args = argparse.Namespace(id="", query="", threshold=25)

    def test_exactly_fifty_tools_five_domains(self):
        self.assertEqual(len(TOOLS), 50)
        for prefix in ("entities", "tasks", "objects", "video", "developer"):
            self.assertEqual(len([n for n in TOOLS if n.startswith(prefix + ".")]), 10)

    def test_every_tool_executes_and_serializes(self):
        for name in TOOLS:
            with self.subTest(tool=name):
                result = invoke(name, self.sample, self.args)
                self.assertEqual(result["mode"], "offline-synthetic")
                self.assertFalse(result["api_compatible"])
                json.dumps(result)

    def test_all_validators(self):
        h = invoke("developer.health", self.sample, self.args)["result"]
        self.assertTrue(all(v["valid"] for v in h.values()))

    def test_full_fleet_count_and_bounded_preview(self):
        s = dataset(1000, 100)
        self.assertEqual(s["sampled"], 10)
        self.assertEqual(s["omitted"], 990)
        roles = invoke("entities.roles", s, self.args)["result"]
        self.assertEqual(sum(roles.values()), 1000)

    def test_huge_fleet_rejected(self):
        with self.assertRaises(ValueError):
            dataset(999999999999, 2)

    def test_no_credentials_in_outputs(self):
        with patch.dict("os.environ", {"ENVIRONMENT_TOKEN": "PRIVATE_SHOULD_NOT_APPEAR", "SANDBOXES_TOKEN": "OTHER_PRIVATE"}):
            response = invoke("developer.auth", self.sample, self.args)
        self.assertNotIn("PRIVATE_SHOULD_NOT_APPEAR", json.dumps(response))
        self.assertEqual(response["result"]["ENVIRONMENT_TOKEN"], True)
        self.assertFalse(privacy_audit(self.sample)["credentials_in_synthetic_records"])

    def test_invalid_name_rejected(self):
        with self.assertRaises(KeyError):
            invoke("tasks.dispatch_real_robot", self.sample, self.args)

    def test_all_assets_marked_synthetic(self):
        for key in ("entities", "tasks", "objects", "video"):
            self.assertTrue(all(r["synthetic"] for r in self.sample[key]))


if __name__ == "__main__":
    unittest.main()
