#!/usr/bin/env python3
"""GPT-GLASSONION cross-source provenance layer.

Glass Onion is a defensive public-source correlation overlay. It verifies the
existing QTFY MASTER LOCK, ingests a separately sourced DOJ disruption pack,
creates only source-grounded cross-links, and seals the overlay with its own
hash manifest. It does not scan, target, authenticate to, or modify external
systems.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_SOURCE = Path("intel/glassonion/DOJ-26-972.json")
BASE_SOURCE = Path("intel/qtfy/JCSA-20260826-01.json")
BASE_ONTOLOGY = Path("intel/qtfy/qtfy-ontology-runtime.json")
BASE_ANALYSIS = Path("intel/qtfy/qtfy-analysis.md")
BASE_LOCK = Path("intel/qtfy/master-lock.json")
DEFAULT_OVERLAY = Path("intel/glassonion/glassonion-overlay.json")
DEFAULT_BRIEF = Path("intel/glassonion/glassonion-brief.md")
DEFAULT_LOCK = Path("intel/glassonion/glassonion-lock.json")


class GlassOnionError(RuntimeError):
    """Raised when Glass Onion cannot prove its source or lock state."""


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise GlassOnionError(message)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise GlassOnionError(f"cannot read JSON {path}: {exc}") from exc
    _require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def _verify_base_master_lock(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    manifest = _read_json(root / BASE_LOCK)
    _require(manifest.get("locked") is True, "base QTFY MASTER LOCK is not locked")
    _require(manifest.get("publicationState") == "LOCKED_AND_PUBLISHABLE", "base QTFY package is not publishable")

    expected = manifest.get("hashes") or {}
    paths = {
        "sourceSha256": root / BASE_SOURCE,
        "ontologySha256": root / BASE_ONTOLOGY,
        "analysisSha256": root / BASE_ANALYSIS,
    }
    for key, path in paths.items():
        _require(path.is_file(), f"base locked artifact missing: {path.relative_to(root)}")
        actual = _sha256_bytes(path.read_bytes())
        _require(actual == expected.get(key), f"base MASTER LOCK hash mismatch: {path.relative_to(root)}")

    ontology = _read_json(root / BASE_ONTOLOGY)
    return manifest, ontology


def _validate_source(source: dict[str, Any]) -> None:
    required = {
        "sourceId",
        "title",
        "published",
        "sourceUrl",
        "sourceClass",
        "pressReleaseNumber",
        "claimPolicy",
        "crossSourceBase",
        "coreFacts",
        "organizations",
        "infrastructure",
        "disruptionEvents",
        "guardrails",
    }
    missing = sorted(required - set(source))
    _require(not missing, f"Glass Onion source pack missing fields: {', '.join(missing)}")
    _require(source["sourceId"] == "DOJ-26-972", "unexpected DOJ source id")
    _require(source["crossSourceBase"] == "JCSA-20260826-01", "unexpected cross-source base")
    _require(str(source["sourceUrl"]).startswith("https://www.justice.gov/"), "source must remain an official justice.gov URL")
    guardrails = source.get("guardrails") or {}
    _require(guardrails.get("automaticBlocking") is False, "automatic blocking must remain disabled")
    _require(guardrails.get("externalThirdPartyAction") is False, "external third-party action must remain disabled")
    _require(guardrails.get("offensiveReplication") is False, "offensive replication must remain disabled")
    _require(guardrails.get("humanReviewRequired") is True, "human review must remain required")


def _object(object_type: str, object_id: str, **properties: Any) -> dict[str, Any]:
    return {"objectType": object_type, "id": object_id, "properties": properties}


def _link(link_type: str, source: str, target: str, **properties: Any) -> dict[str, Any]:
    value: dict[str, Any] = {"linkType": link_type, "from": source, "to": target}
    if properties:
        value["properties"] = properties
    return value


def _base_refs(base_ontology: dict[str, Any]) -> set[str]:
    return {
        f"{item.get('objectType')}:{item.get('id')}"
        for item in (base_ontology.get("objects") or [])
        if item.get("objectType") and item.get("id")
    }


def build_overlay(source: dict[str, Any], base_ontology: dict[str, Any], base_lock_id: str) -> dict[str, Any]:
    """Build a separately sourced overlay that may point into the locked base graph."""
    _validate_source(source)
    refs = _base_refs(base_ontology)
    required_base_refs = {
        "CyberAdvisory:JCSA-20260826-01",
        "ThreatProfile:QTFY",
        "ThreatTool:qscan",
        "ThreatTool:qtrouter",
        "Organization:nanjing-xinjiuwei",
    }
    missing = sorted(required_base_refs - refs)
    _require(not missing, f"base ontology missing Glass Onion anchors: {', '.join(missing)}")

    source_ref = f"PublicSource:{source['sourceId']}"
    objects: list[dict[str, Any]] = [
        _object(
            "PublicSource",
            source["sourceId"],
            title=source["title"],
            sourceUrl=source["sourceUrl"],
            published=source["published"],
            sourceClass=source["sourceClass"],
            pressReleaseNumber=source["pressReleaseNumber"],
            reviewState="VERIFIED_PUBLIC_SOURCE",
        )
    ]
    links: list[dict[str, Any]] = [
        _link(
            "SourceCrossReferencesAdvisory",
            source_ref,
            "CyberAdvisory:JCSA-20260826-01",
            claimNature="DOJ_PRESS_RELEASE_REPORTING",
            sourceLines="76",
        ),
        _link(
            "SourceDescribesThreat",
            source_ref,
            "ThreatProfile:QTFY",
            claimNature="DOJ_SUMMARY_OF_COURT_DOCUMENTS",
            sourceLines="62",
        ),
        _link("SourceDescribesTool", source_ref, "ThreatTool:qscan", sourceLines="61,71"),
        _link("SourceDescribesTool", source_ref, "ThreatTool:qtrouter", sourceLines="61,72"),
    ]

    for fact in source.get("coreFacts") or []:
        fact_id = str(fact["id"])
        ref = f"EvidenceFact:{fact_id}"
        objects.append(
            _object(
                "EvidenceFact",
                fact_id,
                statement=fact["statement"],
                claimNature=fact["claimNature"],
                sourceLines=fact["sourceLines"],
            )
        )
        links.append(_link("SourceSupportsFact", source_ref, ref, sourceLines=fact["sourceLines"]))

    organization_refs: dict[str, str] = {}
    for organization in source.get("organizations") or []:
        organization_id = str(organization["id"])
        ref = f"Organization:{organization_id}"
        organization_refs[organization_id] = ref
        if ref not in refs:
            objects.append(
                _object(
                    "Organization",
                    organization_id,
                    name=organization["name"],
                    role=organization["role"],
                    claimNature=organization["claimNature"],
                    sourceLines=organization["sourceLines"],
                )
            )
        links.append(
            _link(
                "SourceMentionsOrganization",
                source_ref,
                ref,
                role=organization["role"],
                claimNature=organization["claimNature"],
                sourceLines=organization["sourceLines"],
            )
        )

    infrastructure_refs: dict[str, str] = {}
    for component in source.get("infrastructure") or []:
        component_id = str(component["id"])
        ref = f"InfrastructureComponent:{component_id}"
        infrastructure_refs[component_id] = ref
        objects.append(
            _object(
                "InfrastructureComponent",
                component_id,
                name=component["name"],
                role=component["role"],
                sourceLines=component["sourceLines"],
                handling="DEFENSIVE_CONTEXT_ONLY",
            )
        )
        links.append(_link("SourceDescribesInfrastructure", source_ref, ref, sourceLines=component["sourceLines"]))

    disruption_refs: list[str] = []
    for event in source.get("disruptionEvents") or []:
        event_id = str(event["id"])
        ref = f"LegalDisruptionAction:{event_id}"
        disruption_refs.append(ref)
        objects.append(
            _object(
                "LegalDisruptionAction",
                event_id,
                date=event["date"],
                action=event["action"],
                objective=event["objective"],
                reportedOutcome=event["reportedOutcome"],
                claimNature=event["claimNature"],
                sourceLines=event["sourceLines"],
            )
        )
        links.append(_link("SourceDescribesDisruption", source_ref, ref, sourceLines=event["sourceLines"]))
        links.append(_link("DisruptionTargetsTool", ref, "ThreatTool:qscan", sourceLines=event["sourceLines"]))
        links.append(_link("DisruptionTargetsTool", ref, "ThreatTool:qtrouter", sourceLines=event["sourceLines"]))

    for event in source.get("historicalDisruptions") or []:
        event_id = str(event["id"])
        ref = f"HistoricalDisruption:{event_id}"
        objects.append(
            _object(
                "HistoricalDisruption",
                event_id,
                date=event["date"],
                description=event["description"],
                sourceLines=event["sourceLines"],
                relationToQTFY="CONTEXTUAL_PRECEDENT_ONLY",
            )
        )
        links.append(_link("SourceMentionsHistoricalDisruption", source_ref, ref, sourceLines=event["sourceLines"]))

    # Source-grounded relationship layer. These edges preserve the nature of the
    # DOJ/court-document claim instead of converting allegations into independent facts.
    links.extend(
        [
            _link(
                "ThreatReportedEmployedBy",
                "ThreatProfile:QTFY",
                "Organization:nanjing-xinjiuwei",
                claimNature="DOJ_SUMMARY_OF_COURT_DOCUMENTS",
                sourceLines="62",
            ),
            _link(
                "ThreatReportedServiceCustomer",
                "ThreatProfile:QTFY",
                organization_refs["prc-mss"],
                claimNature="DOJ_SUMMARY_OF_COURT_DOCUMENTS",
                sourceLines="71",
            ),
            _link(
                "ThreatReportedServiceCustomer",
                "ThreatProfile:QTFY",
                organization_refs["pla"],
                claimNature="DOJ_SUMMARY_OF_COURT_DOCUMENTS",
                sourceLines="71",
            ),
            _link("ToolCompromisesInfrastructure", "ThreatTool:qscan", infrastructure_refs["compromised-iot-devices"], sourceLines="71"),
            _link("ToolFeedsTool", "ThreatTool:qscan", "ThreatTool:qtrouter", sourceLines="71"),
            _link("ToolUsesInfrastructure", "ThreatTool:qtrouter", infrastructure_refs["compromised-iot-devices"], sourceLines="72"),
            _link("ToolUsesInfrastructure", "ThreatTool:qtrouter", infrastructure_refs["commercial-proxy-devices"], sourceLines="72"),
            _link("ToolUsesInfrastructure", "ThreatTool:qtrouter", infrastructure_refs["leased-vps"], sourceLines="72"),
            _link("ToolDependsOnInfrastructure", "ThreatTool:qscan", infrastructure_refs["hardcoded-platform-domains"], sourceLines="73"),
            _link("ToolDependsOnInfrastructure", "ThreatTool:qtrouter", infrastructure_refs["hardcoded-platform-domains"], sourceLines="73"),
        ]
    )

    for disruption_ref in disruption_refs:
        links.append(_link("DisruptionSeizesDependency", disruption_ref, infrastructure_refs["hardcoded-platform-domains"], sourceLines="73"))
        links.append(_link("DisruptionReportedDisablesTool", disruption_ref, "ThreatTool:qscan", sourceLines="73"))
        links.append(_link("DisruptionReportedDisablesTool", disruption_ref, "ThreatTool:qtrouter", sourceLines="73"))

    victim_ids = ["nasa", "federal-reserve", "us-doe", "us-doj", "hhs", "nih", "us-senate"]
    for victim_id in victim_ids:
        links.append(
            _link(
                "SourceReportsVictimOrganization",
                source_ref,
                organization_refs[victim_id],
                claimNature="DOJ_PRESS_RELEASE_REPORTING",
                sourceLines="62-63",
            )
        )

    return {
        "name": "GPT-GLASSONION Cross-Source QTFY Overlay",
        "version": "1.0.0",
        "mode": "DEFENSIVE_PUBLIC_SOURCE_CORRELATION_ONLY",
        "baseMasterLockId": base_lock_id,
        "baseAdvisory": "JCSA-20260826-01",
        "overlaySource": source["sourceId"],
        "objectTypes": sorted({item["objectType"] for item in objects}),
        "linkTypes": sorted({item["linkType"] for item in links}),
        "objects": objects,
        "links": links,
        "guardrails": {
            "baseOntologyImmutable": True,
            "automaticBlocking": False,
            "externalThirdPartyAction": False,
            "offensiveReplication": False,
            "humanReviewRequired": True,
            "attributionHandling": "PRESERVE_SOURCE_CLAIM_NATURE",
            "crossSourceRule": "CORRELATE_WITHOUT_UPGRADING_CLAIMS_TO_INDEPENDENT_FACTS",
        },
    }


def build_brief(source: dict[str, Any], overlay: dict[str, Any]) -> str:
    victims = [item["name"] for item in source.get("organizations") or [] if "VICTIM" in str(item.get("role"))]
    return "\n".join(
        [
            "# GPT-GLASSONION // DOJ 26-972 Cross-Source Brief",
            "",
            f"Source: {source['sourceUrl']}",
            f"Published: {source['published']} | Press release: {source['pressReleaseNumber']}",
            f"Base ontology lock: {overlay['baseMasterLockId']}",
            "",
            "## Layer 1 — Legal disruption",
            "DOJ reports that court-authorized domain seizures on 2026-08-26 denied access to QScan and QTRouter. DOJ states the seized domains were hard-coded communication/authentication dependencies and that the seizures made both platforms inoperable. [DOJ source lines 61,73]",
            "",
            "## Layer 2 — Operator and service relationships",
            "DOJ summarizes court documents as describing QTFY as employed by Nanjing Xinjiuwei Network Technology Company, as creator/operator of QScan and QTRouter, and as offering services to paying customers including the PRC Ministry of State Security and People's Liberation Army. These remain source claims, not independent Glass Onion attribution. [DOJ source lines 62,71]",
            "",
            "## Layer 3 — Platform architecture",
            "The source describes QScan as scanning/infecting IoT devices and feeding them into QTRouter. QTRouter is described as combining compromised IoT devices, commercial proxy devices, and leased VPS infrastructure into an obfuscation network. Glass Onion records this architecture for defensive exposure and telemetry reasoning only. [DOJ source lines 71-72]",
            "",
            "## Layer 4 — Reported victim context",
            "DOJ identifies the following among victims of QTFY intrusion activity: " + ", ".join(victims) + ". [DOJ source lines 62-63]",
            "",
            "## Layer 5 — Cross-source correlation",
            "The DOJ release explicitly references the same-day FBI/NSA cybersecurity advisory. Glass Onion therefore cross-links DOJ-26-972 to the already MASTER-LOCKED JCSA-20260826-01 graph while leaving the original advisory objects untouched. [DOJ source line 76]",
            "",
            "## Defensive interpretation",
            "The combined public record supports prioritizing visibility into exposed edge/IoT assets, proxy/VPS egress patterns, patching of known exploited vulnerabilities, and validation of dependencies that can be centrally disrupted. It does not authorize scanning or action against third-party infrastructure.",
            "",
        ]
    )


def _atomic_promote(temp_path: Path, final_path: Path) -> None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temp_path, final_path)


def run_glassonion_lock(
    root: str | Path,
    *,
    source_path: Path = DEFAULT_SOURCE,
    overlay_output: Path = DEFAULT_OVERLAY,
    brief_output: Path = DEFAULT_BRIEF,
    lock_output: Path = DEFAULT_LOCK,
) -> dict[str, Any]:
    root = Path(root).resolve()
    base_manifest, base_ontology = _verify_base_master_lock(root)
    source = _read_json(root / source_path)
    _validate_source(source)

    overlay = build_overlay(source, base_ontology, str(base_manifest["lockId"]))
    overlay_text = _json_text(overlay)
    brief_text = build_brief(source, overlay)
    source_hash = _sha256_bytes((root / source_path).read_bytes())
    overlay_hash = _sha256_text(overlay_text)
    brief_hash = _sha256_text(brief_text)
    base_lock_hash = _sha256_bytes((root / BASE_LOCK).read_bytes())
    lock_id = _sha256_text(f"{base_manifest['lockId']}:{base_lock_hash}:{source_hash}:{overlay_hash}:{brief_hash}")[:24]

    manifest = {
        "framework": "GPT-GLASSONION CROSS-SOURCE MASTER LOCK",
        "version": "1.0.0",
        "lockId": lock_id,
        "locked": True,
        "publicationState": "LOCKED_DEFENSIVE_OVERLAY",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "baseMasterLockId": base_manifest["lockId"],
        "baseMasterLockPath": BASE_LOCK.as_posix(),
        "source": source_path.as_posix(),
        "outputs": {
            "overlay": overlay_output.as_posix(),
            "brief": brief_output.as_posix(),
            "lock": lock_output.as_posix(),
        },
        "hashes": {
            "baseMasterLockSha256": base_lock_hash,
            "sourceSha256": source_hash,
            "overlaySha256": overlay_hash,
            "briefSha256": brief_hash,
        },
        "counts": {"objects": len(overlay["objects"]), "links": len(overlay["links"])},
        "guardrails": overlay["guardrails"],
    }

    final_overlay = root / overlay_output
    final_brief = root / brief_output
    final_lock = root / lock_output
    final_overlay.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="glassonion-lock-", dir=final_overlay.parent) as temp_dir:
        temp_root = Path(temp_dir)
        temp_overlay = temp_root / "glassonion-overlay.json"
        temp_brief = temp_root / "glassonion-brief.md"
        temp_lock = temp_root / "glassonion-lock.json"
        temp_overlay.write_text(overlay_text, encoding="utf-8")
        temp_brief.write_text(brief_text, encoding="utf-8")
        temp_lock.write_text(_json_text(manifest), encoding="utf-8")
        _require(_sha256_bytes(temp_overlay.read_bytes()) == overlay_hash, "Glass Onion overlay staging hash mismatch")
        _require(_sha256_bytes(temp_brief.read_bytes()) == brief_hash, "Glass Onion brief staging hash mismatch")
        _atomic_promote(temp_overlay, final_overlay)
        _atomic_promote(temp_brief, final_brief)
        _atomic_promote(temp_lock, final_lock)
    return manifest


def verify_glassonion_lock(root: str | Path) -> tuple[dict[str, Any], dict[str, Any]]:
    root = Path(root).resolve()
    manifest = _read_json(root / DEFAULT_LOCK)
    _require(manifest.get("locked") is True, "Glass Onion overlay is not locked")
    _verify_base_master_lock(root)
    expected = manifest.get("hashes") or {}
    paths = {
        "baseMasterLockSha256": root / BASE_LOCK,
        "sourceSha256": root / DEFAULT_SOURCE,
        "overlaySha256": root / DEFAULT_OVERLAY,
        "briefSha256": root / DEFAULT_BRIEF,
    }
    for key, path in paths.items():
        _require(path.is_file(), f"Glass Onion artifact missing: {path.relative_to(root)}")
        _require(_sha256_bytes(path.read_bytes()) == expected.get(key), f"Glass Onion hash mismatch: {path.relative_to(root)}")
    return manifest, _read_json(root / DEFAULT_OVERLAY)


def status(root: str | Path) -> str:
    manifest, overlay = verify_glassonion_lock(root)
    return (
        "🧅 GPT-GLASSONION STATUS // LOCKED ✅\n"
        f"Lock ID: {manifest['lockId']}\n"
        f"Base MASTER LOCK: {manifest['baseMasterLockId']}\n"
        f"Overlay: {len(overlay.get('objects') or [])} objects / {len(overlay.get('links') or [])} links\n"
        f"Source: {manifest['source']}\n"
        "Mode: defensive public-source correlation; base ontology immutable"
    )


def graph(root: str | Path) -> str:
    manifest, overlay = verify_glassonion_lock(root)
    lines = [f"🧅 GPT-GLASSONION GRAPH // {manifest['lockId']}"]
    for link in overlay.get("links") or []:
        props = link.get("properties") or {}
        locator = f" [DOJ lines {props.get('sourceLines')}]" if props.get("sourceLines") else ""
        lines.append(f"- {link['from']} --{link['linkType']}--> {link['to']}{locator}")
    return "\n".join(lines)


def query(root: str | Path, question: str) -> str:
    manifest, overlay = verify_glassonion_lock(root)
    tokens = {token.lower() for token in re.findall(r"[A-Za-z0-9_.-]{3,}", question)}
    matches: list[str] = []
    matched_refs: set[str] = set()
    for item in overlay.get("objects") or []:
        haystack = json.dumps(item, ensure_ascii=False).lower()
        if any(token in haystack for token in tokens):
            ref = f"{item['objectType']}:{item['id']}"
            matched_refs.add(ref)
            matches.append(f"- {ref} | {json.dumps(item.get('properties') or {}, ensure_ascii=False)}")
    related: list[str] = []
    for link in overlay.get("links") or []:
        if link.get("from") in matched_refs or link.get("to") in matched_refs:
            props = link.get("properties") or {}
            locator = f" [DOJ lines {props.get('sourceLines')}]" if props.get("sourceLines") else ""
            related.append(f"- {link['from']} --{link['linkType']}--> {link['to']}{locator}")
    if not matches:
        return f"🧅 GLASSONION QUERY // no locked overlay objects matched: {question}"
    return "\n".join(
        [
            f"🧅 GPT-GLASSONION QUERY // {question}",
            f"Lock ID: {manifest['lockId']}",
            "Matched source-grounded overlay objects:",
            *matches[:30],
            "Related overlay relationships:",
            *(related[:50] or ["- none"]),
            "Interpretation rule: source claims remain source claims; correlation does not create independent attribution.",
        ]
    )


def run_command(root: str | Path, command: str, argument: str = "") -> str:
    command = command.lower().strip()
    if command == "status":
        return status(root)
    if command == "brief":
        verify_glassonion_lock(root)
        return (Path(root).resolve() / DEFAULT_BRIEF).read_text(encoding="utf-8")
    if command == "graph":
        return graph(root)
    if command == "query":
        _require(bool(argument.strip()), "Glass Onion query requires a question")
        return query(root, argument)
    raise GlassOnionError(f"unknown Glass Onion command: {command}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build or inspect GPT-GLASSONION cross-source overlay")
    parser.add_argument("action", choices=["lock", "status", "brief", "graph", "query"], nargs="?", default="lock")
    parser.add_argument("argument", nargs="*", default=[])
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        if args.action == "lock":
            report = run_glassonion_lock(args.root)
            print("🧅 GPT-GLASSONION MASTER LOCK ✅")
            print(f"Lock ID: {report['lockId']}")
            print(f"Base MASTER LOCK: {report['baseMasterLockId']}")
            print(f"Overlay: {report['counts']['objects']} objects / {report['counts']['links']} links")
            return 0
        print(run_command(args.root, args.action, " ".join(args.argument)))
        return 0
    except GlassOnionError as exc:
        print(f"GPT-GLASSONION FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
