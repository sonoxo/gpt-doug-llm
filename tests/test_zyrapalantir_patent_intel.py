import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "intel/sources/uspto-palantir-query-2026-09-12.json"
ONTOLOGY = ROOT / "safety-shield/agents/knowledge/gpt-doug-uspto-patent-intel-v1.json"
BRIEF = ROOT / "intel/briefings/2026-09-12-uspto-palantir-patent-landscape.md"


def load_cli():
    spec = importlib.util.spec_from_file_location("zyrapalantir_patent_intel", ROOT / "scripts/zyrapalantir_patent_intel.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_uspto_source_preserves_provenance_and_uncertainty():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    assert source["authority"] == "United States Patent and Trademark Office"
    assert source["query"] == "palantir"
    assert source["reported_result_count"] == 3544
    assert source["confidence"]["assignee_or_ownership_attribution"] == "NOT_ESTABLISHED_FROM_THIS_SEARCH_RESULT"
    assert source["controls"]["treat_search_hit_as_confirmed_assignee"] is False
    assert source["controls"]["claim_freedom_to_operate"] is False


def test_selected_records_are_unique_and_include_core_watch_areas():
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = source["records"]
    numbers = [record["document_number"] for record in records]
    assert len(numbers) == len(set(numbers))
    assert "US-20260236234-A1" in numbers
    assert "US-12717753-B2" in numbers
    assert "US-20260252432-A1" in numbers
    themes = {theme for record in records for theme in record["themes"]}
    assert {"ontology", "software-supply-chain", "incident-analysis", "ai-governance"}.issubset(themes)


def test_patent_ontology_is_research_only_and_review_gated():
    ontology = json.loads(ONTOLOGY.read_text(encoding="utf-8"))
    assert ontology["ontology"] == "GPT_DOUG_USPTO_PATENT_INTEL_V1"
    assert ontology["source_id"] == "uspto-palantir-query-2026-09-12"
    blocked = set(ontology["governed_actions"]["BLOCK"])
    review = set(ontology["governed_actions"]["REVIEW"])
    assert "treat_search_hit_as_proof_of_patent_ownership" in blocked
    assert "claim_freedom_to_operate_automatically" in blocked
    assert "claim_level_patent_analysis" in review
    assert "freedom_to_operate_assessment" in review


def test_brief_and_cli_are_wired():
    assert BRIEF.exists()
    text = BRIEF.read_text(encoding="utf-8")
    assert "USPTO PALANTIR-QUERY TECHNOLOGY LANDSCAPE" in text
    assert "zyrapalantir patent-intel summary" in text
    cli = load_cli()
    source = cli.load_source()
    assert source["query"] == "palantir"
    assert cli.doctor() == 0


def test_shell_dispatch_exposes_patent_intel_command():
    shell = (ROOT / "scripts/zyrapalantir").read_text(encoding="utf-8")
    assert "patent-intel" in shell
    assert "zyrapalantir_patent_intel.py" in shell
