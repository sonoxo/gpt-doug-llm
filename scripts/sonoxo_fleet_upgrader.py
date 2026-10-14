#!/usr/bin/env python3
"""Read-only GitHub fleet dependency/CI readiness inventory.

This tool NEVER changes remote repositories. It reports where upgrade PRs
should be prepared and where an upstream fork requires careful review.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


ECO_SYSTEMS = (
    ("npm", {"package.json"}),
    ("pip", {"pyproject.toml", "requirements.txt", "Pipfile"}),
    ("docker", {"Dockerfile"}),
    ("gomod", {"go.mod"}),
    ("cargo", {"Cargo.toml"}),
    ("bundler", {"Gemfile"}),
    ("gradle", {"build.gradle", "build.gradle.kts"}),
    ("composer", {"composer.json"}),
)


class GitHubAPI:
    def __init__(self, token=None):
        self.token = token

    def get_json(self, path):
        request = Request(
            "https://api.github.com" + path,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "sonoxo-fleet-readonly-audit/1.0",
                "X-GitHub-Api-Version": "2022-11-28",
                **({"Authorization": f"Bearer {self.token}"} if self.token else {}),
            },
        )
        try:
            with urlopen(request, timeout=15) as response:
                return json.load(response)
        except HTTPError as exc:
            # No credentials, request bodies or bearer tokens in reports.
            raise RuntimeError(f"GitHub HTTP {exc.code} for {path}") from exc
        except (URLError, TimeoutError) as exc:
            raise RuntimeError(f"GitHub unavailable at {path}: {type(exc).__name__}") from exc


def _path_segment(value):
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", value) or value in {".", ".."}:
        raise ValueError("Invalid GitHub path segment")
    return quote(value, safe="")


def list_owner_repositories(api, owner):
    """Fetch every owned public repo page; omit unrelated owner results."""
    owner = _path_segment(owner)
    result = []
    page = 1
    while True:
        if page > 100:
            raise RuntimeError("GitHub repository pagination exceeded 100 pages")
        entries = api.get_json(f"/users/{owner}/repos?per_page=100&page={page}&type=owner")
        if not isinstance(entries, list):
            raise RuntimeError("Unexpected GitHub repositories response")
        result.extend(
            item for item in entries
            if item.get("owner", {}).get("login", "").casefold() == owner.casefold()
        )
        if len(entries) < 100:
            break
        page += 1
    # The API is sorted by GitHub; deduplicate by stable full name.
    return list({item["full_name"].casefold(): item for item in result}.values())


def detect_ecosystems(root_names, github_names):
    ecosystems = [name for name, manifests in ECO_SYSTEMS if manifests & root_names]
    if "workflows" in github_names:
        ecosystems.append("github-actions")
    return ecosystems


def classify_repository(repository, root_names, github_names, read_error=None):
    """Produce one conservative recommendation from observed repo state."""
    github_names = github_names or set()
    ecosystems = detect_ecosystems(root_names, github_names)
    result = {
        "full_name": repository["full_name"],
        "url": repository.get("html_url", ""),
        "default_branch": repository.get("default_branch"),
        "fork": bool(repository.get("fork")),
        "archived": bool(repository.get("archived")),
        "ecosystems": ecosystems,
        "dependabot": "dependabot.yml" in github_names or "dependabot.yaml" in github_names,
        "error": read_error,
    }
    if read_error:
        status = "inspection-error"
    elif result["archived"]:
        status = "archived-skip"
    elif result["fork"]:
        status = "upstream-sync-first"
    elif result["dependabot"]:
        status = "review-update-prs"
    elif ecosystems:
        status = "enable-dependabot"
    else:
        status = "manual-stack-review"
    result["recommendation"] = status
    return result


def scan_repositories(api, repositories):
    result = []
    for repository in repositories:
        owner, name = repository["full_name"].split("/", 1)
        path = f"/repos/{_path_segment(owner)}/{_path_segment(name)}/contents"
        try:
            root = api.get_json(path)
            if not isinstance(root, list):
                raise ValueError("Repository contents is not a file listing")
            root_names = {item["name"] for item in root}
            github_names = set()
            if ".github" in root_names:
                github = api.get_json(path + "/.github")
                if not isinstance(github, list):
                    raise ValueError(".github contents is not a file listing")
                github_names = {item["name"] for item in github}
            result.append(classify_repository(repository, root_names, github_names))
        except (RuntimeError, ValueError, KeyError, TypeError) as exc:
            result.append(classify_repository(repository, set(), None, str(exc)))
    return result


def render_markdown(records, owner):
    counts = Counter(row["recommendation"] for row in records)
    heading = [
        f"# {owner} fleet upgrade-readiness audit",
        "",
        f"**{len(records)} repositories inspected**. This is a **read-only** inventory,",
        "not a claim that dependencies were upgraded or CI passed.",
        "",
        "## Recommended next actions",
        "",
    ]
    for key in (
        "enable-dependabot", "review-update-prs", "upstream-sync-first",
        "manual-stack-review", "inspection-error", "archived-skip",
    ):
        heading.append(f"- {counts[key]} {key}")
    heading.extend([
        "",
        "**Important:** Only root-level manifests and GitHub Actions are detected.",
        "The public-owner API excludes private repos even when a token is supplied;",
        "nested manifests, upstream changes, CI outcomes and CVEs need separate review.",
        "",
        "| Repository | Fork | Ecosystems | Dependabot | Recommendation |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in sorted(records, key=lambda r: r["full_name"].casefold()):
        # Names originate in GitHub metadata, not user-generated HTML.
        repo_name = row["full_name"].replace("|", "-")
        repo_url = row["url"]
        if not repo_url.startswith("https://github.com/"):
            repo_url = "https://github.com/" + repo_name
        heading.append(
            f"| [{repo_name}]({repo_url}) | {row['fork']} | "
            f"{', '.join(row['ecosystems']) or '-'} | {row['dependabot']} | "
            f"{row['recommendation']} |"
        )
    return "\n".join(heading) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", default="sonoxo")
    parser.add_argument("--output-dir", type=Path, default=Path("reports/sonoxo-fleet"))
    parser.add_argument("--limit", type=int, default=0, help="Inventory first N repos (0=all)")
    args = parser.parse_args(argv)
    if args.limit < 0:
        parser.error("--limit must not be negative")
    api = GitHubAPI(os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN"))
    try:
        repos = list_owner_repositories(api, args.owner)
        if not repos:
            raise RuntimeError("No repositories were returned; verify owner/token")
        records = scan_repositories(api, repos[:args.limit] if args.limit else repos)
    except (RuntimeError, ValueError) as exc:
        print(f"Fleet audit failed: {exc}", file=sys.stderr)
        return 1
    args.output_dir.mkdir(parents=True, exist_ok=True)
    report = {
        "owner": args.owner,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "read_only": True,
        "partial": bool(args.limit) or len(records) != len(repos),
        "repository_count": len(records),
        "records": records,
    }
    (args.output_dir / "audit.json").write_text(json.dumps(report, indent=2) + "\n")
    (args.output_dir / "audit.md").write_text(render_markdown(records, args.owner))
    print(f"Scanned {len(records)} repositories; wrote reports to {args.output_dir}")
    print("Read-only: no changes, dependency bumps or PRs were performed.")
    return 0 if all(row["recommendation"] != "inspection-error" for row in records) else 2


if __name__ == "__main__":
    raise SystemExit(main())
