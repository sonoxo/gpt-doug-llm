"""Exact global-vs-blow-up dichotomy for convex rational quadratic scalar ODEs.

For x'=A*x^2+B*x+C, A>0, and rational x(0)=x0>0, exactly
one applies: finite-time +infinity blow-up, global bounded solution, or
constant equilibrium. Every decision comes with a recomputable exact witness.
This is a classical Riccati phase-line fact, not a result for fluid PDEs.
"""

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

from . import singularity as core
from . import singularity_sos as sos

_SCOPE = "convex rational quadratic autonomous scalar ODE; not a PDE result"


def _validate(coefficients, initial):
    poly = core.polynomial(coefficients)
    x0 = core.rational(initial)
    if len(poly) != 3 or poly[2] <= 0 or x0 <= 0:
        raise ValueError("requires quadratic coefficient A>0 and rational x0>0")
    return poly, x0


def optimal_quadratic_rate(coefficients, initial):
    """Exact rational infimum of P(x)/x^2 over x>=x0>0.

    Substitute y=1/x: the ratio is A+B*y+C*y^2 on y in [0,1/x0].
    Check the endpoints and the interior quadratic vertex (when C>0).
    """
    (c, b, a), x0 = _validate(coefficients, initial)
    rates = [a, core.evaluate((c, b, a), x0) / (x0 * x0)]
    if c > 0:
        vertex = -b / (2 * c)
        if 0 < vertex < 1 / x0:
            rates.append(a - b * b / (4 * c))
    return min(rates)


def _equilibrium(poly, x0):
    return {
        "status": "EQUILIBRIUM_CERTIFIED",
        "coefficients_ascending": [str(c) for c in poly],
        "initial": str(x0),
        "derivative_at_initial": "0",
        "conclusion": "x(t)=x0 for all t>=0",
        "scope": _SCOPE,
    }


def decide(coefficients, initial):
    poly, x0 = _validate(coefficients, initial)
    p0 = core.evaluate(poly, x0)
    if p0 == 0:
        return _equilibrium(poly, x0)
    minimum_rate = optimal_quadratic_rate(poly, x0)
    if minimum_rate > 0:
        cert = sos.synthesize(poly, x0, 2, minimum_rate)
        if cert is None:
            raise ArithmeticError("exact positivity decomposition unexpectedly failed")
        return cert
    c, b, a = poly
    if p0 < 0:
        # Cauchy root bound is stronger than necessary but gives an exact
        # point below every real root of A*x^2+B*x+C.
        root_bound = 1 + max(abs(b) / a, abs(c) / a)
        lower, upper = -root_bound, x0
    else:
        # P(x0)>0 but P becomes nonpositive to the right. Vertex gives
        # an exact rational upper barrier (the stable phase-line region).
        lower, upper = x0, -b / (2 * a)
    cert = core.certify_bounded(poly, x0, lower, upper)
    if cert is None:
        raise ArithmeticError("exact invariant interval construction failed")
    return cert


def verify(cert):
    """Independent replay using exact arithmetic; no numeric root solver."""
    if not isinstance(cert, dict):
        return False
    if sos.verify(cert):
        # sos.verify checks only SOS, not whether input polynomial quadratic.
        try:
            _validate(cert["coefficients_ascending"], cert["initial"])
            return cert == decide(cert["coefficients_ascending"], cert["initial"])
        except (KeyError, ArithmeticError, TypeError, ValueError):
            return False
    if core.verify(cert):
        try:
            _validate(cert["coefficients_ascending"], cert["initial"])
            return cert == decide(cert["coefficients_ascending"], cert["initial"])
        except (KeyError, ArithmeticError, TypeError, ValueError):
            return False
    if cert.get("status") != "EQUILIBRIUM_CERTIFIED":
        return False
    try:
        poly, x0 = _validate(cert["coefficients_ascending"], cert["initial"])
        return core.evaluate(poly, x0) == 0 and cert == _equilibrium(poly, x0)
    except (KeyError, ValueError, TypeError):
        return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prove = sub.add_parser("decide")
    prove.add_argument("--coeffs", required=True, help="C,B,A low to high")
    prove.add_argument("--x0", required=True)
    sub.add_parser("verify").add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "decide":
            cert = decide([c.strip() for c in args.coeffs.split(",")], args.x0)
            code = 0 if verify(cert) else 1
        else:
            cert = json.loads(args.file.read_text(encoding="utf-8"))
            code = 0 if verify(cert) else 1
            cert = {"status": "VERIFIED" if code == 0 else "INVALID"}
        print(json.dumps(cert, indent=2, sort_keys=True))
        return code
    except (OSError, ValueError, TypeError, ArithmeticError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
