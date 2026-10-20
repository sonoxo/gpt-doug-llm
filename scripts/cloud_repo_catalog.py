#!/usr/bin/env python3
"""Fail-closed catalog of cloud clones proven recoverable from Actions caches."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import sys

CATEGORIES = ("global", "ai", "pqc", "sonoxo")


def load_reports(folder: Path, filename: str) -> dict[tuple[str, int], dict]:
    found = {}
    for path in folder.rglob(filename):
        report = json.loads(path.read_text(encoding="utf-8"))
        if report.get("schema_version") != 1:
            raise ValueError(f"Unexpected report format: {path}")
        key = (report.get("category"), report.get("shard"))
        if key in found:
            raise ValueError(f"Duplicate {filename} for {key}")
        found[key] = report
    return found


def compile_catalog(targets: dict, clones: dict, restores: dict, *, shards: int, run_url: str) -> dict:
    if targets.get("schema_version") != 1:
        raise ValueError("Target schema mismatch")
    target_groups = targets["categories"]
    if set(target_groups) != set(CATEGORIES):
        raise ValueError("Wrong categories in targets")
    expected_keys = {(category, shard) for category in CATEGORIES for shard in range(shards)}
    if set(clones) != expected_keys or set(restores) != expected_keys:
        raise ValueError(f"Missing shard reports: clone={sorted(set(expected_keys)-set(clones))}, "
                         f"verify={sorted(set(expected_keys)-set(restores))}")
    catalog: dict[str, dict] = {}
    total_attempts = 0
    total_bytes = 0
    for category in CATEGORIES:
        names = target_groups[category]
        for shard in range(shards):
            key = (category, shard)
            clone_report, verify_report = clones[key], restores[key]
            selected = names[shard::shards]
            count = len(selected)
            if any(report.get("selected") != count or report.get("success") != count
                   or report.get("shard_count") != shards for report in (clone_report, verify_report)):
                raise ValueError(f"Incomplete clone or offline verification in {key}")
            expected_clone = {r["repo"]: r for r in clone_report["repositories"]}
            expected_verified = {r["repo"]: r for r in verify_report["repositories"]}
            if set(expected_clone) != set(selected) or set(expected_verified) != set(selected):
                raise ValueError(f"Unexpected repository identities in {key}")
            for name in selected:
                a = expected_clone[name]
                b = expected_verified[name]
                if (a.get("status") != "cloned" or b.get("status") != "restored_offline"
                        or a.get("sha") != b.get("sha") or not a.get("tracked_blobs")
                        or not b.get("tracked_blobs")
                        or a.get("tracked_blobs") != b.get("tracked_blobs")
                        or len(a.get("sha", "")) != 40):
                    raise ValueError(f"Failed offline recovery or SHA check: {category} {name}")
                existing = catalog.setdefault(name.casefold(), {"repository": name, "categories": [], "snapshots": []})
                existing["categories"].append(category)
                existing["snapshots"].append({"category": category,
                                              "shard": shard,
                                              "sha": a["sha"],
                                              "git_bytes": a["git_bytes"],
                                              "tracked_blobs": a["tracked_blobs"],
                                              "cache_key": f"cloud-git-v3-{targets['cache_version']}-{category}-{shard}"})
                total_attempts += 1
                total_bytes += a["git_bytes"]
    return {
        "schema_version": 1,
        "generated_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_url": run_url,
        "catalog_status": "all_selected_repositories_cloned_and_restored_offline",
        "selected_clones": total_attempts,
        "unique_repositories": len(catalog),
        "restored_clones": total_attempts,
        "total_uncompressed_git_bytes": total_bytes,
        "storage": {"backend": "GitHub Actions cache (ephemeral)",
                    "budget_cap_bytes": 10 * 1024 ** 3,
                    "expiration": "Caches may be evicted after 7 days without access; source catalog remains in GitHub",
                    "checkout": "Git object directories only; restore with offline git reset --hard HEAD"},
        "repositories": [catalog[key] for key in sorted(catalog)],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--targets", type=Path, required=True)
    parser.add_argument("--clone-reports", type=Path, required=True)
    parser.add_argument("--verify-reports", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--shards", type=int, default=4)
    parser.add_argument("--run-url", type=str, required=True)
    args = parser.parse_args()
    try:
        target_text = args.targets.read_text(encoding="utf-8")
        targets = json.loads(target_text)
        targets["cache_version"] = hashlib.sha256(hashlib.sha256(target_text.encode("utf-8")).digest()).hexdigest()
        clones = load_reports(args.clone_reports, "clone-report.json")
        verifies = load_reports(args.verify_reports, "verify-report.json")
        catalog = compile_catalog(targets, clones, verifies, shards=args.shards, run_url=args.run_url)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(catalog, indent=2) + "\n", encoding="utf-8")
        print(f"VERIFIED {catalog['restored_clones']} cloned repository operations; "
              f"{catalog['unique_repositories']} unique repositories", flush=True)
        return 0
    except Exception as error:
        print("CATALOG FAILED:", error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
