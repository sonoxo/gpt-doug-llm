#!/usr/bin/env python3
"""Local USPTO patent-landscape CLI for GPT-DOUG / ZYRAPALANTIR.

This tool reads provenance-preserving public patent metadata stored in the
repository. It performs no network calls and makes no legal conclusions.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "intel" / "sources"
SOURCE_GLOB = "uspto-palantir-query-2026-09-12*.json"
ATTRIBUTED_SOURCE = SOURCE_DIR / "uspto-palantir-attributed-US-20260119865-A1.json"
ONTOLOGY = ROOT / "safety-shield" / "agents" / "knowledge" / "gpt-doug-uspto-patent-intel-v1.json"
BRIEF = ROOT / "intel" / "briefings" / "2026-09-12-uspto-palantir-patent-landscape.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_paths() -> list[Path]:
    paths = sorted(SOURCE_DIR.glob(SOURCE_GLOB))
    if not paths:
        raise RuntimeError("no USPTO Palantir patent-intel sources found")
    return paths


def load_attributed_source() -> dict:
    if not ATTRIBUTED_SOURCE.exists():
        raise RuntimeError("high-confidence attributed patent source missing")
    data = load_json(ATTRIBUTED_SOURCE)
    if data.get("document_number") != "US-20260119865-A1":
        raise RuntimeError("unexpected attributed patent document number")
    return data


def attributed_as_record(source: dict) -> dict:
    watch = source.get("architecture_watch", {})
    return {
        "rank": "exact",
        "document_number": source.get("document_number"),
        "title": source.get("title"),
        "publication_date": source.get("publication_date"),
        "themes": watch.get("themes", []),
        "applicant": source.get("applicant", {}).get("name"),
        "attribution_confidence": source.get("applicant", {}).get("confidence"),
        "source_type": "document-front-page",
    }


def load_source() -> dict:
    """Load captured USPTO search pages plus exact attributed records."""
    pages = [load_json(path) for path in source_paths()]
    for page in pages:
        if page.get("query") != "palantir":
            raise RuntimeError("unexpected patent-intel source query")
        if page.get("reported_result_count") != 3544:
            raise RuntimeError("unexpected patent-intel result count")

    first = pages[0]
    merged: dict = {
        "id": "uspto-palantir-query-2026-09-12-aggregate",
        "type": "patent-search-results-aggregate",
        "authority": first.get("authority"),
        "service": first.get("service"),
        "source_url": first.get("source_url"),
        "retrieved": first.get("retrieved"),
        "query": "palantir",
        "reported_result_count": 3544,
        "reported_pages": [page.get("reported_page") for page in pages],
        "source_ids": [page.get("id") for page in pages],
        "disposition": first.get("disposition"),
        "confidence": first.get("confidence", {}),
        "controls": first.get("controls", {}),
        "records": [],
        "attributed_records": [],
    }

    seen: set[str] = set()
    records: list[dict] = []
    for page in pages:
        for record in page.get("records", []):
            number = str(record.get("document_number", "")).strip()
            if not number or number in seen:
                continue
            seen.add(number)
            records.append(record)

    merged["records"] = sorted(
        records,
        key=lambda record: (
            int(record.get("rank", 10**9)),
            str(record.get("document_number", "")),
        ),
    )
    merged["attributed_records"] = [attributed_as_record(load_attributed_source())]
    return merged


def all_records(source: dict) -> list[dict]:
    return list(source.get("attributed_records", [])) + list(source.get("records", []))


def theme_counts(records: list[dict]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for record in records:
        for theme in record.get("themes", []):
            counts[str(theme)] += 1
    return counts


def print_summary(source: dict) -> None:
    records = source.get("records", [])
    attributed = source.get("attributed_records", [])
    counts = theme_counts(all_records(source))
    pages = ", ".join(str(page) for page in source.get("reported_pages", []))
    print("🔎 GPT-DOUG // USPTO PATENT INTELLIGENCE")
    print("========================================")
    print(f"Authority ........ {source.get('authority')}")
    print(f"Query ............ {source.get('query')}")
    print(f"Reported results . {source.get('reported_result_count')}")
    print(f"Captured pages ... {pages}")
    print(f"Indexed records .. {len(records)} search-result record(s)")
    print(f"Attributed exact . {len(attributed)} document-front-page record(s)")
    print(f"Retrieved ........ {source.get('retrieved')}")
    print("Search ownership . NOT ESTABLISHED FROM SEARCH RESULT")
    print("Exact attribution. DOCUMENT-LEVEL APPLICANT FIELD ONLY")
    print("Legal conclusion . NONE / HUMAN REVIEW REQUIRED")
    print("\n🧠 Top architecture-watch themes")
    for theme, count in counts.most_common(15):
        print(f"  {count:>2}  {theme}")
    print("\nCommands:")
    print("  zyrapalantir patent-intel list")
    print("  zyrapalantir patent-intel attributed")
    print("  zyrapalantir patent-intel eligibility-engine")
    print("  zyrapalantir patent-intel themes")
    print("  zyrapalantir patent-intel search ontology")
    print("  zyrapalantir patent-intel search maven")
    print("  zyrapalantir patent-intel search geospatial")
    print("  zyrapalantir patent-intel json")


def print_records(source: dict, query: str | None = None) -> int:
    records = all_records(source)
    needle = (query or "").strip().lower()
    matched = []
    for record in records:
        haystack = " ".join(
            [
                str(record.get("document_number", "")),
                str(record.get("title", "")),
                str(record.get("applicant", "")),
                " ".join(str(x) for x in record.get("themes", [])),
            ]
        ).lower()
        if not needle or needle in haystack:
            matched.append(record)

    if needle:
        print(f"🔎 Patent watchlist search: {query!r} — {len(matched)} match(es)")
    else:
        print(f"📚 Indexed USPTO watchlist — {len(matched)} selected record(s)")
    print("=" * 72)
    for record in matched:
        print(f"#{record.get('rank')}  {record.get('document_number')}  {record.get('publication_date')}")
        print(f"  {record.get('title')}")
        if record.get("applicant"):
            print(f"  applicant: {record.get('applicant')} ({record.get('attribution_confidence')})")
        print(f"  themes: {', '.join(record.get('themes', []))}")
    if not matched:
        print("No selected records matched. This local index contains curated records from supplied USPTO materials, not the full 3,544-result set.")
    return 0 if matched else 1


def print_attributed() -> None:
    source = load_attributed_source()
    applicant = source.get("applicant", {})
    print("🏷️ GPT-DOUG // HIGH-CONFIDENCE DOCUMENT ATTRIBUTION")
    print("================================================")
    print(f"Document ......... {source.get('document_number')}")
    print(f"Published ........ {source.get('publication_date')}")
    print(f"Title ............ {source.get('title')}")
    print(f"Applicant ........ {applicant.get('name')}")
    print(f"Location ......... {applicant.get('location')}")
    print(f"Evidence ......... {applicant.get('attribution_basis')}")
    print(f"Confidence ....... {applicant.get('confidence')}")
    print("Current ownership  NOT ESTABLISHED")
    print("Claim conclusions  NOT PERFORMED")


def print_eligibility_engine() -> None:
    source = load_attributed_source()
    watch = source.get("architecture_watch", {})
    print("🧠 GPT-DOUG // ELIGIBILITY-ENGINE ARCHITECTURE WATCH")
    print("==================================================")
    print(f"Source document .. {source.get('document_number')}")
    print(f"Applicant ........ {source.get('applicant', {}).get('name')}")
    print(f"Pattern .......... {watch.get('name')}")
    print("\nDiagram-level components:")
    for component in watch.get("diagram_components", []):
        print(f"  • {component}")
    print("\nGPT-DOUG independent-design mapping:")
    for mapping in watch.get("gpt_doug_mapping", []):
        print(f"  • {mapping}")
    print("\nGuardrail ........ architecture watch only; no claim copying")
    print("Review ........... human review required for claim-level/FTO analysis")


def print_themes(source: dict) -> None:
    counts = theme_counts(all_records(source))
    print("🧭 GPT-DOUG architecture-watch themes")
    print("=====================================")
    for theme, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        print(f"{count:>2}  {theme}")


def doctor() -> int:
    source = load_source()
    ontology = load_json(ONTOLOGY)
    attributed = load_attributed_source()
    errors: list[str] = []

    if source.get("reported_result_count") != 3544:
        errors.append("reported_result_count mismatch")
    if source.get("controls", {}).get("treat_search_hit_as_confirmed_assignee") is not False:
        errors.append("ownership guard missing")
    if ontology.get("source_id") not in source.get("source_ids", []):
        errors.append("ontology/source mismatch")
    if not BRIEF.exists():
        errors.append("briefing missing")

    document_numbers = [r.get("document_number") for r in source.get("records", [])]
    if len(document_numbers) != len(set(document_numbers)):
        errors.append("duplicate document number")
    if len(source.get("reported_pages", [])) < 2:
        errors.append("expected at least two captured USPTO pages")

    for path in source_paths():
        page = load_json(path)
        controls = page.get("controls", {})
        if controls.get("claim_freedom_to_operate") is not False:
            errors.append(f"FTO guard missing: {path.name}")
        if controls.get("claim_non_infringement") is not False:
            errors.append(f"non-infringement guard missing: {path.name}")

    applicant = attributed.get("applicant", {})
    if attributed.get("document_number") != "US-20260119865-A1":
        errors.append("attributed document mismatch")
    if applicant.get("name") != "Palantir Technologies Inc.":
        errors.append("document-front-page applicant mismatch")
    if applicant.get("confidence") != "HIGH_FROM_DOCUMENT_FRONT_PAGE":
        errors.append("document attribution confidence mismatch")
    if attributed.get("controls", {}).get("treat_applicant_attribution_as_current_ownership_or_enforceability_proof") is not False:
        errors.append("current-ownership guard missing")
    patterns = ontology.get("architecture_watch_patterns", [])
    if not any(p.get("name") == "eligibility-engine-generative-ai-criteria-evaluation" for p in patterns):
        errors.append("eligibility-engine architecture watch missing")

    if errors:
        print("❌ PATENT INTEL DOCTOR FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("✅ PATENT INTEL DOCTOR: GREEN")
    print(f"   search sources . {len(source.get('source_ids', []))} captured pages")
    print(f"   selected ...... {len(document_numbers)} unique search records")
    print("   attributed .... 1 high-confidence document-front-page record")
    print(f"   ontology ...... {ontology.get('ontology')}")
    print("   eligibility ... architecture watch active")
    print("   ownership ..... current ownership not inferred")
    print("   legal advice .. false")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="zyrapalantir patent-intel")
    parser.add_argument(
        "command",
        nargs="?",
        default="summary",
        choices=["summary", "list", "attributed", "eligibility-engine", "themes", "search", "json", "doctor"],
    )
    parser.add_argument("terms", nargs="*")
    args = parser.parse_args()

    source = load_source()
    if args.command == "summary":
        print_summary(source)
        return 0
    if args.command == "list":
        return print_records(source)
    if args.command == "attributed":
        print_attributed()
        return 0
    if args.command == "eligibility-engine":
        print_eligibility_engine()
        return 0
    if args.command == "themes":
        print_themes(source)
        return 0
    if args.command == "search":
        if not args.terms:
            parser.error("search requires one or more terms")
        return print_records(source, " ".join(args.terms))
    if args.command == "json":
        print(json.dumps(source, indent=2, sort_keys=True))
        return 0
    if args.command == "doctor":
        return doctor()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
