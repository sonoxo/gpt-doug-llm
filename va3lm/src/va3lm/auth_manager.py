from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from va3lm.agent_identity import AgentAccessDecision, AgentAccessRequest, evaluate_agent_access

ProviderKind = Literal["OAUTH2", "OIDC", "API_KEY_VAULT", "MTLS"]


@dataclass(frozen=True)
class AuthProvider:
    provider_id: str
    kind: ProviderKind
    allowed_scopes: tuple[str, ...]
    supports_user_delegation: bool = False
    requires_token_binding: bool = True


@dataclass(frozen=True)
class CredentialEnvelope:
    provider_id: str
    agent_id: str
    scopes: tuple[str, ...]
    credential_class: Literal["SHORT_LIVED_REFERENCE", "USER_DELEGATED_REFERENCE"]
    token_binding: tuple[str, ...]
    raw_secret_exposed: Literal[False] = False


@dataclass(frozen=True)
class BrokerResult:
    decision: AgentAccessDecision
    credential: CredentialEnvelope | None


def broker_auth(request: AgentAccessRequest, provider: AuthProvider) -> BrokerResult:
    if provider.provider_id != request.provider:
        return BrokerResult(AgentAccessDecision("BLOCK", ("AUTH_PROVIDER_MISMATCH",)), None)
    if any(scope not in provider.allowed_scopes for scope in request.requested_scopes):
        return BrokerResult(AgentAccessDecision("REVIEW", ("PROVIDER_SCOPE_EXCEEDED",)), None)
    if request.identity.credential_mode == "USER_DELEGATED" and not provider.supports_user_delegation:
        return BrokerResult(AgentAccessDecision("BLOCK", ("USER_DELEGATION_NOT_SUPPORTED",)), None)

    decision = evaluate_agent_access(request)
    if decision.decision != "ALLOW":
        return BrokerResult(decision, None)

    credential_class = (
        "USER_DELEGATED_REFERENCE"
        if request.identity.credential_mode == "USER_DELEGATED"
        else "SHORT_LIVED_REFERENCE"
    )
    token_binding = request.identity.token_binding if provider.requires_token_binding else ()
    return BrokerResult(
        decision,
        CredentialEnvelope(
            provider_id=provider.provider_id,
            agent_id=request.identity.agent_id,
            scopes=request.requested_scopes,
            credential_class=credential_class,
            token_binding=token_binding,
        ),
    )


AUTH_MANAGER_POLICY = {
    "name": "VA3LM GCPXUNIA Auth Manager",
    "version": "1.0.0",
    "mode": "CENTRAL_OUTBOUND_AUTH_BROKER",
    "rules": {
        "agentOwnIdentity": True,
        "spiffeIdentityPreferred": True,
        "shortLivedCredentials": True,
        "rawSecretsReturnedToAgent": False,
        "sharedCredentials": False,
        "longLivedCredentials": False,
        "dpopSupported": True,
        "mtlsSupported": True,
        "leastPrivilege": True,
        "broadGrantRequiresReview": True,
        "userDelegationSeparate": True,
    },
    "sources": [
        "https://docs.cloud.google.com/iam/docs/auth-agent-own-identity",
        "https://docs.cloud.google.com/iam/docs/auth-manager-overview",
    ],
}
