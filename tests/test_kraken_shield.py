"""Offline Kraken Shield CL1 regression suite. No network, cloud API or secrets."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from kraken_shield import KrakenShield, KrakenShieldError


class FakeGolden:
    def __init__(self, action="ALLOW", fail=False):
        self.action = action
        self.fail = fail
        self.calls = 0

    def inspect_inbound(self, text, source="local"):
        self.calls += 1
        if self.fail:
            raise OSError("simulated guard failure")
        return SimpleNamespace(action=self.action)


class KrakenShieldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.env = mock.patch.dict(os.environ, {
            "GPT_DOUG_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
            "OLLAMA_MODEL": "qwen2.5-coder:3b",
            "GPT_DOUG_AI_BLOCK_ALL": "0",
            "GPT_DOUG_AI_STOP_DIR": str(self.root / "stop"),
            "GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY": "0",
        })
        self.env.start()
        self.addCleanup(self.env.stop)
        self.fake = FakeGolden()
        self.guard = KrakenShield(state_dir=self.root / "audit", shield=self.fake)

    def test_status_is_read_only_and_local(self):
        state = self.guard.status()
        self.assertTrue(state["ready"])
        self.assertFalse(state["paid_services_allowed"])
        self.assertFalse(state["autonomous_execution"])
        self.assertEqual(state["provider_policy"]["provider"], "ollama")
        self.assertFalse((self.root / "audit").exists())

    def test_ontology_is_valid(self):
        ontology = json.loads((Path(__file__).resolve().parents[1] / "kraken_shield" / "ontology.json").read_text())
        self.assertEqual(ontology["operating_mode"], "LOCAL_ONLY_DEFENSIVE")
        self.assertFalse(ontology["paid_services_allowed"])
        self.assertTrue(any(edge[0] == "kraken" and edge[1] == "audit" for edge in ontology["edges"]))

    def test_allow_is_only_an_assessment_and_audited_without_raw_text(self):
        result = self.guard.inspect("Build a private dashboard with secret=DO_NOT_SAVE", source="test")
        self.assertEqual(result["decision"], "ALLOW")
        self.assertFalse(result["executed"])
        self.assertEqual(self.fake.calls, 1)
        audit = self.guard.audit_path.read_text(encoding="utf-8")
        self.assertNotIn("DO_NOT_SAVE", audit)
        self.assertNotIn("private dashboard", audit)
        self.assertTrue(self.guard.verify_audit()["valid"])

    def test_golden_block_is_denied_and_logged(self):
        self.fake.action = "QUARANTINE"
        result = self.guard.inspect("test request")
        self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(result["reason_code"], "golden_shield_reject")

    def test_stop_latch_blocks_before_golden_shield(self):
        with mock.patch.dict(os.environ, {"GPT_DOUG_AI_BLOCK_ALL": "1"}):
            result = self.guard.inspect("Safe request")
            self.assertEqual(result["reason_code"], "operator_stop")
            self.assertEqual(result["decision"], "BLOCK")
        self.assertEqual(self.fake.calls, 0)

    def test_remote_provider_fails_closed(self):
        for name in ("openai", "gemini", "auto", "xunia"):
            with self.subTest(provider=name), mock.patch.dict(os.environ, {"GPT_DOUG_PROVIDER": name}):
                result = self.guard.inspect("Safe request")
                self.assertEqual(result["decision"], "BLOCK")
                self.assertEqual(result["reason_code"], "nonlocal_provider")
        self.assertEqual(self.fake.calls, 0)

    def test_local_policy_rejects_cloud_url_and_cloud_model(self):
        with mock.patch.dict(os.environ, {"OLLAMA_BASE_URL": "https://api.example.com/v1"}):
            self.assertEqual(self.guard.inspect("hello")["reason_code"], "nonlocal_endpoint")
        with mock.patch.dict(os.environ, {"OLLAMA_MODEL": "gemma4:cloud"}):
            self.assertEqual(self.guard.inspect("hello")["reason_code"], "cloud_model_blocked")

    def test_oversize_request_never_reaches_golden(self):
        self.assertEqual(self.guard.inspect("A" * 16_385)["reason_code"], "invalid_request_size")
        self.assertEqual(self.fake.calls, 0)

    def test_guard_error_fails_closed(self):
        self.fake.fail = True
        self.assertEqual(self.guard.inspect("hello")["reason_code"], "golden_shield_unavailable")

    def test_capability_is_advisory_and_cannot_run_deploy(self):
        self.assertEqual(self.guard.check_capability("local_report")["decision"], "ALLOW")
        blocked = self.guard.check_capability("deployment")
        self.assertEqual(blocked["decision"], "BLOCK")
        self.assertFalse(blocked["executed"])

    def test_corruption_is_detected_and_next_request_fails_closed(self):
        self.guard.inspect("hello")
        path = self.guard.audit_path
        path.write_text(path.read_text(encoding="utf-8").replace('"ALLOW"', '"BLOCK"'), encoding="utf-8")
        self.assertFalse(self.guard.verify_audit()["valid"])
        with self.assertRaises(KrakenShieldError):
            self.guard.inspect("another request")

    def test_symlinked_audit_path_fails_closed(self):
        audit_dir = self.root / "audit"
        audit_dir.mkdir(mode=0o700)
        target = self.root / "outside.jsonl"
        target.write_text("", encoding="utf-8")
        (audit_dir / "decisions.jsonl").symlink_to(target)
        self.assertFalse(self.guard.verify_audit()["valid"])
        with self.assertRaises(KrakenShieldError):
            self.guard.inspect("another request")
        self.assertEqual(target.read_text(encoding="utf-8"), "")

    def test_private_directory_permissions(self):
        self.guard.inspect("hello")
        self.assertEqual(self.guard.state_dir.stat().st_mode & 0o077, 0)
        self.assertEqual(self.guard.audit_path.stat().st_mode & 0o077, 0)


if __name__ == "__main__":
    unittest.main()
