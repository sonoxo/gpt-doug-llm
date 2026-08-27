"""VA3LM Red Hat defense ontology and lock pipeline.

Builds a deterministic defensive ontology from NSA QTFY intelligence plus local
Red Hat posture evidence. The pipeline is read-only against the host except for
writing local evidence/lock artifacts. It never scans remote systems, executes
exploits, retaliates, or performs automatic containment.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from agents.va3lm_redhat_defense import CONTROL_CATALOG, write_locked_evidence

SOURCE = Path("intel/va3lm/NSA-QTFY-20260826.json")
EVIDENCE = Path("intel/va3lm/redhat-defense-evidence.json")
ONTOLOGY = Path("intel/va3lm/redhat-defense-ontology.json")
LOCK = Path("intel/va3lm/redhat-ontology-lock.json")
MODE = "DEFENSIVE_AUTHORIZED_ENVIRONMENTS_ONLY"


class Va3lmOntologyError(RuntimeError):
    """Raised when VA3LM defensive ontology evidence cannot be validated."""


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise Va3lmOntologyError(message)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_text(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise Va3lmOntologyError(f"{label} does not exist: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise Va3lmOntologyError(f"{label} is invalid JSON: {exc}") from exc
    if not isinstance(value, dict):
        raise Va3lmOntologyError(f"{label} must be a JSON object")
    return value


def _validate_source(source: dict[str, Any]) -> None:
    required = {
        "intelId",
        "title",
        "published",
        "sourceUrl",
        "intelligenceClass",
        "usePolicy",
        "tooling",
        "threatPatterns",
        "targetSectors",
        "recommendedDefenses",
        "redHatDefenseBindings",
        "guardrails",
    }
    missing = sorted(required - set(source))
    _require(not missing, f"source intelligence missing: {', '.join(missing)}")
    _require(source["intelId"] == "NSA-QTFY-2026-08-26", "unexpected source intelligence id")
    _require(source["usePolicy"] == MODE, "source use policy drift")
    guardrails = source.get("guardrails") or {}
    for key in ("remoteScanning", "exploitExecution", "retaliation", "automaticContainment"):
        _require(guardrails.get(key) is False, f"source guardrail must keep {key}=false")
    _require(guardrails.get("humanReviewRequired") is True, "source human review must remain required")


def _obj(object_type: str, object_id: str, **properties: Any) -> dict[str, Any]:
    return {"objectType": object_type, "id": object_id, "properties": properties}


def _link(link_type: str, source: str, target: str) -> dict[str, str]:
    return {"linkType": link_type, "from": source, "to": target}


def build_ontology(source: dict[str, Any], evidence: dict[str, Any]) -> dict[str, Any]:
    _validate_source(source)
    _require(evidence.get("mode") == MODE, "host evidence mode drift")
    evidence_guardrails = evidence.get("guardrails") or {}
    _require(evidence_guardrails.get("remoteScanning") is False, "host evidence remote scanning drift")
    _require(evidence_guardrails.get("exploitExecution") is False, "host evidence exploit guardrail drift")
    _require(evidence_guardrails.get("retaliation") is False, "host evidence retaliation guardrail drift")

    objects: list[dict[str, Any]] = []
    links: list[dict[str, str]] = []
    source_ref = f"IntelSource:{source['intelId']}"
    objects.append(
        _obj(
            "IntelSource",
            source["intelId"],
            title=source["title"],
            published=source["published"],
            sourceUrl=source["sourceUrl"],
            intelligenceClass=source["intelligenceClass"],
        )
    )

    threat_ref = "ThreatProfile:QTFY"
    objects.append(_obj("ThreatProfile", "QTFY", aliases=source.get("actors") or [], sourceIntel=source["intelId"]))
    links.append(_link("IntelDescribesThreatProfile", source_ref, threat_ref))

    for tool in source["tooling"]:
        ref = f"ThreatTool:{tool['id']}"
        objects.append(_obj("ThreatTool", tool["id"], name=tool["name"], role=tool["role"], sourceIntel=source["intelId"]))
        links.append(_link("ThreatProfileUsesTool", threat_ref, ref))
        links.append(_link("IntelDescribesTool", source_ref, ref))

    for pattern in source["threatPatterns"]:
        ref = f"ThreatPattern:{pattern['id']}"
        objects.append(_obj("ThreatPattern", pattern["id"], statement=pattern["statement"], sourceIntel=source["intelId"]))
        links.append(_link("ThreatProfileExhibitsPattern", threat_ref, ref))
        links.append(_link("IntelDescribesPattern", source_ref, ref))

    for sector in source["targetSectors"]:
        sector_id = sector.lower().replace(" ", "-")
        ref = f"TargetSector:{sector_id}"
        objects.append(_obj("TargetSector", sector_id, name=sector, sourceIntel=source["intelId"]))
        links.append(_link("IntelIdentifiesTargetSector", source_ref, ref))

    control_ids = {item["id"] for item in CONTROL_CATALOG}
    for control in CONTROL_CATALOG:
        ref = f"DefensiveControl:{control['id']}"
        objects.append(
            _obj(
                "DefensiveControl",
                control["id"],
                title=control["title"],
                objective=control["objective"],
                sourceIntel=control["sourceIntel"],
                authorizedOnly=True,
            )
        )

    for recommendation in source["recommendedDefenses"]:
        rec_ref = f"DefenseRecommendation:{recommendation['id']}"
        objects.append(
            _obj(
                "DefenseRecommendation",
                recommendation["id"],
                statement=recommendation["statement"],
                sourceIntel=source["intelId"],
            )
        )
        links.append(_link("IntelRecommendsDefense", source_ref, rec_ref))
        for control_id in (source.get("redHatDefenseBindings") or {}).get(recommendation["id"], []):
            _require(control_id in control_ids, f"unknown Red Hat control binding: {control_id}")
            links.append(_link("RecommendationImplementedByControl", rec_ref, f"DefensiveControl:{control_id}"))

    for check in evidence.get("checks") or []:
        control_id = str(check.get("control_id") or "")
        check_id = control_id + "-CHECK"
        ref = f"HostDefenseCheck:{check_id}"
        objects.append(
            _obj(
                "HostDefenseCheck",
                check_id,
                controlId=control_id,
                status=check.get("status"),
                detail=check.get("detail"),
                sourceIntel=check.get("source_intel"),
                evidenceClass="LOCAL_DEFENSE_EVIDENCE",
            )
        )
        if control_id in control_ids:
            links.append(_link("ControlValidatedByHostCheck", f"DefensiveControl:{control_id}", ref))

    ontology = {
        "framework": "VA3LM RED HAT DEFENSE ONTOLOGY",
        "version": "1.0.0",
        "mode": MODE,
        "sourceIntel": source["intelId"],
        "objects": objects,
        "links": links,
        "guardrails": {
            "remoteScanning": False,
            "exploitExecution": False,
            "retaliation": False,
            "automaticContainment": False,
            "arbitraryShell": False,
            "humanReviewRequired": True,
            "masterLockRequiredForPublish": True,
        },
    }
    _validate_ontology(ontology)
    return ontology


def _validate_ontology(ontology: dict[str, Any]) -> None:
    _require(ontology.get("mode") == MODE, "ontology mode drift")
    guardrails = ontology.get("guardrails") or {}
    for key in ("remoteScanning", "exploitExecution", "retaliation", "automaticContainment", "arbitraryShell"):
        _require(guardrails.get(key) is False, f"ontology guardrail must keep {key}=false")
    _require(guardrails.get("humanReviewRequired") is True, "ontology must require human review")
    _require(guardrails.get("masterLockRequiredForPublish") is True, "ontology must require MASTER LOCK")
    refs = {f"{item.get('objectType')}:{item.get('id')}" for item in ontology.get("objects") or []}
    _require(refs, "ontology has no objects")
    for link in ontology.get("links") or []:
        _require(str(link.get("from")) in refs, f"dangling source: {link.get('from')}")
        _require(str(link.get("to")) in refs, f"dangling target: {link.get('to')}")


def run_lock(root: str | Path) -> dict[str, Any]:
    repo_root = Path(root).resolve()
    source_path = repo_root / SOURCE
    source = _load_json(source_path, "NSA QTFY intelligence pack")
    _validate_source(source)

    defense_result = write_locked_evidence(repo_root)
    evidence = defense_result["evidence"]
    evidence_path = repo_root / EVIDENCE
    ontology = build_ontology(source, evidence)
    ontology_text = _json_text(ontology)

    source_hash = _sha256(source_path.read_bytes())
    evidence_hash = _sha256(evidence_path.read_bytes())
    ontology_hash = _sha256(ontology_text.encode("utf-8"))
    lock_id = _sha256(f"{source_hash}:{evidence_hash}:{ontology_hash}".encode("utf-8"))[:24]

    manifest = {
        "framework": "VA3LM RED HAT ONTOLOGY MASTER LOCK",
        "version": "1.0.0",
        "lockId": lock_id,
        "locked": True,
        "publicationState": "LOCKED_DEFENSIVE_INTELLIGENCE",
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE.as_posix(),
        "evidence": EVIDENCE.as_posix(),
        "ontology": ONTOLOGY.as_posix(),
        "hashes": {
            "sourceSha256": source_hash,
            "evidenceSha256": evidence_hash,
            "ontologySha256": ontology_hash,
        },
        "subagents": [
            {"subagent": "nsa-intel-validator", "status": "PASS"},
            {"subagent": "redhat-posture-agent", "status": "PASS"},
            {"subagent": "defense-ontology-builder", "status": "PASS"},
            {"subagent": "defense-ontology-validator", "status": "PASS"},
            {"subagent": "va3lm-lock-agent", "status": "PASS"},
        ],
        "guardrails": ontology["guardrails"],
    }

    ontology_path = repo_root / ONTOLOGY
    lock_path = repo_root / LOCK
    ontology_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="va3lm-redhat-lock-", dir=ontology_path.parent) as tmp:
        tmp_root = Path(tmp)
        tmp_ontology = tmp_root / ONTOLOGY.name
        tmp_lock = tmp_root / LOCK.name
        tmp_ontology.write_text(ontology_text, encoding="utf-8")
        tmp_lock.write_text(_json_text(manifest), encoding="utf-8")
        _require(_sha256(tmp_ontology.read_bytes()) == ontology_hash, "ontology staging hash mismatch")
        os.replace(tmp_ontology, ontology_path)
        os.replace(tmp_lock, lock_path)
    return manifest


def load_verified(root: str | Path) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    repo_root = Path(root).resolve()
    manifest = _load_json(repo_root / LOCK, "VA3LM lock")
    _require(manifest.get("locked") is True, "VA3LM lock is not locked")
    _require(manifest.get("publicationState") == "LOCKED_DEFENSIVE_INTELLIGENCE", "VA3LM lock state drift")
    source_path = repo_root / str(manifest.get("source") or "")
    evidence_path = repo_root / str(manifest.get("evidence") or "")
    ontology_path = repo_root / str(manifest.get("ontology") or "")
    hashes = manifest.get("hashes") or {}
    for path, key in (
        (source_path, "sourceSha256"),
        (evidence_path, "evidenceSha256"),
        (ontology_path, "ontologySha256"),
    ):
        _require(path.is_file(), f"locked artifact missing: {path}")
        _require(_sha256(path.read_bytes()) == hashes.get(key), f"locked artifact hash mismatch: {path.name}")
    source = _load_json(source_path, "source intelligence")
    evidence = _load_json(evidence_path, "host evidence")
    ontology = _load_json(ontology_path, "defense ontology")
    _validate_source(source)
    _validate_ontology(ontology)
    return manifest, evidence, ontology


def status(root: str | Path) -> str:
    try:
        manifest, evidence, ontology = load_verified(root)
    except Va3lmOntologyError as exc:
        return f"🛡️ VA3LM RED HAT INTELLIGENCE // GATE HOLD ❌ // {exc}"
    counts: dict[str, int] = {}
    for item in evidence.get("checks") or []:
        value = str(item.get("status") or "UNKNOWN")
        counts[value] = counts.get(value, 0) + 1
    return "\n".join(
        [
            "🛡️ VA3LM RED HAT INTELLIGENCE // LOCK VERIFIED ✅",
            f"Lock ID: {manifest['lockId']}",
            f"Ontology: {len(ontology.get('objects') or [])} objects / {len(ontology.get('links') or [])} links",
            "Host checks: " + ", ".join(f"{key}={value}" for key, value in sorted(counts.items())),
            "Remote scanning: OFF // exploit execution: OFF // retaliation: OFF",
        ]
    )


def graph(root: str | Path) -> str:
    manifest, _, ontology = load_verified(root)
    lines = [f"🕸️ VA3LM RED HAT DEFENSE GRAPH // {manifest['lockId']}"]
    for link in ontology.get("links") or []:
        if link.get("linkType") in {
            "IntelRecommendsDefense",
            "RecommendationImplementedByControl",
            "ControlValidatedByHostCheck",
        }:
            lines.append(f"- {link['from']} --{link['linkType']}--> {link['to']}")
    return "\n".join(lines)


def gaps(root: str | Path) -> str:
    manifest, evidence, _ = load_verified(root)
    lines = [f"🧩 VA3LM RED HAT DEFENSE GAPS // {manifest['lockId']}"]
    weak = [item for item in evidence.get("checks") or [] if item.get("status") != "PASS"]
    if not weak:
        lines.append("No local posture gaps detected by the fixed read-only checks.")
    else:
        for item in weak:
            lines.append(f"- {item.get('control_id')}: {item.get('status')} // {item.get('detail')}")
    lines.append("Gap output is defensive posture evidence, not authorization to change systems automatically.")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="VA3LM Red Hat defensive ontology pipeline")
    parser.add_argument("command", choices=("lock", "status", "graph", "gaps"), nargs="?", default="status")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    if args.command == "lock":
        try:
            manifest = run_lock(args.root)
        except Va3lmOntologyError as exc:
            print(f"VA3LM LOCK FAIL: {exc}")
            return 1
        print("🛡️ VA3LM RED HAT ONTOLOGY MASTER LOCK ✅")
        print(f"Lock ID: {manifest['lockId']}")
        print("Subagents: " + ", ".join(item["subagent"] for item in manifest["subagents"]))
        return 0
    if args.command == "graph":
        print(graph(args.root))
        return 0
    if args.command == "gaps":
        print(gaps(args.root))
        return 0
    print(status(args.root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
