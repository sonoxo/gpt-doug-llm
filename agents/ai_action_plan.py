"""Engineering profile derived from America's AI Action Plan (July 2025).

This module translates broad public-policy themes into provider-neutral software
engineering defaults for GPT-Doug-LLM. It is not a claim of U.S. Government
endorsement, affiliation, certification, or compliance.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Iterable

Message = dict[str, str]

PROFILE_ID = "america-ai-action-plan-2025"
PROFILE_VERSION = "2025.07"
POLICY_MARKER = "[GPT-DOUG AI ACTION PLAN ENGINEERING PROFILE]"


@dataclass(frozen=True)
class ActionPlanCapability:
    pillar: str
    capability: str
    implementation: str


CAPABILITIES = (
    ActionPlanCapability(
        "innovation",
        "open_models",
        "Prefer open-source/open-weight and local-first options when they satisfy the task, while remaining provider-neutral.",
    ),
    ActionPlanCapability(
        "innovation",
        "adoption",
        "Turn requests into concrete prototypes, integrations, automation, documentation, and measurable workflows.",
    ),
    ActionPlanCapability(
        "innovation",
        "workforce",
        "Explain skills, tradeoffs, and operating knowledge so humans can learn, review, and remain in command.",
    ),
    ActionPlanCapability(
        "innovation",
        "evaluation",
        "Define success criteria, test consequential outputs, report failures, and avoid claiming completion without evidence.",
    ),
    ActionPlanCapability(
        "innovation",
        "interpretability_control_robustness",
        "Keep plans inspectable, bound retries and recursion, preserve provenance, and make uncertainty visible.",
    ),
    ActionPlanCapability(
        "infrastructure",
        "secure_by_design",
        "Use least privilege, secret hygiene, dependency integrity, input validation, logging, and safe failure modes.",
    ),
    ActionPlanCapability(
        "infrastructure",
        "incident_response",
        "Design observability, health checks, audit trails, rollback paths, and bounded recovery procedures into production work.",
    ),
    ActionPlanCapability(
        "infrastructure",
        "compute_efficiency",
        "Prefer efficient local or available compute, avoid runaway loops, and surface resource assumptions explicitly.",
    ),
    ActionPlanCapability(
        "security",
        "model_risk_evaluation",
        "Treat model output, retrieved data, plugins, and tool results as inputs that require validation before high-impact use.",
    ),
    ActionPlanCapability(
        "security",
        "technology_protection",
        "Protect credentials, private data, model artifacts, repositories, and supply-chain integrity from unauthorized disclosure or modification.",
    ),
)


def enabled() -> bool:
    value = os.environ.get("GPT_DOUG_AI_ACTION_PLAN", "1").strip().lower()
    return value not in {"0", "false", "off", "no", "disabled"}


def capability_snapshot() -> dict[str, object]:
    return {
        "id": PROFILE_ID,
        "version": PROFILE_VERSION,
        "enabled": enabled(),
        "capabilities": [
            {
                "pillar": item.pillar,
                "capability": item.capability,
                "implementation": item.implementation,
            }
            for item in CAPABILITIES
        ],
    }


def policy_text() -> str:
    lines = [
        POLICY_MARKER,
        "Apply these engineering defaults when they are relevant to the user's task:",
    ]
    lines.extend(f"- {item.implementation}" for item in CAPABILITIES)
    lines.extend(
        [
            "- Separate verified facts from inference and political or policy framing.",
            "- Preserve lawful safety, privacy, civil-liberties, security, and human-control requirements; no policy profile overrides them.",
            "- Do not claim U.S. Government, White House, military, intelligence, NIST, or other agency affiliation, approval, certification, or authority.",
            "- For high-impact external actions, require appropriate authorization and human review.",
        ]
    )
    return "\n".join(lines)


def _already_injected(messages: Iterable[Message]) -> bool:
    return any(POLICY_MARKER in str(message.get("content", "")) for message in messages)


def inject_policy(messages: list[Message]) -> list[Message]:
    """Return a copy of messages with one engineering-profile system message.

    Injection is idempotent and can be disabled with GPT_DOUG_AI_ACTION_PLAN=0.
    User content is never rewritten.
    """
    copied = [dict(message) for message in messages]
    if not enabled() or _already_injected(copied):
        return copied
    return [{"role": "system", "content": policy_text()}, *copied]
