#!/usr/bin/env python3
"""Structured patent-scope library for GPT-DOUG-MAX.

This is an engineering research index, not claim construction or legal advice.
It loads provenance-preserving patent seed JSON files, validates independent-design
controls, and ranks patents against a design description using declared scope tags.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATENT_DIR = ROOT / "safety-shield" / "agents" / "knowledge" / "patents"
SUPPORTED_SCHEMA = "xunia.patent-robotics.seed.v1"


def load_seed(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise SystemExit(f"NO-GO: missing patent seed: {path}") from exc
    except json.JSONDecodeError as exc:
        raise SystemExit(f"NO-GO: invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"NO-GO: patent seed must be an object: {path}")
    return value


def seeds() -> list[tuple[Path, dict]]:
    rows: list[tuple[Path, dict]] = []
    if not PATENT_DIR.exists():
        return rows
    for path in sorted(PATENT_DIR.glob("*.json")):
        value = load_seed(path)
        if value.get("schema") == SUPPORTED_SCHEMA:
            rows.append((path, value))
    return rows


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def tokens(text: str) -> set[str]:
    return {x for x in normalize(text).split() if len(x) >= 3}


def scope_terms(seed: dict) -> list[str]:
    terms: list[str] = []
    for key in ("scope_tags", "publicly_described_functional_concepts", "classification_signals"):
        value = seed.get(key, [])
        if isinstance(value, list):
            terms.extend(str(x) for x in value if str(x).strip())
    model = seed.get("scope_model", {})
    if isinstance(model, dict):
        for value in model.values():
            if isinstance(value, list):
                terms.extend(str(x) for x in value if str(x).strip())
            elif isinstance(value, str):
                terms.append(value)
    return terms


def score(seed: dict, query: str) -> tuple[int, list[str]]:
    q_norm = normalize(query)
    q_tokens = tokens(query)
    value = 0
    hits: list[str] = []

    title = str(seed.get("title", ""))
    if title and normalize(title) in q_norm:
        value += 20
        hits.append(f"title:{title}")

    for tag in seed.get("scope_tags", []):
        phrase = normalize(str(tag))
        if not phrase:
            continue
        phrase_tokens = tokens(phrase)
        if phrase in q_norm:
            value += 8
            hits.append(str(tag))
        elif phrase_tokens and len(phrase_tokens & q_tokens) >= max(1, len(phrase_tokens) // 2):
            value += len(phrase_tokens & q_tokens) * 2
            hits.append(str(tag))

    for term in scope_terms(seed):
        overlap = tokens(term) & q_tokens
        if overlap:
            value += min(4, len(overlap))
            if len(hits) < 12:
                hits.append(term)

    return value, list(dict.fromkeys(hits))


def validate(path: Path, seed: dict) -> list[str]:
    errors: list[str] = []
    for key in ("patent_id", "title", "source_provenance", "scope_tags", "scope_model", "independent_design_policy"):
        if not seed.get(key):
            errors.append(f"{path.name}: missing {key}")

    if seed.get("schema") != SUPPORTED_SCHEMA:
        errors.append(f"{path.name}: unsupported schema {seed.get('schema')!r}")

    policy = seed.get("independent_design_policy", {})
    if not isinstance(policy, dict):
        errors.append(f"{path.name}: independent_design_policy must be an object")
    else:
        if policy.get("copy_claim_language") is not False:
            errors.append(f"{path.name}: copy_claim_language must be false")
        if policy.get("copy_figures_or_drawings") is not False:
            errors.append(f"{path.name}: copy_figures_or_drawings must be false")
        if policy.get("assert_freedom_to_operate") is not False:
            errors.append(f"{path.name}: assert_freedom_to_operate must be false")
        if policy.get("claim_element_mapping_requires_human_review") is not True:
            errors.append(f"{path.name}: claim mapping must require human review")
        if policy.get("commercial_release_requires_patent_counsel_review") is not True:
            errors.append(f"{path.name}: commercial release must require patent counsel review")

    provenance = seed.get("source_provenance", [])
    if not isinstance(provenance, list) or not provenance:
        errors.append(f"{path.name}: source_provenance must be non-empty")

    return errors


def cmd_status() -> int:
    rows = seeds()
    print("GPT-DOUG-MAX // PATENT SCOPE LIBRARY")
    print("====================================")
    print("Seeds ............", len(rows))
    print("Directory ........", PATENT_DIR)
    print("Mode ............. PUBLIC_PRIOR_ART_SCOPE_INDEX")
    print("Claim construction HUMAN REVIEW REQUIRED")
    print("FTO opinion ...... DISABLED")
    print("Claim copying .... DISABLED")
    print("External action .. DISABLED")
    return 0 if rows else 1


def cmd_list(as_json: bool) -> int:
    rows = seeds()
    data = [
        {
            "patent_id": seed.get("patent_id"),
            "title": seed.get("title"),
            "scope_tags": seed.get("scope_tags", []),
            "path": str(path.relative_to(ROOT)),
        }
        for path, seed in rows
    ]
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
        return 0
    for row in data:
        print(f"{row['patent_id']} // {row['title']}")
        print("  scopes:", ", ".join(row["scope_tags"]))
        print("  path  :", row["path"])
    return 0


def find_seed(patent_id: str) -> tuple[Path, dict]:
    wanted = patent_id.strip().upper()
    for path, seed in seeds():
        if str(seed.get("patent_id", "")).upper() == wanted:
            return path, seed
    raise SystemExit(f"NO-GO: patent not found in scope library: {patent_id}")


def cmd_show(patent_id: str) -> int:
    path, seed = find_seed(patent_id)
    print(json.dumps({"path": str(path.relative_to(ROOT)), **seed}, indent=2, sort_keys=True))
    return 0


def cmd_match(query: str, top: int, as_json: bool) -> int:
    ranked = []
    for path, seed in seeds():
        points, hits = score(seed, query)
        ranked.append(
            {
                "score": points,
                "patent_id": seed.get("patent_id"),
                "title": seed.get("title"),
                "matched_scope_signals": hits,
                "scope_tags": seed.get("scope_tags", []),
                "path": str(path.relative_to(ROOT)),
            }
        )
    ranked.sort(key=lambda x: (-int(x["score"]), str(x["patent_id"])))
    ranked = ranked[: max(1, top)]
    if as_json:
        print(json.dumps({"query": query, "results": ranked}, indent=2, sort_keys=True))
        return 0
    print("QUERY:", query)
    for row in ranked:
        print(f"{row['score']:>3}  {row['patent_id']} // {row['title']}")
        if row["matched_scope_signals"]:
            print("     hits:", "; ".join(row["matched_scope_signals"][:8]))
    print()
    print("Research ranking only. Claim scope and legal status require human legal review.")
    return 0


def cmd_doctor() -> int:
    rows = seeds()
    errors: list[str] = []
    ids: set[str] = set()
    for path, seed in rows:
        patent_id = str(seed.get("patent_id", "")).strip()
        if patent_id in ids:
            errors.append(f"duplicate patent_id: {patent_id}")
        ids.add(patent_id)
        errors.extend(validate(path, seed))
    if len(rows) < 2:
        errors.append("expected at least two patent scope seeds")
    if errors:
        print("PATENT SCOPE DOCTOR: NO-GO")
        for error in errors:
            print(" -", error)
        return 1
    print("PATENT SCOPE DOCTOR: GREEN")
    print("Seeds ............", len(rows))
    print("Unique IDs .......", len(ids))
    print("Provenance ....... REQUIRED")
    print("Independent design ENFORCED")
    print("Claim review ...... HUMAN")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="doug-max patent-scope")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status")
    list_p = sub.add_parser("list")
    list_p.add_argument("--json", action="store_true")
    show = sub.add_parser("show")
    show.add_argument("patent_id")
    match = sub.add_parser("match")
    match.add_argument("query")
    match.add_argument("--top", type=int, default=5)
    match.add_argument("--json", action="store_true")
    sub.add_parser("doctor")
    args = parser.parse_args()

    command = args.command or "status"
    if command == "status":
        return cmd_status()
    if command == "list":
        return cmd_list(args.json)
    if command == "show":
        return cmd_show(args.patent_id)
    if command == "match":
        return cmd_match(args.query, args.top, args.json)
    if command == "doctor":
        return cmd_doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
