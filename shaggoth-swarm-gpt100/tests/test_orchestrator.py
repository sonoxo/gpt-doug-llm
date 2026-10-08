import unittest
from shaggoth_swarm.config import SwarmConfig
from shaggoth_swarm.models import TaskState
from shaggoth_swarm.orchestrator import SwarmOrchestrator

class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.config=SwarmConfig(agent_count=100,max_fanout=16,max_depth=2,adapter="mock")
    def test_run_respects_fanout(self):
        report=SwarmOrchestrator(config=self.config).run("Build a scheduler",fanout=10)
        self.assertEqual(len(report.results),10); self.assertEqual(report.succeeded,10)
    def test_fanout_is_capped(self):
        report=SwarmOrchestrator(config=self.config).run("Build a scheduler",fanout=100)
        self.assertEqual(len(report.results),16)
    def test_empty_goal_is_rejected(self):
        with self.assertRaises(ValueError): SwarmOrchestrator(config=self.config).run("   ")
