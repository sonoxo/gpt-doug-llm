#!/usr/bin/env python3
"""XUNIA COSMOS: bounded, opt-in, no-key NASA/ESA astronomy catalog importer.

Never runs during site visits or on the user's machine unless explicitly called.
No credentials, paid APIs, backend, login, arbitrary URL download, or tracking.
Output is a STATIC JSON artifact to be reviewed before publication.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import tempfile
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "cosmos" / "catalogs"
ENDPOINTS = {
    "nasa": "https://exoplanetarchive.ipac.caltech.edu/TAP/sync",
    "gaia": "https://gea.esac.esa.int/tap-server/tap/sync",
}
SOURCE_HOME = {
    "nasa": "https://exoplanetarchive.ipac.caltech.edu/",
    "gaia": "https://gea.esac.esa.int/archive/",
}
MAX_DOWNLOAD = 8 * 1024 * 1024
MAX_ROWS = 2000


def numeric(value: object) -> float | None:
    try:
        result = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError, OverflowError):
        return None
    return round(result, 6) if math.isfinite(result) else None


def stable_id(prefix: str, value: object) -> str:
    digest = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
    return prefix + "-" + digest


def sky_layout(ra: object, dec: object, distance_pc: object, *, offset: float = 0.0) -> list[float]:
    """Schematic RA/Dec-oriented positions; radial distances are LOG compressed.

    These are NOT ephemerides, true-scale sky coordinates, or suitable for flight.
    """
    a = numeric(ra)
    d = numeric(dec)
    if a is None or d is None or not (0 <= a < 360 and -90 <= d <= 90):
        return [0.0, 0.0, offset]
    ra_r, dec_r = math.radians(a), math.radians(d)
    distance = numeric(distance_pc)
    radius = (2.0 + min(5.0, math.log1p(max(0.0, distance))) if distance is not None and distance >= 0 else 4.0)
    return [round(radius*math.cos(dec_r)*math.cos(ra_r), 4),
            round(radius*math.cos(dec_r)*math.sin(ra_r), 4),
            round(radius*math.sin(dec_r)+offset, 4)]


def nasa_rows(rows: list[dict[str, object]], limit: int) -> tuple[list[dict], list[dict]]:
    nodes: dict[str, dict] = {}
    edges: list[dict] = []
    seen: set[str] = set()
    for row in rows[:limit]:
        name, hostname = str(row.get("pl_name") or "").strip(), str(row.get("hostname") or "").strip()
        if not name or not hostname or len(name) > 160 or len(hostname) > 160:
            continue
        pid, hid = stable_id("nasa-planet", name), stable_id("nasa-host", hostname)
        if pid in seen:
            continue
        seen.add(pid)
        ra, dec, distance = (numeric(row.get(key)) for key in ("ra", "dec", "sy_dist"))
        nodes.setdefault(hid, {
            "id": hid, "name": hostname, "sector": "STARS", "parent": None,
            "description": "Host star from the NASA Exoplanet Archive composite table.",
            "source_label": "NASA Exoplanet Archive / pscomppars",
            "source_url": SOURCE_HOME["nasa"], "evidence": "NASA TAP archive record",
            "layout": sky_layout(ra, dec, distance),
            "ra_deg": ra, "dec_deg": dec, "distance_pc": distance,
        })
        nodes[pid] = {
            "id": pid, "name": name, "sector": "EXOPLANETS", "parent": hid,
            "description": "Cataloged exoplanet; host relationship from archive.",
            "source_label": "NASA Exoplanet Archive / pscomppars",
            "source_url": SOURCE_HOME["nasa"], "evidence": "NASA TAP archive record",
            "layout": sky_layout(ra, dec, distance, offset=0.12),
            "ra_deg": ra, "dec_deg": dec, "distance_pc": distance,
            "discovery_year": int(float(row["disc_year"])) if numeric(row.get("disc_year")) is not None and 1600 <= float(row["disc_year"]) <= 2100 else None,
            "radius_earth": numeric(row.get("pl_rade")),
        }
        edges.append({"source": hid, "target": pid, "relation": "hosts"})
    return list(nodes.values()), edges


def gaia_rows(rows: list[dict[str, object]], limit: int) -> tuple[list[dict], list[dict]]:
    nodes: list[dict] = []
    seen: set[str] = set()
    for row in rows[:limit]:
        id_ = str(row.get("source_id") or "").strip()
        if not id_.isdigit() or len(id_) > 24 or id_ in seen:
            continue
        seen.add(id_)
        parallax = numeric(row.get("parallax"))
        distance = round(1000 / parallax, 3) if parallax and parallax > 0 else None
        ra, dec = numeric(row.get("ra")), numeric(row.get("dec"))
        nodes.append({
            "id": "gaia-dr3-" + id_, "name": "Gaia DR3 " + id_,
            "sector": "STARS", "parent": None,
            "description": "Gaia DR3 source. The displayed spatial projection is not true scale.",
            "source_label": "ESA Gaia DR3 / gaia_source", "source_url": SOURCE_HOME["gaia"],
            "evidence": "ESA TAP archive record", "layout": sky_layout(ra, dec, distance),
            "ra_deg": ra, "dec_deg": dec, "parallax_mas": parallax,
            "distance_pc_estimate": distance,
            "g_magnitude": numeric(row.get("phot_g_mean_mag")),
        })
    return nodes, []


def read_payload(path: Path, catalog: str) -> list[dict[str, object]]:
    if path.stat().st_size > MAX_DOWNLOAD:
        raise ValueError("Input exceeds the bounded 8 MiB limit")
    if catalog == "nasa":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, list):
            raise ValueError("NASA TAP JSON must contain an array")
        return [r for r in value if isinstance(r, dict)]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def download_rows(catalog: str, limit: int) -> list[dict[str, object]]:
    if catalog == "nasa":
        query = ("select top " + str(limit) +
                 " pl_name,hostname,ra,dec,sy_dist,pl_rade,disc_year "
                 "from pscomppars order by pl_name")
        params = {"query": query, "format": "json"}
    else:
        query = ("SELECT TOP " + str(limit) +
                 " source_id,ra,dec,parallax,phot_g_mean_mag "
                 "FROM gaiadr3.gaia_source WHERE parallax > 20 "
                 "ORDER BY phot_g_mean_mag ASC")
        params = {"REQUEST":"doQuery","LANG":"ADQL","FORMAT":"csv","QUERY":query}
    req = Request(ENDPOINTS[catalog] + "?" + urlencode(params),
                  headers={"User-Agent": "XUNIA-COSMOS/1.0 (free public dataset importer)",
                           "Accept": "application/json" if catalog=="nasa" else "text/csv"})
    with urlopen(req, timeout=35) as response:
        payload = response.read(MAX_DOWNLOAD + 1)
    if len(payload) > MAX_DOWNLOAD:
        raise ValueError("Remote catalog response exceeds 8 MiB")
    if catalog == "nasa":
        decoded = json.loads(payload.decode("utf-8"))
        if not isinstance(decoded, list):
            raise ValueError("Unexpected NASA TAP data format")
        return [x for x in decoded if isinstance(x, dict)]
    return list(csv.DictReader(io.StringIO(payload.decode("utf-8-sig"))))


def build(catalog: str, rows: list[dict[str, object]], limit: int) -> dict[str, object]:
    nodes, edges = (nasa_rows(rows, limit) if catalog=="nasa" else gaia_rows(rows, limit))
    if not nodes:
        raise ValueError("No valid catalog rows; refusing to overwrite output")
    ids = {n["id"] for n in nodes}
    if len(ids)!=len(nodes) or any(e["source"] not in ids or e["target"] not in ids for e in edges):
        raise ValueError("Catalog referential integrity check failed")
    return {
        "schema":"xunia.cosmos.catalog.v1",
        "catalog":catalog,
        "generated_at":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "coordinate_system":"RA/Dec directional / log-compressed radial when distance is present; not true scale",
        "source":ENDPOINTS[catalog],
        "data_mode":"bounded downloaded subset or user-supplied fixture; never complete universe",
        "nodes":nodes,"edges":edges,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="XUNIA COSMOS free open astronomy catalog ingest")
    parser.add_argument("catalog", choices=sorted(ENDPOINTS))
    parser.add_argument("--limit", type=int, default=250)
    parser.add_argument("--input", type=Path, help="Read a downloaded JSON/CSV file offline instead of requesting a provider")
    parser.add_argument("--output", type=Path, help="Write to this JSON file; default docs/cosmos/catalogs/<catalog>.json")
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= MAX_ROWS:
        parser.error(f"--limit must be between 1 and {MAX_ROWS}")
    rows = read_payload(args.input, args.catalog) if args.input else download_rows(args.catalog, args.limit)
    artifact = build(args.catalog, rows, args.limit)
    destination = args.output or OUTPUT / f"{args.catalog}.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write to preserve last good snapshot if conversion or IO fails.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=destination.parent,
                                     prefix=".cosmos-", suffix=".json", delete=False) as handle:
        temp = Path(handle.name)
        json.dump(artifact, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
    try:
        temp.replace(destination)
    finally:
        temp.unlink(missing_ok=True)
    print(f"XUNIA COSMOS {args.catalog}: {len(artifact['nodes'])} nodes, "
          f"{len(artifact['edges'])} links; saved {destination}")
    print("Review imported data and licensing/attribution before committing to GitHub Pages.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
