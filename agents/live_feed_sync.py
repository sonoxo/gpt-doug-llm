#!/usr/bin/env python3
"""Allowlisted public-source sync for defensive intelligence.

This module only performs HTTPS GET requests to explicitly allowlisted public
sources. It does not scan, target, authenticate to, or modify third-party
systems. Snapshots and diffs are written under intel/live/ for local analysis.
"""
from __future__ import annotations

import hashlib
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

CISA_KEV_URL = "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json"
CISA_KEV_FALLBACK = "https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"
IC3_PSA_URL = "https://www.ic3.gov/PSA"
_ALLOWED_HOSTS = {"www.cisa.gov", "raw.githubusercontent.com", "www.ic3.gov"}
_USER_AGENT = "ZYRA-Defensive-Intel/1.0 (+public-source-sync)"


class LiveFeedError(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS:
        raise LiveFeedError(f"source is not allowlisted: {url}")


def _fetch(url: str, *, timeout: int = 20) -> bytes:
    _validate_url(url)
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT, "Accept": "application/json,text/html;q=0.9,*/*;q=0.1"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # nosec B310 - URL host is allowlisted above
            final_url = response.geturl()
            _validate_url(final_url)
            if getattr(response, "status", 200) != 200:
                raise LiveFeedError(f"HTTP {response.status} from {url}")
            return response.read()
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise LiveFeedError(f"fetch failed for {url}: {exc}") from exc


class _IC3Parser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._href: str | None = None
        self._text: list[str] = []
        self.items: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href and re.fullmatch(r"/PSA/20\d{2}/PSA\d+", href):
            self._href = href
            self._text = []

    def handle_data(self, data: str) -> None:
        if self._href:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            title = " ".join("".join(self._text).split())
            url = urljoin(IC3_PSA_URL, self._href)
            self.items.append({"url": url, "title": title or self._href.rsplit("/", 1)[-1]})
            self._href = None
            self._text = []


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _sync_kev() -> tuple[dict, str, str]:
    errors: list[str] = []
    for url in (CISA_KEV_URL, CISA_KEV_FALLBACK):
        try:
            raw = _fetch(url)
            payload = json.loads(raw.decode("utf-8"))
            if not isinstance(payload.get("vulnerabilities"), list):
                raise LiveFeedError("KEV payload missing vulnerabilities list")
            return payload, url, _sha256(raw)
        except (LiveFeedError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(str(exc))
    raise LiveFeedError("; ".join(errors))


def _sync_ic3() -> tuple[list[dict[str, str]], str]:
    raw = _fetch(IC3_PSA_URL)
    parser = _IC3Parser()
    parser.feed(raw.decode("utf-8", errors="replace"))
    dedup = {item["url"]: item for item in parser.items}
    items = [dedup[url] for url in sorted(dedup, reverse=True)]
    return items, _sha256(raw)


def sync_live_sources(root: str | Path) -> str:
    root = Path(root)
    live_dir = root / "intel" / "live"
    previous_kev = _read_json(live_dir / "cisa-kev.json", {})
    previous_ic3 = _read_json(live_dir / "ic3-psa-index.json", [])

    kev, kev_source, kev_hash = _sync_kev()
    ic3_items, ic3_hash = _sync_ic3()

    old_cves = {str(item.get("cveID")) for item in previous_kev.get("vulnerabilities", []) if item.get("cveID")}
    new_cves = {str(item.get("cveID")) for item in kev.get("vulnerabilities", []) if item.get("cveID")}
    old_ic3 = {str(item.get("url")) for item in previous_ic3 if item.get("url")}
    new_ic3 = {str(item.get("url")) for item in ic3_items if item.get("url")}

    added_cve_ids = sorted(new_cves - old_cves)
    removed_cve_ids = sorted(old_cves - new_cves)
    added_ic3_urls = sorted(new_ic3 - old_ic3)
    removed_ic3_urls = sorted(old_ic3 - new_ic3)
    kev_by_id = {str(item.get("cveID")): item for item in kev.get("vulnerabilities", []) if item.get("cveID")}
    ic3_by_url = {item["url"]: item for item in ic3_items}

    changes = {
        "syncedAt": _now(),
        "cisaKev": {
            "source": kev_source,
            "catalogVersion": kev.get("catalogVersion"),
            "count": kev.get("count", len(new_cves)),
            "added": [kev_by_id[cve] for cve in added_cve_ids],
            "removedCveIds": removed_cve_ids,
        },
        "ic3Psa": {
            "source": IC3_PSA_URL,
            "count": len(ic3_items),
            "added": [ic3_by_url[url] for url in added_ic3_urls],
            "removedUrls": removed_ic3_urls,
        },
    }
    state = {
        "syncedAt": changes["syncedAt"],
        "sources": {
            "cisaKev": {"url": kev_source, "sha256": kev_hash, "count": len(new_cves), "catalogVersion": kev.get("catalogVersion")},
            "ic3Psa": {"url": IC3_PSA_URL, "sha256": ic3_hash, "count": len(ic3_items)},
        },
        "changeCounts": {
            "newCves": len(added_cve_ids),
            "removedCves": len(removed_cve_ids),
            "newIc3Advisories": len(added_ic3_urls),
            "removedIc3Advisories": len(removed_ic3_urls),
        },
    }

    _write_json(live_dir / "cisa-kev.json", kev)
    _write_json(live_dir / "ic3-psa-index.json", ic3_items)
    _write_json(live_dir / "live-changes.json", changes)
    _write_json(live_dir / "live-state.json", state)

    return (
        "🌐 ZYRA LIVE SYNC ✅\n"
        f"Synced: {state['syncedAt']}\n"
        f"CISA KEV: {len(new_cves)} entries | +{len(added_cve_ids)} / -{len(removed_cve_ids)}\n"
        f"FBI/IC3 PSA index: {len(ic3_items)} entries | +{len(added_ic3_urls)} / -{len(removed_ic3_urls)}\n"
        "Saved: intel/live/live-state.json + intel/live/live-changes.json\n"
        "Scope: allowlisted public HTTPS GET only; no scanning, auth, targeting, push, deploy, or remote changes."
    )


def live_status(root: str | Path) -> str:
    state = _read_json(Path(root) / "intel" / "live" / "live-state.json", None)
    if not state:
        return "🌐 ZYRA LIVE STATUS // no snapshot yet. Run /live-sync."
    counts = state.get("changeCounts") or {}
    sources = state.get("sources") or {}
    return (
        "🌐 ZYRA LIVE STATUS\n"
        f"Last sync: {state.get('syncedAt')}\n"
        f"CISA KEV: {(sources.get('cisaKev') or {}).get('count', 0)} entries | new {counts.get('newCves', 0)}\n"
        f"FBI/IC3 PSA: {(sources.get('ic3Psa') or {}).get('count', 0)} entries | new {counts.get('newIc3Advisories', 0)}\n"
        "Use /live-changes for the latest diff."
    )


def live_changes(root: str | Path) -> str:
    changes = _read_json(Path(root) / "intel" / "live" / "live-changes.json", None)
    if not changes:
        return "🌐 ZYRA LIVE CHANGES // no diff yet. Run /live-sync."
    kev_added = (changes.get("cisaKev") or {}).get("added") or []
    ic3_added = (changes.get("ic3Psa") or {}).get("added") or []
    lines = [f"🌐 ZYRA LIVE CHANGES // {changes.get('syncedAt')}"]
    lines.append(f"New CISA KEV entries: {len(kev_added)}")
    for item in kev_added[:20]:
        lines.append(f"- {item.get('cveID')} | {item.get('vendorProject')} {item.get('product')} | added {item.get('dateAdded')}")
    if len(kev_added) > 20:
        lines.append(f"- ... {len(kev_added) - 20} more")
    lines.append(f"New FBI/IC3 advisories: {len(ic3_added)}")
    for item in ic3_added[:20]:
        lines.append(f"- {item.get('title')} | {item.get('url')}")
    if len(ic3_added) > 20:
        lines.append(f"- ... {len(ic3_added) - 20} more")
    return "\n".join(lines)
