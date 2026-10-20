#!/usr/bin/env python3
"""Read-only cloud public GitHub repo clone runner. No third-party code execution."""
import argparse
import concurrent.futures
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import urllib.parse
import urllib.request

QUERIES = {
    "global": "stars:>150000 archived:false fork:false",
    "ai": "topic:llm stars:>10000 archived:false fork:false",
    "pqc": "post-quantum cryptography stars:>100",
}
NAME = re.compile(r"[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+\Z")

def github_api(path, params):
    url = "https://api.github.com" + path + "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "GPT-Doug-Cloud-Clone/1.0"}
    token = os.environ.get("GH_READ_TOKEN", "")
    if token:
        headers["Authorization"] = "Bearer " + token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30) as response:
        return json.load(response)

def discover(category):
    count = 25 if category == "sonoxo" else 20
    if category == "sonoxo":
        data = github_api("/users/sonoxo/repos", {"per_page": count, "sort": "updated", "direction": "desc", "type": "owner"})
        names = [item["full_name"] for item in data if not item.get("private")]
    else:
        data = github_api("/search/repositories", {"q": QUERIES[category], "sort": "stars", "order": "desc", "per_page": count})
        names = [item["full_name"] for item in data["items"]]
    names = names[:count]
    if len(names) != count or len(set(n.lower() for n in names)) != len(names):
        raise RuntimeError("Discovery did not return the expected number of unique repositories")
    return names

def clone(name, base):
    record = {"repo": name}
    if not NAME.fullmatch(name) or any(seg in {".", ".."} for seg in name.split("/")):
        record["status"] = "invalid_name"
        return record
    target = base / "repos" / name
    target.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(GIT_LFS_SKIP_SMUDGE="1", GIT_TERMINAL_PROMPT="0")
    try:
        cmd = ["git", "-c", "core.hooksPath=/dev/null", "clone", "--depth=1", "--filter=blob:none",
               "--single-branch", "--no-tags", "https://github.com/" + name + ".git", str(target)]
        p = subprocess.run(cmd, env=env, text=True, capture_output=True, timeout=480)
        if p.returncode:
            record.update(status="failed", reason=(p.stderr or p.stdout)[-700:])
            return record
        verify = subprocess.run(["git", "-C", str(target), "rev-parse", "HEAD"], env=env,
                                text=True, capture_output=True, timeout=30)
        if verify.returncode:
            record.update(status="failed_verification", reason=verify.stderr[-700:])
            return record
        record.update(status="cloned", commit=verify.stdout.strip())
    except (OSError, subprocess.TimeoutExpired) as exc:
        record.update(status="failed", reason=str(exc)[-700:])
    return record

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--category", required=True, choices=["global", "ai", "pqc", "sonoxo"])
    parser.add_argument("--destination", required=True, type=Path)
    opts = parser.parse_args()
    root = opts.destination / opts.category
    root.mkdir(parents=True, exist_ok=True)
    report_path = root / "clone-report.json"
    try:
        repos = discover(opts.category)
        print("Discovered", len(repos), opts.category, "repositories", flush=True)
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(clone, name, root) for name in repos]
            results = []
            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                results.append(result)
                print(result["status"], result["repo"], flush=True)
        results.sort(key=lambda x: x["repo"].lower())
        summary = {status: sum(r["status"] == status for r in results)
                   for status in sorted(set(r["status"] for r in results))}
        report = {"timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                  "category": opts.category, "selected": len(repos), "summary": summary,
                  "repository_results": results,
                  "note": "Clones held on a cloud runner; cache only within free allowance."}
        status = 0 if len(results) == summary.get("cloned", 0) else 1
    except Exception as exc:
        report = {"category": opts.category, "error": str(exc), "status": "discovery_failed"}
        status = 1
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as out:
            out.write("### Cloud GitHub clone: " + opts.category + "\n\n")
            out.write(json.dumps(report.get("summary", report), indent=2) + "\n")
    print("Report:", report_path, flush=True)
    return status

if __name__ == "__main__":
    sys.exit(main())
