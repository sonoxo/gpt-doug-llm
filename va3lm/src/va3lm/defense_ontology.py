from __future__ import annotations

DEFENSE_ONTOLOGY = {
    "id": "GCPXUNIA-VIRGINIA-VA3LM-DEFENSE",
    "version": "1.0.0",
    "root": "sonoxo/xuniadao",
    "architecture": "PALANTIR_ONTOLOGY_ALIGNED",
    "layers": ["GCPXUNIA", "VIRGINIA", "VA3LM", "ZYRA_ACTION_GATE"],
    "objectTypes": [
        "XuniaverseRoot",
        "CloudSecurityLayer",
        "PolicyBoundary",
        "AgentIdentity",
        "AuthProvider",
        "AccessPolicy",
        "VA3LMRuntime",
        "Guardrail",
        "SecurityEvent",
        "Evidence",
    ],
    "linkTypes": [
        ["XuniaverseRoot", "RootProtectsRuntime", "VA3LMRuntime"],
        ["AgentIdentity", "IdentityRunsOn", "VA3LMRuntime"],
        ["AuthProvider", "ProviderBrokersFor", "AgentIdentity"],
        ["AccessPolicy", "PolicyAuthorizesIdentity", "AgentIdentity"],
        ["PolicyBoundary", "BoundaryEnforcesPolicy", "AccessPolicy"],
        ["Guardrail", "GuardrailProtectsRuntime", "VA3LMRuntime"],
        ["SecurityEvent", "EventProducesEvidence", "Evidence"],
    ],
    "actions": [
        {"apiName": "registerAgentIdentity", "requiresHumanApproval": False},
        {"apiName": "verifyAgentIdentity", "requiresHumanApproval": False},
        {"apiName": "brokerShortLivedAuth", "requiresHumanApproval": False},
        {"apiName": "requestBroadAgentGrant", "requiresHumanApproval": True},
        {"apiName": "revokeAgentAccess", "requiresHumanApproval": True},
        {"apiName": "recordSecurityEvidence", "requiresHumanApproval": False},
    ],
    "pipeline": [
        "XUNIA_SCOPE",
        "AGENT_IDENTITY_VERIFY",
        "GCPXUNIA_AUTH_BROKER",
        "VIRGINIA_POLICY_BOUNDARY",
        "VA3LM_REASON_AND_PLAN",
        "RUNTIME_GUARDRAIL",
        "ZYRA_ACTION_GATE",
        "AUDIT_EVIDENCE",
    ],
    "guardrails": {
        "sharedAgentCredentials": False,
        "longLivedAgentCredentials": False,
        "broadAgentGrantWithoutReview": False,
        "rawSecretExposureToAgent": False,
        "automaticPublish": False,
        "automaticFundMovement": False,
        "arbitraryRemoteShell": False,
    },
    "sources": [
        "https://docs.cloud.google.com/iam/docs/auth-agent-own-identity",
        "https://docs.cloud.google.com/iam/docs/auth-manager-overview",
        "https://security.googlecloudcommunity.com/cloud-security-foundation-7/whats-new-in-iam-next-2026-7522",
        "https://www.palantir.com/docs/foundry/ontology/overview",
    ],
    "claims": {
        "googleDeployment": False,
        "palantirDeployment": False,
        "vendorEndorsement": False,
    },
}


def defense_schema() -> dict:
    return DEFENSE_ONTOLOGY
