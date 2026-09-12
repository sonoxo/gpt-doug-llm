import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intel/sources/uspto-palantir-query-2026-09-12.json"
PAGE2 = ROOT / "intel/sources/uspto-palantir-query-2026-09-12-page2.json"
ONTOLOGY = ROOT / "safety-shield/agents/knowledge/gpt-doug-uspto-patent-intel-v1.json"
BRIEF = ROOT / "intel/briefings/2026-09-12-uspto-palantir-patent-landscape.md"

EXPECTED_EXACT = {
    "US-20260119865-A1",
    "US-20260093834-A1",
    "US-12591555-B2",
    "US-12585804-B2",
    "US-20260080157-A1",
    "US-12579156-B2",
}


def load_cli():
    spec = importlib.util.spec_from_file_location(
        "zyrapalantir_patent_intel", ROOT / "scripts/zyrapalantir_patent_intel.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uspto_search_sources_preserve_provenance_and_uncertainty():
    for path in (SOURCE, PAGE2):
        source = json.loads(path.read_text(encoding="utf-8"))
        assert source["authority"] == "United States Patent and Trademark Office"
        assert source["query"] == "palantir"
        assert source["reported_result_count"] == 3544
        assert source["confidence"]["assignee_or_ownership_attribution"] == "NOT_ESTABLISHED_FROM_THIS_SEARCH_RESULT"
        assert source["controls"]["treat_search_hit_as_confirmed_assignee"] is False
        assert source["controls"]["claim_freedom_to_operate"] is False


def test_search_records_are_unique_and_include_core_watch_areas():
    cli = load_cli()
    source = cli.load_source()
    records = source["records"]
    numbers = [record["document_number"] for record in records]
    assert len(numbers) == len(set(numbers))
    assert "US-20260236234-A1" in numbers
    assert "US-12717753-B2" in numbers
    assert "US-20260252432-A1" in numbers
    assert "US-20260187067-A1" in numbers
    assert "US-20260161750-A1" in numbers
    themes = {theme for record in records for theme in record["themes"]}
    assert {"ontology", "software-supply-chain", "incident-analysis", "ai-governance"}.issubset(themes)


def test_aggregate_spans_captured_pages_and_exact_documents():
    cli = load_cli()
    source = cli.load_source()
    assert source["reported_pages"] == ["1 of 71", "2 of 71"]
    assert len(source["source_ids"]) == 2
    assert len(source["records"]) >= 60
    exact_numbers = {record["document_number"] for record in source["attributed_records"]}
    assert EXPECTED_EXACT.issubset(exact_numbers)


def test_exact_front_page_sources_are_palantir_attributed_and_review_gated():
    cli = load_cli()
    exact = cli.load_attributed_sources()
    assert EXPECTED_EXACT.issubset({record["document_number"] for record in exact})
    for record in exact:
        applicant = record.get("applicant", {})
        assignee = record.get("assignee", {})
        if applicant:
            assert applicant["name"] == "Palantir Technologies Inc."
            assert applicant["confidence"] == "HIGH_FROM_DOCUMENT_FRONT_PAGE"
        if assignee:
            assert assignee["name"] == "Palantir Technologies Inc."
            assert assignee["confidence"] == "HIGH_FROM_DOCUMENT_FRONT_PAGE"
        assert record["controls"]["claim_freedom_to_operate"] is False
        assert record["controls"]["claim_non_infringement"] is False


def test_patent_ontology_contains_exact_attributions_and_architecture_watches():
    ontology = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    assert ontology["ontology"] == "GPT_DOUG_USPTO_PATENT_INTEL_V1"
    exact_numbers = {item["document_number"] for item in ontology["high_confidence_attributions"]}
    assert EXPECTED_EXACT.issubset(exact_numbers)
    patterns = {item["name"] for item in ontology["architecture_watch_patterns"]}
    assert {
        "eligibility-engine-generative-ai-criteria-evaluation",
        "shared-infrastructure-data-security-governance",
        "live-data-migration-and-consistency",
        "shared-infrastructure-object-permission-governance",
        "generative-ai-evidence-routed-document-workflow",
        "linked-dataset-interactive-visualization",
    }.issubset(patterns)
    blocked = set(ontology["governed_actions"]["BLOCK"])
    review = set(ontology["governed_actions"]["REVIEW"])
    assert "claim_freedom_to_operate_automatically" in blocked
    assert "claim_level_patent_analysis" in review


def test_brief_and_cli_are_wired():
    assert BRIEF.exists()
    text = BRIEF.read_text(encoding="utf-8")
    assert "USPTO PALANTIR-QUERY TECHNOLOGY LANDSCAPE" in text
    assert "US-20260093834-A1" in text
    assert "US-12591555-B2" in text
    assert "US-20260080157-A1" in text
    assert "US-12579156-B2" in text
    cli = load_cli()
    assert cli.doctor() == 0


def test_shell_dispatch_exposes_patent_intel_command():
    shell = (ROOT / "scripts/zyrapalantir").read_text(encoding="utf-8")
    assert "patent-intel" in shell
    assert "zyrapalantir_patent_intel.py" in shell
