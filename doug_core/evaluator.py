from __future__ import annotations

import json
import time
from pathlib import Path

from .classifier import classify
from .planner import make_plan
from .router import route


EVALS = [
    (
        "coding",
        "Fix this Python API and run tests",
        "coding",
    ),
    (
        "architecture",
        "Compare three architectures and choose one",
        "reasoning",
    ),
    (
        "security",
        "Audit this repository for exposed secrets",
        "security",
    ),
    (
        "debug",
        "Debug the frontend backend connection",
        "coding",
    ),
    (
        "deployment",
        "Inspect project files and deploy the application",
        "coding",
    ),
]


def evaluate() -> dict:

    results = []

    for (
        name,
        prompt,
        expected,
    ) in EVALS:

        task = classify(prompt)
        plan = make_plan(task)
        routing = route(task)

        passed = (
            task.task_type == expected
            and bool(plan)
            and bool(routing)
        )

        results.append(
            {
                "name": name,
                "passed": passed,
                "task_type": task.task_type,
                "complexity": task.complexity,
                "provider": routing[0].name,
            }
        )

    score = (
        sum(
            int(item["passed"])
            for item in results
        )
        / len(results)
    )

    report = {
        "timestamp": time.time(),
        "score": score,
        "results": results,
    }

    path = Path(
        ".doug/eval-history.jsonl"
    )

    path.parent.mkdir(
        exist_ok=True
    )

    with path.open(
        "a",
        encoding="utf-8",
    ) as handle:
        handle.write(
            json.dumps(report)
            + "\n"
        )

    return report


if __name__ == "__main__":

    report = evaluate()

    for result in report["results"]:

        status = (
            "PASS"
            if result["passed"]
            else "FAIL"
        )

        print(
            f"{status:4} "
            f"{result['name']:14} "
            f"{result['task_type']:10} "
            f"complexity="
            f"{result['complexity']:.2f}"
        )

    print()
    print(
        f"DOUG CORE SCORE: "
        f"{report['score']:.1%}"
    )
