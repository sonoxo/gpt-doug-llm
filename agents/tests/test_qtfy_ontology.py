from agents.qtfy_advisory_intel import build_qtfy_defensive_plan


def test_qtfy_ontology_contains_source_grounded_entities():
    plan = build_qtfy_defensive_plan()
    ontology = plan["ontology"]

    object_types = set(ontology["objectTypes"])
    assert {"Organization", "ThreatTool", "Vulnerability", "CampaignEvent"} <= object_types

    objects = ontology["objects"]
    refs = {(item["objectType"], item["id"]) for item in objects}
    assert ("ThreatTool", "qscan") in refs
    assert ("ThreatTool", "qtrouter") in refs
    assert ("Vulnerability", "CVE-2024-24919") in refs
    assert ("CampaignEvent", "evt-2024-05-qscan") in refs
    assert ("Organization", "nanjing-xinjiuwei") in refs

    links = ontology["links"]
    assert any(
        link["linkType"] == "EventUsesTool"
        and link["from"] == "CampaignEvent:evt-2024-05-qscan"
        and link["to"] == "ThreatTool:qscan"
        for link in links
    )
    assert any(
        link["linkType"] == "EventReferencesVulnerability"
        and link["from"] == "CampaignEvent:evt-2024-05-qscan"
        and link["to"] == "Vulnerability:CVE-2024-24919"
        for link in links
    )

    assert ontology["guardrails"]["automaticBlocking"] is False
    assert ontology["guardrails"]["externalThirdPartyAction"] is False
    assert ontology["guardrails"]["attributionHandling"] == "PRESERVE_SOURCE_CLAIM_NATURE"
    assert plan["sourcePack"] == "intel/qtfy/JCSA-20260826-01.json"
