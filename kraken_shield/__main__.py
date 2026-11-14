"""CLI: python3 -m kraken_shield {status|verify|inspect|capability|ontology|judge}."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import KrakenShield, KrakenShieldError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kraken Shield CL1 (free, local, no execution)")
    parser.add_argument("command", choices=("status", "verify", "inspect", "capability", "ontology", "judge"))
    parser.add_argument("--state-dir", help="Absolute private path for hash-linked local audit log")
    parser.add_argument("--capability", help="Capability identifier; for capability checks only")
    args = parser.parse_args(argv)

    try:
        if args.command == "ontology":
            path = Path(__file__).with_name("ontology.json")
            print(path.read_text(encoding="utf-8"), end="")
            return 0

        guard = KrakenShield(state_dir=args.state_dir)
        if args.command == "status":
            result = guard.status()
            good = result["ready"]
        elif args.command == "verify":
            result = guard.verify_audit()
            good = result["valid"]
        elif args.command == "judge":
            data = sys.stdin.buffer.read(16_385)
            if len(data) > 16_384:
                print(json.dumps({"error": "evidence_too_large"}), file=sys.stderr)
                return 3
            result = guard.judge_vulnerability(json.loads(data.decode("utf-8")))
            good = result["decision"] == "READ_ONLY"
        elif args.command == "inspect":
            # STDIN only: don't put security-sensitive payloads on shell command lines.
            data = sys.stdin.buffer.read(16_385)
            if len(data) > 16_384:
                print(json.dumps({"error": "input_too_large"}), file=sys.stderr)
                return 3
            result = guard.inspect(data.decode("utf-8"), source="kraken-cli")
            good = result["decision"] == "ALLOW"
        elif args.command == "capability":
            if args.capability is None:
                parser.error("capability requires --capability")
            result = guard.check_capability(args.capability)
            good = result["decision"] == "ALLOW"
        else:
            parser.error("unrecognized command")
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if good else 3
    except (KrakenShieldError, OSError, UnicodeError, ValueError):
        print(json.dumps({"error": "kraken_shield_fail_closed"}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
