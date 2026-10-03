#!/usr/bin/env python3
"""ZYRAPALANTIR synthetic intelligence demo.

Reads a training-only scenario, correlates defensive evidence, and emits an
analyst-facing mission assurance summary. It performs no external action.
"""

from __future__ import annotations

import json
import pathlib
import statistics
import sys
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCENARIO_PATH = ROOT / "demo" / "zyrapalantir-intel-scenario.json"
ONTOLOGY_PATH = ROOT / "safety-shield" / "ontology" / "zyrapalantir-intel-demo.json"
STATE_PATH = pathlib.Path.home() / ".config" / "gpt-doug" / "defense-profile.json"
AUDIT_PATH = pathlib.Path.home() / ".config" / "gpt-doug" / "zyrapalantir-intel-demo-last.json"


def load_json(path: pathlib.Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    print(f"❌ {message}", file=sys.stderr)
    raise SystemExit(1)


def validate_synthetic(scenario: dict, ontology: dict) -> None:
    if scenario.get("classification") != "SYNTHETIC//UNCLASSIFIED":
        fail("intel demo refused: scenario is not SYNTHETIC//UNCLASSIFIED")
    if ontology.get("mode") != "DEFENSIVE_INTELLIGENCE_DEMO_ONLY":
        fail("intel demo refused: ontology is not defensive demo mode")
    policy = ontology.get("decisionPolicy", {})
    if policy.get("syntheticDataOnly") is not True or policy.get("automaticExternalAction") is not False:
        fail("intel demo refused: safe decision policy is not enforced")
    for indicator in scenario.get("indicators", []):
        if indicator.get("synthetic") is not True:
            fail(f"intel demo refused: non-synthetic indicator {indicator.get('id')}")


def defense_active() -> bool:
    if not STATE_PATH.exists():
        return False
    try:
        return bool(load_json(STATE_PATH).get("active"))
    except Exception:
        return False


def correlate(scenario: dict) -> dict:
    reports = scenario.get("intel_reports", [])
    findings = scenario.get("findings", [])
    assets = {item["id"]: item for item in scenario.get("assets", [])}
    systems = {item["id"]: item for item in scenario.get("mission_systems", [])}

    indicator_sources: dict[str, set[str]] = {}
    confidences = []
    for report in reports:
        confidences.append(float(report.get("confidence", 0)))
        for indicator_id in report.get("indicator_ids", []):
            indicator_sources.setdefault(indicator_id, set()).add(report.get("source", "unknown"))

    corroborated = sorted(k for k, sources in indicator_sources.items() if len(sources) >= 2)
    avg_conf = statistics.fmean(confidences) if confidences else 0.0

    mission = scenario["mission"]
    system = systems[mission["system"]]
    asset = assets[system["asset_id"]]
    severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    max_severity = max((severity_rank.get(f.get("severity", "LOW"), 1) for f in findings), default=1)
    severity_name = {1: "LOW", 2: "MEDIUM", 3: "HIGH", 4: "CRITICAL"}[max_severity]

    evidence_score = min(100, round(avg_conf * 70 + min(len(corroborated), 2) * 15))
    assessment = "REVIEW_REQUIRED" if max_severity >= 3 and corroborated else "MONITOR"

    return {
        "schema": "xunia.zyrapalantir.intel-demo.v1",
        "classification": scenario["classification"],
        "scenario": scenario["scenario"],
        "defense_profile_active": defense_active(),
        "mission": {
            "id": mission["id"],
            "name": mission["name"],
            "priority": mission["priority"],
            "system": system["name"],
            "system_status": system["status"],
            "affected_asset": asset["hostname"],
        },
        "correlation": {
            "intel_reports": len(reports),
            "independent_sources": len({r.get("source") for r in reports}),
            "corroborated_indicators": corroborated,
            "average_source_confidence": round(avg_conf, 3),
            "evidence_score": evidence_score,
            "highest_finding_severity": severity_name,
        },
        "assessment": assessment,
        "artifact_provenance_required": True,
        "recommended_actions": scenario.get("approved_recommendations", []),
        "automatic_external_action_taken": False,
        "analyst_approval_required": True,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def severity_emoji(severity: str) -> str:
    return {
        "LOW": "🟢",
        "MEDIUM": "🟡",
        "HIGH": "🟠",
        "CRITICAL": "🔴",
    }.get(severity, "⚪")


def print_human(result: dict) -> None:
    mission = result["mission"]
    corr = result["correlation"]
    active_icon = "🟢" if result["defense_profile_active"] else "🔴"
    sev_icon = severity_emoji(corr["highest_finding_severity"])
    assessment_icon = "👀" if result["assessment"] == "REVIEW_REQUIRED" else "📡"

    print("\n🛰️  ============================================================")
    print("🐼  ZYRAPALANTIR // SYNTHETIC INTELLIGENCE FUSION")
    print("🧪  EXERCISE LANTERN SHIELD — SYNTHETIC//UNCLASSIFIED")
    print("🛰️  ============================================================")
    print(f"🎯 Mission:          {mission['name']}")
    print(f"🖥️  Mission system:   {mission['system']} ({mission['system_status']})")
    print(f"💻 Affected asset:   {mission['affected_asset']}")
    print(f"{active_icon} Defense profile:  {'ACTIVE' if result['defense_profile_active'] else 'INACTIVE'}")

    print("\n🔎 INTELLIGENCE CORRELATION")
    print(f"  📄 Reports:             {corr['intel_reports']}")
    print(f"  📡 Independent sources: {corr['independent_sources']}")
    print(f"  🔗 Corroborated IOCs:   {len(corr['corroborated_indicators'])}")
    print(f"  📊 Evidence score:      {corr['evidence_score']}/100")
    print(f"  {sev_icon} Highest severity:    {corr['highest_finding_severity']}")
    print(f"  {assessment_icon} Assessment:          {result['assessment']}")

    print("\n💡 ANALYST DECISION SUPPORT")
    for idx, action in enumerate(result["recommended_actions"], start=1):
        print(f"  {idx}. 🧭 {action}")

    print("\n🛡️  CONTROL STATUS")
    print("  🧪 ✅ Synthetic data only")
    print("  🔎 ✅ Evidence sources correlated")
    print("  📦 ✅ Maven provenance required")
    print("  👤 ✅ Human analyst approval required")
    print("  ⛔ ✅ Automatic external action taken: false")
    print("  🔒 ✅ No classified/operational data used")


def main() -> int:
    scenario = load_json(SCENARIO_PATH)
    ontology = load_json(ONTOLOGY_PATH)
    validate_synthetic(scenario, ontology)
    result = correlate(scenario)

    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    AUDIT_PATH.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    AUDIT_PATH.chmod(0o600)

    if "--json" in sys.argv:
        print(json.dumps(result, indent=2))
    else:
        print_human(result)
        print(f"\n🧾 Audit record: {AUDIT_PATH}")
        print("🎉 ✅ ZYRAPALANTIR INTEL CORRELATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
