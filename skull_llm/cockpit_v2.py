"""SKULL-LLM V2: terminal-first interactive 3D cockpit and observable reasoning.

Uses the existing local, bounded SKULL reasoning runtime. The CL1 display
shows software simulation only: no neuronal signal or hardware connection.
No paid APIs, model downloads, or terminal UI libraries are required.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import select
import shutil
import sys
import textwrap
import time
from typing import Any, Callable

from .live_skull import render_frame, status_snapshot


def _safe(value: object, limit: int = 100) -> str:
    """Never allow untrusted model/status text to inject terminal escapes."""
    return "".join(c if 32 <= ord(c) <= 126 else " " for c in str(value))[:limit]


def _line(value: str, width: int) -> str:
    return _safe(value, width).ljust(width)


def _state(status: dict[str, Any]) -> str:
    if status.get("emergency_stop"):
        return "STOPPED"
    return "READY" if status.get("inference_ready") else "OFFLINE"


def _hardware_state(status: dict[str, Any]) -> str:
    # The software has no real CL1 hardware adapter. This is not inferred
    # from hardware scans and must not be described as observed telemetry.
    return "CL1 HARDWARE: NOT CONNECTED | SYNAPSES: SIMULATED"


def _status_cards(status: dict[str, Any], *, width: int, phase: str, elapsed_ms: float | None) -> list[str]:
    lines = [
        "INFERENCE     " + _state(status),
        "MODEL         " + _safe(status.get("ollama_model", "not selected"), max(1, width - 14)),
        "REASONING     " + _safe(phase or "IDLE", max(1, width - 14)),
        "KILLSWITCH    " + ("ENGAGED" if status.get("emergency_stop") else "CLEAR"),
        "CL1 BIOCHIP   SIMULATED ONLY",
        "HARDWARE      NOT CONNECTED",
        "POINT CLOUD   PROCEDURAL 3D",
        "DEPTH BUFFER  ENABLED",
        "SOURCE        GPT-DOUG-LLM",
    ]
    if elapsed_ms is not None:
        lines.append("LAST FRAME    %.1f ms" % elapsed_ms)
    return [_line(line, width) for line in lines]


def compose_screen(
    *,
    yaw: float = 0.0,
    pitch: float = 0.0,
    zoom: float = 1.0,
    fusion: bool = True,
    tick: int = 0,
    width: int = 100,
    height: int = 36,
    status: dict[str, Any] | None = None,
    phase: str = "IDLE",
    frame_ms: float | None = None,
    help_open: bool = False,
) -> str:
    """Deterministic layout, with a real 3D z-buffer frame and separate HUD."""
    if not 0.55 <= zoom <= 2.0:
        raise ValueError("zoom must be in [0.55, 2]")
    width = min(max(48, int(width)), 160)
    height = min(max(24, int(height)), 60)
    snapshot = status or {}
    has_sidebar = width >= 96
    side_width = 32 if has_sidebar else 0
    visual_width = width - side_width - (3 if has_sidebar else 0)
    visual_width = max(36, visual_width)
    visual_height = max(18, min(54, height - (8 if has_sidebar else 14)))
    art = render_frame(
        yaw, pitch, columns=visual_width, rows=visual_height,
        tick=tick, fusion=fusion, zoom=zoom,
    ).splitlines()
    cards = _status_cards(snapshot, width=side_width, phase=phase, elapsed_ms=frame_ms) if has_sidebar else []
    if has_sidebar:
        cards = [
            _line("[ SYSTEM / LOCAL ]", side_width),
            _line("", side_width),
            *cards,
            _line("", side_width),
            _line("[ EXECUTION ]", side_width),
            _line("01 RETRIEVE", side_width),
            _line("02 DRAFT", side_width),
            _line("03 CRITIQUE", side_width),
            _line("04 REVISE", side_width),
            _line("", side_width),
            _line("[ REFERENCE ]", side_width),
            _line("XUNIA / ONTOLOGY", side_width),
            _line("BIOCHIP CL1 // SIMULATION", side_width),
        ]
    output = [
        _line("=" * width, width),
        _line(" BIOCHIP-CL1 // SKULL-GPT-SKULL // GPT-DOUG", width),
        _line(" 3D LIVE ASCII  |  INFERENCE: " + _state(snapshot) + "  |  REAL-TIME SOFTWARE VISUALIZER", width),
        _line("=" * width, width),
    ]
    for i in range(visual_height):
        left = art[i][:visual_width].ljust(visual_width)
        if has_sidebar:
            right = cards[i] if i < len(cards) else " " * side_width
            output.append(left + " | " + right)
        else:
            output.append(_line(left, width))
    output.append(_line("-" * width, width))
    if not has_sidebar:
        output.extend(_status_cards(snapshot, width=width, phase=phase, elapsed_ms=frame_ms)[:4])
    output.append(_line(" MODEL: " + _safe(snapshot.get("ollama_model", "not selected"), 48)
                        + "   CL1: SIMULATED", width))
    output.append(_line(
        " YAW %6.1f  PITCH %6.1f  ZOOM %.2f  FRAME %06d  SYNAPSE %s" %
        (math.degrees(yaw) % 360, math.degrees(pitch), zoom, tick, "ON" if fusion else "OFF"),
        width,
    ))
    if help_open:
        controls = [
            " [HELP]  a/d rotate  w/s tilt  +/- zoom  1/2/3 views",
            "         n neural  p pause  i ask LLM  g refresh status",
            "         v save ASCII snapshot  r reset  ? help  q quit",
        ]
    else:
        controls = [
            " a/d ROTATE  +/- ZOOM  1/2/3 VIEW  i ASK  g CHECK  v SAVE  ? HELP  q QUIT",
        ]
    output.extend(_line(line, width) for line in controls)
    output.append(_line(" " + _hardware_state(snapshot), width))
    return "\n".join(output)


def save_snapshot(path: str, screen: str) -> Path:
    """Create-only ASCII snapshot; never overwrite an existing user file."""
    target = Path(path).expanduser()
    if not target.parent.is_dir():
        raise ValueError("snapshot directory does not exist")
    descriptor = os.open(str(target), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="ascii") as handle:
            handle.write(screen + "\n")
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return target


def infer(
    task: str,
    *,
    depth: int = 2,
    remember: bool = False,
    on_phase: Callable[[str, str], None] | None = None,
):
    """Real underlying model execution stages; no fabricated tokens/rates."""
    from .runtime import SkullConfig, SkullEngine
    task = (task or "").strip()
    if not task:
        raise ValueError("task must not be empty")
    return SkullEngine(
        config=SkullConfig(depth=depth, remember=remember),
        on_progress=on_phase,
    ).run(task)


def _run_prompt(depth: int, restore, fd: int) -> None:
    import termios
    import tty
    termios.tcsetattr(fd, termios.TCSADRAIN, restore)
    try:
        sys.stdout.write("\nSKULL-GPT> ")
        sys.stdout.flush()
        prompt = input().strip()
        if not prompt:
            return
        print("\nLOCAL REASONING - actual phase events, no synthetic tokens:\n")
        started = time.monotonic()
        try:
            result = infer(
                prompt, depth=depth,
                on_phase=lambda stage, message: print(
                    "  [%s] %s" % (_safe(stage, 18).upper(), _safe(message, 160)), flush=True
                ),
            )
            print("\n" + result.answer)
            print(
                "\nMODEL CALLS: %d | ONTOLOGY: %d | MEMORY: %d | ELAPSED: %.1fs" % (
                    result.calls, result.ontology_hits, result.memory_hits,
                    time.monotonic() - started,
                )
            )
        except (RuntimeError, OSError, ValueError) as exc:
            print("INFERENCE FAILED:", _safe(exc, 300))
        input("\n[ENTER to return to 3D cockpit] ")
    finally:
        tty.setcbreak(fd)


def live(
    *,
    once: bool = False,
    frames: int = 0,
    fps: float = 10.0,
    depth: int = 2,
    output=None,
    input_stream=None,
    status: dict[str, Any] | None = None,
    viewport: tuple[int, int] | None = None,
) -> int:
    if not (1 <= fps <= 24) or not (0 <= frames <= 7200):
        raise ValueError("fps 1..24 and frames 0..7200 required")
    out = output if output is not None else sys.stdout
    inp = input_stream if input_stream is not None else sys.stdin
    tty_active = bool(out.isatty() and inp.isatty())
    if not tty_active and not frames:
        once = True
    status = status if status is not None else status_snapshot()
    yaw, pitch, zoom = 0.15, 0.0, 1.0
    fusion, paused, help_open = True, False, False
    last_ms: float | None = None
    count = 1 if once else frames
    previous = None
    fd = None
    if tty_active and not once:
        import termios
        import tty
        fd = inp.fileno()
        previous = termios.tcgetattr(fd)
        tty.setcbreak(fd)
    try:
        step = 0
        while True:
            start = time.monotonic()
            size = viewport or tuple(shutil.get_terminal_size((100, 36)))
            width, height = size
            width, height = max(48, min(width, 160)), max(24, min(height - 1, 60))
            frame = compose_screen(
                yaw=yaw, pitch=pitch, zoom=zoom, fusion=fusion, tick=step,
                width=width, height=height, status=status, frame_ms=last_ms,
                help_open=help_open,
            )
            last_ms = (time.monotonic() - start) * 1000
            if tty_active and not once:
                out.write("\x1b[H\x1b[J")
            out.write(frame + "\n")
            out.flush()
            step += 1
            if count and step >= count:
                break
            if not paused:
                yaw += 0.028
            pause = max(0.0, 1.0 / fps - (time.monotonic() - start))
            if tty_active and previous is not None:
                ready, _, _ = select.select([inp], [], [], pause)
                if ready:
                    key = inp.read(1)
                    if key in ("q", "\x03"):
                        break
                    if key == "a":
                        yaw -= 0.19
                    elif key == "d":
                        yaw += 0.19
                    elif key == "w":
                        pitch = max(-0.85, pitch - 0.11)
                    elif key == "s":
                        pitch = min(0.85, pitch + 0.11)
                    elif key in ("+", "="):
                        zoom = min(2.0, zoom + 0.12)
                    elif key in ("-", "_"):
                        zoom = max(0.55, zoom - 0.12)
                    elif key == "1":
                        yaw, pitch = 0.0, 0.0
                    elif key == "2":
                        yaw, pitch = 0.65, -0.09
                    elif key == "3":
                        yaw, pitch = 1.48, 0.0
                    elif key == "n":
                        fusion = not fusion
                    elif key in ("p", " "):
                        paused = not paused
                    elif key == "r":
                        yaw, pitch, zoom = 0.15, 0.0, 1.0
                    elif key == "?":
                        help_open = not help_open
                    elif key == "g":
                        status = status_snapshot()
                    elif key == "i":
                        _run_prompt(depth, previous, fd)
                    elif key == "v":
                        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime())
                        name = "skull-snapshot-%s-%06d.txt" % (stamp, step)
                        try:
                            save_snapshot(name, frame)
                        except (OSError, ValueError) as exc:
                            # A status line is shown on terminal; no silent overwrite.
                            out.write("SNAPSHOT FAILED: " + _safe(exc, 120) + "\n")
                        else:
                            out.write("SAVED: " + name + "\n")
                        out.flush()
            else:
                time.sleep(pause)
    except KeyboardInterrupt:
        return 130
    finally:
        if previous is not None:
            import termios
            termios.tcsetattr(fd, termios.TCSADRAIN, previous)
            out.write("\x1b[0m\n")
            out.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="biochip-cl1-skull-gpt-skull",
        description="3D terminal-first SKULL cockpit; CL1 is simulated.",
    )
    parser.add_argument(
        "action", nargs="?", choices=("live", "status", "ask", "serve", "snapshot"),
        default="live",
    )
    parser.add_argument("task", nargs="*")
    parser.add_argument("--once", action="store_true", help="single nonanimated cockpit frame")
    parser.add_argument("--frames", type=int, default=0, help="bounded frame count")
    parser.add_argument("--fps", type=float, default=10)
    parser.add_argument("--depth", type=int, choices=(1, 2, 3), default=2)
    parser.add_argument("--remember", action="store_true", help="opt in to episodic memory")
    parser.add_argument("--trace", action="store_true", help="show actual reasoning phase events")
    parser.add_argument("--out", help="ASCII snapshot filename (create only)")
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            print(json.dumps(status_snapshot(), indent=2))
            return 0
        if args.action == "serve":
            from .server import serve
            serve()
            return 0
        if args.action == "snapshot":
            if not args.out:
                parser.error("snapshot requires --out FILE")
            snapshot = compose_screen(
                width=100, height=36, status=status_snapshot(), tick=0,
            )
            print(str(save_snapshot(args.out, snapshot)))
            return 0
        if args.action == "ask":
            if not args.task:
                parser.error("ask requires prompt text")
            def progress(stage: str, message: str) -> None:
                print("[%s] %s" % (_safe(stage, 20), _safe(message, 160)), file=sys.stderr)
            result = infer(
                " ".join(args.task),
                depth=args.depth,
                remember=args.remember,
                on_phase=progress if args.trace else None,
            )
            print(result.answer)
            return 0
        return live(
            once=args.once, frames=args.frames, fps=args.fps, depth=args.depth,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        print("SKULL-LLM: " + _safe(exc, 300), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
