import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intel/sources/uspto-palantir-query-2026-09-12.json"
PAGE2 = ROOT / "intel/sources/uspto-palantir-query-2026-09-12-page2.json"
ATTRIBUTED = ROOT / "intel/sources/uspto-palantir-attributed-US-20260119865-A1.json"
ONTOLOGY = ROOT / "safety-shield/agents/knowledge/gpt-doug-uspto-patent-intel-v1.json"
BRIEF = ROOT / "intel/briefings/2026-09-12-uspto-palantir-patent-landscape.md"


def load_cli():
    spec = importlib.util.spec_from_file_location("zyrapalantir_patent_intel", ROOT / "scripts/zyrapalantir_patent_intel.py")
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


def test_exact_publication_supports_document_level_applicant_attribution():
    source = json.loads(ATTRIBUTED.read_text(encoding="utf-8"))
    assert source["document_number"] == "US-20260119865-A1"
    assert source["publication_date"] == "2026-04-30"
    assert source["applicant"]["name"] == "Palantir Technologies Inc."
    assert source["applicant"]["confidence"] == "HIGH_FROM_DOCUMENT_FRONT_PAGE"
    assert source["controls"]["treat_front_page_applicant_field_as_document_attribution"] is True
    assert source["controls"]["treat_applicant_attribution_as_current_ownership_or_enforceability_proof"] is False
    assert source["controls"]["claim_freedom_to_operate"] is False


def test_selected_records_are_unique_and_include_core_watch_areas():
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
    assert "US-12652299-B1" in numbers
    assert "US-20260140843-A1" in numbers
    themes = {theme for record in cli.all_records(source) for theme in record["themes"]}
    assert {
        "ontology",
        "software-supply-chain",
        "incident-analysis",
        "ai-governance",
        "geospatial",
        "network-security",
        "access-control",
        "audit",
        "eligibility-engine",
        "criteria-evaluation",
    }.issubset(themes)


def test_aggregate_spans_both_captured_pages_and_exact_attribution():
    cli = load_cli()
    source = cli.load_source()
    assert source["reported_pages"] == ["1 of 71", "2 of 71"]
    assert len(source["source_ids"]) == 2
    assert len(source["records"]) >= 60
    assert len(source["attributed_records"]) == 1
    exact = source["attributed_records"][0]
    assert exact["document_number"] == "US-20260119865-A1"
    assert exact["applicant"] == "Palantir Technologies Inc."


def test_patent_ontology_has_eligibility_watch_and_review_gates():
    ontology = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    assert ontology["ontology"] == "GPT_DOUG_USPTO_PATENT_INTEL_V1"
    assert ontology["source_id"] == "uspto-palantir-query-2026-09-12"
    assert "eligibility_engine_and_ai_criteria_evaluation" in ontology["watch_themes"]
    assert ontology["high_confidence_attributions"][0]["document_number"] == "US-20260119865-A1"
    assert ontology["high_confidence_attributions"][0]["applicant_name"] == "Palantir Technologies Inc."
    patterns = ontology["architecture_watch_patterns"]
    assert any(p["name"] == "eligibility-engine-generative-ai-criteria-evaluation" for p in patterns)
    pattern = next(p for p in patterns if p["name"] == "eligibility-engine-generative-ai-criteria-evaluation")
    assert "GAI Logic" in pattern["diagram_components"]
    assert "human review gate for consequential decisions" in pattern["gpt_doug_mapping"]

    blocked = set(ontology["governed_actions"]["BLOCK"])
    review = set(ontology["governed_actions"]["REVIEW"])
    assert "treat_search_hit_as_proof_of_patent_ownership" in blocked
    assert "treat_front_page_applicant_attribution_as_current_ownership_or_enforceability_proof" in blocked
    assert "claim_freedom_to_operate_automatically" in blocked
    assert "claim_level_patent_analysis" in review
    assert "freedom_to_operate_assessment" in review


def test_brief_and_cli_are_wired():
    assert BRIEF.exists()
    text = BRIEF.read_text(encoding="utf-8")
    assert "USPTO PALANTIR-QUERY TECHNOLOGY LANDSCAPE" in text
    assert "US-20260119865-A1" in text
    assert "eligibility-engine" in text.lower()
    assert "zyrapalantir patent-intel summary" in text
    cli = load_cli()
    source = cli.load_source()
    assert source["query"] == "palantir"
    assert cli.doctor() == 0


def test_shell_dispatch_exposes_patent_intel_command():
    shell = (ROOT / "scripts/zyrapalantir").read_text(encoding="utf-8")
    assert "patent-intel" in shell
    assert "zyrapalantir_patent_intel.py" in shell
