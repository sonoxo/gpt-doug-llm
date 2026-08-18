#!/usr/bin/env python3
"""Safe simulation of GPT Doug provider resilience.

This does not contact real providers or control external systems. It simulates
provider failures, retries, circuit breaker transitions, and router failover
for defensive testing and visualization.
"""

from __future__ import annotations

import argparse
import json
import random
from dataclasses import dataclass


@dataclass
class Provider:
    name: str
    base_success: float
    failures: int = 0
    circuit: str = "closed"
    cooldown: int = 0


def simulate(steps: int = 60, seed: int = 7, threshold: int = 3, cooldown_steps: int = 5):
    rng = random.Random(seed)
    providers = [
        Provider("claude", 0.88),
        Provider("openai", 0.90),
        Provider("gemini", 0.86),
        Provider("ollama", 0.94),
    ]
    rows = []

    for t in range(steps):
        # Deliberately inject a temporary outage into the first providers so
        # circuit breakers and failover are visible in a deterministic demo.
        outage = 18 <= t < 30
        selected = None
        attempt_log = []

        for p in providers:
            if p.circuit == "open":
                p.cooldown -= 1
                if p.cooldown <= 0:
                    p.circuit = "half_open"
                else:
                    attempt_log.append({"provider": p.name, "result": "circuit_open"})
                    continue

            success_prob = p.base_success
            if outage and p.name in {"claude", "openai", "gemini"}:
                success_prob = 0.10

            ok = rng.random() < success_prob
            if ok:
                p.failures = 0
                p.circuit = "closed"
                selected = p.name
                attempt_log.append({"provider": p.name, "result": "success"})
                break

            p.failures += 1
            attempt_log.append({"provider": p.name, "result": "failure"})
            if p.circuit == "half_open" or p.failures >= threshold:
                p.circuit = "open"
                p.cooldown = cooldown_steps

        rows.append({
            "step": t,
            "outage_injected": outage,
            "selected_provider": selected or "none",
            "attempts": attempt_log,
            "circuits": {p.name: p.circuit for p in providers},
            "failures": {p.name: p.failures for p in providers},
        })
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--steps", type=int, default=60)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    rows = simulate(args.steps, args.seed)

    if args.json:
        print(json.dumps(rows, indent=2))
        return

    print("STEP  ROUTED     CLAUDE   OPENAI   GEMINI   OLLAMA   EVENT")
    print("----  ---------  -------  -------  -------  -------  ----------------")
    for r in rows:
        c = r["circuits"]
        event = "INJECTED-OUTAGE" if r["outage_injected"] else "normal"
        print(f"{r['step']:>4}  {r['selected_provider']:<9}  {c['claude']:<7}  {c['openai']:<7}  {c['gemini']:<7}  {c['ollama']:<7}  {event}")


if __name__ == "__main__":
    main()
