from __future__ import annotations

import json
from pathlib import Path

import pytest

# SymPy is an optional extra. Full-repository test jobs without [math]
# should skip this module; the dedicated math workflow installs it and runs all tests.
pytest.importorskip("sympy", reason="install gpt-doug-llm[math] to test exact algebra")

from gpt_brain.math_mitochondria import MathMitochondria, MathInputError, math_cli


@pytest.fixture
def engine():
    return MathMitochondria()


def test_quadratic_exact_roots_and_certificates(engine):
    out = engine.solve(["x^2 - 5*x + 6 = 0"])
    assert out["status"] == "verified"
    assert {p["x"] for p in out["solutions"]} == {"2", "3"}
    assert all(p["residual"] == "0" and p["verified"] for p in out["solutions"])


def test_linear_system_exact(engine):
    out = engine.solve(["x+y=3", "x-y=1"], variables=["x", "y"])
    assert out["status"] == "verified"
    assert out["solutions"] == [{"x": "2", "y": "1", "verified": True, "residuals": ["0", "0"]}]


def test_underconstrained_system_not_unique(engine):
    out = engine.solve(["x+y=1"])
    assert out["status"] == "underdetermined"
    assert out["solutions"] == []


def test_inconsistent_system(engine):
    out = engine.solve(["x+y=1", "x+y=3"])
    assert out["status"] == "inconsistent"


def test_false_constant_and_true_constant(engine):
    assert engine.solve(["1=2"])["status"] == "inconsistent"
    assert engine.solve(["2=2"])["status"] == "underdetermined"


def test_real_vs_complex_domains(engine):
    assert engine.solve(["x^2+1=0"])["status"] == "no_real_solution"
    out = engine.solve(["x^2+1=0"], domain="complex")
    assert out["status"] == "verified"
    assert {p["x"] for p in out["solutions"]} == {"-I", "I"}


def test_high_degree_not_falsely_solved(engine):
    result = engine.solve(["x^5-2=0"])
    assert result["status"] == "outside_scope"


def test_nonlinear_system_not_falsely_solved(engine):
    out = engine.solve(["x^2+y=1", "x+y=2"])
    assert out["status"] == "outside_scope"


def test_verified_identity(engine):
    out = engine.verify("x^2-1=(x-1)*(x+1)")
    assert out["status"] == "verified"
    assert out["residual"] == "0"


def test_invalid_identity_not_proven(engine):
    out = engine.verify("x^2=x+1")
    assert out["status"] == "refuted"
    assert out["residual"] != "0"
    assert out["counterexample"] is not None


def test_undecidable_claim_not_invented(engine):
    out = engine.theory("Every even integer greater than 2 is a sum of two primes")
    assert out["status"] == "unverified"
    assert out["proof"] is None


@pytest.mark.parametrize("evil", [
    "__import__('os').system('touch /tmp/never-math-mitochondria')=0",
    "().__class__=0",
    "open('/etc/passwd')=0",
    "x[0]=1",
    "x**999999=0",
    "1e309=0",
    "x//2=0",
])
def test_unsafe_math_rejected(engine, evil):
    with pytest.raises(MathInputError):
        engine.solve([evil])
    assert not Path("/tmp/never-math-mitochondria").exists()


def test_cli_solve_json(capsys):
    assert math_cli(["solve", "x^2-1=0"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["status"] == "verified"


def test_cli_prevents_unverified_archive(capsys, tmp_path):
    rc = math_cli(["theory", "Fermat conjecture number two", "--remember", "--memory-file", str(tmp_path / "m.jsonl")])
    assert rc == 2
    assert not (tmp_path / "m.jsonl").exists()


def test_cli_explicit_verified_save(capsys, tmp_path):
    location = tmp_path / "math.jsonl"
    assert math_cli(["solve", "2*x=8", "--remember", "--memory-file", str(location)]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "verified"
    rows = [json.loads(x) for x in location.read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["metadata"]["verification"] == "symbolic_substitution"


def test_variable_denominator_never_claims_unconditional_identity(engine):
    with pytest.raises(MathInputError, match="variable denominators"):
        engine.verify("1/(x-1) = 1/(x-1)")


def test_constant_denominator_still_supported(engine):
    assert engine.solve(["x/2 = 3"])["solutions"][0]["x"] == "6"


def test_constant_identity_verifies_without_poly_generators(engine):
    assert engine.verify("2=2")["status"] == "verified"
    assert engine.verify("3=2")["status"] == "refuted"


def test_high_degree_rejected_before_expensive_polynomial_expansion(engine, monkeypatch):
    def forbidden_poly(*args, **kwargs):
        raise AssertionError("high degree should be screened before SymPy polynomial expansion")
    monkeypatch.setattr(engine.sp, "Poly", forbidden_poly)
    out = engine.solve(["x^8 - 3 = 0"])
    assert out["status"] == "outside_scope"
