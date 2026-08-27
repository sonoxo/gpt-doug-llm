"""Transactional MASTER LOCK pipeline for the QTFY defensive ontology.

The pipeline coordinates deterministic specialist subagents. No output is marked
published until source ingest, ontology construction, ontology validation, analysis,
and lock sealing all pass. The lock manifest is written last and acts as the
publication commit marker.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.qtfy_advisory_intel import build_qtfy_defensive_plan
from agents.qtfy_analyze import build_analysis

DEFAULT_SOURCE = Path("intel/qtfy/JCSA-20260826-01.json")
DEFAULT_ANALYSIS = Path("intel/qtfy/qtfy-analysis.md")
DEFAULT_ONTOLOGY = Path("intel/qtfy/qtfy-ontology-runtime.json")
DEFAULT_LOCK = Path("intel/qtfy/master-lock.json")


class MasterLockError(RuntimeError):
    """Raised when a MASTER LOCK stage cannot be proven valid."""


@dataclass(frozen=True)
class StageResult:
    subagent: str
    status: str
    detail: str


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise MasterLockError(message)


def _source_ids(items: list[dict[str, Any]]) -> set[str]:
    return {str(item.get("id")) for item in items if item.get("id")}


def _validate_source(data: dict[str, Any]) -> dict[str, int]:
    required = {
        "advisoryId",
        "title",
        "published",
        "tlp",
        "sourceUrl",
        "threatProfile",
        "organizations",
        "tools",
        "attackTechniques",
        "vulnerabilities",
        "campaignEvents",
        "keyDefensiveActions",
        "iocFeeds",
        "iocPolicy",
    }
    missing = sorted(required - set(data))
    _require(not missing, f"source pack missing required fields: {', '.join(missing)}")
    _require(data["advisoryId"] == "JCSA-20260826-01", "unexpected advisoryId")
    _require(data["tlp"] == "TLP:CLEAR", "unexpected TLP marking")
    _require(
        data.get("usePolicy") == "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY",
        "source usePolicy must remain defensive and authorized-only",
    )
    policy = data.get("iocPolicy") or {}
    _require(policy.get("automaticBlocking") is False, "automatic IOC blocking must remain disabled")
    _require(policy.get("humanReviewRequired") is True, "IOC human review must remain required")

    for collection in ("organizations", "tools", "vulnerabilities", "campaignEvents"):
        values = data.get(collection)
        _require(isinstance(values, list) and values, f"{collection} must be a non-empty list")
        seen: set[str] = set()
        for item in values:
            _require(isinstance(item, dict), f"{collection} contains a non-object entry")
            item_id = str(item.get("id") or "")
            _require(bool(item_id), f"{collection} entry is missing id")
            _require(item_id not in seen, f"duplicate {collection} id: {item_id}")
            seen.add(item_id)
            _require(item.get("sourcePage") is not None, f"{collection}:{item_id} missing sourcePage")

    return {
        "organizations": len(data["organizations"]),
        "tools": len(data["tools"]),
        "vulnerabilities": len(data["vulnerabilities"]),
        "campaignEvents": len(data["campaignEvents"]),
        "attackTechniques": len(data["attackTechniques"]),
    }


def _validate_source_plan_alignment(data: dict[str, Any], plan: dict[str, Any]) -> None:
    _require(plan.get("advisoryId") == data.get("advisoryId"), "plan/source advisoryId drift")
    _require(plan.get("source") == data.get("sourceUrl"), "plan/source URL drift")
    _require(plan.get("tlp") == data.get("tlp"), "plan/source TLP drift")
    _require(plan.get("published") == data.get("published"), "plan/source published-date drift")
    _require(plan.get("sourcePack") == DEFAULT_SOURCE.as_posix(), "plan sourcePack path drift")

    comparisons = (
        ("organizations", "organizations"),
        ("tools", "tools"),
        ("vulnerabilities", "vulnerabilities"),
        ("campaignEvents", "campaignEvents"),
    )
    for source_key, plan_key in comparisons:
        source_ids = _source_ids(data[source_key])
        plan_ids = _source_ids(plan[plan_key])
        _require(source_ids == plan_ids, f"{source_key} source/plan id drift")

    source_techniques = {str(item.get("id")) for item in data["attackTechniques"]}
    plan_techniques = set(plan["attackTechniques"])
    _require(source_techniques == plan_techniques, "ATT&CK source/plan id drift")


def _validate_ontology(data: dict[str, Any], ontology: dict[str, Any]) -> dict[str, int]:
    _require(ontology.get("mode") == "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY", "ontology mode drift")
    guardrails = ontology.get("guardrails") or {}
    _require(guardrails.get("automaticBlocking") is False, "ontology automaticBlocking must be false")
    _require(guardrails.get("externalThirdPartyAction") is False, "external third-party action must be false")
    _require(guardrails.get("humanApprovalForContainment") is True, "containment must require human approval")
    _require(
        guardrails.get("masterLockRequiredForPublish") is True,
        "ontology must require MASTER LOCK before publication",
    )

    objects = ontology.get("objects") or []
    links = ontology.get("links") or []
    _require(objects and links, "ontology must contain objects and links")

    refs: set[str] = set()
    for item in objects:
        ref = f"{item.get('objectType')}:{item.get('id')}"
        _require(ref not in refs, f"duplicate ontology object ref: {ref}")
        refs.add(ref)

    for link in links:
        source = str(link.get("from") or "")
        target = str(link.get("to") or "")
        _require(source in refs, f"dangling ontology link source: {source}")
        _require(target in refs, f"dangling ontology link target: {target}")

    expected_refs = {
        *(f"Organization:{item['id']}" for item in data["organizations"]),
        *(f"ThreatTool:{item['id']}" for item in data["tools"]),
        *(f"Vulnerability:{item['id']}" for item in data["vulnerabilities"]),
        *(f"CampaignEvent:{item['id']}" for item in data["campaignEvents"]),
        *(f"AttackTechnique:{item['id']}" for item in data["attackTechniques"]),
    }
    missing = sorted(expected_refs - refs)
    _require(not missing, f"ontology missing source-grounded refs: {', '.join(missing[:8])}")

    advisory_ref = f"CyberAdvisory:{data['advisoryId']}"
    _require(advisory_ref in refs, "ontology missing advisory object")

    return {"objects": len(objects), "links": len(links), "sourceGroundedRefs": len(expected_refs)}


def _atomic_promote(temp_path: Path, final_path: Path) -> None:
    final_path.parent.mkdir(parents=True, exist_ok=True)
    os.replace(temp_path, final_path)


def run_master_lock(
    root: str | Path,
    *,
    source: Path = DEFAULT_SOURCE,
    analysis_output: Path = DEFAULT_ANALYSIS,
    ontology_output: Path = DEFAULT_ONTOLOGY,
    lock_output: Path = DEFAULT_LOCK,
) -> dict[str, Any]:
    """Run all ontology subagents and publish only after every stage passes."""
    repo_root = Path(root).resolve()
    source_path = repo_root / source
    analysis_path = repo_root / analysis_output
    ontology_path = repo_root / ontology_output
    lock_path = repo_root / lock_output
    stages: list[StageResult] = []

    _require(source_path.is_file(), f"source pack does not exist: {source.as_posix()}")
    source_bytes = source_path.read_bytes()
    try:
        data = json.loads(source_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise MasterLockError(f"source pack is not valid UTF-8 JSON: {exc}") from exc

    counts = _validate_source(data)
    stages.append(StageResult("source-agent", "PASS", f"validated source pack: {counts}"))

    plan = build_qtfy_defensive_plan()
    _validate_source_plan_alignment(data, plan)
    ontology = plan["ontology"]
    stages.append(StageResult("ontology-builder-agent", "PASS", "built ontology from verified defensive profile"))

    ontology_counts = _validate_ontology(data, ontology)
    stages.append(StageResult("ontology-validator-agent", "PASS", f"validated graph: {ontology_counts}"))

    analysis_text = build_analysis(data)
    _require(data["advisoryId"] in analysis_text, "analysis missing advisory provenance")
    _require("Source p." in analysis_text, "analysis missing source-page references")
    stages.append(StageResult("analysis-agent", "PASS", "generated provenance-preserving defensive analysis"))

    ontology_text = _json_text(ontology)
    source_hash = _sha256_bytes(source_bytes)
    ontology_hash = _sha256_text(ontology_text)
    analysis_hash = _sha256_text(analysis_text)
    lock_id = _sha256_text(f"{source_hash}:{ontology_hash}:{analysis_hash}")[:24]
    stages.append(StageResult("master-lock-agent", "PASS", f"sealed lock {lock_id}"))

    manifest = {
        "framework": "ZYRA ONTOLOGY MASTER LOCK",
        "version": "1.0.0",
        "lockId": lock_id,
        "locked": True,
        "publicationState": "LOCKED_AND_PUBLISHABLE",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "advisoryId": data["advisoryId"],
        "source": source.as_posix(),
        "outputs": {
            "ontology": ontology_output.as_posix(),
            "analysis": analysis_output.as_posix(),
            "lock": lock_output.as_posix(),
        },
        "hashes": {
            "sourceSha256": source_hash,
            "ontologySha256": ontology_hash,
            "analysisSha256": analysis_hash,
        },
        "subagents": [asdict(stage) for stage in stages],
        "guardrails": {
            "allSubagentsMustPass": True,
            "manifestWrittenLast": True,
            "automaticIOCBlocking": False,
            "externalThirdPartyAction": False,
            "humanApprovalForContainment": True,
            "attributionHandling": "PRESERVE_SOURCE_CLAIM_NATURE",
        },
    }

    analysis_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ontology-master-lock-", dir=analysis_path.parent) as temp_dir:
        temp_root = Path(temp_dir)
        temp_ontology = temp_root / "qtfy-ontology-runtime.json"
        temp_analysis = temp_root / "qtfy-analysis.md"
        temp_lock = temp_root / "master-lock.json"
        temp_ontology.write_text(ontology_text, encoding="utf-8")
        temp_analysis.write_text(analysis_text, encoding="utf-8")
        temp_lock.write_text(_json_text(manifest), encoding="utf-8")

        _require(_sha256_bytes(temp_ontology.read_bytes()) == ontology_hash, "ontology staging hash mismatch")
        _require(_sha256_bytes(temp_analysis.read_bytes()) == analysis_hash, "analysis staging hash mismatch")

        _atomic_promote(temp_ontology, ontology_path)
        _atomic_promote(temp_analysis, analysis_path)
        _atomic_promote(temp_lock, lock_path)

    return manifest


def print_master_lock_report(report: dict[str, Any]) -> None:
    print("\n🔒 ZYRA ONTOLOGY MASTER LOCK")
    for stage in report.get("subagents", []):
        icon = "✅" if stage.get("status") == "PASS" else "❌"
        print(f"   {icon} {stage.get('subagent')}: {stage.get('detail')}")
    print(f"🔐 Lock ID: {report.get('lockId')}")
    print(f"🚦 Result: {'PASS ✅' if report.get('locked') else 'FAIL ❌'}")
    outputs = report.get("outputs") or {}
    print(f"📦 Ontology: {outputs.get('ontology')}")
    print(f"🧾 Analysis: {outputs.get('analysis')}")
    print(f"🪪 Manifest: {outputs.get('lock')}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the ZYRA ontology MASTER LOCK pipeline")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        report = run_master_lock(args.root)
    except MasterLockError as exc:
        print(f"MASTER LOCK FAIL: {exc}")
        return 1
    print_master_lock_report(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
