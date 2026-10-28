import unittest

from gpt_doug.swarm_brain import AgentSpec, SwarmBrain, Task


class GoldenSwarmBrainTests(unittest.TestCase):
    def test_huge_identity_space_is_virtual(self):
        brain = SwarmBrain()
        a = brain.virtual_agent_id(42, "critic")
        self.assertEqual(a, brain.virtual_agent_id(42, "critic"))
        self.assertEqual(brain.snapshot()["logical_agent_count"], 99_999_999_999)
        self.assertFalse(brain.snapshot()["logical_id_space_materialized"])

    def test_index_bounds(self):
        brain = SwarmBrain()
        with self.assertRaises(IndexError):
            brain.virtual_agent_id(99_999_999_999)

    def test_capability_routing(self):
        brain = SwarmBrain()
        brain.register_worker(AgentSpec("worker:evidence", "evidence_auditor", ("research", "citation_check")))
        result = brain.dispatch(Task("task-1", "verify source", ("citation_check",)))
        self.assertEqual(result.status, "assigned")
        self.assertEqual(result.assigned_agent_id, "worker:evidence")

    def test_high_risk_fails_closed(self):
        brain = SwarmBrain()
        brain.register_worker(AgentSpec("worker:ops", "operator", ("ops",)))
        result = brain.dispatch(Task("task-2", "change production", ("ops",), "high"))
        self.assertEqual(result.status, "held")
        self.assertEqual(result.reason, "policy_approval_required")

    def test_no_worker_stays_queued(self):
        result = SwarmBrain().dispatch(Task("task-3", "analyze", ("vision",)))
        self.assertEqual(result.status, "queued")


if __name__ == "__main__":
    unittest.main()
