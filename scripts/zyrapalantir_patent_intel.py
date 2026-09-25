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
ATTRIBUTED_GLOB = "uspto-palantir-attributed-*.json"
ONTOLOGY = ROOT / "safety-shield" / "agents" / "knowledge" / "gpt-doug-uspto-patent-intel-v1.json"
BRIEF = ROOT / "intel" / "briefings" / "2026-09-12-uspto-palantir-patent-landscape.md"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def source_paths() -> list[Path]:
    paths = sorted(SOURCE_DIR.glob(SOURCE_GLOB))
    if not paths:
        raise RuntimeError("no USPTO Palantir patent-intel search sources found")
    return paths


def attributed_paths() -> list[Path]:
    paths = sorted(SOURCE_DIR.glob(ATTRIBUTED_GLOB))
    if not paths:
        raise RuntimeError("no exact attributed Palantir patent sources found")
    return paths


def load_attributed_sources() -> list[dict]:
    records = [load_json(path) for path in attributed_paths()]
    seen: set[str] = set()
    for record in records:
        number = str(record.get("document_number", "")).strip()
        if not number:
            raise RuntimeError("attributed patent source missing document number")
        if number in seen:
            raise RuntimeError(f"duplicate attributed patent source: {number}")
        seen.add(number)
    return records


def find_attributed(document_number: str) -> dict:
    for source in load_attributed_sources():
        if source.get("document_number") == document_number:
            return source
    raise RuntimeError(f"attributed patent source not found: {document_number}")


def attributed_as_record(source: dict) -> dict:
    watch = source.get("architecture_watch", {})
    applicant = source.get("applicant", {})
    assignee = source.get("assignee", {})
    return {
        "rank": "exact",
        "document_number": source.get("document_number"),
        "title": source.get("title"),
        "publication_date": source.get("publication_date") or source.get("patent_date"),
        "themes": watch.get("themes", []),
        "applicant": applicant.get("name"),
        "assignee": assignee.get("name"),
        "attribution_confidence": assignee.get("confidence") or applicant.get("confidence"),
        "source_type": "document-front-page",
        "architecture_watch": watch.get("name"),
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
    merged["attributed_records"] = [
        attributed_as_record(source)
        for source in sorted(
            load_attributed_sources(),
            key=lambda source: str(source.get("document_number", "")),
        )
    ]
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
    print("Exact attribution. DOCUMENT-LEVEL APPLICANT/ASSIGNEE FIELDS ONLY")
    print("Legal conclusion . NONE / HUMAN REVIEW REQUIRED")
    print("\n🧠 Top architecture-watch themes")
    for theme, count in counts.most_common(15):
        print(f"  {count:>2}  {theme}")
    print("\nCommands:")
    print("  zyrapalantir patent-intel list")
    print("  zyrapalantir patent-intel attributed")
    print("  zyrapalantir patent-intel eligibility-engine")
    print("  zyrapalantir patent-intel themes")
    print("  zyrapalantir patent-intel search governance")
    print("  zyrapalantir patent-intel search migration")
    print("  zyrapalantir patent-intel search document-generation")
    print("  zyrapalantir patent-intel search visualization")
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
                str(record.get("assignee", "")),
                str(record.get("architecture_watch", "")),
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
            print(f"  applicant: {record.get('applicant')}")
        if record.get("assignee"):
            print(f"  assignee: {record.get('assignee')}")
        if record.get("attribution_confidence"):
            print(f"  attribution: {record.get('attribution_confidence')}")
        if record.get("architecture_watch"):
            print(f"  architecture-watch: {record.get('architecture_watch')}")
        print(f"  themes: {', '.join(record.get('themes', []))}")
    if not matched:
        print("No selected records matched. This local index contains curated records from supplied USPTO materials, not the full 3,544-result set.")
    return 0 if matched else 1


def print_attributed() -> None:
    sources = load_attributed_sources()
    print("🏷️ GPT-DOUG // HIGH-CONFIDENCE DOCUMENT ATTRIBUTIONS")
    print("=================================================")
    for source in sorted(sources, key=lambda item: str(item.get("document_number", ""))):
        applicant = source.get("applicant", {})
        assignee = source.get("assignee", {})
        date = source.get("publication_date") or source.get("patent_date")
        print(f"\nDocument ......... {source.get('document_number')}")
        print(f"Date ............. {date}")
        print(f"Title ............ {source.get('title')}")
        if applicant:
            print(f"Applicant ........ {applicant.get('name')} ({applicant.get('confidence')})")
        if assignee:
            print(f"Assignee ......... {assignee.get('name')} ({assignee.get('confidence')})")
        print(f"Watch ............ {source.get('architecture_watch', {}).get('name')}")
    print("\nCurrent ownership  NOT INFERRED BEYOND DOCUMENT FIELDS")
    print("Claim conclusions  NOT PERFORMED")


def print_eligibility_engine() -> None:
    source = find_attributed("US-20260119865-A1")
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
    attributed_sources = load_attributed_sources()
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
        errors.append("duplicate search-result document number")
    if len(source.get("reported_pages", [])) < 2:
        errors.append("expected at least two captured USPTO pages")

    for path in source_paths():
        page = load_json(path)
        controls = page.get("controls", {})
        if controls.get("claim_freedom_to_operate") is not False:
            errors.append(f"FTO guard missing: {path.name}")
        if controls.get("claim_non_infringement") is not False:
            errors.append(f"non-infringement guard missing: {path.name}")

    expected_exact = {
        "US-20260119865-A1",
        "US-20260093834-A1",
        "US-12591555-B2",
        "US-12585804-B2",
        "US-20260080157-A1",
        "US-12579156-B2",
    }
    exact_numbers = {str(record.get("document_number")) for record in attributed_sources}
    missing_exact = expected_exact - exact_numbers
    if missing_exact:
        errors.append(f"missing exact attributed records: {sorted(missing_exact)}")

    for attributed in attributed_sources:
        applicant = attributed.get("applicant", {})
        assignee = attributed.get("assignee", {})
        controls = attributed.get("controls", {})
        if applicant and applicant.get("name") != "Palantir Technologies Inc.":
            errors.append(f"unexpected applicant: {attributed.get('document_number')}")
        if assignee and assignee.get("name") != "Palantir Technologies Inc.":
            errors.append(f"unexpected assignee: {attributed.get('document_number')}")
        if controls.get("claim_freedom_to_operate") is not False:
            errors.append(f"exact-source FTO guard missing: {attributed.get('document_number')}")
        if controls.get("claim_non_infringement") is not False:
            errors.append(f"exact-source non-infringement guard missing: {attributed.get('document_number')}")

    pattern_names = {p.get("name") for p in ontology.get("architecture_watch_patterns", [])}
    expected_patterns = {
        "eligibility-engine-generative-ai-criteria-evaluation",
        "shared-infrastructure-data-security-governance",
        "live-data-migration-and-consistency",
        "shared-infrastructure-object-permission-governance",
        "generative-ai-evidence-routed-document-workflow",
        "linked-dataset-interactive-visualization",
    }
    missing_patterns = expected_patterns - pattern_names
    if missing_patterns:
        errors.append(f"architecture watch patterns missing: {sorted(missing_patterns)}")

    if errors:
        print("❌ PATENT INTEL DOCTOR FAILED")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("✅ PATENT INTEL DOCTOR: GREEN")
    print(f"   search sources . {len(source.get('source_ids', []))} captured pages")
    print(f"   selected ...... {len(document_numbers)} unique search records")
    print(f"   attributed .... {len(attributed_sources)} exact document-front-page records")
    print(f"   ontology ...... {ontology.get('ontology')}")
    print(f"   watches ....... {len(pattern_names)} architecture pattern(s)")
    print("   ownership ..... only document-level party fields retained")
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
