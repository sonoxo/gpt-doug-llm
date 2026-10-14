"""Local-only TAK-style Cursor-on-Target and GeoJSON ingestion.

No networking, TAK credentials, sockets, SDK code, or live operational feeds.
Inputs are untrusted. Output is display-oriented, reduced GeoJSON.
"""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

MAX_BYTES = 2_000_000
MAX_FEATURES = 250
MAX_COORDINATES = 10_000
MAX_TEXT = 180
PROPERTIES = (
    "name", "title", "label", "category", "kind", "source", "source_kind",
    "observed_at", "time", "stale", "cot_type", "how", "synthetic", "description",
)


class GeoInputError(ValueError):
    """A local file cannot be safely displayed."""


def _label(value: Any) -> str:
    if value is None:
        return ""
    if not isinstance(value, (str, int, float, bool)):
        return ""
    return str(value).strip()[:MAX_TEXT]


def _lon_lat(value: Any) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) < 2:
        raise GeoInputError("coordinate must be [longitude, latitude]")
    lon, lat = value[:2]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in (lon, lat)):
        raise GeoInputError("coordinates must be finite numbers")
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        raise GeoInputError("WGS84 coordinates out of range")
    return [float(lon), float(lat)]


def _geometry(value: Any) -> tuple[dict, int]:
    if not isinstance(value, dict):
        raise GeoInputError("geometry must be an object")
    kind = value.get("type")
    coords = value.get("coordinates")
    if kind == "Point":
        return {"type": kind, "coordinates": _lon_lat(coords)}, 1
    if kind == "LineString":
        if not isinstance(coords, list) or not 2 <= len(coords) <= MAX_COORDINATES:
            raise GeoInputError("LineString must have 2 to 10000 vertices")
        return {"type": kind, "coordinates": [_lon_lat(p) for p in coords]}, len(coords)
    if kind == "Polygon":
        if not isinstance(coords, list) or not coords or len(coords) > 32:
            raise GeoInputError("Polygon must have 1 to 32 rings")
        normalized = []
        count = 0
        for ring in coords:
            if not isinstance(ring, list) or not 4 <= len(ring) <= MAX_COORDINATES:
                raise GeoInputError("polygon ring requires 4 to 10000 vertices")
            values = [_lon_lat(p) for p in ring]
            if values[0] != values[-1]:
                raise GeoInputError("polygon rings must be closed")
            count += len(values)
            if count > MAX_COORDINATES:
                raise GeoInputError("too many coordinate vertices")
            normalized.append(values)
        return {"type": kind, "coordinates": normalized}, count
    raise GeoInputError("only Point, LineString and Polygon are supported")


def normalize_geojson(raw: Any) -> dict:
    if not isinstance(raw, dict):
        raise GeoInputError("expected a GeoJSON object")
    if raw.get("type") == "FeatureCollection":
        features = raw.get("features")
    elif raw.get("type") == "Feature":
        features = [raw]
    else:
        raise GeoInputError("expected FeatureCollection or Feature")
    if not isinstance(features, list) or len(features) > MAX_FEATURES:
        raise GeoInputError("at most 250 features can be displayed")
    normalized: list[dict] = []
    total_coords = 0
    for index, feature in enumerate(features):
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise GeoInputError(f"feature {index} must be a GeoJSON Feature")
        geometry, count = _geometry(feature.get("geometry"))
        total_coords += count
        if total_coords > MAX_COORDINATES:
            raise GeoInputError("maximum total coordinates exceeded")
        raw_props = feature.get("properties") or {}
        if not isinstance(raw_props, dict):
            raise GeoInputError("feature properties must be an object")
        safe = {key: _label(raw_props.get(key)) for key in PROPERTIES if key in raw_props}
        safe["source_kind"] = safe.get("source_kind") or "LOCAL_FILE"
        if "name" not in safe:
            safe["name"] = _label(feature.get("id")) or f"Observation {index + 1}"
        normalized.append({
            "type": "Feature",
            "id": _label(feature.get("id")) or f"feature-{index + 1}",
            "geometry": geometry,
            "properties": safe,
        })
    return {"type": "FeatureCollection", "features": normalized}


def cot_to_geojson(xml_bytes: bytes) -> dict:
    if len(xml_bytes) > MAX_BYTES:
        raise GeoInputError("CoT XML exceeds the 2 MB file limit")
    if re.search(rb"<!\s*(?:DOCTYPE|ENTITY)\b", xml_bytes, re.I):
        raise GeoInputError("CoT DOCTYPE / ENTITY declarations are prohibited")
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        raise GeoInputError(f"malformed CoT XML: {exc}") from exc
    if root.tag != "event":
        raise GeoInputError("CoT document must contain one root <event>")
    point = root.find("point")
    if point is None:
        raise GeoInputError("CoT event must include a point")
    try:
        lon = float(point.attrib["lon"])
        lat = float(point.attrib["lat"])
    except (KeyError, ValueError) as exc:
        raise GeoInputError("CoT point requires numeric lat and lon") from exc
    coords = _lon_lat([lon, lat])
    contact = root.find("./detail/contact")
    name = contact.attrib.get("callsign") if contact is not None else None
    uid = _label(root.attrib.get("uid")) or "cot-event"
    properties = {
        "name": _label(name) or uid,
        "cot_type": _label(root.attrib.get("type")),
        "how": _label(root.attrib.get("how")),
        "time": _label(root.attrib.get("time")),
        "stale": _label(root.attrib.get("stale")),
        "category": "cot",
        "source_kind": "LOCAL_COT_FILE",
    }
    return normalize_geojson({
        "type": "FeatureCollection",
        "features": [{"type": "Feature", "id": uid, "properties": properties,
                      "geometry": {"type": "Point", "coordinates": coords}}],
    })


def load_file(path: Path) -> dict:
    path = Path(path).expanduser()
    if path.stat().st_size > MAX_BYTES:
        raise GeoInputError("file exceeds 2 MB input limit")
    raw = path.read_bytes()
    if path.suffix.lower() in {".cot", ".xml"}:
        return cot_to_geojson(raw)
    if path.suffix.lower() not in {".json", ".geojson"}:
        raise GeoInputError("supported file extensions: .cot, .xml, .json, .geojson")
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise GeoInputError("invalid UTF-8 GeoJSON") from exc
    return normalize_geojson(parsed)


def render_dashboard(geojson: dict, template: str) -> str:
    if template.count("__TAK_GEO_DATA__") != 1:
        raise GeoInputError("dashboard template missing unique data placeholder")
    normalized = normalize_geojson(geojson)
    serialized = json.dumps(normalized, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    # The embedded script is inert JSON-style data, but still escape HTML delimiters.
    serialized = serialized.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return template.replace("__TAK_GEO_DATA__", serialized)


def write_dashboard(geojson: dict, output: Path, *, overwrite: bool = False) -> dict:
    output = Path(output).expanduser()
    output.mkdir(parents=True, exist_ok=True)
    if not overwrite and any((output / name).exists() for name in ("index.html", "data.geojson")):
        raise GeoInputError("output already exists; use --force to update generated files")
    normalized = normalize_geojson(geojson)
    template = (Path(__file__).with_name("dashboard.html")).read_text(encoding="utf-8")
    (output / "index.html").write_text(render_dashboard(normalized, template), encoding="utf-8")
    (output / "data.geojson").write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8")
    manifest = {
        "system": "GPT-DOUG TAK-GEO",
        "status": "LOCAL_VISUALIZATION_ONLY",
        "feature_count": len(normalized["features"]),
        "default_basemap": "OFFLINE_GRID",
        "optional_external_imagery": "USGS The National Map (explicit opt-in)",
        "tak_server_connected": False,
        "tak_sdk_embedded": False,
        "external_requests_by_default": False,
        "sharing_enabled": False,
    }
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
