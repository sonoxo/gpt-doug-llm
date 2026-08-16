#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys

from doug_core.heat_seek import (
    VERSION,
    create_baseline,
    create_snapshot,
    iterate,
    launch_turtle_shell,
    safe_harden,
    scan,
    verify_audit_chain,
    verify_baseline,
)


def dump(value) -> None:
    if hasattr(value, "to_dict"):
        value = value.to_dict()

    print(
        json.dumps(
            value,
            indent=2,
            default=str,
        )
    )


def banner() -> None:
    print()
    print(
        "╔══════════════════════════════════════════════════════╗"
    )
    print(
        "║            GPT DOUG — HEAT SEEK V6                 ║"
    )
    print(
        "║       DEFENSIVE CIA TRIAD TURTLE SHELL             ║"
    )
    print(
        "║  CONFIDENTIALITY • INTEGRITY • AVAILABILITY        ║"
    )
    print(
        "╚══════════════════════════════════════════════════════╝"
    )
    print()


def main() -> None:

    parser = argparse.ArgumentParser(
        prog="heatseek",
        description=(
            "GPT Doug defensive CIA-triad "
            "turtle shell"
        ),
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"Heat Seek {VERSION}",
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    scan_cmd = sub.add_parser(
        "scan",
        help="Run complete CIA security assessment",
    )

    scan_cmd.add_argument(
        "--port",
        type=int,
        default=8788,
    )

    sub.add_parser(
        "baseline",
        help="Create known-good integrity baseline",
    )

    sub.add_parser(
        "verify",
        help="Verify baseline and audit chain",
    )

    sub.add_parser(
        "harden",
        help="Apply safe local hardening",
    )

    iterate_cmd = sub.add_parser(
        "iterate",
        help=(
            "Run iterative CIA assessment and "
            "optional safe hardening"
        ),
    )

    iterate_cmd.add_argument(
        "--rounds",
        type=int,
        default=3,
    )

    iterate_cmd.add_argument(
        "--target",
        type=int,
        default=95,
    )

    iterate_cmd.add_argument(
        "--harden",
        action="store_true",
    )

    iterate_cmd.add_argument(
        "--port",
        type=int,
        default=8788,
    )

    launch_cmd = sub.add_parser(
        "launch",
        help=(
            "Launch GPT Doug inside the "
            "no-Ollama turtle shell"
        ),
    )

    launch_cmd.add_argument(
        "--port",
        type=int,
        default=8788,
    )

    sub.add_parser(
        "snapshot",
        help="Create local recovery snapshot",
    )

    args = parser.parse_args()

    banner()

    if args.command == "scan":
        dump(
            scan(
                web_port=args.port
            )
        )

    elif args.command == "baseline":
        dump(
            create_baseline()
        )

    elif args.command == "verify":

        baseline_findings, baseline_info = (
            verify_baseline()
        )

        audit_ok, audit_message = (
            verify_audit_chain()
        )

        dump(
            {
                "baseline": baseline_info,
                "baseline_findings": [
                    finding.to_dict()
                    for finding
                    in baseline_findings
                ],
                "audit_chain": {
                    "valid": audit_ok,
                    "message": audit_message,
                },
            }
        )

    elif args.command == "harden":
        dump(
            {
                "actions": safe_harden()
            }
        )

    elif args.command == "iterate":
        dump(
            iterate(
                rounds=args.rounds,
                target_score=args.target,
                harden=args.harden,
                web_port=args.port,
            )
        )

    elif args.command == "launch":
        dump(
            launch_turtle_shell(
                port=args.port
            )
        )

    elif args.command == "snapshot":
        dump(
            create_snapshot()
        )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(
            "\nHeat Seek interrupted.",
            file=sys.stderr,
        )
        raise SystemExit(130)
