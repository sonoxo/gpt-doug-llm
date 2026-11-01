#!/usr/bin/env python3
"""RED NOVEMBER / KRAKEN: bounded finite computational experiments, not proofs."""
import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import os
import pathlib
import time


def sieve(n):
    flags = bytearray(b"\x01") * (n + 1)
    flags[:2] = b"\x00\x00"
    for p in range(2, math.isqrt(n) + 1):
        if flags[p]:
            flags[p * p:n + 1:p] = b"\x00" * (((n - p * p) // p) + 1)
    return flags


def goldbach(limit):
    prime = sieve(limit)
    primes = [i for i in range(2, limit + 1) if prime[i]]
    for even in range(4, limit + 1, 2):
        if not any(prime[even - p] for p in primes if p <= even // 2):
            return dict(problem="Goldbach", status="CANDIDATE_REQUIRES_VERIFICATION",
                        counterexample=even)
    return dict(problem="Goldbach", status="NO_COUNTEREXAMPLE_IN_RANGE",
                even_values_tested=limit // 2 - 1, limit=limit)


def collatz(limit):
    memo = {1: 0}
    maxsteps, maxstart = 0, 1
    for i in range(1, limit + 1):
        x, trail = i, []
        while x not in memo:
            trail.append(x)
            x = 3 * x + 1 if x & 1 else x // 2
        steps = memo[x]
        for t in reversed(trail):
            steps += 1
            memo[t] = steps
        if memo[i] > maxsteps:
            maxsteps, maxstart = memo[i], i
    return dict(problem="Collatz", status="ALL_STARTS_REACHED_ONE",
                starts_tested=limit, max_steps=maxsteps, max_steps_start=maxstart)


def twins(limit):
    prime = sieve(limit)
    return dict(problem="Twin primes", status="FINITE_COUNT", limit=limit,
                pairs=sum(prime[i] and prime[i + 2] for i in range(3, limit - 1, 2)))


def verify():
    return {
        "goldbach_25000": goldbach(25000)["even_values_tested"] == 12499,
        "collatz_25000": collatz(25000)["max_steps"] == 281,
        "twin_25000": twins(25000)["pairs"] == 408,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100000)
    ap.add_argument("--output", default="red_november_report.json")
    args = ap.parse_args()
    if not 100 <= args.limit <= 1000000:
        ap.error("limit must be 100..1000000")
    start = time.perf_counter()
    with cf.ProcessPoolExecutor(max_workers=3) as pool:
        jobs = [pool.submit(fn, args.limit) for fn in (goldbach, collatz, twins)]
        experiments = [job.result() for job in jobs]
    checks = verify()
    report = {
        "name": "RED NOVEMBER / KRAKEN",
        "mode": "local bounded parallel CPU processes",
        "cpu_count": os.cpu_count(),
        "workers": 3,
        "limit": args.limit,
        "experiments": experiments,
        "independent_baseline_check": checks,
        "elapsed_seconds": round(time.perf_counter() - start, 3),
        "caution": "Finite results are not formal mathematical proofs.",
    }
    path = pathlib.Path(args.output)
    path.write_text(json.dumps(report, indent=2) + "\n")
    report["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    print(json.dumps(report, indent=2))
    if not all(checks.values()):
        raise SystemExit("baseline verification failed")


if __name__ == "__main__":
    main()
