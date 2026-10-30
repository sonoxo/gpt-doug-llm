"""Public satellite catalog + opt-in local REA evidence for GPT-Doug.

This module cannot contact spacecraft, uplink commands, deploy replicas, or
connect to arbitrary hosts. Network access is one explicit public HTTPS GET.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SCHEMA = "gpt-doug.satellite-public-catalog.v1"
REPLICA_SCHEMA = "gpt-doug.approved-replica-plan.v1"
CATALOG_URL = "https://celestrak.org/NORAD/elements/gp.php?GROUP=STATIONS&FORMAT=JSON"
MAX_CATALOG_BYTES = 1024 * 1024
MAX_CATALOG_RECORDS = 128
MAX_REA_OUTPUT_BYTES = 1024 * 1024
MODEL_SUFFIXES = frozenset({".gguf", ".safetensors"})
NAME_RE = re.compile(r"^[\w][\w .()\-+/]{0,95}$", re.ASCII)
EPOCH_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z?$")


class BridgeError(RuntimeError):
    """A source, artifact, or policy gate failed closed."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Never forward the GET to a host selected by a redirect response."""

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise BridgeError("catalog redirect rejected by exact URL policy")


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def decode_catalog(raw: bytes, *, source: str, retrieved_at: Optional[str] = None) -> dict[str, Any]:
    """Normalize a bounded public GP catalog without propagating or tracking orbits."""
    if not isinstance(raw, bytes) or len(raw) > MAX_CATALOG_BYTES:
        raise BridgeError("catalog response is invalid or too large")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise BridgeError("catalog is not valid JSON") from exc
    if not isinstance(payload, list) or len(payload) > MAX_CATALOG_RECORDS:
        raise BridgeError("catalog must be a bounded JSON list")
    satellites = []
    seen = set()
    for record in payload:
        if not isinstance(record, dict):
            raise BridgeError("catalog item must be an object")
        ident = record.get("NORAD_CAT_ID")
        name = record.get("OBJECT_NAME")
        epoch = record.get("EPOCH")
        if type(ident) is not int or not 1 <= ident <= 999999999:
            raise BridgeError("invalid NORAD catalog identifier")
        if not isinstance(name, str) or not NAME_RE.fullmatch(name):
            raise BridgeError("invalid public satellite name")
        if not isinstance(epoch, str) or not EPOCH_RE.fullmatch(epoch):
            raise BridgeError("invalid source epoch")
        if ident in seen:
            raise BridgeError("duplicate NORAD catalog identifier")
        seen.add(ident)
        # Deliberately omit position, radio, maneuver and payload parameters.
        satellites.append({"norad_id": ident, "name": name, "epoch": epoch})
    satellites.sort(key=lambda item: item["norad_id"])
    return {
        "schema": SCHEMA,
        "mode": "public-read-only",
        "source": source,
        "retrieved_at": retrieved_at or timestamp(),
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "source_record_count": len(satellites),
        "data_kind": "public-orbital-catalog-metadata-not-live-telemetry",
        "satellites": satellites,
        "external_writes_enabled": False,
        "spacecraft_commands_enabled": False,
    }


def public_catalog(*, opener=None) -> dict[str, Any]:
    """Single opt-in GET to the one hard-coded public CelesTrak catalog URL."""
    request = urllib.request.Request(
        CATALOG_URL,
        method="GET",
        headers={"Accept": "application/json", "User-Agent": "GPT-Doug-Public-Satellite-Lab/1.0"},
    )
    open_url = opener or urllib.request.build_opener(NoRedirect()).open
    try:
        with open_url(request, timeout=8.0) as response:
            # A fixed URL is not enough: reject redirects to unrelated hosts.
            final_url = response.geturl()
            if final_url != CATALOG_URL:
                raise BridgeError("catalog redirect rejected by exact URL policy")
            raw = response.read(MAX_CATALOG_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise BridgeError("public catalog unavailable") from exc
    return decode_catalog(raw, source=CATALOG_URL)


def catalog_from_fixture(path: Path) -> dict[str, Any]:
    """Read bounded, operator-supplied offline test data; never contact a host."""
    with path.open("rb") as stream:
        raw = stream.read(MAX_CATALOG_BYTES + 1)
    return decode_catalog(raw, source="offline-fixture:" + path.name)


def approved_model(root: Path, relative_path: str) -> Path:
    """Admit only a regular model file inside an explicitly approved local root."""
    if not isinstance(relative_path, str) or not relative_path or "\\" in relative_path:
        raise BridgeError("artifact must be a relative local path")
    relative = Path(relative_path)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        raise BridgeError("absolute and traversing paths are denied")
    try:
        base = root.expanduser().resolve(strict=True)
    except (OSError, RuntimeError) as exc:
        raise BridgeError("approved root unavailable") from exc
    if not base.is_dir():
        raise BridgeError("approved root must be a directory")
    current = base
    for part in relative.parts:
        current = current / part
        if current.is_symlink():
            raise BridgeError("symlinked artifacts or parents are denied")
    try:
        target = current.resolve(strict=True)
        target.relative_to(base)
    except (OSError, RuntimeError, ValueError) as exc:
        raise BridgeError("artifact is outside the approved root or missing") from exc
    if not target.is_file() or target.suffix.lower() not in MODEL_SUFFIXES:
        raise BridgeError("only local .gguf and .safetensors files are supported")
    return target


def replica_plan(root: Path, relative_path: str) -> dict[str, Any]:
    """Generate a digest-based plan, not a deployed or self-propagating copy."""
    target = approved_model(root, relative_path)
    digest = hashlib.sha256()
    with target.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return {
        "schema": REPLICA_SCHEMA,
        "status": "plan-only",
        "artifact": relative_path,
        "bytes": target.stat().st_size,
        "sha256": digest.hexdigest(),
        "authorized_target_required": True,
        "human_approval_required": True,
        "deployment_enabled": False,
        "self_propagation_enabled": False,
        "remote_execution_enabled": False,
        "next_step": "Review the digest and explicitly deploy using your authorized host tooling.",
    }


def rea_model_inspect(root: Path, relative_path: str, *, executable: Optional[str] = None) -> dict[str, Any]:
    """Run the documented static REA model inspector, only on a local approved file."""
    target = approved_model(root, relative_path)
    rea = executable or shutil.which("rea")
    if not rea or not Path(rea).is_file():
        raise BridgeError("REA executable unavailable; install the trusted rea-agents release")
    args = [rea, "inspect-model-artifact", str(target), "--json"]
    try:
        # TemporaryFile bounds retained memory; never invoke a shell or download REA.
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            completed = subprocess.run(args, stdout=stdout, stderr=stderr, timeout=45, check=False)
            stdout.seek(0)
            output = stdout.read(MAX_REA_OUTPUT_BYTES + 1)
            if len(output) > MAX_REA_OUTPUT_BYTES:
                raise BridgeError("REA output too large; inspect the artifact directly")
            if completed.returncode:
                raise BridgeError("REA static analysis failed (exit code %d)" % completed.returncode)
    except subprocess.TimeoutExpired as exc:
        raise BridgeError("REA static analysis timed out") from exc
    try:
        evidence = json.loads(output)
    except (UnicodeDecodeError, ValueError) as exc:
        raise BridgeError("REA did not return valid JSON evidence") from exc
    if not isinstance(evidence, dict):
        raise BridgeError("REA evidence must be an object")
    return {
        "schema": "gpt-doug.rea-model-evidence.v1",
        "status": "local-static-analysis",
        "artifact": relative_path,
        "provider": "rea-agents",
        "evidence": evidence,
        "spacecraft_commands_enabled": False,
        "deployment_enabled": False,
    }


def status() -> dict[str, Any]:
    return {
        "mode": "public-read-only-and-local",
        "source": CATALOG_URL,
        "rea_installed": bool(shutil.which("rea")),
        "live_fetch_requires_opt_in": True,
        "network_control": "one-fixed-public-GET-only",
        "satellite_uplink": False,
        "replication": "plan-only-no-remote-operations",
    }


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Public satellite catalog and approved local REA analysis")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Show capabilities without network access")
    catalog = commands.add_parser("catalog", help="Public catalog metadata, never command uplink")
    choices = catalog.add_mutually_exclusive_group()
    choices.add_argument("--live", action="store_true", help="Opt into one CelesTrak HTTPS GET")
    choices.add_argument("--fixture", type=Path, help="Read an offline fixture JSON")
    for name in ("rea-model", "replica-plan"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--root", type=Path, required=True, help="Approved local model directory")
        cmd.add_argument("--artifact", required=True, help="Relative .gguf or .safetensors path")
    args = parser.parse_args(argv)
    try:
        if args.command == "status":
            result = status()
        elif args.command == "catalog" and args.live:
            result = public_catalog()
        elif args.command == "catalog" and args.fixture:
            result = catalog_from_fixture(args.fixture)
        elif args.command == "catalog":
            result = {
                "status": "offline",
                "source": CATALOG_URL,
                "message": "Use --live for one public GET or --fixture for offline input.",
                "network_requests_made": 0,
            }
        elif args.command == "rea-model":
            result = rea_model_inspect(args.root, args.artifact)
        else:
            result = replica_plan(args.root, args.artifact)
    except (BridgeError, OSError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
