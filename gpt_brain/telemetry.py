"""Grounded read-only CL1 telemetry ontology recall.

Metrics describe a local, qualitative Physarum solver; they are not live
sensors, measured biological motion, neural telemetry, or device control.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "docs" / "telemetry" / "registry.json"
SCHEMA = "xunia.cl1.telemetry-ontology.v1"
TRIGGERS = (
    "telemetry", "kinetic flow", "kinetic model", "kinetic network",
    "linear trace", "linear telemetry", "flow vector", "flux history",
    "motion index", "physarum monitor",
)
ALLOWLIST = {
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
}


def applies(query: str) -> bool:
    q = query.casefold()
    return any(term in q for term in TRIGGERS)


def load() -> dict:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    if (
        data.get("schema") != SCHEMA
        or data.get("physical_actuation") is not False
        or not isinstance(data.get("metrics"), list)
        or len(data["metrics"]) != 7
    ):
        raise ValueError("Invalid CL1 telemetry source registry")
    for source in data.get("sources", []):
        url = urlsplit(source.get("url", ""))
        if url.scheme != "https" or url.hostname not in ALLOWLIST:
            raise ValueError("Unapproved telemetry scientific citation")
    return data


def search(query: str, limit: int = 4) -> list[dict]:
    if not applies(query):
        return []
    data = load()
    terms = set(query.lower().replace("-", " ").split())
    sources = {item["id"]: item for item in data["sources"]}
    matches = []
    for metric in data["metrics"]:
        tokens = set(
            (metric["id"] + " " + metric["label"] + " "
             + metric["description"]).lower().replace("-", " ").split()
        )
        score = len(terms & tokens)
        matches.append((score, metric))
    matches.sort(key=lambda row: row[0], reverse=True)
    return [
        {
            "path": "cl1-telemetry:" + item["id"],
            "value": {
                "metric": item["label"],
                "definition": item["description"],
                "unit": item["unit"],
                "evidence": item["evidence"],
                "source_url": sources[item["source_id"]]["url"],
                "visualization": "https://xunia.org/telemetry/",
                "boundary": (
                    "Synthetic solver output only; no measured biological "
                    "velocity, live telemetry, neural recordings or "
                    "physical kinetic actuation."
                ),
            },
        }
        for _, item in matches[:max(1, min(limit, 7))]
    ]
