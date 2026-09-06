from kraken_jutsu.narrative_intel import (
    ClaimStatus,
    ClaimVerifier,
    Evidence,
    EvidenceKind,
    ThreatClaim,
    build_defensive_brief,
)


def _claim(evidence):
    return ThreatClaim(
        claim_id="demo-1",
        event="reported disruption",
        narrative="actor claims a service was compromised",
        actor="example-actor",
        motivations=["visibility"],
        targets=["example-service"],
        ttps=["T1498"],
        observables=["availability anomaly"],
        impacts=["possible service degradation"],
        defenses=["rate limiting", "telemetry correlation"],
        evidence=evidence,
    )


def test_actor_claim_alone_is_not_compromise():
    result = ClaimVerifier().verify(
        _claim(
            [
                Evidence(
                    source_id="actor-channel",
                    kind=EvidenceKind.ACTOR_CLAIM,
                    reliability=0.9,
                    independent=False,
                )
            ]
        )
    )
    assert result.status is ClaimStatus.CLAIMED
    assert result.confidence < 0.40


def test_two_independent_reports_can_corroborate_but_not_verify():
    result = ClaimVerifier().verify(
        _claim(
            [
                Evidence("report-a", EvidenceKind.NEWS_REPORT, 0.9),
                Evidence("report-b", EvidenceKind.THIRD_PARTY_REPORT, 0.9),
            ]
        )
    )
    assert result.status is ClaimStatus.CORROBORATED
    assert result.authoritative_sources == 0
    assert result.technical_sources == 0


def test_verified_requires_authoritative_and_technical_corroboration():
    result = ClaimVerifier().verify(
        _claim(
            [
                Evidence("victim", EvidenceKind.VICTIM_STATEMENT, 0.95),
                Evidence("sensor", EvidenceKind.TELEMETRY, 0.95),
                Evidence("cert", EvidenceKind.GOVERNMENT_ADVISORY, 0.85),
            ]
        )
    )
    assert result.status is ClaimStatus.VERIFIED_INCIDENT
    assert result.confidence >= 0.70


def test_authoritative_contradiction_can_dispute_claim():
    result = ClaimVerifier().verify(
        _claim(
            [
                Evidence("report-a", EvidenceKind.NEWS_REPORT, 0.8),
                Evidence(
                    "victim",
                    EvidenceKind.VICTIM_STATEMENT,
                    0.95,
                    supports=False,
                ),
            ]
        )
    )
    assert result.status is ClaimStatus.DISPUTED


def test_ontology_chain_and_defensive_brief():
    claim = _claim(
        [
            Evidence("victim", EvidenceKind.VICTIM_STATEMENT, 0.95),
            Evidence("sensor", EvidenceKind.TELEMETRY, 0.95),
        ]
    )
    result = ClaimVerifier().verify(claim)
    assert list(result.ontology) == [
        "event",
        "narrative",
        "actor",
        "motivation",
        "target",
        "ttp",
        "observable",
        "impact",
        "defense",
        "confidence",
        "claim_status",
    ]
    brief = build_defensive_brief(claim, result)
    assert brief["posture"] in {
        "MONITOR_AND_CORROBORATE",
        "PRIORITY_INVESTIGATION",
        "DEFENSIVE_RESPONSE",
        "HOLD_ATTRIBUTION",
        "CLOSE_OR_ARCHIVE",
    }
    assert all("exploit" not in action.lower() for action in brief["recommended_actions"])
