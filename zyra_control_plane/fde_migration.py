"""Clean-room AI FDE migration planning primitives for GPT-DOUG-LLM.

This module implements XUNIA-native orchestration patterns learned from public
AI FDE documentation and demonstrations. It does not include or emulate
Palantir proprietary source code, model weights, private APIs, or tenant state.
"""

from dataclasses import dataclass
from typing import Sequence

PUBLIC_SOURCES = (
    "https://www.youtube.com/watch?v=e90qUUh8_us",
    "https://www.palantir.com/docs/foundry/ai-fde/overview/",
    "https://www.palantir.com/docs/foundry/ai-fde/modes-capabilities/",
    "https://www.palantir.com/assets/xrfr7uokpv1b/2F8L1TTINRFCg8IGhcJ8vo/1965d99b6512cbae17b845ec8d26ebd2/SAP_Migration_Whitepaper.pdf",
    "https://github.com/s-andthat/palantir-ai-fde-library",
)

MIGRATION_STAGES = (
    "PLAN",
    "CONNECT",
    "INTERPRET",
    "ENHANCE",
    "STANDARDIZE",
    "VERIFY",
    "DEPLOY",
)

VALIDATION_LOOP = (
    "VERIFY",
    "DIAGNOSE",
    "REPAIR_PROPOSAL",
    "RE_RUN",
    "VERIFY",
)

DEFAULT_MAX_REPAIR_CYCLES = 3


@dataclass(frozen=True)
class MigrationRole:
    name: str
    authority: str
    capabilities: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "authority": self.authority,
            "capabilities": list(self.capabilities),
        }


MIGRATION_FLEET = (
    MigrationRole(
        "source-scout",
        "read-only",
        ("discover-source", "record-provenance", "inventory-constraints"),
    ),
    MigrationRole(
        "schema-cartographer",
        "read-only",
        ("profile-schema", "map-keys", "map-lineage", "measure-quality"),
    ),
    MigrationRole(
        "code-interpreter",
        "read-only",
        ("interpret-code", "extract-business-logic", "map-dependencies"),
    ),
    MigrationRole(
        "mapping-engineer",
        "proposal-only",
        ("map-ontology", "map-standard", "record-assumption", "propose-contract"),
    ),
    MigrationRole(
        "transform-builder",
        "branch-local-write",
        ("generate-transform", "write-branch-artifact", "version-mapping"),
    ),
    MigrationRole(
        "verifier",
        "test-execution",
        ("reconcile", "run-evaluation", "check-lineage", "policy-check"),
    ),
    MigrationRole(
        "diagnostician",
        "proposal-only",
        ("diagnose-failure", "root-cause", "propose-repair"),
    ),
    MigrationRole(
        "sme-gateway",
        "human-decision-recording",
        ("request-decision", "record-decision", "record-acceptance"),
    ),
    MigrationRole(
        "release-controller",
        "approval-gated-write",
        ("check-rollback", "check-impact", "check-approval", "promote-release"),
    ),
    MigrationRole(
        "auditor",
        "append-evidence",
        ("record-tool-use", "record-evidence", "record-risk", "attest-completion"),
    ),
)


@dataclass(frozen=True)
class MigrationMissionPlan:
    objective: str
    source_types: tuple[str, ...]
    stages: tuple[str, ...]
    validation_loop: tuple[str, ...]
    max_repair_cycles: int
    branch_required: bool
    approval_required: bool
    context_strategy: str
    roles: tuple[MigrationRole, ...]
    phase_gates: tuple[str, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "objective": self.objective,
            "source_types": list(self.source_types),
            "stages": list(self.stages),
            "validation_loop": list(self.validation_loop),
            "max_repair_cycles": self.max_repair_cycles,
            "branch_required": self.branch_required,
            "approval_required": self.approval_required,
            "context_strategy": self.context_strategy,
            "roles": [role.to_dict() for role in self.roles],
            "phase_gates": list(self.phase_gates),
        }


def build_migration_plan(
    objective: str,
    source_types: Sequence[str] = (),
    *,
    max_repair_cycles: int = DEFAULT_MAX_REPAIR_CYCLES,
) -> MigrationMissionPlan:
    """Build a deterministic, bounded plan for migration work.

    Migration is always branch-based and approval-gated. A caller may lower the
    repair budget but may not create an unbounded loop.
    """

    clean_objective = objective.strip()
    if not clean_objective:
        raise ValueError("objective must not be empty")
    if max_repair_cycles < 1 or max_repair_cycles > 10:
        raise ValueError("max_repair_cycles must be between 1 and 10")

    normalized_sources = tuple(
        dict.fromkeys(str(item).strip() for item in source_types if str(item).strip())
    )

    return MigrationMissionPlan(
        objective=clean_objective,
        source_types=normalized_sources,
        stages=MIGRATION_STAGES,
        validation_loop=VALIDATION_LOOP,
        max_repair_cycles=max_repair_cycles,
        branch_required=True,
        approval_required=True,
        context_strategy="minimum-viable-context",
        roles=MIGRATION_FLEET,
        phase_gates=(
            "source scope and provenance known",
            "schema and source logic interpreted",
            "canonical mappings reviewed",
            "transforms versioned",
            "reconciliation and evaluations pass",
            "sensitive-data and permission controls pass",
            "ambiguity resolved or explicitly accepted by authorized human",
            "rollback and downstream impact reviewed",
            "deployment evidence recorded",
        ),
    )


def role_for(name: str) -> MigrationRole:
    """Resolve a migration role without inventing permissions."""

    for role in MIGRATION_FLEET:
        if role.name == name:
            return role
    raise KeyError(name)


def repair_cycle_allowed(attempt: int, *, max_cycles: int = DEFAULT_MAX_REPAIR_CYCLES) -> bool:
    """Return whether another automatic diagnose/propose/re-run cycle is allowed."""

    if attempt < 0:
        raise ValueError("attempt must be non-negative")
    if max_cycles < 1 or max_cycles > 10:
        raise ValueError("max_cycles must be between 1 and 10")
    return attempt < max_cycles
