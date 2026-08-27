from __future__ import annotations

AGENTS = [
    {"id": "commander", "role": "route work and enforce approval gates"},
    {"id": "architect", "role": "turn goals into implementation design"},
    {"id": "coder", "role": "propose code changes"},
    {"id": "ontology", "role": "map tasks, files, tests, evidence, and actions"},
    {"id": "tester", "role": "plan and evaluate tests"},
    {"id": "security", "role": "review for unsafe or high-risk changes"},
    {"id": "reviewer", "role": "review quality and completeness"},
    {"id": "evidence", "role": "record hashes, results, and build state"},
    {"id": "explainer", "role": "turn technical work into clear commercials and demos"},
]


def roster() -> list[dict[str, str]]:
    return [dict(item) for item in AGENTS]
