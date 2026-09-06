from kraken_jutsu.ontology import OntologyJudge


def test_high_priority_judgment():
    judgment = OntologyJudge().judge(
        cve="CVE-2099-0001",
        kev_record={"cveID": "CVE-2099-0001", "knownRansomwareCampaignUse": "Known"},
        ssvc={"Exploitation": "active", "Automatable": "yes", "Technical Impact": "total"},
        attack_techniques=["T1190"],
        oscal_controls=["RA-5", "SI-4"],
    )
    assert judgment.priority == 10
    assert judgment.verdict == "CONTAIN_OR_PATCH_NOW"
    assert judgment.recommended_mode == "od"


def test_osint_is_evidence_not_truth():
    judgment = OntologyJudge().judge(osint_evidence=[{"provider": "osint-industries-export"}])
    assert judgment.priority == 1
    assert judgment.verdict == "MONITOR"
    assert "OSINT evidence" in judgment.provenance
