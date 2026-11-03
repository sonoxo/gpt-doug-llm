#!/usr/bin/env python3
"""XUNIA Open Web Mirror: local text snapshot + provenance and link graph.

Free Python standard library only. Crawl ONLY an explicitly approved HTTPS host.
This is a small offline archive, not a copy of the entire Internet.
Reuses the existing XUNIA authorized crawler's DNS, URL, redirect and robots gates.
No JS execution, authentication, media downloads or credential capture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import xunia_authorized_crawl as guard

SCHEMA = "xunia.open-web-mirror.v1"
USER_AGENT = guard.USER_AGENT
BINARY_PATH = re.compile(r"\.(?:pdf|zip|gz|tar|exe|dmg|pkg|mp3|mp4|mov|webm|jpg|jpeg|png|gif|svg|webp|woff2?|ttf|css|js|mjs|json|xml|ico)$", re.I)
PRIVATE_PATH = re.compile(r"(?:^|/)(?:login|logout|signin|signout|admin|private|account|profile|settings|checkout|cart|password|reset|oauth|callback)(?:/|$)", re.I)
SKIP_TAGS = {"script", "style", "noscript", "svg", "template", "form", "iframe", "object", "canvas"}
BLOCK_TAGS = {"p", "div", "br", "li", "ul", "ol", "h1", "h2", "h3", "h4", "h5", "h6", "header", "main", "article", "section"}
MAX_TEXT = 12_000
MAX_EXTERNAL_HOSTS = 80


def normalize_url(url: str, host: str) -> str | None:
    """Strip fragments and query strings (potential tokens) and reject private paths."""
    try:
        p = urlsplit(url.strip())
        normalized = urlunsplit((p.scheme, p.netloc, p.path or "/", "", ""))
        if not guard.allowed_url(normalized, host):
            return None
        if BINARY_PATH.search(p.path) or PRIVATE_PATH.search(p.path):
            return None
        return normalized
    except (ValueError, AttributeError):
        return None


def outbound_host(url: str, own_host: str) -> str | None:
    try:
        p = urlsplit(url)
        hostname = (p.hostname or "").lower()
        if p.scheme != "https" or p.username or p.password or p.port not in (None, 443):
            return None
        if hostname == own_host or not guard.host_is_public(hostname):
            return None
        return hostname
    except ValueError:
        return None


class PageText(HTMLParser):
    """Extract readable page text and hrefs without executing or storing HTML."""
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title = ""
        self.parts: list[str] = []
        self.hrefs: list[str] = []
        self.noindex = False
        self.nofollow = False
        self.skip_depth = 0
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        vals = dict(attrs)
        if tag in SKIP_TAGS:
            self.skip_depth += 1
        if tag == "title":
            self.in_title = True
        if tag == "meta" and (vals.get("name") or "").lower() in {"robots", "xunia-authorizedaudit"}:
            directives = (vals.get("content") or "").lower()
            self.noindex |= "noindex" in directives or "none" in directives
            self.nofollow |= "nofollow" in directives or "none" in directives
        if self.skip_depth == 0 and tag == "a" and vals.get("href"):
            self.hrefs.append(vals["href"])
        if self.skip_depth == 0 and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in SKIP_TAGS and self.skip_depth > 0:
            self.skip_depth -= 1
        if tag == "title":
            self.in_title = False
        if self.skip_depth == 0 and tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.in_title:
            self.title += data
        else:
            self.parts.append(data)

    def text(self) -> str:
        joined = "".join(self.parts)
        return "\n".join(
            line.strip() for line in re.split(r"\n+", joined)
            if line.strip()
        )[:MAX_TEXT]


def robots_for(host: str, timeout: float) -> RobotFileParser:
    if not guard.host_is_public(host) or not guard.verified_addresses(host):
        raise ValueError("Public HTTPS and safe DNS resolution required")
    url = "https://" + host + "/robots.txt"
    parser = RobotFileParser()
    parser.set_url(url)
    try:
        data, _ = guard.fetch_robots(url, host, timeout)
        parser.parse(data.decode("utf-8", "replace").splitlines())
    except HTTPError as exc:
        # RFC 9309 permits access on 404, but fail closed for other HTTP errors.
        if exc.code == 404:
            parser.parse([])
        else:
            raise ValueError("robots.txt unavailable: HTTP " + str(exc.code)) from exc
    except Exception as exc:
        raise ValueError("robots.txt unreachable, blocked: " + str(exc)) from exc
    return parser


def mirror(base_url: str, host: str, max_pages: int = 20,
           max_depth: int = 2, delay: float = 2.0, timeout: float = 8.0,
           robots: RobotFileParser | None = None,
           fetcher=None, sleeper=None) -> dict:
    if not 1 <= max_pages <= 50 or not 0 <= max_depth <= 3:
        raise ValueError("Maximum 50 pages and depth 0-3")
    if delay < 1 or not 1 <= timeout <= 20:
        raise ValueError("Minimum delay 1 second, timeout 1-20 seconds")
    start = normalize_url(base_url, host)
    if not start:
        raise ValueError("Seed must be a public allowlisted HTTPS URL")
    if not guard.verified_addresses(host):
        raise ValueError("Host does not resolve to global IP addresses")
    rules = robots if robots is not None else robots_for(host, timeout)
    fetch_page = fetcher or guard.fetch
    pause = sleeper or time.sleep
    pending = deque([(start, 0)])
    enqueued = {start}
    seen: set[str] = set()
    pages: list[dict] = []
    edges: set[tuple[str, str]] = set()
    outside: dict[str, int] = {}
    skipped = {"robots": 0, "noindex": 0, "error": 0}
    while pending and len(seen) < max_pages:
        url, depth = pending.popleft()
        if url in seen:
            continue
        seen.add(url)
        if not rules.can_fetch(USER_AGENT, url):
            skipped["robots"] += 1
            continue
        if pages:
            pause(delay)
        try:
            raw, final = fetch_page(url, host, timeout)
            final = normalize_url(final, host)
            if not final:
                raise ValueError("Redirect left allowed HTTPS scope")
            decoder = PageText()
            decoder.feed(raw.decode("utf-8", "replace"))
            if decoder.noindex:
                skipped["noindex"] += 1
                continue
            text = decoder.text()
            if not text.strip():
                continue
            sha = hashlib.sha256(raw).hexdigest()
            pages.append({
                "url": final, "title": decoder.title.strip()[:160] or final,
                "text": text, "bytes": len(raw), "sha256": sha,
                "depth": depth, "observedAt": datetime.now(timezone.utc).isoformat()
            })
            if not decoder.nofollow and depth < max_depth:
                for href in decoder.hrefs[:150]:
                    target = urljoin(final, href)
                    approved = normalize_url(target, host)
                    if approved and approved != final:
                        edges.add((final, approved))
                        if approved not in seen and approved not in enqueued:
                            pending.append((approved, depth + 1))
                            enqueued.add(approved)
                    else:
                        ext = outbound_host(target, host)
                        if ext and len(outside) < MAX_EXTERNAL_HOSTS:
                            outside[ext] = outside.get(ext, 0) + 1
        except Exception as exc:
            skipped["error"] += 1
            # Do not include arbitrary exception strings: they can leak URLs/tokens.
            print("Skipped page due to " + type(exc).__name__, file=sys.stderr)
    # Only link to actually archived nodes; do not suggest unseen pages are cloned.
    stored = {p["url"] for p in pages}
    return {
        "schema": SCHEMA,
        "mode": "authorized-public-text-snapshot",
        "origin": start, "allowedHost": host,
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "limits": {"maxPages": max_pages, "maxDepth": max_depth,
                   "delaySeconds": delay, "maxDocumentBytes": guard.MAX_BYTES},
        "coverage": {"pagesStored": len(pages), "pagesVisited": len(seen),
                     "completeInternet": False, "skipped": skipped},
        "policy": {"robotsEnforced": True, "sameHostOnly": True,
                   "authenticationUsed": False, "javascriptExecuted": False,
                   "binaryFilesDownloaded": False, "textOnly": True,
                   "thirdPartyDomainsFetched": False},
        "pages": pages,
        "edges": [{"source": a, "target": b} for a, b in sorted(edges)
                  if a in stored and b in stored],
        "outboundDomains": [{"host": name, "references": count}
                            for name, count in sorted(outside.items(), key=lambda item: -item[1])]
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-url", default="https://xunia.org/")
    ap.add_argument("--allow-host", default="xunia.org")
    ap.add_argument("--authorized", action="store_true",
                    help="Affirm you own this domain or have explicit crawl permission")
    ap.add_argument("--max-pages", type=int, default=20)
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--delay", type=float, default=2)
    ap.add_argument("--timeout", type=float, default=8)
    ap.add_argument("--out", type=Path, default=Path("xunia-open-web-snapshot.json"))
    a = ap.parse_args(argv)
    if not a.authorized:
        ap.error("--authorized required: you must own or have crawl permission for the host")
    try:
        result = mirror(a.base_url, a.allow_host.lower(), a.max_pages,
                        a.max_depth, a.delay, a.timeout)
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("Saved " + str(len(result["pages"])) + " permitted text pages to " + str(a.out))
        return 0
    except (OSError, ValueError) as exc:
        print("XUNIA MIRROR BLOCKED: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
