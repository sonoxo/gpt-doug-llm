from __future__ import annotations

import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from gpt_zyra_shaggoth.bridge import BridgePolicy, ZyraShaggothBridge
from gpt_zyra_shaggoth.cli import main


class ZyraShaggothBridgeTests(unittest.TestCase):
    def test_status_is_hardwired_and_local_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            bridge = ZyraShaggothBridge(tmp)
            status = bridge.status()
            self.assertEqual(status["system"], "GPT-ZYRA-SHAGGOTH")
            self.assertEqual(status["binding"]["project"], "gpt-doug-llm")
            self.assertEqual(status["binding"]["control_plane"], "zyra_control_plane")
            self.assertFalse(status["policy"]["network_allowed"])
            self.assertFalse(status["policy"]["external_effects_allowed"])
            self.assertFalse(status["policy"]["remote_console_allowed"])
            self.assertTrue(status["verification"]["ok"])

    def test_verify_denies_network_and_external_delivery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = ZyraShaggothBridge(tmp).verify()
            self.assertTrue(result["ok"])
            self.assertTrue(result["checks"]["github_delivery_denied"])
            self.assertTrue(result["checks"]["network_provider_denied"])
            self.assertIn("external-effect-boundary", result["denials"]["github"])
            self.assertIn("network-boundary", result["denials"]["network_provider"])

    def test_plan_routes_through_existing_gpt_doug_control_plane(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plan = ZyraShaggothBridge(tmp).plan("  harden local bridge  ")
            self.assertEqual(plan["goal"], "harden local bridge")
            self.assertEqual(plan["model_route"], "gpt-doug-core")
            self.assertEqual(plan["grant"], "read-only")
            executors = [step["executor"] for step in plan["dag"]["steps"]]
            self.assertEqual(executors, ["gpt-doug-core", "security", "gpt-doug-core"])

    def test_escalating_policy_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                ZyraShaggothBridge(tmp, policy=BridgePolicy(network_allowed=True))
            with self.assertRaises(ValueError):
                ZyraShaggothBridge(tmp, policy=BridgePolicy(external_effects_allowed=True))
            with self.assertRaises(ValueError):
                ZyraShaggothBridge(tmp, policy=BridgePolicy(remote_console_allowed=True))

    @unittest.skipIf(not hasattr(os, "symlink"), "symlinks unavailable")
    def test_symlink_state_directory_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "target"
            target.mkdir()
            link = root / "state"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaises(ValueError):
                ZyraShaggothBridge(link)

    def test_cli_verify_returns_machine_readable_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with redirect_stdout(out):
                code = main(["--state-dir", tmp, "verify"])
            payload = json.loads(out.getvalue())
            self.assertEqual(code, 0)
            self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
