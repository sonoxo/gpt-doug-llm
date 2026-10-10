"""Exact bounded lateral stability simulation, independently designed from a video title.

The linked YouTube Short's public metadata identifies 'Lateral Stability &
Mobility Tests', creator NoLimits AI. This code is NOT extracted from that clip
and is NOT a physical robot/exoskeleton controller or medical device.

Toy 1D lateral state x=(position,velocity) and semi-implicit PD update:
    a_k = -kp * p_k - kd * v_k + d_k
    v_(k+1) = v_k + dt * a_k
    p_(k+1) = p_k + dt * v_(k+1)

For A,B below with mu=||A||_infinity<1, beta=||B||_infinity,
||x_k||_infinity <= mu^k ||x0||_infinity + beta*D*(1-mu^k)/(1-mu),
for all disturbances |d_k|<=D. Thus max(||x0||_inf, beta D/(1-mu))
certifies |p_k| <= support_half_width in this 1D model for all k.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

MAX_STEPS = 64
SOURCE = "https://www.youtube.com/shorts/eNIFAcuEFVU?feature=share"
METADATA = {"title": "LATERAL STABILITY & MOBILITY TESTS", "creator": "NoLimits AI",
            "provenance": "YouTube public oEmbed metadata only; visuals and captions not observed"}


def exact(v: Any) -> Fraction:
    if isinstance(v, bool) or isinstance(v, float) or not isinstance(v, (int, str)):
        raise ValueError("exact rational string or integer required; floats prohibited")
    if isinstance(v, str) and (not v or len(v) > 32):
        raise ValueError("rational token length out of bounds")
    try:
        value = Fraction(v)
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError("invalid rational value") from exc
    if abs(value.numerator) > 10000 or value.denominator > 10000:
        raise ValueError("rational coefficient out of bounds")
    return value


def validate(problem: Any) -> tuple[dict[str, Any], dict[str, Fraction]]:
    if not isinstance(problem, dict) or set(problem) != {"model", "initial", "disturbance_bound", "disturbances", "support_half_width"}:
        raise ValueError("expected model, initial, disturbance_bound, disturbances, support_half_width")
    model = problem["model"]
    initial = problem["initial"]
    if not isinstance(model, dict) or set(model) != {"dt", "kp", "kd"}:
        raise ValueError("model must have exactly dt, kp and kd")
    if not isinstance(initial, dict) or set(initial) != {"position", "velocity"}:
        raise ValueError("initial must have position and velocity")
    q = {key: exact(val) for key, val in {**model, **initial,
         "disturbance_bound": problem["disturbance_bound"],
         "support_half_width": problem["support_half_width"]}.items()}
    if not (0 < q["dt"] <= 1 and 0 <= q["kp"] <= 10 and 0 <= q["kd"] <= 10):
        raise ValueError("dt and gains outside bounded simulation range")
    if not (0 <= q["disturbance_bound"] <= 1 and 0 < q["support_half_width"] <= 10):
        raise ValueError("support width or disturbance bound out of range")
    values = problem["disturbances"]
    if not isinstance(values, list) or not 1 <= len(values) <= MAX_STEPS:
        raise ValueError("supply 1..64 explicitly bounded disturbances")
    disturbances = [exact(v) for v in values]
    if any(abs(d) > q["disturbance_bound"] for d in disturbances):
        raise ValueError("finite disturbances exceed stated global bound")
    q["disturbances"] = disturbances
    canonical = {"model": {key: str(q[key]) for key in ("dt", "kp", "kd")},
                 "initial": {key: str(q[key]) for key in ("position", "velocity")},
                 "disturbance_bound": str(q["disturbance_bound"]),
                 "support_half_width": str(q["support_half_width"]),
                 "disturbances": [str(d) for d in disturbances]}
    return canonical, q


def analyze(problem: Any) -> dict[str, Any]:
    canonical, q = validate(problem)
    h, kp, kd = (q[k] for k in ("dt", "kp", "kd"))
    dmax, width = q["disturbance_bound"], q["support_half_width"]
    A = ((1-h*h*kp, h*(1-h*kd)), (-h*kp, 1-h*kd))
    B = (h*h, h)
    mu = max(sum(abs(v) for v in row) for row in A)
    beta = max(abs(z) for z in B)
    p, v = q["position"], q["velocity"]
    initial_inf = max(abs(p), abs(v))
    invariant = max(initial_inf, beta*dmax/(1-mu)) if mu < 1 else None
    proven = invariant is not None and invariant <= width
    data = [{"step": 0, "position": str(p), "velocity": str(v),
             "in_support": abs(p) <= width, "support_margin": str(width-abs(p))}]
    for step, d in enumerate(q["disturbances"], 1):
        a = -kp*p - kd*v + d
        v = v + h*a
        p = p + h*v
        data.append({"step": step, "disturbance": str(d), "acceleration": str(a),
                     "position": str(p), "velocity": str(v),
                     "in_support": abs(p) <= width,
                     "support_margin": str(width-abs(p))})
    report = {
        "status": "PROVED_TOY_SUPPORT_INVARIANT" if proven else "UNCERTIFIED_FOR_ALL_DISTURBANCES",
        "scope": "exact 1D lateral PD simulation; no physical stability guarantee",
        "input": canonical,
        "model_equation": "a=-kp*p-kd*v+d; v_next=v+h*a; p_next=p+h*v_next",
        "A": [[str(x) for x in row] for row in A],
        "B": [str(x) for x in B],
        "proof": {
            "matrix_infinity_norm_mu": str(mu),
            "input_infinity_norm_beta": str(beta),
            "bounded_disturbance": str(dmax),
            "support_half_width": str(width),
            "uniform_infinity_state_bound": str(invariant) if invariant is not None else None,
            "valid_when": "mu<1 and all k have |d[k]|<=D",
            "all_steps_position_in_support_proven": proven,
            "finite_samples_inside_support": all(x["in_support"] for x in data),
        },
        "trajectory": data,
        "source_provenance": {**METADATA, "url": SOURCE},
        "limits": ["Only video title/creator were obtained; no video code reproduced",
                   "Static position corridor is not a dynamic fall-risk certificate",
                   "No hardware, motors, medical treatment, sensors or autonomy involved"],
    }
    stable = json.dumps(report, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    report["evidence_sha256"] = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return report


def verify(report: Any) -> bool:
    try:
        return isinstance(report, dict) and report == analyze(report["input"])
    except (TypeError, ValueError, KeyError, ZeroDivisionError):
        return False


def example() -> dict[str, Any]:
    return {"model": {"dt": "1/2", "kp": "1", "kd": "2"},
            "initial": {"position": "1/20", "velocity": "0"},
            "disturbance_bound": "1/100", "support_half_width": "1/10",
            "disturbances": ["0", "1/100", "-1/100", "0", "1/100", "-1/100"]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="cmd", required=True)
    commands.add_parser("demo")
    a = commands.add_parser("analyze")
    a.add_argument("input", type=Path)
    v = commands.add_parser("verify")
    v.add_argument("report", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.cmd == "verify":
            good = verify(json.loads(args.report.read_text()))
            print(json.dumps({"status": "VERIFIED" if good else "INVALID"}))
            return 0 if good else 1
        model = example() if args.cmd == "demo" else json.loads(args.input.read_text())
        result = analyze(model)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["status"].startswith("PROVED") else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "INVALID_INPUT", "error_type": type(exc).__name__}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
