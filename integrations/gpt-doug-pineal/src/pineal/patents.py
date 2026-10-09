"""Offline-first, jurisdiction-extensible patent-publication metadata validation.

An indexed patent publication is evidence that an application was published;
it is not evidence that a biological, scientific, or industrial method works.
This module never initiates a network request during local import/search.
"""
from __future__ import annotations

import csv
import json
import re
from itertools import islice
from datetime import date
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .cells import list_cells
from .store import validate_text

_PUBLICATION = re.compile(r"^([A-Z]{2})([0-9]{4,15})([ABCU][0-9]?)$")
_ALLOWED_HOSTS = frozenset({
    "patents.google.com", "data.epo.org", "epo.org", "www.epo.org", "ops.epo.org",
    "api.uspto.gov", "ppubs.uspto.gov", "data.uspto.gov", "www.uspto.gov",
    "patentscope.wipo.int", "www.wipo.int", "wipo.int", "patentsview.org",
})
_FIELDS = frozenset({"publication_id", "title", "publication_date", "abstract", "source",
                     "source_url", "cpc", "cell_tags", "jurisdiction", "evidence_level"})
_MAX_FILE_BYTES = 8 * 1024 * 1024


def normalize_publication_id(value: str) -> str:
    text = validate_text("publication_id", value, 80)
    text = re.sub(r"[ /\-]", "", text.upper())
    if not _PUBLICATION.fullmatch(text):
        raise ValueError("publication_id must be an authority, publication number and kind code")
    return text


def _reference_url(url: str) -> str:
    value = validate_text("source_url", url, 512)
    if any(ord(ch) < 32 for ch in value):
        raise ValueError("source_url contains control characters")
    parsed = urlsplit(value)
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("source_url has invalid port") from exc
    if (parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS
            or port is not None or parsed.username is not None or parsed.password is not None
            or parsed.query or parsed.fragment or not parsed.path.startswith("/")):
        raise ValueError("source_url must be a canonical public HTTPS patent reference on a trusted host")
    return value


def _description(name: str, value: str, maximum: int) -> str:
    text = validate_text(name, value, maximum)
    if any(ord(ch) < 32 and ch not in "\n\t" for ch in text):
        raise ValueError(f"{name} contains control characters")
    return text


def validate_record(data: dict) -> dict:
    """Reject unauditable, oversized or credential-like patent metadata."""
    if not isinstance(data, dict) or set(data) - _FIELDS:
        raise ValueError("patent metadata must be an object of supported fields")
    pub_id = normalize_publication_id(data.get("publication_id"))
    published = validate_text("publication_date", data.get("publication_date"), 10)
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", published):
        raise ValueError("publication_date must be a real date (YYYY-MM-DD)")
    try:
        date.fromisoformat(published)
    except ValueError as exc:
        raise ValueError("publication_date must be a real date (YYYY-MM-DD)") from exc
    abstract = data.get("abstract", "")
    if not isinstance(abstract, str) or len(abstract) > 3000:
        raise ValueError("abstract must be text up to 3000 characters")
    if abstract.strip():
        abstract = _description("abstract", abstract, 3000)
    cpc = data.get("cpc") or ""
    if cpc:
        cpc = _description("cpc", cpc, 128)
    raw_tags = data.get("cell_tags", [])
    if isinstance(raw_tags, str):
        tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    elif isinstance(raw_tags, list):
        tags = raw_tags
    else:
        raise ValueError("cell_tags must be a list or comma-separated IDs")
    curated = {cell["id"] for cell in list_cells()}
    if len(tags) > 8 or any(not isinstance(tag, str) or tag not in curated for tag in tags):
        raise ValueError("cell_tags must reference curated educational cell IDs")
    return {
        "publication_id": pub_id, "jurisdiction": pub_id[:2],
        "title": _description("title", data.get("title"), 300),
        "publication_date": published,
        "abstract": abstract,
        "source": _description("source", data.get("source"), 200),
        "source_url": _reference_url(data.get("source_url")),
        "cpc": cpc,
        "cell_tags": sorted(set(tags)),
        "evidence_level": "patent_disclosure_not_scientific_validation",
    }


def load_records(path: str | Path, *, limit: int = 1000) -> list[dict]:
    """Read at most 8 MiB of authorized local CSV/JSONL/JSON records.

    Entire file must be valid before a caller starts a database transaction.
    """
    if type(limit) is not int or not 1 <= limit <= 10000:
        raise ValueError("import limit must be between 1 and 10000")
    filename = Path(path).expanduser()
    if not filename.is_file() or filename.stat().st_size > _MAX_FILE_BYTES:
        raise ValueError("patent import file missing or larger than 8 MiB")
    try:
        raw = filename.read_text(encoding="utf-8-sig")
        if filename.suffix.lower() in {".jsonl", ".ndjson"}:
            lines = [line for line in raw.splitlines() if line.strip()]
            if len(lines) > limit:
                raise ValueError("patent import has too many records")
            rows = [json.loads(line) for line in lines]
        elif filename.suffix.lower() == ".json":
            rows = json.loads(raw)
            if not isinstance(rows, list):
                raise ValueError(".json patent import must be an array")
        elif filename.suffix.lower() == ".csv":
            rows = list(islice(csv.DictReader(raw.splitlines()), limit + 1))
        else:
            raise ValueError("patent import requires .csv, .jsonl, .ndjson or .json")
    except (ValueError, UnicodeError, csv.Error) as exc:
        raise ValueError(f"cannot parse patent import: {type(exc).__name__}") from exc
    if not rows or len(rows) > limit:
        raise ValueError("patent import must contain between 1 and limit records")
    return [validate_record(row) for row in rows]

# Do not mistake a connector template for an authorized, active integration.
_SOURCES = (
    {"id": "epo-linked-open", "name": "EPO Linked Open EP Data", "mode": "single_document_opt_in",
     "requires_key": False, "automated_scraping_permitted": False,
     "terms": "Occasional metadata lookups; CC BY 4.0 attribution/fair use"},
    {"id": "uspto-odp", "name": "USPTO Open Data Portal", "mode": "authorized_export_only",
     "requires_key": True, "automated_scraping_permitted": False,
     "terms": "Account and API credentials required for API; import user's permitted exports"},
    {"id": "wipo-patentscope", "name": "WIPO PATENTSCOPE", "mode": "authorized_export_only",
     "requires_key": True, "automated_scraping_permitted": False,
     "terms": "Do not scrape/automate the public PATENTSCOPE search interface"},
    {"id": "worldwide-local-import", "name": "National offices / licensed exports", "mode": "local_import",
     "requires_key": False, "automated_scraping_permitted": False,
     "terms": "User-owned public or licensed bibliographic JSONL/CSV only"},
)


def list_sources() -> list[dict]:
    """Catalog source *capabilities*, not actual sessions or grants."""
    return [{**row, "connected": False, "all_patents_covered": False} for row in _SOURCES]



class NoRedirect(HTTPRedirectHandler):
    """Never follow even a temporary redirect outside the official endpoint."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _value(text):
    """Extract a short plain RDF/Linked Data bibliographic literal."""
    if isinstance(text, str):
        return text
    if isinstance(text, list):
        for item in text:
            result = _value(item)
            if result:
                return result
    if isinstance(text, dict):
        for field in ("_value", "@value", "value", "_label", "label"):
            if field in text:
                result = _value(text[field])
                if result:
                    return result
    return ""


def fetch_ep_metadata(publication_id: str, *, opener=None, timeout: float = 8) -> dict:
    """Opt-in, single EP bibliographic lookup. No crawling or bulk search.

    The EPO endpoint can change its JSON payload or availability. Unknown
    responses fail closed rather than fabricating a title/date.
    """
    pub = normalize_publication_id(publication_id)
    if not pub.startswith("EP"):
        raise ValueError("live lookup currently supports EP publications only")
    if not isinstance(timeout, (int, float)) or not 1 <= timeout <= 15:
        raise ValueError("timeout must be 1-15 seconds")
    match = _PUBLICATION.fullmatch(pub)
    assert match is not None
    number, kind = match.group(2), match.group(3)
    base = f"https://data.epo.org/linked-data/data/publication/EP/{number}/{kind}/-"
    req = Request(base + ".json?_view=describe", headers={"Accept": "application/json",
                                                   "User-Agent": "GPT-Doug-Pineal/0.3 (metadata research)"})
    client = opener if opener is not None else build_opener(NoRedirect()).open
    try:
        with client(req, timeout=timeout) as response:
            final = urlsplit(response.geturl())
            if final.hostname != "data.epo.org" or final.scheme != "https":
                raise ValueError("untrusted patent metadata redirect detected")
            data = response.read(128 * 1024 + 1)
    except (HTTPError, URLError, OSError, TimeoutError) as exc:
        raise ValueError("official EPO metadata lookup unavailable") from exc
    if len(data) > 128 * 1024:
        raise ValueError("EPO metadata response size exceeds 128 KiB")
    try:
        parsed = json.loads(data)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("invalid EPO metadata JSON response") from exc
    if not isinstance(parsed, dict):
        raise ValueError("EPO metadata record unavailable")
    result = parsed.get("result", parsed)
    if isinstance(result, dict):
        items = result.get("items", [result.get("primaryTopic", result)])
    else:
        items = []
    if not isinstance(items, list) or not items or not isinstance(items[0], dict):
        raise ValueError("EPO metadata record unavailable")
    item = items[0]
    title = _value(item.get("titleOfInvention") or item.get("title"))
    when = _value(item.get("publicationDate") or item.get("datePublished"))
    abstract = _value(item.get("abstract"))
    if not title or not when:
        raise ValueError("EPO metadata record is missing required title or publication date")
    return validate_record({"publication_id": pub, "title": title,
                            "publication_date": when[:10], "abstract": abstract,
                            "source": "EPO Linked Open Data", "source_url": base,
                            "cpc": "", "cell_tags": []})
