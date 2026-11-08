#!/usr/bin/env python3
"""Repair and launch the *current* CL1 full-body Terminal in one operation.

Only fetches source from the official GPT-DOUG raw GitHub URL via HTTPS.
Stages and exercises the downloaded script BEFORE replacing an old copy.
No pip, Git clone, ZIP, browser, cloud token, or physical CL1 hardware.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SOURCE_URL = (
    "https://raw.githubusercontent.com/sonoxo/gpt-doug-llm/main/"
    "scripts/cl1_body_terminal.py"
)
RELEASE = "2026.11.07-speed.3"
MAX_SOURCE_BYTES = 160_000


def _validate_source(content: bytes) -> str:
    """Reject partial, invalid, or outdated downloads without executing them."""
    if not (1_000 <= len(content) <= MAX_SOURCE_BYTES):
        raise ValueError("Downloaded CL1 script has an unexpected size")
    try:
        source = content.decode("utf-8")
        tree = ast.parse(source, filename="cl1_body_terminal.py")
        compile(tree, "cl1_body_terminal.py", "exec")
    except (UnicodeError, SyntaxError) as exc:
        raise ValueError("Downloaded CL1 source is not valid Python") from exc
    found_release = [
        value.value
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name) and target.id == "CL1_RELEASE"
        for value in [node.value]
        if isinstance(value, ast.Constant) and isinstance(value.value, str)
    ]
    if found_release != [RELEASE]:
        raise ValueError("GitHub returned a CL1 build without the current ontology release")
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    if not {"run", "geometry", "mech_ontology", "mechanical_properties", "evaluate_joint"}.issubset(functions):
        raise ValueError("Downloaded renderer is missing mechanical ontology functions")
    return hashlib.sha256(content).hexdigest()


def fetch_official_source() -> bytes:
    request = Request(SOURCE_URL, headers={"User-Agent": "GPT-DOUG-CL1-Installer/1"})
    with urlopen(request, timeout=20) as response:
        final = urlsplit(response.geturl())
        expected = urlsplit(SOURCE_URL)
        if (
            final.scheme != "https"
            or final.hostname != expected.hostname
            or final.path != expected.path
            or final.query or final.fragment
        ):
            raise ValueError("Unexpected download redirect; existing script preserved")
        content = response.read(MAX_SOURCE_BYTES + 1)
    _validate_source(content)
    return content


def _command_json(python: str, staged: Path, args: list[str]) -> dict:
    run = subprocess.run(
        [python, str(staged), *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        encoding="utf-8",
        timeout=15,
        check=False,
    )
    if run.returncode:
        raise ValueError(
            "Downloaded CL1 build failed its functional check: "
            + run.stderr.strip()[:260]
        )
    try:
        obj = json.loads(run.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError("Downloaded CL1 script did not produce valid ontology JSON") from exc
    if not isinstance(obj, dict):
        raise ValueError("Unexpected ontology data format")
    return obj


def verify_candidate(staged: Path, python: str | None = None) -> dict:
    """Check the exact user-facing commands before touching the installed file."""
    python = python or sys.executable
    version = subprocess.run(
        [python, str(staged), "--version"],
        capture_output=True, text=True, timeout=10, check=False,
    )
    if version.returncode or RELEASE not in version.stdout:
        raise ValueError("Downloaded CL1 build failed the version check")
    joint = _command_json(python, staged, [
        "--inspect", "left_forearm", "--joint-angle", "65", "--joint-speed", "15",
    ])
    evaluation = joint.get("joint_evaluation", {})
    if (
        joint.get("id") != "cl1:segment/left_forearm"
        or evaluation.get("simulation_only") is not True
        or evaluation.get("hardware_command_sent") is not False
    ):
        raise ValueError("Downloaded CL1 build failed the joint-inspection check")
    graph = _command_json(python, staged, ["--ontology-json"])
    if (
        graph.get("entity_count", 0) < 19
        or graph.get("simulation_only") is not True
        or graph.get("hardware_connected") is not False
        or len(graph.get("relations", [])) != graph["entity_count"] - 1
    ):
        raise ValueError("Downloaded CL1 build failed the ontology-graph check")
    frame = subprocess.run(
        [python, str(staged), "--once", "--no-color", "--no-spin", "--width", "84",
         "--height", "40", "--mode", "skeleton", "--color", "bone"],
        capture_output=True, text=True, timeout=25, check=False,
    )
    if frame.returncode or "SKELETON | 01 | BONE" not in frame.stdout:
        raise ValueError("Downloaded CL1 build failed the skeleton-rendering check")
    return {
        "version": RELEASE,
        "entities": graph["entity_count"],
        "relationships": len(graph["relations"]),
        "joint_tested": joint["id"],
        "display_tested": "SKELETON | 01 | BONE",
        "hardware_connected": False,
    }


def install(
    destination: Path,
    *,
    fetcher=fetch_official_source,
    verifier=verify_candidate,
) -> dict:
    """Atomically update a single file, keeping the original on any failure."""
    destination = destination.expanduser()
    parent = destination.parent
    if not parent.is_dir():
        raise ValueError(f"Install directory does not exist: {parent}")
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError("Refusing to replace a symlink or a non-file")
    raw = fetcher()
    sha = _validate_source(raw)
    descriptor, filename = tempfile.mkstemp(prefix=".cl1-verified-", suffix=".py", dir=parent)
    stage = Path(filename)
    backup: Path | None = None
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw)
        status = verifier(stage)
        if destination.exists():
            current_bytes = destination.read_bytes()
            if current_bytes == raw:
                status.update(path=str(destination), sha256=sha, changed=False, backup=None)
                return status
            previous_sha = hashlib.sha256(current_bytes).hexdigest()[:12]
            backup = parent / (destination.name + ".backup-" + previous_sha)
            if not backup.exists():
                shutil.copy2(destination, backup)
        os.replace(stage, destination)
        status.update(
            path=str(destination), sha256=sha, changed=True,
            backup=str(backup) if backup is not None else None,
        )
        return status
    finally:
        stage.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repair/install and verify CL1 skeleton + mechanical ontology; no pip."
    )
    parser.add_argument(
        "--destination", type=Path,
        default=Path.home() / "Downloads" / "cl1_body_terminal.py",
        help="installed Python renderer location",
    )
    parser.add_argument(
        "--install-only", action="store_true",
        help="repair and verify but do not launch the animation",
    )
    parser.add_argument(
        "--inspect", metavar="COMPONENT",
        help="repair, then print a named component rather than opening viewer",
    )
    args = parser.parse_args(argv)
    try:
        result = install(args.destination)
    except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as exc:
        print("CL1 UPDATE FAILED (previous version preserved): " + str(exc), file=sys.stderr)
        return 2
    print(
        "CL1 VERIFIED: {version} | {entities} mechanical nodes | "
        "ontology + joint + bone-white renderer OK".format(**result),
        flush=True,
    )
    print("Installed at:", result["path"], flush=True)
    if result["backup"]:
        print("Previous script backed up at:", result["backup"], flush=True)
    if args.install_only:
        return 0
    command = [sys.executable, result["path"]]
    if args.inspect:
        command.extend(["--inspect", args.inspect])
    else:
        command.extend(["--mode", "skeleton", "--color", "bone", "--no-spin"])
        print("Launching skeleton. Press O for ontology, [ / ] to select, Q to quit.", flush=True)
    try:
        return subprocess.call(command)
    except OSError as exc:
        print("CL1 LAUNCH FAILED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
