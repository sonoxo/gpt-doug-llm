"""Deterministic local analyzer for the public QTFY cybersecurity advisory.

This module does not use network access or autonomous shell execution. It reads the
repository's normalized advisory JSON and writes a source-page-preserving defensive
analysis suitable for human review and ontology workflows.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("intel/qtfy/JCSA-20260826-01.json")
DEFAULT_OUTPUT = Path("intel/qtfy/qtfy-analysis.md")


def _page(value: Any) -> str:
    return f"p. {value}" if value not in (None, "") else "page not recorded"


def _event_key(event: dict[str, Any]) -> tuple[int, int, str]:
    raw = str(event.get("date") or "")
    parts = raw.split("-")
    try:
        year = int(parts[0])
    except (ValueError, IndexError):
        year = 9999
    try:
        month = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        month = 0
    return year, month, raw


def build_analysis(data: dict[str, Any]) -> str:
    advisory_id = str(data.get("advisoryId") or "unknown")
    title = str(data.get("title") or "Untitled advisory")
    source_url = str(data.get("sourceUrl") or "")
    agencies = ", ".join(data.get("authoringAgencies") or [])
    threat = data.get("threatProfile") or {}
    organizations = data.get("organizations") or []
    tools = data.get("tools") or []
    vulns = data.get("vulnerabilities") or []
    events = sorted(data.get("campaignEvents") or [], key=_event_key)
    techniques = data.get("attackTechniques") or []
    actions = data.get("keyDefensiveActions") or []
    feeds = data.get("iocFeeds") or []
    policy = data.get("iocPolicy") or {}

    tool_by_id = {str(item.get("id")): item for item in tools}
    vuln_by_id = {str(item.get("id")): item for item in vulns}

    lines: list[str] = []
    lines.append(f"# QTFY Defensive Intelligence Analysis — {advisory_id}")
    lines.append("")
    lines.append(f"**Source:** {title}")
    lines.append(f"**Published:** {data.get('published', 'unknown')}  ")
    lines.append(f"**Authoring agencies:** {agencies or 'not recorded'}  ")
    lines.append(f"**TLP:** {data.get('tlp', 'unknown')}  ")
    lines.append(f"**Source URL:** {source_url}  ")
    lines.append(f"**Use policy:** {data.get('usePolicy', 'DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY')}")
    lines.append("")
    lines.append("> This report preserves the advisory's attribution. Mention in the source is not independent proof of guilt, ownership, or control. Indicators are defensive investigative leads, not automatic authorization to act against third-party systems.")
    lines.append("")

    lines.append("## 1. Source-grounded threat picture")
    lines.append("")
    lines.append(f"- **Threat label:** {threat.get('id', 'QTFY')}")
    aliases = threat.get("aliases") or []
    if aliases:
        lines.append(f"- **Aliases in normalized source:** {', '.join(map(str, aliases))}")
    if threat.get("attribution"):
        lines.append(f"- **Advisory attribution:** {threat['attribution']}")
    lines.append(f"- **Disposition:** {threat.get('disposition', 'MONITOR_AND_DEFEND')}")
    lines.append("")

    lines.append("## 2. Chronological campaign timeline")
    lines.append("")
    for event in events:
        refs: list[str] = []
        for tool_id in event.get("toolIds") or []:
            tool = tool_by_id.get(str(tool_id), {})
            refs.append(f"tool={tool.get('name', tool_id)}")
        for vuln_id in event.get("vulnerabilityIds") or []:
            vuln = vuln_by_id.get(str(vuln_id), {})
            context = vuln.get("context")
            refs.append(f"{vuln_id}{' (' + str(context) + ')' if context else ''}")
        suffix = f" — {'; '.join(refs)}" if refs else ""
        lines.append(
            f"- **{event.get('date', 'unknown')}** — {event.get('targetCategory', 'unspecified target')}: "
            f"{event.get('activity', 'activity not recorded')}; outcome: {event.get('outcome', 'not recorded')}"
            f"{suffix}. **Source {_page(event.get('sourcePage'))}.**"
        )
    lines.append("")

    lines.append("## 3. Organization → tool → CVE → event relationship map")
    lines.append("")
    lines.append("### Organizations named by the advisory")
    for org in organizations:
        lines.append(
            f"- **{org.get('name', org.get('id', 'unknown'))}** — role: `{org.get('role', 'UNSPECIFIED')}`; "
            f"**source {_page(org.get('sourcePage'))}.**"
        )
    lines.append("")
    lines.append("### Tools and platforms")
    for tool in tools:
        event_ids = [str(e.get("id")) for e in events if str(tool.get("id")) in [str(x) for x in e.get("toolIds") or []]]
        used = ", ".join(event_ids) if event_ids else "no specific normalized event linkage recorded"
        lines.append(
            f"- **{tool.get('name', tool.get('id', 'unknown'))}** — `{tool.get('category', 'UNSPECIFIED')}`; "
            f"linked events: {used}; **source {_page(tool.get('sourcePage'))}.**"
        )
    lines.append("")
    lines.append("### Vulnerabilities")
    for vuln in vulns:
        event_ids = [str(e.get("id")) for e in events if str(vuln.get("id")) in [str(x) for x in e.get("vulnerabilityIds") or []]]
        used = ", ".join(event_ids) if event_ids else "not tied to a normalized event in this source pack"
        lines.append(
            f"- **{vuln.get('id', 'unknown')}** — {vuln.get('context', 'context not recorded')}; "
            f"linked events: {used}; **source {_page(vuln.get('sourcePage'))}.**"
        )
    lines.append("")

    lines.append("## 4. MITRE ATT&CK mapping")
    lines.append("")
    for technique in techniques:
        lines.append(f"- **{technique.get('id', 'unknown')}** — {technique.get('name', 'name not recorded')}")
    lines.append("")

    lines.append("## 5. Recurring infrastructure and capability patterns")
    lines.append("")
    patterns = [
        "Repeated scanning and exploitation of internet-facing edge systems and remote-access products.",
        "Use of distributed scanning/exploitation capability (QScan) in normalized events spanning critical-infrastructure and government targets.",
        "Use of traffic-obfuscation, proxy, and botnet-management components in the advisory's described ecosystem.",
        "Repeated exploitation of known and newly disclosed vulnerabilities across multiple years, suggesting a durable vulnerability-exploitation workflow rather than a single campaign.",
        "A recurring emphasis on edge infrastructure means patch state, internet exposure, segmentation, and high-quality telemetry are central defensive control points.",
    ]
    for item in patterns:
        lines.append(f"- {item}")
    lines.append("")

    lines.append("## 6. Confirmed source statements vs. analytic inferences")
    lines.append("")
    lines.append("### Confirmed within the normalized public advisory source")
    lines.append(f"- {agencies or 'The authoring agencies'} published {advisory_id} and the normalized source records it as {data.get('tlp', 'TLP:CLEAR')}.")
    lines.append(f"- The advisory names {len(organizations)} organizations/entities, {len(tools)} tools/platforms, {len(vulns)} vulnerabilities, and {len(events)} campaign events in this normalized source pack.")
    lines.append("- The advisory recommends patching, reducing exposed information, segmenting critical systems, hunting published indicators, and performing evidence-preserving incident response when compromise is suspected.")
    lines.append("")
    lines.append("### Analytic inferences (not independent attribution findings)")
    lines.append("- The normalized timeline indicates persistent interest in exploitable perimeter technologies across many years.")
    lines.append("- QScan-linked events suggest distributed scanning/exploitation is operationally important within the activity described by the advisory.")
    lines.append("- The combination of scanning, exploitation, proxy/obfuscation, and botnet-management tooling is consistent with a scalable infrastructure model; this is an analytic interpretation of the source, not a new attribution claim.")
    lines.append("")

    lines.append("## 7. Evidence gaps requiring human review")
    lines.append("")
    gaps = [
        "The normalized source pack does not include full raw telemetry, packet captures, forensic images, or victim-side logs needed to independently validate each event.",
        "Organization-to-event relationships are not modeled unless explicitly present in the normalized data; do not infer direct responsibility from co-mention in the advisory.",
        "Several vulnerabilities are listed without a one-to-one normalized campaign-event relationship.",
        "IOC feeds are referenced but not embedded here; any indicator match requires contextual validation and human review.",
        "This report does not independently verify the source agencies' attribution judgments.",
    ]
    for gap in gaps:
        lines.append(f"- {gap}")
    lines.append("")

    lines.append("## 8. Prioritized defensive checklist for authorized environments")
    lines.append("")
    for index, action in enumerate(actions, start=1):
        lines.append(f"{index}. {action}")
    if feeds:
        lines.append(f"{len(actions) + 1}. Review the published IOC feeds as investigative leads and correlate them against authorized telemetry before taking action.")
    lines.append("")
    lines.append(f"**IOC default policy:** `{policy.get('defaultAction', 'INVESTIGATE_AND_VET')}`; automatic blocking: `{policy.get('automaticBlocking', False)}`; human review required: `{policy.get('humanReviewRequired', True)}`.")
    lines.append("")

    lines.append("## 9. Source feeds")
    lines.append("")
    for feed in feeds:
        lines.append(f"- {feed}")
    lines.append("")
    lines.append("---")
    lines.append("Generated locally from the repository's normalized public advisory JSON. No external systems were accessed by this analyzer.")
    lines.append("")
    return "\n".join(lines)


def analyze(source: Path = DEFAULT_SOURCE, output: Path = DEFAULT_OUTPUT) -> Path:
    data = json.loads(source.read_text(encoding="utf-8"))
    report = build_analysis(data)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(report, encoding="utf-8")
    return output


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the local QTFY defensive intelligence analysis")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    path = analyze(args.source, args.output)
    print(f"QTFY analysis written: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
