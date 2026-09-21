#!/usr/bin/env python3
"""Truthful live telemetry HUD for GPT-Doug / GPT-Chaos swarm activity.

Every displayed activity metric is derived from persisted runtime evidence.
No synthetic worker states, random progress bars, or time-driven fake events
are generated. Empty capacity is rendered as NO LIVE DATA.

Observed sources:
- workers/live/revenue-swarm.jsonl
- workers/live/revenue-swarm-metrics.json
- xuniaverse-production/xuni-workers/{tasks,claimed,results}
- ~/.gpt-doug/universal-hive/state.json
- this foreground HUD process (CPU time / render timing / uptime)

Controls:
  q / Esc / Ctrl-C  return terminal control
  Space             pause/resume refresh
  r                 force telemetry refresh
"""

from __future__ import annotations

import argparse
import json
import os
import select
import shutil
import signal
import sys
import termios
import time
import tty
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

ESC = "\x1b"
RESET = f"{ESC}[0m"
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

STAGES = ("scout", "qualify", "match", "proposal", "outreach_draft", "qa")


@dataclass
class LiveItem:
    key: str
    source: str
    state: str
    stage: str = ""
    duration_s: Optional[float] = None
    updated_ts: float = 0.0
    detail: str = ""


@dataclass
class Snapshot:
    items: list[LiveItem]
    events: list[str]
    revenue_active: int
    revenue_queue: Optional[int]
    revenue_pool: Optional[int]
    revenue_provider: str
    daemon_active: int
    daemon_queue: int
    completed_60s: int
    failed_60s: int
    avg_stage_s: Optional[float]
    persisted_swarms: Optional[int]
    latest_event_ts: Optional[float]
    source_count: int


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
    if width == 1:
        return text[:1]
    return text[: width - 1] + "…"


def _json_file(path: Path) -> Optional[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _tail_jsonl(path: Path, max_bytes: int = 2_000_000) -> list[dict[str, Any]]:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            start = max(0, size - max_bytes)
            handle.seek(start)
            if start:
                handle.readline()
            data = handle.read().decode("utf-8", "replace")
    except OSError:
        return []

    records: list[dict[str, Any]] = []
    for line in data.splitlines():
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records


def _repo_root(explicit: Optional[str]) -> Optional[Path]:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit).expanduser())
    configured = os.environ.get("GPTDOUG_REPO", "").strip()
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend([Path.cwd(), Path.home() / "gpt-doug-llm"])

    for candidate in candidates:
        resolved = candidate.resolve()
        if (resolved / "workers" / "revenue_swarm.py").exists():
            return resolved
    return None


class TelemetryCollector:
    def __init__(self, repo: Optional[Path], capacity: int) -> None:
        self.repo = repo
        self.capacity = capacity

    def _revenue(self, now: float) -> tuple[list[LiveItem], dict[str, Any], list[str]]:
        if self.repo is None:
            return [], {}, []
        live_dir = self.repo / "workers" / "live"
        records = _tail_jsonl(live_dir / "revenue-swarm.jsonl")
        metrics = _json_file(live_dir / "revenue-swarm-metrics.json") or {}

        starts: dict[tuple[str, str], dict[str, Any]] = {}
        latest: dict[tuple[str, str], LiveItem] = {}
        events: list[str] = []

        for record in records:
            kind = str(record.get("type") or "")
            ts = float(record.get("ts") or 0.0)
            prospect = record.get("prospect") or {}
            prospect_id = str(
                prospect.get("prospect_id")
                or record.get("prospect_id")
                or "unknown"
            )
            if kind == "stage_start":
                stage = str(record.get("stage") or "")
                key = (prospect_id, stage)
                starts[key] = record
                latest[key] = LiveItem(
                    key=prospect_id,
                    source="revenue",
                    state="RUN",
                    stage=stage,
                    duration_s=max(0.0, now - ts),
                    updated_ts=ts,
                    detail="measured stage start",
                )
                events.append(
                    f"[{_stamp(ts)}] revenue START {prospect_id}/{stage}"
                )
            elif kind == "stage_result":
                result = record.get("result") or {}
                stage = str(result.get("stage") or "")
                key = (prospect_id, stage)
                starts.pop(key, None)
                status = str(result.get("status") or "unknown")
                state = "DONE" if status == "ok" else "FAIL"
                duration = _float_or_none(result.get("duration_s"))
                latest[key] = LiveItem(
                    key=prospect_id,
                    source="revenue",
                    state=state,
                    stage=stage,
                    duration_s=duration,
                    updated_ts=ts,
                    detail=status,
                )
                events.append(
                    f"[{_stamp(ts)}] revenue {state} {prospect_id}/{stage}"
                )

        active_keys = set(starts)
        for key in active_keys:
            record = starts[key]
            ts = float(record.get("ts") or 0.0)
            latest[key].duration_s = max(0.0, now - ts)

        items = sorted(
            latest.values(),
            key=lambda item: (item.state != "RUN", -item.updated_ts),
        )
        return items, metrics, events

    def _daemon(self, now: float) -> tuple[list[LiveItem], int, int, list[str]]:
        if self.repo is None:
            return [], 0, 0, []
        base = self.repo / "xuniaverse-production" / "xuni-workers"
        claimed = base / "claimed"
        queued = base / "tasks"
        results = base / "results"
        items: list[LiveItem] = []
        events: list[str] = []

        claimed_files = sorted(
            claimed.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        ) if claimed.exists() else []
        for path in claimed_files:
            ts = path.stat().st_mtime
            payload = _json_file(path) or {}
            task_id = str(payload.get("id") or path.stem)
            items.append(
                LiveItem(
                    key=task_id,
                    source="daemon",
                    state="RUN",
                    stage="task",
                    duration_s=max(0.0, now - ts),
                    updated_ts=ts,
                    detail="claimed task",
                )
            )
            events.append(f"[{_stamp(ts)}] daemon RUN {task_id}")

        queued_files = list(queued.glob("*.json")) if queued.exists() else []

        result_files = sorted(
            results.glob("*.json"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )[:40] if results.exists() else []
        for path in result_files:
            ts = path.stat().st_mtime
            payload = _json_file(path) or {}
            task_id = str(payload.get("id") or path.stem)
            if payload.get("blocked_by"):
                state = "BLOCK"
            elif payload.get("returncode") == 0:
                state = "DONE"
            else:
                state = "FAIL"
            duration = _float_or_none(payload.get("duration_seconds"))
            attempts = payload.get("attempts")
            detail = f"attempts={attempts}" if attempts is not None else ""
            items.append(
                LiveItem(
                    key=task_id,
                    source="daemon",
                    state=state,
                    stage="task",
                    duration_s=duration,
                    updated_ts=ts,
                    detail=detail,
                )
            )
            events.append(f"[{_stamp(ts)}] daemon {state} {task_id}")

        return items, len(claimed_files), len(queued_files), events

    def _hive_count(self) -> Optional[int]:
        state = _json_file(
            Path.home() / ".gpt-doug" / "universal-hive" / "state.json"
        )
        if state is None:
            return None
        swarms = state.get("swarms")
        return len(swarms) if isinstance(swarms, dict) else None

    def snapshot(self) -> Snapshot:
        now = time.time()
        revenue_items, metrics, revenue_events = self._revenue(now)
        daemon_items, daemon_active, daemon_queue, daemon_events = self._daemon(now)
        all_items = revenue_items + daemon_items
        all_items.sort(key=lambda item: (item.state != "RUN", -item.updated_ts))

        result_items = [
            item
            for item in all_items
            if item.state in {"DONE", "FAIL", "BLOCK"} and now - item.updated_ts <= 60
        ]
        completed_60s = sum(item.state == "DONE" for item in result_items)
        failed_60s = sum(item.state in {"FAIL", "BLOCK"} for item in result_items)
        durations = [
            item.duration_s
            for item in result_items
            if item.duration_s is not None
        ]
        avg_stage_s = sum(durations) / len(durations) if durations else None

        revenue_active = sum(
            item.source == "revenue" and item.state == "RUN" for item in all_items
        )
        pool = _int_or_none(metrics.get("active_workers"))
        unique = _int_or_none(metrics.get("prospects_unique"))
        started_ids = {
            item.key for item in revenue_items if item.source == "revenue"
        }
        revenue_queue = None
        if unique is not None:
            revenue_queue = max(0, unique - len(started_ids))

        events = sorted(
            revenue_events + daemon_events,
            key=_event_sort_key,
        )[-12:]
        latest_ts = max(
            (item.updated_ts for item in all_items if item.updated_ts),
            default=0.0,
        )

        source_count = 0
        if self.repo is not None:
            if (self.repo / "workers" / "live" / "revenue-swarm.jsonl").exists():
                source_count += 1
            daemon_base = self.repo / "xuniaverse-production" / "xuni-workers"
            if daemon_base.exists():
                source_count += 1
        hive_count = self._hive_count()
        if hive_count is not None:
            source_count += 1

        return Snapshot(
            items=all_items[: self.capacity],
            events=events,
            revenue_active=revenue_active,
            revenue_queue=revenue_queue,
            revenue_pool=pool,
            revenue_provider=str(metrics.get("provider") or "unknown"),
            daemon_active=daemon_active,
            daemon_queue=daemon_queue,
            completed_60s=completed_60s,
            failed_60s=failed_60s,
            avg_stage_s=avg_stage_s,
            persisted_swarms=hive_count,
            latest_event_ts=latest_ts or None,
            source_count=source_count,
        )


def _event_sort_key(line: str) -> str:
    return line[:10]


def _stamp(ts: float) -> str:
    if not ts:
        return "--:--:--"
    return time.strftime("%H:%M:%S", time.localtime(ts))


def _float_or_none(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int_or_none(value: Any) -> Optional[int]:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fmt_duration(value: Optional[float]) -> str:
    if value is None:
        return "-"
    if value < 1:
        return f"{value * 1000:.0f}ms"
    return f"{value:.1f}s"


def _cell_label(slot: int, item: Optional[LiveItem], width: int) -> str:
    if item is None:
        return crop(f"HIVE-{slot:03d} NO LIVE DATA", width)
    key = crop(item.key, 9)
    stage = crop(item.stage or "-", 5)
    duration = _fmt_duration(item.duration_s)
    text = f"HIVE-{slot:03d} {item.state:<5} {key:<9} {stage:<5} {duration:>6}"
    return crop(text, width)


def render(
    snapshot: Snapshot,
    capacity: int,
    paused: bool,
    process_uptime: float,
    process_cpu_s: float,
    render_ms: float,
) -> str:
    cols, rows = shutil.get_terminal_size((120, 38))
    cols = max(72, cols)
    rows = max(24, rows)
    inner = cols - 4

    lines: list[str] = []
    title = "GPT-DOUG // GPT-CHAOS // REAL SWARM TELEMETRY // NO MOCK DATA"
    lines.append(RUST + "╭" + "─" * (cols - 2) + "╮" + RESET)
    lines.append(ORANGE + "│" + crop(title.center(cols - 2), cols - 2) + "│" + RESET)

    hive_count = (
        str(snapshot.persisted_swarms)
        if snapshot.persisted_swarms is not None
        else "N/A"
    )
    queue = (
        str(snapshot.revenue_queue)
        if snapshot.revenue_queue is not None
        else "N/A"
    )
    summary = (
        f"REAL ACTIVE revenue={snapshot.revenue_active} daemon={snapshot.daemon_active}  "
        f"QUEUE revenue={queue} daemon={snapshot.daemon_queue}  "
        f"PERSISTED SWARMS={hive_count}"
    )
    lines.append(GOLD + "│" + crop(summary.center(cols - 2), cols - 2) + "│" + RESET)

    mode = "PAUSED" if paused else "LIVE"
    controls = (
        f"MODE={mode}  q/Esc=RETURN  Space=PAUSE  r=REFRESH  Ctrl+C=KILL  "
        f"SOURCES={snapshot.source_count}"
    )
    lines.append(SAGE + "│" + crop(controls.center(cols - 2), cols - 2) + "│" + RESET)
    lines.append(RUST + "├" + "─" * (cols - 2) + "┤" + RESET)

    gap = 1
    grid_cols = min(5, max(2, inner // 28))
    boxw = max(22, (inner - gap * (grid_cols - 1)) // grid_cols)
    grid_rows = max(6, rows - 14)
    visible_slots = min(capacity, grid_cols * grid_rows)

    for row_start in range(0, visible_slots, grid_cols):
        chunks = []
        for offset in range(grid_cols):
            slot = row_start + offset + 1
            if slot > visible_slots:
                chunks.append(" " * boxw)
                continue
            item = snapshot.items[slot - 1] if slot <= len(snapshot.items) else None
            chunks.append(_cell_label(slot, item, boxw).ljust(boxw))
        row = (" " * gap).join(chunks)
        lines.append("│ " + CREAM + row + RESET + " │")

    lines.append(RUST + "├" + "─" * (cols - 2) + "┤" + RESET)

    avg = _fmt_duration(snapshot.avg_stage_s)
    age = (
        f"{max(0.0, time.time() - snapshot.latest_event_ts):.1f}s"
        if snapshot.latest_event_ts is not None
        else "N/A"
    )
    metrics = (
        f"MEASURED  done_60s={snapshot.completed_60s} fail_60s={snapshot.failed_60s} "
        f"avg_duration={avg} event_age={age} provider={snapshot.revenue_provider} "
        f"pool_cap={snapshot.revenue_pool if snapshot.revenue_pool is not None else 'N/A'}"
    )
    lines.append(AMBER + "│ " + crop(metrics, cols - 4).ljust(cols - 4) + " │" + RESET)

    process_line = (
        f"HUD PROCESS  uptime={process_uptime:.1f}s cpu_time={process_cpu_s:.2f}s "
        f"render={render_ms:.2f}ms pid={os.getpid()} load1={os.getloadavg()[0]:.2f}"
    )
    lines.append(DIMFG + "│ " + crop(process_line, cols - 4).ljust(cols - 4) + " │" + RESET)

    log_room = max(2, rows - len(lines) - 3)
    events = snapshot.events[-log_room:]
    for event in events:
        lines.append(DIMFG + "│ " + crop(event, cols - 4).ljust(cols - 4) + " │" + RESET)

    if not events:
        message = "NO TELEMETRY EVENTS FOUND // waiting for real runtime evidence"
        lines.append(DIMFG + "│ " + message.ljust(cols - 4) + " │" + RESET)

    while len(lines) < rows - 2:
        lines.append(DIMFG + "│" + " " * (cols - 2) + "│" + RESET)

    footer = (
        "TRUTH MODE=ON // EMPTY SLOTS MEAN NO OBSERVED WORK // "
        "NO SYNTHETIC STATUS OR PROGRESS"
    )
    lines.append(SAGE + "│" + crop(footer.center(cols - 2), cols - 2) + "│" + RESET)
    lines.append(RUST + "╰" + "─" * (cols - 2) + "╯" + RESET)
    return HOME + "\n".join(lines[:rows])


def main() -> int:
    parser = argparse.ArgumentParser(
        description="GPT-Doug truthful live swarm telemetry HUD"
    )
    parser.add_argument(
        "--frames",
        type=int,
        default=0,
        help="exit after N frames; 0 means run until q/Ctrl-C",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=2.0,
        help="telemetry refresh rate (default: 2)",
    )
    parser.add_argument(
        "--cells",
        type=int,
        default=100,
        help="display capacity; unused slots show NO LIVE DATA",
    )
    parser.add_argument("--repo", help="explicit GPT-Doug repository path")
    parser.add_argument(
        "--plain",
        action="store_true",
        help="no alternate screen; useful for tests/logs",
    )
    args = parser.parse_args()

    args.fps = max(0.5, min(args.fps, 10.0))
    args.cells = max(4, min(args.cells, 200))
    collector = TelemetryCollector(_repo_root(args.repo), args.cells)

    paused = False
    running = True
    frame_budget = args.frames
    snapshot = collector.snapshot()
    started = time.monotonic()
    render_ms = 0.0

    def stop(_sig=None, _frame=None) -> None:
        nonlocal running
        running = False

    old_int = signal.signal(signal.SIGINT, stop)
    old_term = signal.signal(signal.SIGTERM, stop)

    try:
        with TerminalMode(not args.plain) as term:
            while running:
                frame_started = time.monotonic()
                key = term.key()
                if key in {"q", "Q", "\x1b"}:
                    break
                if key == " ":
                    paused = not paused
                if not paused or key in {"r", "R"}:
                    snapshot = collector.snapshot()

                output = render(
                    snapshot,
                    args.cells,
                    paused,
                    time.monotonic() - started,
                    time.process_time(),
                    render_ms,
                )
                sys.stdout.write(output)
                if not term.enabled:
                    sys.stdout.write("\n")
                sys.stdout.flush()

                render_ms = (time.monotonic() - frame_started) * 1000.0
                if frame_budget > 0:
                    frame_budget -= 1
                    if frame_budget <= 0:
                        break
                time.sleep(max(0.0, (1.0 / args.fps) - (render_ms / 1000.0)))
    finally:
        signal.signal(signal.SIGINT, old_int)
        signal.signal(signal.SIGTERM, old_term)

    if sys.stdout.isatty():
        print(f"{SAGE}REAL SWARM TELEMETRY // TERMINAL CONTROL RETURNED{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
