"""Validate intelligence knowledge JSONL for provenance and safe ingestion.

Legacy knowledge files may predate the structured provenance schema. This tool
reports gaps without rewriting source material or treating attribution labels as
proof of authenticity.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    level: str
    message: str


REQUIRED_LEGACY_FIELDS = ("id", "topic", "summary", "attribution")
SENSITIVE_SOURCE_LABELS = ("field manual", "classified", "leaked", "stolen")


def validate_record(record: dict, path: str, line: int) -> list[Finding]:
    findings: list[Finding] = []
    for field in REQUIRED_LEGACY_FIELDS:
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            findings.append(Finding(path, line, "error", f"missing or empty field: {field}"))

    attribution = str(record.get("attribution", "")).strip()
    lower_attr = attribution.lower()
    if any(label in lower_attr for label in SENSITIVE_SOURCE_LABELS):
        findings.append(
            Finding(
                path,
                line,
                "warning",
                "attribution label requires independent public-source verification before use",
            )
        )

    source_url = record.get("source_url")
    classification = record.get("classification")
    if source_url is None:
        findings.append(Finding(path, line, "warning", "legacy record has no source_url provenance"))
    if classification is None:
        findings.append(Finding(path, line, "warning", "legacy record has no classification metadata"))
    elif classification not in {"public", "declassified", "licensed", "user_authorized"}:
        findings.append(Finding(path, line, "error", "unsupported classification metadata"))

    return findings


def validate_jsonl(path: Path) -> list[Finding]:
    findings: list[Finding] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            if not raw.strip():
                continue
            try:
                record = json.loads(raw)
            except json.JSONDecodeError as exc:
                findings.append(Finding(str(path), line_number, "error", f"invalid JSON: {exc.msg}"))
                continue
            if not isinstance(record, dict):
                findings.append(Finding(str(path), line_number, "error", "record must be a JSON object"))
                continue
            findings.extend(validate_record(record, str(path), line_number))
    return findings


def validate_paths(paths: Iterable[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        findings.extend(validate_jsonl(path))
    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="JSONL knowledge files to validate")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="treat provenance warnings as a failing exit status",
    )
    args = parser.parse_args()

    findings = validate_paths(args.paths)
    for finding in findings:
        print(f"{finding.level.upper()} {finding.path}:{finding.line}: {finding.message}")

    has_errors = any(f.level == "error" for f in findings)
    has_warnings = any(f.level == "warning" for f in findings)
    if has_errors or (args.strict and has_warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
