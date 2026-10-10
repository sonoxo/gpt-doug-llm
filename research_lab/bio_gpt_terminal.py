"""Bio-Gpt's offline, interactive terminal dashboard.

This is a read-only UI for a mathematical research toy model. It neither starts
five agent runtimes nor interfaces with real biology or remote services.
"""
from __future__ import annotations

import argparse
import sys
from fractions import Fraction
from typing import Any, Mapping

from research_lab import bio_gpt


DIVIDER = "=" * 63


def _decimal(value: Any) -> str:
    return f"{float(Fraction(value)):.6f}"


def header() -> None:
    print(DIVIDER)
    print(" BIO-GPT     |     GPT-DOUG FIVE-CORE MATHEMATICS CONSOLE")
    print(DIVIDER)
    print(" OFFLINE  /  6 CHANNELS PER LAYER  /  EXACT RATIONAL MATH")
    print(" Toy model only: NO biochip, physical brain, or live agent swarm")
    print()


def show_manifest() -> None:
    data = bio_gpt.manifest()
    print("\nFIVE CORE OPERATORS (MATHEMATICAL, NOT ACTIVE SERVICES)")
    for i, role in enumerate(data["roles"], start=1):
        print(f"  {i}. {role['name']:<21} {role['from']:<13} <-> {role['to']}")
    print("  Provenance: sonoxo/gpt-doug-llm; no external calls\n")


def show_demo() -> None:
    report = bio_gpt.analyze(bio_gpt.demo_problem())
    proof: Mapping[str, str] = report["proof"]
    print("\nEXACT 36-DIMENSIONAL BENCHMARK")
    print("  Proof:       ", report["status"])
    print("  Coordinates: ", report["finite_dimensions"])
    print("  Stability:   ", "continuous norm decreases at least as exp(-2t)")
    print("  Delta:       ", proof["dissipation_delta"])
    print("  Lipschitz L: ", proof["lipschitz_upper_bound"])
    print("  Euler q:     ", proof["euler_squared_norm_contraction_factor"])
    print("  q decimal:   ", _decimal(proof["euler_squared_norm_contraction_factor"]))
    print("  Final energy:", _decimal(report["final_squared_norm"]))
    print("  Evidence:    ", report["evidence_sha256"][:20] + "...")
    print("  Result:      exact rational proof replay available\n")
    print("  STEP  SQUARED NORM (approx.; certificate stores exact fractions)")
    for row in report["trajectory"]:
        value = _decimal(row["squared_norm"])
        print(f"   {row['step']:>2}      {value}")
    print("\n  No infinite calculation: theorem analytic, simulation finite.\n")


def show_hierarchy() -> None:
    problem = bio_gpt.demo_problem()
    problem.pop("modes")
    result = bio_gpt.hierarchy(problem, [1, 2, 4, 8, 16])
    print("\nFINITE LAYERS -> COUNTABLY INFINITE THEORY")
    print("  LAYERS    COORDINATES    ENERGY (APPROX.)     EULER EXACT")
    for row in result["layers"]:
        exact = "yes" if row["exact_infinite_euler_horizon"] else "not yet"
        print(f"  {row['modes']:>6}    {row['finite_dimensions']:>11}    "
              f"{_decimal(row['final_squared_norm']):>16}    {exact:>11}")
    print("\n  This exactness concerns finite-step Euler, not continuous time.\n")


def show_cure_swarm() -> None:
    """Safe, entirely synthetic cancer-research evidence preview."""
    from research_lab import cure_swarm

    report = cure_swarm.analyze(cure_swarm.sample_snapshot())
    print("\nBIO-GPT CURE SWARM // SYNTHETIC RESEARCH DEMO")
    print("  PUBLIC CLINICAL TRIAL API FETCH: DISABLED IN THIS MENU")
    print("  SOURCE:              SIMULATED DATA ONLY")
    print("  Recorded trials:     ", report["counts"]["studies"])
    print("  Publications:        ", report["counts"]["publications"])
    print("  Medical review gate: REQUIRED")
    print("  Approved cures:      0 (no clinical efficacy assessed)")
    print("  Research stages:")
    for role in report["agents"]:
        print(f'   - {role["role"]}: {role["function"]}')
    print("  Evidence gaps:")
    for record in report["evidence"]:
        print(f'   - {record["id"]}: {", ".join(record["review_flags"])}')
    print("  For public metadata: bash scripts/doug-max cure-swarm online")
    print("      --query glioblastoma --per-source 5")
    print("  No diagnosis, treatment, drug synthesis or patient data.\n")


def check_replay() -> None:
    report = bio_gpt.analyze(bio_gpt.demo_problem())
    print("\nCERTIFICATE REPLAY:", "VERIFIED" if bio_gpt.verify(report) else "INVALID")
    print("  SHA-256:", report["evidence_sha256"])
    print("  A digest confirms consistency, not physical validity or novelty.\n")


def show_menu() -> None:
    print(" [1] Run exact mathematical simulation")
    print(" [2] Inspect all five operator mappings")
    print(" [3] View dimension hierarchy (6 -> 96)")
    print(" [4] Verify demo proof certificate")
    print(" [5] Bio-Gpt Cure Swarm (synthetic evidence preview)")
    print(" [q] Quit Bio-Gpt\n")


def launch() -> int:
    header()
    show_demo()
    while True:
        show_menu()
        try:
            choice = input("Bio-Gpt> ").strip().lower()
        except EOFError:
            print("\nInput closed. Exiting Bio-Gpt.")
            return 0
        except KeyboardInterrupt:
            print("\nStopped by operator.")
            return 130
        try:
            if choice in ("1", "demo", "run"):
                show_demo()
            elif choice in ("2", "roles", "manifest"):
                show_manifest()
            elif choice in ("3", "hierarchy", "layers"):
                show_hierarchy()
            elif choice in ("4", "verify", "check"):
                check_replay()
            elif choice in ("5", "cure", "cure-swarm", "research"):
                show_cure_swarm()
            elif choice in ("q", "quit", "exit", "0"):
                print("Exiting Bio-Gpt. No background processes left running.")
                return 0
            else:
                print("Unknown command. Enter 1, 2, 3, 4, 5, or q.\n")
        except (ArithmeticError, ValueError, OverflowError):
            print("Model computation failed; no result claimed.\n")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true", help="print dashboard, then exit without interaction")
    args = parser.parse_args(argv)
    if args.once:
        header()
        show_demo()
        show_manifest()
        return 0
    return launch()


if __name__ == "__main__":
    sys.exit(main())
