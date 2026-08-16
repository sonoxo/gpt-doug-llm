from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReasoningContext:
    objective: str
    constraints: list[str]
    assumptions: list[str]
    risks: list[str]
    plan: list[str]


def reason(prompt: str) -> ReasoningContext:
    lower = prompt.lower()

    constraints: list[str] = []

    if "ollama" in lower:
        constraints.append(
            "Do not require Ollama"
        )

    if "local" in lower:
        constraints.append(
            "Support local execution"
        )

    if "preserve" in lower:
        constraints.append(
            "Preserve existing behavior"
        )

    assumptions = [
        "The current repository is authoritative",
        "Changes should be incremental",
        "Tests should validate behavior",
    ]

    risks = [
        "Breaking existing functionality",
        "Editing the wrong files",
        "Unverified assumptions",
        "Configuration drift",
        "Accidental destructive changes",
    ]

    plan = [
        "Inspect current state",
        "Identify exact objective",
        "Locate relevant implementation",
        "Generate possible approaches",
        "Select the smallest reliable solution",
        "Implement",
        "Test",
        "Verify",
        "Iterate if verification fails",
    ]

    return ReasoningContext(
        objective=prompt,
        constraints=constraints,
        assumptions=assumptions,
        risks=risks,
        plan=plan,
    )
