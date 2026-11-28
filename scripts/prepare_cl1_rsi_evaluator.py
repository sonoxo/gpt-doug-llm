#!/usr/bin/env python3
"""Install a frozen CL1 synthetic RSI evaluator outside the AI-editable checkout.

Each installation receives a PRIVATE per-installation held-out seed suite that
is never committed to Git. Reinstall is idempotent and detects tampering.
Explicit --replace creates a fresh suite, resetting benchmark comparability.
No network, paid services, CL SDK or physical hardware is involved.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "cl1_rsi_heldout.py"
DEFAULT_DESTINATION = Path.home() / ".gpt-doug" / "rsi" / "evaluators" / "cl1-heldout.py"
PUBLIC_SEEDS_LINE = "SEEDS = (113, 227, 347, 521, 691, 823)"
PRIVATE_MARKER = "  # CL1_PRIVATE_INSTALLATION_SEEDS"


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    fd, temporary = tempfile.mkstemp(prefix=".cl1-eval-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def install(destination: Path = DEFAULT_DESTINATION, *, replace: bool = False) -> dict:
    repo = ROOT.resolve()
    destination = destination.expanduser().resolve()
    if destination == repo or repo in destination.parents:
        raise ValueError("Evaluator must live outside the editable repository")
    original = SOURCE.read_bytes()
    source_hash = sha256(original)
    metadata_path = destination.with_suffix(destination.suffix + ".provenance.json")
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise ValueError("Evaluator destination must be a regular file")
        existing = destination.read_bytes()
        if not replace:
            if not metadata_path.is_file() or metadata_path.is_symlink():
                raise ValueError("Existing evaluator missing trusted provenance; explicit --replace required")
            try:
                meta = json.loads(metadata_path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ValueError("Invalid evaluator provenance; explicit --replace required") from exc
            if (
                meta.get("schema") == "gpt-doug-cl1-private-heldout/v1"
                and meta.get("source_sha256") == source_hash
                and meta.get("installed_sha256") == sha256(existing)
                and PRIVATE_MARKER.encode() in existing
            ):
                return {"status": "UNCHANGED", "path": str(destination), "sha256": sha256(existing)}
            raise ValueError("Evaluator differs; explicit --replace is required")
    else:
        if metadata_path.exists() and not replace:
            raise ValueError("Unpaired evaluator provenance exists; explicit --replace required")

    source = original.decode("utf-8")
    if source.count(PUBLIC_SEEDS_LINE) != 1:
        raise ValueError("Trusted evaluator template no longer has one public seed marker")
    seeds = tuple(secrets.randbelow(2 ** 31 - 1) + 1 for _ in range(6))
    replacement = "SEEDS = " + repr(seeds) + PRIVATE_MARKER
    installed = source.replace(PUBLIC_SEEDS_LINE, replacement).encode("utf-8")
    checksum = sha256(installed)
    provenance = json.dumps(
        {
            "schema": "gpt-doug-cl1-private-heldout/v1",
            "source_sha256": source_hash,
            "installed_sha256": checksum,
            "kind": "private-synthetic-evaluation-seeds",
            "data_origin": "local cryptographic randomness; no biological measurements",
        },
        indent=2,
        sort_keys=True,
    ).encode("utf-8") + b"\n"
    _atomic_write(destination, installed)
    _atomic_write(metadata_path, provenance)
    return {"status": "INSTALLED", "path": str(destination), "sha256": checksum}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--replace", action="store_true", help="Explicitly install a new private suite")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.destination, replace=args.replace), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"CL1 RSI EVALUATOR NOT INSTALLED: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
