from __future__ import annotations

import html
import json
import os
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


SOURCE_ID = "open-source-everything"
INTEGRATION_LABEL = "gpt-doug-shoggoth-anon-llm"
SOURCE_REPOSITORY = "An-anonymous-coder/Open-Source-Everything"
SOURCE_COMMIT = "7290f2cb9ffa7c7bba1723b7e06f726802de51be"
SOURCE_VERSION = "165.2026.5.13.0"
SOURCE_LICENSE = "GPL-3.0"
SOURCE_HOST = "https://gitlab.com/an-anonymous-coder1/Open-Source-Everything"
SOURCE_MIRROR = "https://github.com/An-anonymous-coder/Open-Source-Everything"
SOURCE_RAW = (
    "https://raw.githubusercontent.com/"
    f"{SOURCE_REPOSITORY}/{SOURCE_COMMIT}/README.md"
)
DEFAULT_CACHE = Path(
    os.getenv(
        "SHAGGOTH_OSE_CACHE",
        "/tmp/shaggoth-catalogs/open-source-everything.json",
    )
)
MAX_SOURCE_BYTES = 12 * 1024 * 1024

CONTENT_SECTIONS = frozenset(
    {
        "AI Tools & Services",
        "Audio & Music",
        "Backup & Sync",
        "Business & Commerce",
        "CD/DVD Tools",
        "Development",
        "Digital Coins & Cryptocurrency",
        "Education & Reference",
        "File Management",
        "File Sharing",
        "Games",
        "Gaming Software",
        "Home & Family",
        "Network & Admin",
        "News & Books",
        "Office & Productivity",
        "Online Services",
        "OS & Utilities",
        "Photos & Graphics",
        "Religion & Prayer",
        "Remote Work & Education",
        "Security & Privacy",
        "Social & Communications",
        "Sport & Health",
        "System & Hardware",
        "Travel & Location",
        "Video & Movies",
        "Web Browsing",
    }
)

_TOKEN_RE = re.compile(
    r"(?P<h1><h1\b[^>]*>.*?</h1>)|"
    r"(?P<h3><h3\b[^>]*>.*?</h3>)|"
    r'(?P<a><a\b[^>]*href="(?P<href>[^"]+)"[^>]*>(?P<label>.*?)</a>)',
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    name: str
    url: str
    section: str
    subsection: str


def _text(value: str) -> str:
    value = _TAG_RE.sub(" ", value)
    value = html.unescape(value)
    return _WS_RE.sub(" ", value).strip()


def parse_catalog(readme: str) -> list[CatalogEntry]:
    section = ""
    subsection = ""
    entries: list[CatalogEntry] = []
    seen: set[tuple[str, str, str, str]] = set()

    for match in _TOKEN_RE.finditer(readme):
        if match.group("h1"):
            section = _text(match.group("h1"))
            subsection = ""
            continue
        if match.group("h3"):
            subsection = _text(match.group("h3"))
            continue

        if section not in CONTENT_SECTIONS:
            continue

        url = html.unescape(match.group("href") or "").strip()
        name = _text(match.group("label") or "")
        if not name or not url.startswith(("https://", "http://")):
            continue

        key = (name.casefold(), url, section, subsection)
        if key in seen:
            continue
        seen.add(key)
        entries.append(
            CatalogEntry(
                name=name,
                url=url,
                section=section,
                subsection=subsection,
            )
        )

    return entries


def fetch_readme(timeout: float = 30.0) -> str:
    request = Request(
        SOURCE_RAW,
        headers={
            "User-Agent": "shaggoth-swarm-catalog/0.3",
            "Accept": "text/plain",
        },
    )
    with urlopen(request, timeout=timeout) as response:
        body = response.read(MAX_SOURCE_BYTES + 1)
    if len(body) > MAX_SOURCE_BYTES:
        raise ValueError("catalog source exceeds maximum allowed size")
    return body.decode("utf-8")


def build_index(readme: str) -> dict:
    entries = parse_catalog(readme)
    return {
        "schema_version": 1,
        "source": {
            "id": SOURCE_ID,
            "integration_label": INTEGRATION_LABEL,
            "repository": SOURCE_REPOSITORY,
            "commit": SOURCE_COMMIT,
            "version": SOURCE_VERSION,
            "license": SOURCE_LICENSE,
            "canonical_host": SOURCE_HOST,
            "github_mirror": SOURCE_MIRROR,
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "entry_count": len(entries),
        "entries": [asdict(entry) for entry in entries],
    }


def refresh_cache(path: Path = DEFAULT_CACHE, timeout: float = 30.0) -> dict:
    index = build_index(fetch_readme(timeout=timeout))
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(index, indent=2, sort_keys=True), encoding="utf-8")
    temp.replace(path)
    return index


def load_cache(path: Path = DEFAULT_CACHE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def search_index(index: dict, query: str, limit: int = 20) -> list[dict]:
    if not 1 <= limit <= 100:
        raise ValueError("limit must be between 1 and 100")
    terms = [term.casefold() for term in query.split() if term.strip()]
    if not terms:
        return []

    results: list[dict] = []
    for entry in index.get("entries", []):
        haystack = " ".join(
            str(entry.get(field, ""))
            for field in ("name", "section", "subsection", "url")
        ).casefold()
        if all(term in haystack for term in terms):
            results.append(entry)
            if len(results) >= limit:
                break
    return results
