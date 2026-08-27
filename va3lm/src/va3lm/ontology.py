from __future__ import annotations

ONTOLOGY = {
    "name": "VA3LM Coding Ontology",
    "version": "1.0.0",
    "deploymentState": "BLUEPRINT_NOT_LIVE_FOUNDRY",
    "objectTypes": [
        "CodingTask", "AgentRun", "FileArtifact", "CodeChange", "TestRun",
        "SecurityFinding", "Approval", "Evidence", "BuildArtifact", "ExplainerArtifact",
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
    "functions": ["rankTasks", "buildWorkflow", "summarizeEvidence", "findBlockingGaps", "buildExplainer"],
    "guardrails": {
        "arbitraryRemoteShell": False,
        "automaticPublish": False,
        "humanApprovalForMutation": True,
        "workspaceBoundaryRequired": True,
    },
}


def schema() -> dict:
    return ONTOLOGY
