import pytest
from va3lm.federal_intel import (
    federal_intel_entity,
    federal_intel_manifest,
    verified_github_sources,
)


def test_manifest_contains_requested_agencies_and_programs():
    manifest = federal_intel_manifest()
    assert manifest["mode"] == "PUBLIC_OSINT_ONLY"
    assert [item["id"] for item in manifest["entities"]] == ["cia", "nsa", "nro", "ngp", "gdip"]


def test_only_verified_official_github_sources_are_promoted():
    verified = verified_github_sources()
    ids = {item["id"] for item in verified}
    assert ids == {"nsa", "ngp"}
    nsa = next(item for item in verified if item["id"] == "nsa")
    assert "https://github.com/NationalSecurityAgency" in nsa["organizations"]
    ngp = next(item for item in verified if item["id"] == "ngp")
    assert ngp["organizations"] == ["https://github.com/ngageoint"]


def test_unverified_agency_github_orgs_are_not_invented():
    for entity_id in ("cia", "nro", "gdip"):
        entity = federal_intel_entity(entity_id)
        assert entity["officialGitHub"]["status"] == "NO_VERIFIED_OFFICIAL_ORG"
        assert entity["officialGitHub"]["organizations"] == []


def test_programs_are_not_mislabeled_as_agencies():
    assert federal_intel_entity("ngp")["entityType"] == "program"
    assert federal_intel_entity("gdip")["entityType"] == "program"
    assert "National Geospatial-Intelligence Agency" in federal_intel_entity("ngp")["owner"]
    assert "Defense Intelligence Agency" in federal_intel_entity("gdip")["owner"]


def test_unknown_entity_rejected():
    with pytest.raises(KeyError, match="unknown federal intel entity"):
        federal_intel_entity("unknown")


def test_catalog_has_explicit_public_source_boundaries():
    boundaries = federal_intel_manifest()["boundaries"]
    assert any("publicly released" in item for item in boundaries)
    assert any("no classified" in item for item in boundaries)
    assert any("no communications interception" in item for item in boundaries)
    assert any("no covert person tracking" in item for item in boundaries)
