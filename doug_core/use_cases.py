from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass
class UseCase:
    id: str
    title: str
    description: str
    capabilities: list[str]
    requires_ai: bool = False


USE_CASES = {
    "build": UseCase(
        "build",
        "Application Builder",
        "Turn requirements into structured implementation work.",
        [
            "project planning",
            "codebase inspection",
            "implementation sequencing",
            "testing",
            "deployment readiness",
        ],
    ),

    "debug": UseCase(
        "debug",
        "Software Debugger",
        "Locate software failures and create safe repair plans.",
        [
            "runtime diagnosis",
            "source inspection",
            "dependency checks",
            "test discovery",
            "repair planning",
        ],
    ),

    "architect": UseCase(
        "architect",
        "Systems Architect",
        "Map and improve software architecture.",
        [
            "architecture mapping",
            "service boundaries",
            "dependency analysis",
            "migration planning",
            "risk analysis",
        ],
    ),

    "operator": UseCase(
        "operator",
        "Local Project Operator",
        "Operate local projects independently of model availability.",
        [
            "workspace inspection",
            "runtime discovery",
            "Git status",
            "project health",
            "test discovery",
        ],
    ),

    "security": UseCase(
        "security",
        "Defensive Security Auditor",
        "Identify defensive configuration and secret-management risks.",
        [
            "secret pattern detection",
            "unsafe config detection",
            "dependency inventory",
            "security inventory",
        ],
    ),

    "release": UseCase(
        "release",
        "Release Engineer",
        "Determine whether a repository is ready for release.",
        [
            "Git cleanliness",
            "test discovery",
            "deployment inventory",
            "documentation checks",
            "readiness scoring",
        ],
    ),

    "docs": UseCase(
        "docs",
        "Documentation Engineer",
        "Identify project documentation surfaces and gaps.",
        [
            "README discovery",
            "entrypoint discovery",
            "architecture documentation",
            "test documentation",
        ],
    ),

    "research": UseCase(
        "research",
        "Technical Research Planner",
        "Structure technical research questions and evidence requirements.",
        [
            "question decomposition",
            "evidence planning",
            "assumption tracking",
            "comparison framework",
        ],
        True,
    ),

    "product": UseCase(
        "product",
        "Product Engineering Planner",
        "Translate a product idea into engineering milestones.",
        [
            "requirements",
            "MVP definition",
            "technical milestones",
            "risk prioritization",
            "release planning",
        ],
    ),

    "agents": UseCase(
        "agents",
        "Agent Systems Designer",
        "Design controlled multi-agent workflows.",
        [
            "agent responsibilities",
            "task routing",
            "state management",
            "verification loops",
            "permission boundaries",
        ],
    ),
}


def list_use_cases() -> list[dict]:
    return [
        asdict(case)
        for case in USE_CASES.values()
    ]


def get_use_case(name: str) -> UseCase:
    key = name.strip().lower()

    if key not in USE_CASES:
        raise KeyError(
            f"Unknown use case: {name}"
        )

    return USE_CASES[key]
