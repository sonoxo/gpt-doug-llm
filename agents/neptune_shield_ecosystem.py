#!/usr/bin/env python3
"""Read-only Neptune Shield ecosystem intelligence for GPT-DOUG-LLM MAX.

This module reads the public-source Glass Onion vendor graph shipped in
safety-shield/ontology/neptune-shield-vendor-ecosystem.json. It never scans,
authenticates to, targets, or modifies third-party systems. Public partner
claims remain source assertions unless separately corroborated.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

SOURCE = Path("safety-shield/ontology/neptune-shield-vendor-ecosystem.json")


class NeptuneShieldError(RuntimeError):
    """Raised when the local public-source ecosystem package fails validation."""


def _read(root: Path) -> dict[str, Any]:
    path = root / SOURCE
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NeptuneShieldError(f"cannot read {SOURCE}: {exc}") from exc
    if not isinstance(data, dict):
        raise NeptuneShieldError("ecosystem package must be a JSON object")
    _validate(data)
    return data


def _validate(data: dict[str, Any]) -> None:
    if data.get("classification") != "PUBLIC_SOURCE_OSINT":
        raise NeptuneShieldError("unexpected classification")
    source = data.get("source") or {}
    if source.get("url") != "https://neptuneshield.com/vendors.html":
        raise NeptuneShieldError("unexpected source URL")
    if source.get("authority") != "first-party public website":
        raise NeptuneShieldError("source authority is not first-party public")
    org = data.get("organization") or {}
    if org.get("id") != "neptune-shield":
        raise NeptuneShieldError("unexpected organization id")
    required = {
        "securexperts",
        "sparkline-cyber",
        "octaris-technologies",
        "local-sphere",
        "the-honor-foundation",
        "radian-forge",
        "community-first-project",
    }
    actual = {str(item.get("id")) for item in data.get("vendor_partners") or []}
    missing = sorted(required - actual)
    if missing:
        raise NeptuneShieldError(f"vendor graph missing: {', '.join(missing)}")
    kraken = ((data.get("xunia_mapping") or {}).get("kraken_jutsu") or {})
    if kraken.get("mode") != "DEFENSIVE_ADAPTIVE_ORCHESTRATION":
        raise NeptuneShieldError("Kraken Jutsu is not in defensive orchestration mode")


def status(root: Path) -> str:
    data = _read(root)
    org = data["organization"]
    vendors = data["vendor_partners"]
    capabilities = sorted({cap for item in vendors for cap in item.get("capabilities") or []})
    return (
        "🐙 KRAKEN JUTSU // NEPTUNE SHIELD ECOSYSTEM ✅\n"
        f"Organization: {org['name']} | CAGE {org['cage']} | UEI {org['uei']}\n"
        f"Vendor partners: {len(vendors)} | Capability assertions: {len(capabilities)}\n"
        f"Source: {data['source']['url']} | State: {data['source']['evidence_state']}\n"
        "Mode: DEFENSIVE_ADAPTIVE_ORCHESTRATION / READ-ONLY PUBLIC OSINT"
    )


def graph(root: Path) -> str:
    data = _read(root)
    lines = ["NEPTUNE SHIELD"]
    for item in data["vendor_partners"]:
        lines.append(f"  ├─ {item['name']} [{item['dossier']}] [{item['status']}]")
        for cap in item.get("capabilities") or []:
            lines.append(f"  │    └─ {cap}")
    return "\n".join(lines)


def brief(root: Path) -> str:
    data = _read(root)
    lines = [
        "# Neptune Shield // Glass Onion Ecosystem Brief",
        "",
        f"Source: {data['source']['url']}",
        f"Captured: {data['captured_at']} | Evidence: {data['source']['evidence_state']}",
        "",
        "Public vendor-partner capability map:",
    ]
    for item in data["vendor_partners"]:
        lines.append(f"- {item['name']} ({item['dossier']}): " + "; ".join(item.get("capabilities") or []))
    lines.extend(
        [
            "",
            "Handling: partner descriptions are first-party public claims, not independent verification.",
            "XUNIA use: lawful integration mapping, partnership analysis, procurement-fit analysis, defensive architecture matching, and evidence-gap detection.",
        ]
    )
    return "\n".join(lines)


def query(root: Path, question: str) -> str:
    data = _read(root)
    needle = question.strip().lower()
    if not needle:
        raise NeptuneShieldError("query cannot be empty")
    matches: list[str] = []
    for item in data["vendor_partners"]:
        haystack = " ".join(
            [
                str(item.get("name", "")),
                str(item.get("dossier", "")),
                " ".join(item.get("capabilities") or []),
            ]
        ).lower()
        if needle in haystack or any(token in haystack for token in needle.split() if len(token) > 2):
            matches.append(
                f"{item['name']} [{item['dossier']}]: " + "; ".join(item.get("capabilities") or [])
            )
    if not matches:
        return "No matching source-asserted vendor capability was found in the local Neptune Shield public-source package."
    return "\n".join(matches)


def run_command(root: str | Path, command: str, argument: str = "") -> str:
    root_path = Path(root).resolve()
    if command == "status":
        return status(root_path)
    if command == "graph":
        return graph(root_path)
    if command == "brief":
        return brief(root_path)
    if command == "query":
        return query(root_path, argument)
    raise NeptuneShieldError(f"unknown command: {command}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Neptune Shield public ecosystem layer")
    parser.add_argument("command", choices=["status", "graph", "brief", "query"])
    parser.add_argument("argument", nargs="*", help="query text")
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    try:
        print(run_command(args.root, args.command, " ".join(args.argument)))
    except NeptuneShieldError as exc:
        print(f"NEPTUNE SHIELD LAYER BLOCKED: {exc}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
