"""SKULL V2 terminal upgrade tests: no hardware, browser or live LLM needed."""
from __future__ import annotations

from io import StringIO
import contextlib
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from skull_llm.cockpit_v2 import (
    compose_screen,
    infer,
    live,
    main,
    save_snapshot,
)
from skull_llm.live_skull import render_frame


_STATUS = {
    "inference_ready": True,
    "emergency_stop": False,
    "ollama_model": "qwen2.5-coder:7b",
    "cl1_hardware": "NOT CONNECTED",
}


class CockpitV2Tests(unittest.TestCase):
    def test_3d_zoom_reprojects_real_point_cloud(self):
        near = render_frame(columns=84, rows=36, yaw=0.52, zoom=1.75)
        far = render_frame(columns=84, rows=36, yaw=0.52, zoom=0.70)
        self.assertNotEqual(near, far)
        for invalid in (0, 0.5, 2.5, float("nan")):
            with self.assertRaises(ValueError):
                render_frame(columns=84, rows=36, zoom=invalid)

    def test_widescreen_display_has_observed_hud(self):
        screen = compose_screen(width=120, height=36, status=_STATUS, tick=7)
        self.assertIn("[ SYSTEM / LOCAL ]", screen)
        self.assertIn("INFERENCE     READY", screen)
        self.assertIn("qwen2.5-coder:7b", screen)
        self.assertIn("CL1 BIOCHIP   SIMULATED ONLY", screen)
        self.assertIn("CL1 HARDWARE: NOT CONNECTED", screen)
        self.assertIn("YAW", screen)
        self.assertTrue(all(len(line) == 120 for line in screen.splitlines()))

    def test_narrow_screen_is_still_functional(self):
        screen = compose_screen(
            width=64, height=28, status={"emergency_stop": True},
            help_open=True,
        )
        self.assertIn("INFERENCE: STOPPED", screen)
        self.assertIn("ZOOM", screen)
        self.assertIn("CL1: SIMULATED", screen)
        self.assertTrue(all(len(line) == 64 for line in screen.splitlines()))

    def test_status_output_sanitizes_escape_sequences(self):
        screen = compose_screen(
            width=120, height=36,
            status={"inference_ready": False, "ollama_model": "\x1b[31mBAD\x1b[0m"},
        )
        self.assertNotIn("\x1b", screen)
        self.assertIn("INFERENCE: OFFLINE", screen)

    def test_rendered_frame_changes_with_angle(self):
        a = compose_screen(width=104, height=32, status=_STATUS, yaw=0.0)
        b = compose_screen(width=104, height=32, status=_STATUS, yaw=1.35)
        self.assertNotEqual(a, b)

    def test_snapshot_is_create_only(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "my-skull.txt"
            first = save_snapshot(str(path), "3D-ASCII")
            self.assertEqual(first.read_text(), "3D-ASCII\n")
            with self.assertRaises(FileExistsError):
                save_snapshot(str(path), "OVERWRITE")
            self.assertEqual(path.read_text(), "3D-ASCII\n")

    def test_offline_one_frame_writes_no_terminal_escape(self):
        output = StringIO()
        ret = live(
            once=True, output=output, input_stream=StringIO(),
            status={"inference_ready": False, "ollama_model": "missing"},
            viewport=(108, 36),
        )
        self.assertEqual(ret, 0)
        self.assertIn("3D LIVE ASCII", output.getvalue())
        self.assertIn("INFERENCE: OFFLINE", output.getvalue())
        self.assertNotIn("\x1b", output.getvalue())

    def test_bounded_two_frames(self):
        output = StringIO()
        ret = live(
            frames=2, fps=24, output=output, input_stream=StringIO(),
            status=_STATUS, viewport=(100, 36),
        )
        self.assertEqual(ret, 0)
        self.assertEqual(output.getvalue().count("3D LIVE ASCII"), 2)

    def test_status_does_not_invent_hardware_telemetry(self):
        status = StringIO()
        with patch("skull_llm.cockpit_v2.status_snapshot", return_value=_STATUS):
            with contextlib.redirect_stdout(status):
                self.assertEqual(main(["status"]), 0)
        self.assertEqual(json.loads(status.getvalue())["cl1_hardware"], "NOT CONNECTED")

    def test_trace_outputs_real_progress_callback_events(self):
        def fake_infer(task, *, depth, remember, on_phase):
            self.assertEqual(task, "Make a graph")
            self.assertEqual(depth, 2)
            self.assertFalse(remember)
            on_phase("retrieve", "Ontology found")
            on_phase("draft", "Generating answer")
            return SimpleNamespace(answer="A traceable graph")
        stdout = StringIO()
        stderr = StringIO()
        with patch("skull_llm.cockpit_v2.infer", side_effect=fake_infer):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(main(["ask", "Make", "a", "graph", "--trace"]), 0)
        self.assertIn("A traceable graph", stdout.getvalue())
        self.assertIn("[retrieve] Ontology found", stderr.getvalue())
        self.assertIn("[draft] Generating answer", stderr.getvalue())

    def test_render_and_infer_validation(self):
        with self.assertRaises(ValueError):
            compose_screen(zoom=3.0)
        with self.assertRaises(ValueError):
            live(frames=-1, status=_STATUS)
        with self.assertRaises(ValueError):
            infer(" ")

    def test_script_invokes_correct_v2_inference(self):
        stub = SimpleNamespace(answer="Local only")
        out = StringIO()
        with patch("skull_llm.cockpit_v2.infer", return_value=stub) as mock:
            with contextlib.redirect_stdout(out):
                self.assertEqual(main(["ask", "test"]), 0)
            self.assertEqual(mock.call_args.kwargs["depth"], 2)
        self.assertEqual(out.getvalue().strip(), "Local only")


if __name__ == "__main__":
    unittest.main()
