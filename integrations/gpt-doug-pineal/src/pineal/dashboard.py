"""Read-only ZYRA federation terminal cortex for macOS and other ANSI terminals."""
from __future__ import annotations

import math
import os
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime
from typing import TextIO

from .federation import list_nodes
from .cells import list_cells
from .kraken import KrakenController, Telemetry
from .store import PinealStore

_GLYPHS = "\u2581\u2582\u2583\u2584\u2585\u2586\u2587\u2588"


def _sparkline(points: list[float], size: int = 12) -> str:
    if not points:
        return "-- no samples --"[:size]
    values = points[-size:]
    bottom, top = min(values), max(values)
    if top == bottom:
        return _GLYPHS[3] * len(values)
    return "".join(_GLYPHS[min(7, int(7 * (v - bottom) / (top - bottom)))] for v in values)


def _demo_series(index: int, frame: int = 0) -> list[float]:
    """Deterministic fake data, never persisted or attributed to a provider."""
    return [round(40 + index * 3 + 12 * math.sin((index + 2) * i / 7) + i * 0.5, 2)
            for i in range(frame, frame + 14)]


def _colored(value: str, code: str, color: bool) -> str:
    return f"\033[{code}m{value}\033[0m" if color else value


def _rule(label: str, width: int) -> str:
    remaining = max(0, width - len(label) - 3)
    return "| " + label + " " + "-" * remaining


def render_dashboard(store: PinealStore, *, demo: bool = False,
                     color: bool = False, width: int = 104, frame: int = 0) -> str:
    """Render a pure text snapshot. No network, mutation, or device I/O."""
    width = min(160, max(100, int(width)))
    all_samples = store.list_observations(limit=500)
    groups: dict[str, list[dict]] = defaultdict(list)
    for row in all_samples:
        groups[row["node"]].append(row)
    nodes = list_nodes()
    audit = store.verify_audit()
    gpu = store.latest_telemetry()
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    lines = ["=" * width,
             _colored("  ZYRA FEDERATION  //  GPT-DOUG-PINEAL  //  SHAGGOTH-KRAKEN", "1;36", color),
             "  LOCAL VISUAL CORTEX  |  " + now,
             "=" * width]
    lines.append(_colored("  SYNTHETIC DEMONSTRATION  |  NO THIRD-PARTY ACCESS" if demo else
                          "  LOCAL OBSERVATIONS ONLY  |  NO LIVE PROVIDER FEEDS", "1;33", color))
    lines.append("  EXTERNAL CONNECTIONS: 0 / " + str(len(nodes)) +
                 "  |  PHYSICAL ACTUATORS: 0  |  BRAIN STIMULATION: DISABLED")
    lines.append("")
    lines.append(_rule("FEDERATION TOPOLOGY", width))
    lines.extend([
        "   [OPEN BIOTECH]    [SOCIAL / MOBILITY]    [TRADE / MARKETS]    [DEFENSE SI SIM]",
        "          \\                |                 |                  //",
        "                 [ ZYRA POLICY + PROVENANCE + AUDIT ]",
        "                         |                  |",
        "                [ PINEAL MEMORY ] --- [ KRAKEN GPU ADVISORY ]",
    ])
    lines.append("")
    lines.append(_rule("FEDERATION NODES", width))
    lines.append("  " + f"{'NODE':<23}{'LINK':<17}{'SIGNAL':<32}{'TREND':<17}{'DATA':<10}")
    lines.append("  " + "-" * (width - 4))
    for index, node in enumerate(nodes):
        samples = groups.get(node["id"], [])
        if samples:
            recent = samples[0]
            signal = f"{recent['metric'][:18]} {recent['value']:.2f} {recent['unit']}"[:31]
            trend = _sparkline([r["value"] for r in reversed(samples)])
            origin = "SIM" if recent["kind"] == "synthetic" else "LOCAL"
        elif demo:
            series = _demo_series(index, frame)
            label = "readiness_pct" if node["id"] == "warfighter-defense-si" else "sample_index"
            signal = f"{label} {series[-1]:.1f}"[:31]
            trend = _sparkline(series)
            origin = "DEMO"
        else:
            signal, trend, origin = "awaiting authorized data", "--", "NONE"
        link = "LOCAL ONLY" if node["id"] == "zyra" else "NOT CONNECTED"
        line = ("  " + f"{node['name'][:22]:<23}{link:<17}{signal:<32}"
                f"{trend:<17}{origin:<10}")
        lines.append(line[:width])
    lines.append("")
    lines.append(_rule("PINEAL  //  BIOLOGICAL & PATENT KNOWLEDGE", width))
    lines.append(f"  CELL ATLAS: {len(list_cells())} curated human cell classes (educational / non-living simulation)")
    lines.append(f"  PATENT INDEX: {store.patent_stats()['total']} local publication records; global corpus incomplete")
    lines.append("  Patent disclosures are not validated biology; no autonomous patent scraping")
    lines.append("")
    lines.append(_rule("LOCAL OBSERVATION PROVENANCE", width))
    if all_samples:
        for sample in all_samples[:4]:
            line = (f"  #{sample['seq']:04d} {sample['node'][:20]:<20} "
                    f"{sample['kind']:<13} {sample['metric'][:21]:<21} "
                    f"source={sample['source']}")
            lines.append(line[:width])
    else:
        lines.append("  No operator-provided observations stored. DEMO mode never seeds the DB.")
    lines.append("")
    lines.append(_rule("SHIELD  //  GOVERNED DATA BOUNDARIES", width))
    lines.extend([
        "  ZYRA POLICY       " + _colored("ENFORCED (LOCAL)", "1;32", color) +
        "    |   MUTATIONS: EXPLICIT + PROVENANCE",
        "  AUDIT CHAIN       " + _colored("VERIFIED" if audit["ok"] else "FAILED", "1;32" if audit["ok"] else "1;31", color) +
        f"    |   ENTRIES CHECKED: {audit['checked']}",
        "  BIOTECH          PUBLIC RESEARCH / SYNTHETIC ONLY; NO PERSONAL EEG OR NEURAL WRITE",
        "  WARFIGHTER SI     SYNTHETIC DEFENSIVE READINESS ONLY; NO TARGETING OR WEAPON CONTROL",
        "  MARKETS & SOCIAL  USER-SUPPLIED PUBLIC/LICENCED AGGREGATES; NO PROVIDER SESSIONS",
        "",
        _rule("KRAKEN  //  GPU & ENERGY ADVISORY", width),
    ])
    if gpu:
        lines.append(f"  LAST STORED LOCAL SAMPLE: {gpu['temperature_c']:.1f} C   "
                     f"{gpu['power_w']:.1f} W   RESERVE {100*gpu['water_fraction']:.0f}%   "
                     f"ADVISORY {gpu['mode'].upper()} (NO ACTUATION)")
    elif demo:
        advisory = KrakenController().evaluate(Telemetry(83.0, 350.0, 0.7))
        lines.append("  DEMO GPU SAMPLE: 83.0 C   350.0 W   RESERVE 70%   "
                     f"ADVISORY {advisory.mode.upper()} (SYNTHETIC; NO ACTUATION)")
    else:
        lines.append("  No local GPU telemetry; external GPUs and physical cooling not connected")
    lines.extend([_rule("DATA CONTRACT", width),
                  "  OFFLINE TEMPLATE != CONNECTED PROVIDER  |  DEMO != MARKET DATA  |  RECORD != ENDORSEMENT",
                  "  On Mac: pineal dashboard --demo --watch  |  Stop with Ctrl+C",
                  "=" * width])
    return "\n".join(lines) + "\n"


def run_dashboard(store: PinealStore, *, demo: bool = False, watch: bool = False,
                  interval: float = 2.0, frames: int | None = None,
                  color: bool | None = None, stream: TextIO | None = None) -> int:
    """Display once or redraw an opt-in local-only terminal view."""
    if type(interval) not in (float, int) or not math.isfinite(interval) or not 0 < interval <= 60:
        raise ValueError("refresh interval must be >0 and <=60 seconds")
    if frames is not None and (type(frames) is not int or frames < 1 or frames > 10000):
        raise ValueError("frames must be a positive integer <=10000")
    output = stream if stream is not None else sys.stdout
    tty = bool(getattr(output, "isatty", lambda: False)())
    use_color = color if color is not None else tty and "NO_COLOR" not in os.environ
    count = 0
    try:
        while True:
            columns = min(160, max(100, shutil.get_terminal_size((104, 30)).columns))
            if watch and tty:
                output.write("\033[H\033[2J")
            output.write(render_dashboard(store, demo=demo, color=use_color, width=columns, frame=count))
            output.flush()
            count += 1
            if not watch or (frames is not None and count >= frames):
                break
            time.sleep(interval)
    except KeyboardInterrupt:
        output.write("\n")
    return 0
