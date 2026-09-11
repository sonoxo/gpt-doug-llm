#!/usr/bin/env python3

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import subprocess
import time

ROOT = pathlib.Path(__file__).resolve().parents[1]
REL = "docs/maven-ontology/ontology.json"


def git(*args):
    p = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    return p


def fingerprint(graph):
    return hashlib.sha256(
        json.dumps(
            {
                "nodes": graph.get("nodes", []),
                "links": graph.get("links", []),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def parse_time(value):
    if not value or not isinstance(value, str):
        return None

    try:
        value = value.replace("Z", "+00:00")
        parsed = dt.datetime.fromisoformat(value)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt.timezone.utc)

        return parsed.astimezone(dt.timezone.utc)
    except Exception:
        return None


def node_timestamp(node):
    p = node.get("provenance", {}) or {}
    u = p.get("upstream", {}) or {}

    candidates = [
        p.get("generatedAt"),
        p.get("approvedAt"),
        p.get("verifiedAt"),
        p.get("createdAt"),
        p.get("date"),
        u.get("generatedAt"),
        u.get("approvedAt"),
        u.get("verifiedAt"),
        u.get("date"),
    ]

    valid = [
        parse_time(x)
        for x in candidates
        if parse_time(x)
    ]

    return max(valid) if valid else None


def metrics(graph):
    nodes = graph.get("nodes", [])
    links = graph.get("links", [])

    ids = {
        n.get("id")
        for n in nodes
        if n.get("id")
    }

    degree = {
        node_id: 0
        for node_id in ids
    }

    dangling = []

    for edge in links:
        if len(edge) < 3:
            continue

        a, b = edge[0], edge[1]

        if a not in ids or b not in ids:
            dangling.append(edge)
            continue

        degree[a] += 1
        degree[b] += 1

    now = dt.datetime.now(dt.timezone.utc)

    low_trust = [
        n.get("id")
        for n in nodes
        if float(n.get("confidence", 0) or 0) < 0.95
    ]

    stale = []

    for node in nodes:
        ts = node_timestamp(node)

        if ts and (
            now - ts
        ).total_seconds() > 86400:
            stale.append(node.get("id"))

    orphans = [
        node_id
        for node_id, count in degree.items()
        if count == 0
    ]

    return {
        "nodes": len(nodes),
        "links": len(links),
        "verified": sum(
            1
            for n in nodes
            if n.get("status") == "verified"
        ),
        "lowTrust": low_trust,
        "stale24h": stale,
        "orphans": orphans,
        "danglingLinks": dangling,
    }


def diff_graph(old, new):
    if old is None:
        return {
            "addedNodes": [],
            "removedNodes": [],
            "addedLinks": [],
            "removedLinks": [],
            "schemaChanged": False,
            "schemaReviewRequired": False,
        }

    old_nodes = {
        n.get("id")
        for n in old.get("nodes", [])
    }

    new_nodes = {
        n.get("id")
        for n in new.get("nodes", [])
    }

    old_links = {
        tuple(x)
        for x in old.get("links", [])
    }

    new_links = {
        tuple(x)
        for x in new.get("links", [])
    }

    old_obj = set(
        old.get("objectTypes", [])
    )

    new_obj = set(
        new.get("objectTypes", [])
    )

    old_rel = set(
        old.get("relationTypes", [])
    )

    new_rel = set(
        new.get("relationTypes", [])
    )

    schema_changed = (
        old_obj != new_obj
        or old_rel != new_rel
    )

    return {
        "addedNodes": sorted(
            new_nodes - old_nodes
        ),
        "removedNodes": sorted(
            old_nodes - new_nodes
        ),
        "addedLinks": [
            list(x)
            for x in sorted(
                new_links - old_links
            )
        ],
        "removedLinks": [
            list(x)
            for x in sorted(
                old_links - new_links
            )
        ],
        "schemaChanged": schema_changed,
        "schemaReviewRequired": schema_changed,
    }


def graph_at_commit(sha):
    p = git(
        "show",
        f"{sha}:{REL}",
    )

    if p.returncode != 0:
        return None

    try:
        return json.loads(p.stdout)
    except Exception:
        return None


def commit_rows(limit):
    p = git(
        "log",
        "--all",
        f"-n{limit}",
        "--format=%H%x1f%cI%x1f%s",
        "--",
        REL,
    )

    if p.returncode != 0:
        return []

    rows = []

    for line in p.stdout.splitlines():
        parts = line.split("\x1f", 2)

        if len(parts) == 3:
            rows.append(parts)

    rows.reverse()

    return rows


def build(current_path, limit):
    snapshots = []
    previous = None

    for sha, date, message in commit_rows(limit):
        graph = graph_at_commit(sha)

        if not graph:
            continue

        fp = fingerprint(graph)

        snapshots.append({
            "kind": "git",
            "sha": sha,
            "shortSha": sha[:8],
            "date": date,
            "message": message,
            "fingerprint": fp,
            "metrics": metrics(graph),
            "drift": diff_graph(
                previous,
                graph,
            ),
            "graph": graph,
        })

        previous = graph

    if current_path and current_path.exists():
        try:
            current = json.loads(
                current_path.read_text()
            )

            fp = fingerprint(current)

            if (
                not snapshots
                or snapshots[-1]["fingerprint"] != fp
            ):
                snapshots.append({
                    "kind": "live",
                    "sha": git(
                        "rev-parse",
                        "HEAD",
                    ).stdout.strip(),
                    "shortSha": git(
                        "rev-parse",
                        "--short=8",
                        "HEAD",
                    ).stdout.strip(),
                    "date": dt.datetime.now(
                        dt.timezone.utc
                    ).isoformat(),
                    "message": "Current live xZOON graph",
                    "fingerprint": fp,
                    "metrics": metrics(current),
                    "drift": diff_graph(
                        previous,
                        current,
                    ),
                    "graph": current,
                })
        except Exception:
            pass

    return {
        "schema": "xunia.xzoon.history.v1",
        "builtAt": dt.datetime.now(
            dt.timezone.utc
        ).isoformat(),
        "snapshots": snapshots,
    }


def write_atomic(path, payload):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    tmp = path.with_suffix(
        path.suffix + ".tmp"
    )

    tmp.write_text(
        json.dumps(
            payload,
            indent=2,
        ) + "\n"
    )

    tmp.replace(path)


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--out",
        required=True,
    )

    parser.add_argument(
        "--current",
    )

    parser.add_argument(
        "--limit",
        type=int,
        default=80,
    )

    parser.add_argument(
        "--watch",
        type=int,
        default=0,
    )

    args = parser.parse_args()

    output = pathlib.Path(args.out)

    current = (
        pathlib.Path(args.current)
        if args.current
        else None
    )

    while True:
        payload = build(
            current,
            max(1, args.limit),
        )

        write_atomic(
            output,
            payload,
        )

        print(
            "xZOON HISTORY",
            "snapshots=",
            len(payload["snapshots"]),
            "built=",
            payload["builtAt"],
            flush=True,
        )

        if args.watch <= 0:
            break

        time.sleep(
            max(5, args.watch)
        )


if __name__ == "__main__":
    main()
