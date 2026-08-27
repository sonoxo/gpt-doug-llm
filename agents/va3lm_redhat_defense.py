"""VA3LM Red Hat defensive intelligence shield.

Deterministic, local-only posture validation for Red Hat Enterprise Linux style
hosts. This module does not exploit, scan remote targets, retaliate, or execute
arbitrary shell. It only runs fixed read-only local checks and produces a
provenance-locked defensive evidence package.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MODE = "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY"
SOURCE_ID = "NSA-QTFY-2026-08-26"
SOURCE_URL = (
    "https://www.nsa.gov/Press-Room/Press-Releases-Statements/Press-Release-View/"
    "Article/4583539/nsa-joins-fbi-in-issuing-warning-about-chinese-hacking-group-qtfy-cyber-activity/"
)
OUTPUT = Path("intel/va3lm/redhat-defense-evidence.json")
LOCK = Path("intel/va3lm/redhat-defense-lock.json")


@dataclass(frozen=True)
class CheckResult:
    control_id: str
    status: str
    detail: str
    source_intel: str


CONTROL_CATALOG: tuple[dict[str, str], ...] = (
    {
        "id": "VA3LM-RH-PATCH",
        "title": "Software and firmware currency",
        "objective": "Keep supported packages current and maintain firmware-update visibility.",
        "sourceIntel": "NSA recommends applying the latest software and firmware updates.",
    },
    {
        "id": "VA3LM-RH-WEB",
        "title": "Public-facing application exposure review",
        "objective": "Inventory exposed services and protect operational information from unintended disclosure.",
        "sourceIntel": "NSA recommends regularly auditing webpages and Internet-facing applications.",
    },
    {
        "id": "VA3LM-RH-SEGMENT",
        "title": "Critical-system edge isolation",
        "objective": "Separate critical workloads from edge devices with host/network policy boundaries.",
        "sourceIntel": "NSA recommends isolating critical systems from edge devices.",
    },
    {
        "id": "VA3LM-RH-HUNT",
        "title": "IOC hunting readiness",
        "objective": "Retain searchable host telemetry for vetted defensive IOC hunting.",
        "sourceIntel": "NSA recommends hunting for provided indicators of compromise.",
    },
    {
        "id": "VA3LM-RH-SELINUX",
        "title": "SELinux mandatory access control",
        "objective": "Keep SELinux enforcing to reduce post-exploitation freedom of movement.",
        "sourceIntel": "Defense-in-depth response to zero/N-day exploitation and persistence risk.",
    },
    {
        "id": "VA3LM-RH-FIREWALL",
        "title": "Host firewall enforcement",
        "objective": "Keep firewalld active and use explicit zone/service exposure.",
        "sourceIntel": "Supports edge isolation and reduction of exposed attack surface.",
    },
    {
        "id": "VA3LM-RH-SSH",
        "title": "Administrative access hardening",
        "objective": "Disable direct root SSH and reduce credential-based persistence opportunities.",
        "sourceIntel": "NSA describes theft/use of legitimate credentials for persistence.",
    },
    {
        "id": "VA3LM-RH-AUDIT",
        "title": "Audit telemetry",
        "objective": "Keep auditd active for privileged-action and persistence evidence.",
        "sourceIntel": "Supports defensive hunting and incident reconstruction.",
    },
    {
        "id": "VA3LM-RH-INTEGRITY",
        "title": "File integrity monitoring",
        "objective": "Maintain AIDE or equivalent host integrity evidence.",
        "sourceIntel": "Supports detection of unauthorized system modification.",
    },
    {
        "id": "VA3LM-RH-ALLOWLIST",
        "title": "Application allowlisting",
        "objective": "Use fapolicyd where operationally appropriate to restrict untrusted execution.",
        "sourceIntel": "Limits malware/tool execution after initial access.",
    },
    {
        "id": "VA3LM-RH-JOURNAL",
        "title": "Persistent security logging",
        "objective": "Retain persistent system journals for defensive investigation.",
        "sourceIntel": "Supports source-grounded IOC and behavior hunting.",
    },
    {
        "id": "VA3LM-RH-TIME",
        "title": "Trusted time synchronization",
        "objective": "Keep chronyd active so security evidence has reliable timestamps.",
        "sourceIntel": "Supports correlation across host and intelligence timelines.",
    },
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _run_fixed(argv: list[str]) -> tuple[int, str]:
    """Run one fixed local read-only command without a shell."""
    if not argv or shutil.which(argv[0]) is None:
        return 127, "command unavailable"
    try:
        result = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            env={"PATH": os.environ.get("PATH", "")},
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 126, f"check error: {type(exc).__name__}"
    text = (result.stdout.strip() or result.stderr.strip())[:1000]
    return result.returncode, text


def _systemctl_active(unit: str) -> CheckResult:
    code, text = _run_fixed(["systemctl", "is-active", unit])
    status = "PASS" if code == 0 and text == "active" else ("UNKNOWN" if code == 127 else "WARN")
    return CheckResult(f"VA3LM-RH-{unit.split('.')[0].upper()}", status, f"{unit}: {text}", SOURCE_ID)


def _selinux() -> CheckResult:
    code, text = _run_fixed(["getenforce"])
    if code == 127:
        return CheckResult("VA3LM-RH-SELINUX", "UNKNOWN", "getenforce unavailable", SOURCE_ID)
    status = "PASS" if text.lower() == "enforcing" else "WARN"
    return CheckResult("VA3LM-RH-SELINUX", status, f"SELinux={text}", SOURCE_ID)


def _firewalld() -> CheckResult:
    code, text = _run_fixed(["firewall-cmd", "--state"])
    if code == 127:
        return CheckResult("VA3LM-RH-FIREWALL", "UNKNOWN", "firewall-cmd unavailable", SOURCE_ID)
    status = "PASS" if code == 0 and "running" in text.lower() else "WARN"
    return CheckResult("VA3LM-RH-FIREWALL", status, f"firewalld={text}", SOURCE_ID)


def _ssh_root_login() -> CheckResult:
    path = Path("/etc/ssh/sshd_config")
    if not path.is_file():
        return CheckResult("VA3LM-RH-SSH", "UNKNOWN", "sshd_config unavailable", SOURCE_ID)
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError as exc:
        return CheckResult("VA3LM-RH-SSH", "UNKNOWN", f"cannot read sshd_config: {exc}", SOURCE_ID)
    values = []
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts and parts[0].lower() == "permitrootlogin" and len(parts) > 1:
            values.append(parts[1].lower())
    if not values:
        return CheckResult("VA3LM-RH-SSH", "WARN", "PermitRootLogin not explicitly hardened", SOURCE_ID)
    value = values[-1]
    status = "PASS" if value in {"no", "prohibit-password", "without-password"} else "WARN"
    return CheckResult("VA3LM-RH-SSH", status, f"PermitRootLogin={value}", SOURCE_ID)


def _rpm_package(control_id: str, package: str, objective: str) -> CheckResult:
    code, text = _run_fixed(["rpm", "-q", package])
    if code == 127:
        return CheckResult(control_id, "UNKNOWN", "rpm unavailable", SOURCE_ID)
    status = "PASS" if code == 0 else "WARN"
    return CheckResult(control_id, status, f"{objective}: {text}", SOURCE_ID)


def _journal_persistence() -> CheckResult:
    path = Path("/var/log/journal")
    status = "PASS" if path.is_dir() else "WARN"
    return CheckResult(
        "VA3LM-RH-JOURNAL",
        status,
        "persistent journal directory present" if status == "PASS" else "persistent journal directory not detected",
        SOURCE_ID,
    )


def _service_inventory() -> CheckResult:
    code, text = _run_fixed(["ss", "-lntup"])
    if code == 127:
        return CheckResult("VA3LM-RH-WEB", "UNKNOWN", "ss unavailable", SOURCE_ID)
    lines = [line for line in text.splitlines() if line.strip()]
    listeners = max(0, len(lines) - 1)
    return CheckResult(
        "VA3LM-RH-WEB",
        "REVIEW",
        f"local listening-socket inventory captured: {listeners} rows; analyst review required",
        SOURCE_ID,
    )


def audit_host() -> dict[str, Any]:
    checks = [
        _selinux(),
        _firewalld(),
        _ssh_root_login(),
        _systemctl_active("auditd.service"),
        _systemctl_active("chronyd.service"),
        _rpm_package("VA3LM-RH-INTEGRITY", "aide", "AIDE package"),
        _rpm_package("VA3LM-RH-ALLOWLIST", "fapolicyd", "fapolicyd package"),
        _journal_persistence(),
        _service_inventory(),
    ]
    platform_blob = {
        "system": platform.system(),
        "release": platform.release(),
        "machine": platform.machine(),
        "platform": platform.platform(),
    }
    return {
        "framework": "VA3LM RED HAT DEFENSIVE INTELLIGENCE SHIELD",
        "version": "1.0.0",
        "mode": MODE,
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceIntel": {
            "sourceId": SOURCE_ID,
            "sourceUrl": SOURCE_URL,
            "sourceDate": "2026-08-26",
            "sourceType": "AGENCY_INTELLIGENCE",
            "threatPattern": [
                "QScan vulnerability scanning and exploitation",
                "QTRouter obfuscation network",
                "botnet management platforms using compromised IoT devices",
                "zero-day and N-day exploitation",
                "legitimate credential theft and persistence",
            ],
            "recommendedDefenses": [
                "apply software and firmware updates",
                "audit webpages and Internet-facing applications",
                "isolate critical systems from edge devices",
                "hunt vetted indicators of compromise",
            ],
        },
        "host": platform_blob,
        "controls": list(CONTROL_CATALOG),
        "checks": [asdict(item) for item in checks],
        "guardrails": {
            "remoteScanning": False,
            "exploitExecution": False,
            "retaliation": False,
            "arbitraryShell": False,
            "automaticContainment": False,
            "humanReviewRequired": True,
            "localReadOnlyChecksOnly": True,
        },
    }


def write_locked_evidence(root: str | Path) -> dict[str, Any]:
    root = Path(root).resolve()
    evidence = audit_host()
    output = root / OUTPUT
    lock_path = root / LOCK
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence_text = json.dumps(evidence, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    output.write_text(evidence_text, encoding="utf-8")
    digest = _sha256(evidence_text.encode("utf-8"))
    lock = {
        "framework": "VA3LM RED HAT DEFENSE LOCK",
        "version": "1.0.0",
        "locked": True,
        "lockId": digest[:24],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sourceIntel": SOURCE_ID,
        "sourceUrl": SOURCE_URL,
        "evidence": OUTPUT.as_posix(),
        "evidenceSha256": digest,
        "guardrails": evidence["guardrails"],
    }
    lock_path.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"evidence": evidence, "lock": lock}


def status(root: str | Path) -> str:
    root = Path(root).resolve()
    lock_path = root / LOCK
    if not lock_path.is_file():
        return "🛡️ VA3LM RED HAT DEFENSE // NO LOCK // run audit"
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        evidence_path = root / str(lock.get("evidence") or "")
        actual = _sha256(evidence_path.read_bytes()) if evidence_path.is_file() else ""
    except (OSError, json.JSONDecodeError) as exc:
        return f"🛡️ VA3LM RED HAT DEFENSE // INVALID LOCK // {exc}"
    valid = bool(actual and actual == lock.get("evidenceSha256"))
    return (
        "🛡️ VA3LM RED HAT DEFENSE // " + ("LOCK VERIFIED ✅" if valid else "LOCK FAILED ❌") + "\n"
        f"Lock ID: {lock.get('lockId')}\n"
        f"Source intelligence: {lock.get('sourceIntel')}\n"
        "Mode: DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY"
    )


def print_audit(result: dict[str, Any]) -> None:
    evidence = result["evidence"]
    lock = result["lock"]
    print("\n🛡️ VA3LM RED HAT DEFENSIVE INTELLIGENCE SHIELD")
    for item in evidence["checks"]:
        icon = "✅" if item["status"] == "PASS" else ("⚠️" if item["status"] in {"WARN", "REVIEW"} else "❔")
        print(f"{icon} {item['control_id']}: {item['detail']}")
    print(f"🔐 Lock ID: {lock['lockId']}")
    print("🚫 remote scanning OFF // exploit execution OFF // retaliation OFF // arbitrary shell OFF\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="VA3LM Red Hat defensive intelligence shield")
    parser.add_argument("command", choices=("audit", "status", "catalog"), nargs="?", default="status")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if args.command == "audit":
        result = write_locked_evidence(args.root)
        print_audit(result)
        return 0
    if args.command == "catalog":
        print(json.dumps(list(CONTROL_CATALOG), indent=2, ensure_ascii=False))
        return 0
    print(status(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
