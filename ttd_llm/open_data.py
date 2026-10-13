"""Opt-in, bounded ingestion of allowlisted public data into local TTD-LLM.

No network discovery, arbitrary URL input, proxy rotation, remote writes, or
model-directed fetches. Randomization samples approved data, not identities.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import re
import secrets
import sqlite3
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

MAX_RESPONSE_BYTES = 2_500_000
MAX_RECORDS_PER_SOURCE = 200
MAX_INPUT_ITEMS = 500
TIMEOUT_SECONDS = 10


class OpenDataError(ValueError):
    """A source was disallowed, malformed, or could not be safely stored."""


@dataclass(frozen=True)
class Source:
    key: str
    publisher: str
    category: str
    endpoint: str
    documentation: str
    measure: str
    unit: str


# Only these literal HTTPS endpoints may be contacted. Add others by reviewed code.
SOURCES = {
    item.key: item for item in (
        Source(
            "usgs_earthquakes", "USGS", "earthquake",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php",
            "earthquake_magnitude", "magnitude",
        ),
        Source(
            "nasa_eonet", "NASA EONET", "natural_event",
            "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=50",
            "https://eonet.gsfc.nasa.gov/docs/v3",
            "natural_event", "event",
        ),
        Source(
            "worldbank_population", "World Bank", "population",
            "https://api.worldbank.org/v2/country/all/indicator/SP.POP.TOTL?format=json&per_page=300&mrv=1",
            "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392",
            "population_total", "people",
        ),
        Source(
            "worldbank_gdp", "World Bank", "economy",
            "https://api.worldbank.org/v2/country/all/indicator/NY.GDP.MKTP.CD?format=json&per_page=300&mrv=1",
            "https://datahelpdesk.worldbank.org/knowledgebase/articles/889392",
            "gdp_current_usd", "USD",
        ),
        Source(
            "openalex_works", "OpenAlex", "scholarly_work",
            "https://api.openalex.org/works?per-page=50",
            "https://help.openalex.org/api/",
            "cited_by_count", "citations",
        ),
    )
}


class RejectRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *_args: Any, **_kwargs: Any) -> None:
        raise OpenDataError("redirects are disallowed for fixed public-data endpoints")


def fetch_source(source: Source) -> tuple[Any, str]:
    """GET a reviewed public HTTPS endpoint once, within a strict byte budget."""
    if source.key not in SOURCES or source != SOURCES[source.key]:
        raise OpenDataError("source is not registered")
    parsed = urllib.parse.urlsplit(source.endpoint)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise OpenDataError("source requires an authenticated HTTPS host")
    from ai_killswitch import require_ai_allowed

    require_ai_allowed("TTD-LLM authorized open-data synchronization")
    request = urllib.request.Request(
        source.endpoint,
        headers={"Accept": "application/json", "User-Agent": "GPT-Doug-TTD-LLM/0.2 public-data-reader"},
        method="GET",
    )
    # No proxy discovery or cross-host redirects; TLS verifies the fixed origin.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), RejectRedirects())
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            if response.geturl() != source.endpoint:
                raise OpenDataError("origin URL changed")
            kind = response.headers.get("Content-Type", "").lower()
            if kind and "json" not in kind:
                raise OpenDataError("source did not return JSON")
            content = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
        # Do not expose remote response bodies, headers or potentially sensitive URLs.
        raise OpenDataError("public source unavailable: " + type(exc).__name__) from exc
    if len(content) > MAX_RESPONSE_BYTES:
        raise OpenDataError("source response exceeds 2.5 MB")
    try:
        return json.loads(content.decode("utf-8")), hashlib.sha256(content).hexdigest()
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise OpenDataError("source response is not UTF-8 JSON") from exc


def _items(source: Source, payload: Any) -> list[dict[str, Any]]:
    if source.key == "usgs_earthquakes":
        items = payload.get("features") if isinstance(payload, dict) else None
    elif source.key == "nasa_eonet":
        items = payload.get("events") if isinstance(payload, dict) else None
    elif source.key.startswith("worldbank_"):
        items = payload[1] if isinstance(payload, list) and len(payload) == 2 else None
    elif source.key == "openalex_works":
        items = payload.get("results") if isinstance(payload, dict) else None
    else:
        raise OpenDataError("unsupported source shape")
    if not isinstance(items, list):
        raise OpenDataError("public source returned an unexpected record envelope")
    if len(items) > MAX_INPUT_ITEMS:
        # Fail closed rather than silently treating an overlarge response as complete.
        raise OpenDataError("source exceeded maximum input item count")
    if any(not isinstance(item, dict) for item in items):
        raise OpenDataError("source contains non-object records")
    return items


def _text(value: Any, limit: int = 240) -> str:
    return str(value)[:limit] if isinstance(value, (str, int, float)) else ""


def _metric(value: Any) -> float | int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value if math.isfinite(value) else None


def _date_ms(value: Any) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return ""
    try:
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat()
    except (OverflowError, OSError, ValueError):
        return ""


def _official_url(url: Any, host: str, fallback: str) -> str:
    if isinstance(url, str):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme == "https" and parsed.hostname == host and not parsed.username and not parsed.password:
            return url[:600]
    return fallback


def _normalized(source: Source, item: dict[str, Any], fetched_at: str) -> dict[str, Any] | None:
    title = ""
    country = ""
    observed_at = ""
    metric = None
    record_url = source.endpoint
    ident = ""

    if source.key == "usgs_earthquakes":
        props = item.get("properties") or {}
        if not isinstance(props, dict):
            return None
        ident = _text(item.get("id"), 100)
        title = _text(props.get("title") or props.get("place"))
        country = _text(props.get("place"))
        observed_at = _date_ms(props.get("time"))
        metric = _metric(props.get("mag"))
        record_url = _official_url(props.get("url"), "earthquake.usgs.gov", source.endpoint)
    elif source.key == "nasa_eonet":
        ident = _text(item.get("id"), 100)
        title = _text(item.get("title"))
        categories = item.get("categories") or []
        if isinstance(categories, list) and categories and isinstance(categories[0], dict):
            country = _text(categories[0].get("title"))
        geometry = item.get("geometry") or []
        if isinstance(geometry, list):
            dates = [g.get("date") for g in geometry if isinstance(g, dict) and isinstance(g.get("date"), str)]
            observed_at = _text(dates[-1], 64) if dates else ""
        if ident and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", ident):
            record_url = "https://eonet.gsfc.nasa.gov/api/v3/events/" + ident
    elif source.key.startswith("worldbank_"):
        code = _text(item.get("countryiso3code"), 3)
        date = _text(item.get("date"), 12)
        if not re.fullmatch(r"[A-Z]{3}", code) or not re.fullmatch(r"\d{4}", date):
            return None
        country_obj = item.get("country") or {}
        if not isinstance(country_obj, dict):
            return None
        country = _text(country_obj.get("value"))
        observed_at = date
        metric = _metric(item.get("value"))
        ident = code + ":" + date + ":" + source.measure
        title = source.measure.replace("_", " ").title() + " - " + country
        indicator = "SP.POP.TOTL" if source.key == "worldbank_population" else "NY.GDP.MKTP.CD"
        record_url = "https://data.worldbank.org/indicator/" + indicator + "?locations=" + code.lower()
    elif source.key == "openalex_works":
        work_url = item.get("id")
        if not isinstance(work_url, str) or not re.fullmatch(r"https://openalex\.org/W\d+", work_url):
            return None
        ident = work_url.rsplit("/", 1)[-1]
        title = _text(item.get("title"))
        observed_at = _text(item.get("publication_date"), 30)
        metric = _metric(item.get("cited_by_count"))
        record_url = work_url
    else:
        return None

    if not ident or not title:
        return None
    raw_digest = hashlib.sha256(json.dumps(item, sort_keys=True, ensure_ascii=False,
                                            separators=(",", ":"), default=str).encode()).hexdigest()
    return {
        "source_id": source.key, "record_id": ident, "title": title,
        "category": source.category, "region": country, "observed_at": observed_at,
        "measure": source.measure, "metric_value": metric, "metric_unit": source.unit,
        "source_url": source.endpoint, "record_url": record_url,
        "fetched_at": fetched_at, "record_sha256": raw_digest,
    }


def choose_sources(keys: list[str], *, randomize: bool = False,
                   seed: int | None = None, sample_sources: int | None = None) -> tuple[list[Source], int | None, random.Random | None]:
    if not keys:
        raise OpenDataError("select at least one explicit --source or --all")
    if any(key not in SOURCES for key in keys):
        raise OpenDataError("unknown source: " + ", ".join(key for key in keys if key not in SOURCES))
    if len(set(keys)) != len(keys):
        raise OpenDataError("duplicate source selection")
    if (seed is not None or sample_sources is not None) and not randomize:
        raise OpenDataError("--seed and --sample-sources require --randomize")
    if sample_sources is not None and (not 1 <= sample_sources <= len(keys)):
        raise OpenDataError("--sample-sources must be between 1 and selected sources")
    actual_seed = seed if seed is not None else secrets.randbits(64) if randomize else None
    rng = random.Random(actual_seed) if randomize else None
    selected = list(keys)
    if rng:
        rng.shuffle(selected)
        if sample_sources is not None:
            selected = selected[:sample_sources]
    return [SOURCES[key] for key in selected], actual_seed, rng


def _write_snapshot(path: Path, *, receipts: list[dict[str, Any]],
                    records: list[dict[str, Any]], replace: bool) -> None:
    if path.is_symlink() or (path.exists() and not replace):
        raise OpenDataError("destination exists; use --replace to overwrite a previous snapshot")
    if not path.parent.is_dir():
        raise OpenDataError("destination parent directory must already exist")
    descriptor, temp_name = tempfile.mkstemp(prefix=".ttd-open-", suffix=".sqlite3", dir=path.parent)
    os.close(descriptor)
    temp_path = Path(temp_name)
    try:
        with closing(sqlite3.connect(temp_path)) as conn, conn:
            conn.execute("""CREATE TABLE open_records (
                source_id TEXT NOT NULL, record_id TEXT NOT NULL, title TEXT NOT NULL,
                category TEXT NOT NULL, region TEXT, observed_at TEXT, measure TEXT NOT NULL,
                metric_value REAL, metric_unit TEXT, source_url TEXT NOT NULL,
                record_url TEXT NOT NULL, fetched_at TEXT NOT NULL,
                record_sha256 TEXT NOT NULL, PRIMARY KEY (source_id, record_id))""")
            conn.execute("""CREATE TABLE source_receipts (
                source_id TEXT PRIMARY KEY, publisher TEXT NOT NULL, endpoint TEXT NOT NULL,
                documentation TEXT NOT NULL, fetched_at TEXT NOT NULL,
                response_sha256 TEXT NOT NULL, items_seen INTEGER NOT NULL,
                records_imported INTEGER NOT NULL, random_seed TEXT)""")
            conn.executemany(
                "INSERT OR IGNORE INTO open_records VALUES (" + ",".join("?" for _ in range(13)) + ")",
                [tuple(row[k] for k in (
                    "source_id", "record_id", "title", "category", "region", "observed_at",
                    "measure", "metric_value", "metric_unit", "source_url", "record_url",
                    "fetched_at", "record_sha256")) for row in records],
            )
            conn.executemany(
                "INSERT INTO source_receipts VALUES (" + ",".join("?" for _ in range(9)) + ")",
                [tuple(rec[k] for k in (
                    "source_id", "publisher", "endpoint", "documentation", "fetched_at",
                    "response_sha256", "items_seen", "records_imported", "random_seed"))
                 for rec in receipts],
            )
            conn.execute("CREATE INDEX idx_open_records_source ON open_records(source_id)")
            conn.execute("CREATE INDEX idx_open_records_date ON open_records(observed_at)")
        # Refuse symlinks and unexpected files before replacing a local snapshot.
        if path.is_symlink() or (path.exists() and not replace):
            raise OpenDataError("destination changed while writing snapshot")
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


def synchronize(keys: list[str], path: str | Path, *, randomize: bool = False,
                seed: int | None = None, sample_sources: int | None = None,
                max_records: int = 50, replace: bool = False,
                dry_run: bool = False,
                fetcher: Callable[[Source], tuple[Any, str]] = fetch_source) -> dict[str, Any]:
    if isinstance(max_records, bool) or not isinstance(max_records, int) or not 1 <= max_records <= MAX_RECORDS_PER_SOURCE:
        raise OpenDataError("--max-records must be an integer between 1 and 200")
    selected, actual_seed, rng = choose_sources(keys, randomize=randomize,
                                                seed=seed, sample_sources=sample_sources)
    dest = Path(path).expanduser().absolute()
    if dry_run:
        return {"ok": True, "dry_run": True, "destination": str(dest),
                "selected_sources": [s.key for s in selected], "seed": actual_seed,
                "max_records_per_source": max_records, "network_calls": 0}
    if dest.is_symlink() or (dest.exists() and not replace):
        raise OpenDataError("destination exists; use --replace only for a previous snapshot")
    if not dest.parent.is_dir():
        raise OpenDataError("destination parent directory must already exist")
    receipts, records, errors = [], [], []
    for spec in selected:
        try:
            payload, digest = fetcher(spec)
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise OpenDataError("invalid source response digest")
            items = _items(spec, payload)
            fetched_at = datetime.now(timezone.utc).isoformat()
            converted = [_normalized(spec, item, fetched_at) for item in items]
            converted = [row for row in converted if row is not None]
            if rng and len(converted) > max_records:
                converted = rng.sample(converted, max_records)
            else:
                converted = converted[:max_records]
            # Deduplicate source-native identifiers in source order.
            dedup = {row["record_id"]: row for row in converted}
            records.extend(dedup.values())
            receipts.append({
                "source_id": spec.key, "publisher": spec.publisher,
                "endpoint": spec.endpoint, "documentation": spec.documentation,
                "fetched_at": fetched_at, "response_sha256": digest,
                "items_seen": len(items), "records_imported": len(dedup),
                "random_seed": str(actual_seed) if actual_seed is not None else None,
            })
        except (OpenDataError, ValueError, OverflowError, TypeError, KeyError) as exc:
            errors.append({"source": spec.key, "error": type(exc).__name__})
    if not receipts:
        raise OpenDataError("all selected public sources failed; previous snapshot unchanged")
    _write_snapshot(dest, receipts=receipts, records=records, replace=replace)
    return {"ok": True, "partial": bool(errors), "db": str(dest),
            "selected_sources": [s.key for s in selected], "sources_imported": len(receipts),
            "records_imported": len(records), "source_failures": errors,
            "seed": actual_seed, "network_calls": len(selected),
            "query": "python3 -m ttd_llm --sqlite " + str(dest) + " --table open_records --schema"}


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description="TTD-LLM opt-in public open-data fabric")
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("sources", help="list code-reviewed, public HTTPS sources (no network)")
    sync = sub.add_parser("sync", help="fetch selected sources once and create local SQLite snapshot")
    names = sync.add_mutually_exclusive_group(required=True)
    names.add_argument("--source", action="append", choices=sorted(SOURCES), help="repeat for sources")
    names.add_argument("--all", action="store_true", help="explicitly opt in to all registered public feeds")
    sync.add_argument("--db", default="ttd_open_data.sqlite3", help="output local SQLite snapshot")
    sync.add_argument("--max-records", type=int, default=50, help="record limit per source (1..200)")
    sync.add_argument("--randomize", action="store_true", help="shuffle approved sources and sample records")
    sync.add_argument("--seed", type=int, help="reproducible randomized source/record selection")
    sync.add_argument("--sample-sources", type=int, help="randomly select this many of the approved sources")
    sync.add_argument("--replace", action="store_true", help="replace existing local snapshot")
    sync.add_argument("--dry-run", action="store_true", help="preview selection without any HTTP calls or writes")
    return ap


def run(argv: list[str] | None = None) -> dict[str, Any]:
    args = parser().parse_args(argv)
    if args.command == "sources":
        return {"ok": True, "network_calls": 0,
                "sources": [dict(key=s.key, publisher=s.publisher, category=s.category,
                                 endpoint=s.endpoint, documentation=s.documentation)
                            for s in SOURCES.values()]}
    return synchronize(list(SOURCES) if args.all else args.source, args.db,
                       randomize=args.randomize, seed=args.seed,
                       sample_sources=args.sample_sources, max_records=args.max_records,
                       replace=args.replace, dry_run=args.dry_run)


def main(argv: list[str] | None = None) -> int:
    try:
        print(json.dumps(run(argv), ensure_ascii=False, indent=2))
        return 0
    except (OpenDataError, OSError, sqlite3.Error) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}),
              file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
