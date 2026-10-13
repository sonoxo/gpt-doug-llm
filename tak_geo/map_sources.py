"""Documentation-grounded ATAK-Maps XML catalog for GPT-Doug.

All operations are offline and read-only against a user-provided ATAK-Maps
checkout. An XML map source describes a remote provider but does NOT grant
rights to access that provider. We never fetch tiles, execute extensions,
embed credentials, or establish a TAK Server session.
"""
from __future__ import annotations

import hashlib
import ipaddress
import json
import math
import re
import subprocess
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

from .core import GeoInputError, load_file, write_dashboard

SOURCE_REPO = "https://github.com/sonoxo/ATAK-Maps"
SOURCE_LICENSE = "MIT; Copyright (c) 2023 Joshua Fuller"
DOCS = {
    "reference": "https://github.com/sonoxo/ATAK-Maps/blob/master/docs/xml-reference.md",
    "installation": "https://github.com/sonoxo/ATAK-Maps/blob/master/docs/install-guide.md",
    "custom_maps": "https://github.com/sonoxo/ATAK-Maps/blob/master/docs/creating-custom-maps.md",
    "schema": "https://github.com/sonoxo/ATAK-Maps/blob/master/schema/mobac-maps.xsd",
}
EXCLUDED = {
    ".git", ".github", "schema", "docs", "scripts", "tests", "images",
    "mapvalidator", "dist", "site", ".venv", "venv", "build",
}
SOURCE_TYPES = {
    "customMapSource": "TMS",
    "customWmsMapSource": "WMS",
    "customMultiLayerMapSource": "Multi-Layer",
}
CATEGORIES = {
    "Satellite", "Topographic", "Street", "Nautical", "Cycling",
    "Overlay", "Land use",
}
RECOMMENDED_MAX_ZOOM = 22
MAX_ZOOM = 25
MAX_XML_FILES = 256
MAX_SINGLE_XML = 128_000
MAX_MAP_NAME = 180
MAX_DESCRIPTION = 300
BAD_XML_MARKUP = re.compile(rb"<!\s*(?:DOCTYPE|ENTITY)\b", re.I)
SENSITIVE_QUERY = re.compile(
    r"^(?:key|api_key|apikey|access_token|token|client_secret|subscription_key|auth|password)$",
    re.I,
)
PUBLIC_GOV_PREVIEW = frozenset({
    "usgs/usgs_usgsbasemap.xml",
    "usgs/usgs_usgsimageryonly.xml",
    "usgs/usgs_usgsimagerytopo.xml",
    "usgs/usgs_usgsshadedrelief.xml",
})
USGS_HOST = "basemap.nationalmap.gov"


class CatalogError(GeoInputError):
    """Untrusted map-source XML or catalog path failed a safety check."""


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _safe_text(value: Any, limit: int = MAX_MAP_NAME) -> str:
    return re.sub(r"[\x00-\x1f\x7f]", " ", str(value or "")).strip()[:limit]


def _required(node: ET.Element, tag: str) -> str:
    value = node.findtext(tag)
    if not value or not value.strip():
        raise CatalogError(f"missing <{tag}> in <{node.tag}>")
    return value.strip()


def _read_zoom(node: ET.Element, tag: str, default: int | None = None) -> int:
    value = node.findtext(tag)
    if value is None:
        if default is None:
            raise CatalogError(f"missing <{tag}>")
        return default
    try:
        number = int(value.strip())
    except (ValueError, AttributeError) as exc:
        raise CatalogError(f"invalid <{tag}> integer") from exc
    if number < -1 or number > MAX_ZOOM:
        raise CatalogError(f"<{tag}> is outside supported range -1..{MAX_ZOOM}")
    return number


def _check_host(url: str, kind: str) -> dict:
    """Validate URL's structure without requesting it or exporting secrets."""
    if len(url) > 4096:
        raise CatalogError("oversize tile URL template")
    placeholder_safe = url.replace("{$serverpart}", "a")
    try:
        parts = urllib.parse.urlsplit(placeholder_safe)
        host = (parts.hostname or "").lower().rstrip(".")
    except ValueError as exc:
        raise CatalogError("invalid map URL") from exc
    if parts.scheme not in {"http", "https"} or not host:
        raise CatalogError("map endpoint must be HTTP(S) with a public host")
    if parts.username is not None or parts.password is not None:
        raise CatalogError("credentials in URL authority are prohibited")
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise CatalogError("local/private map endpoints are prohibited")
    try:
        if not ipaddress.ip_address(host).is_global:
            raise CatalogError("private or non-global IP map endpoint is prohibited")
    except ValueError:
        pass
    if not re.fullmatch(r"[a-z0-9.-]+", host):
        raise CatalogError("invalid map hostname")
    if kind == "TMS":
        has_xyz = all(token in url for token in ("{$z}", "{$x}", "{$y}"))
        if not has_xyz and "{$q}" not in url:
            raise CatalogError("TMS URL needs z/x/y or quadkey placeholders")
    key_required = "API_KEY_HERE" in url.upper() or "YOUR_API_KEY" in url.upper()
    for key, value in urllib.parse.parse_qsl(parts.query, keep_blank_values=True):
        if SENSITIVE_QUERY.fullmatch(key):
            if value and value not in {"API_KEY_HERE", "YOUR_API_KEY", "YOUR_KEY"} and not value.startswith("{$"):
                raise CatalogError("embedded token/key in map-source URL prohibited")
            key_required = True
    return {"host": host, "transport": parts.scheme, "requires_key": key_required}


def _check_extras(node: ET.Element) -> None:
    """Prevent concealed token fields in WMS additional query configuration."""
    for key in ("aditionalparameters", "additionalparameters"):
        extra = node.findtext(key) or ""
        if len(extra) > 2048:
            raise CatalogError("oversized WMS additionalparameters")
        for k, v in urllib.parse.parse_qsl(extra.lstrip("&?"), keep_blank_values=True):
            if SENSITIVE_QUERY.fullmatch(k) and v:
                raise CatalogError("embedded WMS token/key prohibited")


def _parse_source(node: ET.Element, depth: int = 0) -> dict:
    if depth > 4:
        raise CatalogError("composite map nesting exceeds limit")
    if node.tag not in SOURCE_TYPES:
        raise CatalogError(f"unsupported MOBAC root: <{node.tag}>")
    name = _safe_text(_required(node, "name"))
    if not name:
        raise CatalogError("map source name must be nonempty")
    kind = SOURCE_TYPES[node.tag]

    if kind == "Multi-Layer":
        layers_node = node.find("layers")
        children = list(layers_node) if layers_node is not None else []
        if not 1 <= len(children) <= 16:
            raise CatalogError("composite requires 1..16 child layers")
        parsed = [_parse_source(child, depth + 1) for child in children]
        alpha = (node.findtext("layersAlpha") or "").split()
        if alpha:
            if len(alpha) != len(children):
                raise CatalogError("layersAlpha count does not match layers")
            try:
                values = [float(item) for item in alpha]
            except ValueError as exc:
                raise CatalogError("invalid layersAlpha values") from exc
            if not all(math.isfinite(x) and 0 <= x <= 1 for x in values):
                raise CatalogError("layersAlpha values must be in 0..1")
        else:
            values = [1.0] * len(children)
        return {
            "name": name,
            "format": kind,
            "min_zoom": min(x["min_zoom"] for x in parsed),
            "max_zoom": max(x["max_zoom"] for x in parsed),
            "tile_type": "png",
            "coordinate_systems": sorted({crs for p in parsed for crs in p["coordinate_systems"]}),
            "hosts": sorted({host for p in parsed for host in p["hosts"]}),
            "transports": sorted({mode for p in parsed for mode in p["transports"]}),
            "requires_key": any(p["requires_key"] for p in parsed),
            "layer_names": [p["name"] for p in parsed],
            "opacity": values,
            "inverted_y": False,
        }

    min_default = -1 if kind == "WMS" else 0
    low = _read_zoom(node, "minZoom", min_default)
    high = _read_zoom(node, "maxZoom")
    if low > high:
        raise CatalogError("minZoom greater than maxZoom")
    if low < 0 and kind != "WMS":
        raise CatalogError("negative minZoom allowed only for WMS")
    url = _required(node, "url")
    endpoint = _check_host(url, kind)
    tile_type = (node.findtext("tileType") or "").lower().strip()
    if kind == "WMS":
        _required(node, "layers")
        if tile_type not in {"png", "jpg"}:
            raise CatalogError("WMS tileType must be PNG or JPG")
        _check_extras(node)
    elif tile_type and tile_type not in {"png", "jpg", "jpeg"}:
        raise CatalogError("unsupported TMS tileType")
    if "{$serverpart}" in url and not (node.findtext("serverParts") or "").strip():
        raise CatalogError("serverpart placeholder without serverParts definition")
    crs = _safe_text(node.findtext("coordinatesystem") or ("EPSG:4326" if kind == "WMS" else "EPSG:3857"))
    if not re.fullmatch(r"EPSG:[0-9]{4,6}", crs):
        raise CatalogError("coordinate system requires EPSG identifier")
    return {
        "name": name, "format": kind,
        "min_zoom": low, "max_zoom": high, "tile_type": tile_type or "unspecified",
        "coordinate_systems": [crs], "hosts": [endpoint["host"]],
        "transports": [endpoint["transport"]],
        "requires_key": endpoint["requires_key"],
        "layer_names": [], "opacity": [],
        "inverted_y": (node.findtext("invertYCoordinate") or "").strip() == "true",
    }


def _descriptions(root: Path) -> dict[str, dict[str, str]]:
    path = root / "descriptions.yml"
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 128_000:
        return {}
    current = ""
    entries: dict[str, dict[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not line[0].isspace() and line.endswith(":"):
            current = line[:-1].strip()
            if re.fullmatch(r"[a-z0-9-]+", current):
                entries[current] = {}
            else:
                current = ""
        elif current:
            match = re.fullmatch(r"\s{2,}(category|text):\s*(.*?)\s*", line)
            if match:
                raw = match.group(2)
                if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in {"'", '"'}:
                    raw = raw[1:-1]
                entries[current][match.group(1)] = _safe_text(raw, MAX_DESCRIPTION)
    return entries


def _get_source_commit(root: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--verify", "HEAD"],
            capture_output=True, text=True, timeout=5, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = proc.stdout.strip()
    return value if proc.returncode == 0 and re.fullmatch(r"[0-9a-f]{40}", value) else None


def inspect_checkout(root: Path) -> dict:
    """Index locally present map XML; no network, credentials, or execution."""
    root = Path(root).expanduser().resolve(strict=True)
    if not root.is_dir() or not (root / "schema" / "mobac-maps.xsd").is_file() or not (root / "README.md").is_file():
        raise CatalogError("source is not an ATAK-Maps checkout (README and schema required)")
    meta = _descriptions(root)
    paths: list[Path] = []
    for parent in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if parent.is_symlink():
            if parent.name not in EXCLUDED:
                raise CatalogError(f"source provider directory is a symlink: {parent.name}")
            continue
        if parent.name in EXCLUDED or parent.name.startswith(".") or not parent.is_dir():
            continue
        if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_-]{0,60}", parent.name):
            raise CatalogError(f"invalid provider directory: {parent.name}")
        for source in sorted(parent.iterdir(), key=lambda p: p.name.lower()):
            if source.suffix.lower() != ".xml":
                continue
            if source.is_symlink() or not source.is_file():
                raise CatalogError(f"source XML is not a regular file: {source.name}")
            paths.append(source)
            if len(paths) > MAX_XML_FILES:
                raise CatalogError(f"map catalog exceeds maximum of {MAX_XML_FILES} files")

    if not paths:
        raise CatalogError("no map source XML files found under provider directories")
    entries: list[dict] = []
    issues: list[dict] = []
    checksums: list[str] = []
    for path in sorted(paths):
        relative = path.relative_to(root).as_posix()
        if path.stat().st_size > MAX_SINGLE_XML:
            issues.append({"path": relative, "error": "source XML exceeds 128 KB"})
            continue
        raw = path.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        checksums.append(relative + ":" + digest)
        if BAD_XML_MARKUP.search(raw):
            issues.append({"path": relative, "error": "DTD/ENTITY XML is prohibited"})
            continue
        try:
            item = _parse_source(ET.fromstring(raw))
        except (CatalogError, ET.ParseError) as exc:
            issues.append({"path": relative, "error": str(exc)[:240]})
            continue
        slug = _slug(f"{path.parent.name}-{path.stem}")
        description = meta.get(slug, {})
        category = description.get("category") or "Uncategorized"
        if category not in CATEGORIES:
            category = "Uncategorized"
        preview_eligible = relative.lower() in PUBLIC_GOV_PREVIEW and item["hosts"] == [USGS_HOST] and item["format"] == "TMS" and not item["requires_key"]
        if preview_eligible:
            policy = "OPT_IN_USGS_PREVIEW"
        elif item["requires_key"]:
            policy = "AUTH_AND_PROVIDER_TERMS_REQUIRED"
        else:
            policy = "PROVIDER_TERMS_REVIEW"
        if "http" in item["transports"]:
            policy = "INSECURE_HTTP_NOT_PREVIEWED"
        if item["format"] == "Multi-Layer" and len(item["coordinate_systems"]) != 1:
            issues.append({"path": relative, "error": "composite child layers disagree on coordinate systems"})
            continue
        entries.append({
            "id": slug, "provider": path.parent.name, "path": relative, "name": item["name"],
            "category": category, "description": description.get("text", "")[:MAX_DESCRIPTION],
            "source_type": item["format"], "min_zoom": item["min_zoom"], "max_zoom": item["max_zoom"],
            "tile_type": item["tile_type"], "coordinate_systems": item["coordinate_systems"],
            "hostnames": item["hosts"], "requires_key": item["requires_key"],
            "layer_names": item["layer_names"], "layers_alpha": item["opacity"],
            "inverted_y": item["inverted_y"], "overlay": path.parent.name == "GRG",
            "policy": policy, "xml_sha256": digest,
            "url_templates_emitted": False, "source_validated": "BASIC_STRUCTURAL_ONLY",
        })
    types: dict[str, int] = {}
    for entry in entries:
        types[entry["source_type"]] = types.get(entry["source_type"], 0) + 1
    return {
        "schema": "xunia.tak.maps-ecosystem.v1",
        "authority": "LOCAL_DOCUMENTED_CATALOG",
        "source": {
            "repository": SOURCE_REPO,
            "commit_sha": _get_source_commit(root),
            "source_xml_files": len(paths),
            "catalog_sha256": hashlib.sha256("\n".join(sorted(checksums)).encode()).hexdigest(),
            "format_documentation": DOCS,
            "xml_schema_validation": "NOT_RUN_USE_UPSTREAM_MAPVALIDATOR",
            "license_notice": SOURCE_LICENSE,
            "provider_imagery_rights": "NOT_CONVEYED_BY_REPOSITORY_LICENSE",
        },
        "summary": {
            "sources": len(entries),
            "providers": len({p["provider"] for p in entries}),
            "formats": types, "issues": len(issues),
            "requires_key": sum(p["requires_key"] for p in entries),
            "optional_usgs_preview": sum(p["policy"] == "OPT_IN_USGS_PREVIEW" for p in entries),
            "overlay_sources": sum(p["overlay"] for p in entries),
        },
        "policy": {
            "network_access": False, "live_tak_server": False,
            "bulk_tile_download": False, "external_urls_in_catalog": False,
            "copy_vendor_maps": False, "machine_actions": False,
            "operator_review_required_for_remote_map_sources": True,
        },
        "entries": entries,
        "issues": issues,
    }


def render_catalog_page(catalog: dict, template: str) -> str:
    if template.count("__ATAK_MAPS_CATALOG__") != 1:
        raise CatalogError("Atlas template must contain a unique data placeholder")
    data = json.dumps(catalog, ensure_ascii=True, sort_keys=True, allow_nan=False)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return template.replace("__ATAK_MAPS_CATALOG__", data)


def write_ecosystem(source: Path, output: Path, *, force: bool = False) -> dict:
    """Emit standalone catalog + synthetic geoviewer, with explicit local provenance."""
    output = Path(output).expanduser()
    generated = ("index.html", "atlas.html", "catalog.json", "atlas-ontology.json", "ecosystem-status.json")
    if any((output / name).exists() for name in generated) and not force:
        raise CatalogError("ecosystem output exists; pass --force to regenerate generated files")
    report = inspect_checkout(source)
    output.mkdir(parents=True, exist_ok=True)
    # The map preview uses *only* local synthetic observations.
    fixture = Path(__file__).resolve().parent.parent / "examples" / "tak_geo" / "synthetic-civilian-exercise.geojson"
    write_dashboard(load_file(fixture), output, overwrite=force)
    (output / "atlas.html").write_text(
        render_catalog_page(report, Path(__file__).with_name("atlas.html").read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    (output / "catalog.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    from .atlas_ontology import build_ontology
    graph = build_ontology(report)
    (output / "atlas-ontology.json").write_text(json.dumps(graph, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    status = {
        "system": "GPT-DOUG TAK-ATLAS ECOSYSTEM",
        "status": "OFFLINE_CATALOG_BUILT",
        "atlas": str(output / "atlas.html"),
        "viewer": str(output / "index.html"),
        "catalog": str(output / "catalog.json"),
        "source_commit": report["source"]["commit_sha"],
        "summary": report["summary"],
        "ontology_nodes": len(graph["nodes"]),
        "ontology_edges": len(graph["edges"]),
        "network_calls": 0,
        "tak_server_connected": False,
        "source_repo": SOURCE_REPO,
    }
    (output / "ecosystem-status.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    return status
