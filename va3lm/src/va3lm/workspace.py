from __future__ import annotations

import base64
import hashlib
import json
import os
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any


class WorkspaceError(RuntimeError):
    """Raised when a workspace operation violates a runtime boundary."""


_DEFAULT_COMMANDS = {
    "python",
    "python3",
    "pytest",
    "ruff",
    "bandit",
    "node",
    "npm",
    "npx",
    "pnpm",
    "yarn",
    "git",
}
_GIT_READ_ONLY = {"status", "diff", "log", "show", "rev-parse", "ls-files"}
_BLOCKED_PACKAGE_ACTIONS = {"publish", "deploy", "release"}
_IGNORED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".va3lm"}
_BLOCKED_FILES = {".env", ".env.local", ".env.production", ".env.development", "id_rsa", "id_ed25519"}
_MAX_TEXT_BYTES = 1_000_000
_MAX_COMMAND_OUTPUT = 100_000


def _allowed_commands() -> set[str]:
    configured = os.getenv("VA3LM_ALLOWED_COMMANDS", "").strip()
    if not configured:
        return set(_DEFAULT_COMMANDS)
    return {item.strip() for item in configured.split(",") if item.strip()}


def _safe_environment() -> dict[str, str]:
    explicit = {item.strip() for item in os.getenv("VA3LM_PASS_ENV", "").split(",") if item.strip()}
    result: dict[str, str] = {}
    for key, value in os.environ.items():
        upper = key.upper()
        sensitive = any(marker in upper for marker in ("TOKEN", "SECRET", "PASSWORD", "PRIVATE", "CREDENTIAL"))
        if sensitive and key not in explicit:
            continue
        if key.startswith("VA3LM_MODEL_") and key not in explicit:
            continue
        result[key] = value
    return result


def _command_policy(argv: list[str]) -> None:
    executable = Path(argv[0]).name
    if executable == "git":
        if len(argv) < 2 or argv[1] not in _GIT_READ_ONLY:
            allowed = ", ".join(sorted(_GIT_READ_ONLY))
            raise WorkspaceError(f"git is read-only in VA3LM command mode; allowed subcommands: {allowed}")
        return

    if executable in {"npm", "pnpm", "yarn"}:
        lowered = [item.lower() for item in argv[1:]]
        if lowered and lowered[0] in _BLOCKED_PACKAGE_ACTIONS:
            raise WorkspaceError(f"package-manager {lowered[0]} is blocked by the local coding runtime")
        if "run" in lowered:
            run_index = lowered.index("run")
            if run_index + 1 < len(lowered) and lowered[run_index + 1] in _BLOCKED_PACKAGE_ACTIONS:
                raise WorkspaceError(f"package-manager script {lowered[run_index + 1]} is blocked by the local coding runtime")


class WorkspaceRuntime:
    """Local coding tools with strict file-tool boundaries and explicit command approval.

    VA3LM file operations are confined to the configured workspace. Development
    commands start with that workspace as their current directory, use shell=False,
    and require explicit approval, but they are not an operating-system filesystem
    sandbox. Trusted project code can still access resources granted to the local OS
    user. Production isolation therefore requires a separate container/VM runner.
    """

    def __init__(self, root: str | Path | None = None) -> None:
        configured = root or os.getenv("VA3LM_WORKSPACE_ROOT") or os.getcwd()
        self.root = Path(configured).expanduser().resolve()
        if not self.root.exists() or not self.root.is_dir():
            raise WorkspaceError(f"workspace root is not a directory: {self.root}")
        self.meta_dir = self.root / ".va3lm"
        self.backup_dir = self.meta_dir / "backups"

    def status(self) -> dict[str, Any]:
        return {
            "root": str(self.root),
            "exists": self.root.exists(),
            "writesRequireApproval": True,
            "commandsRequireApproval": True,
            "shell": False,
            "commandFilesystemSandboxed": False,
            "commandWorkingDirectory": str(self.root),
            "allowedCommands": sorted(_allowed_commands()),
            "gitPolicy": "read-only-subcommands",
            "publishDeployCommandsBlocked": True,
            "maxTextBytes": _MAX_TEXT_BYTES,
            "modelSecretsPassedToCommandsByDefault": False,
        }

    def _resolve(self, relative: str | Path, *, allow_meta: bool = False) -> Path:
        raw = Path(relative)
        if raw.is_absolute():
            raise WorkspaceError("absolute paths are not allowed")
        candidate = (self.root / raw).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceError("path escapes workspace root") from exc
        rel = candidate.relative_to(self.root)
        if not allow_meta and ".va3lm" in rel.parts:
            raise WorkspaceError(".va3lm runtime metadata is not directly accessible")
        if ".git" in rel.parts:
            raise WorkspaceError("direct .git file access is blocked")
        if candidate.name in _BLOCKED_FILES:
            raise WorkspaceError(f"sensitive file is blocked: {candidate.name}")
        return candidate

    def list_files(self, relative: str = ".", *, limit: int = 500) -> dict[str, Any]:
        base = self._resolve(relative)
        if not base.exists():
            raise WorkspaceError(f"path does not exist: {relative}")
        if base.is_file():
            rel = str(base.relative_to(self.root))
            return {"path": rel, "files": [rel], "truncated": False}

        files: list[str] = []
        for path in sorted(base.rglob("*")):
            rel = path.relative_to(self.root)
            if any(part in _IGNORED_PARTS for part in rel.parts):
                continue
            if path.is_file():
                files.append(str(rel))
                if len(files) >= limit:
                    return {"path": str(base.relative_to(self.root)), "files": files, "truncated": True}
        return {"path": str(base.relative_to(self.root)), "files": files, "truncated": False}

    def read_file(self, relative: str, *, max_bytes: int = 250_000) -> dict[str, Any]:
        path = self._resolve(relative)
        if not path.exists() or not path.is_file():
            raise WorkspaceError(f"file does not exist: {relative}")
        data = path.read_bytes()
        if len(data) > max_bytes:
            raise WorkspaceError(f"file exceeds read limit of {max_bytes} bytes")
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise WorkspaceError("binary/non-UTF-8 files are not readable through the text tool") from exc
        return {
            "path": str(path.relative_to(self.root)),
            "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "content": text,
        }

    def _require_approval(self, approved: bool) -> None:
        if not approved:
            raise WorkspaceError("mutation blocked: explicit approval is required")

    def _backup(self, path: Path) -> str | None:
        if not path.exists():
            return None
        if not path.is_file():
            raise WorkspaceError("only files can be backed up")
        data = path.read_bytes()
        if len(data) > _MAX_TEXT_BYTES:
            raise WorkspaceError("existing file is too large for bounded backup")
        backup_id = f"{int(time.time() * 1000)}-{hashlib.sha256(str(path).encode()).hexdigest()[:10]}"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "backupId": backup_id,
            "path": str(path.relative_to(self.root)),
            "contentB64": base64.b64encode(data).decode("ascii"),
            "sha256": hashlib.sha256(data).hexdigest(),
        }
        (self.backup_dir / f"{backup_id}.json").write_text(json.dumps(payload), encoding="utf-8")
        return backup_id

    def write_file(self, relative: str, content: str, *, approved: bool = False) -> dict[str, Any]:
        self._require_approval(approved)
        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_TEXT_BYTES:
            raise WorkspaceError(f"write exceeds {_MAX_TEXT_BYTES} byte limit")
        path = self._resolve(relative)
        backup_id = self._backup(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return {
            "path": str(path.relative_to(self.root)),
            "bytes": len(encoded),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "backupId": backup_id,
            "written": True,
        }

    def delete_file(self, relative: str, *, approved: bool = False) -> dict[str, Any]:
        self._require_approval(approved)
        path = self._resolve(relative)
        if not path.exists() or not path.is_file():
            raise WorkspaceError(f"file does not exist: {relative}")
        backup_id = self._backup(path)
        path.unlink()
        return {"path": str(path.relative_to(self.root)), "deleted": True, "backupId": backup_id}

    def restore_backup(self, backup_id: str, *, approved: bool = False) -> dict[str, Any]:
        self._require_approval(approved)
        valid_chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
        if not backup_id or any(ch not in valid_chars for ch in backup_id):
            raise WorkspaceError("invalid backup id")
        backup_path = self.backup_dir / f"{backup_id}.json"
        if not backup_path.exists():
            raise WorkspaceError("backup not found")
        payload = json.loads(backup_path.read_text(encoding="utf-8"))
        destination = self._resolve(payload["path"])
        data = base64.b64decode(payload["contentB64"].encode("ascii"))
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        return {
            "backupId": backup_id,
            "path": payload["path"],
            "restored": True,
            "sha256": hashlib.sha256(data).hexdigest(),
        }

    def run_command(self, command: str | list[str], *, timeout: int = 60, approved: bool = False) -> dict[str, Any]:
        self._require_approval(approved)
        argv = shlex.split(command) if isinstance(command, str) else list(command)
        if not argv:
            raise WorkspaceError("command is required")
        executable = Path(argv[0]).name
        if executable not in _allowed_commands():
            raise WorkspaceError(f"command is not allow-listed: {executable}")
        _command_policy(argv)
        timeout = max(1, min(int(timeout), 300))
        started = time.monotonic()
        try:
            process = subprocess.run(  # noqa: S603 - allow-list, policy, shell=False
                argv,
                cwd=self.root,
                env=_safe_environment(),
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            return {
                "command": argv,
                "exitCode": None,
                "timedOut": True,
                "durationMs": int((time.monotonic() - started) * 1000),
                "stdout": (exc.stdout or "")[-_MAX_COMMAND_OUTPUT:] if isinstance(exc.stdout, str) else "",
                "stderr": (exc.stderr or "")[-_MAX_COMMAND_OUTPUT:] if isinstance(exc.stderr, str) else "",
            }
        return {
            "command": argv,
            "exitCode": process.returncode,
            "timedOut": False,
            "durationMs": int((time.monotonic() - started) * 1000),
            "stdout": process.stdout[-_MAX_COMMAND_OUTPUT:],
            "stderr": process.stderr[-_MAX_COMMAND_OUTPUT:],
        }

    def inspect_project(self) -> dict[str, Any]:
        markers = {
            "package.json": "node",
            "pnpm-lock.yaml": "pnpm",
            "yarn.lock": "yarn",
            "pyproject.toml": "python",
            "requirements.txt": "python",
            "Dockerfile": "docker",
            "vite.config.ts": "vite",
            "next.config.js": "nextjs",
            "next.config.mjs": "nextjs",
        }
        found = {name: kind for name, kind in markers.items() if (self.root / name).exists()}
        suggested: list[str] = []
        if "package.json" in found:
            try:
                package = json.loads((self.root / "package.json").read_text(encoding="utf-8"))
                scripts = package.get("scripts") or {}
                for key in ("test", "lint", "build", "dev", "start"):
                    if key in scripts:
                        suggested.append(f"npm run {key}")
            except (OSError, UnicodeDecodeError, json.JSONDecodeError):
                pass
        if "pyproject.toml" in found or "requirements.txt" in found:
            suggested.extend(["python -m pytest -q", "python -m compileall -q ."])
        return {
            "root": str(self.root),
            "markers": found,
            "suggestedCommands": suggested,
            "automaticApprovalSupported": False,
            "commandFilesystemSandboxed": False,
        }
