from __future__ import annotations

import json
import math
import statistics
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from typing import Callable, Final

CACHE_TTL_SECONDS: Final = 300
HTTP_TIMEOUT_SECONDS: Final = 8
USER_AGENT: Final = "GPT-DOUG-Global-Intel/1.0 (+public-source; read-only)"
ALLOWED_SOURCE_HOSTS: Final = {
    "earthquake.usgs.gov",
    "eonet.gsfc.nasa.gov",
    "services.swpc.noaa.gov",
    "www.cisa.gov",
    "api.worldbank.org",
}

SAFE_INTEL_POLICY: Final = {
    "mode": "PUBLIC_STRATEGIC_ONLY",
    "allowed": [
        "public cyber-defense indicators",
        "natural hazards",
        "space weather",
        "environmental events",
        "aggregate development indicators",
        "source health and provenance benchmarking",
    ],
    "blocked": [
        "real-time military unit locations",
        "weapon targeting",
        "strike planning",
        "payload release",
        "private-person surveillance",
        "unauthorized access",
    ],
    "note": (
        "This layer is strategic/public-source situational awareness and source-quality "
        "benchmarking. It is not a tactical ISR or targeting service."
    ),
}

SOURCE_DEFINITIONS: Final = [
    {
        "id": "usgs-earthquakes",
        "name": "USGS Earthquake GeoJSON",
        "domain": "NATURAL_HAZARDS",
        "authority": "U.S. Geological Survey",
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
        "cadence": "minutes",
        "expectedFreshnessSeconds": 1800,
    },
    {
        "id": "nasa-eonet",
        "name": "NASA EONET Open Natural Events",
        "domain": "ENVIRONMENT",
        "authority": "NASA GSFC",
        "url": "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30&limit=100",
        "cadence": "event-driven",
        "expectedFreshnessSeconds": 86400,
    },
    {
        "id": "noaa-swpc-kp",
        "name": "NOAA SWPC Planetary K-index",
        "domain": "SPACE_WEATHER",
        "authority": "NOAA Space Weather Prediction Center",
        "url": "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
        "cadence": "near-real-time",
        "expectedFreshnessSeconds": 7200,
    },
    {
        "id": "cisa-kev",
        "name": "CISA Known Exploited Vulnerabilities",
        "domain": "CYBER_DEFENSE",
        "authority": "Cybersecurity and Infrastructure Security Agency",
        "url": "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
        "cadence": "catalog",
        "expectedFreshnessSeconds": 604800,
    },
    {
        "id": "world-bank-internet",
        "name": "World Bank Internet Usage Indicator",
        "domain": "STRUCTURAL_CONTEXT",
        "authority": "World Bank",
        "url": (
            "https://api.worldbank.org/v2/country/WLD/indicator/"
            "IT.NET.USER.ZS?format=json&per_page=8"
        ),
        "cadence": "annual",
        "expectedFreshnessSeconds": 94608000,
    },
]

_cache_lock = threading.Lock()
_cache: dict = {"expires": 0.0, "value": None}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def _parse_iso(value: object) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip().replace("Z", "+00:00")
    try:
        result = datetime.fromisoformat(raw)
        if result.tzinfo is None:
            result = result.replace(tzinfo=timezone.utc)
        return result.astimezone(timezone.utc)
    except ValueError:
        return None


def _fetch_json(url: str) -> tuple[object, int]:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in ALLOWED_SOURCE_HOSTS:
        raise ValueError("source URL is outside the approved HTTPS allowlist")
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,application/geo+json;q=0.9,*/*;q=0.5",
        },
    )
    started = time.perf_counter()
    with urllib.request.urlopen(  # nosec B310 - HTTPS host allowlist validated above
        request, timeout=HTTP_TIMEOUT_SECONDS
    ) as response:
        payload = response.read(6 * 1024 * 1024)
    elapsed_ms = int((time.perf_counter() - started) * 1000)
    return json.loads(payload.decode("utf-8")), elapsed_ms


def _point(
    source_id: str,
    title: str,
    category: str,
    lon: object,
    lat: object,
    severity: str = "INFO",
) -> dict | None:
    try:
        longitude = float(lon)
        latitude = float(lat)
    except (TypeError, ValueError):
        return None
    if not (-180 <= longitude <= 180 and -90 <= latitude <= 90):
        return None
    return {
        "sourceId": source_id,
        "title": str(title)[:160],
        "category": str(category)[:64],
        "longitude": round(longitude, 5),
        "latitude": round(latitude, 5),
        "severity": severity,
    }


def _usgs(payload: object) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("features"), list):
        raise ValueError("unexpected USGS GeoJSON schema")
    features = payload["features"]
    generated = payload.get("metadata", {}).get("generated")
    observed_at = None
    if isinstance(generated, (int, float)):
        observed_at = datetime.fromtimestamp(float(generated) / 1000, timezone.utc)

    magnitudes = []
    points = []
    significant = 0
    for feature in features:
        if not isinstance(feature, dict):
            continue
        props = feature.get("properties") or {}
        geometry = feature.get("geometry") or {}
        coordinates = geometry.get("coordinates") or []
        magnitude = props.get("mag")
        if isinstance(magnitude, (int, float)):
            magnitudes.append(float(magnitude))
            if magnitude >= 4.5:
                significant += 1
        if len(coordinates) >= 2 and len(points) < 80:
            severity = "HIGH" if isinstance(magnitude, (int, float)) and magnitude >= 6 else (
                "MEDIUM" if isinstance(magnitude, (int, float)) and magnitude >= 4.5 else "INFO"
            )
            item = _point(
                "usgs-earthquakes",
                props.get("place") or "Earthquake",
                "EARTHQUAKE",
                coordinates[0],
                coordinates[1],
                severity,
            )
            if item:
                points.append(item)
    return {
        "schemaValid": True,
        "observedAt": _iso(observed_at),
        "summary": {
            "events24h": len(features),
            "magnitude45Plus": significant,
            "maxMagnitude": round(max(magnitudes), 2) if magnitudes else None,
        },
        "mapPoints": points,
    }


def _eonet(payload: object) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("events"), list):
        raise ValueError("unexpected NASA EONET schema")
    events = payload["events"]
    categories: Counter[str] = Counter()
    points = []
    latest = None
    for event in events:
        if not isinstance(event, dict):
            continue
        cats = event.get("categories") or []
        category = cats[0].get("title") if cats and isinstance(cats[0], dict) else "Natural Event"
        categories[str(category)] += 1
        geometry = event.get("geometry") or []
        if geometry:
            last = geometry[-1] if isinstance(geometry[-1], dict) else {}
            observed = _parse_iso(last.get("date"))
            if observed and (latest is None or observed > latest):
                latest = observed
            coordinates = last.get("coordinates") or []
            if len(coordinates) >= 2 and len(points) < 80:
                item = _point(
                    "nasa-eonet",
                    event.get("title") or "Natural event",
                    category,
                    coordinates[0],
                    coordinates[1],
                    "MEDIUM",
                )
                if item:
                    points.append(item)
    return {
        "schemaValid": True,
        "observedAt": _iso(latest),
        "summary": {
            "openEvents": len(events),
            "topCategories": categories.most_common(8),
        },
        "mapPoints": points,
    }


def _swpc(payload: object) -> dict:
    if not isinstance(payload, list) or len(payload) < 2:
        raise ValueError("unexpected NOAA SWPC K-index schema")
    header = payload[0]
    if not isinstance(header, list):
        raise ValueError("NOAA SWPC header missing")
    names = [str(item).strip().lower() for item in header]
    rows = [row for row in payload[1:] if isinstance(row, list) and len(row) == len(header)]
    if not rows:
        raise ValueError("NOAA SWPC contains no data rows")
    last = rows[-1]
    record = dict(zip(names, last))
    time_value = (
        record.get("time_tag")
        or record.get("time tag")
        or record.get("timestamp")
        or record.get("time")
    )
    observed_at = _parse_iso(time_value)
    kp_value = None
    for key, value in record.items():
        if "kp" in key or "k-index" in key or "k_index" in key:
            try:
                kp_value = float(value)
                break
            except (TypeError, ValueError):
                continue
    return {
        "schemaValid": True,
        "observedAt": _iso(observed_at),
        "summary": {
            "planetaryKp": round(kp_value, 2) if kp_value is not None else None,
            "stormScale": (
                "G5"
                if kp_value is not None and kp_value >= 9
                else "G4"
                if kp_value is not None and kp_value >= 8
                else "G3"
                if kp_value is not None and kp_value >= 7
                else "G2"
                if kp_value is not None and kp_value >= 6
                else "G1"
                if kp_value is not None and kp_value >= 5
                else "BELOW_G1"
            ),
        },
        "mapPoints": [],
    }


def _cisa(payload: object) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("vulnerabilities"), list):
        raise ValueError("unexpected CISA KEV schema")
    items = payload["vulnerabilities"]
    dates = []
    ransomware = 0
    for item in items:
        if not isinstance(item, dict):
            continue
        parsed = _parse_iso(item.get("dateAdded"))
        if parsed:
            dates.append(parsed)
        if str(item.get("knownRansomwareCampaignUse") or "").strip().lower() == "known":
            ransomware += 1
    latest = max(dates) if dates else None
    return {
        "schemaValid": True,
        "observedAt": _iso(latest),
        "summary": {
            "catalogSize": len(items),
            "knownRansomwareUse": ransomware,
            "latestDateAdded": latest.date().isoformat() if latest else None,
        },
        "mapPoints": [],
    }


def _world_bank(payload: object) -> dict:
    if not isinstance(payload, list) or len(payload) < 2 or not isinstance(payload[1], list):
        raise ValueError("unexpected World Bank schema")
    rows = payload[1]
    latest = next(
        (
            item
            for item in rows
            if isinstance(item, dict) and isinstance(item.get("value"), (int, float))
        ),
        None,
    )
    if latest is None:
        raise ValueError("World Bank indicator contains no numeric value")
    year = int(latest.get("date"))
    observed_at = datetime(year, 12, 31, tzinfo=timezone.utc)
    return {
        "schemaValid": True,
        "observedAt": _iso(observed_at),
        "summary": {
            "indicator": latest.get("indicator", {}).get("value"),
            "valuePercent": round(float(latest["value"]), 2),
            "year": year,
        },
        "mapPoints": [],
    }


PARSERS: Final = {
    "usgs-earthquakes": _usgs,
    "nasa-eonet": _eonet,
    "noaa-swpc-kp": _swpc,
    "cisa-kev": _cisa,
    "world-bank-internet": _world_bank,
}


def score_probe(
    *,
    available: bool,
    schema_valid: bool,
    latency_ms: int | None,
    observed_at: datetime | None,
    expected_freshness_seconds: int,
    cadence: str,
) -> tuple[int, dict]:
    availability_score = 30 if available else 0
    schema_score = 25 if schema_valid else 0

    if latency_ms is None:
        latency_score = 0
    elif latency_ms <= 750:
        latency_score = 15
    elif latency_ms <= 1500:
        latency_score = 12
    elif latency_ms <= 3000:
        latency_score = 9
    elif latency_ms <= 6000:
        latency_score = 5
    else:
        latency_score = 2

    if not available:
        freshness_score = 0
        freshness_age = None
    elif cadence == "annual":
        freshness_score = 20
        freshness_age = (
            int((_utc_now() - observed_at).total_seconds()) if observed_at else None
        )
    elif observed_at is None:
        freshness_score = 8
        freshness_age = None
    else:
        freshness_age = max(0, int((_utc_now() - observed_at).total_seconds()))
        ratio = freshness_age / max(1, expected_freshness_seconds)
        freshness_score = max(0, round(20 * math.exp(-0.65 * max(0.0, ratio - 1.0))))

    provenance_score = 10 if available else 0
    score = availability_score + schema_score + latency_score + freshness_score + provenance_score
    detail = {
        "availability": availability_score,
        "schema": schema_score,
        "latency": latency_score,
        "freshness": freshness_score,
        "provenance": provenance_score,
        "freshnessAgeSeconds": freshness_age,
    }
    return min(100, int(score)), detail


def source_catalog() -> dict:
    return {
        "schema": "gpt-doug.global-intel.sources.v1",
        "policy": SAFE_INTEL_POLICY,
        "sources": SOURCE_DEFINITIONS,
    }


def _probe_source(
    definition: dict,
    fetcher: Callable[[str], tuple[object, int]] = _fetch_json,
) -> dict:
    fetched_at = _utc_now()
    try:
        payload, latency_ms = fetcher(definition["url"])
        parsed = PARSERS[definition["id"]](payload)
        observed_at = _parse_iso(parsed.get("observedAt"))
        score, score_detail = score_probe(
            available=True,
            schema_valid=bool(parsed.get("schemaValid")),
            latency_ms=latency_ms,
            observed_at=observed_at,
            expected_freshness_seconds=definition["expectedFreshnessSeconds"],
            cadence=definition["cadence"],
        )
        return {
            **definition,
            "status": "ONLINE",
            "score": score,
            "scoreDetail": score_detail,
            "latencyMs": latency_ms,
            "fetchedAt": _iso(fetched_at),
            **parsed,
        }
    except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
        score, score_detail = score_probe(
            available=False,
            schema_valid=False,
            latency_ms=None,
            observed_at=None,
            expected_freshness_seconds=definition["expectedFreshnessSeconds"],
            cadence=definition["cadence"],
        )
        return {
            **definition,
            "status": "DEGRADED",
            "score": score,
            "scoreDetail": score_detail,
            "latencyMs": None,
            "fetchedAt": _iso(fetched_at),
            "observedAt": None,
            "summary": {},
            "mapPoints": [],
            "error": str(exc)[:280],
        }


def _grade(score: float) -> str:
    if score >= 93:
        return "A+"
    if score >= 88:
        return "A"
    if score >= 82:
        return "B+"
    if score >= 75:
        return "B"
    if score >= 68:
        return "C"
    return "D"


def build_benchmark(
    fetcher: Callable[[str], tuple[object, int]] = _fetch_json,
) -> dict:
    probes = [_probe_source(definition, fetcher) for definition in SOURCE_DEFINITIONS]
    scores = [item["score"] for item in probes]
    online = [item for item in probes if item["status"] == "ONLINE"]
    latencies = [
        item["latencyMs"]
        for item in online
        if isinstance(item.get("latencyMs"), int)
    ]

    domains = {}
    for item in probes:
        bucket = domains.setdefault(
            item["domain"],
            {"sources": 0, "online": 0, "scores": []},
        )
        bucket["sources"] += 1
        bucket["online"] += 1 if item["status"] == "ONLINE" else 0
        bucket["scores"].append(item["score"])

    domain_results = {
        domain: {
            "sources": values["sources"],
            "online": values["online"],
            "score": round(statistics.mean(values["scores"]), 1),
        }
        for domain, values in domains.items()
    }

    overall = round(statistics.mean(scores), 1) if scores else 0.0
    map_points = [
        point
        for item in probes
        for point in item.get("mapPoints", [])
    ][:160]

    return {
        "schema": "gpt-doug.global-intel-benchmark.v1",
        "generatedAt": _iso(_utc_now()),
        "benchmark": {
            "name": "GLOBAL-INTEL-BENCHMARK-2030",
            "overallScore": overall,
            "grade": _grade(overall),
            "sourceCount": len(probes),
            "onlineSources": len(online),
            "degradedSources": len(probes) - len(online),
            "medianLatencyMs": int(statistics.median(latencies)) if latencies else None,
            "dimensions": [
                "availability",
                "schema integrity",
                "latency",
                "freshness",
                "provenance",
                "domain coverage",
            ],
        },
        "policy": SAFE_INTEL_POLICY,
        "domains": domain_results,
        "sources": probes,
        "mapPoints": map_points,
        "signals": {
            item["id"]: item.get("summary", {})
            for item in probes
        },
        "claim": (
            "Public-source strategic awareness and data-quality benchmark only. "
            "Source score measures feed fitness, not geopolitical threat severity."
        ),
    }


def global_intel_benchmark(force: bool = False) -> dict:
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get("value")
        expires = float(_cache.get("expires") or 0)
        if cached is not None and not force and now < expires:
            return cached

    value = build_benchmark()
    with _cache_lock:
        _cache["value"] = value
        _cache["expires"] = time.monotonic() + CACHE_TTL_SECONDS
    return value
