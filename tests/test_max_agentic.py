import tempfile
import unittest
from pathlib import Path

from agents.max_agentic import ZyraMaxOrchestrator
from agents.protective_order import authorize_capability, status


class MaxAgenticPolicyTests(unittest.TestCase):
    def test_protective_order_blocks_destructive_controls(self):
        for capability in (
            "weapon_control",
            "targeting",
            "launch_control",
            "destructive_external_control",
            "safety_bypass",
        ):
            self.assertFalse(authorize_capability(capability)["allowed"])

    def test_protective_order_allows_defensive_engineering(self):
        for capability in (
            "repository_read",
            "repository_write",
            "test_execution",
            "checkpoint",
            "rollback",
            "emergency_shutdown",
        ):
            self.assertTrue(authorize_capability(capability)["allowed"])

    def test_max_starts_dormant_and_requires_operator(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = ZyraMaxOrchestrator(Path(tmp), model="test", state_dir=Path(tmp) / ".state")
            current = agent.status()
            self.assertTrue(current["sleeper_mode"])
            self.assertFalse(current["operator_authorized"])
            self.assertTrue(current["no_rebellion"])
            self.assertFalse(current["weapon_control"])

    def test_operator_override_cannot_change_hard_boundaries(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = ZyraMaxOrchestrator(Path(tmp), model="test", state_dir=Path(tmp) / ".state")
            agent.authorize_operator()
            result = agent.operator_override(max_steps=64, max_model_calls=96)
            self.assertEqual(result["profile"]["max_steps"], 64)
            self.assertEqual(result["profile"]["max_model_calls"], 96)
            self.assertFalse(result["non_bypassable"]["weapon_control"])
            self.assertTrue(result["non_bypassable"]["rollback_required"])

    def test_emergency_shutdown_latches(self):
        with tempfile.TemporaryDirectory() as tmp:
            agent = ZyraMaxOrchestrator(Path(tmp), model="test", state_dir=Path(tmp) / ".state")
            agent.authorize_operator()
            agent.activate()
            shutdown = agent.emergency_shutdown()
            self.assertEqual(shutdown["status"], "SHUTDOWN_LATCHED")
            self.assertTrue(agent.status()["shutdown_latched"])

    def test_policy_status_is_defensive_only(self):
        self.assertEqual(status()["mode"], "DEFENSIVE_ONLY")


if __name__ == "__main__":
    unittest.main()
