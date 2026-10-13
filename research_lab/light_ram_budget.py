"""Light-speed latency calculator and safe local RAM budget estimator.

The speed of light constrains signal travel time, not RAM capacity.
No memory allocation or privileged operations are performed.
"""
from __future__ import annotations

import argparse
import json
import platform
from pathlib import Path
import subprocess

C_METERS_PER_SECOND = 299_792_458.0


def light_latency(distance_m: float, velocity_fraction: float = 1.0) -> dict:
    if distance_m < 0:
        raise ValueError("distance must be non-negative")
    if not 0 < velocity_fraction <= 1:
        raise ValueError("velocity fraction must be in (0, 1]")
    v = C_METERS_PER_SECOND * velocity_fraction
    ns_one_way = distance_m / v * 1e9
    ns_round_trip = 2 * ns_one_way
    return {
        "distance_m": distance_m,
        "fraction_of_c": velocity_fraction,
        "one_way_ns_floor": round(ns_one_way, 6),
        "round_trip_ns_floor": round(ns_round_trip, 6),
        "serial_round_trip_hz_ceiling": round(1e9 / ns_round_trip, 3) if ns_round_trip else None,
    }


def local_ram_bytes() -> tuple[int | None, int | None, str]:
    """Report physical and OS-estimated available RAM (bytes), not swap capacity."""
    system = platform.system()
    if system == "Linux":
        try:
            values = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                key, _, rest = line.partition(":")
                if key in ("MemTotal", "MemAvailable"):
                    values[key] = int(rest.strip().split()[0]) * 1024
            return values.get("MemTotal"), values.get("MemAvailable"), "linux-proc-meminfo"
        except (OSError, ValueError, IndexError):
            pass
    if system == "Darwin":
        try:
            size = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True, timeout=2).strip())
            return size, None, "macos-sysctl-physical-only"
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    return None, None, "unavailable"


def build_report(distance_m: float, velocity_fraction: float, reserve_fraction: float) -> dict:
    if not 0 <= reserve_fraction < 1:
        raise ValueError("reserve fraction must be in [0, 1)")
    physical, available, source = local_ram_bytes()
    # MemAvailable on Linux estimates reclaimable cache and system needs.
    # macOS physical total cannot imply free RAM; no safe budget is guessed.
    workload_budget = int(available * (1 - reserve_fraction)) if available is not None else None
    return {
        "physics": light_latency(distance_m, velocity_fraction),
        "memory": {
            "physical_ram_bytes": physical,
            "os_available_ram_bytes": available,
            "suggested_additional_workload_budget_bytes": workload_budget,
            "reserve_fraction": reserve_fraction,
            "source": source,
        },
        "disclaimer": "Propagation delays do not determine RAM size. This is not a memory benchmark or a promise of usable model context capacity.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--distance-m", type=float, default=0.1)
    parser.add_argument("--velocity-fraction", type=float, default=0.67)
    parser.add_argument("--reserve-fraction", type=float, default=0.25)
    args = parser.parse_args()
    try:
        report = build_report(args.distance_m, args.velocity_fraction, args.reserve_fraction)
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
