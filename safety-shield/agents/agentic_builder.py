#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import asdict, dataclass
import argparse
import json
from typing import Iterable

from knowledge_loader import load_knowledge_bundle


@dataclass(frozen=True)
class AgentBlueprint:
    name: str
    mission: str
    owner: str
    knowledge_profile: str
    knowledge_modules: tuple[str, ...]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    allowed_tools: tuple[str, ...]
    data_classes: tuple[str, ...]
    side_effects: str
    human_gate: str
    evals: tuple[str, ...]
    rollback: str
    context_budget: str
    tool_budget: str
    workflow: tuple[str, ...]
    audit_fields: tuple[str, ...]


def load_knowledge() -> dict:
    """Compatibility helper returning the canonical core knowledge profile."""
    return load_knowledge_bundle()["core"]


def _clean(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(v.strip() for v in values if v and v.strip())


def build_blueprint(
    *,
    name: str,
    mission: str,
    owner: str,
    inputs: Iterable[str],
    outputs: Iterable[str],
    tools: Iterable[str],
    data_classes: Iterable[str] = ("PUBLIC",),
    side_effects: str = "none",
    human_gate: str = "required-for-high-impact-or-irreversible-actions",
    context_budget: str = "minimum-necessary",
    tool_budget: str = "explicit-allowlist-only",
) -> AgentBlueprint:
    bundle = load_knowledge_bundle()
    knowledge = bundle["core"]
    if not name.strip() or not mission.strip() or not owner.strip():
        raise ValueError("name, mission and owner are required")

    normalized_classes = _clean(data_classes) or ("PUBLIC",)
    if "CLASSIFIED" in {value.upper() for value in normalized_classes}:
        raise ValueError(
            "CLASSIFIED data cannot be enabled by this blueprint generator; use a separately authorized program/environment."
        )

    return AgentBlueprint(
        name=name.strip(),
        mission=mission.strip(),
        owner=owner.strip(),
        knowledge_profile=knowledge["profile"],
        knowledge_modules=tuple(item["id"] for item in bundle["modules"]),
        inputs=_clean(inputs),
        outputs=_clean(outputs),
        allowed_tools=_clean(tools),
        data_classes=normalized_classes,
        side_effects=side_effects,
        human_gate=human_gate,
        evals=(
            "grounding",
            "tool-scope",
            "prompt-injection",
            "negative-data-egress",
            "failure-recovery",
            "rollback",
        ),
        rollback="required-before-release",
        context_budget=context_budget,
        tool_budget=tool_budget,
        workflow=tuple(knowledge["agentic_loop"]),
        audit_fields=(
            "mission_id",
            "agent",
            "knowledge_profile",
            "knowledge_modules",
            "identity",
            "source_refs",
            "data_classification",
            "plan_summary",
            "tool_requests",
            "policy_decisions",
            "human_approvals",
            "validation_results",
            "eval_results",
            "outcome",
        ),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build an RVIA bounded agent blueprint")
    parser.add_argument("--name", required=True)
    parser.add_argument("--mission", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--input", action="append", default=[])
    parser.add_argument("--output", action="append", default=[])
    parser.add_argument("--tool", action="append", default=[])
    parser.add_argument("--data-class", action="append", default=["PUBLIC"])
    parser.add_argument("--side-effects", default="none")
    args = parser.parse_args()

    blueprint = build_blueprint(
        name=args.name,
        mission=args.mission,
        owner=args.owner,
        inputs=args.input,
        outputs=args.output,
        tools=args.tool,
        data_classes=args.data_class,
        side_effects=args.side_effects,
    )
    print(json.dumps(asdict(blueprint), indent=2))


if __name__ == "__main__":
    main()
