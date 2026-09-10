#!/usr/bin/env python3
"""ZYRAPALANTIR field-operations terminal console.

Read-only / decision-support oriented. It summarizes local ZYRAPALANTIR LIVE
state plus explicitly authorized JSON inputs. It does not control weapons,
select targets, issue fires, steer vehicles, or perform automatic external
actions.
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import platform
import socket
import subprocess
from datetime import datetime, timezone
from typing import Any

STATE_DIR = pathlib.Path.home() / ".config" / "gpt-doug"
DEFENSE_STATE = STATE_DIR / "defense-profile.json"
LIVE_STATE = STATE_DIR / "zyrapalantir-live-state.json"
LIVE_PID = STATE_DIR / "zyrapalantir-live.pid"
FIELD_STATE = STATE_DIR / "zyrapalantir-field-state.json"
FIELD_AUDIT = STATE_DIR / "zyrapalantir-field-audit.jsonl"

SEVERITY = {"SAFE": 0, "INFO": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4, "PLANETARY": 4}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: pathlib.Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_private(path: pathlib.Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    path.chmod(0o600)


def append_audit(payload: dict[str, Any]) -> None:
    FIELD_AUDIT.parent.mkdir(parents=True, exist_ok=True)
    with FIELD_AUDIT.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True) + "\n")
    FIELD_AUDIT.chmod(0o600)


def pid_running() -> tuple[bool, int | None]:
    try:
        pid = int(LIVE_PID.read_text(encoding="utf-8").strip())
    except Exception:
        return False, None
    try:
        os.kill(pid, 0)
        return True, pid
    except OSError:
        return False, pid


def load_authorized_data(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    if os.getenv("ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK") != "YES":
        raise SystemExit(
            "⛔ External field-data import requires ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK=YES "
            "to confirm you are authorized to use that data."
        )
    p = pathlib.Path(path).expanduser().resolve()
    payload = load_json(p)
    if not isinstance(payload, dict):
        raise SystemExit(f"❌ Authorized field-data file is not valid JSON: {p}")
    return payload


def run_readonly(argv: list[str], timeout: int = 5) -> str:
    try:
        proc = subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)
        if proc.returncode == 0:
            return (proc.stdout or "").strip()
    except Exception:
        pass
    return ""


def local_addresses() -> list[str]:
    out: set[str] = set()
    try:
        for item in socket.getaddrinfo(socket.gethostname(), None):
            addr = item[4][0]
            if addr:
                out.add(addr)
    except Exception:
        pass
    out.update({"127.0.0.1", "::1"})
    return sorted(out)


def default_route() -> str:
    if platform.system() == "Darwin":
        text = run_readonly(["route", "-n", "get", "default"])
        for line in text.splitlines():
            if "interface:" in line:
                return line.split("interface:", 1)[1].strip()
    else:
        text = run_readonly(["ip", "route", "show", "default"])
        if text:
            return text.splitlines()[0][:180]
    return "unknown"


def snapshot(data_path: str | None = None) -> dict[str, Any]:
    defense = load_json(DEFENSE_STATE, {}) or {}
    live = load_json(LIVE_STATE, {}) or {}
    running, live_pid = pid_running()
    imported = load_authorized_data(data_path)

    findings = live.get("findings", [])
    if not isinstance(findings, list):
        findings = []
    counts = live.get("severity_counts", {}) if isinstance(live, dict) else {}
    if not isinstance(counts, dict):
        counts = {}

    highest = str(live.get("highest_severity", "SAFE")).upper()
    readiness = str(live.get("readiness", "UNKNOWN")).upper()
    maven_ok = bool(live.get("maven_ok"))
    cpr_ok = bool(live.get("cpr_ok"))
    defense_active = bool(defense.get("active"))

    field_ready = bool(defense_active and running and readiness == "READY" and maven_ok and cpr_ok)
    analyst_attention = bool(live.get("needs_alert")) or SEVERITY.get(highest, 0) >= SEVERITY["HIGH"]

    return {
        "schema": "xunia.zyrapalantir-field.v1",
        "timestamp": utc_now(),
        "mode": "FIELD_DECISION_SUPPORT_ONLY",
        "field_ready": field_ready,
        "defense_profile_active": defense_active,
        "live_service_running": running,
        "live_pid": live_pid,
        "live_readiness": readiness,
        "maven_ok": maven_ok,
        "redpanda_cpr_ok": cpr_ok,
        "highest_severity": highest,
        "analyst_attention_required": analyst_attention,
        "automatic_external_action": False,
        "weapons_control": False,
        "targeting_control": False,
        "local_asset": {
            "hostname": socket.gethostname(),
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
        },
        "comms": {
            "local_addresses": local_addresses(),
            "default_route_interface": default_route(),
            "external_control": False,
        },
        "cyber": {
            "finding_count": len(findings),
            "severity_counts": {
                "LOW": int(counts.get("LOW", 0)),
                "MEDIUM": int(counts.get("MEDIUM", 0)),
                "HIGH": int(counts.get("HIGH", 0)),
                "CRITICAL": int(counts.get("CRITICAL", 0)),
            },
            "findings": findings[:25],
            "alert_reasons": live.get("alert_reasons", []),
        },
        "authorized_data": imported,
    }


def banner() -> None:
    print()
    print("🎖️  ===============================================================")
    print("🐼  ZYRAPALANTIR FIELD OPS // HUMAN-CONTROLLED DECISION SUPPORT")
    print("🛡️  CYBER • COMMS • READINESS • ASSETS • INTEL • INCIDENTS")
    print("🎖️  ===============================================================")


def show_status(s: dict[str, Any]) -> None:
    banner()
    print(f"🚦 FIELD READY ............ {'✅ YES' if s['field_ready'] else '⚠️ NO'}")
    print(f"🛡️  DEFENSE PROFILE ....... {'✅ ACTIVE' if s['defense_profile_active'] else '❌ INACTIVE'}")
    print(f"📡 LIVE MONITOR ........... {'🟢 RUNNING' if s['live_service_running'] else '⚫ STOPPED'}")
    print(f"📦 PALANTIR MAVEN ......... {'✅ PASS' if s['maven_ok'] else '⚠️ NOT READY'}")
    print(f"🐼 REDPANDA CPR ........... {'✅ PASS' if s['redpanda_cpr_ok'] else '⚠️ NOT READY'}")
    print(f"🚨 ANALYST ATTENTION ...... {'REQUIRED' if s['analyst_attention_required'] else 'NO'}")
    print("👤 EXTERNAL ACTION ........ HUMAN APPROVAL REQUIRED")
    print("⛔ AUTO EXTERNAL ACTION ... FALSE")
    print("🎯 TARGETING CONTROL ...... FALSE")
    print("🧨 WEAPONS CONTROL ........ FALSE")


def show_assets(s: dict[str, Any]) -> None:
    a = s["local_asset"]
    print("🧩 ASSETS")
    print(f"   💻 local host: {a['hostname']}")
    print(f"   🖥️  platform: {a['system']} {a['release']} ({a['machine']})")
    extra = s["authorized_data"].get("assets", [])
    print(f"   🔐 authorized imported assets: {len(extra) if isinstance(extra, list) else 0}")


def show_comms(s: dict[str, Any]) -> None:
    c = s["comms"]
    print("📶 COMMS")
    print(f"   🔌 default route/interface: {c['default_route_interface']}")
    print(f"   🧭 local addresses: {', '.join(c['local_addresses'][:6])}")
    extra = s["authorized_data"].get("comms", [])
    print(f"   🔐 authorized imported comms records: {len(extra) if isinstance(extra, list) else 0}")
    print("   ⛔ this console does not reconfigure or disrupt networks")


def show_intel(s: dict[str, Any]) -> None:
    cyber = s["cyber"]
    print("🧠 INTEL / CORRELATION")
    print(f"   📊 current defensive findings: {cyber['finding_count']}")
    print(f"   🚦 highest severity: {s['highest_severity']}")
    reports = s["authorized_data"].get("reports", [])
    print(f"   🗂️  authorized imported reports: {len(reports) if isinstance(reports, list) else 0}")
    for finding in cyber["findings"][:5]:
        sev = str(finding.get("severity", "INFO")).upper()
        print(f"   ↳ {sev}: {str(finding.get('description', ''))[:150]}")


def show_cyber(s: dict[str, Any]) -> None:
    counts = s["cyber"]["severity_counts"]
    print("🛡️  CYBER")
    print(
        f"   🟡 LOW={counts['LOW']}  🟠 MEDIUM={counts['MEDIUM']}  "
        f"🔴 HIGH={counts['HIGH']}  🚨 CRITICAL={counts['CRITICAL']}"
    )
    print(f"   📦 Maven: {'PASS' if s['maven_ok'] else 'NOT READY'}")
    print(f"   🐼 REDPANDA CPR: {'PASS' if s['redpanda_cpr_ok'] else 'NOT READY'}")


def show_incidents(s: dict[str, Any]) -> None:
    cyber = s["cyber"]
    reasons = cyber.get("alert_reasons", [])
    print("🚨 INCIDENTS")
    if s["analyst_attention_required"]:
        print("   🔴 analyst review required")
        if isinstance(reasons, list):
            for reason in reasons[:5]:
                print(f"   ↳ {reason}")
    else:
        print("   🟢 no current HIGH/CRITICAL analyst threshold")
    imported = s["authorized_data"].get("incidents", [])
    print(f"   📁 authorized imported incidents: {len(imported) if isinstance(imported, list) else 0}")
    print("   👤 response remains human-authorized")


def show_readiness(s: dict[str, Any]) -> None:
    print("📋 READINESS")
    print(f"   🛡️ defense profile: {'PASS' if s['defense_profile_active'] else 'FAIL'}")
    print(f"   📡 live telemetry: {'PASS' if s['live_service_running'] else 'FAIL'}")
    print(f"   📦 Maven supply-chain gate: {'PASS' if s['maven_ok'] else 'FAIL'}")
    print(f"   🐼 REDPANDA CPR: {'PASS' if s['redpanda_cpr_ok'] else 'FAIL'}")
    print(f"   🚦 field console: {'READY' if s['field_ready'] else 'DEGRADED/PENDING'}")
    print("   ⚠️ engineering readiness only — not certification/ATO")


def show_simulation() -> None:
    print("🧪 FIELD SIMULATION // SYNTHETIC TRAINING ONLY")
    print("   📡 simulated comms link ........ 🟠 DEGRADED")
    print("   🛡️ simulated endpoint alert ... 🔴 HIGH")
    print("   📦 trusted artifact ............ ✅ VERIFIED")
    print("   👤 analyst approval ............ REQUIRED")
    print("   ⛔ automatic external action ... FALSE")
    print("   🎯 targeting/weapons control ... DISABLED")


def show_all(s: dict[str, Any]) -> None:
    show_status(s)
    print()
    show_assets(s)
    print()
    show_comms(s)
    print()
    show_intel(s)
    print()
    show_cyber(s)
    print()
    show_incidents(s)
    print()
    show_readiness(s)


def main() -> int:
    parser = argparse.ArgumentParser(prog="zyrapalantir field")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["status", "assets", "comms", "intel", "cyber", "incidents", "readiness", "simulate", "all"],
        default="status",
    )
    parser.add_argument(
        "--data",
        default=os.getenv("ZYRAPALANTIR_FIELD_DATA", ""),
        help="optional authorized local JSON data file; requires ZYRAPALANTIR_AUTHORIZED_SCOPE_ACK=YES",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable snapshot")
    args = parser.parse_args()

    if args.command == "simulate":
        show_simulation()
        return 0

    s = snapshot(args.data or None)
    write_private(FIELD_STATE, s)
    append_audit(
        {
            "schema": "xunia.zyrapalantir-field.event.v1",
            "timestamp": utc_now(),
            "command": args.command,
            "field_ready": s["field_ready"],
            "highest_severity": s["highest_severity"],
            "automatic_external_action": False,
            "weapons_control": False,
            "targeting_control": False,
        }
    )

    if args.json:
        print(json.dumps(s, indent=2))
        return 0

    dispatch = {
        "status": show_status,
        "assets": show_assets,
        "comms": show_comms,
        "intel": show_intel,
        "cyber": show_cyber,
        "incidents": show_incidents,
        "readiness": show_readiness,
        "all": show_all,
    }
    dispatch[args.command](s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
