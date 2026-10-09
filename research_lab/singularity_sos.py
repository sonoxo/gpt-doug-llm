"""Exact rational sum-of-squares witnesses for finite-time scalar ODE blow-up.

For z >= 0, each weighted square w*q(z)^2 and z*w*q(z)^2 is
nonnegative. Exact polynomial identity therefore certifies the differential
inequality P(x) >= a*x**p for all x>=x0, which gives finite-time blow-up.

An incomplete deterministic synthesizer generates some witnesses; the
independent checker uses only rational polynomial arithmetic. No claim is made
about Navier-Stokes, new theorems, or novelty.
"""

import argparse
import json
import sys
from fractions import Fraction
from pathlib import Path

from . import singularity as core

_MAX_TERMS = 64
_SCOPE = "scalar polynomial ODE, rational SOS half-line proof; not a PDE result"


def trim(values):
    coeffs = tuple(values)
    while len(coeffs) > 1 and coeffs[-1] == 0:
        coeffs = coeffs[:-1]
    return coeffs or (Fraction(0),)


def plus(a, b):
    out = [Fraction(0)] * max(len(a), len(b))
    for i, value in enumerate(a):
        out[i] += value
    for i, value in enumerate(b):
        out[i] += value
    return trim(out)


def minus(a, b):
    return plus(a, [-v for v in b])


def times(a, b):
    out = [Fraction(0)] * (len(a) + len(b) - 1)
    for i, left in enumerate(a):
        for j, right in enumerate(b):
            out[i + j] += left * right
    return trim(out)


def shifted_gap(coefficients, initial, exponent, rate):
    poly = core.polynomial(coefficients)
    x0, a = core.rational(initial), core.rational(rate)
    if type(exponent) is not int or not 2 <= exponent <= 24:
        raise ValueError("comparison exponent must be an integer between 2 and 24")
    if x0 <= 0 or a <= 0:
        raise ValueError("positive initial state and comparison rate required")
    if exponent > len(poly) - 1:
        # This convenient SOS search intentionally handles only polynomial
        # degrees >= comparison exponent.
        raise ValueError("polynomial degree must be at least comparison exponent")
    adjusted = list(poly)
    adjusted[exponent] -= a
    return core.translate(adjusted, x0)


def _term(weight, poly):
    weight = core.rational(weight)
    if weight <= 0:
        raise ValueError("SOS weights must be strictly positive")
    coeffs = core.polynomial(poly)
    if coeffs == (0,):
        raise ValueError("zero SOS polynomials are not accepted")
    return {"weight": str(weight), "polynomial_ascending": [str(v) for v in coeffs]}


def _canonicalize(terms):
    if not isinstance(terms, (list, tuple)) or len(terms) > _MAX_TERMS:
        raise ValueError("expected a sequence of at most 64 SOS terms")
    canonical = []
    for item in terms:
        if not isinstance(item, dict) or set(item) != {"weight", "polynomial_ascending"}:
            raise ValueError("SOS terms must contain only weight and polynomial_ascending")
        canonical.append(_term(item["weight"], item["polynomial_ascending"]))
    return canonical


def _evaluate_terms(sos_terms, z_sos_terms):
    total = (Fraction(0),)
    for z_power, terms in [(0, sos_terms), (1, z_sos_terms)]:
        for item in terms:
            poly = core.polynomial(item["polynomial_ascending"])
            weight = core.rational(item["weight"])
            square = times(poly, poly)
            square = tuple([Fraction(0)] * z_power + [weight * c for c in square])
            total = plus(total, square)
    return total


def certify_sos(coefficients, initial, exponent, rate, sos_terms, z_sos_terms):
    """Return a certificate only if the exact weighted SOS identity holds."""
    poly = core.polynomial(coefficients)
    x0, a = core.rational(initial), core.rational(rate)
    gap = shifted_gap(poly, x0, exponent, a)
    sos, z_sos = _canonicalize(sos_terms), _canonicalize(z_sos_terms)
    if _evaluate_terms(sos, z_sos) != trim(gap):
        return None
    limit = Fraction(1) / (a * (exponent - 1) * x0 ** (exponent - 1))
    return {
        "status": "BLOWUP_CERTIFIED_SOS",
        "equation": "x'=P(x), x(0)=x0",
        "coefficients_ascending": [str(c) for c in poly],
        "initial": str(x0),
        "comparison_exponent": exponent,
        "comparison_rate": str(a),
        "shifted_gap_coefficients": [str(c) for c in trim(gap)],
        "sos_terms": sos,
        "z_sos_terms": z_sos,
        "blowup_time_upper_bound": str(limit),
        "scope": _SCOPE,
    }


def verify(certificate):
    """Recompute every exact identity and require canonical full-field equality."""
    if not isinstance(certificate, dict):
        return False
    try:
        if certificate.get("status") != "BLOWUP_CERTIFIED_SOS":
            return False
        expected = certify_sos(
            certificate["coefficients_ascending"],
            certificate["initial"],
            certificate["comparison_exponent"],
            certificate["comparison_rate"],
            certificate["sos_terms"],
            certificate["z_sos_terms"],
        )
        return expected is not None and certificate == expected
    except (KeyError, TypeError, ValueError, OverflowError):
        return False


def _monomial_sos(gap):
    sos, z_sos = [], []
    for degree, coeff in enumerate(gap):
        if coeff < 0:
            return None
        if coeff == 0:
            continue
        monomial = [0] * (degree // 2) + [1]
        term = _term(coeff, monomial)
        (z_sos if degree % 2 else sos).append(term)
    return sos, z_sos


def _quadratic_sos(gap):
    """Find a rational weighted-SOS representation of a nonnegative quadratic."""
    c, b, a = gap
    if a <= 0 or b >= 0 or c < 0:
        return None
    constant = c - b * b / (4 * a)
    if constant < 0:
        return None
    sos = [_term(a, [b / (2 * a), 1])]
    if constant > 0:
        sos.append(_term(constant, [1]))
    return sos, []


def _square_completion(gap, depth):
    """Extract one exact high-degree rational square and recurse on remainder.

    This algorithm is deliberately incomplete: it can fail even for positive
    polynomials. Every success is independently checked by certify_sos.
    """
    if depth >= 8:
        return None
    degree = len(gap) - 1
    if degree <= 2 or gap[-1] <= 0:
        return None
    odd = degree % 2
    half = degree // 2
    lead = gap[-1]
    square_base = [Fraction(0)] * (half + 1)
    square_base[half] = Fraction(1)
    for k in range(1, half + 1):
        idx = half - k
        known = sum(
            square_base[i] * square_base[j]
            for i in range(idx + 1, half + 1)
            for j in range(idx + 1, half + 1)
            if i + j == 2 * half - k
        )
        square_base[idx] = (gap[degree - k] / lead - known) / 2
    main_square = times(square_base, square_base)
    main_square = trim(([Fraction(0)] * odd) + [lead * v for v in main_square])
    residual = minus(gap, main_square)
    smaller = _synthesize(residual, depth + 1)
    if smaller is None:
        return None
    sos, z_sos = smaller
    if odd:
        z_sos.insert(0, _term(lead, square_base))
    else:
        sos.insert(0, _term(lead, square_base))
    return sos, z_sos


def _synthesize(gap, depth=0):
    gap = trim(gap)
    direct = _monomial_sos(gap)
    if direct is not None:
        return direct
    if len(gap) == 3:
        return _quadratic_sos(gap)
    return _square_completion(gap, depth)


def synthesize(coefficients, initial, exponent, rate):
    """Search constructively, and refuse to certify without identity checking."""
    gap = shifted_gap(coefficients, initial, exponent, rate)
    pair = _synthesize(gap)
    if pair is None:
        return None
    return certify_sos(coefficients, initial, exponent, rate, *pair)


def scan(coefficients, initial):
    """Finite deterministic witness search; absence of a proof is inconclusive."""
    poly = core.polynomial(coefficients)
    x0 = core.rational(initial)
    if x0 > 0:
        for p in range(2, min(len(poly) - 1, 8) + 1):
            for rate in [Fraction(2), Fraction(1), Fraction(1, 2), Fraction(1, 4),
                         Fraction(1, 8), Fraction(1, 16), Fraction(1, 32)]:
                cert = synthesize(poly, x0, p, rate)
                if cert is not None:
                    return cert
    return {
        "status": "INCONCLUSIVE",
        "coefficients_ascending": [str(c) for c in poly],
        "initial": str(x0),
        "scope": "finite SOS witness search; no regularity or blow-up conclusion",
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest="command", required=True)
    modes.add_parser("demo")
    for name in ("prove", "scan"):
        sub = modes.add_parser(name)
        sub.add_argument("--coeffs", required=True, help="coefficients, low to high")
        sub.add_argument("--x0", required=True)
        if name == "prove":
            sub.add_argument("--p", required=True, type=int)
            sub.add_argument("--a", required=True)
    modes.add_parser("verify").add_argument("file", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            prior = core.certify_blowup([4, -4, 2], 1, 2, 1)
            result = {
                "previous_coefficient_method": "INCONCLUSIVE" if prior is None else "CERTIFIED",
                "new_sos_certificate": synthesize([4, -4, 2], 1, 2, 1),
            }
            code = 0 if prior is None and verify(result["new_sos_certificate"]) else 1
        elif args.command == "verify":
            cert = json.loads(args.file.read_text(encoding="utf-8"))
            valid = verify(cert)
            result = {"status": "VERIFIED" if valid else "INVALID"}
            code = 0 if valid else 1
        else:
            coeffs = core.polynomial(item.strip() for item in args.coeffs.split(","))
            if args.command == "prove":
                result = synthesize(coeffs, args.x0, args.p, args.a)
            else:
                result = scan(coeffs, args.x0)
            if result is None:
                result = {"status": "INCONCLUSIVE", "scope": "no exact SOS witness found"}
            code = 1 if result["status"] == "INCONCLUSIVE" else 0
        print(json.dumps(result, sort_keys=True, indent=2))
        return code
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "ERROR", "message": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
