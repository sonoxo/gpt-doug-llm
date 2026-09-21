#!/usr/bin/env python3
"""GPT-Doug / GPT-Chaos Light Force terminal takeover.

Single-process, foreground-only visualization of the logical 999-swarm / 999-hive
federation. It does not spawn worker daemons or perform external actions.

Controls:
  q / Esc / Ctrl-C  return terminal control
  Space             pause/resume animation
  p                 trigger a visible pulse
"""

from __future__ import annotations

import argparse
import math
import os
import select
import shutil
import signal
import sys
import termios
import time
import tty
from collections import deque
from dataclasses import dataclass
from typing import Deque

ESC = "\x1b"
RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"
DIM = f"{ESC}[2m"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
ALT_ON = f"{ESC}[?1049h"
ALT_OFF = f"{ESC}[?1049l"
HOME = f"{ESC}[H"
CLEAR = f"{ESC}[2J"

RUST = f"{ESC}[38;5;166m"
ORANGE = f"{ESC}[38;5;208m"
GOLD = f"{ESC}[38;5;220m"
AMBER = f"{ESC}[38;5;214m"
SAGE = f"{ESC}[38;5;142m"
CREAM = f"{ESC}[38;5;230m"
DIMFG = f"{ESC}[38;5;244m"
RED = f"{ESC}[38;5;196m"

ICONS = ["🐝", "✨", "🍂", "🌾", "⚡", "🧠", "🍯", "✦"]
STATUSES = ["SYNC", "PLAN", "ROUTE", "VERIFY", "LEARN", "RECONCILE", "IDLE", "PULSE"]
EVENTS = [
    "ontology hash verified",
    "blackboard state reconciled",
    "Doug↔Chaos peer link synchronized",
    "artifact provenance checked",
    "bounded worker route completed",
    "hive telemetry heartbeat",
    "result confidence rescored",
    "human override channel healthy",
    "logical swarm checkpoint committed",
    "no external side effect requested",
]


@dataclass
class Cell:
    name: str
    role: str
    icon: str
    phase: float
    speed: float
    status: str = "IDLE"
    progress: float = 0.45

    def tick(self, t: float, pulse: float) -> None:
        # Stable visual motion: progress eases toward a slow-moving target
        # instead of jumping directly to a new waveform value every frame.
        wave = (math.sin(t * self.speed * 0.35 + self.phase) + 1.0) / 2.0
        target = min(0.96, max(0.08, 0.16 + wave * 0.72 + pulse * 0.05))
        self.progress += (target - self.progress) * 0.10

        # Status text changes only every four seconds. Keeping the label fixed
        # between slots prevents the dense 100-HIVE wall from visually shaking.
        slot = int(t // 4.0)
        idx = (slot + int(self.phase * 10.0)) % len(STATUSES)
        self.status = STATUSES[idx]


class TerminalMode:
    def __init__(self, enabled: bool) -> None:
        self.enabled = enabled and sys.stdin.isatty() and sys.stdout.isatty()
        self.fd = sys.stdin.fileno() if self.enabled else None
        self.old = None

    def __enter__(self) -> "TerminalMode":
        if self.enabled and self.fd is not None:
            self.old = termios.tcgetattr(self.fd)
            tty.setcbreak(self.fd)
            sys.stdout.write(ALT_ON + HIDE_CURSOR + CLEAR + HOME)
            sys.stdout.flush()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.enabled and self.fd is not None and self.old is not None:
            termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old)
            sys.stdout.write(RESET + SHOW_CURSOR + ALT_OFF)
            sys.stdout.flush()

    def key(self) -> str:
        if not self.enabled or self.fd is None:
            return ""
        ready, _, _ = select.select([self.fd], [], [], 0)
        if not ready:
            return ""
        try:
            return os.read(self.fd, 1).decode("utf-8", "ignore")
        except OSError:
            return ""


def crop(text: str, width: int) -> str:
    if width <= 0:
        return ""
    if len(text) <= width:
        return text
    if width <= 1:
        return text[:width]
    return text[: width - 1] + "…"


def bar(value: float, width: int) -> str:
    width = max(4, width)
    filled = max(0, min(width, int(round(value * width))))
    return "█" * filled + "░" * (width - filled)


def frame(
    cells: list[Cell],
    events: Deque[str],
    tick: int,
    fps: float,
    paused: bool,
    pulse: float,
    swarms: int,
    hives: int,
) -> str:
    cols, rows = shutil.get_terminal_size((120, 38))
    cols = max(72, cols)
    rows = max(24, rows)
    t = tick / max(1.0, fps)

    for c in cells:
        c.tick(t, pulse)

    lines: list[str] = []
    title = "GPT-DOUG // GPT-CHAOS // SWARM LIGHT FORCE // DARK FALL"
    lines.append(RUST + "╭" + "─" * (cols - 2) + "╮" + RESET)
    lines.append(
        ORANGE
        + "│"
        + crop(title.center(cols - 2), cols - 2)
        + "│"
        + RESET
    )
    peer = (
        f"DOUG = CHAOS   {swarms} LOGICAL SWARMS   "
        f"{hives} LOGICAL HIVES   ZERO HIDDEN DAEMONS"
    )
    lines.append(GOLD + "│" + crop(peer.center(cols - 2), cols - 2) + "│" + RESET)
    status = "PAUSED" if paused else "ACTIVE"
    controls = f"MODE={status}  q/Esc=RETURN CONTROL  Space=PAUSE  p=PULSE  Ctrl+C=KILL SWITCH"
    lines.append(SAGE + "│" + crop(controls.center(cols - 2), cols - 2) + "│" + RESET)
    lines.append(RUST + "├" + "─" * (cols - 2) + "┤" + RESET)

    inner = cols - 4
    gap = 1

    # Compact multi-column hive wall. A normal 120x38 terminal can now show
    # 100 HIVE cells at once (4 columns x 25 available rows), while wider
    # terminals use 5 columns for a denser wall.
    grid_cols = min(5, max(2, inner // 28))
    boxw = max(22, (inner - gap * (grid_cols - 1)) // grid_cols)
    grid_rows = max(6, rows - 13)
    visible = min(len(cells), grid_cols * grid_rows)
    visible_cells = cells[:visible]

    for i in range(0, len(visible_cells), grid_cols):
        chunks = []
        for cell in visible_cells[i : i + grid_cols]:
            meter_width = max(4, boxw - 22)
            short_status = cell.status[:5]
            label = (
                f"{cell.name} {short_status:<5} "
                f"{bar(cell.progress, meter_width)} {int(cell.progress*100):3d}%"
            )
            chunks.append(crop(label, boxw))
        while len(chunks) < grid_cols:
            chunks.append(" " * boxw)
        row = (" " * gap).join(chunk.ljust(boxw) for chunk in chunks)
        lines.append("│ " + CREAM + row + RESET + " │")

    lines.append(RUST + "├" + "─" * (cols - 2) + "┤" + RESET)
    pulse_char = [".", "+", "*", "+"][tick % 4]
    bus = (
        f"{pulse_char} PEER BUS  DOUG <-> CHAOS <-> HIVE  "
        f"pulse={pulse:0.2f}  visible_hives={visible}/{len(cells)}  "
        f"logical_federation={swarms}x{hives}"
    )
    lines.append(AMBER + "│ " + crop(bus, cols - 4).ljust(cols - 4) + " │" + RESET)

    log_room = max(3, rows - len(lines) - 4)
    recent = list(events)[-log_room:]
    for event in recent:
        lines.append(DIMFG + "│ " + crop(event, cols - 4).ljust(cols - 4) + " │" + RESET)

    while len(lines) < rows - 2:
        lines.append(DIMFG + "│" + " " * (cols - 2) + "│" + RESET)

    footer = "HUMAN OVERRIDE=TRUE  //  SINGLE FOREGROUND PROCESS  //  TERMINAL CONTROL ALWAYS RETURNABLE"
    lines.append(SAGE + "│" + crop(footer.center(cols - 2), cols - 2) + "│" + RESET)
    lines.append(RUST + "╰" + "─" * (cols - 2) + "╯" + RESET)
    return HOME + "\n".join(lines[:rows])


def build_cells(count: int) -> list[Cell]:
    roles = [
        "Planner", "Retriever", "Ranker", "Analyst", "Verifier", "Router",
        "Memory", "Critic", "Scout", "Builder", "Auditor", "Reconciler",
    ]
    cells: list[Cell] = []
    for i in range(count):
        role = roles[i % len(roles)]
        cells.append(
            Cell(
                name=f"HIVE-{i+1:03d}",
                role=role,
                icon=ICONS[i % len(ICONS)],
                phase=i * 0.77,
                speed=0.75 + (i % 5) * 0.11,
            )
        )
    return cells


def main() -> int:
    parser = argparse.ArgumentParser(description="GPT-Doug Light Force live terminal visualization")
    parser.add_argument("--frames", type=int, default=0, help="exit after N frames; 0 means run until q/Ctrl-C")
    parser.add_argument(
        "--fps",
        type=float,
        default=6.0,
        help="refresh rate for the stable terminal renderer (default: 6)",
    )
    parser.add_argument(
        "--cells",
        type=int,
        default=100,
        help="number of visible HIVE cells to animate (default: 100)",
    )
    parser.add_argument("--swarms", type=int, default=int(os.getenv("GPTDOUG_LIGHTFORCE_SWARMS", "999")))
    parser.add_argument("--hives", type=int, default=int(os.getenv("GPTDOUG_LIGHTFORCE_HIVES", "999")))
    parser.add_argument("--plain", action="store_true", help="no alternate screen; useful for tests/logs")
    args = parser.parse_args()

    args.fps = max(2.0, min(args.fps, 30.0))
    args.cells = max(4, min(args.cells, 200))
    cells = build_cells(args.cells)
    events: Deque[str] = deque(maxlen=12)

    def push_event(message: str) -> None:
        events.append(f"[{time.strftime('%H:%M:%S')}] {message}")

    push_event("Light Force foreground visualizer attached")
    push_event("Doug<->Chaos peer symmetry online")
    push_event(f"{args.swarms} logical swarms / {args.hives} logical hives represented")
    push_event("human override channel healthy")

    paused = False
    pulse = 0.0
    running = True
    tick = 0
    next_event = 24
    frame_budget = args.frames

    def stop(_sig=None, _frame=None) -> None:
        nonlocal running
        running = False

    old_int = signal.signal(signal.SIGINT, stop)
    old_term = signal.signal(signal.SIGTERM, stop)

    try:
        with TerminalMode(not args.plain) as term:
            if not term.enabled:
                sys.stdout.write(
                    f"LIGHTFORCE LIVE // {args.swarms} logical swarms // "
                    f"{args.hives} logical hives // zero hidden daemons\n"
                )
            while running:
                start = time.monotonic()
                key = term.key()
                if key in {"q", "Q", "\x1b"}:
                    break
                if key == " ":
                    paused = not paused
                    push_event("visual clock paused" if paused else "visual clock resumed")
                elif key in {"p", "P"}:
                    pulse = 1.0
                    push_event("manual Light Force pulse injected")

                if not paused:
                    tick += 1
                    pulse *= 0.90
                    if tick >= next_event:
                        push_event(EVENTS[(tick // 24) % len(EVENTS)])
                        next_event = tick + 24 + (tick % 12)

                sys.stdout.write(
                    frame(
                        cells,
                        events,
                        tick,
                        args.fps,
                        paused,
                        pulse,
                        args.swarms,
                        args.hives,
                    )
                )
                sys.stdout.flush()

                if frame_budget > 0:
                    frame_budget -= 1
                    if frame_budget <= 0:
                        break

                elapsed = time.monotonic() - start
                time.sleep(max(0.0, (1.0 / args.fps) - elapsed))
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)

    if sys.stdout.isatty():
        print(f"{SAGE}✨ LIGHT FORCE // TERMINAL CONTROL RETURNED{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
