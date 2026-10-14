"""GPT-Doug CL1 organoid digital twin + authorized evidence swarm.

This module is intentionally simulator-only for CL1. It does not grow cells,
stimulate physical neural tissue, or connect to arbitrary external systems.

Two bounded modes are provided:
- simulator: records synthetic CL1 activity through the official cl-sdk.
- evidence-swarm: concurrently fetches only an explicit allowlist of public
  research/documentation URLs for provenance snapshots.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import importlib.metadata
import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "intel" / "sources" / "cl1-organoid-authorized-sources.json"
MAX_BYTES = 512_000
MAX_WORKERS = 6
TIMEOUT = 8.0


def _physical_marker_present() -> bool:
    return Path("/opt/cl-api-whl").exists()


def ensure_simulator() -> str:
    if _physical_marker_present():
        raise RuntimeError("Physical CL1 environment detected; this coordinator refuses hardware access")
    try:
        return importlib.metadata.version("cl-sdk")
    except importlib.metadata.PackageNotFoundError as exc:
        raise RuntimeError("Install cl-sdk in a dedicated simulator virtual environment") from exc


def load_manifest(path: Path = DEFAULT_MANIFEST) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "gpt-doug-cl1-authorized-sources/v1":
        raise ValueError("unexpected source manifest schema")
    sources = data.get("sources")
    if not isinstance(sources, list) or not sources:
        raise ValueError("source manifest must contain sources")
    for item in sources:
        parsed = urlparse(item["url"])
        if parsed.scheme != "https" or not parsed.hostname:
            raise ValueError("only explicit HTTPS sources are permitted")
        if parsed.hostname not in set(data["allowed_hosts"]):
            raise ValueError(f"source host not allowlisted: {parsed.hostname}")
    return data


def simulator_snapshot(seconds: float, output: Path) -> dict[str, Any]:
    if not (0.1 <= seconds <= 10.0):
        raise ValueError("seconds must be between 0.1 and 10")
    sdk_version = ensure_simulator()
    import cl

    output = output.expanduser().resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with cl.open() as neurons:
        recording = neurons.record(file_location=str(output), stop_after_seconds=seconds)
        recording.wait_until_stopped()
        channel_count = neurons.get_channel_count()
        fps = neurons.get_frames_per_second()

    return {
        "mode": "CL1_SIMULATOR_ONLY",
        "sdk_version": sdk_version,
        "recording": str(output),
        "seconds": seconds,
        "channel_count": int(channel_count),
        "frames_per_second": float(fps),
        "physical_hardware": False,
        "organoid_created": False,
        "biological_learning_claim": False,
        "note": "Synthetic SDK data is not evidence of a living organoid or biological learning.",
    }


def _fetch_one(item: dict[str, Any]) -> dict[str, Any]:
    req = Request(item["url"], headers={
        "User-Agent": "GPT-Doug-CL1-Evidence-Swarm/1.0",
        "Accept": "text/html,application/json,text/plain;q=0.8,*/*;q=0.2",
    })
    started = time.monotonic()
    with urlopen(req, timeout=TIMEOUT) as response:
        body = response.read(MAX_BYTES + 1)
        if len(body) > MAX_BYTES:
            raise ValueError("response exceeds bounded evidence limit")
        content_type = response.headers.get("Content-Type", "")
        final_url = response.geturl()
    parsed = urlparse(final_url)
    if parsed.scheme != "https":
        raise ValueError("redirect left HTTPS")
    return {
        "id": item["id"],
        "url": item["url"],
        "final_url": final_url,
        "authority": item["authority"],
        "status": "OK",
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "content_type": content_type[:160],
        "elapsed_ms": round((time.monotonic() - started) * 1000, 1),
    }


def evidence_swarm(path: Path = DEFAULT_MANIFEST, workers: int = 4) -> dict[str, Any]:
    manifest = load_manifest(path)
    workers = max(1, min(int(workers), MAX_WORKERS))
    results: list[dict[str, Any]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="cl1-evidence") as pool:
        futures = {pool.submit(_fetch_one, item): item for item in manifest["sources"]}
        for future in concurrent.futures.as_completed(futures):
            item = futures[future]
            try:
                results.append(future.result())
            except Exception as exc:
                results.append({
                    "id": item["id"],
                    "url": item["url"],
                    "authority": item["authority"],
                    "status": "ERROR",
                    "error": str(exc)[:240],
                })
    results.sort(key=lambda row: row["id"])
    return {
        "mode": "AUTHORIZED_PUBLIC_EVIDENCE_SWARM",
        "workers": workers,
        "source_count": len(results),
        "ok": sum(1 for row in results if row["status"] == "OK"),
        "errors": sum(1 for row in results if row["status"] != "OK"),
        "arbitrary_network_access": False,
        "physical_cl1_access": False,
        "results": results,
    }


def topology() -> dict[str, Any]:
    manifest = load_manifest()
    return {
        "system": "GPT-DOUG-CL1-RESEARCH-SWARM",
        "layers": [
            {"id": "cl1-simulator", "kind": "synthetic_neural_recording"},
            {"id": "organoid-digital-twin", "kind": "software_reference_model"},
            {"id": "evidence-swarm", "kind": "allowlisted_public_https"},
            {"id": "gmro", "kind": "provenance_graph"},
            {"id": "human-review", "kind": "required_gate"},
        ],
        "edges": [
            ["cl1-simulator", "organoid-digital-twin"],
            ["evidence-swarm", "gmro"],
            ["organoid-digital-twin", "gmro"],
            ["gmro", "human-review"],
        ],
        "allowlisted_hosts": manifest["allowed_hosts"],
        "physical_organoid": False,
        "global_infrastructure_control": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    sim = sub.add_parser("simulator")
    sim.add_argument("--seconds", type=float, default=3.0)
    sim.add_argument("--output", type=Path, default=Path("cl1-organoid-sim.h5"))

    swarm = sub.add_parser("evidence-swarm")
    swarm.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    swarm.add_argument("--workers", type=int, default=4)

    sub.add_parser("topology")

    args = parser.parse_args(argv)
    if args.cmd == "simulator":
        result = simulator_snapshot(args.seconds, args.output)
    elif args.cmd == "evidence-swarm":
        result = evidence_swarm(args.manifest, args.workers)
    else:
        result = topology()
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
