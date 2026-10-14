"""Finite arithmetic research with independently replayed evidence.

These checks establish results only for their *explicit finite range*. They do
not prove Goldbach's conjecture, the Collatz conjecture or any open problem.
This module intentionally needs only Python's standard library and no network.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import math
import sys
from pathlib import Path
from typing import Any, Optional

SCHEMA = "gpt-doug.math-frontier.v1"
MAX_CASES = 2000
MAX_END = {"goldbach": 100_000, "collatz": 20_000}
DEFAULT_STEPS = 1500
MAX_STEPS = 5000
MAX_EVIDENCE_BYTES = 1_000_000


class EvidenceError(ValueError):
    """The finite research request or certificate is invalid."""


def _bounds(problem: str, start: int, end: int, max_steps: int) -> range:
    if not isinstance(problem, str) or problem not in MAX_END:
        raise EvidenceError("unsupported research problem")
    if any(type(v) is not int for v in (start, end, max_steps)):
        raise EvidenceError("bounds must be integers")
    if max_steps < 1 or max_steps > MAX_STEPS:
        raise EvidenceError("max_steps is outside the resource limit")
    low = 4 if problem == "goldbach" else 1
    if start < low or end < start or end > MAX_END[problem]:
        raise EvidenceError("range is outside the supported finite domain")
    if problem == "goldbach" and (start % 2 or end % 2):
        raise EvidenceError("Goldbach range endpoints must be even")
    span = range(start, end + 1, 2 if problem == "goldbach" else 1)
    if len(span) > MAX_CASES:
        raise EvidenceError("range exceeds the maximum number of cases")
    return span


def _sieve(n: int) -> bytearray:
    prime = bytearray(b"\x01") * (n + 1)
    prime[0:2] = b"\x00\x00"
    for p in range(2, math.isqrt(n) + 1):
        if prime[p]:
            prime[p * p:n + 1:p] = b"\x00" * ((n - p * p) // p + 1)
    return prime


def _trial_prime(n: int) -> bool:
    """Independent integer-division primality check (not the generator sieve)."""
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    for divisor in range(3, math.isqrt(n) + 1, 2):
        if n % divisor == 0:
            return False
    return True


def _collatz_candidate(n: int, max_steps: int) -> dict[str, Any]:
    value, peak, steps = n, n, 0
    while value != 1 and steps < max_steps:
        value = (3 * value + 1) if value % 2 else value // 2
        peak = max(peak, value)
        steps += 1
        if value.bit_length() > 4096:
            break
    return {"n": n, "steps": steps, "peak": peak, "reached_one": value == 1}


def _verify_collatz_case(n: int, row: Any, max_steps: int) -> None:
    if not isinstance(row, dict) or set(row) != {"n", "steps", "peak", "reached_one"}:
        raise EvidenceError("invalid Collatz certificate fields")
    if any(type(row[k]) is not int for k in ("n", "steps", "peak")) or type(row["reached_one"]) is not bool:
        raise EvidenceError("invalid Collatz certificate types")
    if row["n"] != n:
        raise EvidenceError("Collatz range ordering has been changed")
    # Replay rather than trusting the candidate's claimed termination or peak.
    cursor, maximum, iterations = n, n, 0
    while cursor != 1 and iterations < max_steps:
        if cursor & 1:
            cursor = cursor * 3 + 1
        else:
            cursor >>= 1
        maximum = cursor if cursor > maximum else maximum
        iterations += 1
        if cursor.bit_length() > 4096:
            break
    if (row["steps"], row["peak"], row["reached_one"]) != (iterations, maximum, cursor == 1):
        raise EvidenceError("Collatz trajectory did not replay")


def _verify_goldbach_case(n: int, row: Any) -> None:
    if not isinstance(row, dict) or set(row) != {"n", "p", "q"}:
        raise EvidenceError("invalid Goldbach certificate fields")
    if type(row["n"]) is not int or row["n"] != n:
        raise EvidenceError("Goldbach range ordering has been changed")
    p, q = row["p"], row["q"]
    if p is None and q is None:
        if any(_trial_prime(k) and _trial_prime(n - k) for k in range(2, n // 2 + 1)):
            raise EvidenceError("an omitted Goldbach pair exists")
        return
    if type(p) is not int or type(q) is not int or not (2 <= p <= q and p + q == n):
        raise EvidenceError("Goldbach decomposition is malformed")
    if not (_trial_prime(p) and _trial_prime(q)):
        raise EvidenceError("Goldbach factors are not both prime")
    if any(_trial_prime(k) and _trial_prime(n - k) for k in range(2, p)):
        raise EvidenceError("Goldbach minimal witness is incorrect")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("ascii")


def _digest(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical(payload)).hexdigest()


def verify_evidence(evidence: Any) -> dict[str, Any]:
    """Reject altered, omitted, reordered or mathematically wrong finite evidence."""
    fields = {"schema", "problem", "start", "end", "max_steps", "claim_scope", "status", "summary", "results", "sha256"}
    if not isinstance(evidence, dict) or set(evidence) != fields or evidence["schema"] != SCHEMA:
        raise EvidenceError("unknown certificate schema or fields")
    problem = evidence["problem"]
    expected = _bounds(problem, evidence["start"], evidence["end"], evidence["max_steps"])
    if evidence["claim_scope"] != "finite_range_only":
        raise EvidenceError("certificate makes an unsupported scope claim")
    rows = evidence["results"]
    if not isinstance(rows, list) or len(rows) != len(expected):
        raise EvidenceError("missing or duplicated certificate cases")
    review = []
    for n, row in zip(expected, rows):
        if problem == "goldbach":
            _verify_goldbach_case(n, row)
            if row["p"] is None:
                review.append(n)
        else:
            _verify_collatz_case(n, row, evidence["max_steps"])
            if not row["reached_one"]:
                review.append(n)
    summary = {"checked_cases": len(expected), "requires_review": review}
    status = "requires_review" if review else "verified_finite"
    if evidence["summary"] != summary or evidence["status"] != status:
        raise EvidenceError("certificate summary or status is incorrect")
    signature = evidence["sha256"]
    if not isinstance(signature, str) or len(signature) != 64:
        raise EvidenceError("certificate hash is missing")
    if not hmac.compare_digest(_digest({k: v for k, v in evidence.items() if k != "sha256"}), signature):
        raise EvidenceError("certificate digest mismatch")
    return {"verification": "passed", "status": status, "problem": problem, "scope": "finite_range_only", "checked_cases": len(expected), "sha256": signature}


def run_experiment(problem: str, start: int, end: int, *, max_steps: int = DEFAULT_STEPS) -> dict[str, Any]:
    values = _bounds(problem, start, end, max_steps)
    rows: list[dict[str, Any]] = []
    if problem == "goldbach":
        primes = _sieve(end)
        for n in values:
            match = next(((p, n - p) for p in range(2, n // 2 + 1) if primes[p] and primes[n - p]), None)
            rows.append({"n": n, "p": match[0] if match else None, "q": match[1] if match else None})
        review = [row["n"] for row in rows if row["p"] is None]
    else:
        rows = [_collatz_candidate(n, max_steps) for n in values]
        review = [row["n"] for row in rows if not row["reached_one"]]
    result = {"schema": SCHEMA, "problem": problem, "start": start, "end": end,
              "max_steps": max_steps, "claim_scope": "finite_range_only",
              "status": "requires_review" if review else "verified_finite",
              "summary": {"checked_cases": len(rows), "requires_review": review}, "results": rows}
    result["sha256"] = _digest(result)
    verify_evidence(result)  # fail closed before reporting even a finite result
    return result


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output = {}
    for name, value in pairs:
        if name in output:
            raise EvidenceError("duplicate JSON field")
        output[name] = value
    return output


def read_evidence(path: str) -> dict[str, Any]:
    source = Path(path)
    if not source.is_file() or source.stat().st_size > MAX_EVIDENCE_BYTES:
        raise EvidenceError("evidence file is missing or too large")
    try:
        return json.loads(source.read_text(encoding="utf-8"), object_pairs_hook=_unique_keys)
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("evidence is not valid JSON") from exc


def frontier_cli(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="gpt-doug math frontier")
    subs = parser.add_subparsers(dest="command", required=True)
    run = subs.add_parser("run", help="compute and independently replay bounded arithmetic")
    run.add_argument("problem", choices=sorted(MAX_END))
    run.add_argument("--start", type=int, required=True)
    run.add_argument("--end", type=int, required=True)
    run.add_argument("--max-steps", type=int, default=DEFAULT_STEPS)
    run.add_argument("--output", help="write a new JSON evidence file (never overwrite)")
    check = subs.add_parser("verify", help="independently replay a JSON certificate")
    check.add_argument("evidence_file")
    subs.add_parser("catalogue", help="show supported finite experimental targets")
    args = parser.parse_args(argv)
    try:
        if args.command == "run":
            result = run_experiment(args.problem, args.start, args.end, max_steps=args.max_steps)
            if args.output:
                with Path(args.output).open("x", encoding="utf-8") as handle:
                    json.dump(result, handle, sort_keys=True, indent=2)
                    handle.write("\n")
            report = verify_evidence(result)
            report["requires_review"] = result["summary"]["requires_review"]
            report["evidence_file"] = args.output
        elif args.command == "verify":
            report = verify_evidence(read_evidence(args.evidence_file))
        else:
            report = {"scope": "finite_range_only", "targets": [
                {"problem": "goldbach", "claim": "tested even integers have a two-prime decomposition", "not_proven": "all even integers"},
                {"problem": "collatz", "claim": "tested starting integers reach one within an explicit step bound", "not_proven": "all positive integers"}],
                "open_problem_claims": "none"}
        print(json.dumps(report, sort_keys=True, indent=2))
        return 0
    except (EvidenceError, OSError, ValueError, OverflowError) as exc:
        print(json.dumps({"ok": False, "error": "math_frontier_failed", "detail": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(frontier_cli())
