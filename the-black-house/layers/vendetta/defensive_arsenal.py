#!/usr/bin/env python3
"""VENDETTA defensive arsenal.

Offline, non-destructive defensive utilities:
- WATCHTOWER: triage event records.
- MIRROR: generate synthetic adversary-emulation events.
- BLACKBOX: hash evidence files.
- AIRLOCK: produce containment plans only.
- REWIND: produce recovery plans only.

No exploit generation, malware, credential collection, remote execution, or
external network action is implemented here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

SEVERITY_WEIGHTS = {
    "auth_failure": 15,
    "privilege_change": 35,
    "new_persistence": 45,
    "suspicious_process": 30,
    "unexpected_network": 25,
    "file_integrity_change": 20,
    "ransomware_indicator": 70,
}

SYNTHETIC_PATTERNS = [
    "auth_failure",
    "privilege_change",
    "new_persistence",
    "suspicious_process",
    "unexpected_network",
    "file_integrity_change",
]


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, sort_keys=True))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for index, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at line {index}: {exc}") from exc
        if not isinstance(item, dict):
            raise ValueError(f"line {index} must contain a JSON object")
        events.append(item)
    return events


def score_event(event: dict[str, Any]) -> dict[str, Any]:
    kind = str(event.get("event_type", "unknown"))
    score = SEVERITY_WEIGHTS.get(kind, 5)
    repeats = int(event.get("repeat_count", 1) or 1)
    score += min(25, max(0, repeats - 1) * 3)
    if bool(event.get("critical_asset", False)):
        score += 20
    score = min(100, score)
    if score >= 75:
        severity = "critical"
    elif score >= 50:
        severity = "high"
    elif score >= 25:
        severity = "medium"
    else:
        severity = "low"
    return {
        "event": event,
        "score": score,
        "severity": severity,
        "recommended_action": "human_review" if score >= 25 else "monitor",
    }


def watchtower(path: Path) -> None:
    events = load_jsonl(path)
    assessments = [score_event(event) for event in events]
    emit(
        {
            "weapon": "WATCHTOWER",
            "mode": "DEFENSIVE_ONLY",
            "event_count": len(events),
            "assessments": assessments,
        }
    )


def mirror(count: int, seed: int) -> None:
    rng = random.Random(seed)
    now = int(time.time())
    events: list[dict[str, Any]] = []
    for idx in range(count):
        event_type = rng.choice(SYNTHETIC_PATTERNS)
        events.append(
            {
                "synthetic": True,
                "event_id": f"mirror-{seed}-{idx + 1}",
                "timestamp": now + idx,
                "event_type": event_type,
                "repeat_count": rng.randint(1, 8),
                "critical_asset": rng.random() < 0.2,
                "source": "VENDETTA_MIRROR_SANDBOX",
            }
        )
    emit({"weapon": "MIRROR", "sandboxed": True, "events": events})


def blackbox(path: Path) -> None:
    if not path.is_file():
        raise ValueError("evidence path must be a regular file")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    emit(
        {
            "weapon": "BLACKBOX",
            "evidence": {
                "path": str(path),
                "sha256": digest,
                "size_bytes": path.stat().st_size,
                "recorded_at": int(time.time()),
            },
        }
    )


def airlock(incident: str, critical: bool) -> None:
    steps = [
        "Preserve volatile and durable evidence before changes.",
        "Identify affected assets, identities, and dependencies.",
        "Prepare isolation rules for human approval; do not execute automatically.",
        "Revoke or rotate exposed credentials only after authorization and evidence capture.",
        "Validate business continuity and safety impact before containment.",
        "Record every approved action and resulting evidence.",
    ]
    if critical:
        steps.insert(2, "Escalate to the designated incident owner and safety authority.")
    emit(
        {
            "weapon": "AIRLOCK",
            "incident": incident,
            "execution": "PLAN_ONLY",
            "requires_human_approval": True,
            "steps": steps,
        }
    )


def rewind(incident: str) -> None:
    emit(
        {
            "weapon": "REWIND",
            "incident": incident,
            "execution": "PLAN_ONLY",
            "requires_human_approval": True,
            "steps": [
                "Confirm containment and preserve evidence.",
                "Select a known-good recovery point and verify integrity.",
                "Restore in an isolated validation environment first.",
                "Rotate affected secrets and invalidate compromised sessions.",
                "Patch the verified root cause before reconnecting services.",
                "Run functional, security, and backup validation.",
                "Return to service gradually with heightened monitoring.",
            ],
        }
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="VENDETTA defensive arsenal")
    sub = parser.add_subparsers(dest="command", required=True)

    p_watch = sub.add_parser("watchtower", help="triage JSONL security events")
    p_watch.add_argument("file", type=Path)

    p_mirror = sub.add_parser("mirror", help="generate synthetic sandbox events")
    p_mirror.add_argument("--count", type=int, default=10)
    p_mirror.add_argument("--seed", type=int, default=1337)

    p_blackbox = sub.add_parser("blackbox", help="hash a local evidence file")
    p_blackbox.add_argument("file", type=Path)

    p_airlock = sub.add_parser("airlock", help="generate a containment plan")
    p_airlock.add_argument("incident")
    p_airlock.add_argument("--critical", action="store_true")

    p_rewind = sub.add_parser("rewind", help="generate a recovery plan")
    p_rewind.add_argument("incident")

    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "watchtower":
            watchtower(args.file)
        elif args.command == "mirror":
            if not 1 <= args.count <= 1000:
                raise ValueError("count must be between 1 and 1000")
            mirror(args.count, args.seed)
        elif args.command == "blackbox":
            blackbox(args.file)
        elif args.command == "airlock":
            airlock(args.incident, args.critical)
        elif args.command == "rewind":
            rewind(args.incident)
        else:
            raise ValueError("unsupported command")
    except (OSError, ValueError) as exc:
        print(f"VENDETTA error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
