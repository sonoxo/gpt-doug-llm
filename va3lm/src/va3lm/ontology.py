from __future__ import annotations

ONTOLOGY = {
    "name": "VA3LM XUNIAverse Ontology",
    "version": "1.1.0",
    "root": "sonoxo/xuniadao",
    "deploymentState": "LOCAL_RUNTIME_WITH_PORTABLE_ONTOLOGY_CONTRACT",
    "objectTypes": [
        "CodingTask", "AgentRun", "FileArtifact", "CodeChange", "TestRun",
        "SecurityFinding", "Approval", "Evidence", "BuildArtifact", "ExplainerArtifact",
        "AgentIdentity", "AuthProvider", "AccessPolicy", "PolicyBoundary", "Guardrail",
        "SecurityEvent", "TechnologyPeer", "SecurityDomain", "XuniaverseNode",
    ],
    "linkTypes": [
        ["CodingTask", "TaskHasRun", "AgentRun"],
        ["AgentRun", "RunProposesChange", "CodeChange"],
        ["CodeChange", "ChangeTouchesFile", "FileArtifact"],
        ["CodeChange", "ChangeValidatedByTest", "TestRun"],
        ["CodeChange", "ChangeHasSecurityFinding", "SecurityFinding"],
        ["CodeChange", "ChangeRequiresApproval", "Approval"],
        ["TestRun", "TestProducesEvidence", "Evidence"],
        ["Approval", "ApprovalProducesBuild", "BuildArtifact"],
        ["CodingTask", "TaskHasExplainer", "ExplainerArtifact"],
        ["AgentIdentity", "IdentityRunsAgent", "AgentRun"],
        ["AuthProvider", "ProviderBrokersFor", "AgentIdentity"],
        ["AccessPolicy", "PolicyAuthorizesIdentity", "AgentIdentity"],
        ["PolicyBoundary", "BoundaryEnforcesPolicy", "AccessPolicy"],
        ["Guardrail", "GuardrailProtectsRun", "AgentRun"],
        ["SecurityEvent", "EventProducesEvidence", "Evidence"],
        ["XuniaverseNode", "NodeBenchmarksAgainst", "TechnologyPeer"],
        ["TechnologyPeer", "PeerCoversDomain", "SecurityDomain"],
    ],
    "actions": [
        {"apiName": "proposeChange", "requiresHumanApproval": False},
        {"apiName": "runValidation", "requiresHumanApproval": False},
        {"apiName": "createExplainer", "requiresHumanApproval": False},
        {"apiName": "verifyAgentIdentity", "requiresHumanApproval": False},
        {"apiName": "brokerShortLivedAuth", "requiresHumanApproval": False},
        {"apiName": "recordSecurityEvidence", "requiresHumanApproval": False},
        {"apiName": "approveChange", "requiresHumanApproval": True},
        {"apiName": "requestBroadAgentGrant", "requiresHumanApproval": True},
        {"apiName": "revokeAgentAccess", "requiresHumanApproval": True},
        {"apiName": "publishBuild", "requiresHumanApproval": True},
    ],
    "functions": [
        "rankTasks", "buildWorkflow", "summarizeEvidence", "findBlockingGaps", "buildExplainer",
        "evaluateAgentIdentity", "evaluateAgentScope", "assessPeerEvidence", "buildDefenseGraph",
    ],
    "guardrails": {
        "arbitraryRemoteShell": False,
        "automaticPublish": False,
        "automaticFundMovement": False,
        "humanApprovalForMutation": True,
        "workspaceBoundaryRequired": True,
        "agentIdentityRequired": True,
        "sharedAgentCredentials": False,
        "longLivedAgentCredentials": False,
        "broadAgentGrantWithoutReview": False,
        "rawSecretExposureToAgent": False,
    },
}


def schema() -> dict:
    return ONTOLOGY
