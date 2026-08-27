from agents.federal_threat_intel import build_taxii_collection_config, normalize_stix_bundle


def test_taxii_config_is_read_only_and_human_reviewed():
    config = build_taxii_collection_config("https://example.gov/taxii2", "collection-1")
    assert config["operation"] == "READ_ONLY_INGEST"
    assert config["automaticBlocking"] is False
    assert config["humanReviewRequired"] is True


def test_stix_bundle_normalizes_into_defensive_ontology_bindings():
    bundle = {
        "type": "bundle",
        "id": "bundle--1",
        "objects": [
            {
                "type": "indicator",
                "id": "indicator--1",
                "name": "example defensive lead",
                "pattern": "[ipv4-addr:value = '203.0.113.5']",
                "pattern_type": "stix",
                "confidence": 80,
            },
            {
                "type": "attack-pattern",
                "id": "attack-pattern--1",
                "name": "Exploit Public-Facing Application",
                "external_references": [{"source_name": "mitre-attack", "external_id": "T1190"}],
            },
        ],
    }
    result = normalize_stix_bundle(bundle)
    assert result["indicators"][0]["reviewState"] == "UNDER_REVIEW"
    assert result["indicators"][0]["automaticBlocking"] is False
    assert result["attackPatterns"][0]["externalId"] == "T1190"
    assert result["ontologyBindings"]["incidentObjectType"] == "Incident"
    assert result["guardrails"]["externalThirdPartyAction"] is False
