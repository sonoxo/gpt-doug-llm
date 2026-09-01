from __future__ import annotations

import pytest

from zyra_control_plane.capabilities import READ_ONLY, WRITE_LOCAL, CapabilityRegistry
from zyra_control_plane.fde_migration import (
    DEFAULT_MAX_REPAIR_CYCLES,
    MIGRATION_FLEET,
    MIGRATION_STAGES,
    VALIDATION_LOOP,
    build_migration_plan,
    repair_cycle_allowed,
    role_for,
)


def test_migration_plan_is_branch_based_and_approval_gated() -> None:
    plan = build_migration_plan(
        "Migrate legacy ERP data and business logic into XUNIA",
        ["database", "code", "pdf", "spreadsheet"],
    )
    assert plan.stages == ("PLAN", "CONNECT", "INTERPRET", "ENHANCE", "STANDARDIZE", "VERIFY", "DEPLOY")
    assert plan.branch_required is True
    assert plan.approval_required is True
    assert plan.context_strategy == "minimum-viable-context"
    assert plan.max_repair_cycles == DEFAULT_MAX_REPAIR_CYCLES
    assert plan.validation_loop[-1] == "VERIFY"
    assert "deployment evidence recorded" in plan.phase_gates


def test_migration_fleet_has_separated_authority() -> None:
    assert role_for("source-scout").authority == "read-only"
    assert role_for("mapping-engineer").authority == "proposal-only"
    assert role_for("transform-builder").authority == "branch-local-write"
    assert role_for("release-controller").authority == "approval-gated-write"
    assert len(MIGRATION_FLEET) == 10


def test_repair_loop_is_bounded() -> None:
    assert repair_cycle_allowed(0)
    assert repair_cycle_allowed(2)
    assert not repair_cycle_allowed(3)
    with pytest.raises(ValueError):
        repair_cycle_allowed(0, max_cycles=0)
    with pytest.raises(ValueError):
        build_migration_plan("x", max_repair_cycles=11)


def test_read_only_grant_allows_discovery_but_not_transform_write() -> None:
    registry = CapabilityRegistry()
    ok, missing = registry.authorize(
        "fde-source-scout",
        READ_ONLY,
        ("discover-source", "record-provenance"),
    )
    assert ok
    assert missing == ()

    ok, missing = registry.authorize(
        "fde-transform-builder",
        READ_ONLY,
        ("generate-transform",),
    )
    assert not ok
    assert "generate-transform" in missing
    assert "write-boundary" in missing

    ok, missing = registry.authorize(
        "fde-transform-builder",
        WRITE_LOCAL,
        ("generate-transform", "write-branch-artifact"),
    )
    assert ok
    assert missing == ()


def test_release_controller_cannot_cross_external_effect_boundary_with_local_grant() -> None:
    registry = CapabilityRegistry()
    ok, missing = registry.authorize(
        "fde-release-controller",
        WRITE_LOCAL,
        ("check-rollback",),
    )
    assert not ok
    assert "network-boundary" in missing
    assert "external-effect-boundary" in missing


def test_constants_remain_deterministic() -> None:
    assert MIGRATION_STAGES[0] == "PLAN"
    assert MIGRATION_STAGES[-1] == "DEPLOY"
    assert VALIDATION_LOOP == ("VERIFY", "DIAGNOSE", "REPAIR_PROPOSAL", "RE_RUN", "VERIFY")
