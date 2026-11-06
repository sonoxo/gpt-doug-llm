"""End-to-end offline framework health and SKULL 3D projection integration."""
from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from gpt_brain import framework_health as health


class SkullFrameworkHealthTests(unittest.TestCase):
    def test_actual_3d_projection_passes_without_any_inference(self):
        with patch("skull_llm.runtime.SkullEngine", side_effect=AssertionError("model called")):
            result = health._skull_projection_check()
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["views_checked"], 2)
        self.assertEqual(result["model_calls"], 0)
        self.assertEqual(result["network_calls"], 0)
        self.assertEqual(result["cl1"], "SIMULATED")

    def test_broken_projector_is_explicitly_failed(self):
        with patch("skull_llm.live_skull.render_frame", return_value="all the same"):
            result = health._skull_projection_check()
        self.assertEqual(result["status"], "FAILED")

    def test_default_health_skips_graphics_and_network(self):
        with patch.object(health, "_skull_projection_check", side_effect=AssertionError("graphics called")):
            with patch.object(health, "_ollama_check", side_effect=AssertionError("network called")):
                output = health.collect_status()
        self.assertEqual(output["skull_projection"]["status"], "NOT_CHECKED")
        self.assertEqual(output["ollama"]["status"], "NOT_CHECKED")

    def test_integrated_health_cli_json_and_success(self):
        result = io.StringIO()
        with patch.object(health, "_ollama_check", side_effect=AssertionError("network called")):
            with contextlib.redirect_stdout(result):
                code = health.main(["--json", "--verify-skull", "--strict"])
        self.assertEqual(code, 0)
        output = json.loads(result.getvalue())
        self.assertTrue(output["core_complete"])
        self.assertEqual(output["skull_projection"]["status"], "PASS")
        self.assertEqual(output["ollama"]["status"], "NOT_CHECKED")

    def test_strict_reports_failure_if_graphics_broken(self):
        with patch.object(health, "_skull_projection_check", return_value={"status": "FAILED"}):
            with contextlib.redirect_stdout(io.StringIO()):
                code = health.main(["--strict", "--verify-skull"])
        self.assertEqual(code, 1)


if __name__ == "__main__":
    unittest.main()
