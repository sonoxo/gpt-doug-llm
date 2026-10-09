"""Exact phase-line and rate-search randomized validation."""

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from research_lab import singularity_quadratic as q

ROOT = Path(__file__).resolve().parents[2]


class QuadraticDichotomyTests(unittest.TestCase):
    def test_sos_blowup(self):
        cert = q.decide([4, -4, 2], 1)
        self.assertEqual(cert["status"], "BLOWUP_CERTIFIED_SOS")
        self.assertEqual(cert["comparison_rate"], "1")
        self.assertEqual(cert["blowup_time_upper_bound"], "1")
        self.assertTrue(q.verify(cert))

    def test_nontrivial_optimum(self):
        # P(x)=2x^2-4x+4, inf P(x)/x^2=1 attained at x=2.
        self.assertEqual(q.optimal_quadratic_rate([4, -4, 2], 1), 1)

    def test_rate_at_initial(self):
        # P=x^2-1/2*x, x0=1, ratio increasing to 1.
        self.assertEqual(q.optimal_quadratic_rate([0, "-1/2", 1], 1), Fraction(1, 2))

    def test_rate_at_infinity(self):
        # P=x^2+3*x+3, ratio decreasing to 1.
        self.assertEqual(q.optimal_quadratic_rate([3, 3, 1], 1), 1)

    def test_equilibrium(self):
        cert = q.decide([2, -3, 1], 1)
        self.assertEqual(cert["status"], "EQUILIBRIUM_CERTIFIED")
        self.assertTrue(q.verify(cert))

    def test_global_from_negative_rhs(self):
        cert = q.decide([2, -3, 1], "3/2")
        self.assertEqual(cert["status"], "GLOBALLY_BOUNDED_CERTIFIED")
        self.assertTrue(q.verify(cert))

    def test_global_from_attracting_root(self):
        cert = q.decide([6, -5, 1], 1)
        self.assertEqual(cert["status"], "GLOBALLY_BOUNDED_CERTIFIED")
        self.assertTrue(q.verify(cert))

    def test_global_from_double_root(self):
        # P=(x-2)^2, x0=1; solution increases toward 2 asymptotically.
        cert = q.decide([4, -4, 1], 1)
        self.assertEqual(cert["status"], "GLOBALLY_BOUNDED_CERTIFIED")
        self.assertTrue(q.verify(cert))

    def test_already_above_highest_root(self):
        cert = q.decide([2, -3, 1], 4)
        self.assertEqual(cert["status"], "BLOWUP_CERTIFIED_SOS")
        self.assertTrue(q.verify(cert))

    def test_discriminant_negative(self):
        cert = q.decide([100, -20, 2], "1/8")
        self.assertEqual(cert["status"], "BLOWUP_CERTIFIED_SOS")
        self.assertTrue(q.verify(cert))

    def test_nonapplicable(self):
        for poly, x0 in [([0, 0, -1], 1), ([1, 1], 1), ([0, 0, 1], 0),
                         ([0, 0, 1], -1)]:
            with self.assertRaises(ValueError):
                q.decide(poly, x0)

    def test_tampering_rejected(self):
        for poly, x0 in [([4, -4, 2], 1), ([4, -4, 1], 1), ([2, -3, 1], 1)]:
            cert = q.decide(poly, x0)
            fake = dict(cert, scope="fluid PDE breakthrough")
            self.assertFalse(q.verify(fake))

    def test_rate_is_exact_global_infimum(self):
        rng = random.Random(8787)
        for _ in range(1000):
            poly = [Fraction(rng.randint(-8, 8), rng.randint(1, 3)),
                    Fraction(rng.randint(-8, 8), rng.randint(1, 3)),
                    Fraction(rng.randint(1, 8), rng.randint(1, 3))]
            x0 = Fraction(rng.randint(1, 8), rng.randint(1, 4))
            r = q.optimal_quadratic_rate(poly, x0)
            for n in range(1, 10):
                x = x0 + Fraction(n * n, 7)
                self.assertLessEqual(r, (poly[2]*x*x + poly[1]*x + poly[0]) / (x*x))

    def test_random_dichotomy_against_phase_line(self):
        rng = random.Random(987654321)
        counts = {"BLOWUP_CERTIFIED_SOS": 0, "GLOBALLY_BOUNDED_CERTIFIED": 0,
                  "EQUILIBRIUM_CERTIFIED": 0}
        for _ in range(1200):
            c = Fraction(rng.randint(-12, 12), rng.randint(1, 5))
            b = Fraction(rng.randint(-12, 12), rng.randint(1, 5))
            a = Fraction(rng.randint(1, 12), rng.randint(1, 5))
            x0 = Fraction(rng.randint(1, 12), rng.randint(1, 6))
            p0 = a*x0*x0 + b*x0 + c
            derivative = 2*a*x0 + b
            discriminant = b*b - 4*a*c
            # Independent phase-line classification using discriminant & slope.
            if p0 == 0:
                expected = "EQUILIBRIUM_CERTIFIED"
            elif p0 > 0 and (discriminant < 0 or derivative >= 0):
                expected = "BLOWUP_CERTIFIED_SOS"
            else:
                expected = "GLOBALLY_BOUNDED_CERTIFIED"
            cert = q.decide([c, b, a], x0)
            self.assertEqual(cert["status"], expected, (c, b, a, x0))
            self.assertTrue(q.verify(cert))
            counts[expected] += 1
        self.assertGreater(counts["BLOWUP_CERTIFIED_SOS"], 200)
        self.assertGreater(counts["GLOBALLY_BOUNDED_CERTIFIED"], 200)

    def test_cli_round_trip(self):
        cp = subprocess.run([sys.executable, "-m", "research_lab.singularity_quadratic",
                             "decide", "--coeffs", "4,-4,2", "--x0", "1"],
                            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        cert = json.loads(cp.stdout)
        self.assertTrue(q.verify(cert))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cert.json"
            path.write_text(json.dumps(cert), encoding="utf-8")
            check = subprocess.run([sys.executable, "-m", "research_lab.singularity_quadratic",
                                    "verify", str(path)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(check.returncode, 0)
            self.assertEqual(json.loads(check.stdout)["status"], "VERIFIED")


if __name__ == "__main__":
    unittest.main()
