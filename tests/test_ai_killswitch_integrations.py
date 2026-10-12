"""Emergency stop regression checks at actual model, agent and tool boundaries."""
from __future__ import annotations

import importlib.util
import os
import sys
import tempfile
import threading
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import ai_killswitch as ks


class TestAIStopEnforcement(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patcher = mock.patch.dict(os.environ, {
            ks.STATE_DIRECTORY_ENV: str(Path(self.tmp.name)/"switch"),
            ks.FORCE_STOP_ENV: "0",
        })
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_provider_facade_rejects_all_model_requests(self):
        from agents import llm_backend
        messages = [{"role": "user", "content": "do not send"}]
        fake = mock.Mock()
        ks.emergency_stop()
        with mock.patch.object(llm_backend, "_provider", fake):
            with self.assertRaises(ks.AIKillSwitchEngaged):
                llm_backend.chat_once(messages)
            with self.assertRaises(ks.AIKillSwitchEngaged):
                list(llm_backend.chat_stream(messages))
            fake.chat_once.assert_not_called()
            self.assertTrue(llm_backend.health()["killswitch"]["stopped"])

    def test_provider_http_transport_rejects_before_socket(self):
        from agents import llm_backend
        ks.emergency_stop()
        with mock.patch.object(urllib.request, "urlopen") as fake_network:
            with self.assertRaises(ks.AIKillSwitchEngaged):
                llm_backend._safe_urlopen(
                    urllib.request.Request("https://api.openai.com/v1/chat/completions"),
                    timeout=3,
                )
            fake_network.assert_not_called()

    def test_mission_control_blocks_new_dags(self):
        from zyra_control_plane.control_plane import MissionControl
        from zyra_control_plane.dag import MissionDAG, MissionStep
        ctrl = MissionControl(Path(self.tmp.name)/"mission")
        ks.emergency_stop()
        dag = MissionDAG([MissionStep("a", "test", "zyra")])
        with self.assertRaises(ks.AIKillSwitchEngaged):
            ctrl.new_mission("should not start", dag)

    def test_mission_control_cannot_run_second_step_after_stop(self):
        from zyra_control_plane.control_plane import MissionControl
        from zyra_control_plane.dag import MissionDAG, MissionStep, StepResult
        ctrl = MissionControl(Path(self.tmp.name)/"mission")
        dag = MissionDAG([
            MissionStep("a", "start", "gpt-doug-core", capabilities=("plan",)),
            MissionStep("b", "dispatch", "zyra", depends_on=("a",), capabilities=("plan",)),
        ])
        mission = ctrl.new_mission("test", dag)
        seen = []
        def execute(step):
            seen.append(step.step_id)
            if step.step_id == "a":
                ks.emergency_stop()
            return StepResult(step.step_id, True)
        outcome = ctrl.execute(mission, {"gpt-doug-core": execute, "zyra": execute})
        self.assertFalse(outcome["verified"])
        self.assertEqual(seen, ["a"])

    def test_wakeup3lm_tools_block_even_with_valid_decision(self):
        from wakeup3lm.runtime import DecisionStatus, Wakeup3LM
        workspace = Path(self.tmp.name)/"w"
        workspace.mkdir()
        runtime = Wakeup3LM(workspace_root=workspace)
        ks.emergency_stop()
        outcome = runtime.execute({"action":"write_file", "arguments":{"path":"x.txt","content":"unsafe"}})
        self.assertEqual(outcome.status, DecisionStatus.BLOCKED)
        self.assertFalse((workspace/"x.txt").exists())

    def test_brain_injected_model_cannot_bypass(self):
        from gpt_brain.kernel import BrainKernel
        fake_call = mock.Mock(return_value={"message":{"content":"unexpected"}})
        brain = BrainKernel(chat_fn=fake_call)
        ks.emergency_stop()
        with self.assertRaises(ks.AIKillSwitchEngaged):
            brain.run("this must be blocked")
        fake_call.assert_not_called()

    def test_supervised_subprocess_is_terminated_after_stop(self):
        source = Path(__file__).resolve().parents[1]/"workers"/"agent-daemon.py"
        spec = importlib.util.spec_from_file_location("ai_stop_test_worker", source)
        self.assertIsNotNone(spec)
        worker = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(worker)
        failures = []
        started = threading.Event()
        def invoke():
            try:
                worker._run_supervised([sys.executable, "-c", "import time; time.sleep(8)"],
                                       cwd=self.tmp.name, timeout=12, started=started)
            except ks.AIKillSwitchEngaged:
                failures.append("stopped")
        thread = threading.Thread(target=invoke)
        thread.start()
        self.assertTrue(started.wait(3))
        ks.emergency_stop()
        thread.join(timeout=3)
        self.assertFalse(thread.is_alive(), "worker must terminate shortly after STOP")
        self.assertEqual(failures, ["stopped"])


if __name__ == "__main__":
    unittest.main()
