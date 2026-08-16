from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, asdict
from pathlib import Path


IGNORE = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
}

SECRET_PATTERNS = [
    ("generic_api_key", re.compile(r'(?i)(api[_-]?key|secret[_-]?key)\s*[:=]\s*["\'][^"\']{12,}')),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b")),
]


@dataclass
class WorkspaceReport:
    root: str
    files: int
    directories: int
    languages: dict[str, int]
    entrypoints: list[str]
    tests: list[str]
    deployment: list[str]
    docs: list[str]
    git_branch: str
    git_dirty: bool
    security_findings: list[dict]

    def to_dict(self):
        return asdict(self)


def _git(root: Path, *args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=5,
        ).strip()
    except Exception:
        return ""


def _iter_files(root: Path):
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        base = Path(current)
        for name in files:
            path = base / name
            try:
                if path.stat().st_size <= 2_000_000:
                    yield path
            except OSError:
                continue


def inspect_workspace(root: str | Path = ".") -> WorkspaceReport:
    root = Path(root).expanduser().resolve()

    files = list(_iter_files(root))
    dirs = {
        str(p.parent)
        for p in files
    }

    languages: dict[str, int] = {}
    entrypoints = []
    tests = []
    deployment = []
    docs = []
    security_findings = []

    entry_names = {
        "main.py", "app.py", "server.py", "index.js", "index.ts",
        "package.json", "manage.py", "Dockerfile",
    }

    deployment_names = {
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "vercel.json", "netlify.toml", "Procfile", "fly.toml",
    }

    doc_names = {
        "README.md", "README", "CONTRIBUTING.md",
        "SECURITY.md", "ARCHITECTURE.md",
    }

    for path in files:
        rel = str(path.relative_to(root))
        suffix = path.suffix.lower() or "<none>"
        languages[suffix] = languages.get(suffix, 0) + 1

        if path.name in entry_names:
            entrypoints.append(rel)

        if (
            path.name.startswith("test_")
            or path.name.endswith("_test.py")
            or "/tests/" in f"/{rel}"
        ):
            tests.append(rel)

        if path.name in deployment_names:
            deployment.append(rel)

        if path.name in doc_names:
            docs.append(rel)

        if path.suffix.lower() in {
            ".py", ".js", ".ts", ".tsx", ".jsx", ".json",
            ".toml", ".yaml", ".yml", ".env", ".md",
        }:
            try:
                content = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except Exception:
                continue

            for finding_name, pattern in SECRET_PATTERNS:
                if pattern.search(content):
                    security_findings.append({
                        "type": finding_name,
                        "file": rel,
                    })

    branch = _git(root, "branch", "--show-current") or "unknown"
    dirty = bool(_git(root, "status", "--porcelain"))

    return WorkspaceReport(
        root=str(root),
        files=len(files),
        directories=len(dirs),
        languages=dict(
            sorted(
                languages.items(),
                key=lambda x: x[1],
                reverse=True,
            )
        ),
        entrypoints=sorted(entrypoints),
        tests=sorted(tests),
        deployment=sorted(deployment),
        docs=sorted(docs),
        git_branch=branch,
        git_dirty=dirty,
        security_findings=security_findings,
    )
