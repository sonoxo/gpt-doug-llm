from __future__ import annotations

import pytest

from zyrapalantir import (
    DigitalTwinAsset,
    Domain,
    SafetyViolation,
    ZyraPalantir,
    ZyraPalantirBackbone,
)


class FakeFoundry:
    def __init__(self) -> None:
        self.apply_action_called = False

    def status(self) -> dict:
        return {"configured": True, "host": "example.test", "writes_enabled": False}

    def list_object_types(self, ontology: str) -> dict:
        return {"ontology": ontology, "data": [{"apiName": "ZyraDigitalTwinAsset"}]}

    def list_objects(self, ontology: str, object_type: str, page_size=100, select=None) -> dict:
        return {
            "ontology": ontology,
            "object_type": object_type,
            "page_size": page_size,
            "select": select,
            "data": [],
        }

    def search_objects(self, ontology: str, object_type: str, search_body: dict) -> dict:
        return {
            "ontology": ontology,
            "object_type": object_type,
            "search": search_body,
            "data": [],
        }

    def apply_action(self, *args, **kwargs):  # pragma: no cover - must never execute
        self.apply_action_called = True
        raise AssertionError("ZYRAPALANTIR backbone must not execute Foundry actions")


def test_backbone_reports_simulation_only_and_no_actuation() -> None:
    backbone = ZyraPalantirBackbone(
        twin=ZyraPalantir("test"),
        foundry=FakeFoundry(),
        ontology="zyra-sim",
    )

    status = backbone.status()

    assert status["backbone"]["mode"] == "PALANTIR_BACKBONE_SIMULATION_ONLY"
    assert status["backbone"]["writes_from_backbone"] is False
    assert status["backbone"]["outbound_actuation"] is False
    assert status["safety"]["real_infrastructure_write_access"] is False
    assert status["safety"]["arbitrary_foundry_actions"] is False


def test_reads_are_restricted_to_simulation_object_types() -> None:
    backbone = ZyraPalantirBackbone(
        foundry=FakeFoundry(),
        ontology="zyra-sim",
    )

    result = backbone.list_simulation_objects("ZyraDigitalTwinAsset")
    assert result["object_type"] == "ZyraDigitalTwinAsset"

    with pytest.raises(SafetyViolation):
        backbone.list_simulation_objects("RealSubstation")


def test_staged_action_requires_human_approval_and_synthetic_flag() -> None:
    fake = FakeFoundry()
    backbone = ZyraPalantirBackbone(foundry=fake, ontology="zyra-sim")

    with pytest.raises(SafetyViolation):
        backbone.stage_simulation_action(
            "ISOLATE_SIMULATED_NODE",
            {"synthetic": True, "asset_id": "traffic-07"},
            approved_by_human=False,
        )

    with pytest.raises(SafetyViolation):
        backbone.stage_simulation_action(
            "ISOLATE_SIMULATED_NODE",
            {"synthetic": False, "asset_id": "traffic-07"},
            approved_by_human=True,
        )

    staged = backbone.stage_simulation_action(
        "ISOLATE_SIMULATED_NODE",
        {"synthetic": True, "asset_id": "traffic-07"},
        approved_by_human=True,
    )

    assert staged["execution"] == "NOT_EXECUTED_BY_BACKBONE"
    assert staged["review"] == "HUMAN_REQUIRED"
    assert staged["outbound_actuation"] is False
    assert fake.apply_action_called is False


def test_arbitrary_action_is_blocked() -> None:
    backbone = ZyraPalantirBackbone(foundry=FakeFoundry(), ontology="zyra-sim")

    with pytest.raises(SafetyViolation):
        backbone.stage_simulation_action(
            "RUN_ARBITRARY_ACTION",
            {"synthetic": True},
            approved_by_human=True,
        )


def test_real_control_metadata_is_rejected() -> None:
    backbone = ZyraPalantirBackbone(foundry=FakeFoundry(), ontology="zyra-sim")

    with pytest.raises(SafetyViolation):
        backbone.stage_simulation_action(
            "DECLARE_EXERCISE",
            {"synthetic": True, "controller_ip": "192.0.2.10"},
            approved_by_human=True,
        )


def test_non_synthetic_asset_registration_is_blocked() -> None:
    backbone = ZyraPalantirBackbone()
    asset = DigitalTwinAsset(
        asset_id="real-node",
        domain=Domain.POWER,
        label="not allowed",
        synthetic=False,
    )

    with pytest.raises(SafetyViolation):
        backbone.register_local_asset(asset)
