"""Offline Cure Swarm interactive terminal smoke tests."""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


class CureSwarmTerminalTests(unittest.TestCase):
    def test_menu_and_provenance(self):
        p=subprocess.run(['bash',str(ROOT/'run-Cure-Swarm.command')],cwd=ROOT,
            input='2\n3\n4\nq\n',text=True,capture_output=True,timeout=20)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('RESEARCH ROLES',p.stdout)
        self.assertIn('EVIDENCE REVIEW QUEUE',p.stdout)
        self.assertIn('PROVENANCE REPLAY: VERIFIED',p.stdout)
        self.assertIn('No background workers remain',p.stdout)

    def test_noninteractive_flag(self):
        p=subprocess.run(['bash',str(ROOT/'run-Cure-Swarm.command'),'--once'],cwd=ROOT,
            text=True,capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('BIO-GPT / CURE SWARM',p.stdout)
        self.assertIn('SIMULATED EVIDENCE',p.stdout)

    def test_eof_is_clean(self):
        p=subprocess.run(['bash',str(ROOT/'run-Cure-Swarm.command')],cwd=ROOT,
            input='',text=True,capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('Input closed',p.stdout)

    def test_no_autonomous_network_input(self):
        p=subprocess.run([sys.executable,'-m','research_lab.cure_swarm_terminal','--online'],cwd=ROOT,
            text=True,capture_output=True,timeout=15)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('unrecognized arguments',p.stderr)

    def test_bad_menu_recovers(self):
        p=subprocess.run(['bash',str(ROOT/'run-Cure-Swarm.command')],cwd=ROOT,
            input='invalid\nq\n',text=True,capture_output=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertIn('Invalid selection',p.stdout)


if __name__=='__main__':
    unittest.main()
