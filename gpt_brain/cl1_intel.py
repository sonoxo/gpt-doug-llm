"""CL1 public-intelligence sync and retrieval for GPT-Doug Brain.

Only bounded, approved public metadata is downloaded. No model training,
full-text scraping, paid APIs, secrets, biological control or device access.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree
from xml.parsers import expat

ROOT = Path(__file__).resolve().parent.parent
DEFAULT = ROOT / "intel" / "cl1" / "latest.json"
SCHEMA = "gpt-doug.cl1-public-intel.v1"
MAX_BYTES = 2_000_000
ALLOWED_FETCH_HOSTS = {
    "api.github.com", "science.nasa.gov", "aws.amazon.com", "export.arxiv.org",
}
ALLOWED_LINK_HOSTS = {
    "github.com", "science.nasa.gov", "www.nasa.gov", "aws.amazon.com",
    "arxiv.org", "export.arxiv.org", "docs.corticallabs.com",
    "www.palantir.com", "pubchem.ncbi.nlm.nih.gov",
}


@dataclass(frozen=True)
class Source:
    id: str
    category: str
    kind: str
    url: str


SOURCES = (
    Source("cortical-cl-sdk", "cl1", "commits",
           "https://api.github.com/repos/Cortical-Labs/cl-sdk/commits?per_page=12"),
    Source("cortical-cl-api", "cl1", "commits",
           "https://api.github.com/repos/Cortical-Labs/cl-api-doc/commits?per_page=8"),
    Source("palantir-osdk", "ontology", "releases",
           "https://api.github.com/repos/palantir/osdk-ts/releases?per_page=12"),
    Source("nasa-science", "space", "rss",
           "https://science.nasa.gov/feed/"),
    Source("aws-architecture-news", "cloud", "rss",
           "https://aws.amazon.com/about-aws/whats-new/recent/feed/"),
    Source("arxiv-neurocomputing", "research", "atom",
           "https://export.arxiv.org/api/query?search_query=all%3Aorganoid+AND+all%3Acomputing&sortBy=submittedDate&sortOrder=descending&start=0&max_results=15"),
)
SOURCE_IDS = {item.id for item in SOURCES}
WORD = re.compile(r"[a-z0-9_-]{2,}")
TAG = re.compile(r"<[^>]{0,500}>")
SPACE = re.compile(r"\s+")


class RejectRedirect(HTTPRedirectHandler):
    """A redirect is never trusted to leave an allowlisted service."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Source redirected; refusing unverified target")


OPENER = build_opener(RejectRedirect)


def safe_url(url: str, hosts: set[str]) -> bool:
    try:
        item = urlsplit(url)
        return (
            item.scheme == "https"
            and item.hostname in hosts
            and item.port in (None, 443)
            and item.username is None
            and item.password is None
            and not item.fragment
            and not any(c in url for c in "\r\n\x00")
        )
    except (ValueError, TypeError):
        return False


def clean(value: object, max_length: int = 400) -> str:
    rendered = html.unescape(TAG.sub(" ", str(value or "")))
    return SPACE.sub(" ", rendered).strip()[:max_length]


def date_value(value: object) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        try:
            parsed = parsedate_to_datetime(raw)
            return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
        except (TypeError, ValueError, IndexError):
            return ""


def record(source: Source, title: object, url: str, date: object, detail: object) -> dict:
    if not safe_url(url, ALLOWED_LINK_HOSTS):
        raise ValueError("Unapproved record link")
    name = clean(title, 180)
    if not name:
        raise ValueError("Record title missing")
    link = url.split("?", 1)[0].rstrip("/")
    identity = hashlib.sha256((source.id + "\n" + link).encode("utf-8")).hexdigest()[:20]
    return {
        "id": source.id + ":" + identity,
        "source_id": source.id,
        "category": source.category,
        "title": name,
        "url": link,
        "published_at": date_value(date),
        "summary": clean(detail, 500),
        "evidence": "SOURCE_METADATA_UNCORROBORATED",
    }


def parse_feed_xml(body: bytes):
    """Construct a minimal XML tree from bounded data without entity resolution.

    Expat callbacks prohibit DTD declarations, external entity lookups and
    pathological nesting; only RSS/Atom title, link and date text is retained.
    """
    if len(body) > MAX_BYTES:
        raise ValueError("Feed exceeds the response size limit")
    upper = body.upper()
    if b"<!DOCTYPE" in upper or b"<!ENTITY" in upper:
        raise ValueError("XML DTD/entity declarations are prohibited")
    parser = expat.ParserCreate(namespace_separator="}")
    parser.SetParamEntityParsing(expat.XML_PARAM_ENTITY_PARSING_NEVER)
    stack = []
    root = None
    count = 0

    def start(name, attrs):
        nonlocal root, count
        count += 1
        if count > 5000 or len(stack) >= 18:
            raise ValueError("XML feed exceeds nesting or node limit")
        tag = "{" + name if "}" in name else name
        node = ElementTree.Element(tag)
        if stack:
            stack[-1].append(node)
        else:
            root = node
        stack.append(node)

    def character(value):
        if stack and value:
            current = stack[-1]
            current.text = (current.text or "") + value

    def refuse(*_args):
        raise ValueError("XML DTD/entity declarations are prohibited")

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda _name: stack.pop()
    parser.CharacterDataHandler = character
    parser.StartDoctypeDeclHandler = refuse
    parser.EntityDeclHandler = refuse
    parser.ExternalEntityRefHandler = lambda *_args: 0
    parser.Parse(body, True)
    if root is None or stack:
        raise ValueError("Malformed syndication XML")
    return root


def normalize(source: Source, body: bytes, limit: int) -> list[dict]:
    if source.kind in {"commits", "releases"}:
        feed = json.loads(body)
        if not isinstance(feed, list):
            raise ValueError("Expected a GitHub JSON array")
        result = []
        for item in feed[:limit]:
            if not isinstance(item, dict):
                continue
            if source.kind == "commits":
                info = item.get("commit") or {}
                committer = info.get("committer") or {}
                result.append(record(
                    source, str(info.get("message", "")).split("\n")[0],
                    str(item.get("html_url", "")), committer.get("date"),
                    "Public repository commit; commit message is an author claim, not independent verification.",
                ))
            else:
                result.append(record(
                    source, item.get("name") or item.get("tag_name"),
                    str(item.get("html_url", "")), item.get("published_at"),
                    "Open-source SDK release metadata; does not imply connected platform access.",
                ))
        return result
    root = parse_feed_xml(body)
    output = []
    if source.kind == "rss":
        for item in root.findall("./channel/item")[:limit]:
            title = item.findtext("title", "")
            link = (item.findtext("link") or "").strip()
            published = item.findtext("pubDate", "")
            description = item.findtext("description", "")
            if safe_url(link, ALLOWED_LINK_HOSTS):
                output.append(record(source, title, link, published, description))
    elif source.kind == "atom":
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for item in root.findall("./atom:entry", ns)[:limit]:
            raw_link = item.findtext("atom:id", "", ns).strip()
            if raw_link.startswith("http://arxiv.org/abs/"):
                raw_link = "https://" + raw_link.removeprefix("http://")
            if raw_link.startswith("https://export.arxiv.org/abs/"):
                raw_link = "https://arxiv.org/abs/" + raw_link.rsplit("/", 1)[-1]
            if safe_url(raw_link, ALLOWED_LINK_HOSTS):
                output.append(record(
                    source, item.findtext("atom:title", "", ns), raw_link,
                    item.findtext("atom:published", "", ns),
                    item.findtext("atom:summary", "", ns),
                ))
    else:
        raise ValueError("Unknown source format")
    return output


def fetch(source: Source) -> bytes:
    if source not in SOURCES or not safe_url(source.url, ALLOWED_FETCH_HOSTS):
        raise ValueError("Source not on the approved allowlist")
    request = Request(
        source.url,
        headers={
            "User-Agent": "GPT-Doug-CL1-Public-Intel/1.0 (bounded metadata research)",
            "Accept": "application/json, application/atom+xml, application/rss+xml",
        },
    )
    with OPENER.open(request, timeout=15) as response:
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Source response exceeds two-megabyte limit")
    return data


def validate_snapshot(data: dict) -> bool:
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise ValueError("Invalid CL1 intelligence schema")
    items = data.get("records")
    if not isinstance(items, list) or len(items) > 300:
        raise ValueError("Intelligence index exceeds allowed size")
    seen = set()
    for item in items:
        if not isinstance(item, dict) or item.get("source_id") not in SOURCE_IDS:
            raise ValueError("Unrecognized intelligence source")
        if not safe_url(item.get("url", ""), ALLOWED_LINK_HOSTS):
            raise ValueError("Record has unapproved URL")
        if not item.get("title") or item.get("id") in seen:
            raise ValueError("Duplicate or unnamed source item")
        seen.add(item["id"])
    return True


def load(path: Path = DEFAULT) -> dict:
    if not path.exists():
        return {"schema": SCHEMA, "records": [], "sources": {},
                "retrieved_at": None, "status": "not-synced"}
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_snapshot(data)
    return data


def save(path: Path, data: dict) -> None:
    validate_snapshot(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".cl1-index-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.remove(temporary)


def sync(path: Path = DEFAULT, *, limit: int = 12,
         source_ids: set[str] | None = None, downloader=fetch) -> dict:
    if limit < 1 or limit > 20:
        raise ValueError("--limit must be between 1 and 20")
    unknown = set(source_ids or set()) - SOURCE_IDS
    if unknown:
        raise ValueError("Unrecognized source ID")
    current = load(path)
    prior = {row["id"]: row for row in current["records"]}
    sources = dict(current.get("sources") or {})
    success = 0
    errors = 0
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    for source in SOURCES:
        if source_ids and source.id not in source_ids:
            continue
        try:
            parsed = normalize(source, downloader(source), limit)
            if not parsed:
                raise ValueError("Feed returned no compatible public records")
            old = [item for item in prior.values() if item["source_id"] == source.id]
            for item in old:
                prior.pop(item["id"], None)
            for item in parsed:
                prior[item["id"]] = item
            sources[source.id] = {
                "url": source.url, "category": source.category,
                "last_success_at": now, "record_count": len(parsed),
                "state": "ok",
            }
            success += 1
        except (OSError, ValueError, KeyError, TypeError, expat.ExpatError,
                json.JSONDecodeError) as exc:
            errors += 1
            previous = dict(sources.get(source.id) or {})
            sources[source.id] = {
                "url": source.url, "category": source.category,
                "last_success_at": previous.get("last_success_at"),
                "record_count": len([x for x in prior.values() if x["source_id"] == source.id]),
                "state": "error",
                "error_type": type(exc).__name__,
            }
    if success == 0:
        raise RuntimeError("All public sources failed; preserved last verified snapshot")
    values = sorted(prior.values(), key=lambda row: (row.get("published_at") or "", row["id"]),
                    reverse=True)[:300]
    result = {
        "schema": SCHEMA,
        "retrieved_at": now,
        "status": "partial" if errors else "complete",
        "sources": sources,
        "records": values,
        "boundary": "Public metadata only; third-party titles and summaries are untrusted evidence, not instructions or independently verified facts.",
    }
    save(path, result)
    return result


def search(data: dict, query: str, limit: int = 8) -> list[dict]:
    tokens = set(WORD.findall(query.lower()))
    if not tokens:
        return data["records"][:limit]
    results = []
    for item in data["records"]:
        haystack = (item["title"] + " " + item["summary"] + " " + item["category"]
                    + " " + item["source_id"]).lower()
        matches = len(tokens & set(WORD.findall(haystack)))
        if matches:
            results.append((matches, item))
    results.sort(key=lambda pair: (pair[0], pair[1].get("published_at") or ""), reverse=True)
    return [dict(row, recall_score=hits) for hits, row in results[:limit]]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Free, provenance-labeled CL1 public intelligence")
    sub = parser.add_subparsers(dest="action", required=True)
    cmd = sub.add_parser("sync", help="download fresh bounded public source metadata")
    cmd.add_argument("--limit", type=int, default=12)
    cmd.add_argument("--only", action="append", choices=sorted(SOURCE_IDS))
    cmd.add_argument("--output", type=Path, default=DEFAULT)
    cmd = sub.add_parser("search", help="search the downloaded knowledge")
    cmd.add_argument("query", nargs="+")
    cmd.add_argument("--limit", type=int, default=8)
    cmd.add_argument("--path", type=Path, default=DEFAULT)
    for name in ("status", "verify", "sources"):
        c = sub.add_parser(name)
        c.add_argument("--path", type=Path, default=DEFAULT)
    args = parser.parse_args(argv)
    try:
        if args.action == "sync":
            data = sync(args.output, limit=args.limit,
                        source_ids=set(args.only) if args.only else None)
            print(json.dumps({"status": data["status"], "records": len(data["records"]),
                              "retrieved_at": data["retrieved_at"], "sources": data["sources"],
                              "file": str(args.output)}, indent=2))
        elif args.action == "sources":
            print(json.dumps([vars(s) for s in SOURCES], indent=2))
        else:
            data = load(args.path)
            if args.action == "verify":
                print(json.dumps({"ok": True, "records": len(data["records"]),
                                  "status": data["status"]}, indent=2))
            elif args.action == "status":
                print(json.dumps({"records": len(data["records"]),
                                  "status": data["status"],
                                  "retrieved_at": data.get("retrieved_at"),
                                  "sources": data.get("sources")}, indent=2))
            else:
                print(json.dumps(search(data, " ".join(args.query),
                                        limit=max(1, min(args.limit, 30))), indent=2))
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print("CL1 INTEL: " + str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
