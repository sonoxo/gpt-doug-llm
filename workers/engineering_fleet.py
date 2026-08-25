"""Bounded engineering-fleet planning for GPT-DOUG/XUNIA.

The fleet uses clean-room data-engineering and application-development patterns
summarized in ``workers/knowledge/palantir_engineering_stack.jsonl``. It plans
specialist roles and gates only; the surrounding runtime still owns tools,
permissions, execution, approvals, and evidence.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FleetRole:
    id: str
    mission: str
    depends_on: tuple[str, ...] = ()


ROLES = {
    "intake": FleetRole(
        "intake",
        "Inspect sources, constraints, ownership, provenance, and target outcomes.",
    ),
    "pipeline": FleetRole(
        "pipeline",
        "Design ingestion, normalization, transforms, publication, and freshness contracts.",
        ("intake",),
    ),
    "quality": FleetRole(
        "quality",
        "Define tests, preconditions, postconditions, integrity checks, and failure policy.",
        ("pipeline",),
    ),
    "ontology": FleetRole(
        "ontology",
        "Model canonical objects, properties, links, actions, and semantic contracts.",
        ("pipeline",),
    ),
    "application": FleetRole(
        "application",
        "Build the lowest-complexity UI/workflow surface that satisfies the use case.",
        ("ontology",),
    ),
    "security": FleetRole(
        "security",
        "Check least privilege, data boundaries, write controls, secrets, and abuse cases.",
    ),
    "release": FleetRole(
        "release",
        "Verify tests, health, rollback, downstream impact, and release evidence.",
    ),
    "observer": FleetRole(
        "observer",
        "Track evidence, unresolved risks, lineage, status, and claimed completion.",
    ),
}

DATA_TERMS = {
    "data",
    "dataset",
    "pipeline",
    "ingestion",
    "transform",
    "etl",
    "streaming",
    "batch",
    "schema",
}
APP_TERMS = {
    "app",
    "application",
    "frontend",
    "backend",
    "ui",
    "widget",
    "workflow",
    "react",
    "api",
}
ONTOLOGY_TERMS = {"ontology", "object", "objects", "link", "links", "semantic", "action"}
HIGH_IMPACT_TERMS = {
    "production",
    "deploy",
    "release",
    "delete",
    "migrate",
    "payment",
    "credential",
    "external action",
}


def _contains_any(prompt: str, terms: set[str]) -> bool:
    """Match whole terms, not arbitrary substrings.

    This prevents short terms like ``ui`` or ``api`` from matching unrelated
    words such as ``build`` or ``capability`` and accidentally spawning the
    application role for a pure data-pipeline task.
    """
    lower = prompt.lower()
    for term in terms:
        if " " in term:
            if term in lower:
                return True
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", lower):
            return True
    return False


def select_roles(prompt: str) -> list[FleetRole]:
    """Select the smallest useful specialist fleet for an engineering objective."""
    selected: list[str] = ["intake"]
    is_data = _contains_any(prompt, DATA_TERMS)
    is_app = _contains_any(prompt, APP_TERMS)
    is_ontology = _contains_any(prompt, ONTOLOGY_TERMS)

    if is_data:
        selected.extend(["pipeline", "quality"])
    if is_ontology or is_data or is_app:
        selected.append("ontology")
    if is_app:
        selected.append("application")

    selected.extend(["security", "release", "observer"])
    seen: set[str] = set()
    ordered = []
    for role_id in selected:
        if role_id not in seen:
            ordered.append(ROLES[role_id])
            seen.add(role_id)
    return ordered


def plan_engineering_mission(prompt: str) -> dict:
    """Return a deterministic, auditable fleet plan without executing tools."""
    roles = select_roles(prompt)
    approval_required = _contains_any(prompt, HIGH_IMPACT_TERMS)
    return {
        "objective": prompt.strip(),
        "decision_loop": [
            "INSPECT",
            "MODEL",
            "PLAN",
            "DECOMPOSE",
            "EXECUTE",
            "VALIDATE",
            "OBSERVE",
            "REPAIR",
            "APPROVE",
            "RELEASE",
            "AUDIT",
        ],
        "roles": [asdict(role) for role in roles],
        "approval_required": approval_required,
        "completion_gates": [
            "source and provenance known",
            "contracts and ontology reviewed",
            "tests and data expectations pass",
            "security checks pass",
            "downstream impact reviewed",
            "rollback path exists",
            "execution evidence recorded",
        ],
    }


def fleet_context(prompt: str) -> str:
    """Render a compact fleet context block suitable for an LLM system prompt."""
    plan = plan_engineering_mission(prompt)
    role_lines = [f"- {role['id']}: {role['mission']}" for role in plan["roles"]]
    approval = "required" if plan["approval_required"] else "policy-dependent"
    return "\n".join(
        [
            "XUNIA engineering fleet:",
            *role_lines,
            f"Approval before consequential external writes/releases: {approval}.",
            "Do not claim completion until every applicable completion gate has evidence.",
        ]
    )
