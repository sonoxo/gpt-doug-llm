from __future__ import annotations

from .types import Task


def make_plan(task: Task) -> list[str]:
    steps = [
        "Understand the requested outcome",
        "Identify constraints and safety boundaries",
    ]

    if task.needs_files:
        steps += [
            "Inspect the workspace",
            "Locate relevant files and entrypoints",
        ]

    if task.needs_code:
        steps += [
            "Inspect existing implementation before editing",
            "Identify the smallest reliable change",
            "Implement incrementally",
            "Run syntax checks and tests",
            "Inspect the resulting diff",
        ]

    if task.needs_tools:
        steps += [
            "Identify required tool operations",
            "Execute guarded operations",
            "Verify tool results",
        ]

    if task.needs_security:
        steps += [
            "Check for exposed secrets",
            "Review unsafe configuration",
            "Preserve least-privilege boundaries",
        ]

    if task.needs_reasoning:
        steps += [
            "Generate candidate approaches",
            "Compare tradeoffs",
            "Check assumptions and failure modes",
            "Select the strongest supported approach",
        ]

    steps += [
        "Verify against the original objective",
        "Report result and remaining limitations",
    ]

    return steps
