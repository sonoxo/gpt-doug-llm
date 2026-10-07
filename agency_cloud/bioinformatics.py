from __future__ import annotations

import json
import math
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Callable, Final

CACHE_TTL_SECONDS: Final = 900
HTTP_TIMEOUT_SECONDS: Final = 10
USER_AGENT: Final = "GPT-DOUG-Bioinformatics-Fusion/1.0 (+public-research; read-only)"

ALLOWED_HOSTS: Final = {
    "rest.ensembl.org",
    "reactome.org",
    "data.rcsb.org",
    "www.ebi.ac.uk",
}

BIO_POLICY: Final = {
    "mode": "PUBLIC_REFERENCE_PLUS_SYNTHETIC_BIOCHIP",
    "realData": [
        "public reference genomics metadata",
        "public protein structure metadata",
        "public pathway-database release metadata",
        "public scientific-literature counts",
    ],
    "simulatedData": [
        "biochip electrode telemetry",
        "kinetic pulse propagation",
        "signal confidence",
        "synthetic impedance",
        "synthetic optical/electrical channel activity",
    ],
    "blocked": [
        "patient-specific genetic data",
        "implant control",
        "clinical diagnosis",
        "wet-lab protocol generation",
        "genetic modification instructions",
        "real-world biological actuation",
    ],
    "note": (
        "Real public reference data is fused with a simulated biochip digital twin. "
        "No implant, clinical device, patient record, or wet-lab system is controlled."
    ),
}

SOURCE_CATALOG: Final = [
    {
        "id": "ensembl-rest",
        "name": "Ensembl REST API",
        "domain": "GENOMICS",
        "authority": "EMBL-EBI / Ensembl",
        "url": "https://rest.ensembl.org/info/rest?content-type=application/json",
        "format": "json",
    },
    {
        "id": "reactome-version",
        "name": "Reactome Content Service",
        "domain": "PATHWAYS",
        "authority": "Reactome",
        "url": "https://reactome.org/ContentService/data/database/version",
        "format": "text",
    },
    {
        "id": "rcsb-4hhb",
        "name": "RCSB PDB — Hemoglobin 4HHB",
        "domain": "STRUCTURAL_BIOLOGY",
        "authority": "RCSB Protein Data Bank",
        "url": "https://data.rcsb.org/rest/v1/core/entry/4HHB",
        "format": "json",
    },
    {
        "id": "rcsb-1crn",
        "name": "RCSB PDB — Crambin 1CRN",
        "domain": "STRUCTURAL_BIOLOGY",
        "authority": "RCSB Protein Data Bank",
        "url": "https://data.rcsb.org/rest/v1/core/entry/1CRN",
        "format": "json",
    },
    {
        "id": "europepmc-biochip",
        "name": "Europe PMC — Biochip/Biosensor Literature",
        "domain": "LITERATURE",
        "authority": "Europe PMC / EMBL-EBI",
        "url": (
            "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
            "?query=biochip%20OR%20biosensor&format=json&pageSize=1"
        ),
        "format": "json",
    },
]

_cache_lock = threading.Lock()
_cache: dict = {"expires": 0.0, "value": None}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _fetch(url: str, expected_format: str) -> tuple[object, int]:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError("source URL is outside the approved HTTPS allowlist")

    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.5",
        },
    )
    started = time.perf_counter()
    with urllib.request.urlopen(  # nosec B310 - HTTPS host allowlist validated above
        request, timeout=HTTP_TIMEOUT_SECONDS
    ) as response:
        raw = response.read(4 * 1024 * 1024)
    latency_ms = int((time.perf_counter() - started) * 1000)
    text = raw.decode("utf-8", errors="replace")
    if expected_format == "json":
        return json.loads(text), latency_ms
    return text.strip(), latency_ms


def _parse(source_id: str, payload: object) -> dict:
    if source_id == "ensembl-rest":
        if not isinstance(payload, dict):
            raise ValueError("unexpected Ensembl schema")
        return {
            "apiRelease": payload.get("release"),
            "apiVersion": payload.get("version"),
            "referenceType": "GENOMICS_METADATA",
        }

    if source_id == "reactome-version":
        version = str(payload).strip()
        if not version:
            raise ValueError("empty Reactome version")
        return {
            "databaseVersion": version,
            "referenceType": "PATHWAY_KNOWLEDGEBASE",
        }

    if source_id.startswith("rcsb-"):
        if not isinstance(payload, dict):
            raise ValueError("unexpected RCSB schema")
        struct = payload.get("struct") or {}
        entry_info = payload.get("rcsb_entry_info") or {}
        methods = payload.get("exptl") or []
        resolution = entry_info.get("resolution_combined") or []
        return {
            "entryId": payload.get("rcsb_id") or source_id.split("-", 1)[-1].upper(),
            "title": struct.get("title"),
            "experimentalMethod": (
                methods[0].get("method")
                if methods and isinstance(methods[0], dict)
                else None
            ),
            "resolutionAngstrom": resolution[0] if resolution else None,
            "polymerEntityCount": entry_info.get("polymer_entity_count"),
            "nonpolymerEntityCount": entry_info.get("nonpolymer_entity_count"),
            "referenceType": "STRUCTURE_METADATA",
        }

    if source_id == "europepmc-biochip":
        if not isinstance(payload, dict):
            raise ValueError("unexpected Europe PMC schema")
        result_list = payload.get("resultList") or {}
        results = result_list.get("result") or []
        first = results[0] if results and isinstance(results[0], dict) else {}
        return {
            "hitCount": payload.get("hitCount"),
            "query": "biochip OR biosensor",
            "sampleTitle": first.get("title"),
            "sampleJournal": first.get("journalTitle"),
            "sampleYear": first.get("pubYear"),
            "referenceType": "LITERATURE_SIGNAL",
        }

    raise ValueError("unsupported bioinformatics source")


def _source_score(online: bool, latency_ms: int | None) -> int:
    if not online:
        return 0
    if latency_ms is None:
        return 60
    latency_component = max(0, min(25, round(25 * math.exp(-latency_ms / 5000))))
    return min(100, 75 + latency_component)


def build_fusion(
    fetcher: Callable[[str, str], tuple[object, int]] = _fetch,
) -> dict:
    sources = []
    for definition in SOURCE_CATALOG:
        try:
            payload, latency_ms = fetcher(definition["url"], definition["format"])
            parsed = _parse(definition["id"], payload)
            sources.append(
                {
                    **definition,
                    "status": "ONLINE",
                    "score": _source_score(True, latency_ms),
                    "latencyMs": latency_ms,
                    "data": parsed,
                }
            )
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            sources.append(
                {
                    **definition,
                    "status": "DEGRADED",
                    "score": 0,
                    "latencyMs": None,
                    "data": {},
                    "error": str(exc)[:300],
                }
            )

    online = [item for item in sources if item["status"] == "ONLINE"]
    structure_refs = [
        item["data"]
        for item in online
        if item["domain"] == "STRUCTURAL_BIOLOGY"
    ]
    literature = next(
        (item["data"] for item in online if item["id"] == "europepmc-biochip"),
        {},
    )

    seed = sum(item["score"] for item in sources) or 1
    chip_nodes = []
    for row in range(8):
        for col in range(8):
            idx = row * 8 + col
            phase = (seed + idx * 17) % 360
            chip_nodes.append(
                {
                    "id": f"E{idx + 1:02d}",
                    "row": row,
                    "col": col,
                    "channel": ["OPTICAL", "ELECTRICAL", "CHEMICAL_SIM", "REFERENCE"][idx % 4],
                    "activity": round(0.25 + ((phase % 70) / 100), 3),
                    "impedanceKOhm": round(20 + ((phase * 13) % 180) / 10, 2),
                    "confidence": round(0.80 + ((idx * 7) % 18) / 100, 2),
                    "simulated": True,
                }
            )

    return {
        "schema": "gpt-doug.bioinformatics-fusion.v1",
        "generatedAt": _now().isoformat(),
        "policy": BIO_POLICY,
        "summary": {
            "sourceCount": len(sources),
            "onlineSources": len(online),
            "degradedSources": len(sources) - len(online),
            "structureReferences": len(structure_refs),
            "literatureHits": literature.get("hitCount"),
            "biochipNodes": len(chip_nodes),
            "realReferenceLayer": True,
            "realDeviceControl": False,
        },
        "sources": sources,
        "structures": structure_refs,
        "biochip": {
            "mode": "DIGITAL_TWIN_SIMULATION",
            "label": "Synthetic 8x8 multi-channel biochip",
            "nodes": chip_nodes,
            "kinetics": {
                "model": "visual signal-propagation simulation",
                "actuation": False,
                "implantControl": False,
                "clinicalUse": False,
            },
        },
        "claim": (
            "Real public bioinformatics reference metadata is shown alongside simulated "
            "biochip kinetics. The biochip layer is not a real implant or clinical device."
        ),
    }


def bioinformatics_catalog() -> dict:
    return {
        "schema": "gpt-doug.bioinformatics-sources.v1",
        "policy": BIO_POLICY,
        "sources": SOURCE_CATALOG,
    }


def bioinformatics_fusion(force: bool = False) -> dict:
    now = time.monotonic()
    with _cache_lock:
        if _cache.get("value") is not None and not force and now < float(_cache["expires"]):
            return _cache["value"]

    value = build_fusion()
    with _cache_lock:
        _cache["value"] = value
        _cache["expires"] = time.monotonic() + CACHE_TTL_SECONDS
    return value
