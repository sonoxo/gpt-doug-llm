#!/usr/bin/env python3
"""Bounded, permission-based public website evidence crawler.

Requires explicit authorization: --allow-host must match --base-url.
Honors robots.txt, same-host boundaries, safe HTTP(S), timeouts and size limits.
Never fetches .onion URLs or credentials. Standard library only.
"""
from __future__ import annotations

import argparse
import html.parser
import ipaddress
import json
import socket
import sys
import time
from collections import deque
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urldefrag, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

USER_AGENT = "XUNIA-AuthorizedAudit/1.0 (+https://xunia.org/darkweb/)"
MAX_BYTES = 512_000
MAX_PAGES = 50
REDIRECT_LIMIT = 5


class PageLinks(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []
        self.title = ""
        self._title = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "a" and "href" in values:
            self.hrefs.append(values["href"])
        if tag == "title":
            self._title = True

    def handle_endtag(self, tag):
        if tag == "title":
            self._title = False

    def handle_data(self, data):
        if self._title:
            self.title += data


def host_is_public(host: str) -> bool:
    """Disallow local network and IP-literal fetches to prevent SSRF."""
    if host.lower() in {"localhost"} or host.lower().endswith((".local", ".internal", ".onion")):
        return False
    try:
        ipaddress.ip_address(host)
        return False
    except ValueError:
        return bool(host and "." in host)


def verified_addresses(host: str) -> bool:
    """Fail closed on local, private, or reserved DNS responses."""
    try:
        answers = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
        ips = [ipaddress.ip_address(a[4][0]) for a in answers]
        return bool(ips) and all(ip.is_global for ip in ips)
    except (OSError, ValueError):
        return False


def allowed_url(value: str, allow_host: str) -> bool:
    try:
        p = urlsplit(value)
        return (p.scheme == "https" and p.hostname == allow_host
                and p.username is None and p.password is None
                and p.port in {None, 443} and host_is_public(allow_host))
    except ValueError:
        return False


class RestrictedRedirect(HTTPRedirectHandler):
    def __init__(self, allow_host):
        super().__init__()
        self.allow_host = allow_host
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        if self.count > REDIRECT_LIMIT or not allowed_url(newurl, self.allow_host):
            raise ValueError("Redirect outside explicitly authorized HTTPS host")
        if not verified_addresses(self.allow_host):
            raise ValueError("Target no longer resolves to global addresses")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch(url: str, allow_host: str, timeout: float) -> tuple[bytes, str]:
    if not allowed_url(url, allow_host) or not verified_addresses(allow_host):
        raise ValueError("URL or target DNS does not pass scope checks")
    opener = build_opener(RestrictedRedirect(allow_host))
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.8"})
    with opener.open(request, timeout=timeout) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if not (content_type.startswith("text/html") or content_type.startswith("text/plain")):
            raise ValueError("Response is not an HTML or text document")
        if int(response.headers.get("Content-Length", "0") or 0) > MAX_BYTES:
            raise ValueError("Document exceeds size limit")
        content = response.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError("Document exceeds size limit")
        return content, response.geturl()


def crawl(base: str, host: str, max_pages: int, delay: float, timeout: float):
    if not allowed_url(base, host):
        raise ValueError("Only the exact allowlisted HTTPS host is permitted")
    if not verified_addresses(host):
        raise ValueError("Host is not publicly resolvable to global IP addresses")
    robots_url = f"https://{host}/robots.txt"
    robot = RobotFileParser()
    robot.set_url(robots_url)
    try:
        data, _ = fetch_robots(robots_url, host, timeout)
        robot.parse(data.decode("utf-8", "replace").splitlines())
    except HTTPError as exc:
        if exc.code == 404:
            robot.parse([])
        else:
            raise ValueError(f"Cannot verify robots.txt: HTTP {exc.code}") from exc
    except Exception as exc:
        raise ValueError(f"Cannot verify robots.txt: {exc}") from exc
    pending = deque([base])
    seen = set()
    while pending and len(seen) < max_pages:
        url = pending.popleft()
        if url in seen or not allowed_url(url, host):
            continue
        if not robot.can_fetch(USER_AGENT, url):
            continue
        seen.add(url)
        try:
            raw, final_url = fetch(url, host, timeout)
            parser = PageLinks()
            parser.feed(raw.decode("utf-8", "replace"))
            yield {"url": final_url, "title": parser.title.strip()[:180],
                   "bytes": len(raw), "source": "authorized-site-audit",
                   "observed": datetime.now(timezone.utc).isoformat()}
            for href in parser.hrefs:
                candidate = urldefrag(urljoin(final_url, href))[0]
                if allowed_url(candidate, host) and candidate not in seen and candidate not in pending:
                    pending.append(candidate)
        except Exception as exc:
            yield {"url": url, "error": str(exc), "source": "authorized-site-audit"}
        if pending:
            time.sleep(delay)


def fetch_robots(url: str, host: str, timeout: float):
    if not verified_addresses(host):
        raise ValueError("Unsafe DNS response")
    opener = build_opener(RestrictedRedirect(host))
    with opener.open(Request(url, headers={"User-Agent": USER_AGENT}), timeout=timeout) as response:
        data = response.read(256_001)
        if len(data) > 256_000:
            raise ValueError("Oversized robots.txt")
        return data, response.geturl()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--allow-host", required=True)
    parser.add_argument("--max-pages", type=int, default=10)
    parser.add_argument("--delay", type=float, default=2.0)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--authorized", action="store_true",
                        help="Affirm written authorization or ownership of the target")
    opts = parser.parse_args(argv)
    host = opts.allow_host.lower().strip()
    if not opts.authorized:
        parser.error("Explicit authorization acknowledgement required: --authorized")
    if not 1 <= opts.max_pages <= MAX_PAGES:
        parser.error("--max-pages must be between 1 and 50")
    if opts.delay < 1 or not 1 <= opts.timeout <= 20:
        parser.error("Minimum delay 1s; timeout 1-20s")
    try:
        for row in crawl(opts.base_url, host, opts.max_pages, opts.delay, opts.timeout):
            print(json.dumps(row, ensure_ascii=False))
        return 0
    except ValueError as exc:
        print(f"Blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
