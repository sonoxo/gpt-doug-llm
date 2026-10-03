#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import pathlib
import shutil
import subprocess
import time
import urllib.parse
import urllib.request


def fetch_json(repo: str, resource: str):
    endpoint = f"repos/{repo}/{resource}"

    if shutil.which("gh"):
        p = subprocess.run(
            ["gh", "api", endpoint],
            capture_output=True,
            text=True,
        )
        if p.returncode == 0:
            return json.loads(p.stdout)

    url = "https://api.github.com/" + endpoint

    parsed = urllib.parse.urlsplit(url)

    if (
        parsed.scheme != "https"
        or parsed.hostname != "api.github.com"
        or parsed.username is not None
        or parsed.password is not None
        or parsed.port not in (None, 443)
    ):
        raise ValueError(
            "refusing non-HTTPS or unexpected GitHub API origin"
        )

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "gpt-doug-xzoon-live",
        },
    )

    # B310 is intentionally suppressed only after validating
    # the fixed HTTPS GitHub API origin above.
    with urllib.request.urlopen(  # nosec B310
        req,
        timeout=30,
    ) as r:
        return json.load(r)


def pos(key: str):
    h = hashlib.sha256(key.encode()).digest()

    lat = -65 + (
        int.from_bytes(h[:2], "big") / 65535
    ) * 130

    lon = -175 + (
        int.from_bytes(h[2:4], "big") / 65535
    ) * 350

    return round(lat, 4), round(lon, 4)


def atomically_write(path: pathlib.Path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")

    tmp.write_text(
        json.dumps(payload, indent=2) + "\n"
    )

    tmp.replace(path)


def build(repo: str, site: pathlib.Path):
    base_file = (
        site /
        "maven-ontology" /
        "ontology.base.json"
    )

    output_file = (
        site /
        "maven-ontology" /
        "ontology.json"
    )

    summary_file = (
        site /
        "planet-xzoon" /
        "github-live.json"
    )

    base = json.loads(base_file.read_text())

    commits = fetch_json(
        repo,
        "commits?per_page=25"
    )

    branches = fetch_json(
        repo,
        "branches?per_page=100"
    )

    pulls = fetch_json(
        repo,
        "pulls?state=open&per_page=100"
    )

    nodes = list(base.get("nodes", []))
    links = list(base.get("links", []))

    repo_id = "github:repo:" + repo

    lat, lon = pos(repo_id)

    nodes.append({
        "id": repo_id,
        "label": repo,
        "objectType": "GitHubRepository",
        "type": "governance",
        "lat": lat,
        "lon": lon,
        "status": "verified",
        "confidence": 1.0,
        "desc": "Live GitHub repository activity.",
        "provenance": {
            "sourceSystem": "GitHub API",
            "repository": repo,
        },
    })

    commit_ids = {}

    for commit in commits:
        sha = commit["sha"]
        cid = "github:commit:" + sha
        commit_ids[sha] = cid

        lat, lon = pos(cid)

        info = commit.get("commit", {})
        message = (
            info.get("message", "")
            .splitlines()[0]
        )

        author = info.get("author") or {}

        nodes.append({
            "id": cid,
            "label": (
                sha[:7] + " · " +
                message[:52]
            ),
            "objectType": "GitCommit",
            "type": "knowledge",
            "lat": lat,
            "lon": lon,
            "status": "verified",
            "confidence": 1.0,
            "desc": message,
            "provenance": {
                "sourceSystem": "GitHub API",
                "sha": sha,
                "url": commit.get("html_url"),
                "date": author.get("date"),
            },
        })

        links.append([
            repo_id,
            cid,
            "HAS_COMMIT",
        ])

    for branch in branches:
        name = branch["name"]
        bid = "github:branch:" + name

        lat, lon = pos(bid)

        nodes.append({
            "id": bid,
            "label": "branch/" + name,
            "objectType": "GitBranch",
            "type": "system",
            "lat": lat,
            "lon": lon,
            "status": "verified",
            "confidence": 1.0,
            "desc": "Live GitHub branch.",
            "provenance": {
                "sourceSystem": "GitHub API",
                "branch": name,
                "headSha": branch["commit"]["sha"],
            },
        })

        links.append([
            repo_id,
            bid,
            "HAS_BRANCH",
        ])

        sha = branch["commit"]["sha"]

        if sha in commit_ids:
            links.append([
                bid,
                commit_ids[sha],
                "POINTS_TO",
            ])

    for pr in pulls:
        number = pr["number"]
        pid = f"github:pr:{number}"

        lat, lon = pos(pid)

        nodes.append({
            "id": pid,
            "label": (
                f"PR #{number} · " +
                pr.get("title", "")[:48]
            ),
            "objectType": "PullRequest",
            "type": "governance",
            "lat": lat,
            "lon": lon,
            "status": "candidate" if pr.get("draft") else "verified",
            "confidence": 0.95,
            "desc": pr.get("title", ""),
            "provenance": {
                "sourceSystem": "GitHub API",
                "number": number,
                "url": pr.get("html_url"),
                "draft": pr.get("draft"),
                "head": pr.get("head", {}).get("ref"),
                "base": pr.get("base", {}).get("ref"),
            },
        })

        links.append([
            repo_id,
            pid,
            "HAS_OPEN_PR",
        ])

    node_map = {}

    for node in nodes:
        node_map[node["id"]] = node

    nodes = list(node_map.values())

    seen = set()
    unique_links = []

    for edge in links:
        key = tuple(edge)

        if key not in seen:
            seen.add(key)
            unique_links.append(edge)

    links = unique_links

    fingerprint = hashlib.sha256(
        json.dumps(
            {
                "nodes": nodes,
                "links": links,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()

    old_fingerprint = None

    if output_file.exists():
        try:
            previous = json.loads(
                output_file.read_text()
            )
            old_fingerprint = (
                previous
                .get("meta", {})
                .get("liveSync", {})
                .get("graphFingerprint")
            )
        except Exception:
            pass

    changed = fingerprint != old_fingerprint

    now = (
        datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat()
    )

    meta = base.setdefault("meta", {})
    sync = meta.setdefault("liveSync", {})

    sync.update({
        "mode": "REAL_FOUNDRY_MAVEN_PLUS_GITHUB",
        "githubRepository": repo,
        "githubPolling": True,
        "githubCommitCount": len(commits),
        "githubBranchCount": len(branches),
        "githubOpenPrCount": len(pulls),
        "githubHeadSha": (
            commits[0]["sha"]
            if commits else None
        ),
        "graphFingerprint": fingerprint,
        "githubUpdatedAt": now,
        "credentialsStored": False,
    })

    base["nodes"] = nodes
    base["links"] = links

    atomically_write(
        output_file,
        base,
    )

    latest = None

    if commits:
        c = commits[0]

        latest = {
            "sha": c["sha"],
            "shortSha": c["sha"][:7],
            "message": (
                c.get("commit", {})
                .get("message", "")
                .splitlines()[0]
            ),
            "url": c.get("html_url"),
            "date": (
                c.get("commit", {})
                .get("author", {})
                .get("date")
            ),
        }

    summary = {
        "schema": "xunia.xzoon.github-live.v1",
        "repository": repo,
        "polledAt": now,
        "changed": changed,
        "headSha": (
            commits[0]["sha"]
            if commits else None
        ),
        "fingerprint": fingerprint,
        "commits": len(commits),
        "branches": len(branches),
        "openPullRequests": len(pulls),
        "latestCommit": latest,
    }

    atomically_write(
        summary_file,
        summary,
    )

    return summary


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--repo",
        required=True,
    )

    parser.add_argument(
        "--site",
        required=True,
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=10,
    )

    args = parser.parse_args()

    site = pathlib.Path(args.site)

    while True:
        try:
            summary = build(
                args.repo,
                site,
            )

            print(
                datetime.datetime.now().isoformat(),
                summary["headSha"][:7]
                if summary["headSha"]
                else "none",
                "changed=" + str(summary["changed"]),
                "commits=" + str(summary["commits"]),
                "branches=" + str(summary["branches"]),
                "prs=" + str(summary["openPullRequests"]),
                flush=True,
            )

        except Exception as exc:
            print(
                "SYNC ERROR:",
                type(exc).__name__,
                str(exc),
                flush=True,
            )

        time.sleep(
            max(5, args.interval)
        )


if __name__ == "__main__":
    main()
