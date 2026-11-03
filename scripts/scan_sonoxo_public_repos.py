#!/usr/bin/env python3
"""Public-only XUNIA GitHub ecosystem metadata scan. Never clones or executes code.

Requires only Python standard library. This script reads the public /users/sonoxo/repos
GitHub API and can enrich a checked-in public-only snapshot. It does not assess
vulnerabilities, private repositories, authentication, tokens or runtime dependencies.
"""
from __future__ import annotations
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

OWNER = "sonoxo"
BASE = "https://api.github.com/users/sonoxo/repos"
DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[1] / "docs/ecosystem-observatory/snapshot.json"
MAX_PAGES = 8

def is_public_repo(value: dict) -> bool:
    if not isinstance(value, dict):
        return False
    owner = value.get("owner") or {}
    name = value.get("full_name")
    return (owner.get("login") == OWNER and isinstance(name, str)
            and name.startswith(OWNER + "/") and len(name.split("/")) == 2
            and value.get("private") is False and value.get("visibility") != "private")

def normalize(repo: dict, previous: dict | None = None) -> dict:
    if not is_public_repo(repo):
        raise ValueError("Nonpublic or invalid repository refused")
    previous = previous or {}
    return {
        "id": repo["full_name"], "name": repo["name"],
        "url": "https://github.com/" + repo["full_name"],
        "defaultBranch": repo.get("default_branch") or None,
        "archived": repo.get("archived") is True,
        "sizeKB": repo.get("size"),
        "category": previous.get("category", "Other public repositories"),
        "classificationBasis": previous.get("classificationBasis", "unclassified"),
        "language": repo.get("language"),
        "pushedAt": repo.get("pushed_at"),
        "stars": repo.get("stargazers_count"),
        "openIssues": repo.get("open_issues_count"),
        "fork": repo.get("fork") is True,
    }

def page_url(page: int) -> str:
    if not 1 <= page <= MAX_PAGES:
        raise ValueError("Page outside bounded public API scope")
    return f"{BASE}?per_page=100&type=owner&sort=updated&page={page}"

def fetch_page(page: int) -> list[dict]:
    req = Request(page_url(page), headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "XUNIA-Ecosystem-Observatory/1.0",
    })
    with urlopen(req, timeout=20) as resp:
        payload = json.load(resp)
    if not isinstance(payload, list):
        raise ValueError("Unexpected GitHub API response")
    return payload

def scan(snapshot: dict, fetcher=fetch_page) -> dict:
    existing = {r["id"]:r for r in snapshot.get("repositories", []) if r.get("id", "").startswith("sonoxo/")}
    found: dict[str, dict] = {}
    completed = False
    for page in range(1, MAX_PAGES + 1):
        entries = fetcher(page)
        for item in entries:
            if is_public_repo(item):
                found[item["full_name"]] = normalize(item, existing.get(item["full_name"]))
        if len(entries) < 100:
            completed = True
            break
    if not completed:
        raise ValueError("Scan stopped at page safety limit without complete pagination")
    if not found:
        raise ValueError("GitHub returned no public repositories; snapshot unchanged")
    cats: dict[str,int] = {}
    for entry in found.values():
        cats[entry["category"]] = cats.get(entry["category"], 0) + 1
    return {
        "schema": "xunia.public-repo-scan.v1", "owner": OWNER,
        "snapshotDate": datetime.now(timezone.utc).isoformat(),
        "collection": "GitHub public REST API: /users/sonoxo/repos, all pages",
        "coverage": {"publicRepositories": len(found), "excludedNonpublic": None,
                     "totalAccessibleFound": None, "paginationComplete": True},
        "confidence": {"ownership": "GitHub public API",
                       "categories": "existing curated museum categories preserved; new repos unclassified",
                       "runtimeIntegration": "not assessed", "securityStatus": "not assessed"},
        "relationshipTypes": snapshot.get("relationshipTypes", []),
        "knownLinks": snapshot.get("knownLinks", []),
        "categories": cats,
        "repositories": sorted(found.values(), key=lambda r:r["id"].lower()),
    }

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    parser.add_argument("--out", type=Path, default=None,
                        help="Write live scan to this path; original snapshot remains unchanged")
    args = parser.parse_args()
    try:
        prior = json.loads(args.snapshot.read_text(encoding="utf-8"))
        if prior.get("schema") != "xunia.public-repo-scan.v1":
            raise ValueError("Wrong baseline inventory schema")
        result = scan(prior)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print("Wrote public-only metadata:", args.out)
        else:
            print(json.dumps({"publicRepositories": len(result["repositories"]),
                              "categories": result["categories"],
                              "at": result["snapshotDate"],
                              "noCodeExecution": True}, indent=2))
        return 0
    except (OSError, ValueError, HTTPError, URLError) as exc:
        print("XUNIA SCAN FAILED CLOSED:", exc, file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
