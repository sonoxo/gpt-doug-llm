"""Ephemeral reproducible sandbox runner for generated applications."""

from __future__ import annotations

import difflib
import hashlib
import json
import os
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

LOCK_FILES = (
    "requirements.txt",
    "requirements.lock",
    "poetry.lock",
    "uv.lock",
    "Pipfile.lock",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
)
EXCLUDES = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}
ALLOWED_EXECUTABLES = {"python", "python3", "pytest", "ruff", "node", "npm", "npx", "pnpm", "yarn"}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class SandboxCommand:
    argv: tuple[str, ...]
    timeout: int = 120


class SandboxRunner:
    """Copies a workspace into a disposable directory and runs allowlisted checks."""

    def __init__(self, source: str | Path) -> None:
        self.source = Path(source).resolve()
        if not self.source.is_dir():
            raise ValueError("sandbox source must be a directory")
        self._tmp: tempfile.TemporaryDirectory[str] | None = None
        self.root: Path | None = None
        self.started_at: float | None = None

    def __enter__(self) -> "SandboxRunner":
        self._tmp = tempfile.TemporaryDirectory(prefix="zyra-sandbox-")
        self.root = Path(self._tmp.name) / "workspace"
        shutil.copytree(
            self.source,
            self.root,
            ignore=shutil.ignore_patterns(*EXCLUDES),
            dirs_exist_ok=True,
        )
        self.started_at = time.time()
        return self

    def __exit__(self, *_exc: object) -> None:
        if self._tmp is not None:
            self._tmp.cleanup()
        self.root = None
        self._tmp = None

    def _require_root(self) -> Path:
        if self.root is None:
            raise RuntimeError("sandbox is not active")
        return self.root

    def lock_manifest(self) -> dict[str, str]:
        root = self._require_root()
        return {name: _sha256_file(root / name) for name in LOCK_FILES if (root / name).is_file()}

    def run(self, command: SandboxCommand) -> dict[str, object]:
        root = self._require_root()
        if not command.argv:
            raise ValueError("empty sandbox command")
        executable = Path(command.argv[0]).name
        if executable not in ALLOWED_EXECUTABLES:
            raise PermissionError(f"sandbox executable not allowlisted: {executable}")
        before = self.lock_manifest()
        started = time.monotonic()
        completed = subprocess.run(
            list(command.argv),
            cwd=root,
            capture_output=True,
            text=True,
            timeout=max(1, min(int(command.timeout), 600)),
            shell=False,
            env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "CI": "1"},
            check=False,
        )
        after = self.lock_manifest()
        return {
            "argv": list(command.argv),
            "returncode": completed.returncode,
            "ok": completed.returncode == 0 and before == after,
            "stdout": completed.stdout[-12000:],
            "stderr": completed.stderr[-12000:],
            "duration_ms": int((time.monotonic() - started) * 1000),
            "lockfiles_unchanged": before == after,
            "lock_manifest": after,
        }

    def smoke_test(self) -> dict[str, object]:
        root = self._require_root()
        if (root / "tests").is_dir():
            return self.run(SandboxCommand(("python", "-m", "pytest", "-q"), 180))
        return self.run(SandboxCommand(("python", "-m", "compileall", "-q", "."), 120))

    def start_static_preview(self) -> "PreviewProcessManager":
        root = self._require_root()
        entrypoints = ("index.html", "dist/index.html", "build/index.html", "public/index.html")
        if not any((root / candidate).is_file() for candidate in entrypoints):
            raise FileNotFoundError("no static web entrypoint found for automatic preview")
        manager = PreviewProcessManager(root)
        result = manager.start()
        if not result["ok"]:
            raise RuntimeError("preview failed to start")
        return manager

    def artifact_manifest(self) -> dict[str, object]:
        root = self._require_root()
        files: dict[str, str] = {}
        for path in sorted(root.rglob("*")):
            if path.is_file() and not any(part in EXCLUDES for part in path.parts):
                files[path.relative_to(root).as_posix()] = _sha256_file(path)
        canonical = json.dumps(files, sort_keys=True, separators=(",", ":")).encode()
        return {
            "files": files,
            "digest": hashlib.sha256(canonical).hexdigest(),
            "source": str(self.source),
            "created_at": time.time(),
        }

    def diff_against_source(self, *, max_chars: int = 50000) -> dict[str, str]:
        root = self._require_root()
        diffs: dict[str, str] = {}
        candidates = set()
        for base in (self.source, root):
            for path in base.rglob("*"):
                if path.is_file() and not any(part in EXCLUDES for part in path.parts):
                    candidates.add(path.relative_to(base).as_posix())
        for rel in sorted(candidates):
            original = self.source / rel
            changed = root / rel
            try:
                old = original.read_text(encoding="utf-8").splitlines(keepends=True) if original.exists() else []
                new = changed.read_text(encoding="utf-8").splitlines(keepends=True) if changed.exists() else []
            except (UnicodeDecodeError, OSError):
                continue
            if old == new:
                continue
            diff = "".join(difflib.unified_diff(old, new, fromfile=f"a/{rel}", tofile=f"b/{rel}"))
            diffs[rel] = diff[:max_chars]
        return diffs


class PreviewProcessManager:
    """Bounded localhost-only preview lifecycle for sandbox web artifacts."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.process: subprocess.Popen[str] | None = None
        self.port: int | None = None

    @staticmethod
    def _free_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def start(self, port: int | None = None) -> dict[str, object]:
        if self.process is not None and self.process.poll() is None:
            return {"ok": True, "port": self.port, "already_running": True}
        chosen = int(port or self._free_port())
        if not (1024 <= chosen <= 65535):
            raise ValueError("preview port must be between 1024 and 65535")
        self.process = subprocess.Popen(
            ["python", "-m", "http.server", str(chosen), "--bind", "127.0.0.1"],
            cwd=self.root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            shell=False,
        )
        self.port = chosen
        time.sleep(0.15)
        ok = self.process.poll() is None
        if not ok:
            self.stop()
        return {"ok": ok, "port": chosen, "url": f"http://127.0.0.1:{chosen}/"}

    def stop(self) -> dict[str, object]:
        if self.process is None:
            return {"ok": True, "stopped": False}
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)
        code = self.process.returncode
        self.process = None
        self.port = None
        return {"ok": True, "stopped": True, "returncode": code}
