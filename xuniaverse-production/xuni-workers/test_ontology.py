#!/usr/bin/env python3
"""
Copyright (c) 2026 Douglas Brown Jr / Xuniaverse. Licensed under the
xuniaverse-production LICENSE (All Rights Reserved).

Regression suite for ontology.py, codifying the manual verifications run
throughout this project's development: real object counts, real link
scoring, and the Action-type validation gate.

Run directly: python3 test_ontology.py
Exits 0 on all-pass, 1 on any failure (so CI can gate on it).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ontology


def _check(label, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {label}" + (f" ({detail})" if detail else ""))
    return condition


def main():
    results = []

    # --- list_knowledge / list_tasks / list_results return real, loadable data
    knowledge = ontology.list_knowledge()
    results.append(_check(
        "list_knowledge returns entries with required fields",
        len(knowledge) > 0 and all("id" in e and "attribution" in e and "keywords" in e for e in knowledge),
        f"{len(knowledge)} entries",
    ))

    # --- confidence scoring: matched/total ratio, capped at 1.0, real formula
    links = ontology.link_task_to_knowledge(
        "test-taiwan", "is Taiwan a near-term military risk from China? what about proxy warfare?"
    )
    top = links[0] if links else None
    results.append(_check(
        "link_task_to_knowledge returns confidence-scored links, sorted best-first",
        top is not None and 0 < top["confidence"] <= 1.0 and top["to"][1] == "bustamante-taiwan-risk",
        repr(top),
    ))
    results.append(_check(
        "confidence never exceeds 1.0 across all returned links",
        all(0 < l["confidence"] <= 1.0 for l in links),
    ))

    # --- no keyword overlap -> no links (not a fabricated match)
    empty_links = ontology.link_task_to_knowledge("test-empty", "compile the frontend build pipeline xyz123")
    results.append(_check(
        "no keyword overlap returns no links",
        empty_links == [],
        repr(empty_links),
    ))

    # --- Action validation: destructive prompt must be rejected before any file write
    try:
        ontology.submit_task_action("test-destructive-reject", "rm -rf / now")
        results.append(_check("destructive task rejected by submit_task_action", False, "no exception raised"))
    except ontology.ActionValidationError as e:
        results.append(_check("destructive task rejected by submit_task_action", True, str(e)))

    # --- Action validation: path-traversal task_id must be rejected (the real bug found+fixed this session)
    for bad_id in ("../../../../tmp/evil", "/tmp/evil-abs", "has spaces", ""):
        try:
            ontology.submit_task_action(bad_id, "harmless prompt")
            results.append(_check(f"path-unsafe task_id rejected: {bad_id!r}", False, "no exception raised"))
        except ontology.ActionValidationError as e:
            results.append(_check(f"path-unsafe task_id rejected: {bad_id!r}", True, str(e)))

    # --- summary() returns real, internally consistent counts
    summary = ontology.summary()
    results.append(_check(
        "summary() object_counts are non-negative ints",
        all(isinstance(v, int) and v >= 0 for v in summary["object_counts"].values()),
        repr(summary["object_counts"]),
    ))
    results.append(_check(
        "summary() link_count is a non-negative int",
        isinstance(summary["link_count"], int) and summary["link_count"] >= 0,
        summary["link_count"],
    ))

    passed = sum(results)
    total = len(results)
    print(f"\n{passed}/{total} passed")
    sys.exit(0 if passed == total else 1)


if __name__ == "__main__":
    main()
