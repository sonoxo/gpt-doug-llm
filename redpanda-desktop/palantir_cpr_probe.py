#!/usr/bin/env python3
"""Read-only Palantir/GPT-DOUG integrity probe for REDPANDA CPR.

The probe validates the local integration surface without performing Foundry
writes, Maven publishing, or changing repository state. It is intended to be
run against a local checkout of sonoxo/gpt-doug-llm.
"""
from __future__ import annotations

import argparse
import json
import os
import py_compile
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    "palantir_foundry.py",
    "palantir_maven.py",
    "sovereignty_performance.py",
    "tools/palantir-toolbox/manifest.json",
    "tools/palantir-toolbox/foundry.js",
    "tools/palantir-toolbox/bridge/palantir_bridge.py",
    "safety-shield/agents/knowledge/palantir-stack-v1.json",
    "safety-shield/ontology/palantir-maven-glass-onion.json",
    "redpanda-desktop/palantir-maven",
)
PYTHON_FILES = (
    "palantir_foundry.py",
    "palantir_maven.py",
    "sovereignty_performance.py",
    "tools/palantir-toolbox/bridge/palantir_bridge.py",
)
JSON_FILES = (
    "tools/palantir-toolbox/manifest.json",
    "safety-shield/agents/knowledge/palantir-stack-v1.json",
    "safety-shield/ontology/palantir-maven-glass-onion.json",
)


def _resolve_repo_root(explicit: str) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    env_root = os.environ.get("REDPANDA_REPO_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.append(Path.cwd())

    for candidate in candidates:
        root = candidate.resolve()
        if (root / "palantir_foundry.py").is_file():
            return root
    return candidates[0].resolve() if candidates else Path.cwd().resolve()


def _compile_python(path: Path) -> dict[str, Any]:
    try:
        py_compile.compile(str(path), doraise=True)
        return {"ok": True, "path": str(path)}
    except Exception as exc:
        return {"ok": False, "path": str(path), "error": str(exc)}


def _parse_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "ok": isinstance(payload, dict),
            "path": str(path),
            "top_level_type": type(payload).__name__,
            "payload": payload if isinstance(payload, dict) else None,
        }
    except Exception as exc:
        return {"ok": False, "path": str(path), "error": str(exc), "payload": None}


def _run_sovereignty_profile(root: Path, benchmark: bool) -> dict[str, Any]:
    cmd = [sys.executable, str(root / "sovereignty_performance.py")]
    if benchmark:
        cmd.append("--benchmark")
    try:
        proc = subprocess.run(
            cmd, cwd=root, text=True, capture_output=True, timeout=30, check=False
        )
        if proc.returncode != 0:
            return {
                "ok": False,
                "exit_code": proc.returncode,
                "error": (proc.stderr or proc.stdout or "runtime failed")[-4000:],
            }
        payload = json.loads(proc.stdout)
        safe_boundary = payload.get("palantir_infrastructure_controlled") is False
        hardware = payload.get("hardware", {}) if isinstance(payload, dict) else {}
        return {
            "ok": bool(safe_boundary),
            "exit_code": 0,
            "preferred_accelerator": hardware.get("preferred_accelerator"),
            "accelerators": hardware.get("accelerators", []),
            "cpu_count": hardware.get("cpu_count"),
            "memory_bytes": hardware.get("memory_bytes"),
            "benchmark": payload.get("benchmark") if benchmark else None,
            "palantir_infrastructure_controlled": payload.get("palantir_infrastructure_controlled"),
        }
    except Exception as exc:
        return {"ok": False, "exit_code": 1, "error": str(exc)}


def probe(repo_root: Path, benchmark: bool = False) -> dict[str, Any]:
    root = repo_root.resolve()
    missing = [name for name in REQUIRED_FILES if not (root / name).is_file()]
    syntax = {name: _compile_python(root / name) for name in PYTHON_FILES if (root / name).is_file()}
    parsed_json = {name: _parse_json(root / name) for name in JSON_FILES if (root / name).is_file()}

    manifest = parsed_json.get("tools/palantir-toolbox/manifest.json", {}).get("payload") or {}
    knowledge = parsed_json.get("safety-shield/agents/knowledge/palantir-stack-v1.json", {}).get("payload") or {}
    maven_ontology = parsed_json.get("safety-shield/ontology/palantir-maven-glass-onion.json", {}).get("payload") or {}

    manifest_ok = manifest.get("manifest_version") == 3
    knowledge_ok = knowledge.get("knowledge_id") == "palantir-stack-v1"
    maven_ontology_ok = (
        maven_ontology.get("ontology") == "PalantirMavenGlassOnion"
        and maven_ontology.get("guardrails", {}).get("automaticPublishing") is False
        and maven_ontology.get("guardrails", {}).get("storesCredentialsInGit") is False
    )
    syntax_ok = bool(syntax) and all(item.get("ok") for item in syntax.values())
    json_ok = len(parsed_json) == len(JSON_FILES) and all(item.get("ok") for item in parsed_json.values())
    runtime = (
        _run_sovereignty_profile(root, benchmark)
        if not missing and (root / "sovereignty_performance.py").is_file()
        else {"ok": False, "skipped": True, "reason": "required files missing"}
    )

    ok = not missing and syntax_ok and json_ok and manifest_ok and knowledge_ok and maven_ontology_ok and bool(runtime.get("ok"))
    return {
        "schema": "gpt-redpanda.palantir-cpr.v2",
        "mode": "read-only-local-integrity",
        "repo_root": str(root),
        "ok": ok,
        "missing": missing,
        "checks": {
            "python_syntax": syntax,
            "json": {key: {k: v for k, v in value.items() if k != "payload"} for key, value in parsed_json.items()},
            "manifest_v3": manifest_ok,
            "knowledge_registry": knowledge_ok,
            "palantir_maven_glass_onion": maven_ontology_ok,
            "sovereignty_runtime": runtime,
        },
        "writes_performed": False,
        "maven_publish_called": False,
        "foundry_actions_called": False,
        "checked_at": int(time.time()),
    }


def main() -> int:
    parser = argparse.ArgumentParser(prog="redpanda-palantir-cpr")
    parser.add_argument("--repo-root", default="", help="local gpt-doug-llm checkout")
    parser.add_argument("--benchmark", action="store_true", help="include local microbenchmark")
    args = parser.parse_args()
    result = probe(_resolve_repo_root(args.repo_root), benchmark=args.benchmark)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
