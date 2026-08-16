from .types import Task

def make_plan(task: Task) -> list[str]:
    steps = ["Understand the requested outcome"]

    if task.needs_code:
        steps += [
            "Inspect relevant source files",
            "Make the smallest safe implementation",
            "Run syntax and unit tests",
            "Inspect the diff",
        ]

    if task.needs_tools:
        steps += [
            "Identify required tool operations",
            "Execute guarded tool actions",
            "Verify tool results",
        ]

    if task.needs_reasoning:
        steps += [
            "Generate candidate approaches",
            "Check assumptions and failure modes",
            "Select the strongest approach",
        ]

    steps += [
        "Verify the result against the original request",
        "Return the result with confidence metadata",
    ]

    return steps
