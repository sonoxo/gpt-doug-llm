#!/usr/bin/env python3
"""Structured patent-scope library for GPT-DOUG-MAX.

Engineering research index only: not claim construction or legal advice.
Validated scope seeds are kept separate from pending patent intake records so the
system never invents technical scope when a source document is unavailable.
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATENT_DIR = ROOT / "safety-shield" / "agents" / "knowledge" / "patents"
INTAKE_DIR = ROOT / "safety-shield" / "agents" / "knowledge" / "patent-intake"
SUPPORTED_SCHEMA = "xunia.patent-robotics.seed.v1"
INTAKE_SCHEMA = "xunia.patent-intake.v1"


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise SystemExit(f"NO-GO: cannot load {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise SystemExit(f"NO-GO: record must be an object: {path}")
    return value


def seeds() -> list[tuple[Path, dict]]:
    rows: list[tuple[Path, dict]] = []
    for path in sorted(PATENT_DIR.glob("*.json")) if PATENT_DIR.exists() else []:
        value = load_json(path)
        if value.get("schema") == SUPPORTED_SCHEMA:
            rows.append((path, value))
    return rows


def intakes() -> list[tuple[Path, dict]]:
    rows: list[tuple[Path, dict]] = []
    for path in sorted(INTAKE_DIR.glob("*.json")) if INTAKE_DIR.exists() else []:
        value = load_json(path)
        if value.get("schema") == INTAKE_SCHEMA:
            rows.append((path, value))
    return rows


def norm(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def toks(text: str) -> set[str]:
    return {x for x in norm(text).split() if len(x) >= 3}


def scope_terms(seed: dict) -> list[str]:
    out: list[str] = []
    for key in ("scope_tags", "publicly_described_functional_concepts", "classification_signals"):
        if isinstance(seed.get(key), list):
            out += [str(x) for x in seed[key]]
    model = seed.get("scope_model", {})
    if isinstance(model, dict):
        for value in model.values():
            if isinstance(value, list):
                out += [str(x) for x in value]
            elif isinstance(value, str):
                out.append(value)
    return out


def score(seed: dict, query: str) -> tuple[int, list[str]]:
    query_norm = norm(query)
    query_tokens = toks(query)
    points = 0
    hits: list[str] = []

    title = str(seed.get("title", ""))
    if title and norm(title) in query_norm:
        points += 20
        hits.append("title:" + title)

    for tag in seed.get("scope_tags", []):
        phrase = norm(tag)
        overlap = toks(phrase) & query_tokens
        if phrase and phrase in query_norm:
            points += 8
            hits.append(str(tag))
        elif overlap:
            points += 2 * len(overlap)
            hits.append(str(tag))

    for term in scope_terms(seed):
        overlap = toks(term) & query_tokens
        if overlap:
            points += min(4, len(overlap))
            hits.append(term)

    return points, list(dict.fromkeys(hits))


def publication_date_value(seed: dict) -> date:
    raw = str(seed.get("publication_date", "")).strip()
    try:
        return date.fromisoformat(raw)
    except ValueError:
        return date.min


def validate_seed(path: Path, seed: dict) -> list[str]:
    errors: list[str] = []
    for key in (
        "patent_id",
        "title",
        "source_provenance",
        "scope_tags",
        "scope_model",
        "independent_design_policy",
    ):
        if not seed.get(key):
            errors.append(f"{path.name}: missing {key}")

    policy = seed.get("independent_design_policy", {})
    expected = {
        "copy_claim_language": False,
        "copy_figures_or_drawings": False,
        "assert_freedom_to_operate": False,
        "claim_element_mapping_requires_human_review": True,
        "commercial_release_requires_patent_counsel_review": True,
    }
    for key, value in expected.items():
        if policy.get(key) is not value:
            errors.append(f"{path.name}: {key} must be {value!r}")
    return errors


def validate_intake(path: Path, intake: dict) -> list[str]:
    errors: list[str] = []
    if not intake.get("patent_id"):
        errors.append(f"{path.name}: missing patent_id")
    if intake.get("intake_status") != "PENDING_SCOPE_EXTRACTION":
        errors.append(f"{path.name}: unsupported intake_status")

    source = intake.get("source", {})
    if not isinstance(source, dict) or not source.get("stable_pdf_url"):
        errors.append(f"{path.name}: stable source URL required")
    if isinstance(source, dict) and source.get("request_token_persisted") is not False:
        errors.append(f"{path.name}: ephemeral request tokens must not be persisted")

    policy = intake.get("scope_policy", {})
    if not isinstance(policy, dict):
        errors.append(f"{path.name}: scope_policy must be an object")
    else:
        if policy.get("infer_scope_without_document") is not False:
            errors.append(f"{path.name}: infer_scope_without_document must be false")
        if policy.get("promote_to_validated_scope_seed_only_after_source_review") is not True:
            errors.append(f"{path.name}: source-review promotion gate missing")
        if policy.get("assert_freedom_to_operate") is not False:
            errors.append(f"{path.name}: assert_freedom_to_operate must be false")
    return errors


def status() -> int:
    validated = seeds()
    pending = intakes()
    print("GPT-DOUG-MAX // PATENT SCOPE LIBRARY")
    print("Validated seeds ...", len(validated))
    print("Pending intake ....", len(pending))
    print("Mode .............. PUBLIC_PRIOR_ART_SCOPE_INDEX")
    print("Unknown scope ..... NEVER INFERRED WITHOUT SOURCE")
    print("Claim construction  HUMAN REVIEW REQUIRED")
    print("FTO opinion ....... DISABLED")
    return 0 if validated or pending else 1


def list_cmd(as_json: bool = False) -> int:
    data = [
        {
            "patent_id": seed.get("patent_id"),
            "title": seed.get("title"),
            "scope_tags": seed.get("scope_tags", []),
            "status": "VALIDATED_SCOPE_SEED",
            "path": str(path.relative_to(ROOT)),
        }
        for path, seed in seeds()
    ]
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        for row in data:
            print(f"{row['patent_id']} // {row['title']}")
            print("  scopes:", ", ".join(row["scope_tags"]))
    return 0


def pending_cmd(as_json: bool = False) -> int:
    data = [
        {
            "patent_id": intake.get("patent_id"),
            "status": intake.get("intake_status"),
            "official_document_text_retrieved": intake.get("verification", {}).get(
                "official_document_text_retrieved", False
            ),
            "path": str(path.relative_to(ROOT)),
        }
        for path, intake in intakes()
    ]
    if as_json:
        print(json.dumps(data, indent=2, sort_keys=True))
    else:
        if not data:
            print("No pending patent intake records.")
            return 0
        for row in data:
            print(f"{row['patent_id']} // {row['status']}")
            print("  source text retrieved:", str(row["official_document_text_retrieved"]).lower())
            print("  path:", row["path"])
    return 0


def show(patent_id: str) -> int:
    wanted = patent_id.upper()
    for path, seed in seeds():
        if str(seed.get("patent_id", "")).upper() == wanted:
            print(json.dumps({"path": str(path.relative_to(ROOT)), **seed}, indent=2, sort_keys=True))
            return 0
    for path, intake in intakes():
        if str(intake.get("patent_id", "")).upper() == wanted:
            print(json.dumps({"path": str(path.relative_to(ROOT)), **intake}, indent=2, sort_keys=True))
            return 0
    raise SystemExit(f"NO-GO: patent not found: {patent_id}")


def match(query: str, top: int, as_json: bool = False) -> int:
    data_by_title: dict[str, dict] = {}
    for path, seed in seeds():
        points, hits = score(seed, query)
        row = {
            "patent_id": seed.get("patent_id"),
            "title": seed.get("title"),
            "scope_tags": seed.get("scope_tags", []),
            "path": str(path.relative_to(ROOT)),
            "_publication_date": publication_date_value(seed),
        }
        title_key = norm(str(seed.get("title", "")))
        existing = data_by_title.get(title_key)
        if existing is None:
            data_by_title[title_key] = {
                **row,
                "score": points,
                "matched_scope_signals": hits,
                "_best_match_key": (points, row["_publication_date"], str(row["patent_id"])),
            }
            continue
        if (row["_publication_date"], str(row["patent_id"])) > (
            existing["_publication_date"],
            str(existing["patent_id"]),
        ):
            existing.update(row)
        best_match_key = (points, row["_publication_date"], str(row["patent_id"]))
        if best_match_key > existing["_best_match_key"]:
            existing["score"] = points
            existing["matched_scope_signals"] = hits
            existing["_best_match_key"] = best_match_key
    data = list(data_by_title.values())
    data.sort(key=lambda x: (-int(x["score"]), str(x["patent_id"])))
    for row in data:
        row.pop("_publication_date", None)
        row.pop("_best_match_key", None)
    data = data[: max(1, top)]
    payload = {
        "query": query,
        "results": data,
        "pending_patents_excluded_from_scope_ranking": [
            intake.get("patent_id") for _, intake in intakes()
        ],
    }
    if as_json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        for row in data:
            print(f"{row['score']:>3}  {row['patent_id']} // {row['title']}")
        if payload["pending_patents_excluded_from_scope_ranking"]:
            print(
                "Pending/not-yet-extracted patents excluded:",
                ", ".join(payload["pending_patents_excluded_from_scope_ranking"]),
            )
        print("Research ranking only; claim scope/legal status require human review.")
    return 0


def doctor() -> int:
    validated = seeds()
    pending = intakes()
    errors: list[str] = []
    ids: set[str] = set()

    for path, seed in validated:
        patent_id = str(seed.get("patent_id", ""))
        if patent_id in ids:
            errors.append(f"duplicate patent_id: {patent_id}")
        ids.add(patent_id)
        errors += validate_seed(path, seed)

    for path, intake in pending:
        patent_id = str(intake.get("patent_id", ""))
        if patent_id in ids:
            errors.append(f"duplicate patent_id across validated/pending records: {patent_id}")
        ids.add(patent_id)
        errors += validate_intake(path, intake)

    if len(validated) < 2:
        errors.append("expected at least two validated patent scope seeds")

    if errors:
        print("PATENT SCOPE DOCTOR: NO-GO")
        for error in errors:
            print(" -", error)
        return 1

    print("PATENT SCOPE DOCTOR: GREEN")
    print("Validated seeds ...", len(validated))
    print("Pending intake ....", len(pending))
    print("Unique IDs ........", len(ids))
    print("Independent design  ENFORCED")
    print("Unknown scope ...... FAIL-CLOSED")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="doug-max patent-scope")
    sub = parser.add_subparsers(dest="command")
    sub.add_parser("status")

    list_parser = sub.add_parser("list")
    list_parser.add_argument("--json", action="store_true")

    pending_parser = sub.add_parser("pending")
    pending_parser.add_argument("--json", action="store_true")

    show_parser = sub.add_parser("show")
    show_parser.add_argument("patent_id")

    match_parser = sub.add_parser("match")
    match_parser.add_argument("query")
    match_parser.add_argument("--top", type=int, default=5)
    match_parser.add_argument("--json", action="store_true")

    sub.add_parser("doctor")
    args = parser.parse_args()
    command = args.command or "status"

    if command == "status":
        return status()
    if command == "list":
        return list_cmd(args.json)
    if command == "pending":
        return pending_cmd(args.json)
    if command == "show":
        return show(args.patent_id)
    if command == "match":
        return match(args.query, args.top, args.json)
    if command == "doctor":
        return doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
