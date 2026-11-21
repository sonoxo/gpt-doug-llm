"""Grounded, local Physarum polycephalum knowledge for GPT-Doug Brain.

Read only a curated, source-cited ontology committed to the repository.
Biological observations are differentiated from virtual physicalization and AI.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / "docs" / "physarum" / "ontology.json"
SCHEMA = "xunia.cl1.physarum-ontology.v1"
KEYWORDS = (
    "physarum", "polycephalum", "plasmodium", "slime mold", "slime mould",
    "the blob", "protoplasm", "amoebozoa", "physa-01",
)
APPROVED = {
    "pubmed.ncbi.nlm.nih.gov",
    "pmc.ncbi.nlm.nih.gov",
    "link.springer.com",
    "www.sciencedirect.com",
}
_WORDS = re.compile(r"[a-z0-9]{3,}")


def applies(query: str) -> bool:
    return any(word in query.casefold() for word in KEYWORDS)


def load() -> dict:
    data = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    if (
        data.get("schema") != SCHEMA
        or data.get("scientific_name") != "Physarum polycephalum"
        or not isinstance(data.get("observational_facts"), list)
        or not isinstance(data.get("sources"), list)
        or len(data["sources"]) < 4
    ):
        raise ValueError("Physarum source ontology failed validation")
    for source in data["sources"]:
        u = urlsplit(source.get("url", ""))
        if u.scheme != "https" or u.hostname not in APPROVED:
            raise ValueError("Unapproved scientific source URL")
    return data


def search(query: str, limit: int = 4) -> list[dict]:
    if not applies(query):
        return []
    ontology = load()
    terms = set(_WORDS.findall(query.casefold()))
    sources = {item["id"]: item for item in ontology["sources"]}
    candidates = []
    for fact in ontology["observational_facts"]:
        source = sources[fact["source_id"]]
        words = set(
            _WORDS.findall(
                (fact["title"] + " " + fact["description"]).casefold()
            )
        )
        score = len(terms & words)
        candidates.append((score, fact, source))
    candidates.sort(key=lambda row: row[0], reverse=True)
    return [
        {
            "path": "cl1-bio:physarum:" + fact["id"],
            "value": {
                "title": fact["title"],
                "summary": fact["description"],
                "scientific_name": ontology["scientific_name"],
                "source_url": source["url"],
                "evidence": "CURATED_SCIENTIFIC_LITERATURE",
                "life_stage": ontology["lifecycle_scope"],
                "simulation": "https://xunia.org/physarum/",
                "limitations": (
                    "Amoebozoan protist, not fungus or neural tissue; "
                    "no proof of consciousness. Simulated route/flow graphs "
                    "are not measured physiology or connected hardware."
                ),
            },
        }
        for _, fact, source in candidates[:max(1, min(limit, 5))]
    ]
