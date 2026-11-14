"""CLI: python3 -m kraken_shield {status|verify|inspect|capability|ontology|judge|services|service-check}."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import KrakenShield, KrakenShieldError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Kraken Shield CL1 (free, local, no execution)")
    parser.add_argument("command", choices=("status", "verify", "inspect", "capability", "ontology", "judge", "services", "service-check"))
    parser.add_argument("--state-dir", help="Absolute private path for hash-linked local audit log")
    parser.add_argument("--capability", help="Capability identifier; for capability checks only")
    parser.add_argument("--sector", choices=("music", "bank"))
    parser.add_argument("--service", help="Public service identifier; never enter account numbers")
    parser.add_argument("--operation", help="Policy action: open_public_link, read_public_catalog, status etc.")

    args = parser.parse_args(argv)

    try:
        if args.command == "services":
            from .service_policy import service_catalog

            print(json.dumps(service_catalog(), indent=2, sort_keys=True))
            return 0
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
        elif args.command == "service-check":
            if not (args.sector and args.service and args.operation):
                parser.error("service-check requires --sector, --service and --operation")
            # Only a public URL may be passed via STDIN. Never supply OAuth
            # codes, bank URLs, passwords or account numbers to this tool.
            data = sys.stdin.buffer.read(2049)
            if len(data) > 2048:
                print(json.dumps({"error": "public_url_too_large"}), file=sys.stderr)
                return 3
            url = data.decode("utf-8").strip() or None
            result = guard.check_service(args.sector, args.service, args.operation, url=url)
            good = result["decision"] == "ALLOW"
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
