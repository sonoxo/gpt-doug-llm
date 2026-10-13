"""EO 14434 SI-readiness evidence gate for the public Sonoxo fleet.

Read-only, bounded GitHub metadata inspection. It does not execute code from
remote repositories, access private repos, or modify any GitHub resources.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .cli import SNAPSHOT, load_snapshot
from .core import AuditError, OWNER, plan_upgrade, validate_snapshot

EO_ID = "14434"
EO_URL = "https://www.govinfo.gov/content/pkg/FR-2026-10-02/html/2026-20321.htm"
SCHEMA = "sonoxo.si-readiness.v1"
MAX_BYTES = 1_500_000
CHECKED_PATHS = ("package-lock.json", "pyproject.toml", ".github/dependabot.yml")
ADVISORIES = {
    "proxy-addr": {"introduced": (1, 1, 0), "patched": (2, 0, 8),
                   "id": "GHSA-jqcg-44mw-7w3h", "severity": "critical"},
    "source-map-js": {"introduced": (1, 0, 0), "patched": (1, 2, 2),
                      "id": "GHSA-68fv-2mgg-jv7q", "severity": "high"},
}
NAME_RE = re.compile(r"[A-Za-z0-9_.-]{1,100}\Z")
REF_RE = re.compile(r"[A-Za-z0-9_./-]{1,220}\Z")


def _version(value: Any) -> tuple[int, int, int] | None:
    """Conservatively parse only stable three-part versions."""
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(\d+)\.(\d+)\.(\d+)(?:\+[A-Za-z0-9.-]+)?", value)
    return tuple(map(int, match.groups())) if match else None


def audit_npm_lock(text: str) -> dict[str, Any]:
    """Check exact installed lockfile versions; no npm execution required."""
    try:
        doc = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise AuditError("invalid npm lockfile JSON") from exc
    if not isinstance(doc, dict) or not isinstance(doc.get("packages"), dict):
        raise AuditError("npm lockfile has no supported packages mapping")
    findings: list[dict[str, str]] = []
    unverified: list[dict[str, str]] = []
    examined = 0
    for path, package in doc["packages"].items():
        if not isinstance(path, str) or not isinstance(package, dict):
            raise AuditError("invalid npm lockfile package entry")
        name = path.rsplit("/", 1)[-1]
        if name not in ADVISORIES or "node_modules/" not in path:
            continue
        examined += 1
        raw_version = package.get("version")
        parsed = _version(raw_version)
        if parsed is None:
            unverified.append({"package": name, "version": str(raw_version)[:80]})
            continue
        rule = ADVISORIES[name]
        if rule["introduced"] <= parsed < rule["patched"]:
            findings.append({
                "package": name, "version": raw_version,
                "advisory": rule["id"], "severity": rule["severity"],
                "minimum_patched_version": ".".join(map(str, rule["patched"])),
            })
    return {
        "checked_packages": examined,
        "findings": sorted(findings, key=lambda x: (x["package"], x["version"])),
        "versions_unverified": sorted(unverified, key=lambda x: x["package"]),
        "scope": "ONLY_LISTED_ADVISORIES_AND_CHECKED_ROOT_LOCKFILE",
    }


def github_public_text(repo: str, branch: str, path: str, *, token: str | None = None) -> str | None:
    """Read one allowlisted public-repository file through the GitHub Contents API."""
    if (not isinstance(repo, str) or not repo.startswith(OWNER + "/")
            or not NAME_RE.fullmatch(repo[len(OWNER) + 1:])):
        raise AuditError("public Sonoxo repository required")
    if not isinstance(branch, str) or not REF_RE.fullmatch(branch) or ".." in branch:
        raise AuditError("invalid default branch")
    if path not in CHECKED_PATHS:
        raise AuditError("path is not in the root-manifest allowlist")
    name = quote(repo.split("/", 1)[1], safe="")
    url = ("https://api.github.com/repos/" + OWNER + "/" + name + "/contents/"
           + path + "?ref=" + quote(branch, safe=""))
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "gpt-doug-si-readiness/1.0",
    }
    if token:
        headers["Authorization"] = "Bearer " + token
    try:
        with urlopen(Request(url, headers=headers), timeout=12) as response:
            if response.status != 200:
                raise AuditError("GitHub metadata read returned a non-success status")
            raw = response.read(2 * MAX_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 404:
            return None
        raise AuditError("GitHub public file inspection failed") from None
    except (OSError, URLError, TimeoutError) as exc:
        raise AuditError("GitHub public file inspection unavailable") from exc
    if len(raw) > 2 * MAX_BYTES:
        raise AuditError("GitHub contents response exceeded the size limit")
    try:
        payload = json.loads(raw.decode("utf-8"))
        if not isinstance(payload, dict) or payload.get("type") != "file":
            raise AuditError("GitHub response was not a file")
        if payload.get("size", MAX_BYTES + 1) > MAX_BYTES:
            raise AuditError("manifest file exceeded the size limit")
        if payload.get("encoding") != "base64":
            raise AuditError("manifest encoding unsupported; inspection incomplete")
        blob = base64.b64decode(payload["content"].replace("\n", ""), validate=True)
        if len(blob) > MAX_BYTES:
            raise AuditError("decoded manifest exceeded the size limit")
        return blob.decode("utf-8")
    except (UnicodeError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, AuditError):
            raise
        raise AuditError("invalid GitHub contents response") from exc


def build_report(
    snapshot: dict[str, Any], *,
    limit: int = 12,
    fetch_text: Callable[[str, str, str], str | None] | None = None,
) -> dict[str, Any]:
    """Create an honest, whole-fleet review queue; inspect only bounded sample."""
    snapshot = validate_snapshot(snapshot)
    if not isinstance(limit, int) or isinstance(limit, bool) or not 0 <= limit <= 206:
        raise AuditError("inspection limit must be in 0..206")
    plan = plan_upgrade(snapshot)
    rows = plan["repositories"]
    selected = sorted(
        (r for r in rows if r["priority"] == "core_review" and "archived" not in r["blockers"]),
        key=lambda r: r["repo"].casefold(),
    )
    others = sorted(
        (r for r in rows if r not in selected and "archived" not in r["blockers"]),
        key=lambda r: r["repo"].casefold(),
    )
    selected_names = {r["repo"] for r in (selected + others)[:limit]} if fetch_text else set()
    results: list[dict[str, Any]] = []
    for row in rows:
        result: dict[str, Any] = {
            "repo": row["repo"], "default_branch": row["default_branch"],
            "priority": row["priority"], "open_prs_from_snapshot": row["observed_open_prs"],
            "status": "not_scanned", "manifest_evidence": {},
            "advisory_findings": [], "unverified_versions": [],
            "read_errors": [], "changes_applied": False,
        }
        if row["repo"] in selected_names:
            content_by_path: dict[str, str | None] = {}
            for path in CHECKED_PATHS:
                try:
                    value = fetch_text(row["repo"], row["default_branch"], path)
                    if value is not None and not isinstance(value, str):
                        raise AuditError("unexpected manifest content type")
                    if value is not None and len(value.encode("utf-8")) > MAX_BYTES:
                        raise AuditError("manifest file exceeded size limit")
                    content_by_path[path] = value
                    result["manifest_evidence"][path] = "present" if value is not None else "absent_at_root"
                except Exception:
                    # Avoid including tokens, URLs, server messages, or response bodies.
                    result["manifest_evidence"][path] = "unverified"
                    result["read_errors"].append(path)
            lock = content_by_path.get("package-lock.json")
            if lock is not None:
                try:
                    npm = audit_npm_lock(lock)
                    result["advisory_findings"] = npm["findings"]
                    result["unverified_versions"] = npm["versions_unverified"]
                except AuditError:
                    result["read_errors"].append("package-lock.json:invalid")
            if result["advisory_findings"]:
                result["status"] = "advisory_found"
            elif result["read_errors"] or result["unverified_versions"]:
                result["status"] = "incomplete_evidence"
            else:
                result["status"] = "review_current_evidence"
        results.append(result)
    counts = {key: sum(r["status"] == key for r in results) for key in (
        "advisory_found", "incomplete_evidence", "review_current_evidence", "not_scanned"
    )}
    return {
        "schema": SCHEMA,
        "order": {
            "number": EO_ID, "title": "Inaugurating the Era of Super Intelligence",
            "signed": "2026-09-29", "federal_register": "91 FR 63129",
            "source": EO_URL, "executive_branch_scope": True,
            "private_repositories_required_to_rename": False,
        },
        "scope": "SONOXO_PUBLIC_REPOSITORIES_ONLY",
        "repository_count": len(results), "manifest_inspections": len(selected_names),
        "counts": counts, "source_date": snapshot["observed_at"],
        "source_sha256": snapshot["snapshot_sha256"],
        "policy": {
            "si_aliases": "ADDITIVE_AND_BACKWARD_COMPATIBLE",
            "statutory_terms_and_existing_contracts": "PRESERVE",
            "safety_claims": "EVIDENCE_REQUIRED",
            "government_certification": False,
            "remote_writes": False, "auto_merge": False, "force_push": False,
            "code_execution": False, "secret_collection": False,
            "vulnerability_scope": "ONLY_TWO_SPECIFIED_GITHUB_ADVISORIES_IN_ROOT_NPM_LOCKFILES",
        },
        "repositories": results,
    }


def render_markdown(report: dict[str, Any]) -> str:
    c = report["counts"]
    lines = [
        "# GPT-Doug | Super Intelligence readiness — public Sonoxo fleet",
        "",
        "Source: [Executive Order 14434](" + EO_URL + "), signed September 29, 2026.",
        "The order governs federal executive-branch terminology; it is not a private-repo",
        "mandate, an SI capability certification, or proof of federal endorsement.",
        "",
        f"- Public repositories indexed: **{report['repository_count']}**",
        f"- Root-manifest inspections performed: **{report['manifest_inspections']}**",
        f"- Known advisory matches: **{c['advisory_found']}**",
        f"- Incomplete inspections: **{c['incomplete_evidence']}**",
        f"- Repositories not scanned for root manifests: **{c['not_scanned']}**",
        "",
        "Inspections are read-only. The only advisory checks are proxy-addr below",
        "2.0.8 (GHSA-jqcg-44mw-7w3h) and source-map-js below 1.2.2",
        "(GHSA-68fv-2mgg-jv7q), in the inspected root npm lockfiles.",
        "",
        "## Priority review queue",
        "",
    ]
    order = {"advisory_found": 0, "incomplete_evidence": 1,
             "review_current_evidence": 2, "not_scanned": 3}
    for row in sorted(report["repositories"], key=lambda r: (
            order[r["status"]], r["priority"] != "core_review", r["repo"].casefold())):
        title = row["repo"]
        lines.append(f"- [{title}](https://github.com/{title}) — **{row['status']}**")
        for finding in row["advisory_findings"]:
            lines.append(
                f"  - {finding['advisory']}: {finding['package']} "
                f"{finding['version']} → {finding['minimum_patched_version']} or later"
            )
    lines += [
        "", "## Required per-repository gates", "",
        "Verify ownership/fork license, supported upstream baseline, actual build and",
        "test commands, dependencies beyond root lockfiles, security/CI results,",
        "and the correct default branch before proposing an individual review PR.",
        "No changes are automatically pushed or merged. Keep established AI/API",
        "interfaces; use SI as an additive communication and taxonomy alias.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="EO 14434 public fleet SI readiness gate")
    parser.add_argument("--snapshot", type=Path, default=SNAPSHOT)
    parser.add_argument("--output", type=Path, default=Path("build/sonoxo-si"))
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--live", action="store_true", help="opt in to bounded public GitHub GETs")
    parser.add_argument("--force", action="store_true", help="replace local report files only")
    args = parser.parse_args(argv)
    try:
        snapshot = load_snapshot(args.snapshot)
        token = os.environ.get("GITHUB_TOKEN") if args.live else None
        fetch = (lambda r, b, p: github_public_text(r, b, p, token=token)) if args.live else None
        report = build_report(snapshot, limit=args.limit, fetch_text=fetch)
        out = args.output.expanduser()
        targets = (out / "si-readiness.json", out / "si-readiness.md")
        if not args.force and any(path.exists() for path in targets):
            raise AuditError("output exists; use --force only to replace local reports")
        out.mkdir(parents=True, exist_ok=True)
        targets[0].write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
        targets[1].write_text(render_markdown(report))
        print(json.dumps({
            "ok": True, "public_repositories": report["repository_count"],
            "inspected": report["manifest_inspections"], "counts": report["counts"],
            "remote_writes": 0, "report": str(targets[0]),
        }))
        return 0
    except (AuditError, OSError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "remote_writes": 0}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
