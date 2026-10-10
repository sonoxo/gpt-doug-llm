"""Bio-Gpt: five named, mathematically active operators on Bio-Hilbert.

Not a physical biochip, functioning agent swarm, or model of real neurons.
For every six-channel layer, add sum(eta_r J_r X_j) to the established
Bio-Hilbert vector field, with five fixed skew-symmetric J_r rotations.
The new operators preserve the infinite-space dissipation inequality.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Sequence

from research_lab import bio_hilbert as base

NAME = "Bio-Gpt"
# Name, from channel, to channel, existing source path.
ROLE_EDGES = (
    ("GPT-Doug", 0, 1, "gpt_brain/math_mitochondria.py"),
    ("GPT-Pineal", 1, 5, "integrations/gpt-doug-pineal/src/pineal/store.py"),
    ("GPT-Doug-Shaggoth", 2, 3, "gpt_zyra_shaggoth/bridge.py"),
    ("GPT-Doug-Chaos", 3, 4, "gpt_chaos/runtime.py"),
    ("GPT-Doug-Redpanda", 4, 5, "redpanda-desktop/gpt_redpanda_llm.py"),
)
ROLE_NAMES = tuple(name for name, _, _, _ in ROLE_EDGES)
DEFAULT_ROLES = {name: "1/32" for name in ROLE_NAMES}


def strengths(raw: Any) -> Dict[str, Fraction]:
    if not isinstance(raw, dict) or set(raw) != set(ROLE_NAMES):
        raise ValueError("roles must contain precisely the five Bio-Gpt components")
    weights = {name: base.rational(raw[name]) for name in ROLE_NAMES}
    if any(abs(w) > 1 for w in weights.values()):
        raise ValueError("role strengths must remain between -1 and 1")
    return weights


def role_field(state, weights):
    out = []
    for block in state:
        transfer = [Fraction(0) for _ in range(6)]
        for name, a, b, _ in ROLE_EDGES:
            w = weights[name]
            transfer[a] -= w * block[b]
            transfer[b] += w * block[a]
        out.append(tuple(transfer))
    return tuple(out)


def combined_field(state, model, weights):
    base_field = base.vector_field(state, model)
    roles = role_field(state, weights)
    return tuple(tuple(v + w for v, w in zip(b, r)) for b, r in zip(base_field, roles))


def constants(model, weights):
    extra = sum((abs(w) for w in weights.values()), Fraction(0))
    lip = model["L"] + extra
    h, delta = model["dt"], model["delta"]
    q = 1 - 2 * h * delta + h * h * lip * lip
    if not 0 <= q < 1:
        raise ValueError("Euler stability unverified: reduce dt or role strengths")
    return {"extra": extra, "lip": lip, "q": q, "rho": (1 + q) / 2}


def validated(payload):
    if not isinstance(payload, dict) or set(payload) != {"model", "roles", "modes", "initial", "steps"}:
        raise ValueError("expected model, roles, modes, initial, steps")
    canonical, model, state = base._canonical_problem(
        {key: payload[key] for key in ("model", "modes", "initial", "steps")}
    )
    weights = strengths(payload["roles"])
    cert = constants(model, weights)
    canonical["roles"] = {name: str(weights[name]) for name in ROLE_NAMES}
    return canonical, model, state, weights, cert


def exact_energy(state, model, weights):
    cross = base.dot(state, role_field(state, weights))
    if cross != 0:
        raise ArithmeticError("skew-symmetric energy identity failed")
    baseline_margin = base.exact_dissipation_check(state, model)
    full = combined_field(state, model, weights)
    margin = -model["delta"] * base.norm2(state) - base.dot(state, full)
    if margin != baseline_margin or margin < 0:
        raise ArithmeticError("Bio-Gpt energy dissipation failed")
    return margin, cross, full


def manifest():
    return {"name": NAME, "repository": "sonoxo/gpt-doug-llm",
            "mathematical_space": "ell2(N;R^6)", "channels": list(base.CHANNELS),
            "roles": [{"name": name, "source_path": source,
                       "from": base.CHANNELS[a], "to": base.CHANNELS[b],
                       "rotation": f"J({a},{b})"}
                      for name, a, b, source in ROLE_EDGES],
            "runtime_scope": "read-only symbolic adapters; no subagents started or external effects"}


def analyze(payload: Any) -> Dict[str, Any]:
    canonical, model, state, weights, cert = validated(payload)
    h, q, rho = model["dt"], cert["q"], cert["rho"]
    initial_energy = base.norm2(state)
    support = max((i + 1 for i, block in enumerate(state) if any(block)), default=0)
    error = Fraction(0)
    trajectory = []
    for step in range(canonical["steps"] + 1):
        base._ensure_bit_cap(state)
        energy = base.norm2(state)
        margin, cross, derivative = exact_energy(state, model, weights)
        trajectory.append({
            "step": step, "squared_norm": str(energy),
            "role_cross_term": str(cross), "dissipation_margin": str(margin),
            "boundary_generator_residual_squared": str(base.boundary_residual_squared(state, model)),
            "infinite_euler_error_upper_bound": str(error),
        })
        if step == canonical["steps"]:
            break
        newer = tuple(tuple(x + h * y for x, y in zip(block, d))
                      for block, d in zip(state, derivative))
        base._ensure_bit_cap(newer)
        if base.norm2(newer) > q * energy:
            raise ArithmeticError("exact Euler energy contraction failed")
        error = rho * error + h * model["kappa"] * sum((abs(x) for x in state[-1]), Fraction(0))
        state = newer
    report = {
        "status": "CERTIFIED_BIO_GPT_SIX_TO_INFINITY", "name": NAME,
        "scope": "six-channel infinite-dimensional Hilbert-space toy model; finite exact Euler",
        "input": canonical, "channels": list(base.CHANNELS),
        "roles": [{"name": name, "strength": str(weights[name]),
                   "source_path": source, "edge": [base.CHANNELS[a], base.CHANNELS[b]]}
                  for name, a, b, source in ROLE_EDGES],
        "finite_dimensions": 6 * len(state),
        "proof": {
            "continuous_decay": "||X(t)|| <= exp(-(alpha-beta)*t) ||X(0)|| if U=0",
            "forced_decay": "||X(t)|| <= exp(-delta*t)||X(0)|| + integral_0^t exp(-delta*(t-s))||U(s)|| ds",
            "skew_role_energy_identity": "<X,J_r X>=0 for each r",
            "dissipation_delta": str(model["delta"]),
            "operator_norm_upper_bound": str(cert["extra"]),
            "lipschitz_upper_bound": str(cert["lip"]),
            "euler_squared_norm_contraction_factor": str(q),
            "euler_norm_factor_upper_bound": str(rho),
            "nearest_neighbor_only": True,
        },
        "initial_support_modes": support,
        "exact_infinite_euler_horizon": (
            model["kappa"] == 0 or canonical["modes"] >= support + canonical["steps"]
        ),
        "trajectory": trajectory,
        "final_state": [[str(x) for x in block] for block in state],
        "initial_squared_norm": str(initial_energy),
        "final_squared_norm": str(base.norm2(state)),
        "external_calls": 0,
        "limits": "No physical biology, hidden model weights, consciousness, external API access, or infinite computation",
    }
    raw = json.dumps(report, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    report["evidence_sha256"] = hashlib.sha256(raw.encode("ascii")).hexdigest()
    return report


def verify(report: Any) -> bool:
    try:
        return isinstance(report, dict) and report == analyze(report["input"])
    except (ValueError, TypeError, KeyError, ArithmeticError, OverflowError):
        return False


def hierarchy(payload: Any, levels: Sequence[int]) -> Dict[str, Any]:
    if (not isinstance(levels, list) or not levels or len(levels) > 12 or
        any(type(n) is not int or not 1 <= n <= base.MAX_MODES for n in levels) or
        levels != sorted(set(levels))):
        raise ValueError("levels must be 1..12 unique ascending integers in range 1..128")
    if not isinstance(payload, dict) or set(payload) != {"model", "roles", "initial", "steps"}:
        raise ValueError("hierarchy expects model, roles, initial, steps")
    if not isinstance(payload["initial"], list) or len(payload["initial"]) > levels[0]:
        raise ValueError("initial support must fit the smallest level")
    rows = []
    for n in levels:
        result = analyze({**payload, "modes": n})
        rows.append({"modes": n, "finite_dimensions": result["finite_dimensions"],
                     "final_squared_norm": result["final_squared_norm"],
                     "exact_infinite_euler_horizon": result["exact_infinite_euler_horizon"],
                     "error_bound": result["trajectory"][-1]["infinite_euler_error_upper_bound"],
                     "evidence_sha256": result["evidence_sha256"]})
    return {"name": NAME, "status": "CERTIFIED_BOUNDED_FINITE_HIERARCHY", "layers": rows,
            "limits": "The analytic infinite-space claim does not compute infinitely many coordinates"}


def demo_problem() -> Dict[str, Any]:
    return {**base.demo_problem(), "roles": dict(DEFAULT_ROLES)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog=NAME, description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("demo")
    commands.add_parser("manifest")
    for action in ("analyze", "verify", "hierarchy"):
        c = commands.add_parser(action)
        c.add_argument("file", type=Path)
        if action == "hierarchy":
            c.add_argument("--levels", default="1,2,4,8,16")
    args = parser.parse_args(argv)
    try:
        if args.action == "demo":
            result = analyze(demo_problem())
        elif args.action == "manifest":
            result = manifest()
        elif args.action == "verify":
            result = {"status": "VERIFIED" if verify(base.load_json(args.file)) else "INVALID"}
        elif args.action == "hierarchy":
            result = hierarchy(base.load_json(args.file), [int(x) for x in args.levels.split(",")])
        else:
            result = analyze(base.load_json(args.file))
        print(json.dumps(result, sort_keys=True, indent=2))
        return 1 if result.get("status") == "INVALID" else 0
    except (ValueError, TypeError, OSError, KeyError, ArithmeticError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "kind": type(exc).__name__,
                          "message": str(exc)[:160]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
