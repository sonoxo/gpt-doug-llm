"""BioPineal ontology and patent metadata: exact, offline, fail-closed tests."""
import copy
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from pineal.innovation_nexus import (
    ONTOLOGY, PATENT_ID, OWNER, PROVENANCE, REQUIRED_EDGES, REQUIRED_NODES,
    _read_ontology, _source_record, audit, validate_graph, import_reference,
    preview, report, terminal_map, static_html, dot_graph, watch,
)
from pineal.store import PinealStore

PROJECT = Path(__file__).resolve().parents[1]


def local_store(tmp_path):
    return PinealStore(tmp_path / "memory.sqlite3")


def cli(tmp_path, *args):
    env = os.environ.copy()
    env["PINEAL_HOME"] = str(tmp_path / "pineal-local")
    return subprocess.run([sys.executable, "-m", "pineal", *args],
                          cwd=PROJECT, env=env, capture_output=True, text=True, timeout=15)


def test_fixture_is_accepted_by_existing_pineal_patent_schema():
    row = _source_record()
    assert row["publication_id"] == PATENT_ID
    assert row["publication_date"] == "2026-10-13"
    assert row["evidence_level"] == "patent_disclosure_not_scientific_validation"
    assert "user-provided" in row["source"].lower()
    assert not row["cell_tags"]


def test_assignee_is_third_party():
    data = _read_ontology()
    assert data["issued_to"] == OWNER
    assert data["patent_rights"] == "THIRD_PARTY_RIGHTS_AND_FREEDOM_TO_OPERATE_REVIEW_REQUIRED"
    assert not data["policy"]["patent_license_or_ownership_granted"]


def test_basic_graph_audit():
    r = audit()
    assert r["ontology_status"] == "VALID_LOCAL_SOURCE_GRAPH"
    assert r["nodes"] == 17
    assert r["links"] == 16
    assert not r["external_chemistry_verification"]
    assert not r["peace_impact_proven"]
    assert not r["physical_equipment_control_enabled"]


def test_typed_nodes_and_edges_all_exist():
    graph = _read_ontology()
    assert {n["id"] for n in graph["nodes"]} == REQUIRED_NODES
    assert REQUIRED_EDGES <= {(e["from"], e["to"], e["relation"]) for e in graph["edges"]}


@pytest.mark.parametrize("field", [
    "physical_hardware_build_authorized",
    "dangerous_electrolysis_operations_authorized",
    "patent_license_or_ownership_granted",
    "independent_patent_or_claim_verification_completed",
    "clinical_or_biological_effect_proven",
    "humanitarian_impact_independently_verified",
    "external_network_or_chemical_actuation",
])
def test_explicit_governance_flags_cannot_be_enabled(field):
    graph = _read_ontology()
    graph["policy"][field] = True
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_evidence_provenance_cannot_be_promoted_to_verified():
    graph = _read_ontology()
    graph["source_provenance"] = "INDEPENDENTLY_VERIFIED"
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_pineal_cannot_take_patent_ownership():
    graph = _read_ontology()
    graph["issued_to"] = "GPT-Doug-LLM"
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_cannot_merge_patent_metadata_into_peace_impact():
    graph = _read_ontology()
    graph["peace_impact_transfer"] = "VERIFIED_PEACE_OUTCOMES"
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_missing_hazard_link_is_rejected():
    graph = _read_ontology()
    graph["edges"] = [e for e in graph["edges"] if e["relation"] != "requires_risk_review"]
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_duplicate_node_fails():
    graph = _read_ontology()
    graph["nodes"].append(copy.deepcopy(graph["nodes"][0]))
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_stray_node_attribute_fails():
    graph = _read_ontology()
    graph["nodes"][0]["public_override"] = True
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_redirected_edge_fails():
    graph = _read_ontology()
    graph["edges"][0]["to"] = "unknown_service"
    with pytest.raises(ValueError):
        validate_graph(graph)


def test_duplicate_json_keys_rejected(tmp_path):
    p = tmp_path / "invalid.json"
    p.write_text('{"nodes":[],"nodes":[]}')
    with pytest.raises(ValueError, match="duplicate JSON field"):
        _read_ontology(p)


def test_symlink_file_rejected(tmp_path):
    l = tmp_path / "ont.json"
    l.symlink_to(ONTOLOGY)
    with pytest.raises(ValueError):
        _read_ontology(l)


def test_preview_never_inserts(tmp_path):
    store = local_store(tmp_path)
    p = import_reference(store)
    assert p["dry_run"] and p["database_writes"] == 0
    assert store.patent_stats()["total"] == 0


def test_integration_with_existing_sqlite_index(tmp_path):
    store = local_store(tmp_path)
    assert report(store)["index_status"] == "NOT_IMPORTED"
    result = import_reference(store, commit=True)
    assert result["local_import"]["inserted"] == 1
    assert result["existing_pineal_memory_index_updated"]
    assert store.patent_stats()["total"] == 1
    assert report(store)["index_status"] == "USER_EXCERPT_METADATA_INDEXED"


def test_import_is_idempotent(tmp_path):
    store = local_store(tmp_path)
    import_reference(store, commit=True)
    r = import_reference(store, commit=True)
    assert r["local_import"]["inserted"] == 0
    assert r["local_import"]["skipped"] == 1
    assert store.patent_stats()["total"] == 1


def test_bibliographic_context_search_after_import(tmp_path):
    store = local_store(tmp_path)
    import_reference(store, commit=True)
    matches = store.search_patents("lithium",limit=10)
    assert len(matches) == 1
    assert matches[0]["publication_id"] == PATENT_ID


def test_sqlite_audit_chain_after_import(tmp_path):
    store=local_store(tmp_path)
    import_reference(store,commit=True)
    a=store.verify_audit()
    assert a["ok"]
    assert a["checked"] >= 1


def test_limited_local_keyword_groups_not_global(tmp_path):
    store=local_store(tmp_path)
    import_reference(store,commit=True)
    data=report(store)
    assert data["local_patent_metadata_total"] == 1
    assert data["keyword_sample_size"] == 1
    assert data["keyword_hits_within_last_20_local_records"]["lithium"] == 1
    assert data["network_fetches"] == 0
    assert not data["official_uspto_record_verified"]


def test_report_digest_deterministic(tmp_path):
    store=local_store(tmp_path)
    a=report(store)
    b=report(store)
    assert a==b
    assert len(a["report_sha256"])==64


def test_terminal_live_state_truthfully_changes_after_import(tmp_path):
    store=local_store(tmp_path)
    before=terminal_map(report(store))
    assert "NOT_IMPORTED" in before
    assert "PROVIDER REQUESTS: 0" in before
    import_reference(store,commit=True)
    after=terminal_map(report(store))
    assert "USER_EXCERPT_METADATA_INDEXED" in after


def test_zero_network_requests(monkeypatch,tmp_path):
    def bad(*_args,**_kwargs):
        raise AssertionError("No HTTPS requests permitted for offline BioPineal nexus")
    import urllib.request
    monkeypatch.setattr(urllib.request,"urlopen",bad)
    store=local_store(tmp_path)
    assert audit()["ontology_status"]=="VALID_LOCAL_SOURCE_GRAPH"
    assert report(store)["network_fetches"]==0
    import_reference(store,commit=True)
    assert report(store)["local_patent_metadata_total"]==1


def test_hazard_safety_not_actionable(tmp_path):
    store=local_store(tmp_path)
    data=report(store)
    assert data["real_world_device_built_or_controlled"] is False
    assert len(data["hazard_reviews_required"])==3
    assert data["patent_counsel_review_required"]


def test_html_self_contained_and_safe(tmp_path):
    data=report(local_store(tmp_path))
    output=static_html(data)
    assert "<!doctype html>" in output
    assert "default-src 'none'" in output
    assert "<script" not in output
    assert "<iframe" not in output
    assert "PolyPlus Battery Company" in output
    assert "NO" in output.upper()


def test_dot_exports_typed_links():
    graph=dot_graph()
    assert graph.startswith("digraph BioPinealNexus")
    assert '"publication" -> "assignee"' in graph
    assert '"hydrogen_gas" -> "flammability"' in graph
    assert '"chlorine_gas" -> "toxicity"' in graph


def test_watch_bounded(tmp_path,capsys):
    store=local_store(tmp_path)
    assert watch(store,frames=2,interval=0.2)==0
    out=capsys.readouterr().out
    assert out.count("BIOPINEAL EVIDENCE NEXUS")==2


@pytest.mark.parametrize("frames,interval",[(0,0.2),(121,0.2),(1,0),(1,11)])
def test_unbounded_or_invalid_watch_refused(tmp_path,frames,interval):
    with pytest.raises(ValueError):
        watch(local_store(tmp_path),frames=frames,interval=interval)


def test_cli_status_via_clean_mac_environment(tmp_path):
    result=cli(tmp_path,"nexus","status")
    assert result.returncode==0,result.stderr
    payload=json.loads(result.stdout)
    assert payload["index_status"]=="NOT_IMPORTED"
    assert payload["official_uspto_record_verified"] is False


def test_cli_ontology_audit(tmp_path):
    r=cli(tmp_path,"nexus","audit")
    assert r.returncode==0,r.stderr
    assert json.loads(r.stdout)["ontology_status"]=="VALID_LOCAL_SOURCE_GRAPH"


def test_cli_import_requires_commit(tmp_path):
    before=cli(tmp_path,"nexus","import-reference")
    assert before.returncode==0,before.stderr
    assert json.loads(before.stdout)["dry_run"]
    assert json.loads(cli(tmp_path,"nexus","status").stdout)["local_patent_metadata_total"]==0
    actual=cli(tmp_path,"nexus","import-reference","--commit")
    assert actual.returncode==0,actual.stderr
    assert json.loads(actual.stdout)["local_import"]["inserted"]==1
    assert json.loads(cli(tmp_path,"nexus","status").stdout)["index_status"]=="USER_EXCERPT_METADATA_INDEXED"


def test_cli_terminal_graph_and_html(tmp_path):
    a=cli(tmp_path,"nexus","map")
    b=cli(tmp_path,"nexus","html")
    c=cli(tmp_path,"nexus","dot")
    assert a.returncode==b.returncode==c.returncode==0
    assert "USER-SUPPLIED" in a.stdout
    assert "BioPineal" in b.stdout
    assert "digraph BioPinealNexus" in c.stdout


def test_cli_context_integrates_imported_record(tmp_path):
    cli(tmp_path,"nexus","import-reference","--commit")
    c=cli(tmp_path,"context","lithium")
    assert c.returncode==0,c.stderr
    payload=json.loads(c.stdout)
    assert any(x["publication_id"]==PATENT_ID for x in payload["patent_publications"])


def test_cli_watch_mode_stops(tmp_path):
    result=cli(tmp_path,"nexus","watch","--frames","2","--interval","0.2")
    assert result.returncode==0,result.stderr
    assert result.stdout.count("BIOPINEAL EVIDENCE NEXUS")==2
