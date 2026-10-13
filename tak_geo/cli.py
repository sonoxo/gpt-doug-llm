"""Run the local GPT-Doug TAK-style geospatial viewer; no TAK connection."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .core import GeoInputError, load_file, write_dashboard

ROOT = Path(__file__).resolve().parent.parent
DEMO = ROOT / "examples" / "tak_geo" / "synthetic-civilian-exercise.geojson"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="tak-geo", description="Local geospatial CoT/GeoJSON graph and imagery viewer")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="show actual integration capability and limits")
    demo = sub.add_parser("demo", help="generate offline viewer using fictional exercise locations")
    demo.add_argument("--output", type=Path, default=Path("build/tak-geo-demo"))
    demo.add_argument("--force", action="store_true")
    render = sub.add_parser("render", help="visualize a local CoT or GeoJSON file")
    render.add_argument("input", type=Path)
    render.add_argument("--output", type=Path, default=Path("build/tak-geo-view"))
    render.add_argument("--force", action="store_true")
    convert = sub.add_parser("convert", help="normalize a local CoT or GeoJSON file to safe GeoJSON")
    convert.add_argument("input", type=Path)
    convert.add_argument("--output", required=True, type=Path)
    convert.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)

    if args.command == "status":
        print(json.dumps({
            "system": "GPT-DOUG TAK-GEO",
            "mode": "LOCAL_DATA_ONLY",
            "data_formats": ["GeoJSON", "CoT XML"],
            "views": ["interactive_map", "observation_category_graph"],
            "basemaps": ["offline_grid", "opt_in_USGS_topographic", "opt_in_USGS_imagery"],
            "authorized_tak_server_connection": False,
            "credentials_required": False,
            "tak_sdk_installed": False,
            "operational_feed_connected": False,
            "export_to_server": False,
            "physical_actions": False,
        }, indent=2))
        return 0

    try:
        source = DEMO if args.command == "demo" else args.input
        data = load_file(source)
        if args.command == "convert":
            target = args.output.expanduser()
            if target.exists() and not args.force:
                raise GeoInputError("output already exists; use --force to overwrite")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps({"ok": True, "output": str(target), "features": len(data["features"])}))
            return 0
        result = write_dashboard(data, args.output, overwrite=args.force)
        print(json.dumps({
            "ok": True, "output": str(args.output), "viewer": str(args.output / "index.html"),
            "feature_count": result["feature_count"],
            "tak_server_connected": False,
            "online_imagery_default": False,
        }, indent=2))
        return 0
    except (GeoInputError, OSError, UnicodeError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc), "network_actions": 0}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
