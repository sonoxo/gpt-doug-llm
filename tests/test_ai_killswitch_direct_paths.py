"""No-network tests for legacy direct-Ollama AI execution paths."""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest import mock

import ai_killswitch as ks


class TestLegacyAIEntryPoints(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        patch = mock.patch.dict(os.environ, {
            ks.STATE_DIRECTORY_ENV: str(Path(self.tmp.name) / "operator-stop"),
            ks.REQUIRED_STOP_DIR_ENV: "0",
            ks.FORCE_STOP_ENV: "0",
        })
        patch.start()
        self.addCleanup(patch.stop)

    def test_zyra_agent_direct_model_and_mission_do_not_call_ollama(self):
        from zyra_agent import ZyraAgent

        agent = ZyraAgent(
            self.tmp.name, model="test",
            state_dir=Path(self.tmp.name) / "mission-state",
        )
        ks.emergency_stop()
        with mock.patch.object(urllib.request, "urlopen") as network:
            with self.assertRaises(ks.AIKillSwitchEngaged):
                agent._chat("system", "prompt")
            with self.assertRaises(ks.AIKillSwitchEngaged):
                agent.preview("create a safe plan")
            with self.assertRaises(ks.AIKillSwitchEngaged):
                agent.run("create a safe project")
            network.assert_not_called()
        self.assertFalse(agent.last_result)

    def test_xunia_direct_ollama_client_is_blocked_before_network(self):
        from xunia_godis import OllamaClient

        client = OllamaClient(base_url="http://127.0.0.1:11434")
        ks.emergency_stop()
        with mock.patch.object(urllib.request, "urlopen") as network:
            with self.assertRaises(ks.AIKillSwitchEngaged):
                client.chat("mock", "test")
            network.assert_not_called()

    def test_xunia_readonly_health_still_available(self):
        from xunia_godis import OllamaClient

        client = OllamaClient(base_url="http://127.0.0.1:11434")
        ks.emergency_stop()
        with mock.patch.object(urllib.request, "urlopen") as network:
            response = network.return_value.__enter__.return_value
            response.read.return_value = b'{"models":[{"name":"mock:latest"}]}'
            self.assertEqual(client.installed_models(), ["mock:latest"])
            self.assertEqual(network.call_count, 1)

    def test_zyra_terminal_direct_stream_cannot_make_provider_request(self):
        from zyra_chat import stream_chat

        ks.emergency_stop()
        with mock.patch.object(urllib.request, "urlopen") as network:
            with self.assertRaises(ks.AIKillSwitchEngaged):
                stream_chat("mock", [{"role": "user", "content": "test"}], "fast")
            network.assert_not_called()

    def test_zyra_terminal_stop_is_clean_and_does_not_self_heal(self):
        import zyra_chat

        ks.emergency_stop()
        with (
            mock.patch.object(zyra_chat, "run_self_heal") as heal,
            mock.patch.object(zyra_chat, "Zyra") as zyra,
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            self.assertEqual(zyra_chat.main(), 3)
            self.assertIn("stopped", output.getvalue().lower())
            heal.assert_not_called()
            zyra.assert_not_called()


if __name__ == "__main__":
    unittest.main()
