"""Terminal-first 3D SKULL-LLM regressions; no Ollama or CL1 hardware needed."""
from __future__ import annotations

import contextlib
import io
import json
import unittest
from unittest.mock import patch

from skull_llm.live_skull import (
    console_frame,
    live,
    main,
    render_frame,
    skull_cloud,
)


class TerminalSkullTests(unittest.TestCase):
    def test_model_is_real_three_dimensional_point_cloud(self):
        cloud = skull_cloud()
        self.assertGreater(len(cloud), 8000)
        self.assertTrue(any(abs(p.z) > 0.3 for p in cloud))
        self.assertTrue(any(abs(p.x) > 0.4 for p in cloud))
        self.assertTrue(any(p.layer == "sim-neuron" for p in cloud))
        self.assertTrue(all(-2 < p.y < 2 for p in cloud))

    def test_rotation_reprojects_depth(self):
        front = render_frame(0.0, 0.0, columns=68, rows=30, fusion=False)
        angle = render_frame(0.65, 0.0, columns=68, rows=30, fusion=False)
        self.assertNotEqual(front, angle)
        self.assertEqual(len(front.splitlines()), 30)
        self.assertGreater(len(set(front) - {" ", "\n"}), 3)
        self.assertFalse(any(ord(c) > 127 for c in front))

    def test_neural_pulse_is_optional_and_changes_over_time(self):
        bone = render_frame(0.0, 0.0, columns=80, rows=34, fusion=False)
        neural = render_frame(0.0, 0.0, columns=80, rows=34, tick=1, fusion=True)
        self.assertNotEqual(bone, neural)

    def test_input_dimensions_are_bounded(self):
        for values in ((30, 30), (68, 10), (200, 30)):
            with self.assertRaises(ValueError):
                render_frame(columns=values[0], rows=values[1])
        with self.assertRaises(ValueError):
            live(fps=0.0, status={})
        with self.assertRaises(ValueError):
            live(frames=9999999, status={})

    def test_console_shows_simulation_not_hardware_claims(self):
        fake = {
            "inference_ready": False,
            "emergency_stop": True,
            "ollama_model": "test\x1b[2Jmodel",
        }
        frame = console_frame(status=fake, columns=80, lines=40)
        self.assertIn("BIOCHIP-CL1 // SKULL-GPT-SKULL", frame)
        self.assertIn("CL1: SIMULATED", frame)
        self.assertIn("INFERENCE: STOPPED", frame)
        self.assertIn("NO NEURONAL HARDWARE TELEMETRY", frame)
        self.assertNotIn("\x1b", frame)
        self.assertTrue(all(len(line) == 80 for line in frame.splitlines()))

    def test_once_runs_offline_noninteractive_and_exits(self):
        out = io.StringIO()
        result = live(
            once=True,
            fps=20,
            output=out,
            input_stream=io.StringIO(),
            status={"inference_ready": False, "ollama_model": "not installed"},
        )
        self.assertEqual(result, 0)
        self.assertIn("INFERENCE: OFFLINE", out.getvalue())
        self.assertNotIn("\x1b", out.getvalue())

    def test_two_frames_complete_in_noninteractive_mode(self):
        out = io.StringIO()
        result = live(
            frames=2, fps=24, output=out, input_stream=io.StringIO(),
            status={"inference_ready": True, "ollama_model": "test"},
        )
        self.assertEqual(result, 0)
        self.assertEqual(out.getvalue().count("BIOCHIP-CL1 // SKULL-GPT-SKULL"), 2)

    def test_cli_status_and_ask_are_separated_from_simulation(self):
        fake = {
            "inference_ready": False, "emergency_stop": False,
            "cl1_hardware": "NOT CONNECTED",
            "cl1_visualization": "SIMULATED / NO HARDWARE DATA",
        }
        output = io.StringIO()
        with patch("skull_llm.live_skull.status_snapshot", return_value=fake):
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["status"]), 0)
        self.assertEqual(json.loads(output.getvalue())["cl1_hardware"], "NOT CONNECTED")
        output = io.StringIO()
        with patch("skull_llm.live_skull.ask_local", return_value="local result") as fn:
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(["ask", "build", "the", "graph"]), 0)
            fn.assert_called_once_with("build the graph", depth=2, remember=False)
        self.assertEqual(output.getvalue().strip(), "local result")


if __name__ == "__main__":
    unittest.main()
