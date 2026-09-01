"""Free local change watcher for the XUNIA realtime runtime.

Watches local Git repositories or filesystem paths and submits an already-scoped engagement
manifest to the loopback runtime when meaningful changes are detected. No third-party API or
watcher dependency is required.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen


def _digest_path(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_file():
        stat = path.stat()
        material = f"{path}:{stat.st_mtime_ns}:{stat.st_size}".encode()
        return hashlib.sha256(material).hexdigest()
    digest = hashlib.sha256()
    count = 0
    for item in sorted(path.rglob("*")):
        if count >= 10_000:
            break
        if any(part in {".git", "node_modules", ".venv", "venv", "dist", "build"} for part in item.parts):
            continue
        if not item.is_file():
            continue
        try:
            stat = item.stat()
        except OSError:
            continue
        digest.update(str(item.relative_to(path)).encode())
        digest.update(str(stat.st_mtime_ns).encode())
        digest.update(str(stat.st_size).encode())
        count += 1
    return digest.hexdigest()


def _git_state(path: Path) -> str:
    git = path / ".git"
    if not git.exists():
        raise ValueError(f"NOT_A_GIT_REPOSITORY:{path}")
    head = (git / "HEAD").read_text(encoding="utf-8").strip()
    if head.startswith("ref: "):
        ref = git / head[5:]
        commit = ref.read_text(encoding="utf-8").strip() if ref.exists() else head
    else:
        commit = head
    index = git / "index"
    index_state = _digest_path(index)
    return hashlib.sha256(f"{commit}:{index_state}".encode()).hexdigest()


def _load_manifest(entry: dict[str, Any], config_dir: Path) -> dict[str, Any]:
    if isinstance(entry.get("manifest"), dict):
        return dict(entry["manifest"])
    manifest_file = entry.get("manifestFile")
    if not manifest_file:
        raise ValueError("WATCH_MANIFEST_REQUIRED")
    path = (config_dir / str(manifest_file)).resolve()
    return json.loads(path.read_text(encoding="utf-8"))


def _submit(runtime_url: str, manifest: dict[str, Any], token: str | None) -> str:
    payload = json.dumps({"manifest": manifest}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{runtime_url.rstrip('/')}/v1/jobs", data=payload, headers=headers, method="POST")
    with urlopen(request, timeout=10) as response:  # noqa: S310 - URL is operator-controlled local runtime config
        data = json.loads(response.read().decode("utf-8"))
    return str(data["jobId"])


def run(config_path: str) -> None:
    source = Path(config_path).resolve()
    config = json.loads(source.read_text(encoding="utf-8"))
    runtime_url = str(config.get("runtimeUrl", "http://127.0.0.1:8765"))
    if not runtime_url.startswith(("http://127.0.0.1", "http://localhost", "http://[::1]")) and os.getenv("XUNIA_WATCH_ALLOW_REMOTE") != "1":
        raise PermissionError("WATCH_REMOTE_RUNTIME_DENIED")
    interval = max(1.0, float(config.get("pollSeconds", 2)))
    debounce = max(1.0, float(config.get("debounceSeconds", 3)))
    token = os.getenv("XUNIA_LOCAL_TOKEN")
    watches = list(config.get("watches", []))
    if not watches:
        raise ValueError("WATCH_ENTRY_REQUIRED")

    state: dict[str, str] = {}
    last_trigger: dict[str, float] = {}
    print(f"XUNIA watcher active: {len(watches)} watch(es), polling every {interval:g}s")
    while True:
        for index, entry in enumerate(watches):
            key = str(entry.get("name", f"watch-{index}"))
            watch_type = str(entry.get("type", "path"))
            path = Path(str(entry.get("path", "."))).expanduser().resolve()
            current = _git_state(path) if watch_type == "git" else _digest_path(path)
            previous = state.get(key)
            state[key] = current
            if previous is None or previous == current:
                continue
            now = time.monotonic()
            if now - last_trigger.get(key, 0.0) < debounce:
                continue
            manifest = _load_manifest(entry, source.parent)
            timestamp = int(time.time())
            manifest["engagementId"] = f"{manifest['engagementId']}-watch-{timestamp}"
            from datetime import datetime, timedelta, timezone

            start = datetime.now(timezone.utc)
            manifest["startsAt"] = start.isoformat()
            manifest["endsAt"] = (start + timedelta(hours=1)).isoformat()
            try:
                job_id = _submit(runtime_url, manifest, token)
                last_trigger[key] = now
                print(f"[{key}] change detected -> queued {job_id}")
            except (URLError, OSError, KeyError, ValueError) as exc:
                print(f"[{key}] trigger failed: {exc}")
        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="Watch Git/files and trigger free local XUNIA scans")
    parser.add_argument("config", help="Path to watcher JSON configuration")
    args = parser.parse_args()
    run(args.config)


if __name__ == "__main__":
    main()
