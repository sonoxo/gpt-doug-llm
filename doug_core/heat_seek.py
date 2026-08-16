from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import time
import urllib.error
import urllib.request

from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Iterable


VERSION = "6.0.0"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOUG_DIR = PROJECT_ROOT / ".doug"

BASELINE_PATH = DOUG_DIR / "heatseek-baseline.json"
AUDIT_PATH = DOUG_DIR / "heatseek-audit.jsonl"
STATE_PATH = DOUG_DIR / "heatseek-state.json"

DEFAULT_WEB_PORT = 8788
FORBIDDEN_OLLAMA_PORT = 11434

IGNORE_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    "node_modules",
    "dist",
    "build",
}

SENSITIVE_FILENAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".npmrc",
    ".pypirc",
    "credentials.json",
    "secrets.json",
}

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "private_key",
        re.compile(
            r"-----BEGIN "
            r"(?:RSA |EC |OPENSSH |DSA )?"
            r"PRIVATE KEY-----"
        ),
    ),
    (
        "github_token",
        re.compile(
            r"\bgh[pousr]_[A-Za-z0-9_]{20,}\b"
        ),
    ),
    (
        "generic_secret_assignment",
        re.compile(
            r"""(?ix)
            \b(
                api[_-]?key|
                secret[_-]?key|
                access[_-]?token|
                auth[_-]?token|
                client[_-]?secret
            )
            \b
            \s*[:=]\s*
            ["']
            [^"'\n]{12,}
            ["']
            """
        ),
    ),
]

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".md",
    ".txt",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".yaml",
    ".yml",
    ".env",
    ".html",
    ".css",
    ".sh",
}


# ============================================================
# DATA TYPES
# ============================================================


@dataclass
class Finding:
    control: str
    severity: str
    title: str
    detail: str
    file: str = ""
    remediation: str = ""
    points: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CIAStatus:
    confidentiality: int = 100
    integrity: int = 100
    availability: int = 100

    @property
    def overall(self) -> int:
        return max(
            0,
            round(
                (
                    self.confidentiality
                    + self.integrity
                    + self.availability
                )
                / 3
            ),
        )

    def to_dict(self) -> dict:
        result = asdict(self)
        result["overall"] = self.overall
        return result


@dataclass
class HeatSeekReport:
    version: str
    timestamp: float
    project_root: str
    cia: CIAStatus
    findings: list[Finding] = field(default_factory=list)
    checks: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "timestamp": self.timestamp,
            "project_root": self.project_root,
            "cia": self.cia.to_dict(),
            "findings": [
                finding.to_dict()
                for finding in self.findings
            ],
            "checks": self.checks,
        }


# ============================================================
# UTILITIES
# ============================================================


def ensure_private_state_dir() -> None:
    DOUG_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        DOUG_DIR.chmod(0o700)
    except OSError:
        pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(
            lambda: handle.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def relative(path: Path) -> str:
    try:
        return str(
            path.resolve().relative_to(
                PROJECT_ROOT.resolve()
            )
        )
    except Exception:
        return str(path)


def iter_project_files() -> Iterable[Path]:
    for current, dirs, files in os.walk(PROJECT_ROOT):

        dirs[:] = [
            directory
            for directory in dirs
            if directory not in IGNORE_DIRS
        ]

        root = Path(current)

        for filename in files:
            path = root / filename

            try:
                if (
                    path.is_file()
                    and path.stat().st_size
                    <= 5_000_000
                ):
                    yield path

            except OSError:
                continue


def read_text_safe(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except Exception:
        return ""


def run_git(*args: str) -> str:
    try:
        return subprocess.check_output(
            ["git", *args],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        ).strip()
    except Exception:
        return ""


def port_open(
    host: str,
    port: int,
    timeout: float = 0.3,
) -> bool:

    try:
        with socket.create_connection(
            (host, port),
            timeout=timeout,
        ):
            return True

    except OSError:
        return False


def http_health(
    url: str,
    timeout: float = 2.0,
) -> bool:

    try:
        request = urllib.request.Request(
            url,
            method="GET",
        )

        with urllib.request.urlopen(
            request,
            timeout=timeout,
        ) as response:

            return 200 <= response.status < 500

    except Exception:
        return False


# ============================================================
# TAMPER-EVIDENT AUDIT LOG
# ============================================================


def last_audit_hash() -> str:
    if not AUDIT_PATH.exists():
        return "GENESIS"

    lines = AUDIT_PATH.read_text(
        encoding="utf-8",
        errors="ignore",
    ).splitlines()

    if not lines:
        return "GENESIS"

    try:
        record = json.loads(lines[-1])
        return str(
            record.get("record_hash", "GENESIS")
        )
    except Exception:
        return "GENESIS"


def audit(
    event: str,
    data: dict | None = None,
) -> str:

    ensure_private_state_dir()

    previous_hash = last_audit_hash()

    body = {
        "timestamp": time.time(),
        "event": event,
        "data": data or {},
        "previous_hash": previous_hash,
    }

    canonical = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    record_hash = sha256_bytes(
        previous_hash.encode("utf-8")
        + canonical
    )

    body["record_hash"] = record_hash

    with AUDIT_PATH.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(body)
            + "\n"
        )

    try:
        AUDIT_PATH.chmod(0o600)
    except OSError:
        pass

    return record_hash


def verify_audit_chain() -> tuple[bool, str]:
    if not AUDIT_PATH.exists():
        return True, "No audit records yet"

    previous = "GENESIS"

    for line_number, line in enumerate(
        AUDIT_PATH.read_text(
            encoding="utf-8",
            errors="ignore",
        ).splitlines(),
        1,
    ):
        try:
            record = json.loads(line)

            stored_hash = record.pop(
                "record_hash"
            )

            expected_previous = record.get(
                "previous_hash"
            )

            if expected_previous != previous:
                return (
                    False,
                    f"Audit chain broken at line "
                    f"{line_number}",
                )

            canonical = json.dumps(
                record,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")

            calculated = sha256_bytes(
                previous.encode("utf-8")
                + canonical
            )

            if calculated != stored_hash:
                return (
                    False,
                    f"Audit record modified at "
                    f"line {line_number}",
                )

            previous = stored_hash

        except Exception as exc:
            return (
                False,
                f"Audit parse error at line "
                f"{line_number}: {exc}",
            )

    return True, "Audit chain verified"


# ============================================================
# CONFIDENTIALITY
# ============================================================


def confidentiality_checks() -> tuple[
    list[Finding],
    dict,
]:

    findings: list[Finding] = []

    files_checked = 0
    sensitive_files = []
    tracked_sensitive = []

    tracked_files = set(
        run_git(
            "ls-files"
        ).splitlines()
    )

    for path in iter_project_files():

        files_checked += 1
        rel = relative(path)

        if path.name in SENSITIVE_FILENAMES:
            sensitive_files.append(rel)

            if rel in tracked_files:
                tracked_sensitive.append(rel)

                findings.append(
                    Finding(
                        control="C",
                        severity="HIGH",
                        title="Sensitive file tracked by Git",
                        detail=(
                            f"{rel} appears to be "
                            f"tracked by Git."
                        ),
                        file=rel,
                        remediation=(
                            "Move credentials to ignored "
                            "environment storage and rotate "
                            "exposed secrets."
                        ),
                        points=25,
                    )
                )

        if (
            path.suffix.lower()
            not in TEXT_EXTENSIONS
            and path.name
            not in SENSITIVE_FILENAMES
        ):
            continue

        content = read_text_safe(path)

        if not content:
            continue

        for (
            secret_type,
            pattern,
        ) in SECRET_PATTERNS:

            if pattern.search(content):

                findings.append(
                    Finding(
                        control="C",
                        severity="HIGH",
                        title=(
                            "Potential embedded secret"
                        ),
                        detail=(
                            f"Pattern '{secret_type}' "
                            f"detected."
                        ),
                        file=rel,
                        remediation=(
                            "Remove embedded credential, "
                            "store it outside source control, "
                            "and rotate it if real."
                        ),
                        points=20,
                    )
                )

                break

    for path in PROJECT_ROOT.rglob("*"):

        if not path.is_file():
            continue

        if path.name not in SENSITIVE_FILENAMES:
            continue

        try:
            mode = stat.S_IMODE(
                path.stat().st_mode
            )

            if mode & 0o077:

                findings.append(
                    Finding(
                        control="C",
                        severity="MEDIUM",
                        title=(
                            "Sensitive file permissions "
                            "too broad"
                        ),
                        detail=(
                            f"{relative(path)} mode is "
                            f"{oct(mode)}."
                        ),
                        file=relative(path),
                        remediation=(
                            "Set sensitive files to "
                            "owner-only permissions."
                        ),
                        points=10,
                    )
                )

        except OSError:
            continue

    checks = {
        "files_checked": files_checked,
        "sensitive_files": sensitive_files,
        "tracked_sensitive_files": tracked_sensitive,
    }

    return findings, checks


# ============================================================
# INTEGRITY
# ============================================================


def build_manifest() -> dict[str, str]:
    manifest: dict[str, str] = {}

    for path in iter_project_files():

        rel = relative(path)

        if rel.startswith(".doug/"):
            continue

        try:
            manifest[rel] = sha256_file(path)
        except Exception:
            continue

    return dict(
        sorted(
            manifest.items()
        )
    )


def create_baseline() -> dict:
    ensure_private_state_dir()

    manifest = build_manifest()

    payload = {
        "version": VERSION,
        "created_at": time.time(),
        "git_branch": (
            run_git(
                "branch",
                "--show-current",
            )
            or "unknown"
        ),
        "git_commit": (
            run_git(
                "rev-parse",
                "HEAD",
            )
            or "unknown"
        ),
        "files": manifest,
    }

    BASELINE_PATH.write_text(
        json.dumps(
            payload,
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        BASELINE_PATH.chmod(0o600)
    except OSError:
        pass

    audit(
        "integrity_baseline_created",
        {
            "files": len(manifest),
            "git_commit": payload["git_commit"],
        },
    )

    return payload


def verify_baseline() -> tuple[
    list[Finding],
    dict,
]:

    findings: list[Finding] = []

    if not BASELINE_PATH.exists():

        findings.append(
            Finding(
                control="I",
                severity="MEDIUM",
                title="No integrity baseline",
                detail=(
                    "Heat Seek does not yet have a "
                    "known-good file hash baseline."
                ),
                remediation=(
                    "Run: python3 heatseek.py baseline"
                ),
                points=10,
            )
        )

        return findings, {
            "baseline_exists": False,
        }

    try:
        baseline = json.loads(
            BASELINE_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception:

        findings.append(
            Finding(
                control="I",
                severity="HIGH",
                title="Integrity baseline unreadable",
                detail=(
                    "The baseline file cannot be parsed."
                ),
                remediation=(
                    "Inspect .doug/heatseek-baseline.json "
                    "and recreate it after verification."
                ),
                points=25,
            )
        )

        return findings, {
            "baseline_exists": True,
            "baseline_valid": False,
        }

    expected = baseline.get(
        "files",
        {},
    )

    current = build_manifest()

    modified = sorted(
        path
        for path in expected
        if (
            path in current
            and current[path] != expected[path]
        )
    )

    deleted = sorted(
        path
        for path in expected
        if path not in current
    )

    added = sorted(
        path
        for path in current
        if path not in expected
    )

    if modified:

        findings.append(
            Finding(
                control="I",
                severity="MEDIUM",
                title="Files changed since baseline",
                detail=(
                    f"{len(modified)} tracked "
                    f"baseline file(s) changed."
                ),
                remediation=(
                    "Review the changes. If expected, "
                    "create a new baseline after tests."
                ),
                points=min(
                    20,
                    2 * len(modified),
                ),
            )
        )

    if deleted:

        findings.append(
            Finding(
                control="I",
                severity="MEDIUM",
                title="Baseline files missing",
                detail=(
                    f"{len(deleted)} baseline "
                    f"file(s) are missing."
                ),
                remediation=(
                    "Confirm deletions were intentional."
                ),
                points=min(
                    20,
                    3 * len(deleted),
                ),
            )
        )

    audit_ok, audit_message = (
        verify_audit_chain()
    )

    if not audit_ok:

        findings.append(
            Finding(
                control="I",
                severity="HIGH",
                title="Audit chain verification failed",
                detail=audit_message,
                remediation=(
                    "Preserve the audit log and inspect "
                    "for unexpected modification."
                ),
                points=30,
            )
        )

    git_dirty = bool(
        run_git(
            "status",
            "--porcelain",
        )
    )

    checks = {
        "baseline_exists": True,
        "baseline_valid": True,
        "modified": modified,
        "deleted": deleted,
        "added": added,
        "git_dirty": git_dirty,
        "audit_chain_valid": audit_ok,
        "audit_chain_message": audit_message,
    }

    return findings, checks


# ============================================================
# AVAILABILITY
# ============================================================


def availability_checks(
    web_port: int = DEFAULT_WEB_PORT,
) -> tuple[
    list[Finding],
    dict,
]:

    findings: list[Finding] = []

    disk = shutil.disk_usage(
        PROJECT_ROOT
    )

    disk_free_pct = (
        disk.free / disk.total * 100
        if disk.total
        else 0
    )

    if disk_free_pct < 5:

        findings.append(
            Finding(
                control="A",
                severity="HIGH",
                title="Critically low disk space",
                detail=(
                    f"Only {disk_free_pct:.1f}% "
                    f"disk space remains."
                ),
                remediation=(
                    "Free disk space before builds "
                    "or deployments."
                ),
                points=30,
            )
        )

    elif disk_free_pct < 15:

        findings.append(
            Finding(
                control="A",
                severity="MEDIUM",
                title="Low disk space",
                detail=(
                    f"{disk_free_pct:.1f}% "
                    f"disk space remains."
                ),
                remediation=(
                    "Clear unnecessary build artifacts "
                    "and caches."
                ),
                points=15,
            )
        )

    web_port_open = port_open(
        "127.0.0.1",
        web_port,
    )

    web_healthy = False

    if web_port_open:
        web_healthy = http_health(
            f"http://127.0.0.1:{web_port}/"
        )

    ollama_port_open = port_open(
        "127.0.0.1",
        FORBIDDEN_OLLAMA_PORT,
    )

    if ollama_port_open:

        findings.append(
            Finding(
                control="A",
                severity="MEDIUM",
                title="Ollama port detected",
                detail=(
                    "Port 11434 is listening even "
                    "though GPT-Doug is configured "
                    "for no-Ollama operation."
                ),
                remediation=(
                    "Stop the Ollama process if it is "
                    "not intentionally running."
                ),
                points=15,
            )
        )

    load = None

    if hasattr(os, "getloadavg"):
        try:
            load = os.getloadavg()
        except Exception:
            load = None

    checks = {
        "disk_free_percent": round(
            disk_free_pct,
            2,
        ),
        "web_port": web_port,
        "web_port_open": web_port_open,
        "web_healthy": web_healthy,
        "ollama_11434_open": ollama_port_open,
        "load_average": load,
    }

    return findings, checks


# ============================================================
# SCORING
# ============================================================


def calculate_cia(
    findings: list[Finding],
) -> CIAStatus:

    cia = CIAStatus()

    for finding in findings:

        deduction = max(
            0,
            finding.points,
        )

        if finding.control == "C":
            cia.confidentiality -= deduction

        elif finding.control == "I":
            cia.integrity -= deduction

        elif finding.control == "A":
            cia.availability -= deduction

    cia.confidentiality = max(
        0,
        min(
            100,
            cia.confidentiality,
        ),
    )

    cia.integrity = max(
        0,
        min(
            100,
            cia.integrity,
        ),
    )

    cia.availability = max(
        0,
        min(
            100,
            cia.availability,
        ),
    )

    return cia


# ============================================================
# MASTER SCAN
# ============================================================


def scan(
    web_port: int = DEFAULT_WEB_PORT,
) -> HeatSeekReport:

    ensure_private_state_dir()

    c_findings, c_checks = (
        confidentiality_checks()
    )

    i_findings, i_checks = (
        verify_baseline()
    )

    a_findings, a_checks = (
        availability_checks(
            web_port=web_port
        )
    )

    findings = (
        c_findings
        + i_findings
        + a_findings
    )

    cia = calculate_cia(findings)

    report = HeatSeekReport(
        version=VERSION,
        timestamp=time.time(),
        project_root=str(PROJECT_ROOT),
        cia=cia,
        findings=findings,
        checks={
            "confidentiality": c_checks,
            "integrity": i_checks,
            "availability": a_checks,
        },
    )

    STATE_PATH.write_text(
        json.dumps(
            report.to_dict(),
            indent=2,
        ),
        encoding="utf-8",
    )

    try:
        STATE_PATH.chmod(0o600)
    except OSError:
        pass

    audit(
        "heat_seek_scan",
        {
            "overall": cia.overall,
            "confidentiality": (
                cia.confidentiality
            ),
            "integrity": (
                cia.integrity
            ),
            "availability": (
                cia.availability
            ),
            "findings": len(findings),
        },
    )

    return report


# ============================================================
# SAFE HARDENING
# ============================================================


def safe_harden() -> list[str]:
    actions: list[str] = []

    ensure_private_state_dir()

    actions.append(
        "Protected .doug state directory with 0700"
    )

    gitignore = PROJECT_ROOT / ".gitignore"

    existing = (
        gitignore.read_text(
            encoding="utf-8",
            errors="ignore",
        )
        if gitignore.exists()
        else ""
    )

    additions = [
        ".env",
        ".env.local",
        ".env.*.local",
        "*.pem",
        "*.key",
        ".doug/*.runtime",
    ]

    missing = [
        line
        for line in additions
        if line not in existing.splitlines()
    ]

    if missing:

        with gitignore.open(
            "a",
            encoding="utf-8",
        ) as handle:

            if (
                existing
                and not existing.endswith("\n")
            ):
                handle.write("\n")

            handle.write(
                "\n# GPT Doug Heat Seek security\n"
            )

            for line in missing:
                handle.write(
                    line + "\n"
                )

        actions.append(
            "Extended .gitignore for common "
            "credential files"
        )

    for path in PROJECT_ROOT.rglob("*"):

        if (
            not path.is_file()
            or path.name
            not in SENSITIVE_FILENAMES
        ):
            continue

        try:
            path.chmod(0o600)

            actions.append(
                f"Set owner-only permissions: "
                f"{relative(path)}"
            )

        except OSError:
            continue

    audit(
        "safe_hardening",
        {
            "actions": actions,
        },
    )

    return actions


# ============================================================
# CIA ITERATION ENGINE
#
# Discover
# -> Assess
# -> Harden
# -> Re-scan
# -> Verify
# -> Measure improvement
#
# ============================================================


def iterate(
    rounds: int = 3,
    target_score: int = 95,
    harden: bool = False,
    web_port: int = DEFAULT_WEB_PORT,
) -> dict:

    rounds = max(
        1,
        min(
            rounds,
            10,
        ),
    )

    history = []

    previous_score = None

    for iteration_number in range(
        1,
        rounds + 1,
    ):

        report = scan(
            web_port=web_port
        )

        score = report.cia.overall

        history.append(
            {
                "iteration": iteration_number,
                "score": score,
                "confidentiality": (
                    report.cia.confidentiality
                ),
                "integrity": (
                    report.cia.integrity
                ),
                "availability": (
                    report.cia.availability
                ),
                "findings": len(
                    report.findings
                ),
            }
        )

        if score >= target_score:
            break

        if (
            harden
            and iteration_number == 1
        ):
            safe_harden()

        if (
            previous_score is not None
            and score <= previous_score
            and not harden
        ):
            break

        previous_score = score

    final = scan(
        web_port=web_port
    )

    result = {
        "target_score": target_score,
        "target_met": (
            final.cia.overall
            >= target_score
        ),
        "history": history,
        "final": final.to_dict(),
    }

    audit(
        "cia_iteration_complete",
        {
            "target": target_score,
            "final_score": (
                final.cia.overall
            ),
            "iterations": len(history),
        },
    )

    return result


# ============================================================
# TURTLE SHELL RUNTIME ENVIRONMENT
# ============================================================


def turtle_environment(
    port: int = DEFAULT_WEB_PORT,
) -> dict[str, str]:

    env = os.environ.copy()

    env["GPT_DOUG_PROVIDER"] = "none"
    env["PORT"] = str(port)

    env.setdefault(
        "HOST",
        "127.0.0.1",
    )

    env.setdefault(
        "DOUG_HOST",
        "127.0.0.1",
    )

    # Explicitly remove local Ollama overrides.
    for key in (
        "OLLAMA_HOST",
        "OLLAMA_API_BASE",
    ):
        env.pop(
            key,
            None,
        )

    return env


def launch_turtle_shell(
    port: int = DEFAULT_WEB_PORT,
) -> dict:

    if port_open(
        "127.0.0.1",
        port,
    ):

        result = {
            "started": False,
            "reason": (
                f"Port {port} already listening"
            ),
            "url": (
                f"http://127.0.0.1:{port}"
            ),
        }

        audit(
            "turtle_shell_launch_skipped",
            result,
        )

        return result

    server = PROJECT_ROOT / "web" / "server.py"

    if not server.exists():
        raise FileNotFoundError(
            "web/server.py not found"
        )

    log_path = Path(
        "/tmp/gpt-doug-heatseek.log"
    )

    env = turtle_environment(
        port=port
    )

    log_handle = log_path.open(
        "a",
        encoding="utf-8",
    )

    process = subprocess.Popen(
        [
            sys.executable,
            str(server),
        ],
        cwd=PROJECT_ROOT,
        env=env,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )

    time.sleep(2)

    healthy = port_open(
        "127.0.0.1",
        port,
    )

    result = {
        "started": True,
        "pid": process.pid,
        "healthy": healthy,
        "port": port,
        "url": (
            f"http://127.0.0.1:{port}"
        ),
        "log": str(log_path),
        "provider": "none",
        "ollama": False,
    }

    audit(
        "turtle_shell_launched",
        result,
    )

    return result


# ============================================================
# SNAPSHOT
# ============================================================


def create_snapshot() -> dict:

    ensure_private_state_dir()

    timestamp = time.strftime(
        "%Y%m%d-%H%M%S"
    )

    snapshot_dir = (
        DOUG_DIR
        / "snapshots"
    )

    snapshot_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:
        snapshot_dir.chmod(0o700)
    except OSError:
        pass

    output = (
        snapshot_dir
        / f"heatseek-{timestamp}.tar.gz"
    )

    subprocess.check_call(
        [
            "tar",
            "-czf",
            str(output),
            "--exclude=.git",
            "--exclude=.doug/snapshots",
            "--exclude=node_modules",
            "--exclude=.venv",
            ".",
        ],
        cwd=PROJECT_ROOT,
    )

    result = {
        "snapshot": str(output),
        "sha256": sha256_file(output),
        "bytes": output.stat().st_size,
    }

    audit(
        "snapshot_created",
        result,
    )

    return result
