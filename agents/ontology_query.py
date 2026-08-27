"""Read-only query engine for MASTER-LOCKED ontology packages.

Every query verifies the MASTER LOCK manifest and SHA-256 hashes before reading
ontology output. The engine is deterministic, local-only, and does not execute
ontology actions or perform network operations.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_LOCK = Path("intel/qtfy/master-lock.json")


class OntologyQueryError(RuntimeError):
    """Raised when a locked ontology package cannot be verified or queried."""


@dataclass(frozen=True)
class LockedOntologyPackage:
    root: Path
    manifest: dict[str, Any]
    ontology: dict[str, Any]
    analysis: str
    source: dict[str, Any]

    @property
    def lock_id(self) -> str:
        return str(self.manifest.get("lockId") or "")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise OntologyQueryError(f"{label} does not exist: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OntologyQueryError(f"{label} is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise OntologyQueryError(f"{label} must be a JSON object")
    return value


def load_locked_package(root: str | Path, lock_path: Path = DEFAULT_LOCK) -> LockedOntologyPackage:
    repo_root = Path(root).resolve()
    manifest_path = repo_root / lock_path
    manifest = _load_json(manifest_path, "MASTER LOCK manifest")
    if manifest.get("locked") is not True:
        raise OntologyQueryError("MASTER LOCK manifest is not locked")
    if manifest.get("publicationState") != "LOCKED_AND_PUBLISHABLE":
        raise OntologyQueryError("MASTER LOCK package is not publishable")
    stages = manifest.get("subagents") or []
    if not stages or any(stage.get("status") != "PASS" for stage in stages):
        raise OntologyQueryError("MASTER LOCK subagent chain is not fully PASS")

    outputs = manifest.get("outputs") or {}
    source_rel = Path(str(manifest.get("source") or ""))
    ontology_rel = Path(str(outputs.get("ontology") or ""))
    analysis_rel = Path(str(outputs.get("analysis") or ""))
    if not source_rel.as_posix() or not ontology_rel.as_posix() or not analysis_rel.as_posix():
        raise OntologyQueryError("MASTER LOCK manifest is missing package paths")

    source_path = repo_root / source_rel
    ontology_path = repo_root / ontology_rel
    analysis_path = repo_root / analysis_rel
    for path, label in (
        (source_path, "source pack"),
        (ontology_path, "ontology output"),
        (analysis_path, "analysis output"),
    ):
        if not path.is_file():
            raise OntologyQueryError(f"{label} does not exist: {path.relative_to(repo_root)}")

    hashes = manifest.get("hashes") or {}
    expected = {
        source_path: str(hashes.get("sourceSha256") or ""),
        ontology_path: str(hashes.get("ontologySha256") or ""),
        analysis_path: str(hashes.get("analysisSha256") or ""),
    }
    for path, expected_hash in expected.items():
        if not expected_hash:
            raise OntologyQueryError(f"MASTER LOCK missing hash for {path.name}")
        actual = _sha256(path.read_bytes())
        if actual != expected_hash:
            raise OntologyQueryError(f"MASTER LOCK hash mismatch: {path.relative_to(repo_root)}")

    ontology = _load_json(ontology_path, "ontology output")
    source = _load_json(source_path, "source pack")
    analysis = analysis_path.read_text(encoding="utf-8")
    if ontology.get("mode") != "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY":
        raise OntologyQueryError("ontology mode is not defensive authorized-only")
    guardrails = ontology.get("guardrails") or {}
    if guardrails.get("masterLockRequiredForPublish") is not True:
        raise OntologyQueryError("ontology no longer requires MASTER LOCK")
    return LockedOntologyPackage(repo_root, manifest, ontology, analysis, source)


def _objects(package: LockedOntologyPackage, object_type: str | None = None) -> list[dict[str, Any]]:
    values = package.ontology.get("objects") or []
    if object_type is None:
        return list(values)
    return [item for item in values if item.get("objectType") == object_type]


def _ref(item: dict[str, Any]) -> str:
    return f"{item.get('objectType')}:{item.get('id')}"


def _display(item: dict[str, Any]) -> str:
    props = item.get("properties") or {}
    label = props.get("name") or props.get("label") or props.get("cve") or props.get("title") or item.get("id")
    page = props.get("sourcePage")
    suffix = f" [Source p.{page}]" if page is not None else ""
    return f"{item.get('objectType')}:{item.get('id')} — {label}{suffix}"


def ontology_status(package: LockedOntologyPackage) -> str:
    object_counts = Counter(str(item.get("objectType")) for item in _objects(package))
    links = package.ontology.get("links") or []
    lines = [
        "🔐 ONTOLOGY STATUS // MASTER LOCK VERIFIED",
        f"Lock ID: {package.lock_id}",
        f"Advisory: {package.manifest.get('advisoryId')}",
        f"Ontology version: {package.ontology.get('version')}",
        f"Objects: {sum(object_counts.values())} // Links: {len(links)}",
        "Core objects: " + ", ".join(f"{name}={count}" for name, count in sorted(object_counts.items()) if count),
        "Mode: DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "Integrity: source + ontology + analysis SHA-256 verified ✅",
    ]
    return "\n".join(lines)


def ontology_timeline(package: LockedOntologyPackage) -> str:
    events = sorted(_objects(package, "CampaignEvent"), key=lambda item: str((item.get("properties") or {}).get("date") or ""))
    lines = ["🗓️ ONTOLOGY TIMELINE // source-grounded campaign events"]
    for event in events:
        props = event.get("properties") or {}
        page = props.get("sourcePage")
        lines.append(
            f"{props.get('date') or '?'} | {props.get('targetCategory') or '?'} | "
            f"{props.get('activity') or '?'} | {props.get('outcome') or '?'}"
            + (f" [Source p.{page}]" if page is not None else "")
        )
    return "\n".join(lines)


def ontology_graph(package: LockedOntologyPackage) -> str:
    objects = {_ref(item): item for item in _objects(package)}
    links = package.ontology.get("links") or []
    counts = Counter(str(link.get("linkType")) for link in links)
    lines = ["🕸️ ONTOLOGY GRAPH // verified relationship summary"]
    for link_type, count in sorted(counts.items()):
        lines.append(f"{link_type}: {count}")
    event_links = [link for link in links if str(link.get("from", "")).startswith("CampaignEvent:") and link.get("linkType") in {"EventUsesTool", "EventReferencesVulnerability"}]
    if event_links:
        lines.append("\nCampaign event relationships:")
        by_event: dict[str, list[str]] = defaultdict(list)
        for link in event_links:
            target = objects.get(str(link.get("to")))
            target_text = _display(target) if target else str(link.get("to"))
            by_event[str(link.get("from"))].append(f"{link.get('linkType')} → {target_text}")
        for event_ref, relationships in sorted(by_event.items()):
            event = objects.get(event_ref)
            lines.append((_display(event) if event else event_ref) + ":")
            lines.extend(f"  - {relationship}" for relationship in relationships)
    return "\n".join(lines)


def ontology_gaps(package: LockedOntologyPackage) -> str:
    links = package.ontology.get("links") or []
    event_tools = {str(link.get("from")) for link in links if link.get("linkType") == "EventUsesTool"}
    event_vulns = {str(link.get("from")) for link in links if link.get("linkType") == "EventReferencesVulnerability"}
    referenced_vulns = {str(link.get("to")) for link in links if link.get("linkType") == "EventReferencesVulnerability"}

    lines = [
        "🧩 ONTOLOGY EVIDENCE GAPS // linkage gaps, not claims of source error",
        "These gaps identify where the locked graph lacks an explicit relationship; absence of a link does not prove absence in reality.",
    ]
    missing_any = False
    for event in _objects(package, "CampaignEvent"):
        ref = _ref(event)
        missing = []
        if ref not in event_tools:
            missing.append("no explicit tool link")
        if ref not in event_vulns:
            missing.append("no explicit vulnerability link")
        if missing:
            missing_any = True
            lines.append(f"- {_display(event)}: {', '.join(missing)}")

    unlinked_vulns = [item for item in _objects(package, "Vulnerability") if _ref(item) not in referenced_vulns]
    if unlinked_vulns:
        missing_any = True
        lines.append("Vulnerabilities mentioned by the advisory but not tied to a specific modeled campaign event:")
        lines.extend(f"- {_display(item)}" for item in unlinked_vulns)
    if not missing_any:
        lines.append("No modeled linkage gaps detected.")
    return "\n".join(lines)


def ontology_brief(package: LockedOntologyPackage) -> str:
    tools = _objects(package, "ThreatTool")
    vulns = _objects(package, "Vulnerability")
    techniques = _objects(package, "AttackTechnique")
    orgs = _objects(package, "Organization")
    events = _objects(package, "CampaignEvent")
    controls = _objects(package, "DefensiveControl")
    lines = [
        "📚 MASTER-LOCKED DEFENSIVE INTELLIGENCE BRIEF",
        f"Lock: {package.lock_id} // Advisory: {package.manifest.get('advisoryId')}",
        f"Scope: {len(orgs)} organizations, {len(tools)} tools, {len(vulns)} vulnerabilities, {len(events)} campaign events, {len(techniques)} ATT&CK techniques.",
        "Attribution handling: source attribution only; analytic inference must remain distinct from source claims.",
        "\nTools:",
    ]
    lines.extend(f"- {_display(item)}" for item in tools)
    lines.append("\nATT&CK:")
    lines.extend(f"- {_display(item)}" for item in techniques)
    lines.append("\nPrioritized defensive controls from the locked ontology:")
    for item in controls:
        props = item.get("properties") or {}
        lines.append(f"- {item.get('id')}: {props.get('objective')} (authorizedOnly={props.get('authorizedOnly')})")
    lines.append("\nUse /ontology-timeline, /ontology-graph, /ontology-gaps, or /ontology-query <question> for detail.")
    return "\n".join(lines)


_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "did", "do", "does", "for", "from", "how", "in", "is",
    "it", "of", "on", "or", "the", "to", "was", "were", "what", "when", "where", "which", "who", "with",
}


def _query_terms(question: str) -> list[str]:
    terms = [term.lower() for term in re.findall(r"[A-Za-z0-9_.:-]+", question)]
    return [term for term in terms if len(term) > 1 and term not in _STOPWORDS]


def ontology_query(package: LockedOntologyPackage, question: str, limit: int = 8) -> str:
    terms = _query_terms(question)
    if not terms:
        raise OntologyQueryError("query needs at least one meaningful term")
    objects = _objects(package)
    scored: list[tuple[int, dict[str, Any]]] = []
    for item in objects:
        blob = json.dumps(item, sort_keys=True, ensure_ascii=False).lower()
        score = sum(3 if term in str(item.get("id", "")).lower() else 1 for term in terms if term in blob)
        if score:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], str(pair[1].get("objectType")), str(pair[1].get("id"))))
    selected = [item for _, item in scored[: max(1, limit)]]
    if not selected:
        return "🔎 ONTOLOGY QUERY // no locked graph objects matched: " + question

    refs = {_ref(item) for item in selected}
    related_links = [
        link for link in package.ontology.get("links") or []
        if str(link.get("from")) in refs or str(link.get("to")) in refs
    ]
    lines = [f"🔎 ONTOLOGY QUERY // {question}", f"Lock ID: {package.lock_id}", "Matched source-grounded objects:"]
    for item in selected:
        props = item.get("properties") or {}
        lines.append(f"- {_display(item)}")
        details = []
        for key in ("role", "category", "context", "date", "targetCategory", "activity", "outcome", "objective", "framework"):
            value = props.get(key)
            if value not in (None, ""):
                details.append(f"{key}={value}")
        if details:
            lines.append("  " + " | ".join(details))
    if related_links:
        lines.append("Relevant locked relationships:")
        for link in related_links[:16]:
            lines.append(f"- {link.get('from')} --{link.get('linkType')}--> {link.get('to')}")
    lines.append("Interpretation rule: these are locked source/graph matches, not a determination of guilt or independent attribution.")
    return "\n".join(lines)


def run_query_command(root: str | Path, command: str, argument: str = "") -> str:
    package = load_locked_package(root)
    if command == "status":
        return ontology_status(package)
    if command == "timeline":
        return ontology_timeline(package)
    if command == "graph":
        return ontology_graph(package)
    if command == "gaps":
        return ontology_gaps(package)
    if command == "brief":
        return ontology_brief(package)
    if command == "query":
        return ontology_query(package, argument)
    raise OntologyQueryError(f"unknown ontology query command: {command}")
