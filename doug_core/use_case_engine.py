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

    def to_dict(self) -> dict:
        return asdict(self)


def run_use_case(
    name: str,
    root: str | Path = ".",
) -> UseCaseResult:

    case = get_use_case(name)
    report = inspect_workspace(root)
    data = report.to_dict()

    actions: list[str] = []

    if name == "build":
        actions = [
            "Identify the primary application surface",
            "Confirm runtime and dependencies",
            "Inspect current behavior",
            "Implement one feature increment",
            "Run tests",
            "Inspect diff",
            "Repeat until objective is satisfied",
        ]

    elif name == "debug":
        actions = [
            "Capture the reproducible failure",
            "Check Git state",
            "Inspect likely entrypoints",
            "Run relevant tests",
            "Identify root cause",
            "Implement smallest safe fix",
            "Re-run verification",
        ]

    elif name == "architect":
        actions = [
            "Map application entrypoints",
            "Map UI and API boundaries",
            "Map agents and workers",
            "Map storage and memory",
            "Centralize duplicated configuration",
            "Define health boundaries",
            "Benchmark changes",
        ]

    elif name == "operator":
        actions = [
            f"Git branch: {report.git_branch}",
            f"Workspace files: {report.files}",
            f"Test files: {len(report.tests)}",
            f"Entrypoints: {len(report.entrypoints)}",
            "Maintain provider-independent local operation",
        ]

    elif name == "security":
        actions = [
            f"Review {len(report.security_findings)} potential secret findings",
            "Keep credentials outside committed source",
            "Review runtime permissions",
            "Review deployment permissions",
            "Keep local services loopback-bound by default",
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
            score -= min(
                30,
                len(report.security_findings) * 10,
            )

        data["readiness_score"] = max(
            0,
            score,
        )

        actions = [
            "Run complete test suite",
            "Resolve unexpected Git changes",
            "Review security findings",
            "Verify startup command",
            "Verify deployment configuration",
            "Create release only after verification",
        ]

    elif name == "docs":
        actions = [
            "Document primary entrypoints",
            "Document local startup",
            "Document provider configuration",
            "Document test commands",
            "Document security boundaries",
        ]

    elif name == "research":
        actions = [
            "Define the exact research question",
            "Separate facts from assumptions",
            "Identify required authoritative sources",
            "Compare evidence",
            "Document uncertainty",
        ]

    elif name == "product":
        actions = [
            "Define target user",
            "Define core problem",
            "Define minimum viable workflow",
            "Map required engineering surfaces",
            "Prioritize implementation milestones",
            "Define verification metrics",
        ]

    elif name == "agents":
        actions = [
            "Define agent roles",
            "Define permissions",
            "Define routing rules",
            "Define shared state",
            "Define verification checkpoints",
            "Define failure and retry behavior",
        ]

    return UseCaseResult(
        use_case=case.id,
        title=case.title,
        summary=case.description,
        actions=actions,
        data=data,
    )
