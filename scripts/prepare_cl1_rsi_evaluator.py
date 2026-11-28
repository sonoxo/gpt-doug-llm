#!/usr/bin/env python3
"""Install a frozen CL1 RSI evaluator outside the AI-editable checkout.

No network access or paid services. Never silently overwrite a trusted evaluator.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "scripts" / "cl1_rsi_heldout.py"
DEFAULT_DESTINATION = Path.home() / ".gpt-doug" / "rsi" / "evaluators" / "cl1-heldout.py"


def install(destination: Path = DEFAULT_DESTINATION, *, replace: bool = False) -> dict:
    repo = ROOT.resolve()
    destination = destination.expanduser().resolve()
    if destination == repo or repo in destination.parents:
        raise ValueError("Evaluator must live outside the editable repository")
    data = SOURCE.read_bytes()
    checksum = hashlib.sha256(data).hexdigest()
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    if destination.exists():
        if destination.is_symlink() or not destination.is_file():
            raise ValueError("Evaluator destination must be a regular file")
        current = destination.read_bytes()
        if current == data:
            return {"status": "UNCHANGED", "path": str(destination), "sha256": checksum}
        if not replace:
            raise ValueError("Evaluator differs; explicit --replace is required")
    fd, temp_name = tempfile.mkstemp(prefix=".cl1-eval-", dir=destination.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, 0o600)
        os.replace(temp_name, destination)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
    return {"status": "INSTALLED", "path": str(destination), "sha256": checksum}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, default=DEFAULT_DESTINATION)
    parser.add_argument("--replace", action="store_true", help="Explicitly replace an existing evaluator")
    args = parser.parse_args()
    try:
        print(json.dumps(install(args.destination, replace=args.replace), indent=2))
    except (OSError, ValueError) as exc:
        parser.exit(1, f"CL1 RSI EVALUATOR NOT INSTALLED: {exc}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
