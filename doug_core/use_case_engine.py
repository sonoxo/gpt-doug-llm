from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path

from .use_cases import get_use_case
from .workspace import inspect_workspace


@dataclass
class UseCaseResult:
    use_case: str
    title: str
    summary: str
    actions: list[str]
    data: dict

    def to_dict(self):
        return asdict(self)


def run_use_case(name: str, root: str | Path = ".") -> UseCaseResult:
    case = get_use_case(name)
    report = inspect_workspace(root)
    data = report.to_dict()

    actions: list[str] = []

    if name == "build":
        actions = [
            "Choose the primary application entrypoint",
            "Confirm required runtime and dependencies",
            "Create or update tests before large changes",
            "Implement one feature increment at a time",
            "Run tests after each increment",
            "Validate deployment configuration",
        ]

    elif name == "debug":
        actions = [
            "Check Git status before modifying files",
            f"Inspect {len(report.entrypoints)} detected entrypoint(s)",
            f"Run {len(report.tests)} discovered test file(s)",
            "Capture the first reproducible failure",
            "Fix the smallest root cause",
            "Re-run tests and verify runtime behavior",
        ]

    elif name == "architect":
        actions = [
            "Map entrypoints and runtime boundaries",
            "Separate UI, API, agents, tools, and persistence",
            "Identify duplicated provider logic",
            "Centralize configuration and routing",
            "Add health checks between components",
            "Benchmark before and after architectural changes",
        ]

    elif name == "operator":
        actions = [
            f"Current Git branch: {report.git_branch}",
            f"Workspace contains {report.files} files",
            f"Detected {len(report.tests)} test files",
            f"Detected {len(report.entrypoints)} entrypoints",
            "Keep project runtime independent from AI provider availability",
        ]

    elif name == "security":
        actions = [
            f"Review {len(report.security_findings)} potential secret finding(s)",
            "Keep credentials outside committed source files",
            "Validate guarded terminal execution",
            "Keep local services bound to loopback unless intentionally exposed",
            "Review dependencies and deployment permissions",
        ]

    elif name == "release":
        score = 100

        if report.git_dirty:
            score -= 20

        if not report.tests:
            score -= 25

        if not report.docs:
            score -= 10

        if report.security_findings:
            score -= min(30, 10 * len(report.security_findings))

        data["readiness_score"] = max(score, 0)

        actions = [
            "Run the complete test suite",
            "Resolve unexpected Git changes",
            "Review security findings",
            "Verify startup commands",
            "Verify deployment configuration",
            "Tag only after tests and runtime checks pass",
        ]

    elif name == "docs":
        actions = [
            "Document detected entrypoints",
            "Document local startup procedure",
            "Document provider-independent functionality",
            "Document test commands",
            "Document architecture and security boundaries",
        ]

    return UseCaseResult(
        use_case=case.id,
        title=case.title,
        summary=case.description,
        actions=actions,
        data=data,
    )
