"""Measured CPU optimization checks for CL1 software skeleton 3D renderer.

No timing thresholds, GPUs, CL1 hardware, external assets or network required.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "cl1_body_perf", ROOT / "scripts" / "cl1_body_terminal.py",
)
cl1 = importlib.util.module_from_spec(spec)
# Avoid global module registration side effects in tests.
import sys
sys.modules[spec.name] = cl1
spec.loader.exec_module(cl1)


class CL1PerformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original_points = cl1.geometry("normal")

    def test_auto_raster_caps_work_per_frame_without_changing_source(self):
        c = cl1.BodyCanvas(self.original_points, width=90, height=42)
        samples = c._render_samples()
        self.assertLessEqual(len(samples), 4 * c.width * c.height)
        self.assertGreater(len(samples), 3000)
        self.assertEqual(len(c.points), len(self.original_points))
        self.assertEqual(c.tint, "BONE")
        self.assertEqual(c.mode, "SKELETON")
        self.assertTrue(all(p[3] in (cl1.BONE, cl1.BIOCHIP) for p in samples))

    def test_cached_samples_reused_until_mode_or_view_changes(self):
        c = cl1.BodyCanvas(self.original_points, width=100, height=48)
        first = c._render_samples()
        self.assertIs(first, c._render_samples())
        c.yaw = 1.0
        self.assertIs(first, c._render_samples())
        c.view = "HEAD"
        head = c._render_samples()
        self.assertIsNot(first, head)
        self.assertTrue(all(p[1] >= 1.45 for p in head))
        c.view = "FULL"
        c.mode = "NEURAL"
        neural = c._render_samples()
        self.assertIsNot(first, neural)
        self.assertTrue(any(p[3] == cl1.NEURAL for p in neural))

    def test_full_quality_retains_original_bone_points(self):
        c = cl1.BodyCanvas(self.original_points, width=80, height=40)
        c.render_quality = "full"
        points = c._render_samples()
        all_bones = [p for p in self.original_points if p[3] in (cl1.BONE, cl1.BIOCHIP)]
        self.assertEqual(len(points), len(all_bones))
        self.assertEqual(points[::20], tuple(all_bones)[::20])

    def test_auto_and_full_are_both_valid_binary_3d(self):
        c = cl1.BodyCanvas(self.original_points, width=90, height=42)
        auto = c.render(color=False)
        self.assertTrue(set(auto).issubset(set("01 \n")))
        self.assertGreater(auto.count("0") + auto.count("1"), 200)
        self.assertEqual(len(auto.splitlines()), 42)
        c.yaw = 0.85
        self.assertNotEqual(auto, c.render(color=False))
        c.render_quality = "full"
        full = c.render(color=False)
        self.assertTrue(set(full).issubset(set("01 \n")))
        self.assertEqual(len(full.splitlines()), 42)

    def test_measured_benchmark_is_bounded_truthful_and_offline(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cl1.run([
                "--benchmark", "3", "--width", "90", "--height", "42",
                "--quality", "auto", "--no-color",
            ]), 0)
        data = json.loads(output.getvalue())
        self.assertEqual(data["frames_measured"], 3)
        self.assertEqual(data["quality"], "auto")
        self.assertIn("CPU z-buffer", data["renderer"])
        self.assertLess(data["projected_points_per_frame"], data["source_points"])
        self.assertLessEqual(data["projected_points_per_frame"], 4 * 90 * 42)
        self.assertGreater(data["mean_ms_per_frame"], 0)
        self.assertGreater(data["measured_fps"], 0)
        self.assertTrue(data["simulation_only"])

    def test_original_mechanical_ontology_is_unchanged(self):
        graph = cl1.mech_ontology()
        self.assertEqual(graph["entity_count"], 19)
        self.assertFalse(graph["hardware_connected"])
        self.assertEqual(len(graph["relations"]), 18)
        evaluation = cl1.evaluate_joint("left_forearm", 65, 15)
        self.assertFalse(evaluation["hardware_command_sent"])

    def test_light_geometry_and_auto_fps_are_independent(self):
        c = cl1.BodyCanvas(cl1.geometry("light"), width=90, height=42)
        self.assertLess(len(c.points), len(self.original_points))
        self.assertLessEqual(len(c._render_samples()), 4 * 90 * 42)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(cl1.run([
                "--once", "--no-color", "--width", "90", "--height", "42",
                "--detail", "light", "--quality", "auto", "--no-spin",
            ]), 0)
        self.assertIn("SKELETON | 01 | BONE", output.getvalue())

    def test_invalid_quality_and_benchmark_inputs_are_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()):
            for args in (["--quality", "bad"], ["--benchmark", "13"],
                         ["--benchmark", "-1"]):
                with self.assertRaises(SystemExit):
                    cl1.run(args)


if __name__ == "__main__":
    unittest.main()
