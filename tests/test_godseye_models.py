from godseye.models import GoDsEyeSnapshot, SubsystemState


def test_snapshot_to_dict_preserves_subsystem_state():
    subsystem = SubsystemState(
        name="global_intel",
        status="DEGRADED",
        generated_at="2026-10-07T20:00:00+00:00",
        source_count=5,
        stale=True,
        partial=True,
        provenance=["public:cisa-kev"],
        errors=["timeout"],
        payload={"benchmark": {"onlineSources": 4}},
    )
    snapshot = GoDsEyeSnapshot(
        schema="gpt-doug.godseye-snapshot.v1",
        generated_at="2026-10-07T20:00:01+00:00",
        policy={"mode": "READ_ONLY"},
        subsystems={"global_intel": subsystem},
        provenance=["public:cisa-kev"],
        uncertainty=["global_intel degraded"],
    )

    data = snapshot.to_dict()

    assert data["subsystems"]["global_intel"]["status"] == "DEGRADED"
    assert data["subsystems"]["global_intel"]["stale"] is True
    assert data["subsystems"]["global_intel"]["partial"] is True
    assert data["subsystems"]["global_intel"]["errors"] == ["timeout"]
    assert data["subsystems"]["global_intel"]["provenance"] == ["public:cisa-kev"]
    assert data["subsystems"]["global_intel"]["payload"] == {"benchmark": {"onlineSources": 4}}
    assert data["provenance"] == ["public:cisa-kev"]
    assert data["uncertainty"] == ["global_intel degraded"]
