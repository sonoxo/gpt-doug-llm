"""Regression checks for Bio-Gpt console startup and interactive commands."""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAUNCH = ROOT / "run-Bio-Gpt.command"


class TerminalLauncherTests(unittest.TestCase):
    def invoke(self, argv, input_text=None, cwd=None):
        return subprocess.run(argv, cwd=cwd or str(ROOT), input=input_text,
                              text=True, capture_output=True, timeout=30)

    def test_python_one_shot_dashboard(self):
        run = self.invoke([sys.executable, "-m", "research_lab.bio_gpt_terminal", "--once"])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("CERTIFIED_BIO_GPT_SIX_TO_INFINITY", run.stdout)
        self.assertIn("FIVE CORE OPERATORS", run.stdout)
        self.assertIn("GPT-Doug-Redpanda", run.stdout)

    def test_clickable_script_launch_from_elsewhere(self):
        with tempfile.TemporaryDirectory() as d:
            run = self.invoke(["bash", str(LAUNCH), "--once"], cwd=d)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("BIO-GPT", run.stdout)

    def test_interactive_menu_and_certificate_replay(self):
        run = self.invoke(["bash", str(LAUNCH)], input_text="2\n3\n4\nq\n")
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("FIVE CORE OPERATORS", run.stdout)
        self.assertIn("FINITE LAYERS", run.stdout)
        self.assertIn("CERTIFICATE REPLAY: VERIFIED", run.stdout)
        self.assertIn("Exiting Bio-Gpt", run.stdout)

    def test_q_exits_cleanly(self):
        run = self.invoke(["bash", str(LAUNCH)], input_text="q\n")
        self.assertEqual(run.returncode, 0)
        self.assertNotIn("Traceback", run.stdout + run.stderr)

    def test_eof_exits_cleanly(self):
        run = self.invoke(["bash", str(LAUNCH)], input_text="")
        self.assertEqual(run.returncode, 0)
        self.assertIn("Input closed", run.stdout)

    def test_bad_menu_input_recovers(self):
        run = self.invoke(["bash", str(LAUNCH)], input_text="invalid\nq\n")
        self.assertEqual(run.returncode, 0)
        self.assertIn("Unknown command", run.stdout)

    def test_help(self):
        run = self.invoke([sys.executable, "-m", "research_lab.bio_gpt_terminal", "--help"])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertIn("--once", run.stdout)

    def test_invalid_argument_fails_closed(self):
        run = self.invoke([sys.executable, "-m", "research_lab.bio_gpt_terminal", "--connect-all"])
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("unrecognized arguments", run.stderr)


if __name__ == "__main__":
    unittest.main()
