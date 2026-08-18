#!/usr/bin/env python3
"""Zyra Defense Matrix: safe real-data-informed cyber-defense simulation.

Uses only defensive/public or local telemetry signals. It does NOT scan,
exploit, target, or control real systems. External data may be supplied as
aggregate JSON metrics (for example KEV/CVE counts) and local Zyra audit logs
may be summarized into alert pressure.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path


REGIONS = ["NA", "SA", "EU", "AF", "ME", "AS", "OC"]


@dataclass
class Node:
    region: str
    integrity: float = 100.0
    shield: float = 50.0
    pressure: float = 0.0
    score: int = 0


def load_public_metrics(path: str | None) -> dict:
    if not path:
        return {"kev_recent": 0, "cve_critical": 0, "attack_index": 1.0}
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return {
        "kev_recent": int(data.get("kev_recent", 0)),
        "cve_critical": int(data.get("cve_critical", 0)),
        "attack_index": float(data.get("attack_index", 1.0)),
    }


def summarize_zyra_audit(path: str | None) -> dict:
    if not path:
        return {"events": 0, "blocked": 0, "approval": 0}
    p = Path(path).expanduser()
    if not p.exists():
        return {"events": 0, "blocked": 0, "approval": 0}
    events = blocked = approval = 0
    for line in p.read_text(encoding="utf-8").splitlines()[-2000:]:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        events += 1
        if not event.get("allowed", True):
            blocked += 1
        if "ZYRA-HITL-001" in event.get("control_ids", []):
            approval += 1
    return {"events": events, "blocked": blocked, "approval": approval}


def threat_pressure(round_no: int, public: dict, audit: dict) -> float:
    kev = min(public["kev_recent"] / 50.0, 4.0)
    cve = min(public["cve_critical"] / 100.0, 4.0)
    audit_rate = audit["blocked"] / max(audit["events"], 1)
    escalation = 1.0 + math.log2(max(round_no, 1)) * 0.15
    return max(0.5, public["attack_index"] + kev + cve + 2.0 * audit_rate) * escalation


def run_round(nodes, rng, round_no, public, audit):
    global_pressure = threat_pressure(round_no, public, audit)
    events = []
    for node in nodes:
        regional = global_pressure * rng.uniform(0.65, 1.35)
        node.pressure = regional
        defend = 8.0 + math.sqrt(round_no) * 0.6 + rng.uniform(-2.5, 2.5)
        node.shield = min(100.0, node.shield + defend)
        incoming = regional * rng.uniform(2.5, 5.0)
        absorbed = min(node.shield, incoming)
        node.shield -= absorbed
        damage = incoming - absorbed
        node.integrity = max(0.0, node.integrity - damage)
        if damage == 0:
            node.score += int(10 + regional)
            outcome = "BLOCKED"
        elif node.integrity > 0:
            node.score += 2
            outcome = "DEGRADED"
        else:
            outcome = "NODE-DOWN"
        events.append({
            "region": node.region,
            "pressure": round(regional, 2),
            "integrity": round(node.integrity, 1),
            "shield": round(node.shield, 1),
            "outcome": outcome,
            "score": node.score,
        })
    return global_pressure, events


def print_frame(round_no, global_pressure, events, public, audit):
    print("\033[2J\033[H", end="")
    print("ZYRA DEFENSE MATRIX // SAFE WORLD SIM")
    print(f"ROUND {round_no}  THREAT {global_pressure:6.2f}  KEV {public['kev_recent']}  CRIT-CVE {public['cve_critical']}  AUDIT-BLOCKED {audit['blocked']}")
    print("REGION  INTEGRITY  SHIELD  PRESSURE  STATUS      SCORE")
    print("------  ---------  ------  --------  ----------  -----")
    for e in events:
        bar_i = "#" * int(e["integrity"] / 10)
        bar_s = "+" * int(e["shield"] / 10)
        print(f"{e['region']:<6}  {e['integrity']:>8.1f}  {e['shield']:>6.1f}  {e['pressure']:>8.2f}  {e['outcome']:<10}  {e['score']:>5}  I[{bar_i:<10}] S[{bar_s:<10}]")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--public-metrics", help="JSON file with kev_recent, cve_critical, attack_index")
    parser.add_argument("--zyra-audit", default="~/.gpt-doug/zyra-audit.jsonl")
    parser.add_argument("--seed", type=int, default=369)
    parser.add_argument("--delay", type=float, default=0.4)
    parser.add_argument("--rounds", type=int, default=0, help="0 = infinite")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    rng = random.Random(args.seed)
    public = load_public_metrics(args.public_metrics)
    audit = summarize_zyra_audit(args.zyra_audit)
    nodes = [Node(r) for r in REGIONS]

    round_no = 1
    try:
        while args.rounds == 0 or round_no <= args.rounds:
            pressure, events = run_round(nodes, rng, round_no, public, audit)
            if args.json:
                print(json.dumps({"round": round_no, "threat": pressure, "events": events}))
            else:
                print_frame(round_no, pressure, events, public, audit)
            # Recover down nodes as simulated disaster-recovery rebuilds.
            for node in nodes:
                if node.integrity <= 0:
                    node.integrity = 65.0
                    node.shield = 25.0
            round_no += 1
            time.sleep(max(0.0, args.delay))
    except KeyboardInterrupt:
        print("\nSimulation stopped safely.")


if __name__ == "__main__":
    main()
