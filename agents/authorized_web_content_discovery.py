"""Bounded, authorization-first web content discovery skill for Zyra / GPT-DOUG-ASTRA.

This module wraps an installed content-discovery CLI (Feroxbuster by default)
without expanding scope on its own. Execution is fail-closed unless the caller
explicitly marks the request authorized and the target host is inside the
approved scope set.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlparse


class DiscoveryAuthorizationError(PermissionError):
    pass


class DiscoveryRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class DiscoveryRequest:
    target: str
    authorized: bool
    allowed_hosts: tuple[str, ...]
    wordlist: str | None = None
    depth: int = 2
    rate_limit: int = 20
    threads: int = 20
    timeout_seconds: int = 120


@dataclass(frozen=True)
class DiscoveryResult:
    target: str
    tool: str
    executed: bool
    returncode: int | None
    findings: tuple[dict, ...]
    command: tuple[str, ...]
    message: str


def _host(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    return (parsed.hostname or "").lower().rstrip(".")


def validate_scope(request: DiscoveryRequest) -> str:
    if not request.authorized:
        raise DiscoveryAuthorizationError("explicit authorization is required")
    host = _host(request.target)
    if not host:
        raise DiscoveryAuthorizationError("target must contain a valid host")
    allowed = {_host(item) for item in request.allowed_hosts}
    if host not in allowed:
        raise DiscoveryAuthorizationError(f"target host {host!r} is outside approved scope")
    if request.depth < 0 or request.depth > 10:
        raise ValueError("depth must be between 0 and 10")
    if request.rate_limit < 1 or request.rate_limit > 200:
        raise ValueError("rate_limit must be between 1 and 200 requests/second")
    if request.threads < 1 or request.threads > 100:
        raise ValueError("threads must be between 1 and 100")
    return host


def build_feroxbuster_command(request: DiscoveryRequest, output_file: str) -> list[str]:
    validate_scope(request)
    cmd = [
        "feroxbuster",
        "--url", request.target,
        "--depth", str(request.depth),
        "--rate-limit", str(request.rate_limit),
        "--threads", str(request.threads),
        "--json",
        "--output", output_file,
        "--silent",
    ]
    if request.wordlist:
        cmd.extend(["--wordlist", request.wordlist])
    return cmd


def _parse_json_lines(path: Path) -> tuple[dict, ...]:
    if not path.exists():
        return ()
    findings: list[dict] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            findings.append(row)
    return tuple(findings)


def execute_discovery(request: DiscoveryRequest, workdir: str | Path = ".") -> DiscoveryResult:
    validate_scope(request)
    if shutil.which("feroxbuster") is None:
        raise DiscoveryRuntimeError("feroxbuster is not installed on this runtime")

    root = Path(workdir)
    root.mkdir(parents=True, exist_ok=True)
    output = root / "feroxbuster-results.jsonl"
    cmd = build_feroxbuster_command(request, str(output))
    completed = subprocess.run(
        cmd,
        cwd=root,
        text=True,
        capture_output=True,
        timeout=request.timeout_seconds,
        check=False,
    )
    findings = _parse_json_lines(output)
    message = "discovery completed" if completed.returncode == 0 else "discovery completed with non-zero exit"
    return DiscoveryResult(
        target=request.target,
        tool="feroxbuster",
        executed=True,
        returncode=completed.returncode,
        findings=findings,
        command=tuple(cmd),
        message=message,
    )


def skill_manifest() -> dict:
    return {
        "skill": "AUTHORIZED_WEB_CONTENT_DISCOVERY",
        "learnedBy": ["gpt-doug-astra-llm", "gpt-doug-llm", "zyra"],
        "tool": "feroxbuster",
        "executionPolicy": "FAIL_CLOSED_AUTHORIZED_SCOPE_ONLY",
        "capabilities": [
            "recursive_content_discovery",
            "wordlist_driven_enumeration",
            "response_discovery",
            "depth_control",
            "rate_limiting",
            "structured_findings",
        ],
        "guardrails": {
            "explicitAuthorizationRequired": True,
            "approvedHostScopeRequired": True,
            "maxDepth": 10,
            "maxRateLimit": 200,
            "maxThreads": 100,
        },
    }


def request_as_dict(request: DiscoveryRequest) -> dict:
    return asdict(request)
