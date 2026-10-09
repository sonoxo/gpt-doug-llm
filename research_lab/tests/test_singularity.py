"""Tests for exact-arithmetic scalar polynomial ODE certificates."""

import copy
import json
import subprocess
import sys
import unittest
from fractions import Fraction
from pathlib import Path

from research_lab import singularity as s

ROOT = Path(__file__).resolve().parents[2]


class SingularityTests(unittest.TestCase):
    def test_rationals_exact(self):
        self.assertEqual(s.rational("0.125"), Fraction(1, 8))
        self.assertEqual(s.rational("2/3"), Fraction(2, 3))
        with self.assertRaises(ValueError):
            s.rational(0.1)

    def test_reject_bool(self):
        with self.assertRaises(ValueError):
            s.rational(True)

    def test_horner(self):
        self.assertEqual(s.evaluate([2, -3, 1], 4), 6)

    def test_translate(self):
        self.assertEqual(s.translate([2, -3, 1], 4), (6, 5, 1))

    def test_translate_identity(self):
        for coeffs, origin in [([2, -3, 1], 4), ([1, 0, 0, "1/2"], "-3/2")]:
            for shift in [0, 1, "2/3", "7/5"]:
                self.assertEqual(s.evaluate(s.translate(coeffs, origin), shift),
                                 s.evaluate(coeffs, s.rational(origin) + s.rational(shift)))

    def test_riccati_exact(self):
        cert = s.certify_blowup([0, 0, 1], 1, 2, 1)
        self.assertEqual(cert["blowup_time_upper_bound"], "1")
        self.assertTrue(s.verify(cert))

    def test_nontrivial_blowup(self):
        cert = s.certify_blowup([2, -3, 1], 4, 2, "1/4")
        self.assertEqual(cert["shifted_gap_coefficients"], ["2", "3", "3/4"])
        self.assertEqual(cert["blowup_time_upper_bound"], "1")
        self.assertTrue(s.verify(cert))

    def test_higher_power(self):
        cert = s.certify_blowup([0, 1, -2, 1], 2, 3, "1/4")
        self.assertEqual(cert["blowup_time_upper_bound"], "1/2")
        self.assertTrue(s.verify(cert))

    def test_failed_comparison(self):
        self.assertIsNone(s.certify_blowup([2, -3, 1], 1, 2, "1/4"))
        self.assertIsNone(s.certify_blowup([0, 0, -1], 1, 2, 1))

    def test_invalid_inputs(self):
        for args in [([0, 0, 1], -1, 2, 1), ([0, 0, 1], 1, 1, 1),
                     ([0, 0, 1], 1, 2, 0), ([0, 0, 1], 1, True, 1)]:
            with self.assertRaises(ValueError):
                s.certify_blowup(*args)

    def test_blowup_tampering(self):
        cert = s.certify_blowup([2, -3, 1], 4, 2, "1/4")
        for field, value in [
            ("blowup_time_upper_bound", "1/2"),
            ("shifted_gap_coefficients", ["0", "0", "0"]),
            ("coefficients_ascending", ["2", "-2", "1"]),
        ]:
            modified = copy.deepcopy(cert)
            modified[field] = value
            self.assertFalse(s.verify(modified))

    def test_trapping(self):
        cert = s.certify_bounded([0, 1, 0, -1], "1/2", -1, 1)
        self.assertEqual(cert["vector_field_at_lower"], "0")
        self.assertEqual(cert["vector_field_at_upper"], "0")
        self.assertTrue(s.verify(cert))

    def test_inward_boundaries(self):
        cert = s.certify_bounded([0, 1, 0, -1], 0, -2, 2)
        self.assertEqual(cert["vector_field_at_lower"], "6")
        self.assertEqual(cert["vector_field_at_upper"], "-6")
        self.assertTrue(s.verify(cert))

    def test_bounded_negative_cases(self):
        self.assertIsNone(s.certify_bounded([0, 0, 1], 1, -2, 2))
        self.assertIsNone(s.certify_bounded([0, 1, 0, -1], 5, -1, 1))
        with self.assertRaises(ValueError):
            s.certify_bounded([0], 0, 1, -1)

    def test_bounded_tamper(self):
        cert = s.certify_bounded([0, 1, 0, -1], 0, -2, 2)
        self.assertFalse(s.verify(dict(cert, vector_field_at_upper="-7")))

    def test_scan_blowup(self):
        cert = s.scan([2, -3, 1], 4)
        self.assertEqual(cert["status"], "BLOWUP_CERTIFIED")
        self.assertTrue(s.verify(cert))

    def test_scan_bounded(self):
        cert = s.scan([0, 1, 0, -1], 0)
        self.assertEqual(cert["status"], "GLOBALLY_BOUNDED_CERTIFIED")
        self.assertTrue(s.verify(cert))

    def test_inconclusive(self):
        cert = s.scan([0, 0, -1], 1)
        self.assertEqual(cert["status"], "INCONCLUSIVE")
        self.assertFalse(s.verify(cert))

    def test_cli_demo(self):
        cp = subprocess.run([sys.executable, "-m", "research_lab.singularity", "demo"],
                            cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        results = json.loads(cp.stdout)
        self.assertTrue(s.verify(results["quadratic"]))
        self.assertTrue(s.verify(results["restoring"]))

    def test_cli_blowup(self):
        cp = subprocess.run(
            [sys.executable, "-m", "research_lab.singularity", "blowup",
             "--coeffs", "2,-3,1", "--x0", "4", "--p", "2", "--a", "1/4"],
            cwd=str(ROOT), capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertTrue(s.verify(json.loads(cp.stdout)))

    def test_decimal_string_exact(self):
        self.assertEqual(s.rational("0.2"), Fraction(1, 5))

    def test_invalid_certificate(self):
        self.assertFalse(s.verify({"status": "BLOWUP_CERTIFIED"}))


if __name__ == "__main__":
    unittest.main()
