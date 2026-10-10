"""Exact, bounded multidimensional mathematical research for linear systems.

No network or credentials. Certificates establish stability for a *specified*
rational linear system, never universal intelligence or open PDE theorems.

Discrete: x[k+1] = A x[k].  Continuous: x'(t) = A x(t).
Proof: find rational symmetric positive-definite P with respectively
P - A.T P A = I or -(A.T P + P A) = I.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

MAX_DIM = 6
MAX_GRID_EVALUATIONS = 100000
MAX_RADIUS = 5
MAX_INPUT_BYTES = 65536

Matrix = Tuple[Tuple[Fraction, ...], ...]


def fraction(value: Any) -> Fraction:
    """Parse exact rational strings/integers. Never silently round a float."""
    if isinstance(value, bool) or isinstance(value, float) or not isinstance(value, (str, int)):
        raise ValueError("coefficients must be integers or exact rational strings")
    if isinstance(value, str) and (not value or len(value) > 48):
        raise ValueError("rational token length is out of bounds")
    try:
        out = Fraction(value)
    except (ValueError, ZeroDivisionError, TypeError) as exc:
        raise ValueError("invalid rational coefficient") from exc
    if abs(out.numerator) > 1000000 or out.denominator > 1000000:
        raise ValueError("coefficient magnitude or denominator exceeds cap")
    return out


def matrix(value: Any) -> Matrix:
    if not isinstance(value, list) or not 1 <= len(value) <= MAX_DIM:
        raise ValueError("matrix must be a list of 1..6 rows")
    n = len(value)
    if any(not isinstance(row, list) or len(row) != n for row in value):
        raise ValueError("matrix must be square")
    return tuple(tuple(fraction(x) for x in row) for row in value)


def as_strings(A: Matrix) -> List[List[str]]:
    return [[str(value) for value in row] for row in A]


def identity(n: int) -> Matrix:
    return tuple(tuple(Fraction(i == j) for j in range(n)) for i in range(n))


def transpose(A: Matrix) -> Matrix:
    return tuple(zip(*A))


def mult(A: Matrix, B: Matrix) -> Matrix:
    n = len(A)
    return tuple(tuple(sum((A[i][k] * B[k][j] for k in range(n)), Fraction(0))
                       for j in range(n)) for i in range(n))


def add(A: Matrix, B: Matrix, scale: int = 1) -> Matrix:
    return tuple(tuple(a + scale * b for a, b in zip(ar, br))
                 for ar, br in zip(A, B))


def determinant(A: Matrix) -> Fraction:
    work = [list(row) for row in A]
    n = len(A)
    determinant_value = Fraction(1)
    for col in range(n):
        pivot = next((row for row in range(col, n) if work[row][col]), None)
        if pivot is None:
            return Fraction(0)
        if pivot != col:
            work[col], work[pivot] = work[pivot], work[col]
            determinant_value = -determinant_value
        val = work[col][col]
        determinant_value *= val
        for row in range(col + 1, n):
            factor = work[row][col] / val
            for j in range(col + 1, n):
                work[row][j] -= factor * work[col][j]
            work[row][col] = Fraction(0)
    return determinant_value


def positive_definite(P: Matrix) -> bool:
    if any(P[i][j] != P[j][i] for i in range(len(P)) for j in range(len(P))):
        return False
    return all(determinant(tuple(tuple(row[:k]) for row in P[:k])) > 0
               for k in range(1, len(P) + 1))


def solve_linear(augmented: List[List[Fraction]]) -> Optional[List[Fraction]]:
    """Exact Gaussian elimination; returns None when not uniquely soluble."""
    n = len(augmented)
    rows = [list(row) for row in augmented]
    for col in range(n):
        pivot = next((i for i in range(col, n) if rows[i][col]), None)
        if pivot is None:
            return None
        rows[col], rows[pivot] = rows[pivot], rows[col]
        scale = rows[col][col]
        rows[col] = [c / scale for c in rows[col]]
        for i in range(n):
            if i == col:
                continue
            factor = rows[i][col]
            if factor:
                rows[i] = [v - factor * pv for v, pv in zip(rows[i], rows[col])]
    return [row[-1] for row in rows]


def lyapunov_operator(A: Matrix, P: Matrix, mode: str) -> Matrix:
    AT = transpose(A)
    if mode == "discrete":
        return add(P, mult(mult(AT, P), A), -1)
    return add(mult(AT, P), mult(P, A), 1)


def solve_lyapunov(A: Matrix, mode: str) -> Optional[Matrix]:
    """Solve the symmetric Lyapunov system by exact rational elimination."""
    if mode not in ("discrete", "continuous"):
        raise ValueError("mode must be discrete or continuous")
    n = len(A)
    positions = [(i, j) for i in range(n) for j in range(i, n)]
    columns = []
    for i, j in positions:
        B = [[Fraction(0) for _ in range(n)] for _ in range(n)]
        B[i][j] = Fraction(1)
        B[j][i] = Fraction(1)
        columns.append(lyapunov_operator(A, tuple(tuple(r) for r in B), mode))
    rows = []
    for i, j in positions:
        right = Fraction(i == j) * (1 if mode == "discrete" else -1)
        rows.append([C[i][j] for C in columns] + [right])
    solution = solve_linear(rows)
    if solution is None:
        return None
    P = [[Fraction(0) for _ in range(n)] for _ in range(n)]
    for (i, j), value in zip(positions, solution):
        P[i][j] = P[j][i] = value
    return tuple(tuple(row) for row in P)


def stability_proof(A: Matrix, mode: str) -> Dict[str, Any]:
    """Return exact proof, or honestly say INCONCLUSIVE."""
    P = solve_lyapunov(A, mode)
    target = identity(len(A))
    if mode == "continuous":
        target = tuple(tuple(-a for a in row) for row in target)
    if P is None or not positive_definite(P) or lyapunov_operator(A, P, mode) != target:
        return {"status": "INCONCLUSIVE", "reason": "no positive-definite exact Lyapunov witness"}
    trace = sum((P[i][i] for i in range(len(P))), Fraction(0))
    result = {
        "status": "PROVED_GLOBALLY_ASYMPTOTICALLY_STABLE",
        "certificate_type": "exact_rational_quadratic_lyapunov",
        "P": as_strings(P),
        "lyapunov_identity": "P-A^T P A=I" if mode == "discrete" else "A^T P+P A=-I",
        "leading_principal_minors": [str(determinant(tuple(tuple(row[:k]) for row in P[:k])))
                                     for k in range(1, len(P) + 1)],
        "trace_P": str(trace),
    }
    if mode == "discrete":
        result["certified_energy_step_factor_upper_bound"] = str(1 - 1 / trace)
    else:
        result["certified_energy_decay_exponent_lower_bound"] = str(1 / trace)
    return result


def growth(A: Matrix, mode: str, vector: Sequence[int]) -> Fraction:
    v = tuple(Fraction(x) for x in vector)
    Av = tuple(sum((a * b for a, b in zip(row, v)), Fraction(0)) for row in A)
    if mode == "discrete":
        return sum((x*x for x in Av), Fraction(0)) - sum((x*x for x in v), Fraction(0))
    return 2 * sum((v[i]*Av[i] for i in range(len(v))), Fraction(0))


def grid_search(A: Matrix, mode: str, radius: int, max_evaluations: int) -> Dict[str, Any]:
    """Bounded exhaustive search for Euclidean norm amplification witnesses."""
    if isinstance(radius, bool) or not isinstance(radius, int) or not 1 <= radius <= MAX_RADIUS:
        raise ValueError("radius must be an integer from 1 to 5")
    if (isinstance(max_evaluations, bool) or not isinstance(max_evaluations, int)
            or not 1 <= max_evaluations <= MAX_GRID_EVALUATIONS):
        raise ValueError("max_evaluations must be an integer from 1 to 100000")
    total_vectors = (2 * radius + 1) ** len(A) - 1
    checked = 0
    for vector in itertools.product(range(-radius, radius + 1), repeat=len(A)):
        if all(x == 0 for x in vector):
            continue
        if checked >= max_evaluations:
            break
        checked += 1
        delta = growth(A, mode, vector)
        if delta > 0:
            return {
                "status": "ONE_STEP_AMPLIFICATION_WITNESS",
                "vector": list(vector),
                "delta_euclidean_squared_norm": str(delta) if mode == "discrete" else None,
                "instantaneous_squared_norm_derivative": str(delta) if mode == "continuous" else None,
                "checked_vectors": checked,
                "total_vectors_in_box": total_vectors,
                "claim_limit": "Not a proof of long-term instability or finite-time blow-up",
            }
    return {
        "status": "NO_WITNESS_IN_FINITE_BOX" if checked == total_vectors else "SEARCH_LIMIT_REACHED",
        "checked_vectors": checked,
        "total_vectors_in_box": total_vectors,
        "claim_limit": "Finite testing cannot prove universal stability",
    }


def analyze(problem: Any) -> Dict[str, Any]:
    if not isinstance(problem, dict) or set(problem) - {"matrix", "mode", "radius", "max_evaluations"}:
        raise ValueError("only matrix, mode, radius and max_evaluations are supported")
    A = matrix(problem.get("matrix"))
    mode = problem.get("mode", "discrete")
    if not isinstance(mode, str) or mode not in {"discrete", "continuous"}:
        raise ValueError("mode must be discrete or continuous")
    radius = problem.get("radius", 2)
    max_evaluations = problem.get("max_evaluations", 10000)
    canonical_input = {"matrix": as_strings(A), "mode": mode, "radius": radius,
                       "max_evaluations": max_evaluations}
    witness = grid_search(A, mode, radius, max_evaluations)
    output: Dict[str, Any] = {
        "research_scope": "finite_dimensional_rational_linear_dynamics_only",
        "dimension": len(A),
        "input": canonical_input,
        "proof": stability_proof(A, mode),
        "bounded_exhaustive_search": witness,
        "external_access": "none",
        "caveat": "No claim about universal intelligence, arbitrary nonlinear systems or Navier-Stokes",
    }
    stable_json = json.dumps(output, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    output["evidence_sha256"] = hashlib.sha256(stable_json.encode("ascii")).hexdigest()
    return output


def verify(report: Any) -> bool:
    """Replay all exact calculations; reject any altered claim or model."""
    if not isinstance(report, dict) or not isinstance(report.get("input"), dict):
        return False
    try:
        return report == analyze(report["input"])
    except (ValueError, TypeError, KeyError, OverflowError):
        return False


def read_json(path: Path) -> Any:
    if path.stat().st_size > MAX_INPUT_BYTES:
        raise ValueError("file exceeds 64KiB input limit")
    return json.loads(path.read_text(encoding="utf-8"))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("demo", help="prove a stable but non-normal 2D example")
    p = sub.add_parser("analyze", help="analyze local JSON model")
    p.add_argument("file", type=Path)
    v = sub.add_parser("verify", help="replay a saved JSON result")
    v.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            ok = verify(read_json(args.file))
            print(json.dumps({"status": "VERIFIED" if ok else "INVALID"}, indent=2))
            return 0 if ok else 1
        problem = ({"matrix": [["1/2", "2"], ["0", "1/2"]], "mode": "discrete"}
                   if args.command == "demo" else read_json(args.file))
        result = analyze(problem)
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0 if result["proof"]["status"].startswith("PROVED") else 1
    except (ValueError, OSError, json.JSONDecodeError, TypeError) as exc:
        print(json.dumps({"status": "ERROR", "reason": type(exc).__name__}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
