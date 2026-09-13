from __future__ import annotations

import importlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "workers"))
ontology = importlib.import_module("ontology_workers")


EXPECTED_WORLD_BANK_IDS = {
    "world-bank-api-overview",
    "world-bank-indicators-api-v2",
    "world-bank-indicators-api-purpose",
    "world-bank-data-catalog-api",
    "world-bank-projects-api",
    "world-bank-finances-api",
    "world-bank-climate-data-api",
    "world-bank-api-applications",
    "world-bank-api-terms",
}


def test_world_bank_entries_are_loaded_by_ontology() -> None:
    entries = {entry["id"]: entry for entry in ontology.list_knowledge()}
    assert EXPECTED_WORLD_BANK_IDS.issubset(entries)


def test_world_bank_entries_keep_source_provenance() -> None:
    entries = {entry["id"]: entry for entry in ontology.list_knowledge()}
    for entry_id in EXPECTED_WORLD_BANK_IDS:
        entry = entries[entry_id]
        assert entry["attribution"] == "World Bank Data Help Desk — Developer Information: Overview"
        assert entry["source_url"] == "https://datahelpdesk.worldbank.org/knowledgebase/articles/889386"
        assert entry["keywords"]
        assert entry["summary"]


def test_indicators_api_v1_is_not_treated_as_current() -> None:
    entries = {entry["id"]: entry for entry in ontology.list_knowledge()}
    summary = entries["world-bank-indicators-api-v2"]["summary"].lower()
    assert "use version 2" in summary
    assert "version 1" in summary
    assert "discontinued" in summary
