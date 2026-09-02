#!/usr/bin/env python3
"""Daily White House first-party source ingestion for The Black House.

This collector stores metadata, provenance, hashes, mission tags, and source links.
It intentionally does not treat White House assertions as independently verified facts
and does not reproduce full article text.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "intel" / "white-house"
DAILY = OUT / "daily"
STATE_PATH = OUT / "state.json"

SOURCES = {
    "news": "https://www.whitehouse.gov/news/",
    "fact-sheets": "https://www.whitehouse.gov/fact-sheets/",
    "releases": "https://www.whitehouse.gov/releases/",
    "briefings-statements": "https://www.whitehouse.gov/briefings-statements/",
    "remarks": "https://www.whitehouse.gov/remarks/",
    "research": "https://www.whitehouse.gov/research/",
    "executive-orders": "https://www.whitehouse.gov/presidential-actions/executive-orders/",
    "presidential-memoranda": "https://www.whitehouse.gov/presidential-actions/presidential-memoranda/",
}

MONTHS = "January|February|March|April|May|June|July|August|September|October|November|December"
DATE_RE = re.compile(rf"\b({MONTHS})\s+\d{{1,2}},\s+\d{{4}}\b")
IGNORE_TITLES = {
    "news", "fact sheets", "releases", "briefings & statements", "remarks",
    "research", "executive orders", "presidential memoranda", "presidential actions",
}
MISSION_KEYWORDS = {
    "ai": ("artificial intelligence", " ai ", "a.i.", "machine learning", "model"),
    "cyber": ("cyber", "cryptograph", "zero trust", "software security"),
    "defense": ("defense", "military", "warfighter", "national security"),
    "space": ("space", "nasa", "satellite", "artemis"),
    "technology": ("technology", "semiconductor", "quantum", "compute", "digital"),
    "supply-chain": ("supply chain", "critical mineral", "industrial base"),
    "energy": ("energy", "power grid", "bulk-power", "nuclear"),
    "intelligence": ("intelligence", "counterintelligence"),
}


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": "TheBlackHouse-RVIA/1.0 (+public-source-research)"})
    with urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def canonical(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/") + "/"


def published_date(text: str) -> str | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    try:
        return datetime.strptime(match.group(0), "%B %d, %Y").date().isoformat()
    except ValueError:
        return None


def mission_tags(title: str, description: str = "") -> list[str]:
    haystack = f" {title} {description} ".lower()
    return sorted(tag for tag, terms in MISSION_KEYWORDS.items() if any(term in haystack for term in terms))


def article_metadata(url: str) -> tuple[str | None, str | None]:
    """Return meta description and SHA-256 of normalized article/main text."""
    try:
        html = fetch(url)
    except Exception:
        return None, None
    soup = BeautifulSoup(html, "html.parser")
    meta = soup.find("meta", attrs={"name": "description"})
    description = meta.get("content", "").strip() if meta else None
    body = soup.find("article") or soup.find("main") or soup
    normalized = " ".join(body.get_text(" ", strip=True).split())
    digest = sha256(normalized.encode("utf-8")).hexdigest() if normalized else None
    return description or None, digest


def discover(source_name: str, listing_url: str) -> list[dict[str, object]]:
    soup = BeautifulSoup(fetch(listing_url), "html.parser")
    found: dict[str, dict[str, object]] = {}

    for heading in soup.find_all(["h2", "h3"]):
        anchor = heading.find("a", href=True)
        if anchor is None:
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split())
        if not title or title.lower() in IGNORE_TITLES:
            continue
        url = canonical(urljoin(listing_url, anchor["href"]))
        if urlparse(url).netloc != "www.whitehouse.gov":
            continue
        if canonical(listing_url) == url:
            continue

        container = heading
        for _ in range(3):
            if container.parent is None:
                break
            container = container.parent
            text = container.get_text(" ", strip=True)
            if DATE_RE.search(text):
                break
        pub = published_date(container.get_text(" ", strip=True))
        found[url] = {
            "title": title,
            "url": url,
            "category": source_name,
            "published_date": pub,
        }

    return list(found.values())[:25]


def load_state() -> dict[str, object]:
    if STATE_PATH.exists():
        return json.loads(STATE_PATH.read_text())
    return {"known_urls": [], "last_run": None}


def write_daily(records: list[dict[str, object]], run_at: str, errors: list[dict[str, str]]) -> None:
    day = run_at[:10]
    DAILY.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "rvia.white-house-daily.v1",
        "date": day,
        "retrieved_at": run_at,
        "source_authority": "Executive Office of the President / whitehouse.gov",
        "source_tier": "T1_OFFICIAL_PRIMARY",
        "research_rule": "OFFICIAL_SOURCE_STATEMENT_IS_NOT_INDEPENDENT_VERIFICATION",
        "new_items": records,
        "collection_errors": errors,
    }
    (DAILY / f"{day}.json").write_text(json.dumps(payload, indent=2) + "\n")

    lines = [
        f"# 🏛️ White House Daily Source Watch — {day}",
        "",
        f"Retrieved: `{run_at}`",
        "",
        "> **Source discipline:** Items below are official White House publications. Their presence proves that the White House published the statement; it does **not** independently verify every claim inside the publication.",
        "",
        f"New first-party items: **{len(records)}**",
        "",
    ]
    if records:
        for record in records:
            tags = ", ".join(record.get("mission_tags", [])) or "general"
            lines.extend([
                f"## {record['title']}",
                f"- Category: `{record['category']}`",
                f"- Published: `{record.get('published_date') or 'unknown'}`",
                f"- Mission tags: `{tags}`",
                f"- Source: {record['url']}",
                f"- Content SHA-256: `{record.get('content_sha256') or 'unavailable'}`",
                "",
            ])
    else:
        lines.extend(["No newly discovered first-party items on this run.", ""])
    if errors:
        lines.extend(["## Collection gaps", ""])
        for error in errors:
            lines.append(f"- `{error['source']}`: {error['error']}")
        lines.append("")
    lines.extend([
        "## Downstream workflow",
        "",
        "```text",
        "WHITEHOUSE.GOV → PROVENANCE → DEDUPE → MISSION TAGS → SHADOW GLASS → THE BLACK HOUSE",
        "       source statement ≠ independently verified fact",
        "```",
        "",
    ])
    (DAILY / f"{day}.md").write_text("\n".join(lines))


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    run_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    state = load_state()
    known = set(state.get("known_urls", []))
    candidates: dict[str, dict[str, object]] = {}
    errors: list[dict[str, str]] = []

    for source_name, listing_url in SOURCES.items():
        try:
            for item in discover(source_name, listing_url):
                candidates[str(item["url"])] = item
        except Exception as exc:
            errors.append({"source": source_name, "error": f"{type(exc).__name__}: {exc}"})

    new_records: list[dict[str, object]] = []
    for url, item in candidates.items():
        if url in known:
            continue
        description, digest = article_metadata(url)
        item["description"] = description
        item["content_sha256"] = digest
        item["mission_tags"] = mission_tags(str(item["title"]), description or "")
        item["source_authority"] = "whitehouse.gov"
        item["source_tier"] = "T1_OFFICIAL_PRIMARY"
        item["claim_status"] = "SOURCE_STATEMENT"
        item["independent_verification"] = False
        new_records.append(item)

    new_records.sort(key=lambda x: (str(x.get("published_date") or ""), str(x["title"])), reverse=True)
    known.update(candidates)
    state = {
        "schema": "rvia.white-house-daily-state.v1",
        "last_run": run_at,
        "known_urls": sorted(known),
        "last_discovered_count": len(new_records),
        "source_pages": SOURCES,
    }
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n")
    write_daily(new_records, run_at, errors)
    print(f"WHITE HOUSE DAILY: {len(new_records)} new items; {len(errors)} source errors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
