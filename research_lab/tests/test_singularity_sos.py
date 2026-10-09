"""Independent identity checks, regression tests and property tests for SOS proofs."""

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from research_lab import singularity as old
from research_lab import singularity_sos as sos

ROOT = Path(__file__).resolve().parents[2]


class PolynomialTests(unittest.TestCase):
    def test_add_multiply_subtract(self):
        self.assertEqual(sos.plus([1, 1], [1, -1]), (2,))
        self.assertEqual(sos.times([1, -1], [1, -1]), (1, -2, 1))
        self.assertEqual(sos.minus([2, 1], [1, 3]), (1, -2))

    def test_shifted_gap(self):
        self.assertEqual(sos.shifted_gap([4, -4, 2], 1, 2, 1), (1, -2, 1))

    def test_reject_invalid_rate(self):
        with self.assertRaises(ValueError):
            sos.shifted_gap([0, 0, 1], 1, 2, 0)

    def test_reject_nonrational_float(self):
        with self.assertRaises(ValueError):
            sos.shifted_gap([0, 0, 1], 1, 2, 0.3)

    def test_reject_exponent_bool(self):
        with self.assertRaises(ValueError):
            sos.shifted_gap([0, 0, 1], 1, True, 1)


class SOSWitnessTests(unittest.TestCase):
    def test_new_quadratic_proven(self):
        poly = [4, -4, 2]  # x'=2(x-1)^2+2
        self.assertIsNone(old.certify_blowup(poly, 1, 2, 1))
        cert = sos.synthesize(poly, 1, 2, 1)
        self.assertTrue(sos.verify(cert))
        self.assertEqual(cert["blowup_time_upper_bound"], "1")
        self.assertEqual(cert["sos_terms"][0]["polynomial_ascending"], ["-1", "1"])

    def test_scan_finds_new_proof(self):
        cert = sos.scan([4, -4, 2], 1)
        self.assertTrue(sos.verify(cert))
        self.assertEqual(cert["comparison_rate"], "1")

    def test_quadratic_with_positive_residual(self):
        # Gap = z^2-2z+2 = (z-1)^2+1
        cert = sos.synthesize([5, -4, 2], 1, 2, 1)
        self.assertTrue(sos.verify(cert))
        self.assertEqual(len(cert["sos_terms"]), 2)

    def test_quadratic_with_rational_weights(self):
        # x0=1, gap(z)=3z^2-2z+1 = 3(z-1/3)^2 + 2/3
        cert = sos.synthesize([6, -8, 4], 1, 2, 1)
        self.assertTrue(sos.verify(cert))
        self.assertEqual(cert["shifted_gap_coefficients"], ["1", "-2", "3"])

    def test_quadratic_that_is_negative_rejected(self):
        # Gap=z^2-4z+1 is negative at z=2.
        self.assertIsNone(sos.synthesize([8, -8, 2], 1, 2, 1))

    def test_nonnegative_shifted_monomials(self):
        cert = sos.synthesize([2, -3, 1], 4, 2, "1/4")
        self.assertTrue(sos.verify(cert))
        self.assertEqual(len(cert["z_sos_terms"]), 1)

    def test_perfect_square_quartic(self):
        # Gap=(z^2-3z+2)^2. x0=1, P(x)=x^2+(x^2-5x+6)^2
        poly = [36, -60, 38, -10, 1]
        cert = sos.synthesize(poly, 1, 2, 1)
        self.assertTrue(sos.verify(cert))
        self.assertEqual(cert["shifted_gap_coefficients"], ["4", "-12", "13", "-6", "1"])

    def test_perfect_square_sextic(self):
        # Gap=(z^3-2z+1)^2 where z=x-1.
        gap = sos.times([1, -2, 0, 1], [1, -2, 0, 1])
        # Express P(x)=x^2+gap(x-1) exactly, by substituting z=x-1.
        from math import comb
        poly = [Fraction(0)] * 7
        for i, c in enumerate(gap):
            for k in range(i + 1):
                poly[k] += c * comb(i, k) * (-1) ** (i-k)
        poly[2] += 1
        cert = sos.synthesize(poly, 1, 2, 1)
        self.assertTrue(sos.verify(cert))
        self.assertEqual(len(cert["sos_terms"]), 1)

    def test_odd_degree_z_times_square(self):
        # Gap=z(z-1)^2, x0=1.
        # (x-1)(x-2)^2 + x^2 = x^3-4x^2+8x-4.
        cert = sos.synthesize([-4, 8, -4, 1], 1, 2, 1)
        self.assertTrue(sos.verify(cert))
        self.assertEqual(cert["sos_terms"], [])
        self.assertEqual(len(cert["z_sos_terms"]), 1)

    def test_invalid_manual_witness_rejected(self):
        term = {"weight": "1", "polynomial_ascending": ["1", "1"]}
        self.assertIsNone(sos.certify_sos([4, -4, 2], 1, 2, 1, [term], []))

    def test_manual_valid_witness(self):
        term = {"weight": "1", "polynomial_ascending": ["-1", "1"]}
        cert = sos.certify_sos([4, -4, 2], 1, 2, 1, [term], [])
        self.assertTrue(sos.verify(cert))

    def test_bad_weights(self):
        for w in [0, -1, 1.2, "inf"]:
            with self.assertRaises(ValueError):
                sos.certify_sos([4, -4, 2], 1, 2, 1,
                                [{"weight": w, "polynomial_ascending": [1]}], [])

    def test_tampered_certificate(self):
        cert = sos.synthesize([4, -4, 2], 1, 2, 1)
        cases = [
            ("comparison_rate", "2"),
            ("blowup_time_upper_bound", "1/2"),
            ("shifted_gap_coefficients", ["1", "1", "1"]),
            ("initial", "2"),
            ("scope", "proves Navier Stokes"),
        ]
        for field, value in cases:
            forged = copy.deepcopy(cert)
            forged[field] = value
            self.assertFalse(sos.verify(forged), field)
        forged = copy.deepcopy(cert)
        forged["sos_terms"][0]["weight"] = "2"
        self.assertFalse(sos.verify(forged))
        forged = copy.deepcopy(cert)
        forged["extra"] = "unexpected"
        self.assertFalse(sos.verify(forged))

    def test_noncanonical_term_fails(self):
        term = {"weight": "1", "polynomial_ascending": [1, 0]}
        cert = sos.certify_sos([4, -4, 2], 1, 2, 1, [term], [])
        self.assertIsNone(cert)

    def test_inconclusive_not_singularity_proof(self):
        cert = sos.scan([0, 0, -1], 1)
        self.assertEqual(cert["status"], "INCONCLUSIVE")
        self.assertFalse(sos.verify(cert))

    def test_randomized_rational_quadratic_squares(self):
        random.seed(20261008)
        for _ in range(300):
            weight = Fraction(random.randint(1, 12), random.randint(1, 5))
            shift = Fraction(random.randint(-9, -1), random.randint(1, 5))
            residual = Fraction(random.randint(0, 12), random.randint(1, 5))
            # Build gap(z)=weight*(z+shift)^2+residual
            gap = [weight*shift*shift + residual, 2*weight*shift, weight]
            # P(x)=x^2+gap(x-1)
            poly = [gap[0] - gap[1] + gap[2], gap[1] - 2*gap[2],
                    1 + gap[2]]
            cert = sos.synthesize(poly, 1, 2, 1)
            self.assertIsNotNone(cert, (poly, gap))
            self.assertTrue(sos.verify(cert))

    def test_randomized_quartic_square(self):
        random.seed(112358)
        for _ in range(200):
            b, c = random.randint(-6, 6), random.randint(-6, 6)
            gap = sos.times([c, b, 1], [c, b, 1])
            poly = [Fraction(0)] * 5
            from math import comb
            for i, coeff in enumerate(gap):
                for j in range(i + 1):
                    poly[j] += coeff * comb(i, j) * (-1) ** (i-j)
            poly[2] += 1
            cert = sos.synthesize(poly, 1, 2, 1)
            self.assertTrue(sos.verify(cert), (b, c))

    def test_cli_demo(self):
        cp = subprocess.run([sys.executable, "-m", "research_lab.singularity_sos", "demo"],
                            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(cp.returncode, 0, cp.stderr)
        output = json.loads(cp.stdout)
        self.assertEqual(output["previous_coefficient_method"], "INCONCLUSIVE")
        self.assertTrue(sos.verify(output["new_sos_certificate"]))

    def test_cli_verify_file(self):
        cert = sos.synthesize([4, -4, 2], 1, 2, 1)
        with tempfile.TemporaryDirectory() as folder:
            filename = Path(folder) / "proof.json"
            filename.write_text(json.dumps(cert), encoding="utf-8")
            cp = subprocess.run([sys.executable, "-m", "research_lab.singularity_sos", "verify",
                                 str(filename)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 0, cp.stderr)
            self.assertEqual(json.loads(cp.stdout)["status"], "VERIFIED")
            cert["comparison_rate"] = "2"
            filename.write_text(json.dumps(cert), encoding="utf-8")
            cp = subprocess.run([sys.executable, "-m", "research_lab.singularity_sos", "verify",
                                 str(filename)], cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(cp.returncode, 1)


if __name__ == "__main__":
    unittest.main()
