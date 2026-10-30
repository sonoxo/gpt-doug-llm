import unittest

from gpt_doug.rea_recovery import HealthSignal, RecoveryEngine, RecoveryPolicy
from gpt_doug.rea_recovery.engine import HealthState


def signal(state):
    return HealthSignal("component:api", state, "2026-10-30T10:00:00Z", evidence_refs=("probe:1",))


class RecoveryEngineTests(unittest.TestCase):
    def test_healthy_resets_retry_state(self):
        engine = RecoveryEngine()
        engine.attempts["component:api"] = 2
        result = engine.evaluate(signal(HealthState.HEALTHY))
        self.assertEqual(result.decision, "stable")
        self.assertEqual(engine.attempts["component:api"], 0)

    def test_failure_requires_verified_checkpoint(self):
        engine = RecoveryEngine()
        result = engine.evaluate(signal(HealthState.FAILED))
        self.assertEqual(result.decision, "hold")
        self.assertEqual(result.recommended_action, "create_and_verify_checkpoint")

    def test_verified_checkpoint_allows_bounded_retry_recommendation(self):
        engine = RecoveryEngine()
        engine.register_verified_checkpoint("component:api", "checkpoint:stable-1", "a" * 64)
        result = engine.evaluate(signal(HealthState.FAILED))
        self.assertEqual(result.decision, "recommend")
        self.assertEqual(result.retry_after_seconds, 1)
        self.assertEqual(result.checkpoint_id, "checkpoint:stable-1")

    def test_retry_budget_opens_circuit(self):
        engine = RecoveryEngine(policy=RecoveryPolicy(max_cycles=1))
        engine.register_verified_checkpoint("component:api", "checkpoint:stable-1", "b" * 64)
        engine.evaluate(signal(HealthState.FAILED))
        result = engine.evaluate(signal(HealthState.FAILED))
        self.assertEqual(result.decision, "hold")
        self.assertIn("component:api", engine.circuit_open)

    def test_degraded_and_unknown_never_trigger_retry(self):
        engine = RecoveryEngine()
        self.assertEqual(engine.evaluate(signal(HealthState.DEGRADED)).decision, "observe")
        self.assertEqual(engine.evaluate(signal(HealthState.UNKNOWN)).decision, "hold")

    def test_no_shell_or_deployment_side_effects(self):
        engine = RecoveryEngine()
        engine.evaluate(signal(HealthState.HEALTHY))
        snapshot = engine.snapshot()
        self.assertFalse(snapshot["executes_repairs"])
        self.assertFalse(snapshot["runs_shell_commands"])
        self.assertFalse(snapshot["autonomous_deploy"])


if __name__ == "__main__":
    unittest.main()
