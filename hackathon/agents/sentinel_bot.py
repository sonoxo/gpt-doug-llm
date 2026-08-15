"""
Agent #1 — Zyra Sentinel Bot (Everyday Agents Track)

Autonomous home network security monitor. Runs silently, scans for
vulnerabilities, monitors IoT devices, and only surfaces when there's
a real threat requiring a human decision.

Free deployment options:
  - AWS Lambda free tier (1M req/month, 400K GB-sec)
  - GitHub Actions (free for public repos)
  - Local cron job (free, any machine)
  - Cloudflare Workers (100K req/day free)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

SYSTEM_PROMPT = """You are Zyra Sentinel Bot, an autonomous home network security monitor.

You run silently in the background. Your job:
1. Scan the home network for open ports, vulnerable services, misconfigured files
2. Monitor for known malware processes
3. Check DNS for poisoned domains
4. Verify SSL certificates aren't expiring
5. Scan dependencies for known CVEs
6. Check environment for leaked secrets
7. Monitor satellite/orbital feeds for infrastructure threats

You ONLY surface the user when:
- A CRITICAL finding is detected (malware, suspicious port, secret leak)
- A HIGH finding persists across 3 consecutive scans
- A satellite feed goes down (infrastructure monitoring degraded)

For everything else, you log silently and continue monitoring.
"""


def run_home_scan() -> dict:
    """Run a full home network security scan.
    
    Returns:
        Scan results with findings, severity breakdown, and alert decision
    """
    from golden_shield import ZyraSentinel
    
    sentinel = ZyraSentinel()
    report = sentinel.full_sweep()
    
    # Determine if we need to alert the user
    needs_alert = False
    alert_reasons = []
    
    for f in report.internal_findings:
        if f.severity == "CRITICAL":
            needs_alert = True
            alert_reasons.append(f"CRITICAL: {f.description}")
        elif f.severity == "HIGH":
            # Only alert on HIGH if it persists (simplified: alert on first)
            needs_alert = True
            alert_reasons.append(f"HIGH: {f.description}")
    
    for f in report.satellite_findings:
        if f.severity == "PLANETARY":
            needs_alert = True
            alert_reasons.append(f"PLANETARY: {f.description}")
    
    return {
        "scan_id": report.scan_id,
        "timestamp": report.completed_at,
        "total_findings": report.total_findings,
        "critical_count": report.critical_count,
        "planetary_count": report.planetary_count,
        "needs_alert": needs_alert,
        "alert_reasons": alert_reasons if needs_alert else [],
        "internal_findings": [
            {"severity": f.severity, "category": f.category, "target": f.target, "description": f.description, "recommendation": f.recommendation}
            for f in report.internal_findings[:10]
        ],
        "external_findings": [
            {"severity": f.severity, "cve_id": f.cve_id, "description": f.description[:100]}
            for f in report.external_findings[:5]
        ],
        "satellite_findings": [
            {"severity": f.severity, "category": f.category, "description": f.description[:100]}
            for f in report.satellite_findings[:3]
        ],
    }


def format_alert(scan_result: dict) -> str:
    """Format scan results as a user-facing alert (only if needs_alert)."""
    if not scan_result.get("needs_alert"):
        return "✅ Home network secure. No threats detected."
    
    lines = ["🚨 **ZYRA SENTINEL ALERT**\n"]
    for reason in scan_result.get("alert_reasons", []):
        lines.append(f"  • {reason}")
    lines.append(f"\nTotal findings: {scan_result['total_findings']}")
    lines.append(f"Critical: {scan_result['critical_count']}")
    if scan_result.get("planetary_count"):
        lines.append(f"Planetary: {scan_result['planetary_count']}")
    return "\n".join(lines)


if __name__ == "__main__":
    result = run_home_scan()
    print(format_alert(result))
    if result["needs_alert"]:
        print("\n--- Detailed Findings ---")
        print(json.dumps(result["internal_findings"][:5], indent=2))
