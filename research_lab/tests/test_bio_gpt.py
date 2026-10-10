"""Bio-Gpt mathematical, safety and integration tests, no external services."""
from __future__ import annotations

import copy
import json
import random
import subprocess
import sys
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from research_lab import bio_gpt as g
from research_lab import bio_hilbert as b

ROOT = Path(__file__).resolve().parents[2]


def model(**updates):
    payload = g.demo_problem()
    payload.update(updates)
    return payload


class RoleArchitectureTests(unittest.TestCase):
    def test_brand_and_five_exact_names(self):
        self.assertEqual(g.NAME, "Bio-Gpt")
        self.assertEqual(g.ROLE_NAMES, (
            "GPT-Doug", "GPT-Pineal", "GPT-Doug-Shaggoth", "GPT-Doug-Chaos",
            "GPT-Doug-Redpanda"))

    def test_manifest_has_existing_implementations(self):
        manifest = g.manifest()
        self.assertEqual(manifest["name"], "Bio-Gpt")
        self.assertEqual(len(manifest["roles"]), 5)
        self.assertEqual(len(set(x["source_path"] for x in manifest["roles"])), 5)
        self.assertEqual(len(manifest["channels"]), 6)
        self.assertEqual(manifest["mathematical_space"], "ell2(N;R^6)")

    def test_every_role_actually_changes_vector_field(self):
        state = b.initial_state([[1, 2, 3, 4, 5, 6]], 1)
        for name, a, channel, _ in g.ROLE_EDGES:
            weights = {n: Fraction(0) for n in g.ROLE_NAMES}
            weights[name] = Fraction(1, 8)
            result = g.role_field(state, weights)[0]
            self.assertEqual(result[a], -weights[name] * state[0][channel])
            self.assertEqual(result[channel], weights[name] * state[0][a])
            self.assertEqual(sum(x != 0 for x in result), 2)

    def test_exact_individual_and_total_skew_orthogonality(self):
        rng = random.Random(1309)
        for _ in range(40):
            state = tuple(tuple(Fraction(rng.randint(-8, 8), 9) for _ in range(6))
                          for _ in range(rng.randint(1, 4)))
            values = {name: Fraction(rng.randint(-6, 6), 32) for name in g.ROLE_NAMES}
            self.assertEqual(b.dot(state, g.role_field(state, values)), 0)
            for name in g.ROLE_NAMES:
                single = {n: values[n] if n == name else Fraction(0) for n in g.ROLE_NAMES}
                self.assertEqual(b.dot(state, g.role_field(state, single)), 0)

    def test_all_five_nonzero_in_demo(self):
        result = g.analyze(model())
        self.assertEqual(result["name"], "Bio-Gpt")
        self.assertTrue(all(Fraction(r["strength"]) != 0 for r in result["roles"]))
        self.assertTrue(g.verify(result))

    def test_credentials_or_new_modules_not_accepted(self):
        for extra in ("API_KEY", "GPT-Harvest", "GPT-Doug-Breakout"):
            bad = model()
            bad["roles"] = dict(bad["roles"], **{extra: "1/8"})
            with self.subTest(name=extra), self.assertRaises(ValueError):
                g.analyze(bad)
        bad = model()
        bad["token"] = "secret"
        with self.assertRaises(ValueError):
            g.analyze(bad)

    def test_unsafe_role_strengths_rejected(self):
        for bad_value in (1.0, True, False, None, "1e50", "3/2", "-9/8", {}, []):
            bad = model()
            bad["roles"]["GPT-Pineal"] = bad_value
            with self.subTest(v=bad_value), self.assertRaises(ValueError):
                g.analyze(bad)

    def test_unstable_explicit_euler_step_refused(self):
        bad = model()
        bad["roles"] = {name: 1 for name in g.ROLE_NAMES}
        with self.assertRaises(ValueError):
            g.analyze(bad)

    def test_negated_strengths_are_permitted_if_certified(self):
        bad = model()
        bad["roles"]["GPT-Doug-Chaos"] = "-1/32"
        self.assertTrue(g.verify(g.analyze(bad)))


class ExactHilbertTests(unittest.TestCase):
    def test_analytic_delta_remains_unchanged(self):
        result = g.analyze(model())
        self.assertEqual(result["proof"]["dissipation_delta"], "2")
        self.assertEqual(result["proof"]["operator_norm_upper_bound"], "5/32")
        self.assertEqual(result["proof"]["lipschitz_upper_bound"], "173/32")
        self.assertEqual(result["proof"]["euler_squared_norm_contraction_factor"], "226537/262144")

    def test_every_step_has_exact_energy_cross_term_zero(self):
        report = g.analyze(model(modes=6, steps=5))
        for record in report["trajectory"]:
            self.assertEqual(record["role_cross_term"], "0")
            self.assertGreaterEqual(Fraction(record["dissipation_margin"]), 0)

    def test_exact_euler_stability_at_every_step(self):
        result = g.analyze(model(modes=6, steps=5))
        q = Fraction(result["proof"]["euler_squared_norm_contraction_factor"])
        energies = [Fraction(row["squared_norm"]) for row in result["trajectory"]]
        self.assertTrue(all(b <= q*a for a, b in zip(energies, energies[1:])))

    def test_zero_role_coupling_recovers_bio_hilbert_exactly(self):
        p = model(modes=4, steps=3)
        p["roles"] = {name: "0" for name in g.ROLE_NAMES}
        coupled = g.analyze(p)
        original = b.analyze({k: p[k] for k in ("model", "modes", "initial", "steps")})
        self.assertEqual(coupled["final_state"], original["final_state"])
        self.assertEqual(coupled["final_squared_norm"], original["final_squared_norm"])
        self.assertEqual(coupled["proof"]["euler_squared_norm_contraction_factor"],
                         original["theorem"]["euler_squared_norm_factor_upper_bound"])

    def test_infinite_euler_propagation_exact_at_sufficient_layers(self):
        a = g.analyze(model(modes=4, steps=3))
        longer = g.analyze(model(modes=10, steps=3))
        self.assertTrue(a["exact_infinite_euler_horizon"])
        self.assertEqual(a["final_state"], longer["final_state"][:4])
        self.assertTrue(all(not any(Fraction(z) for z in row)
                            for row in longer["final_state"][4:]))
        self.assertEqual(a["final_squared_norm"], longer["final_squared_norm"])
        self.assertEqual(a["trajectory"][-1]["infinite_euler_error_upper_bound"], "0")

    def test_boundary_error_for_one_layer_is_nonnegative(self):
        short = g.analyze(model(modes=1, steps=3))
        self.assertFalse(short["exact_infinite_euler_horizon"])
        self.assertGreater(Fraction(short["trajectory"][-1]["infinite_euler_error_upper_bound"]), 0)

    def test_decoupled_layers_exact_with_only_one_layer(self):
        p = model(modes=1, steps=3)
        p["model"]["kappa"] = "0"
        a = g.analyze(p)
        self.assertTrue(a["exact_infinite_euler_horizon"])
        self.assertEqual(a["trajectory"][-1]["infinite_euler_error_upper_bound"], "0")

    def test_six_dimensional_case(self):
        self.assertEqual(g.analyze(model(modes=1, steps=0))["finite_dimensions"], 6)

    def test_768_coordinate_case(self):
        report = g.analyze(model(modes=128, steps=1))
        self.assertEqual(report["finite_dimensions"], 768)
        self.assertTrue(g.verify(report))

    def test_hierarchy_proofs_and_finite_limit(self):
        p = model()
        del p["modes"]
        results = g.hierarchy(p, [1, 2, 4, 8])
        self.assertEqual([row["finite_dimensions"] for row in results["layers"]], [6, 12, 24, 48])
        self.assertTrue(results["layers"][-1]["exact_infinite_euler_horizon"])

    def test_hierarchy_bounds_on_number_of_levels(self):
        p = model()
        del p["modes"]
        for levels in ([0], [129], [2, 1], [1, 1], [1]*13, [True, 2]):
            with self.subTest(levels=levels), self.assertRaises(ValueError):
                g.hierarchy(p, levels)

    def test_tampering_rejected_on_every_factual_layer(self):
        original = g.analyze(model())
        for field, value in (("status", "BREAKTHROUGH"), ("external_calls", 7),
                             ("final_squared_norm", "0"), ("evidence_sha256", "0"*64),
                             ("exact_infinite_euler_horizon", False)):
            forged = copy.deepcopy(original)
            forged[field] = value
            self.assertFalse(g.verify(forged))
        forged = copy.deepcopy(original)
        forged["roles"][0]["name"] = "GPT-Other"
        self.assertFalse(g.verify(forged))
        forged = copy.deepcopy(original)
        forged["trajectory"][0]["role_cross_term"] = "1"
        self.assertFalse(g.verify(forged))
        forged = copy.deepcopy(original)
        forged["input"]["roles"]["GPT-Doug"] = "9/8"
        self.assertFalse(g.verify(forged))

    def test_reproducibility(self):
        self.assertEqual(g.analyze(model()), g.analyze(model()))


class CommandLineTests(unittest.TestCase):
    def run_cmd(self, *args):
        return subprocess.run([sys.executable, "-m", "research_lab.bio_gpt", *args],
                              cwd=ROOT, capture_output=True, text=True, timeout=20)

    def test_demo_and_manifest(self):
        demo = self.run_cmd("demo")
        self.assertEqual(demo.returncode, 0, demo.stderr)
        self.assertEqual(json.loads(demo.stdout)["name"], "Bio-Gpt")
        manifest = self.run_cmd("manifest")
        self.assertEqual(manifest.returncode, 0, manifest.stderr)
        self.assertEqual(len(json.loads(manifest.stdout)["roles"]), 5)

    def test_analysis_verification_round_trip_and_tampering(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, cert = Path(tmp) / "src.json", Path(tmp) / "proof.json"
            src.write_text(json.dumps(model()))
            check = self.run_cmd("analyze", str(src))
            self.assertEqual(check.returncode, 0, check.stderr)
            cert.write_text(check.stdout)
            self.assertEqual(self.run_cmd("verify", str(cert)).returncode, 0)
            fake = json.loads(check.stdout)
            fake["proof"]["dissipation_delta"] = "0"
            cert.write_text(json.dumps(fake))
            self.assertEqual(self.run_cmd("verify", str(cert)).returncode, 1)

    def test_invalid_input_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "src.json"
            src.write_text(json.dumps({"bad": "input"}))
            self.assertEqual(self.run_cmd("analyze", str(src)).returncode, 2)


if __name__ == "__main__":
    unittest.main()
