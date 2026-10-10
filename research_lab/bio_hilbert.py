"""Exact 6-channel, finite-to-infinite Hilbert-space biocomputing toy model.

A mathematical abstraction: not a physical biochip, measured biology, AGI,
or a result about arbitrary nonlinear systems. Infinite-dimensional theorems
are established analytically; the program computes only finite truncations.

H = ell^2(N, R^6), X_0 = 0 (boundary at left).
X'_j = -alpha X_j + kappa (X_{j-1}-2 X_j+X_{j+1})
      + Omega X_j + beta sat(X_j) + U_j,
sat(z)=z/(1+abs(z)), Omega skew-symmetric with three 2x2 blocks.
Assumptions alpha > beta >= 0, kappa >= 0, U locally integrable into H.
No input produces exponential decay with delta=alpha-beta.
Finite Euler simulations use exact rational arithmetic and certified h.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Sequence, Tuple

CHANNELS = ("neural", "metabolic", "immune", "epigenetic", "sensory", "memory")
MAX_MODES = 128
MAX_STEPS = 8
MAX_INPUT_BYTES = 65536
MAX_BITS = 8192
ZERO = (Fraction(0),) * 6
RATIONAL_RE = re.compile(r"-?[0-9]+(?:/[1-9][0-9]*|\.[0-9]+)?\Z")


def rational(value: Any) -> Fraction:
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (int, str, Fraction)):
        raise ValueError("all quantities must be exact rational values, never float or bool")
    if isinstance(value, str) and (len(value) > 48 or not RATIONAL_RE.fullmatch(value)):
        raise ValueError("bad rational literal")
    try:
        result = Fraction(value)
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError("bad rational literal") from exc
    if abs(result.numerator) > 1000000 or result.denominator > 1000000:
        raise ValueError("input rational out of bounds")
    return result


def param_model(value: Any) -> Dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"alpha", "beta", "kappa", "omega", "dt"}:
        raise ValueError("model keys must be alpha, beta, kappa, omega, dt")
    omega_raw = value["omega"]
    if not isinstance(omega_raw, list) or len(omega_raw) != 3:
        raise ValueError("omega must be a list of three rational frequencies")
    alpha, beta, kappa, dt = (rational(value[k]) for k in ("alpha", "beta", "kappa", "dt"))
    omegas = tuple(rational(w) for w in omega_raw)
    if not alpha > beta >= 0 or kappa < 0 or dt <= 0:
        raise ValueError("requires alpha > beta >= 0, kappa >= 0 and dt > 0")
    delta = alpha - beta
    max_omega = max(abs(w) for w in omegas)
    L = alpha + 4 * kappa + max_omega + beta
    q = Fraction(1) - 2 * dt * delta + dt * dt * L * L
    if not 0 <= q < 1:
        raise ValueError("Euler step not certified: require 0 < dt < 2*(alpha-beta)/L^2")
    return {"alpha": alpha, "beta": beta, "kappa": kappa, "omega": omegas,
            "dt": dt, "delta": delta, "L": L, "q": q, "rho": (1 + q) / 2}


def zero_block() -> Tuple[Fraction, ...]:
    return ZERO


def initial_state(raw: Any, modes: int) -> Tuple[Tuple[Fraction, ...], ...]:
    if not isinstance(raw, list) or len(raw) > modes:
        raise ValueError("initial must be a list of at most modes six-channel blocks")
    rows = []
    for block in raw:
        if not isinstance(block, list) or len(block) != 6:
            raise ValueError("each initial mode must contain exactly 6 rational values")
        rows.append(tuple(rational(x) for x in block))
    rows.extend([ZERO] * (modes - len(rows)))
    return tuple(rows)


def norm2(x: Sequence[Sequence[Fraction]]) -> Fraction:
    return sum((v * v for block in x for v in block), Fraction(0))


def gradient2(x: Sequence[Sequence[Fraction]]) -> Fraction:
    previous = ZERO
    total = Fraction(0)
    for block in list(x) + [ZERO]:
        total += sum(((a-b)**2 for a, b in zip(block, previous)), Fraction(0))
        previous = block
    return total


def sat(z: Fraction) -> Fraction:
    return z / (1 + abs(z))


def vector_field(x: Tuple[Tuple[Fraction, ...], ...], model: Dict[str, Any]) -> Tuple[Tuple[Fraction, ...], ...]:
    alpha, beta, kappa, omega = (model[k] for k in ("alpha", "beta", "kappa", "omega"))
    n = len(x)
    result = []
    for index, block in enumerate(x):
        before = x[index-1] if index > 0 else ZERO
        after = x[index+1] if index+1 < n else ZERO
        cross = [Fraction(0)] * 6
        for pair, w in enumerate(omega):
            a = 2*pair
            cross[a] = -w * block[a+1]
            cross[a+1] = w * block[a]
        result.append(tuple(-alpha*z + kappa*(before[j]-2*z+after[j]) + cross[j] + beta*sat(z)
                            for j, z in enumerate(block)))
    return tuple(result)


def dot(a: Sequence[Sequence[Fraction]], b: Sequence[Sequence[Fraction]]) -> Fraction:
    return sum((u*v for aa, bb in zip(a,b) for u,v in zip(aa,bb)), Fraction(0))


def exact_dissipation_check(x: Tuple[Tuple[Fraction, ...], ...], model: Dict[str, Any]) -> Fraction:
    """Prove <x,F(x)> = -alpha||x||^2 - kappa||grad x||^2 + beta sum z*sat(z)."""
    d = dot(x, vector_field(x, model))
    rhs = (-model["alpha"]*norm2(x) - model["kappa"]*gradient2(x)
           + model["beta"]*sum((z*sat(z) for row in x for z in row), Fraction(0)))
    if d != rhs:
        raise ArithmeticError("exact energy identity failed")
    margin = -model["delta"] * norm2(x) - d
    if margin < 0:
        raise ArithmeticError("exact energy dissipation inequality failed")
    return margin


def boundary_residual_squared(x: Tuple[Tuple[Fraction, ...], ...], model: Dict[str, Any]) -> Fraction:
    """Exact squared norm of continuous generator's omitted mode n+1."""
    return model["kappa"] ** 2 * sum((z*z for z in x[-1]), Fraction(0))


def _state_strings(state: Sequence[Sequence[Fraction]]) -> List[List[str]]:
    return [[str(z) for z in row] for row in state]


def _canonical_problem(payload: Any):
    if not isinstance(payload, dict) or set(payload) != {"model", "modes", "initial", "steps"}:
        raise ValueError("problem keys must be model, modes, initial, steps")
    modes = payload["modes"]
    steps = payload["steps"]
    if type(modes) is not int or not (1 <= modes <= MAX_MODES):
        raise ValueError("modes must be an integer 1..128")
    if type(steps) is not int or not (0 <= steps <= MAX_STEPS):
        raise ValueError("steps must be an integer 0..8")
    model = param_model(payload["model"])
    state = initial_state(payload["initial"], modes)
    canonical = {
        "model": {key: str(model[key]) for key in ("alpha", "beta", "kappa", "dt")},
        "modes": modes,
        "initial": _state_strings(state),
        "steps": steps,
    }
    canonical["model"]["omega"] = [str(w) for w in model["omega"]]
    return canonical, model, state


def _ensure_bit_cap(state: Sequence[Sequence[Fraction]]):
    if any(z.numerator.bit_length() > MAX_BITS or z.denominator.bit_length() > MAX_BITS
           for row in state for z in row):
        raise ValueError("rational complexity cap reached; reduce steps or parameters")


def analyze(payload: Any) -> Dict[str, Any]:
    canonical, model, state = _canonical_problem(payload)
    h, q, rho, kappa = (model[k] for k in ("dt", "q", "rho", "kappa"))
    support = max((i+1 for i, row in enumerate(state) if any(row)), default=0)
    error_bound = Fraction(0)
    trajectory = []
    initial_energy = norm2(state)
    for step in range(canonical["steps"]+1):
        _ensure_bit_cap(state)
        current_energy = norm2(state)
        margin = exact_dissipation_check(state, model)
        residual_squared = boundary_residual_squared(state, model)
        trajectory.append({
            "step": step,
            "squared_norm": str(current_energy),
            "energy_dissipation_margin": str(margin),
            "boundary_generator_residual_squared": str(residual_squared),
            "infinite_euler_truncation_error_upper_bound": str(error_bound),
        })
        if step == canonical["steps"]:
            break
        derivative = vector_field(state, model)
        next_state = tuple(tuple(z + h * dz for z, dz in zip(row, grad))
                           for row, grad in zip(state, derivative))
        _ensure_bit_cap(next_state)
        next_energy = norm2(next_state)
        if next_energy > q * current_energy:
            raise ArithmeticError("Euler stability inequality failed")
        # q <= rho**2 follows from ((1-q)/2)**2 >= 0.
        # The missing infinite Euler mode is h*kappa*state[-1].
        error_bound = rho*error_bound + h*kappa*sum((abs(z) for z in state[-1]), Fraction(0))
        state = next_state
    delta, L = model["delta"], model["L"]
    theorem = {
        "space": "ell2(N;R^6), Dirichlet left boundary X_0=0",
        "saturation": "sat(z)=z/(1+abs(z)), applied componentwise",
        "dissipation_rate_lower_bound": str(delta),
        "vector_field_global_lipschitz_upper_bound": str(L),
        "continuous_norm_bound": "||X(t)|| <= exp(-(alpha-beta)*t)*||X(0)||, for U=0",
        "continuous_forced_norm_bound": "||X(t)|| <= exp(-delta*t)*||X0|| + integral_0^t exp(-delta*(t-s))*||U(s)|| ds",
        "finite_dissipation_identity": "<X,Delta X>=-sum_{j=0}^{n}||X_(j+1)-X_j||^2; X0=X_(n+1)=0",
        "omega_skew_symmetric": True,
        "global_wellposedness": "analytic theorem under globally Lipschitz vector field and locally integrable H forcing",
        "euler_squared_norm_factor_upper_bound": str(q),
        "euler_norm_factor_rational_upper_bound": str(rho),
        "euler_strict_contraction": True,
    }
    report = {
        "status": "CERTIFIED_SIX_CHANNEL_HILBERT_MODEL",
        "interpretation": "mathematical abstraction; not physical biocomputing validation",
        "infinite_dimension": "countably infinite six-channel layers with finite ell2 energy",
        "finite_dimensions": 6 * canonical["modes"],
        "channels": list(CHANNELS),
        "input": canonical,
        "theorem": theorem,
        "initial_support_modes": support,
        "exact_infinite_euler_horizon": canonical["modes"] >= support + canonical["steps"],
        "trajectory": trajectory,
        "final_state": _state_strings(state),
        "initial_squared_norm": str(initial_energy),
        "final_squared_norm": str(norm2(state)),
        "external_calls": 0,
        "qualification": "finite Euler trace is not an exact continuous-time trajectory; infinite-space claims rely on analysis",
    }
    canonical_text = json.dumps(report, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    report["evidence_sha256"] = hashlib.sha256(canonical_text.encode("ascii")).hexdigest()
    return report


def hierarchy(payload: Any, levels: Sequence[int]) -> Dict[str, Any]:
    if not isinstance(levels, list) or not levels or len(levels) > 12 or any(type(n) is not int or n < 1 or n > MAX_MODES for n in levels):
        raise ValueError("levels must be at most 12 mode counts between 1 and 128")
    if len(set(levels)) != len(levels) or list(levels) != sorted(levels):
        raise ValueError("levels must be distinct and increasing")
    if not isinstance(payload, dict) or set(payload) != {"model", "initial", "steps"}:
        raise ValueError("hierarchy keys must be model, initial, steps")
    if not isinstance(payload["initial"], list) or len(payload["initial"]) > levels[0]:
        raise ValueError("initial support must fit the smallest level")
    result = []
    for modes in levels:
        certificate = analyze(dict(payload, modes=modes))
        result.append({
            "modes": modes,
            "dimensions": 6 * modes,
            "final_squared_norm": certificate["final_squared_norm"],
            "finite_euler_is_exact_in_infinite_space_for_horizon": certificate["exact_infinite_euler_horizon"],
            "euler_error_upper_bound": certificate["trajectory"][-1]["infinite_euler_truncation_error_upper_bound"],
            "certificate_sha256": certificate["evidence_sha256"],
        })
    return {"status": "FINITE_HIERARCHY_WITH_INFINITE_DIMENSION_THEOREM", "layers": result,
            "warning": "No finite run computes all infinitely many coordinates or validates physical biology."}


def verify(report: Any) -> bool:
    try:
        return isinstance(report, dict) and report == analyze(report["input"])
    except (ValueError, TypeError, KeyError, ArithmeticError, OverflowError):
        return False


def load_json(path: Path) -> Any:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("JSON input exceeds 64KiB")
    return json.loads(path.read_text(encoding="utf-8"))


def demo_problem() -> Dict[str, Any]:
    return {"model": {"alpha": "3", "beta": "1", "kappa": "1/4",
                      "omega": ["1/4", "1/8", "1/16"], "dt": "1/16"},
            "modes": 6, "initial": [[1, 0, 0, 0, 0, 0]], "steps": 3}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    sub.add_parser("demo", help="exact 36D toy model with infinite-space theorem")
    for action in ("analyze", "verify", "hierarchy"):
        cmd = sub.add_parser(action)
        cmd.add_argument("file", type=Path)
        if action == "hierarchy":
            cmd.add_argument("--levels", default="1,2,4,8,16", help="comma-separated increasing mode counts")
    args = parser.parse_args(argv)
    try:
        if args.action == "demo":
            result = analyze(demo_problem())
        elif args.action == "verify":
            result = {"status": "VERIFIED" if verify(load_json(args.file)) else "INVALID"}
        elif args.action == "hierarchy":
            levels = [int(s) for s in args.levels.split(",")]
            result = hierarchy(load_json(args.file), levels)
        else:
            result = analyze(load_json(args.file))
        print(json.dumps(result, indent=2, sort_keys=True, ensure_ascii=True))
        return 0 if result["status"] != "INVALID" else 1
    except (ValueError, TypeError, OSError, KeyError, ArithmeticError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "kind": type(exc).__name__, "message": str(exc)[:160]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
