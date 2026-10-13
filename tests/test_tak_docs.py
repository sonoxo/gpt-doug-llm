from __future__ import annotations

import json
from pathlib import Path
import pytest

from tak_geo.cli import main
from tak_geo.docs_registry import (
    DOCS, inventory_local_documents, local_text_search,
    documentation_graph, public_registry, validate_document_refs,
    write_docs_portal,
)


def test_catalog_is_curated_and_access_restricted():
    refs = public_registry()
    assert refs["authority"] == "PUBLIC_REFERENCES_ONLY"
    assert refs["login_required_references"] >= 3
    assert refs["public_full_text_mirrored"] is False
    assert refs["authenticated_library_scraped"] is False
    assert refs["sdk_installed"] is False
    assert refs["tak_server_connected"] is False
    assert refs["document_count"] == len(DOCS)
    assert len(set(d["id"] for d in DOCS)) == len(DOCS)


def test_pipeline_requirements_are_honest():
    report = public_registry()
    pipeline = report["third_party_pipeline"]
    assert pipeline["archive_root"] == "GPTDougGeoAtlas/"
    assert pipeline["build_target"] == "assembleCivRelease"
    assert pipeline["source_package_checks"] == "PASSED"
    assert pipeline["authenticated_release_compilation"] == "NOT_RUN"
    assert pipeline["tak_gov_upload"] == "NOT_SUBMITTED"
    assert pipeline["signed_apk"] == "NOT_AVAILABLE"
    assert pipeline["takdev_dependency_from_supplied_text_for_atak_4_2_plus"] == "2.+"
    assert pipeline["upstream_atak_5_6_template_dependency"] == "3.+"
    assert pipeline["dependency_version_discrepancy"].startswith("UNRESOLVED")
    doc = next(x for x in report["records"] if x["id"] == "tak-thirdparty-pipeline")
    assert doc["access"] == "login_required"
    assert doc["status"] == "access_required"
    assert "sonoxo/atak-civ/pull/1" in pipeline["source_pr"]


def test_provenance_graph_never_claims_live_networks():
    index = public_registry()
    graph = documentation_graph(index)
    assert graph["runtime_connections"] == 0
    assert graph["scraped_authenticated_content"] is False
    assert graph["docs_registry_sha256"] == index["registry_sha256"]
    assert len([node for node in graph["nodes"] if node["type"] == "DocumentReference"]) == len(DOCS)
    assert len(graph["edges"]) == len(DOCS) * 3


def test_invalid_and_duplicate_links_fail():
    record = dict(DOCS[0])
    record["url"] = "http://localhost/secret"
    with pytest.raises(ValueError):
        validate_document_refs((record,))
    with pytest.raises(ValueError):
        validate_document_refs((DOCS[0], DOCS[0]))


def test_docs_portal_is_offline_and_links_real_fork(tmp_path):
    result = write_docs_portal(tmp_path / "portal")
    assert result["authenticated_library_scraped"] is False
    page = (tmp_path / "portal/docs.html").read_text()
    assert "const DATA = {" in page
    assert "TAK Third Party Pipeline release readiness" in page
    assert "github.com/sonoxo/atak-civ/pull/1" in page
    assert "tak.gov/user_builds/agreement" in page
    assert (tmp_path / "portal/docs-registry.json").exists()
    assert (tmp_path / "portal/docs-ontology.json").exists()
    with pytest.raises(ValueError, match="--force"):
        write_docs_portal(tmp_path / "portal")
    write_docs_portal(tmp_path / "portal", force=True)


def test_local_docs_are_not_uploaded_and_can_be_read_in_place(tmp_path):
    folder = tmp_path / "confidential"
    folder.mkdir()
    (folder / "manual.md").write_text("The developer must verify assembleCivRelease.\nPrivate local notes.\n")
    (folder / "notes.pdf").write_bytes(b"%PDF-1.2\n%Example placeholder bytes")
    inventory = inventory_local_documents(folder)
    assert inventory["files"] == 2
    assert inventory["metadata_only"] is True
    assert inventory["files_uploaded"] == 0
    assert inventory["network_actions"] == 0
    assert all("relative_path" not in record for record in inventory["records"])
    report = local_text_search(folder, "assembleCivRelease")
    assert len(report["results"]) == 1
    assert report["results"][0]["line"] == 1
    assert report["persisted_index"] is False


def test_reject_symlink_root(tmp_path):
    folder = tmp_path / "docs"
    folder.mkdir()
    alias = tmp_path / "alias"
    alias.symlink_to(folder, target_is_directory=True)
    with pytest.raises(ValueError, match="nonsymlink"):
        inventory_local_documents(alias)
    with pytest.raises(ValueError, match="nonsymlink"):
        local_text_search(alias, "abc")


def test_cli_status_build_and_local_inventory(tmp_path, capsys):
    assert main(["docs-status"]) == 0
    status = json.loads(capsys.readouterr().out)
    assert status["restricted_documents_retrieved"] is False
    folder = tmp_path / "artifacts"
    assert main(["docs-build", "--output", str(folder)]) == 0
    assert (folder / "docs.html").exists()
    capsys.readouterr()
    local = tmp_path / "manuals"
    local.mkdir()
    (local / "readme.txt").write_text("TAK source archive.")
    assert main(["docs-inventory", "--local-root", str(local)]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["network_actions"] == 0
