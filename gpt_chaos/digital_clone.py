from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

PATENT_ID = "US-20260279583-A1"
PATTERN_ID = "ADAPTIVE_DIGITAL_CLONE_MEMORY_INTERFACE_V1"


@dataclass(frozen=True)
class DigitalClonePolicy:
    state_guardian: bool = True
    graph_context: bool = True
    episodic_memory: bool = True
    semantic_memory: bool = True
    procedural_memory: bool = True
    multimodal_archive: bool = True
    voice_interface: bool = True
    body_interface: bool = True
    meta_learning_proposals: bool = True
    human_approval_for_major_actions: bool = True
    autonomous_medical_decisions: bool = False
    unrestricted_self_modification: bool = False
    secret_storage_in_memory: bool = False


def pattern() -> dict[str, Any]:
    return {
        "pattern_id": PATTERN_ID,
        "source_patent": PATENT_ID,
        "mode": "GENERALIZED_NON_MEDICAL_ARCHITECTURE",
        "policy": asdict(DigitalClonePolicy()),
        "modules": [
            "STATE_GUARDIAN",
            "EVENT_NORMALIZER",
            "GRAPH_CONTEXT",
            "EPISODIC_MEMORY_ARCHIVIST",
            "SEMANTIC_MEMORY_INDEX",
            "PROCEDURAL_MEMORY_APM",
            "MULTIMODAL_INGEST",
            "AI_INTERFACE",
            "BODY_LINK",
            "META_LEARNING_PROPOSER",
            "GPT_CHAOS_CRITIC",
            "HUMAN_APPROVAL_GATE",
            "PROVENANCE_LOG",
            "UNIVERSAL_HIVE_SYNC",
        ],
        "runtime_loop": [
            "OBSERVE",
            "NORMALIZE",
            "LINK_CONTEXT",
            "RECALL",
            "REASON",
            "PROPOSE_ADAPTATION",
            "CRITIC_REVIEW",
            "HUMAN_OR_POLICY_APPROVAL",
            "ACT",
            "MEASURE",
            "ARCHIVE",
        ],
        "memory_model": {
            "episodic": "events, conversations, missions, outcomes, timestamps",
            "semantic": "facts, ontology objects, relationships, durable knowledge",
            "procedural": "validated reusable procedures and APM patterns",
        },
        "body_mapping": {
            "IDLE": "low activity / breathing / blink",
            "LISTEN": "incoming signal capture",
            "THINK": "context linking and retrieval",
            "TALK": "interactive AI interface output",
            "ACT": "authorized execution",
            "LEARN": "archive + adaptation proposal + critic review",
            "ERROR": "anomaly/state-guardian alert",
            "SLEEP": "reduced activity / consolidation",
        },
        "execution_boundary": "NO_UNREVIEWED_SELF_MODIFICATION_OR_MEDICAL_ACTION",
    }


def evaluate_learning_event(
    *,
    has_provenance: bool,
    contains_secret: bool,
    is_sensitive_personal_data: bool,
    user_consent: bool,
    proposes_external_action: bool,
    approved: bool,
) -> dict[str, Any]:
    reasons: list[str] = []
    decision = "ALLOW"

    if not has_provenance:
        decision = "BLOCK"
        reasons.append("PROVENANCE_REQUIRED")
    if contains_secret:
        decision = "BLOCK"
        reasons.append("SECRET_STORAGE_BLOCKED")
    if is_sensitive_personal_data and not user_consent:
        decision = "BLOCK"
        reasons.append("CONSENT_REQUIRED_FOR_SENSITIVE_DATA")
    if proposes_external_action and not approved:
        decision = "BLOCK"
        reasons.append("EXTERNAL_ACTION_REQUIRES_APPROVAL")

    if decision == "ALLOW":
        reasons.append("ARCHIVE_AND_ADAPTATION_PROPOSAL_ALLOWED")

    return {
        "pattern_id": PATTERN_ID,
        "decision": decision,
        "reasons": reasons,
        "adaptation_mode": "PROPOSE_THEN_VALIDATE",
        "self_modification": "DISABLED",
    }
