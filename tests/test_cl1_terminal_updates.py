"""CL1 Terminal low-bandwidth rendering, FPS honesty and skeletal fidelity."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import math
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("cl1_terminal_io",ROOT/"scripts"/"cl1_body_terminal.py")
cl1=importlib.util.module_from_spec(spec)
sys.modules[spec.name]=cl1
spec.loader.exec_module(cl1)


class TerminalDiffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.points=cl1.geometry("normal")

    def test_initial_full_frame_and_cache(self):
        text="HEADER\n"+(" "*24)+"01"+"\nFOOTER"
        command,previous=cl1.build_terminal_delta(None,text)
        self.assertTrue(command.startswith("\x1b[H"))
        self.assertIn(text,command)
        self.assertEqual(previous,tuple(text.splitlines()))

    def test_identical_frame_sends_zero_bytes(self):
        frame="H\n"+" "*20+"101001"+" "*40+"\nF"
        previous=tuple(frame.splitlines())
        out,current=cl1.build_terminal_delta(previous,frame)
        self.assertEqual(out,"")
        self.assertIsInstance(current,tuple)
        self.assertEqual(current,previous)

    def test_changed_skeleton_row_skips_blank_left_margin(self):
        old="HEAD\n"+" "*70+"0110"+" "*25+"\nFOOT"
        new="HEAD\n"+" "*70+"1010"+" "*25+"\nFOOT"
        out,current=cl1.build_terminal_delta(tuple(old.splitlines()),new)
        self.assertIn("\x1b[2;1H\x1b[2K\x1b[71G1010",out)
        self.assertLess(len(out),len(new))
        self.assertEqual(current[1],new.splitlines()[1])

    def test_removed_row_is_cleared(self):
        before=tuple(("HEADER","BODY","OBSOLETE"))
        result,new=cl1.build_terminal_delta(before,"HEADER\nBODY")
        self.assertIn("\x1b[3;1H\x1b[J",result)
        self.assertEqual(new,("HEADER","BODY"))

    def test_escaped_color_ends_reset_and_preserves_valid_ansi(self):
        original="HDR\n"+(" "*30)+"0000\x1b[0m\nFOOT"
        changed="HDR\n"+(" "*30)+"1111\x1b[0m\nFOOT"
        update,_=cl1.build_terminal_delta(tuple(original.splitlines()),changed)
        self.assertIn("\x1b[31G1111\x1b[0m",update)

    def test_rotation_is_time_based_and_bounded(self):
        self.assertAlmostEqual(cl1.rotation_delta(1/9),.032,places=5)
        self.assertAlmostEqual(cl1.rotation_delta(.5),.144,places=5)
        self.assertAlmostEqual(cl1.rotation_delta(100),.144,places=5)
        self.assertEqual(cl1.rotation_delta(-1),0)

    def test_fast_color_preserves_3d_skeleton_and_reduces_escape_bytes(self):
        c=cl1.BodyCanvas(self.points,120,54,mode="SKELETON")
        c.color_detail="fast"
        fast=c.render(color=True)
        c.color_detail="detailed"
        detailed=c.render(color=True)
        self.assertIn("\x1b[38;2;",fast)
        self.assertIn("\x1b[38;2;",detailed)
        self.assertLess(len(fast.encode()),len(detailed.encode()))
        import re
        plain=re.compile(r"\x1b\[[0-9;]*m")
        self.assertEqual(plain.sub("",fast),plain.sub("",detailed))
        self.assertTrue(set(plain.sub("",fast)).issubset(set("01 \n")))

    def test_benchmark_explicitly_discloses_unmeasured_display_latency(self):
        out=io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cl1.run(["--benchmark","3","--width","90",
                                      "--height","42","--quality","auto"]),0)
        report=json.loads(out.getvalue())
        self.assertEqual(report["frames_measured"],3)
        self.assertTrue(report["fps_is_projection_only"])
        self.assertFalse(report["terminal_io_measured"])
        self.assertGreater(report["colored_format_mean_ms"],0)
        self.assertGreater(report["full_colored_frame_bytes"],0)
        self.assertGreaterEqual(report["full_colored_frame_bytes"],
                                report["changed_rows_frame_bytes"])
        self.assertTrue(report["simulation_only"])

    def test_mechanical_inspector_and_binary_mode_remain_intact(self):
        c=cl1.BodyCanvas(self.points,90,42)
        self.assertEqual(c.mode,"SKELETON")
        self.assertEqual(c.tint,"BONE")
        self.assertEqual(cl1.mech_ontology()["entity_count"],19)
        self.assertIn("ONTOLOGY 01/19",c.dashboard(False))
        self.assertTrue(set(c.render(False))<=set("01 \n"))
        self.assertFalse(cl1.evaluate_joint("left_forearm",65,15)["hardware_command_sent"])


if __name__=="__main__":
    unittest.main()
