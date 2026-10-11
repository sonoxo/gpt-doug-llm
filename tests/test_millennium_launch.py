"""Standalone launcher checks, including unrelated working directory."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class LauncherTests(unittest.TestCase):
    def test_external_working_directory(self):
        with tempfile.TemporaryDirectory() as other:
            result=subprocess.run(['bash',str(ROOT/'run-Millennium-Forge.command'),'status'],
                                  cwd=other, text=True,capture_output=True,timeout=12)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('navier_stokes',result.stdout)
    def test_exact_report_default_from_outside(self):
        with tempfile.TemporaryDirectory() as other:
            result=subprocess.run(['bash',str(ROOT/'run-Millennium-Forge.command')],
                                  cwd=other,text=True,capture_output=True,timeout=16)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('"evidence_sha256"',result.stdout)
    def test_unsupported_command_fails_closed(self):
        result=subprocess.run(['bash',str(ROOT/'run-Millennium-Forge.command'),'unsupported-action'],
                              cwd=ROOT,text=True,capture_output=True,timeout=8)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('invalid choice',result.stderr)
