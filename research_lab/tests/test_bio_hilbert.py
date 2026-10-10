"""Offline tests: exact six-channel Galerkin model and infinite-space bounds."""
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

from research_lab import bio_hilbert as b

ROOT = Path(__file__).resolve().parents[2]
MODEL = {"alpha": "3", "beta": "1", "kappa": "1/4", "omega": ["1/4", "1/8", "1/16"], "dt": "1/16"}


def problem(modes=6, steps=3, initial=None):
    if initial is None:
        initial = [[1, 0, 0, 0, 0, 0]]
    return {"model": dict(MODEL), "modes": modes, "initial": initial, "steps": steps}


class ExactInputTests(unittest.TestCase):
    def test_exact_ratios_and_decimal_strings(self):
        self.assertEqual(b.rational("0.125"), Fraction(1, 8))
        self.assertEqual(b.rational("-5/8"), Fraction(-5, 8))

    def test_reject_float_boolean_and_invalid(self):
        for x in (True, False, 0.1, None, [], {}, "NaN", "1/0", "1e3", "1000001", "1/1000001", "1" * 49):
            with self.subTest(x=x), self.assertRaises(ValueError):
                b.rational(x)

    def test_reject_incorrect_model_schema(self):
        for bad in ({}, {"alpha": "3"}, dict(MODEL, password="secret")):
            with self.subTest(model=bad), self.assertRaises(ValueError):
                b.param_model(bad)

    def test_reject_model_parameters_not_dissipative(self):
        for key, bad in [("alpha", "1"), ("beta", "4"), ("beta", "-1"), ("kappa", "-1"), ("dt", "0"), ("dt", "1")]:
            raw = dict(MODEL, **{key: bad})
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                b.param_model(raw)

    def test_reject_wrong_omega_types(self):
        for o in ([], [1, 2], "1,2,3", [0, True, 0], [0, 0, []]):
            with self.subTest(o=o), self.assertRaises(ValueError):
                b.param_model(dict(MODEL, omega=o))

    def test_reject_modes_steps_and_extra_keys(self):
        for key, bad in (("modes", 0), ("modes", 129), ("modes", True), ("steps", -1), ("steps", 9), ("steps", 0.1)):
            with self.subTest(key=key, bad=bad), self.assertRaises(ValueError):
                b.analyze(dict(problem(), **{key:bad}))
        with self.assertRaises(ValueError):
            b.analyze(dict(problem(), secret="no"))

    def test_initial_schema_and_bounds(self):
        for value in ("raw", [[1]], [[0,0,0,0,0, True]], [[1]*6, [2]*6]):
            with self.subTest(value=value), self.assertRaises(ValueError):
                b.initial_state(value, 1)

    def test_input_file_size_limit(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "huge.json"
            path.write_text("x"*(b.MAX_INPUT_BYTES+1))
            with self.assertRaises(ValueError):
                b.load_json(path)


class OperatorIdentityTests(unittest.TestCase):
    def test_channels_and_dimensions(self):
        self.assertEqual(len(b.CHANNELS), 6)
        self.assertEqual(len(b.initial_state([[1,0,0,0,0,0]], 6)), 6)
        self.assertEqual(b.analyze(problem())["finite_dimensions"], 36)

    def test_energy_and_gradient_dirichlet_boundary(self):
        x = b.initial_state([[1,0,0,0,0,0]], 1)
        self.assertEqual(b.norm2(x), 1)
        self.assertEqual(b.gradient2(x), 2)
        self.assertEqual(b.boundary_residual_squared(x,b.param_model(MODEL)), Fraction(1,16))

    def test_nonlinear_saturation_exact(self):
        self.assertEqual(b.sat(Fraction(2)), Fraction(2,3))
        self.assertEqual(b.sat(Fraction(-2)), Fraction(-2,3))
        self.assertEqual(b.sat(Fraction(0)), 0)

    def test_skew_channel_coupling_does_no_work(self):
        p = b.param_model(MODEL)
        x = b.initial_state([[3,4,-5,2,7,11]], 1)
        self.assertGreaterEqual(b.exact_dissipation_check(x,p), 0)
        F = b.vector_field(x,p)
        # Pure skew action is orthogonal to the full state, exactly.
        w = p["omega"]
        omega_x = [(-w[0]*x[0][1],w[0]*x[0][0],-w[1]*x[0][3],w[1]*x[0][2],-w[2]*x[0][5],w[2]*x[0][4])]
        self.assertEqual(b.dot(x,omega_x), 0)
        self.assertEqual(len(F[0]), 6)

    def test_energy_identity_randomized(self):
        rng = random.Random(761)
        m = b.param_model(MODEL)
        for _ in range(80):
            n = rng.randint(1, 8)
            x = b.initial_state([[rng.randrange(-6,7) for _ in range(6)] for _ in range(n)],n)
            self.assertGreaterEqual(b.exact_dissipation_check(x,m), 0)

    def test_zero_is_equilibrium(self):
        x=b.initial_state([],3)
        self.assertEqual(b.vector_field(x,b.param_model(MODEL)), (b.ZERO,)*3)
        self.assertEqual(b.norm2(x),0)

    def test_nontrivial_three_pair_interaction(self):
        m = b.param_model(MODEL)
        x = b.initial_state([[1,0,0,0,0,0]],1)
        F = b.vector_field(x,m)
        self.assertEqual(F[0][0],-3)
        self.assertEqual(F[0][1],Fraction(1,4))
        self.assertEqual(F[0][2:],(Fraction(0),)*4)


class StabilityAndTruncationTests(unittest.TestCase):
    def test_reproduces_earlier_six_dimensional_half_identity(self):
        # The previous 6D linear test system A=(1/2)*I_6 is a special case.
        legacy = {"alpha": "8", "beta": "0", "kappa": "0",
                  "omega": ["0", "0", "0"], "dt": "1/16"}
        out = b.analyze({"model": legacy, "modes": 1,
                         "initial": [[2, -4, 6, -8, 10, -12]], "steps": 1})
        self.assertEqual(out["final_state"], [["1", "-2", "3", "-4", "5", "-6"]])
        self.assertEqual(out["theorem"]["euler_squared_norm_factor_upper_bound"], "1/4")
        self.assertTrue(out["exact_infinite_euler_horizon"])
        self.assertTrue(b.verify(out))

    def test_exact_dimension_independent_certificate(self):
        model=b.param_model(MODEL)
        self.assertEqual(model["delta"],2)
        self.assertEqual(model["L"],Fraction(21,4))
        self.assertEqual(model["q"],Fraction(3513,4096))
        self.assertTrue(0<model["q"]<1)
        self.assertGreaterEqual(model["rho"]*model["rho"],model["q"])

    def test_first_step_rational_6d(self):
        out=b.analyze(problem(modes=1,steps=1))
        self.assertEqual(out["finite_dimensions"],6)
        self.assertEqual(out["final_state"][0][:2],["13/16","1/64"])
        self.assertEqual(out["final_squared_norm"],"2705/4096")
        self.assertEqual(out["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"],"1/64")
        self.assertFalse(out["exact_infinite_euler_horizon"])
        self.assertTrue(b.verify(out))

    def test_two_modes_capture_one_step_infinitely_exact(self):
        out=b.analyze(problem(modes=2,steps=1))
        self.assertTrue(out["exact_infinite_euler_horizon"])
        self.assertEqual(out["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"],"0")
        self.assertEqual(out["final_state"][1][0],"1/64")
        self.assertTrue(b.verify(out))

    def test_exact_finite_propagation_at_mode4_step3(self):
        out=b.analyze(problem(modes=4,steps=3))
        self.assertTrue(out["exact_infinite_euler_horizon"])
        self.assertEqual(out["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"],"0")

    def test_truncation_bound_positive_when_omitting_new_modes(self):
        out=b.analyze(problem(modes=1,steps=3))
        self.assertGreater(Fraction(out["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"]),0)
        self.assertLessEqual(Fraction(out["final_squared_norm"]),Fraction(out["initial_squared_norm"]))
        self.assertTrue(b.verify(out))

    def test_energy_bound_all_exact_steps(self):
        out=b.analyze(problem(modes=6,steps=3))
        q=Fraction(out["theorem"]["euler_squared_norm_factor_upper_bound"])
        trace=out["trajectory"]
        for i in range(len(trace)-1):
            self.assertLessEqual(Fraction(trace[i+1]["squared_norm"]),q*Fraction(trace[i]["squared_norm"]))
        self.assertTrue(b.verify(out))

    def test_hierarchy_6d_to_96d(self):
        payload=problem()
        payload.pop("modes")
        out=b.hierarchy(payload,[1,2,4,8,16])
        self.assertEqual([x["dimensions"] for x in out["layers"]],[6,12,24,48,96])
        self.assertTrue(out["layers"][2]["finite_euler_is_exact_in_infinite_space_for_horizon"])
        self.assertFalse(out["layers"][0]["finite_euler_is_exact_in_infinite_space_for_horizon"])
        self.assertEqual(out["layers"][2]["euler_error_upper_bound"],"0")
        self.assertEqual(out["layers"][3]["final_squared_norm"],out["layers"][4]["final_squared_norm"])

    def test_hierarchy_rejects_invalid_levels(self):
        p=problem();p.pop("modes")
        for bad in ([],[4,4],[2,1],[0],[129],[1.5],[True],list(range(1,14))):
            with self.subTest(levels=bad),self.assertRaises(ValueError):
                b.hierarchy(p,bad)

    def test_128_modes_768_channels(self):
        out=b.analyze(problem(modes=128,steps=1))
        self.assertEqual(out["finite_dimensions"],768)
        self.assertTrue(out["exact_infinite_euler_horizon"])
        self.assertEqual(out["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"],"0")

    def test_wrong_initial_support_for_hierarchy(self):
        p=problem();p.pop("modes");p["initial"]=[[1]*6,[1]*6]
        with self.assertRaises(ValueError):
            b.hierarchy(p,[1,2])

    def test_tampered_report_rejected(self):
        report=b.analyze(problem(modes=2,steps=1))
        for change in (("evidence_sha256","0"*64),
                       ("finite_dimensions",999),
                       ("exact_infinite_euler_horizon",False),
                       ("external_calls",15),
                       ("qualification","solved all biology")):
            v=copy.deepcopy(report)
            v[change[0]]=change[1]
            self.assertFalse(b.verify(v))
        v=copy.deepcopy(report)
        v["final_state"][1][0]="1000"
        self.assertFalse(b.verify(v))
        v=copy.deepcopy(report)
        v["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"]="0"
        # This one should actually be zero; change to a bad nonzero value.
        v["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"]="7"
        self.assertFalse(b.verify(v))

    def test_cli_analyze_verify_roundtrip(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"problem.json";p.write_text(json.dumps(problem(modes=2,steps=1)))
            proc=subprocess.run([sys.executable,"-m","research_lab.bio_hilbert","analyze",str(p)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            path=Path(directory)/"report.json";path.write_text(proc.stdout)
            check=subprocess.run([sys.executable,"-m","research_lab.bio_hilbert","verify",str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(check.returncode,0,check.stderr)
            self.assertEqual(json.loads(check.stdout)["status"],"VERIFIED")
            tampered=json.loads(proc.stdout);tampered["theorem"]["omega_skew_symmetric"]=False
            path.write_text(json.dumps(tampered))
            check=subprocess.run([sys.executable,"-m","research_lab.bio_hilbert","verify",str(path)],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(check.returncode,1)

    def test_hierarchy_cli(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/"hierarchy.json";q=problem();q.pop("modes");p.write_text(json.dumps(q))
            proc=subprocess.run([sys.executable,"-m","research_lab.bio_hilbert","hierarchy",str(p),"--levels","1,2,4,8"],cwd=ROOT,capture_output=True,text=True)
            self.assertEqual(proc.returncode,0,proc.stderr)
            self.assertEqual([x["dimensions"] for x in json.loads(proc.stdout)["layers"]],[6,12,24,48])

    def test_no_network_or_credentials_in_module(self):
        source=(ROOT/"research_lab"/"bio_hilbert.py").read_text(encoding="utf-8")
        for forbidden in ("urllib", "requests.get", "socket.", "subprocess.", "os.environ", "OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY"):
            self.assertNotIn(forbidden,source)


if __name__=="__main__":
    unittest.main()
