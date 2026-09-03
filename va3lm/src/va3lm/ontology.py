from __future__ import annotations

KERNEL_VERSION = "3.0.0"
CONTROL_PLANE = "THE_BLACK_HOUSE_V1"

CANONICAL_OBJECT_TYPES = [
    "Mission",
    "Agent",
    "Model",
    "User",
    "Repository",
    "Service",
    "Tool",
    "Resource",
    "Evidence",
    "Source",
    "Decision",
    "Approval",
    "Action",
    "Deployment",
    "Incident",
    "Policy",
    "CredentialReference",
    "Artifact",
    "IntelligenceBrief",
]

CANONICAL_RELATIONSHIPS = [
    "EXECUTES",
    "USES",
    "PRODUCES",
    "DERIVED_FROM",
    "AUTHORIZES",
    "GOVERNS",
    "DEPLOYED_TO",
    "IMPLEMENTS",
    "RUNS_ON",
    "ROUTES_TO",
    "AUDITS",
    "EVIDENCES",
]

ONTOLOGY = {
    "name": "VA3LM Coding Ontology",
    "version": "2.0.0",
    "deploymentState": "BLUEPRINT_NOT_LIVE_FOUNDRY",
    "kernel": {
        "version": KERNEL_VERSION,
        "controlPlane": CONTROL_PLANE,
        "authority": "sonoxo/gpt-doug-llm/the-black-house",
        "objectTypes": CANONICAL_OBJECT_TYPES,
        "relationshipTypes": CANONICAL_RELATIONSHIPS,
        "failClosed": True,
    },
    "objectTypes": [
        "CodingTask",
        "AgentRun",
        "FileArtifact",
        "CodeChange",
        "TestRun",
        "SecurityFinding",
        "Approval",
        "Evidence",
        "BuildArtifact",
        "ExplainerArtifact",
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
    ],
    "actions": [
        {"apiName": "proposeChange", "requiresHumanApproval": False},
        {"apiName": "runValidation", "requiresHumanApproval": False},
        {"apiName": "createExplainer", "requiresHumanApproval": False},
        {"apiName": "approveChange", "requiresHumanApproval": True},
        {"apiName": "publishBuild", "requiresHumanApproval": True},
    ],
    "functions": [
        "rankTasks",
        "buildWorkflow",
        "summarizeEvidence",
        "findBlockingGaps",
        "buildExplainer",
    ],
    "guardrails": {
        "arbitraryRemoteShell": False,
        "automaticPublish": False,
        "humanApprovalForMutation": True,
        "workspaceBoundaryRequired": True,
        "unknownKernelTypeFailsClosed": True,
    },
}


def schema() -> dict:
    return ONTOLOGY


def kernel_status() -> dict:
    return {
        "status": "GREEN",
        "version": KERNEL_VERSION,
        "controlPlane": CONTROL_PLANE,
        "objectTypes": len(CANONICAL_OBJECT_TYPES),
        "relationshipTypes": len(CANONICAL_RELATIONSHIPS),
        "failClosed": True,
    }
