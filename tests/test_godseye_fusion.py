from godseye.fusion import collect_snapshot, snapshot_sources


class FakeWarHawk:
    def status(self):
        return {
            "codename": "US-01-GoDsWarHawk",
            "mode": "DEFENSIVE_SOFTWARE_SWARM",
            "workers": [{"id": "guardian"}],
        }


def _brain():
    return {"readiness": {"core_ready": True, "model_ready": True}, "mode": "MATRIX_COMMAND_CENTER"}


def _intel(*, force=False):
    return {
        "generatedAt": "2026-10-07T20:00:00+00:00",
        "benchmark": {"sourceCount": 5, "onlineSources": 5, "degradedSources": 0},
        "sources": [{"id": "cisa-kev", "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog"}],
    }


def _compliance(settings):
    assert settings == "settings"
    return {"schema": "gpt-doug.global-posture.v1", "counts": {"EXTERNAL": 3}}


def _bio(*, force=False):
    return {
        "generatedAt": "2026-10-07T20:00:00+00:00",
        "summary": {"sourceCount": 5, "onlineSources": 5, "degradedSources": 0},
        "sources": [{"id": "ensembl-rest", "url": "https://rest.ensembl.org/info/rest"}],
    }


def _zyra():
    return {
        "schema": "gpt-doug.zyra-status.v1",
        "status": "ONLINE",
        "sourceCount": 1,
        "logicalAgentCount": 100,
        "provenance": ["safety-shield/ontology/zyra-mss-v1.json"],
    }


def _planet():
    return {
        "schema": "gpt-doug.planetary-status.v1",
        "status": "ONLINE",
        "sourceCount": 2,
        "sources": [{"id": "public-space", "mode": "PUBLIC"}],
        "errors": [],
        "partial": False,
    }


def test_collect_snapshot_normalizes_all_subsystems():
    snapshot = collect_snapshot(
        settings="settings",
        brain_status_fn=_brain,
        warhawk_factory=FakeWarHawk,
        intel_fn=_intel,
        compliance_fn=_compliance,
        bio_fn=_bio,
        planetary_fn=_planet,
        zyra_fn=_zyra,
    )

    assert set(snapshot.subsystems) == {
        "brain",
        "warhawk",
        "global_intel",
        "global_compliance",
        "biofusion",
        "zyra",
        "planetary",
    }
    assert all(state.status == "ONLINE" for state in snapshot.subsystems.values())
    assert snapshot.subsystems["global_intel"].source_count == 5
    assert snapshot.subsystems["biofusion"].source_count == 5
    assert snapshot.subsystems["planetary"].source_count == 2
    assert snapshot.subsystems["zyra"].source_count == 1
    assert snapshot.policy["mode"] == "READ_ONLY_FUSION"
    assert "safety-shield/ontology/zyra-mss-v1.json" in snapshot.provenance


def test_timeout_degrades_only_one_subsystem():
    def broken(*, force=False):
        raise TimeoutError("intel timeout")

    snapshot = collect_snapshot(
        settings="settings",
        brain_status_fn=_brain,
        warhawk_factory=FakeWarHawk,
        intel_fn=broken,
        compliance_fn=_compliance,
        bio_fn=_bio,
        planetary_fn=_planet,
        zyra_fn=_zyra,
    )

    assert snapshot.subsystems["global_intel"].status == "DEGRADED"
    assert snapshot.subsystems["global_intel"].partial is True
    assert "TimeoutError" in snapshot.subsystems["global_intel"].errors[0]
    assert snapshot.subsystems["brain"].status == "ONLINE"
    assert any("global_intel" in item for item in snapshot.uncertainty)


def test_malformed_payload_degrades_only_that_subsystem():
    snapshot = collect_snapshot(
        settings="settings",
        brain_status_fn=lambda: "not-a-dict",
        warhawk_factory=FakeWarHawk,
        intel_fn=_intel,
        compliance_fn=_compliance,
        bio_fn=_bio,
        planetary_fn=_planet,
        zyra_fn=_zyra,
    )

    assert snapshot.subsystems["brain"].status == "DEGRADED"
    assert snapshot.subsystems["brain"].partial is True
    assert snapshot.subsystems["global_intel"].status == "ONLINE"


def test_snapshot_sources_flattens_source_provenance():
    snapshot = collect_snapshot(
        settings="settings",
        brain_status_fn=_brain,
        warhawk_factory=FakeWarHawk,
        intel_fn=_intel,
        compliance_fn=_compliance,
        bio_fn=_bio,
        planetary_fn=_planet,
        zyra_fn=_zyra,
    )
    sources = snapshot_sources(snapshot)
    assert any(item["subsystem"] == "global_intel" and item["id"] == "cisa-kev" for item in sources)
    assert any(item["subsystem"] == "biofusion" and item["id"] == "ensembl-rest" for item in sources)
