"""Bounded, exact rational multidimensional research lab regression tests."""

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from research_lab import multidimensional as m

ROOT = Path(__file__).resolve().parents[2]


class RationalMatrixTests(unittest.TestCase):
    def test_fraction_is_exact(self):
        self.assertEqual(m.fraction("0.1"), Fraction(1, 10))
        self.assertEqual(m.fraction("-7/3"), Fraction(-7, 3))

    def test_no_implicit_float_or_booleans(self):
        for value in (0.5, True, False, None, [], {}):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.fraction(value)

    def test_invalid_rationals_rejected(self):
        for value in ("NaN", "1/0", "1000001", "1/1000001", "", "2" * 50):
            with self.subTest(value=value), self.assertRaises(ValueError):
                m.fraction(value)

    def test_invalid_shapes_and_dimensions(self):
        for value in ([], [[1, 2]], [[1], [2]], [1], [[1, 2], [3]], [[0]*7 for _ in range(7)], "1"):
            with self.subTest(value=str(value)[:50]), self.assertRaises(ValueError):
                m.matrix(value)

    def test_matrix_arithmetic(self):
        A = m.matrix([["1/2", "2"], [0, "1/2"]])
        expected = ((Fraction(1, 4), Fraction(2)), (Fraction(0), Fraction(1, 4)))
        self.assertEqual(m.mult(A, A), expected)
        self.assertEqual(m.mult(m.identity(2), A), A)

    def test_determinant_with_swap(self):
        A = m.matrix([[0, 1], [1, 0]])
        self.assertEqual(m.determinant(A), -1)
        self.assertEqual(m.determinant(m.matrix([[1, 1], [2, 2]])), 0)

    def test_spd_sylvester_exact(self):
        self.assertTrue(m.positive_definite(m.matrix([[2, 1], [1, 2]])))
        self.assertFalse(m.positive_definite(m.matrix([[2, 1], [3, 2]])))
        self.assertFalse(m.positive_definite(m.matrix([[1, 2], [2, 1]])))

    def test_linear_elimination(self):
        result = m.solve_linear([[Fraction(1), Fraction(1), Fraction(3)],
                                 [Fraction(1), Fraction(-1), Fraction(1)]])
        self.assertEqual(result, [Fraction(2), Fraction(1)])
        self.assertIsNone(m.solve_linear([[Fraction(1), Fraction(1), Fraction(2)],
                                          [Fraction(2), Fraction(2), Fraction(4)]]))


class LyapunovCertificateTests(unittest.TestCase):
    def test_scalar_discrete(self):
        A = m.matrix([["1/2"]])
        proof = m.stability_proof(A, "discrete")
        self.assertEqual(proof["P"], [["4/3"]])
        self.assertEqual(proof["certified_energy_step_factor_upper_bound"], "1/4")

    def test_scalar_continuous(self):
        A = m.matrix([[-1]])
        proof = m.stability_proof(A, "continuous")
        self.assertEqual(proof["P"], [["1/2"]])
        self.assertEqual(proof["certified_energy_decay_exponent_lower_bound"], "2")

    def test_stable_nonnormal_with_euclidean_amplification(self):
        result = m.analyze({"matrix": [["1/2", 2], [0, "1/2"]]})
        self.assertEqual(result["proof"]["status"], "PROVED_GLOBALLY_ASYMPTOTICALLY_STABLE")
        self.assertEqual(result["proof"]["P"], [["4/3", "16/9"], ["16/9", "356/27"]])
        self.assertEqual(result["proof"]["certified_energy_step_factor_upper_bound"], "365/392")
        self.assertEqual(result["bounded_exhaustive_search"]["status"], "ONE_STEP_AMPLIFICATION_WITNESS")
        self.assertTrue(m.verify(result))

    def test_unstable_discrete_not_wrongly_certified(self):
        result = m.analyze({"matrix": [[2, 0], [0, "1/2"]]})
        self.assertEqual(result["proof"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["bounded_exhaustive_search"]["status"], "ONE_STEP_AMPLIFICATION_WITNESS")
        self.assertTrue(m.verify(result))

    def test_marginal_dynamics_not_certified(self):
        for mode, value in (("discrete", 1), ("continuous", 0)):
            with self.subTest(mode=mode):
                result = m.analyze({"matrix": [[value]], "mode": mode})
                self.assertEqual(result["proof"]["status"], "INCONCLUSIVE")
                self.assertEqual(result["bounded_exhaustive_search"]["status"], "NO_WITNESS_IN_FINITE_BOX")

    def test_continuous_spiral(self):
        result = m.analyze({"matrix": [[-1, -1], [1, -1]], "mode": "continuous"})
        self.assertEqual(result["proof"]["P"], [["1/2", "0"], ["0", "1/2"]])
        self.assertEqual(result["proof"]["certified_energy_decay_exponent_lower_bound"], "1")
        self.assertTrue(m.verify(result))

    def test_continuous_nonnormal(self):
        result = m.analyze({"matrix": [[-1, 4], [0, -1]], "mode": "continuous"})
        self.assertTrue(m.verify(result))
        self.assertEqual(result["proof"]["status"], "PROVED_GLOBALLY_ASYMPTOTICALLY_STABLE")
        self.assertEqual(result["bounded_exhaustive_search"]["status"], "ONE_STEP_AMPLIFICATION_WITNESS")

    def test_continuous_unstable(self):
        result = m.analyze({"matrix": [[1]], "mode": "continuous"})
        self.assertEqual(result["proof"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["bounded_exhaustive_search"]["status"], "ONE_STEP_AMPLIFICATION_WITNESS")

    def test_skew_symmetric_no_contraction(self):
        result = m.analyze({"matrix": [[0, -1], [1, 0]], "mode": "continuous"})
        self.assertEqual(result["proof"]["status"], "INCONCLUSIVE")
        self.assertEqual(result["bounded_exhaustive_search"]["status"], "NO_WITNESS_IN_FINITE_BOX")

    def test_exact_residual_random_diagonal_3d(self):
        rng = random.Random(14072)
        for i in range(80):
            mode = "discrete" if i % 2 else "continuous"
            diag = [rng.choice(["-1/2", "-1/3", "1/2", "1/4"]) if mode == "discrete"
                    else rng.choice(["-1/2", "-1", "-2", "-3"]) for _ in range(3)]
            A = m.matrix([[diag[j] if j == k else 0 for k in range(3)] for j in range(3)])
            P = m.solve_lyapunov(A, mode)
            self.assertTrue(m.positive_definite(P))
            Q = m.lyapunov_operator(A, P, mode)
            target = m.identity(3)
            if mode == "continuous":
                target = tuple(tuple(-v for v in row) for row in target)
            self.assertEqual(Q, target)

    def test_6d_support(self):
        A = [["1/2" if i == j else 0 for j in range(6)] for i in range(6)]
        result = m.analyze({"matrix": A, "max_evaluations": 2, "radius": 1})
        self.assertTrue(m.verify(result))
        self.assertEqual(result["dimension"], 6)
        self.assertEqual(result["proof"]["status"], "PROVED_GLOBALLY_ASYMPTOTICALLY_STABLE")


class BoundedSearchTests(unittest.TestCase):
    def test_exact_growth(self):
        A = m.matrix([["1/2", 2], [0, "1/2"]])
        self.assertEqual(m.growth(A, "discrete", (0, 1)), Fraction(13, 4))

    def test_bounded_no_witness(self):
        A = m.matrix([["1/2", 0], [0, "1/2"]])
        result = m.grid_search(A, "discrete", 1, 100)
        self.assertEqual(result["status"], "NO_WITNESS_IN_FINITE_BOX")
        self.assertEqual(result["checked_vectors"], 8)

    def test_limited_search_is_not_exhaustive(self):
        A = m.matrix([["1/2", 0], [0, "1/2"]])
        result = m.grid_search(A, "discrete", 5, 3)
        self.assertEqual(result["status"], "SEARCH_LIMIT_REACHED")
        self.assertEqual(result["checked_vectors"], 3)
        self.assertEqual(result["total_vectors_in_box"], 120)

    def test_rejects_unbounded_search(self):
        A = m.matrix([[0]])
        for radius, cap in ((0, 50), (6, 50), (1, 100001), (1, -1), (True, 5), (1, True)):
            with self.subTest(radius=radius, cap=cap), self.assertRaises(ValueError):
                m.grid_search(A, "discrete", radius, cap)

    def test_invalid_top_level_objects(self):
        cases = [[], {}, {"matrix": [[1]], "API_KEY": "test"},
                 {"matrix": [[1]], "mode": "impossible"},
                 {"matrix": [[1]], "radius": 1.5},
                 {"matrix": [[1]], "max_evaluations": None}]
        for problem in cases:
            with self.subTest(problem=problem), self.assertRaises(ValueError):
                m.analyze(problem)

    def test_reject_tampered_certificates(self):
        result = m.analyze({"matrix": [["1/2", "2"], [0, "1/2"]]})
        for key, new_value in (("evidence_sha256", "0"*64), ("dimension", 99),
                               ("caveat", "solved all universal problems"),
                               ("external_access", "on")):
            modified = copy.deepcopy(result)
            modified[key] = new_value
            self.assertFalse(m.verify(modified))
        modified = copy.deepcopy(result)
        modified["proof"]["P"][0][0] = "7/8"
        self.assertFalse(m.verify(modified))
        modified = copy.deepcopy(result)
        modified["bounded_exhaustive_search"]["vector"] = [0, 0]
        self.assertFalse(m.verify(modified))

    def test_no_unknown_status_could_verify(self):
        self.assertFalse(m.verify({"input": [], "proof": "fake"}))

    def test_real_cli_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            model_file = Path(td) / "model.json"
            cert_file = Path(td) / "certificate.json"
            model_file.write_text(json.dumps({"matrix": [["1/2", 2], [0, "1/2"]]}))
            proc = subprocess.run([sys.executable, "-m", "research_lab.multidimensional", "analyze", str(model_file)],
                                  cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            cert_file.write_text(proc.stdout)
            check = subprocess.run([sys.executable, "-m", "research_lab.multidimensional", "verify", str(cert_file)],
                                   cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)
            self.assertEqual(json.loads(check.stdout)["status"], "VERIFIED")
            forged = json.loads(cert_file.read_text())
            forged["proof"]["trace_P"] = "1000"
            cert_file.write_text(json.dumps(forged))
            check = subprocess.run([sys.executable, "-m", "research_lab.multidimensional", "verify", str(cert_file)],
                                   cwd=ROOT, text=True, capture_output=True)
            self.assertEqual(check.returncode, 1)

    def test_oversized_json_file(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "large.json"
            p.write_text("a" * (m.MAX_INPUT_BYTES + 1))
            with self.assertRaises(ValueError):
                m.read_json(p)


if __name__ == "__main__":
    unittest.main()
