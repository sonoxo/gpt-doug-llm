"""Bounded HTTP for explicitly configured loopback servers. No redirects or proxies."""
from __future__ import annotations

import re
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener
from typing import Any

from .validation import MAX_BYTES, bounded_int, decode_json, encode_json, finite_number


def normalize_loopback_url(url: str) -> str:
    if not isinstance(url, str) or not url or any(ord(c) <= 32 or ord(c) >= 127 for c in url):
        raise ValueError('loopback URL must contain printable ASCII without whitespace')
    if '?' in url or '#' in url or '\\' in url:
        raise ValueError('loopback URL cannot contain query, fragment or backslash')
    try:
        parts = urlsplit(url)
        host, port = parts.hostname, parts.port
    except ValueError as exc:
        raise ValueError('invalid loopback URL') from exc
    if (parts.scheme != 'http' or host not in ('127.0.0.1', 'localhost', '::1') or
            parts.username is not None or parts.password is not None or
            parts.path not in ('', '/') or parts.netloc.endswith(':') or
            (port is not None and not 1 <= port <= 65535)):
        raise ValueError('only HTTP loopback base URLs with valid ports are supported')
    host = '[::1]' if host == '::1' else '127.0.0.1'
    return 'http://' + host + (':' + str(port) if port is not None else '')


class _NoRedirect(HTTPRedirectHandler):
    def http_error_302(self, req, fp, code, msg, headers):
        fp.close()
        raise HTTPError(req.full_url, code, 'redirect refused', {}, None)
    http_error_301 = http_error_302
    http_error_303 = http_error_302
    http_error_307 = http_error_302
    http_error_308 = http_error_302


def request_json(base_url: str, path: str, payload: dict[str, Any] | None,
                 *, timeout: float, max_bytes: int = MAX_BYTES) -> dict[str, Any]:
    url = normalize_loopback_url(base_url)
    if not isinstance(path, str) or not re.fullmatch(r'/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_-]+', path):
        raise ValueError('invalid relative API path')
    timeout = finite_number(timeout, name='timeout', minimum=0, exclusive_minimum=True)
    bounded_int(max_bytes, name='max_bytes', minimum=1, maximum=MAX_BYTES)
    if payload is not None and not isinstance(payload, dict):
        raise ValueError('request must be a JSON object')
    data = None if payload is None else encode_json(payload, max_bytes=max_bytes)
    request = Request(url + path, data=data,
                      headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
                      method='GET' if data is None else 'POST')
    try:
        with build_opener(ProxyHandler({}), _NoRedirect()).open(request, timeout=timeout) as response:
            lengths = response.headers.get_all('Content-Length', [])
            if len(lengths) > 1 or (lengths and (not lengths[0].isascii() or
                    not lengths[0].isdecimal() or int(lengths[0]) > max_bytes)):
                raise ValueError('invalid or oversized response length')
            # This is a socket inactivity timeout, not a wall-clock deadline.
            # The fleet supervisor supplies the absolute deadline in its own process.
            raw = response.read(max_bytes + 1)
    except OverflowError:
        raise ValueError('timeout is not representable by this platform') from None
    except HTTPError as exc:
        code = exc.code
        exc.close()
        raise HTTPError(url + path, code, 'local HTTP request rejected', {}, None) from None
    result = decode_json(raw, max_bytes=max_bytes)
    if not isinstance(result, dict):
        raise ValueError('provider response must be a JSON object')
    return result
