"""Offline tests for installed GPT-DOUG framework cross-module health."""
from __future__ import annotations

from io import StringIO
import contextlib
import json
import unittest
from unittest.mock import patch

from gpt_brain import framework_health as health


class FrameworkHealthTests(unittest.TestCase):
    def test_required_components_detected_and_optional_missing_does_not_fail(self):
        core = {module for _, module, required in health._COMPONENTS if required}
        with patch.object(health, "_installed", side_effect=lambda name: name in core):
            with patch.object(health, "_stop_check", return_value={"status": "CLEAR"}):
                report = health.collect_status()
        self.assertTrue(report["core_complete"])
        self.assertEqual(report["missing_required"], [])
        self.assertEqual(report["ollama"]["status"], "NOT_CHECKED")
        self.assertEqual(
            next(x for x in report["components"] if x["component"] == "skull_3d")["status"],
            "MISSING",
        )
        self.assertTrue(report["checks_are_read_only"])

    def test_missing_required_detected_without_importing_model(self):
        with patch.object(health, "_installed", return_value=False):
            with patch.object(health, "_stop_check", return_value={"status": "STOPPED"}):
                result = health.collect_status()
        self.assertFalse(result["core_complete"])
        self.assertIn("brain_ontology", result["missing_required"])
        self.assertEqual(result["emergency_stop"]["status"], "STOPPED")
        self.assertFalse(any(x["status"] == "IMPORTABLE" for x in result["components"]))

    def test_strict_exit_code_and_json_output(self):
        with patch.object(health, "collect_status", return_value={
            "core_complete": False, "missing_required": ["brain_ontology"],
            "components": [], "emergency_stop": {"status": "UNKNOWN"},
            "ollama": {"status": "NOT_CHECKED"},
        }):
            out = StringIO()
            with contextlib.redirect_stdout(out):
                result = health.main(["--json", "--strict"])
            self.assertEqual(result, 1)
            self.assertEqual(json.loads(out.getvalue())["missing_required"], ["brain_ontology"])
        with patch.object(health, "collect_status", return_value={
            "core_complete": True, "missing_required": [], "components": [],
            "emergency_stop": {"status": "CLEAR"},
            "ollama": {"status": "NOT_CHECKED"},
        }):
            out = StringIO()
            with contextlib.redirect_stdout(out):
                result = health.main(["--strict"])
            self.assertEqual(result, 0)

    def test_non_loopback_ollama_is_rejected_without_network(self):
        with patch.object(health, "HTTPConnection", side_effect=AssertionError("network used")):
            for url in (
                "https://127.0.0.1:11434",
                "http://ollama.example.com:11434",
                "http://127.0.0.1:11434/redirect",
                "http://user:pass@localhost:11434",
                "http://localhost:11434/?x=1",
            ):
                self.assertEqual(health._ollama_check(url)["status"], "REJECTED")

    def test_opt_in_ollama_returns_grounded_response_count(self):
        class FakeResponse:
            status = 200

            def read(self, size):
                return b'{"models": [{"name": "local"}, {"name": "other"}]}'

        class FakeConnection:
            def __init__(self, *args, **kwargs):
                self.requested = None
            def request(self, method, path, headers=None):
                self.requested = (method, path)
            def getresponse(self):
                return FakeResponse()
            def close(self):
                pass

        connection = FakeConnection()
        with patch.object(health, "HTTPConnection", return_value=connection) as connect:
            result = health._ollama_check("http://127.0.0.1:11434")
            self.assertEqual(result, {"status": "REACHABLE", "model_count": 2})
            self.assertEqual(connection.requested, ("GET", "/api/tags"))
            self.assertEqual(connect.call_args.args[:2], ("127.0.0.1", 11434))
        with patch.object(health, "HTTPConnection", side_effect=OSError("no server")):
            self.assertEqual(health._ollama_check("http://localhost:11434")["status"], "OFFLINE")

    def test_malformed_ollama_endpoint_rejected(self):
        with patch.object(health, "HTTPConnection", side_effect=AssertionError("network used")):
            self.assertEqual(health._ollama_check("http://[bad")["status"], "REJECTED")
            self.assertEqual(health._ollama_check("http://localhost:invalid")["status"], "REJECTED")

    def test_ollama_redirect_is_not_followed(self):
        class RedirectResponse:
            status = 302

            def read(self, size):
                return b""
        class FakeConnection:
            def request(self, *args, **kwargs):
                pass
            def getresponse(self):
                return RedirectResponse()
            def close(self):
                pass
        with patch.object(health, "HTTPConnection", return_value=FakeConnection()):
            self.assertEqual(health._ollama_check("http://127.0.0.1:11434")["status"], "INVALID_RESPONSE")

    def test_console_sanitizes_model_status_and_only_adds_optional_probe_on_request(self):
        report = {
            "components": [
                {"component": "brain", "status": "IMPORTABLE", "required": True},
            ],
            "core_complete": True,
            "emergency_stop": {"status": "CLEAR"},
            "ollama": {"status": "NOT_CHECKED"},
        }
        rendered = health.format_terminal(report)
        self.assertIn("CORE COMPONENTS  COMPLETE", rendered)
        self.assertIn("OLLAMA           NOT_CHECKED", rendered)
        self.assertIn("IMPORTABLE IS NOT PROOF", rendered)


if __name__ == "__main__":
    unittest.main()
