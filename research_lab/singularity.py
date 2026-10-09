"""Offline, exact-arithmetic certificates for scalar polynomial ODEs.

This is a research benchmark, NOT a solution to the 3D Navier-Stokes problem.
All calculations use rational arithmetic; numerical sampling is never treated as
proof. The sufficient criteria are conservative, so INCONCLUSIVE means only
that the chosen certificates did not apply.

Run: python3 -m research_lab.singularity demo
"""

import argparse
import json
import math
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple

_MAX_DEGREE = 24


def rational(value: Any) -> Fraction:
    """Parse exact rational inputs; silently rounded floats are forbidden."""
    if isinstance(value, bool) or isinstance(value, float):
        raise ValueError("use an integer or exact rational string, never a float")
    if isinstance(value, (int, str, Fraction)):
        try:
            return Fraction(value)
        except (ValueError, ZeroDivisionError) as exc:
            raise ValueError("invalid rational number") from exc
    raise ValueError("rational value must be an int, string or Fraction")


def polynomial(values: Iterable[Any]) -> Tuple[Fraction, ...]:
    if isinstance(values, (str, bytes)):
        raise ValueError("polynomial requires a sequence of coefficients")
    coeffs = tuple(rational(v) for v in values)
    if not coeffs or len(coeffs) - 1 > _MAX_DEGREE:
        raise ValueError("polynomial must have 1 to 25 coefficients")
    while len(coeffs) > 1 and coeffs[-1] == 0:
        coeffs = coeffs[:-1]
    return coeffs


def evaluate(coeffs: Iterable[Any], value: Any) -> Fraction:
    """Evaluate sum(c_i*x**i) with Horner's rule, exactly."""
    x = rational(value)
    total = Fraction(0)
    for coeff in reversed(polynomial(coeffs)):
        total = total * x + coeff
    return total


def translate(coeffs: Iterable[Any], origin: Any) -> Tuple[Fraction, ...]:
    """Exact coefficients of P(origin+z), in increasing powers of z."""
    poly = polynomial(coeffs)
    x0 = rational(origin)
    return tuple(
        sum(
            (poly[j] * math.comb(j, i) * x0 ** (j - i)
             for j in range(i, len(poly))),
            Fraction(0),
        )
        for i in range(len(poly))
    )


def _gap(poly: Tuple[Fraction, ...], exponent: int, rate: Fraction):
    degree = max(len(poly) - 1, exponent)
    padded = list(poly) + [Fraction(0)] * (degree + 1 - len(poly))
    padded[exponent] -= rate
    return tuple(padded)


def certify_blowup(
    coefficients: Iterable[Any], initial: Any, exponent: int, rate: Any
) -> Optional[Dict[str, Any]]:
    """Prove finite-time blow-up via P(x)>=a*x**p for every x>=x0>0.

    Sufficient exact certificate: every coefficient of
    P(x0+z)-a*(x0+z)**p is nonnegative, so the gap is >=0 for z>=0.
    Then (x**(1-p))' <= -(p-1)*a and T <= x0**(1-p)/(a*(p-1)).
    """
    poly = polynomial(coefficients)
    x0 = rational(initial)
    a = rational(rate)
    if isinstance(exponent, bool) or not isinstance(exponent, int):
        raise ValueError("exponent must be an integer")
    if not 2 <= exponent <= _MAX_DEGREE:
        raise ValueError("exponent must be between 2 and 24")
    if x0 <= 0 or a <= 0:
        raise ValueError("positive initial value and comparison rate required")
    if exponent > len(poly) - 1:
        return None
    gap = translate(_gap(poly, exponent, a), x0)
    if any(value < 0 for value in gap):
        return None
    upper = Fraction(1, 1) / (a * (exponent - 1) * x0 ** (exponent - 1))
    return {
        "status": "BLOWUP_CERTIFIED",
        "equation": "x'=P(x), x(0)=x0",
        "coefficients_ascending": [str(c) for c in poly],
        "initial": str(x0),
        "comparison_exponent": exponent,
        "comparison_rate": str(a),
        "shifted_gap_coefficients": [str(c) for c in gap],
        "blowup_time_upper_bound": str(upper),
        "scope": "scalar autonomous polynomial ODE; exact sufficient comparison proof",
    }


def certify_bounded(
    coefficients: Iterable[Any], initial: Any, lower: Any, upper: Any
) -> Optional[Dict[str, Any]]:
    """Prove a closed interval is positively invariant, hence global existence.

    If P(lo)>=0 and P(hi)<=0, the polynomial vector field points inward at
    each boundary. Local uniqueness and compact continuation imply the result.
    """
    poly = polynomial(coefficients)
    x0, lo, hi = rational(initial), rational(lower), rational(upper)
    if lo >= hi:
        raise ValueError("lower must be strictly less than upper")
    if not lo <= x0 <= hi:
        return None
    left, right = evaluate(poly, lo), evaluate(poly, hi)
    if left < 0 or right > 0:
        return None
    return {
        "status": "GLOBALLY_BOUNDED_CERTIFIED",
        "equation": "x'=P(x), x(0)=x0",
        "coefficients_ascending": [str(c) for c in poly],
        "initial": str(x0),
        "interval_lower": str(lo),
        "interval_upper": str(hi),
        "vector_field_at_lower": str(left),
        "vector_field_at_upper": str(right),
        "scope": "scalar autonomous polynomial ODE; forward invariant interval proof",
    }


def verify(certificate: Mapping[str, Any]) -> bool:
    """Replay the exact sufficient conditions and compare the entire witness."""
    if not isinstance(certificate, Mapping):
        return False
    try:
        kind = certificate.get("status")
        poly = certificate["coefficients_ascending"]
        x0 = certificate["initial"]
        if kind == "BLOWUP_CERTIFIED":
            expected = certify_blowup(
                poly, x0, certificate["comparison_exponent"],
                certificate["comparison_rate"],
            )
        elif kind == "GLOBALLY_BOUNDED_CERTIFIED":
            expected = certify_bounded(
                poly, x0, certificate["interval_lower"],
                certificate["interval_upper"],
            )
        else:
            return False
        return expected is not None and dict(certificate) == expected
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def scan(coefficients: Iterable[Any], initial: Any) -> Dict[str, Any]:
    """Search a small fixed catalog of witnesses; no solver completeness claim."""
    poly = polynomial(coefficients)
    x0 = rational(initial)
    if x0 > 0:
        for p in range(2, min(len(poly) - 1, 8) + 1):
            for denominator in (1, 2, 4, 8, 16, 32, 64):
                certificate = certify_blowup(poly, x0, p, Fraction(1, denominator))
                if certificate is not None:
                    return certificate
    for radius in (1, 2, 4, 8, 16, 32, 64):
        certificate = certify_bounded(poly, x0, -radius, radius)
        if certificate is not None:
            return certificate
    return {
        "status": "INCONCLUSIVE",
        "coefficients_ascending": [str(c) for c in poly],
        "initial": str(x0),
        "scope": "no witness found in finite search; NOT a claim of regularity or blow-up",
    }


def _coefficients(text: str) -> Tuple[Fraction, ...]:
    return polynomial(part.strip() for part in text.split(","))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    cmds = parser.add_subparsers(dest="action", required=True)
    cmds.add_parser("demo", help="run known finite-time and globally bounded examples")
    for name in ("blowup", "bounded", "scan"):
        sub = cmds.add_parser(name)
        sub.add_argument("--coeffs", required=True, help="P(x) coefficients low to high")
        sub.add_argument("--x0", required=True, help="exact rational initial value")
        if name == "blowup":
            sub.add_argument("--p", required=True, type=int)
            sub.add_argument("--a", required=True, help="exact rational comparison rate")
        if name == "bounded":
            sub.add_argument("--lo", required=True)
            sub.add_argument("--hi", required=True)
    sub = cmds.add_parser("verify", help="re-check a saved JSON certificate")
    sub.add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.action == "demo":
            result = {
                "quadratic": certify_blowup([2, -3, 1], 4, 2, "1/4"),
                "restoring": certify_bounded([0, 1, 0, -1], "1/2", -1, 1),
                "negative_quadratic_scan": scan([0, 0, -1], 1),
            }
            status = 0
        elif args.action == "verify":
            data = json.loads(args.file.read_text(encoding="utf-8"))
            valid = verify(data)
            result = {"status": "VERIFIED" if valid else "INVALID"}
            status = 0 if valid else 1
        else:
            coeffs = _coefficients(args.coeffs)
            if args.action == "blowup":
                result = certify_blowup(coeffs, args.x0, args.p, args.a)
            elif args.action == "bounded":
                result = certify_bounded(coeffs, args.x0, args.lo, args.hi)
            else:
                result = scan(coeffs, args.x0)
            if result is None:
                result = {"status": "INCONCLUSIVE", "scope": "certificate failed"}
            status = 1 if result["status"] == "INCONCLUSIVE" else 0
        print(json.dumps(result, sort_keys=True, indent=2, allow_nan=False))
        return status
    except (ValueError, TypeError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
