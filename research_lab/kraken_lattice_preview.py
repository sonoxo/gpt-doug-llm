"""Offline, non-operational Lattice-style telemetry export for Kraken.

Produces *local* JSON snapshots for manual inspection. Does not call Lattice
APIs, ingest external tracks, issue tasks, connect to devices, or authenticate.
This is an illustrative interchange schema, NOT an API-valid Lattice Entity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from research_lab.kraken_robot_sim import MAX_AGENTS, simulate


def make_snapshot(agent_count: int = 16, ticks: int = 20) -> dict:
    result = simulate(agent_count, ticks)
    return {
        "schema": "gpt-doug.kraken.lattice-preview.v1",
        "mode": "offline-synthetic",
        "compatible_with_lattice_api": False,
        "simulation": result["simulation"],
        "robot_count": result["agents"],
        "ticks": result["ticks"],
        "task_count": result["completed_tasks"],
        "health": {"powered_units": result["healthy_agents"]},
        "entity_previews": [
            {
                "external_id": f"kraken-sim-{r['id']:04d}",
                "classification": "virtual-civilian-support-robot",
                "role": r["role"],
                "grid_position": {"x": r["x"], "y": r["y"], "units": "synthetic_grid"},
                "battery_percent": r["battery"],
                "synthetic": True,
            }
            for r in result["units"]
        ],
        "authorization": "no API access; no real entity publishing",
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--agents", type=int, default=16)
    p.add_argument("--ticks", type=int, default=20)
    p.add_argument("--output", type=Path, help="Optional path for local JSON")
    args = p.parse_args()
    if not 1 <= args.agents <= MAX_AGENTS:
        p.error(f"--agents must be between 1 and {MAX_AGENTS}")
    snapshot = make_snapshot(args.agents, args.ticks)
    encoded = json.dumps(snapshot, indent=2) + "\n"
    if args.output:
        if args.output.exists():
            p.error("refusing to overwrite an existing file")
        args.output.write_text(encoded, encoding="utf-8")
        print(f"Saved offline preview: {args.output}")
    else:
        print(encoded, end="")


if __name__ == "__main__":
    main()
