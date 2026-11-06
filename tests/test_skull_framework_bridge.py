"""Integration tests: GPT-DOUG command bridge and real-metric SKULL benchmark."""
from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from gpt_brain import cli as brain_cli
from skull_llm import benchmark as skull_benchmark


class IntegratedCLITests(unittest.TestCase):
    def test_gpt_doug_skull_defaults_to_tui_without_constructing_brain(self):
        with patch.object(sys, "argv", ["gpt-doug", "skull"]):
            with patch("skull_llm.cli.main", return_value=0) as skull, patch.object(
                brain_cli, "BrainMemory", side_effect=AssertionError("eager memory")
            ):
                self.assertEqual(brain_cli.main(), 0)
        skull.assert_called_once_with(["live"])

    def test_gpt_doug_skull_forwards_bound_argv(self):
        argv = ["skull", "bench", "--iterations", "2"]
        with patch.object(sys, "argv", ["gpt-doug", *argv]):
            with patch("skull_llm.cli.main", return_value=7) as skull:
                self.assertEqual(brain_cli.main(), 7)
        skull.assert_called_once_with(["bench", "--iterations", "2"])

    def test_gpt_doug_health_dispatches_without_brain_inference(self):
        with patch.object(sys, "argv", ["gpt-doug", "health", "--json", "--strict"]):
            with patch("gpt_brain.framework_health.main", return_value=0) as health, patch.object(
                brain_cli, "BrainKernel", side_effect=AssertionError("no AI run")
            ):
                self.assertEqual(brain_cli.main(), 0)
        health.assert_called_once_with(["--json", "--strict"])


class BoundedBenchmarkTests(unittest.TestCase):
    def test_measured_latency_and_no_private_output(self):
        answer = SimpleNamespace(answer="local model answer", calls=1)
        engine = Mock()
        engine.run.return_value = answer
        factory = Mock(return_value=engine)
        timer = iter([1.0, 1.15, 3.0, 3.25, 5.0, 5.5])
        with patch.object(skull_benchmark, "require_ai_allowed") as guard:
            report = skull_benchmark.benchmark(
                prompt="private prompt",
                repetitions=3,
                model="qwen2.5-coder:7b",
                engine_factory=factory,
                clock=lambda: next(timer),
            )
        self.assertEqual(report["model_calls"], 3)
        self.assertEqual(report["response_chars"], [18, 18, 18])
        self.assertEqual(report["min_ms"], 150.0)
        self.assertEqual(report["median_ms"], 250.0)
        self.assertEqual(report["p95_ms"], 500.0)
        self.assertFalse(report["token_throughput_measured"])
        self.assertNotIn("private prompt", json.dumps(report))
        self.assertNotIn("local model answer", json.dumps(report))
        self.assertEqual(guard.call_count, 6)
        self.assertEqual(factory.call_count, 3)
        self.assertTrue(all(c.kwargs["config"].depth == 1 for c in factory.call_args_list))
        self.assertTrue(all(not c.kwargs["config"].remember for c in factory.call_args_list))

    def test_invalid_requests_do_not_execute_models(self):
        for count, prompt in [(0, "hello"), (6, "hello"), (1, ""), (1, "x" * 401)]:
            with patch.object(skull_benchmark, "SkullEngine", side_effect=AssertionError("model called")):
                with self.assertRaises(ValueError):
                    skull_benchmark.benchmark(prompt=prompt, repetitions=count)

    def test_emergency_stop_prevents_model_launch(self):
        with patch.object(skull_benchmark, "require_ai_allowed", side_effect=PermissionError("STOP")):
            factory = Mock()
            with self.assertRaises(PermissionError):
                skull_benchmark.benchmark(engine_factory=factory)
            factory.assert_not_called()

    def test_benchmark_cli_dispatches_to_bounded_metrics(self):
        payload = {"model": "local", "min_ms": 12.0, "token_throughput_measured": False}
        from skull_llm.cli import main
        stdout = io.StringIO()
        with patch("skull_llm.benchmark.benchmark", return_value=payload) as bench:
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(main(["bench", "--iterations", "2", "--model", "local"]), 0)
        self.assertEqual(json.loads(stdout.getvalue()), payload)
        self.assertEqual(bench.call_args.kwargs["repetitions"], 2)


if __name__ == "__main__":
    unittest.main()
