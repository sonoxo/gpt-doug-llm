"""Kraken Shield web preflight smoke tests; no network or model calls."""
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from kraken_shield import KrakenShield


class StubGolden:
    action = "ALLOW"
    def inspect_inbound(self, text, source="local"):
        return SimpleNamespace(action=self.action)


class KrakenWebTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        patcher = mock.patch.dict(os.environ, {
            "GPT_DOUG_PROVIDER": "ollama",
            "OLLAMA_BASE_URL": "http://127.0.0.1:11434",
            "OLLAMA_MODEL": "qwen2.5-coder:3b",
            "GPT_DOUG_AI_BLOCK_ALL": "0",
            "GPT_DOUG_AI_STOP_DIR": str(root / "stop"),
            "GPT_DOUG_AI_REQUIRE_STOP_DIRECTORY": "0",
        })
        patcher.start()
        self.addCleanup(patcher.stop)
        self.golden = StubGolden()
        self.shield = KrakenShield(state_dir=root / "audit", shield=self.golden)

    def test_standard_and_streaming_handlers_import_offline(self):
        from web import server as base
        from web import xunia_server

        self.assertTrue(hasattr(base.Handler, "_handle_chat"))
        self.assertTrue(hasattr(xunia_server.XuniaHandler, "_handle_chat"))

    def test_preflight_allows_safe_request_and_denies_golden_rejection(self):
        from web import server as base

        with mock.patch.object(base, "_KRAKEN_GUARD", self.shield):
            self.assertIsNone(base.kraken_preflight("Build a local dashboard"))
            self.golden.action = "BLOCK"
            msg = base.kraken_preflight("bad request")
            self.assertIn("Kraken Shield blocked request", msg)

    def test_preflight_denies_audit_failure(self):
        from web import server as base

        self.shield._append = mock.Mock(side_effect=OSError("simulated filesystem error"))
        with mock.patch.object(base, "_KRAKEN_GUARD", self.shield):
            msg = base.kraken_preflight("safe request")
            self.assertIn("Kraken Shield unavailable", msg)


if __name__ == "__main__":
    unittest.main()
