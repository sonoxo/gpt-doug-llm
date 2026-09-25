#!/usr/bin/env python3
"""ZYRAPALANTIR live defensive monitoring runtime.

This process continuously evaluates the local defensive posture using the
existing Zyra Sentinel scanner plus Palantir Maven and GPT-REDPANDA readiness
checks. It is monitoring/decision-support only: it never performs external
remediation or executes retrieved artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[1]
STATE_DIR = pathlib.Path.home() / ".config" / "gpt-doug"
DEFENSE_STATE = STATE_DIR / "defense-profile.json"
LIVE_STATE = STATE_DIR / "zyrapalantir-live-state.json"
AUDIT_LOG = STATE_DIR / "zyrapalantir-live-audit.jsonl"
LIVE_ONTOLOGY = ROOT / "safety-shield" / "ontology" / "zyrapalantir-live.json"

SEVERITY_RANK = {
    "INFO": 0,
    "SAFE": 0,
    "LOW": 1,
    "MEDIUM": 2,
    "HIGH": 3,
    "CRITICAL": 4,
    "PLANETARY": 4,
}

_STOP = False


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: pathlib.Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json_private(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def append_audit(payload: dict[str, Any]) -> None:
    AUDIT_LOG.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    AUDIT_LOG.chmod(0o600)


def defense_profile_active() -> bool:
    state = load_json(DEFENSE_STATE, {}) or {}
    return bool(state.get("active"))


def validate_live_policy() -> dict[str, Any]:
    policy = load_json(LIVE_ONTOLOGY)
    if not isinstance(policy, dict):
        raise RuntimeError("ZYRAPALANTIR live ontology is missing or invalid")
    if policy.get("mode") != "DEFENSIVE_MONITORING_ONLY":
        raise RuntimeError("live ontology is not in DEFENSIVE_MONITORING_ONLY mode")
    controls = policy.get("controls", {})
    if controls.get("automaticExternalAction") is not False:
        raise RuntimeError("live policy must prohibit automatic external action")
    if controls.get("artifactExecutionFromMonitor") is not False:
        raise RuntimeError("live policy must prohibit artifact execution from monitor")
    return policy


def run_json_command(argv: list[str], timeout: int = 90) -> tuple[bool, dict[str, Any] | str]:
    try:
        proc = subprocess.run(
            argv,
            cwd=str(ROOT),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except Exception as exc:
        return False, f"{type(exc).__name__}: {exc}"

    text = (proc.stdout or "").strip()
    if proc.returncode != 0:
        err = (proc.stderr or text or f"exit {proc.returncode}").strip()
        return False, err
    try:
        return True, json.loads(text)
    except Exception:
        return True, text


def maven_probe() -> tuple[bool, dict[str, Any] | str]:
    ok, result = run_json_command([sys.executable, str(ROOT / "palantir_maven.py"), "probe"], timeout=45)
    if not ok:
        return False, result
    if isinstance(result, dict):
        reachable = bool(result.get("reachable")) and not bool(result.get("auth_rejected"))
        return reachable, result
    return False, result


def redpanda_cpr() -> tuple[bool, dict[str, Any] | str]:
    ok, result = run_json_command(
        [sys.executable, str(ROOT / "redpanda-desktop" / "palantir_cpr_probe.py")],
        timeout=90,
    )
    if not ok:
        return False, result
    if isinstance(result, dict):
        return bool(result.get("ok")), result
    return False, result


def finding_to_dict(finding: Any) -> dict[str, Any]:
    return {
        "severity": str(getattr(finding, "severity", "INFO")).upper(),
        "category": str(getattr(finding, "category", "unknown")),
        "target": str(getattr(finding, "target", "local-system")),
        "description": str(getattr(finding, "description", ""))[:500],
        "recommendation": str(getattr(finding, "recommendation", ""))[:500],
    }


def run_sentinel(scan_mode: str) -> list[dict[str, Any]]:
    sys.path.insert(0, str(ROOT))
    from golden_shield import ZyraSentinel  # imported lazily after policy checks

    sentinel = ZyraSentinel()
    if scan_mode == "internal":
        findings = sentinel.scan_internal()
    elif scan_mode == "external":
        findings = sentinel.scan_external()
    elif scan_mode == "satellite":
        findings = sentinel.scan_satellite()
    elif scan_mode == "darkweb":
        findings = sentinel.scan_darkweb_exposure()
    elif scan_mode == "full":
        report = sentinel.full_sweep()
        findings = (
            list(report.internal_findings)
            + list(report.external_findings)
            + list(report.satellite_findings)
            + list(report.darkweb_findings)
        )
    else:
        raise RuntimeError(f"unsupported scan mode: {scan_mode}")
    return [finding_to_dict(item) for item in findings]


def finding_fingerprint(finding: dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(finding.get("severity", "")),
            str(finding.get("category", "")),
            str(finding.get("target", "")),
            str(finding.get("description", "")),
        ]
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def highest_severity(findings: list[dict[str, Any]]) -> str:
    if not findings:
        return "SAFE"
    return max(findings, key=lambda f: SEVERITY_RANK.get(str(f.get("severity", "INFO")).upper(), 0)).get(
        "severity", "INFO"
    )


def update_high_persistence(
    previous: dict[str, int], findings: list[dict[str, Any]]
) -> dict[str, int]:
    current_high = {
        finding_fingerprint(f)
        for f in findings
        if str(f.get("severity", "")).upper() == "HIGH"
    }
    updated: dict[str, int] = {}
    for fingerprint in current_high:
        updated[fingerprint] = int(previous.get(fingerprint, 0)) + 1
    return updated


def severity_counts(findings: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for finding in findings:
        severity = str(finding.get("severity", "INFO")).upper()
        if severity == "PLANETARY":
            severity = "CRITICAL"
        if severity in counts:
            counts[severity] += 1
    return counts


def alert_decision(findings: list[dict[str, Any]], high_persistence: dict[str, int]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    for finding in findings:
        severity = str(finding.get("severity", "INFO")).upper()
        fingerprint = finding_fingerprint(finding)
        if severity in {"CRITICAL", "PLANETARY"}:
            reasons.append(f"{severity}: {finding.get('description', '')[:160]}")
        elif severity == "HIGH" and high_persistence.get(fingerprint, 0) >= 3:
            reasons.append(f"HIGH persisted {high_persistence[fingerprint]} cycles: {finding.get('description', '')[:160]}")
    return bool(reasons), reasons


def authorized_scan_mode(scan_mode: str) -> None:
    if scan_mode == "internal":
        return
    if os.getenv("ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK") != "YES":
        raise RuntimeError(
            "non-internal live scanning requires ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK=YES "
            "to confirm the selected sources/systems are authorized"
        )


def preflight(scan_mode: str) -> tuple[dict[str, Any], dict[str, Any]]:
    print("🧅 validating ZYRAPALANTIR live policy...", flush=True)
    validate_live_policy()
    print("✅ live policy valid", flush=True)

    if not defense_profile_active():
        raise RuntimeError("defensive profile is inactive; run `defense activate` first")
    print("🛡️  defensive profile ACTIVE", flush=True)

    authorized_scan_mode(scan_mode)
    print(f"🎯 authorized scan mode: {scan_mode}", flush=True)

    print("📦 probing Palantir Maven...", flush=True)
    maven_ok, maven = maven_probe()
    if not maven_ok:
        raise RuntimeError(f"Palantir Maven readiness failed: {maven}")
    print("✅ Palantir Maven reachable/authenticated", flush=True)

    print("🐼 running GPT-REDPANDA CPR...", flush=True)
    cpr_ok, cpr = redpanda_cpr()
    if not cpr_ok:
        raise RuntimeError(f"GPT-REDPANDA CPR failed: {cpr}")
    print("✅ GPT-REDPANDA CPR PASS", flush=True)
    return (
        maven if isinstance(maven, dict) else {"result": maven},
        cpr if isinstance(cpr, dict) else {"result": cpr},
    )


def render_cycle(snapshot: dict[str, Any]) -> None:
    counts = snapshot["severity_counts"]
    icon = "🟢" if not snapshot["needs_alert"] else "🚨"
    print("", flush=True)
    print(f"📡 LIVE CYCLE {snapshot['cycle']:04d}  {snapshot['timestamp']}", flush=True)
    print(f"🛡️  readiness: {snapshot['readiness']}", flush=True)
    print(f"🔎 scan mode: {snapshot['scan_mode']} | findings: {snapshot['finding_count']}", flush=True)
    print(
        f"📊 low={counts['LOW']}  medium={counts['MEDIUM']}  high={counts['HIGH']}  critical={counts['CRITICAL']}",
        flush=True,
    )
    if snapshot["maven_checked_this_cycle"]:
        print(f"📦 Maven: {'✅ PASS' if snapshot['maven_ok'] else '⚠️ DEGRADED'}", flush=True)
    if snapshot["cpr_checked_this_cycle"]:
        print(f"🐼 REDPANDA CPR: {'✅ PASS' if snapshot['cpr_ok'] else '⚠️ DEGRADED'}", flush=True)
    if snapshot["needs_alert"]:
        print("🚨 ANALYST ATTENTION REQUIRED", flush=True)
        for reason in snapshot["alert_reasons"]:
            print(f"   ↳ {reason}", flush=True)
    elif counts["HIGH"]:
        max_seen = max(snapshot.get("high_persistence", {}).values(), default=1)
        print(f"🟠 HIGH finding observed; persistence gate {max_seen}/3 before alert", flush=True)
    else:
        print(f"{icon} no analyst alert threshold met", flush=True)
    print("👤 external remediation: HUMAN APPROVAL REQUIRED", flush=True)
    print("⛔ automatic external action: false", flush=True)
    print(f"🧾 audit: {AUDIT_LOG}", flush=True)


def run_cycle(
    cycle: int,
    scan_mode: str,
    previous_state: dict[str, Any],
    maven_every: int,
    cpr_every: int,
) -> dict[str, Any]:
    findings = run_sentinel(scan_mode)
    high_persistence = update_high_persistence(previous_state.get("high_persistence", {}), findings)
    needs_alert, alert_reasons = alert_decision(findings, high_persistence)

    maven_ok = bool(previous_state.get("maven_ok", True))
    cpr_ok = bool(previous_state.get("cpr_ok", True))
    maven_checked = cycle == 1 or cycle % max(1, maven_every) == 0
    cpr_checked = cycle == 1 or cycle % max(1, cpr_every) == 0

    if maven_checked:
        maven_ok, _ = maven_probe()
    if cpr_checked:
        cpr_ok, _ = redpanda_cpr()

    readiness = "READY" if maven_ok and cpr_ok and defense_profile_active() else "DEGRADED"
    counts = severity_counts(findings)
    snapshot = {
        "schema": "xunia.zyrapalantir-live.v1",
        "running": True,
        "pid": os.getpid(),
        "cycle": cycle,
        "timestamp": utc_now(),
        "scan_mode": scan_mode,
        "defense_profile_active": defense_profile_active(),
        "readiness": readiness,
        "finding_count": len(findings),
        "severity_counts": counts,
        "highest_severity": highest_severity(findings),
        "high_persistence": high_persistence,
        "needs_alert": needs_alert,
        "alert_reasons": alert_reasons,
        "maven_ok": maven_ok,
        "maven_checked_this_cycle": maven_checked,
        "cpr_ok": cpr_ok,
        "cpr_checked_this_cycle": cpr_checked,
        "automatic_external_action_taken": False,
        "human_approval_required_for_external_action": True,
        "findings": findings[:25],
    }
    write_json_private(LIVE_STATE, snapshot)
    append_audit(snapshot)
    render_cycle(snapshot)
    return snapshot


def handle_stop(signum: int, frame: Any) -> None:  # noqa: ARG001
    global _STOP
    _STOP = True


def run_loop(args: argparse.Namespace) -> int:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    signal.signal(signal.SIGTERM, handle_stop)
    signal.signal(signal.SIGINT, handle_stop)

    print("🐼 ZYRAPALANTIR LIVE // DEFENSIVE MONITORING", flush=True)
    print("📡 local/authorized telemetry → correlation → analyst alerting", flush=True)
    print("⛔ no automatic external remediation; no artifact execution", flush=True)
    preflight(args.scan_mode)

    previous = load_json(LIVE_STATE, {}) or {}
    cycle = 0
    try:
        while not _STOP:
            cycle += 1
            previous = run_cycle(cycle, args.scan_mode, previous, args.maven_every, args.cpr_every)
            if args.once:
                break
            for _ in range(max(1, int(args.interval * 10))):
                if _STOP:
                    break
                time.sleep(0.1)
    finally:
        final_state = load_json(LIVE_STATE, {}) or {}
        final_state.update({"running": False, "stopped_at": utc_now(), "pid": os.getpid()})
        write_json_private(LIVE_STATE, final_state)
        append_audit(
            {
                "schema": "xunia.zyrapalantir-live.event.v1",
                "event": "STOP",
                "timestamp": utc_now(),
                "pid": os.getpid(),
            }
        )
        print("🛑 ZYRAPALANTIR LIVE stopped cleanly", flush=True)
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ZYRAPALANTIR live defensive monitor")
    parser.add_argument("--once", action="store_true", help="run one monitoring cycle and exit")
    parser.add_argument(
        "--interval",
        type=float,
        default=float(os.getenv("ZYRAPALANTIR_LIVE_INTERVAL", "60")),
        help="seconds between scan cycles (default: 60)",
    )
    parser.add_argument(
        "--scan-mode",
        choices=["internal", "external", "satellite", "darkweb", "full"],
        default=os.getenv("ZYRAPALANTIR_LIVE_SCAN_MODE", "internal"),
        help="monitoring source set; internal is the safe default",
    )
    parser.add_argument(
        "--maven-every",
        type=int,
        default=int(os.getenv("ZYRAPALANTIR_MAVEN_HEALTH_EVERY", "5")),
        help="re-check Maven every N cycles",
    )
    parser.add_argument(
        "--cpr-every",
        type=int,
        default=int(os.getenv("ZYRAPALANTIR_CPR_EVERY", "10")),
        help="re-run REDPANDA CPR every N cycles",
    )
    return parser.parse_args()


if __name__ == "__main__":
    raise SystemExit(run_loop(parse_args()))
