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
        id="build",
        title="Application Builder",
        description="Turn product requirements into an implementation plan and project workspace.",
        capabilities=[
            "project planning",
            "repository inspection",
            "file discovery",
            "implementation sequencing",
            "test planning",
            "deployment readiness",
        ],
    ),
    "debug": UseCase(
        id="debug",
        title="Software Debugger",
        description="Inspect a project, identify likely failure surfaces, and produce a repair plan.",
        capabilities=[
            "source inspection",
            "configuration checks",
            "dependency checks",
            "test discovery",
            "runtime diagnostics",
        ],
    ),
    "architect": UseCase(
        id="architect",
        title="Systems Architect",
        description="Map a codebase and recommend scalable architecture improvements.",
        capabilities=[
            "architecture mapping",
            "dependency analysis",
            "service boundaries",
            "risk analysis",
            "migration planning",
        ],
    ),
    "operator": UseCase(
        id="operator",
        title="Local Project Operator",
        description="Operate and inspect local GPT-Doug projects without a model provider.",
        capabilities=[
            "project discovery",
            "health checks",
            "test discovery",
            "Git status",
            "runtime discovery",
            "workspace summaries",
        ],
    ),
    "security": UseCase(
        id="security",
        title="Defensive Security Auditor",
        description="Perform defensive local checks for exposed secrets and risky project configuration.",
        capabilities=[
            "secret-pattern detection",
            "dangerous config detection",
            "dependency inventory",
            "security file discovery",
        ],
    ),
    "release": UseCase(
        id="release",
        title="Release Readiness",
        description="Determine whether a repository is ready to build, test, commit, and deploy.",
        capabilities=[
            "Git cleanliness",
            "test discovery",
            "configuration inventory",
            "deployment file discovery",
            "readiness scoring",
        ],
    ),
    "docs": UseCase(
        id="docs",
        title="Documentation Engineer",
        description="Inventory project structure and documentation gaps.",
        capabilities=[
            "README discovery",
            "API surface inventory",
            "entrypoint discovery",
            "documentation gap analysis",
        ],
    ),
}


def list_use_cases() -> list[dict]:
    return [asdict(x) for x in USE_CASES.values()]


def get_use_case(name: str) -> UseCase:
    key = name.strip().lower()
    if key not in USE_CASES:
        raise KeyError(f"Unknown use case: {name}")
    return USE_CASES[key]
