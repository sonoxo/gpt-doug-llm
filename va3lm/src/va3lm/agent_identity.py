from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

Decision = Literal["ALLOW", "REVIEW", "BLOCK"]
Runtime = Literal["VA3LM", "ZYRA", "GPT_UAP_XO", "OTHER"]
CredentialMode = Literal["SHORT_LIVED", "USER_DELEGATED"]

_SPIFFE_RE = re.compile(r"^spiffe://[a-z0-9.-]+/[A-Za-z0-9._/-]+$")


@dataclass(frozen=True)
class AgentIdentity:
    agent_id: str
    spiffe_id: str
    runtime: Runtime
    credential_mode: CredentialMode
    scopes: tuple[str, ...]
    provenance: tuple[str, ...]
    token_binding: tuple[str, ...] = ("DPOP", "MTLS")


@dataclass(frozen=True)
class AgentAccessRequest:
    identity: AgentIdentity
    provider: str
    requested_scopes: tuple[str, ...]
    shared_credential: bool = False
    long_lived_credential: bool = False
    project_wide_grant: bool = False
    organization_wide_grant: bool = False
    human_approved: bool = False


@dataclass(frozen=True)
class AgentAccessDecision:
    decision: Decision
    reasons: tuple[str, ...]


def valid_spiffe_id(value: str) -> bool:
    return bool(_SPIFFE_RE.fullmatch(value))


def evaluate_agent_access(request: AgentAccessRequest) -> AgentAccessDecision:
    reasons: list[str] = []
    identity = request.identity

    if not identity.agent_id.strip():
        reasons.append("AGENT_ID_REQUIRED")
    if not valid_spiffe_id(identity.spiffe_id):
        reasons.append("SPIFFE_ID_REQUIRED")
    if not identity.provenance:
        reasons.append("IDENTITY_PROVENANCE_REQUIRED")
    if not request.provider.strip():
        reasons.append("AUTH_PROVIDER_REQUIRED")
    if request.shared_credential:
        reasons.append("SHARED_AGENT_CREDENTIAL_BLOCKED")
    if request.long_lived_credential:
        reasons.append("LONG_LIVED_AGENT_CREDENTIAL_BLOCKED")
    if request.project_wide_grant or request.organization_wide_grant:
        reasons.append("BROAD_AGENT_GRANT_REQUIRES_REVIEW")
    if any(scope not in identity.scopes for scope in request.requested_scopes):
        reasons.append("REQUESTED_SCOPE_EXCEEDS_AGENT_SCOPE")

    hard_blocks = {
        "AGENT_ID_REQUIRED",
        "SPIFFE_ID_REQUIRED",
        "SHARED_AGENT_CREDENTIAL_BLOCKED",
        "LONG_LIVED_AGENT_CREDENTIAL_BLOCKED",
    }
    if any(reason in hard_blocks for reason in reasons):
        return AgentAccessDecision("BLOCK", tuple(reasons))
    if reasons and not request.human_approved:
        return AgentAccessDecision("REVIEW", tuple(reasons))
    return AgentAccessDecision("ALLOW", tuple(reasons))
