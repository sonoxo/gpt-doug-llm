"""BIOCHIP-CL1-SKULL-GPT-SKULL: terminal-first rotating 3D ASCII cockpit.

A genuine perspective/z-buffer projection of a procedurally sampled skull.
The CL1 activity layer is SYNTHETIC visual telemetry, NOT physical CL1
hardware or measured neuronal activity. Everything runs locally; inference
is delegated to the existing SKULL-LLM engine, with its global stop checks.
"""
from __future__ import annotations

import argparse
import functools
import json
import math
import os
import select
import shutil
import sys
import time
from dataclasses import dataclass


RAMP = " .,:;irsXA253hMHGS#9B&@"


@dataclass(frozen=True)
class Point:
    x: float
    y: float
    z: float
    nx: float
    ny: float
    nz: float
    layer: str = "bone"


@functools.lru_cache(maxsize=1)
def skull_cloud() -> tuple[Point, ...]:
    """Sample an anatomical-inspired THREE-DIMENSIONAL surface, no model download."""
    points: list[Point] = []

    # Rounded neurocranium. Frontal orbital sockets remove real surface points.
    for ti in range(2, 68):
        theta = ti * 2.06 / 68
        st, ct = math.sin(theta), math.cos(theta)
        for pi in range(126):
            phi = 2 * math.pi * pi / 126
            sx, sz = math.sin(phi), math.cos(phi)
            x, y, z = 0.87 * st * sx, -0.15 - 1.01 * ct, 0.80 * st * sz
            if z > 0.30:
                eye = ((abs(x) - 0.36) / 0.255) ** 2 + ((y + 0.11) / 0.22) ** 2
                if eye < 1.04:
                    continue
                nose = (x / (0.06 + max(0, y - 0.08) * 0.35)) ** 2
                if 0.15 < y < 0.42 and nose < 1:
                    continue
            points.append(Point(x, y, z, sx * st, -ct, sz * st))

    # Midface/maxilla and hollow nasal aperture.
    for yi in range(29):
        y = 0.19 + yi * 0.020
        taper = 0.67 - 0.18 * (y - 0.19) / 0.56
        for pi in range(96):
            phi = 2 * math.pi * pi / 96
            x, z = taper * math.sin(phi), 0.64 * math.cos(phi) + 0.025
            hole = 0.09 + 0.30 * max(0, y - 0.21)
            if z > 0.25 and abs(x) < hole and y < 0.48:
                continue
            points.append(Point(x, y, z, math.sin(phi), 0.10, math.cos(phi)))

    # Zygomatic arches highlight the cheekbone contours.
    for side in (-1, 1):
        for i in range(33):
            u = (i / 32 - 0.5) * 2
            for j in range(26):
                v = 2 * math.pi * j / 26
                radius = math.sqrt(max(0.0, 1 - u * u))
                x = side * (0.71 + 0.11 * u)
                y = 0.16 + 0.11 * u + 0.13 * radius * math.cos(v)
                z = 0.37 + 0.12 * radius * math.sin(v)
                points.append(Point(x, y, z, side, math.cos(v), math.sin(v)))

    # Mandibular arch with individual teeth.
    for yi in range(23):
        y = 0.61 + yi * 0.019
        radius = 0.62 - 0.23 * (y - 0.61)
        for pi in range(112):
            phi = 2 * math.pi * pi / 112
            x, z = radius * math.sin(phi), 0.51 * math.cos(phi) + 0.08
            if abs(x) < 0.22 and 0.64 < y < 0.82 and z < 0.05:
                continue
            points.append(Point(x, y, z, math.sin(phi), 0.13, math.cos(phi)))
    for row in (0, 1):
        for i in range(-6, 7):
            x = i * 0.077
            y = 0.60 + 0.095 * row
            z = 0.72 - 0.27 * (abs(x) / 0.55) ** 2
            for a in range(10):
                for b in range(7):
                    ang = 2 * math.pi * a / 10
                    lift = (b / 6 - 0.5) * 0.09
                    px = x + math.sin(ang) * 0.030
                    pz = z + math.cos(ang) * 0.034
                    points.append(Point(px, y + lift, pz, math.sin(ang), 0.1, math.cos(ang)))

    # Internal, optional neural fluorescence; simulated signals only.
    for i in range(320):
        a = i * 2.399963229728653
        v = 1 - 2 * ((i + 0.5) / 320)
        r = (1 - v * v) ** 0.5
        x = 0.69 * r * math.cos(a)
        y = -0.15 - 0.75 * v
        z = 0.60 * r * math.sin(a)
        points.append(Point(x, y, z, 0, 0, 1, "sim-neuron"))
    return tuple(points)


def _rotate(p: Point, yaw: float, pitch: float) -> tuple[float, float, float, float]:
    cy, sy = math.cos(yaw), math.sin(yaw)
    cp, sp = math.cos(pitch), math.sin(pitch)
    x = cy * p.x + sy * p.z
    front = -sy * p.x + cy * p.z
    y = cp * p.y - sp * front
    z = sp * p.y + cp * front
    nz = cp * (-sy * p.nx + cy * p.nz) + sp * p.ny
    return x, y, z, nz


def render_frame(
    yaw: float = 0.0,
    pitch: float = 0.0,
    *,
    columns: int = 68,
    rows: int = 30,
    tick: int = 0,
    fusion: bool = True,
) -> str:
    """Rotate and perspective-project real 3D points through a z-buffer."""
    if not 36 <= columns <= 140 or not 18 <= rows <= 54:
        raise ValueError("frame dimensions out of range")
    pixels = [[" "] * columns for _ in range(rows)]
    zbuf = [[-99.0] * columns for _ in range(rows)]
    for idx, p in enumerate(skull_cloud()):
        if p.layer == "sim-neuron" and (not fusion or (idx + tick * 7) % 5):
            continue
        x, y, z, normal = _rotate(p, yaw, pitch)
        perspective = max(1.5, 3.8 - z * 0.28)
        col = int(columns / 2 + (x / perspective) * columns * 1.44)
        row = int(rows / 2 + (y / perspective) * rows * 1.37)
        if not (0 <= col < columns and 0 <= row < rows):
            continue
        if z <= zbuf[row][col]:
            continue
        zbuf[row][col] = z
        if p.layer == "sim-neuron":
            character = "*" if tick % 3 else "+"
        else:
            lighting = max(0.0, min(1.0, 0.42 + 0.32 * normal - 0.12 * x + 0.11 * y))
            character = RAMP[min(len(RAMP) - 1, int(lighting * (len(RAMP) - 1)))]
        pixels[row][col] = character
    return "\n".join("".join(line).rstrip() for line in pixels)


def status_snapshot() -> dict:
    from .cli import doctor

    result = doctor()
    return {
        "name": "BIOCHIP-CL1-SKULL-GPT-SKULL",
        "inference_ready": bool(result.get("ready_for_inference")),
        "emergency_stop": bool(result.get("stopped")),
        "ollama_model": str((result.get("ollama") or {}).get("model") or "not selected"),
        "cl1_hardware": "NOT CONNECTED",
        "cl1_visualization": "SIMULATED / NO HARDWARE DATA",
    }


def console_frame(
    *,
    yaw: float = 0.0,
    pitch: float = 0.0,
    tick: int = 0,
    columns: int = 80,
    lines: int = 39,
    fusion: bool = True,
    status: dict | None = None,
) -> str:
    width = max(48, min(columns, 140))
    h = max(18, min(lines - 9, 42))
    area = render_frame(yaw, pitch, columns=width - 2, rows=h, tick=tick, fusion=fusion)
    state = status or {}
    online = "READY" if state.get("inference_ready") else "OFFLINE"
    if state.get("emergency_stop"):
        online = "STOPPED"
    model = "".join(ch if 32 <= ord(ch) < 127 else " " for ch in str(
        state.get("ollama_model", "not selected")
    ))[:45]
    divider = "=" * width
    output = [
        divider,
        " BIOCHIP-CL1 // SKULL-GPT-SKULL // GPT-DOUG".ljust(width)[:width],
        (" MODE: 3D ASCII  |  INFERENCE: " + online + "  |  CL1: SIMULATED").ljust(width)[:width],
        divider,
    ]
    output.extend(" " + line.ljust(width - 2) + " " for line in area.split("\n"))
    output += [
        divider,
        (" MODEL: " + model).ljust(width)[:width],
        (" YAW: %5.1f deg   PITCH: %5.1f deg   FRAME: %06d" %
         (math.degrees(yaw), math.degrees(pitch), tick)).ljust(width)[:width],
        " a/d=orbit  w/s=tilt  n=neural  p=pause  i=ask  r=reset  q=quit".ljust(width)[:width],
        " CL1 IS A SOFTWARE SIMULATION; NO NEURONAL HARDWARE TELEMETRY.".ljust(width)[:width],
    ]
    return "\n".join(output)


def ask_local(task: str, depth: int = 2, remember: bool = False) -> str:
    from .runtime import SkullConfig, SkullEngine

    engine = SkullEngine(config=SkullConfig(depth=depth, remember=remember))
    return engine.run(task).answer


def _interactive_chat(restore: list, fd: int, depth: int) -> None:
    import termios
    import tty

    termios.tcsetattr(fd, termios.TCSADRAIN, restore)
    try:
        sys.stdout.write("\n SKULL> ")
        sys.stdout.flush()
        prompt = input()
        if prompt.strip():
            try:
                answer = ask_local(prompt.strip(), depth=depth)
                print("\n" + answer + "\n")
            except (RuntimeError, OSError, ValueError) as exc:
                print("\nLLM UNAVAILABLE: " + str(exc)[:200] + "\n")
            input("[press ENTER to resume the skull] ")
    finally:
        tty.setcbreak(fd)


def live(
    *,
    frames: int = 0,
    fps: float = 12,
    once: bool = False,
    depth: int = 2,
    output=None,
    input_stream=None,
    status: dict | None = None,
) -> int:
    """Animate in a TTY; render just one frame when output is redirected."""
    if not 1 <= fps <= 24:
        raise ValueError("fps must be between 1 and 24")
    if frames < 0 or frames > 7200:
        raise ValueError("frames must be 0..7200")
    out = output or sys.stdout
    inp = input_stream or sys.stdin
    is_tty = bool(out.isatty() and inp.isatty())
    if not is_tty and frames == 0:
        once = True
    state = status if status is not None else status_snapshot()
    terminal = shutil.get_terminal_size((80, 39))
    width = max(48, min(terminal.columns, 140))
    height = max(28, min(terminal.lines, 52))
    yaw, pitch = 0.15, 0.0
    paused, fusion = False, True
    count = 1 if once else frames
    try:
        if is_tty and not once:
            import termios
            import tty

            fd = inp.fileno()
            previous = termios.tcgetattr(fd)
            tty.setcbreak(fd)
        else:
            previous = None
        try:
            step = 0
            while True:
                start = time.monotonic()
                frame = console_frame(
                    yaw=yaw, pitch=pitch, tick=step,
                    columns=width, lines=height, fusion=fusion, status=state,
                )
                if is_tty and not once:
                    out.write("\x1b[H\x1b[2J")
                out.write(frame + "\n")
                out.flush()
                step += 1
                if count and step >= count:
                    break
                if not paused:
                    yaw += 0.032
                remaining = max(0, 1 / fps - (time.monotonic() - start))
                if is_tty and previous is not None:
                    ready, _, _ = select.select([inp], [], [], remaining)
                    if ready:
                        key = inp.read(1)
                        if key in {"q", "\x03"}:
                            break
                        if key == "a":
                            yaw -= 0.18
                        if key == "d":
                            yaw += 0.18
                        if key == "w":
                            pitch = max(-0.85, pitch - 0.10)
                        if key == "s":
                            pitch = min(0.85, pitch + 0.10)
                        if key == "p" or key == " ":
                            paused = not paused
                        if key == "n":
                            fusion = not fusion
                        if key == "r":
                            yaw, pitch = 0.15, 0.0
                        if key == "i":
                            _interactive_chat(previous, inp.fileno(), depth)
                else:
                    time.sleep(remaining)
        finally:
            if previous is not None:
                termios.tcsetattr(fd, termios.TCSADRAIN, previous)
            if is_tty and not once:
                out.write("\x1b[0m\n")
    except KeyboardInterrupt:
        return 130
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="biochip-cl1-skull-gpt-skull",
        description="Terminal-first 3D SKULL-LLM cockpit. CL1 activity is simulated.",
    )
    parser.add_argument("action", nargs="?", default="live",
                        choices=("live", "status", "ask", "serve"))
    parser.add_argument("task", nargs="*")
    parser.add_argument("--once", action="store_true", help="print a non-animated 3D frame")
    parser.add_argument("--frames", type=int, default=0, help="bounded animation frames")
    parser.add_argument("--fps", type=float, default=12)
    parser.add_argument("--depth", type=int, choices=[1, 2, 3], default=2)
    parser.add_argument("--remember", action="store_true", help="opt in to local memory writes")
    args = parser.parse_args(argv)
    try:
        if args.action == "status":
            print(json.dumps(status_snapshot(), indent=2))
            return 0
        if args.action == "ask":
            task = " ".join(args.task).strip()
            if not task:
                parser.error("ask requires task text")
            print(ask_local(task, depth=args.depth, remember=args.remember))
            return 0
        if args.action == "serve":
            from .server import serve
            serve()
            return 0
        return live(frames=args.frames, fps=args.fps, once=args.once, depth=args.depth)
    except (OSError, RuntimeError, ValueError) as exc:
        print("SKULL-LLM: " + str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
