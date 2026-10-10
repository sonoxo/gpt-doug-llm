"""Test the Cure Swarm path through the actual Bio-Gpt terminal and launcher."""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class BioGptCureSwarmTerminalTests(unittest.TestCase):
    def test_interactive_terminal_option_five_is_synthetic(self):
        result = subprocess.run(
            [sys.executable, "-m", "research_lab.bio_gpt_terminal"],
            input="5\nq\n", cwd=ROOT, text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("BIO-GPT CURE SWARM // SYNTHETIC RESEARCH DEMO", result.stdout)
        self.assertIn("Medical review gate: REQUIRED", result.stdout)
        self.assertIn("Approved cures:      0", result.stdout)
        self.assertIn("Exiting Bio-Gpt", result.stdout)

    def test_command_line_offline_demo(self):
        result = subprocess.run(
            ["bash", str(ROOT / "scripts" / "doug-max"), "cure-swarm", "demo"],
            cwd=ROOT, text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["synthetic_demo"])
        self.assertTrue(report["agents"][3]["approval"] == "REQUIRED")

    def test_standalone_script_defaults_to_offline(self):
        result = subprocess.run(
            ["bash", str(ROOT / "run-Cure-Swarm.command")],
            cwd=ROOT, text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["origin"], "synthetic")


if __name__ == "__main__":
    unittest.main()
