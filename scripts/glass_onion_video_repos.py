#!/usr/bin/env python3
"""Glass Onion: stage cited GitHub repositories from a verified video transcript/description.

Usage:
  python3 scripts/glass_onion_video_repos.py video-description.txt
  python3 scripts/glass_onion_video_repos.py video-description.txt --clone

This tool does not treat a video URL as proof of any repository. It extracts
explicit GitHub URLs from supplied text, produces a provenance manifest, and
optionally clones repositories into an isolated, gitignored staging directory.
No code is executed, dependencies installed, or upstream files merged.
"""
import argparse
import json
import re
import subprocess
from pathlib import Path

VIDEO = "https://www.youtube.com/watch?v=rmkXyB6JBX8&t=166s"
PATTERN = re.compile(r"https?://(?:www\\.)?github\\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)", re.I)
DENY = {".", ".."}

def extract(text):
    found = {}
    for owner, name in PATTERN.findall(text):
        name = name.removesuffix(".git")
        if owner in DENY or name in DENY:
            continue
        key = f"{owner}/{name}"
        found[key.lower()] = {"repository": key, "url": f"https://github.com/{key}", "source": VIDEO, "verified": False}
    return sorted(found.values(), key=lambda r: r["repository"].lower())

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="Saved video description or transcript")
    parser.add_argument("--clone", action="store_true", help="Clone into isolated staging")
    parser.add_argument("--dest", type=Path, default=Path("glass-onion-staging"))
    args = parser.parse_args()
    records = extract(args.source.read_text(encoding="utf-8"))
    args.dest.mkdir(parents=True, exist_ok=True)
    for record in records:
        if not args.clone:
            record["status"] = "discovered_not_cloned"
            continue
        target = args.dest / record["repository"]
        if target.exists():
            record["status"] = "already_exists"
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run(["git", "clone", "--depth", "1", "--", record["url"] + ".git", str(target)], capture_output=True, text=True, check=False)
        record["status"] = "cloned" if result.returncode == 0 else "clone_failed"
        if result.returncode:
            record["error"] = result.stderr[-500:]
    manifest = args.dest / "video-repositories.json"
    manifest.write_text(json.dumps({"source": VIDEO, "repositories": records}, indent=2) + "\n", encoding="utf-8")
    print(f"{len(records)} explicit repositories found; manifest: {manifest}")
    for r in records:
        print(f'{r["status"]}: {r["repository"]}')

if __name__ == "__main__":
    main()
