"""Sonoxo portfolio index and safe review-only upgrade plans.

Read-only against GitHub by default. Never writes remote repositories, merges
PRs, runs arbitrary repository code, modifies policies or fetches secrets.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import urllib.error
import urllib.request
from typing import Any

OWNER = "sonoxo"
SCHEMA = "sonoxo.portfolio.snapshot.v1"
REPORT_SCHEMA = "sonoxo.portfolio.upgrade-report.v1"
MAX_REPOS = 1000
MAX_RESPONSE_BYTES = 8_000_000
# Named integration points already established in the Sonoxo ecosystem.
# Other repositories are inventoried, never guessed to be safe to change.
PRIORITY = {
    "gpt-doug-llm": "brain_and_governance",
    "zyra": "zyra_application",
    "xuniadao": "xunia_governance",
    "ATAK-Maps": "map_source_registry",
    "atak-civ": "civilian_atak_plugin_source",
    "gods-eye-viewXUNIA": "geospatial_visualization",
    "MMGISxunia-": "geospatial_mapping",
    "zyrahawk": "research_workbench",
    "eyeris": "visual_interface",
    "CyberStrikeZYRA": "defensive_testing",
    "osirisanon": "osiris_viewer",
    "ZyraOS": "sandbox_runtime",
}
REPO_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,100}$")
BRANCH_NAME = re.compile(r"^[A-Za-z0-9_./-]{1,220}$")


class AuditError(ValueError):
    """Invalid inventory or unexpected GitHub response."""


def _sha(obj: Any) -> str:
    canonical = json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _validate_repo(entry: Any) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise AuditError("repository entry must be a JSON object")
    full_name = entry.get("full_name")
    if not isinstance(full_name, str) or not full_name.startswith(OWNER + "/"):
        raise AuditError("only sonoxo repositories can be indexed")
    name = full_name[len(OWNER) + 1:]
    if not REPO_NAME.fullmatch(name):
        raise AuditError("repository name has an unsupported character or length")
    branch = entry.get("default_branch")
    if not isinstance(branch, str) or not BRANCH_NAME.fullmatch(branch) or ".." in branch:
        raise AuditError(f"invalid default branch for {full_name}")
    visibility = entry.get("visibility", "public")
    if visibility != "public":
        # This integration is for published public repository metadata only.
        raise AuditError(f"cannot publish private repository metadata: {full_name}")
    archived = entry.get("archived", False)
    if type(archived) is not bool:
        raise AuditError(f"archived must be a boolean: {full_name}")
    size_kb = entry.get("size_kb", 0)
    if isinstance(size_kb, bool) or not isinstance(size_kb, int) or size_kb < 0:
        raise AuditError(f"invalid repository size: {full_name}")
    fork = entry.get("fork", None)
    if fork is not None and type(fork) is not bool:
        raise AuditError(f"fork must be null or bool: {full_name}")
    return {
        "full_name": full_name, "default_branch": branch,
        "visibility": visibility, "archived": archived,
        "fork": fork, "size_kb": size_kb,
    }


def snapshot_from_repos(entries: list[dict], *, observed_at: str, source: str) -> dict:
    if not isinstance(entries, list) or len(entries) > MAX_REPOS:
        raise AuditError(f"only 0..{MAX_REPOS} public repositories can be processed")
    by_name = {}
    for raw in entries:
        repo = _validate_repo(raw)
        key = repo["full_name"].casefold()
        if key in by_name:
            raise AuditError("duplicate repository identity: " + key)
        by_name[key] = repo
    records = sorted(by_name.values(), key=lambda x: x["full_name"].casefold())
    if not observed_at or len(observed_at) > 48:
        raise AuditError("observed_at must contain a timestamp or observation date")
    result = {
        "schema": SCHEMA, "owner": OWNER, "observed_at": observed_at,
        "source": source, "visibility_scope": "PUBLIC_REPOSITORIES_ONLY",
        "private_repositories_discovered": False,
        "repository_count": len(records), "repositories": records,
        "operations": {"read_only": True, "remote_writes": False, "force_push": False,
                       "auto_merge": False, "remote_code_execution": False},
    }
    result["snapshot_sha256"] = _sha(result["repositories"])
    return result


def validate_snapshot(value: Any) -> dict:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA or value.get("owner") != OWNER:
        raise AuditError("unsupported public Sonoxo snapshot schema")
    normalized = snapshot_from_repos(
        value.get("repositories", []), observed_at=value.get("observed_at", ""),
        source=value.get("source", "unknown"),
    )
    if normalized["repository_count"] != value.get("repository_count"):
        raise AuditError("declared repository count does not match entries")
    if normalized["snapshot_sha256"] != value.get("snapshot_sha256"):
        raise AuditError("snapshot digest mismatch")
    return normalized


def _validate_prs(items: Any) -> list[dict]:
    if items is None:
        return []
    if not isinstance(items, list) or len(items) > 2000:
        raise AuditError("invalid PR reference inventory")
    seen = set()
    result = []
    for pr in items:
        if not isinstance(pr, dict):
            raise AuditError("PR entry must be an object")
        url = pr.get("url")
        title = pr.get("title")
        if not isinstance(url, str) or not re.fullmatch(
            r"https://github[.]com/sonoxo/[A-Za-z0-9_.-]+/pull/[0-9]+", url
        ):
            raise AuditError("invalid public GitHub PR reference")
        if not isinstance(title, str) or not 1 <= len(title) <= 350:
            raise AuditError("invalid PR title")
        if url in seen:
            continue
        seen.add(url)
        result.append({"url": url, "title": title})
    return sorted(result, key=lambda x: x["url"].casefold())


def plan_upgrade(snapshot: Any, *, open_pull_requests: Any = None) -> dict:
    data = validate_snapshot(snapshot)
    refs = _validate_prs(open_pull_requests)
    prs_per_repo: Counter[str] = Counter()
    for pr in refs:
        repo = pr["url"].split("/")[4]
        prs_per_repo[repo.casefold()] += 1
    roles = []
    for repo in data["repositories"]:
        name = repo["full_name"].split("/", 1)[1]
        role = PRIORITY.get(name)
        blockers = []
        if repo["archived"]:
            blockers.append("archived")
        if repo["fork"] is None:
            blockers.append("fork_status_unverified")
        elif repo["fork"]:
            blockers.append("upstream_license_and_sync_review")
        # Branch protection and required CI checks are not represented in a
        # public search result, so they must not be invented as passing.
        blockers.extend(["required_checks_unverified", "release_compatibility_unverified"])
        candidate = bool(role) and not repo["archived"]
        roles.append({
            "repo": repo["full_name"],
            "default_branch": repo["default_branch"],
            "area": role or "unclassified_repository",
            "priority": "core_review" if candidate else "portfolio_inventory",
            "action": "OPEN_REVIEW_PR_IF_TESTED" if candidate else "AUDIT_THEN_SCOPE",
            "observed_open_prs": prs_per_repo[name.casefold()],
            "blockers": blockers,
            "auto_merge": False,
            "force_push": False,
            "secrets_access": False,
        })
    return {
        "schema": REPORT_SCHEMA, "scope": "SONOXO_PUBLIC_REPOSITORIES",
        "source_date": data["observed_at"],
        "source_sha256": data["snapshot_sha256"],
        "repositories_indexed": len(roles),
        "core_repositories": sum(r["priority"] == "core_review" for r in roles),
        "observed_open_prs": len(refs),
        "branches": dict(sorted(Counter(r["default_branch"] for r in data["repositories"]).items())),
        "archived": sum(r["archived"] for r in data["repositories"]),
        "fork_unknown": sum(r["fork"] is None for r in data["repositories"]),
        "default_policy": {
            "repository_write": "PROHIBITED_UNTIL_INDIVIDUAL_PR_REVIEW",
            "cross_repo_token_required": False,
            "auto_merge": False, "force_push": False,
            "private_repo_inventory": False,
            "third_party_code_reused": False,
            "workflow_execution": "READ_ONLY_INSPECTION",
            "patent_references": "ARCHITECTURE_ONLY_NOT_CODE_OWNERSHIP",
        },
        "gate_order": [
            "owner_and_license_verification",
            "baseline_revision_and_fork_check",
            "per_repo_dependency_diff",
            "tests_and_security_scan",
            "human_review_and_required_checks",
            "separate_approved_merge",
        ],
        "repositories": roles,
        "pull_requests": refs,
    }


def public_repo_inventory(
    *, token: str | None = None, fetch_json: Any = None, max_pages: int = 10
) -> dict:
    """Opt-in public GitHub user-repos GET only; never follows repo code or writes."""
    if not 1 <= max_pages <= 10:
        raise AuditError("page budget must be 1..10")
    if fetch_json is None:
        fetch_json = lambda url: _read_github_json(url, token=token)
    repos: list[dict] = []
    for page in range(1, max_pages + 1):
        # Endpoint and owner are constants. Never accept arbitrary URL/owner.
        url = f"https://api.github.com/users/{OWNER}/repos?per_page=100&page={page}&type=owner&sort=full_name"
        payload = fetch_json(url)
        if not isinstance(payload, list) or len(payload) > 100:
            raise AuditError("unexpected GitHub repository response")
        for entry in payload:
            if not isinstance(entry, dict):
                raise AuditError("unexpected repo object")
            full_name = entry.get("full_name")
            if entry.get("private") or entry.get("visibility") == "private":
                # Never index or export a private repo into public CI artifacts.
                continue
            if entry.get("owner", {}).get("login", "").casefold() != OWNER or not str(full_name).startswith(OWNER + "/"):
                raise AuditError("GitHub response contained wrong owner")
            repos.append({
                "full_name": full_name,
                "default_branch": entry.get("default_branch") or "main",
                "visibility": "public",
                "archived": entry.get("archived") is True,
                "fork": entry.get("fork") if isinstance(entry.get("fork"), bool) else None,
                "size_kb": entry.get("size", 0),
            })
        if len(payload) < 100:
            break
    else:
        raise AuditError("repository pagination exhausted page budget; increase approved budget")
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    return snapshot_from_repos(repos, observed_at=at, source="GITHUB_PUBLIC_USERS_API")


def _read_github_json(url: str, *, token: str | None) -> Any:
    req = urllib.request.Request(url, headers={
        "User-Agent": "gpt-doug-sonoxo-public-audit/1.0",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": "Bearer " + token} if token else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            if response.status != 200:
                raise AuditError(f"GitHub returned HTTP {response.status}")
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as exc:
        raise AuditError(f"GitHub public inventory HTTP {exc.code}; credentials are never logged") from None
    except (OSError, TimeoutError) as exc:
        raise AuditError("GitHub public inventory unavailable") from exc
    if len(content) > MAX_RESPONSE_BYTES:
        raise AuditError("GitHub public inventory response oversized")
    try:
        return json.loads(content.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditError("GitHub public inventory returned invalid JSON") from exc


def write_reports(snapshot: Any, output: Path, *, prs: Any = None, force: bool = False) -> dict:
    from .viewer import render_dashboard
    plan = plan_upgrade(snapshot, open_pull_requests=prs)
    output = Path(output).expanduser()
    names = ("summary.json", "upgrade-plan.json", "portfolio.html")
    if not force and any((output / name).exists() for name in names):
        raise AuditError("reports already exist; pass --force to replace generated outputs")
    output.mkdir(parents=True, exist_ok=True)
    summary = {k: v for k, v in plan.items() if k not in ("repositories", "pull_requests")}
    (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    (output / "upgrade-plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    (output / "portfolio.html").write_text(render_dashboard(plan), encoding="utf-8")
    return summary
