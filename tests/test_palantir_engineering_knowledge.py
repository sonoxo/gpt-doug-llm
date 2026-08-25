import json
from pathlib import Path

from tools.validate_intelligence_knowledge import validate_jsonl
from workers import ontology_workers as ontology


KNOWLEDGE_PATH = Path("workers/knowledge/palantir_engineering_stack.jsonl")


def test_engineering_knowledge_has_public_provenance():
    findings = validate_jsonl(KNOWLEDGE_PATH)
    assert [finding for finding in findings if finding.level == "error"] == []

    records = [json.loads(line) for line in KNOWLEDGE_PATH.read_text().splitlines() if line.strip()]
    assert len(records) >= 10
    assert all(record["classification"] == "public" for record in records)
    assert all(record["source_url"].startswith("https://") for record in records)


def test_data_engineer_prompt_retrieves_pipeline_knowledge():
    links = ontology.link_task_to_knowledge(
        "test-palantir-data-engineer",
        "Design a data engineer pipeline with dataset schema, ingestion, transforms, and quality checks",
        top_n=8,
    )
    ids = {link["to"][1] for link in links}
    assert "palantir-de-pipeline-foundation" in ids
    assert "palantir-de-data-quality" in ids


def test_application_developer_prompt_retrieves_ontology_and_state_knowledge():
    links = ontology.link_task_to_knowledge(
        "test-palantir-app-developer",
        "Build an application developer workflow with ontology object actions widgets variables and events",
        top_n=10,
    )
    ids = {link["to"][1] for link in links}
    assert "palantir-app-ontology-first" in ids
    assert "palantir-app-state-events" in ids


def test_agentic_fleet_prompt_retrieves_fleet_entry():
    links = ontology.link_task_to_knowledge(
        "test-engineering-fleet",
        "Use an agentic fleet with parallel agents for data engineer application ontology quality security release",
        top_n=8,
    )
    ids = {link["to"][1] for link in links}
    assert "xunia-engineering-fleet" in ids
