"""Dependency-based advisory repair planning; never executes a patch or rollback."""
from collections import deque


def affected_nodes(dependencies, changed):
    if not isinstance(dependencies, dict):
        raise ValueError("dependency map required")
    reverse = {node: set() for node in dependencies}
    for node, upstream in dependencies.items():
        if not isinstance(node, str) or not node or not isinstance(upstream, list):
            raise ValueError("nodes must be names with dependency lists")
        for parent in upstream:
            if parent not in reverse:
                raise ValueError("unknown dependency: " + str(parent))
            reverse[parent].add(node)
    changed = set(changed)
    if not changed <= set(dependencies):
        raise ValueError("changed node missing from graph")
    seen, queue = set(changed), deque(sorted(changed))
    while queue:
        for node in sorted(reverse[queue.popleft()]):
            if node not in seen:
                seen.add(node)
                queue.append(node)
    return sorted(seen)


def plan(dependencies, changed, tests, revisions):
    affected = affected_nodes(dependencies, changed)
    if not isinstance(tests, dict) or not all(isinstance(v, list) for v in tests.values()):
        raise ValueError("test map required")
    if set(tests) - set(dependencies):
        raise ValueError("test mapping contains unknown nodes")
    if any(not isinstance(t, str) or not t for values in tests.values() for t in values):
        raise ValueError("test IDs must be nonempty strings")
    missing_tests = [node for node in affected if not tests.get(node)]
    missing_revisions = [node for node in affected if not isinstance(revisions.get(node), str) or not revisions[node]]
    return {
        "status": "REVIEW" if missing_tests or missing_revisions else "PLAN_READY",
        "affected": affected,
        "tests": sorted({test for node in affected for test in tests.get(node, [])}),
        "missing_test_coverage": missing_tests,
        "missing_rollback_revisions": missing_revisions,
        "rollback_boundary": {node: revisions.get(node) for node in affected},
        "execution": "disabled",
        "assumption": "Completeness depends on supplied dependency and test maps; retain full CI gates.",
    }
