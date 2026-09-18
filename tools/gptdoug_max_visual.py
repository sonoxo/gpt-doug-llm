#!/usr/bin/env python3
"""State-driven GPT-Doug MAX terminal skin // Smooth Motion Engine.

The renderer is view-only and watches ~/.gpt-doug/max-shell-state.json.

Smoothness strategy:
- 60 Hz animation clock with frame-rate-independent easing.
- Localized head/eye/brow/mouth/shoulder motion instead of re-scaling the
  entire portrait every frame.
- Quantized truecolor cells to reduce escape-code churn.
- Differential ANSI painting: only changed terminal cells are repainted.
- Full redraw only on resize, first frame, or large POWER/ERROR transitions.

This keeps the command shell and visual renderer in separate PTYs while making
Terminal.app repaint far less data per frame.
"""
from __future__ import annotations

import json
import math
import os
import shutil
import signal
import sys
import time
from pathlib import Path

try:
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter
except ImportError as exc:
    raise SystemExit("Pillow is required for the visual shell: python3 -m pip install pillow") from exc

STATE_FILE = Path.home() / ".gpt-doug" / "max-shell-state.json"
SKIN_CANDIDATES = [
    Path(os.environ.get("GPT_DOUG_SKIN", "")).expanduser() if os.environ.get("GPT_DOUG_SKIN") else None,
    Path.home() / "Pictures" / "gptdoug-alive-v2.png",
    Path.home() / "Pictures" / "gptdoug-alive.png",
]
SKIN = next((p for p in SKIN_CANDIDATES if p and p.exists()), None)
if SKIN is None:
    raise SystemExit("GPT-Doug skin missing. Set GPT_DOUG_SKIN or save ~/Pictures/gptdoug-alive-v2.png")

FPS = max(15.0, min(float(os.environ.get("GPT_DOUG_VISUAL_FPS", "60")), 60.0))
FRAME_TIME = 1.0 / FPS

# "24K" here means maximum-fidelity terminal sampling from the master portrait.
# ANSI terminals cannot physically display a 24,576-pixel-wide raster; output is
# still bounded by the visible terminal character grid.
VISUAL_PRESET = os.environ.get("GPT_DOUG_VISUAL_PRESET", "").strip().lower()
if VISUAL_PRESET in {"24k", "24k-master", "ultra"}:
    MAX_RENDER_COLS = max(120, min(int(os.environ.get("GPT_DOUG_VISUAL_COLS", "240")), 320))
    COLOR_STEP = max(4, min(int(os.environ.get("GPT_DOUG_COLOR_STEP", "8")), 32))
else:
    MAX_RENDER_COLS = max(64, min(int(os.environ.get("GPT_DOUG_VISUAL_COLS", "110")), 320))
    COLOR_STEP = max(4, min(int(os.environ.get("GPT_DOUG_COLOR_STEP", "16")), 64))

DIFF_FULL_THRESHOLD = max(0.15, min(float(os.environ.get("GPT_DOUG_DIFF_THRESHOLD", "0.58")), 0.95))

RESET = "\033[0m"
HOME = "\033[H"
CLEAR = "\033[2J"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
ALT_ON = "\033[?1049h"
ALT_OFF = "\033[?1049l"
WRAP_OFF = "\033[?7l"
WRAP_ON = "\033[?7h"
BLACK = "\033[48;2;0;0;0m"
CLEAR_EOL = "\033[K"

running = True


def stop(*_args):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def read_state() -> dict:
    try:
        payload = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            return payload
    except Exception:
        pass
    return {
        "state": "IDLE",
        "detail": "waiting for GPT-Doug MAX",
        "provider": "unknown",
        "model": "unknown",
    }


def fg(rgb):
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


def bg(rgb):
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m"


def cursor(row: int, col: int = 1) -> str:
    return f"\033[{row};{col}H"


def quantize(rgb):
    step = COLOR_STEP
    return tuple(min(255, (int(c) // step) * step) for c in rgb)


def fit(img: Image.Image) -> Image.Image:
    cols, rows = shutil.get_terminal_size((180, 60))
    max_cols = min(MAX_RENDER_COLS, max(54, cols - 4))
    max_rows = max(18, rows - 5)
    max_h_px = max_rows * 2
    scale = min(max_cols / img.width, max_h_px / img.height)
    w = max(24, int(img.width * scale))
    h = max(24, int(img.height * scale))
    if h % 2:
        h -= 1
    return img.resize((w, h), Image.Resampling.LANCZOS)


def rgb_shift(img: Image.Image, amount: int) -> Image.Image:
    if not amount:
        return img
    r, g, b = img.split()
    return Image.merge(
        "RGB",
        (
            ImageChops.offset(r, amount, 0),
            g,
            ImageChops.offset(b, -amount, 0),
        ),
    )


def tint(img: Image.Image, rgb: tuple[int, int, int], strength: float) -> Image.Image:
    layer = Image.new("RGB", img.size, rgb)
    return Image.blend(img, layer, max(0.0, min(strength, 0.75)))


def warp_region(
    img: Image.Image,
    box,
    *,
    sx=1.0,
    sy=1.0,
    dx=0.0,
    dy=0.0,
    brightness=1.0,
) -> Image.Image:
    x1, y1, x2, y2 = box
    crop = img.crop((x1, y1, x2, y2))
    if brightness != 1.0:
        crop = ImageEnhance.Brightness(crop).enhance(brightness)
    cw, ch = max(1, x2 - x1), max(1, y2 - y1)
    nw, nh = max(2, int(cw * sx)), max(2, int(ch * sy))
    crop = crop.resize((nw, nh), Image.Resampling.BICUBIC)
    out = img.copy()
    px = int((x1 + x2) / 2 - nw / 2 + dx)
    py = int((y1 + y2) / 2 - nh / 2 + dy)
    blur = max(1, min(nw, nh) // 20)
    mask = Image.new("L", (nw, nh), 255).filter(ImageFilter.GaussianBlur(blur))
    out.paste(crop, (px, py), mask)
    return out


class Motion:
    """Frame-rate-independent state easing."""

    NAMES = ("listen", "think", "talk", "act", "power", "error", "offline")

    def __init__(self):
        self.levels = {name: 0.0 for name in self.NAMES}

    def update(self, state: str, dt: float) -> dict[str, float]:
        state = state.lower()
        response = 8.5
        alpha = 1.0 - math.exp(-response * max(0.001, min(dt, 0.05)))
        for name in self.NAMES:
            target = 1.0 if name == state else 0.0
            self.levels[name] += (target - self.levels[name]) * alpha
        return self.levels


def blink_amount(t: float) -> float:
    """Two quick natural blinks about every 4.6 seconds."""
    phase = t % 4.6
    if phase < 0.11:
        return math.sin(math.pi * phase / 0.11)
    if 0.20 < phase < 0.29:
        return 0.62 * math.sin(math.pi * (phase - 0.20) / 0.09)
    return 0.0


def animate(base: Image.Image, levels: dict[str, float], t: float) -> Image.Image:
    listen = levels["listen"]
    think = levels["think"]
    talk = levels["talk"]
    act = levels["act"]
    power = levels["power"]
    error = levels["error"]
    offline = levels["offline"]

    frame = base.copy()
    w, h = frame.size

    head = (int(w * 0.25), int(h * 0.06), int(w * 0.75), int(h * 0.69))
    shoulders = (int(w * 0.15), int(h * 0.60), int(w * 0.85), int(h * 0.95))
    left_eye = (int(w * 0.35), int(h * 0.30), int(w * 0.47), int(h * 0.43))
    right_eye = (int(w * 0.53), int(h * 0.30), int(w * 0.65), int(h * 0.43))
    mouth = (int(w * 0.39), int(h * 0.52), int(w * 0.61), int(h * 0.64))
    left_brow = (int(w * 0.32), int(h * 0.25), int(w * 0.48), int(h * 0.34))
    right_brow = (int(w * 0.52), int(h * 0.25), int(w * 0.68), int(h * 0.34))

    # Breathing lives mostly in the shoulders, so the whole image does not
    # thrash every frame. This is much friendlier to differential painting.
    breath = math.sin(t * 1.25)
    frame = warp_region(
        frame,
        shoulders,
        sy=1.0 + 0.007 * breath,
        dy=0.55 * breath,
        brightness=1.0 + 0.012 * max(0.0, breath),
    )

    # Subtle head presence / listening lean / action focus.
    head_dx = (
        math.sin(t * 0.62) * 0.55
        + listen * math.sin(t * 0.95) * 0.65
        + act * math.sin(t * 2.4) * 0.35
    )
    head_dy = math.sin(t * 0.83) * 0.34
    frame = warp_region(frame, head, dx=head_dx, dy=head_dy)

    # Natural blink remains active in every non-offline state.
    blink = blink_amount(t) * (1.0 - offline)
    eye_sy = max(0.16, 1.0 - blink * 0.78 - talk * 0.035)
    eye_bright = 1.0 + listen * 0.22 + think * 0.10 + talk * 0.08 + power * 0.55
    frame = warp_region(frame, left_eye, sy=eye_sy, brightness=eye_bright)
    frame = warp_region(frame, right_eye, sy=eye_sy, brightness=eye_bright)

    # Brow movement gives thought and speech more readable expression.
    brow_lift = -(think * 1.6 + talk * 0.65 + power * 2.4)
    brow_light = 1.0 + think * 0.07 + power * 0.12
    frame = warp_region(frame, left_brow, dy=brow_lift, brightness=brow_light)
    frame = warp_region(frame, right_brow, dy=brow_lift, brightness=brow_light)

    # Smooth pseudo-phoneme motion. Multiple frequencies avoid a robotic
    # single-sine mouth.
    speech_wave = (
        0.50
        + 0.23 * math.sin(t * 10.5)
        + 0.13 * math.sin(t * 16.8 + 0.7)
        + 0.07 * math.sin(t * 23.5 + 1.9)
    )
    mouth_open = max(0.0, min(1.0, speech_wave)) * talk
    if mouth_open > 0.002:
        frame = warp_region(
            frame,
            mouth,
            sx=1.0 - mouth_open * 0.035,
            sy=1.0 + mouth_open * 0.30,
            dy=mouth_open * 0.85,
            brightness=1.0 + mouth_open * 0.06,
        )

    # THINK/ACT are deliberately restrained: small chromatic drift, not a
    # full-frame seizure. POWER is the intentionally dramatic exception.
    shift = int(round(
        think * math.sin(t * 4.6) * 1.1
        + act * math.sin(t * 7.0) * 1.0
        + power * (2.0 + abs(math.sin(t * 8.0)) * 3.0)
        + error * math.sin(t * 13.0) * 2.0
    ))
    if shift:
        frame = rgb_shift(frame, shift)

    if power > 0.01:
        pulse = abs(math.sin(t * 6.8))
        frame = ImageEnhance.Contrast(frame).enhance(1.0 + power * (0.10 + 0.08 * pulse))
        frame = ImageEnhance.Brightness(frame).enhance(1.0 + power * (0.08 + 0.10 * pulse))
        if power > 0.35:
            bloom = frame.filter(ImageFilter.GaussianBlur(1.6 + 1.4 * pulse))
            frame = Image.blend(frame, bloom, min(0.08, 0.035 + power * 0.035))

    if error > 0.01:
        frame = tint(frame, (255, 0, 0), 0.10 * error)

    if offline > 0.01:
        frame = ImageEnhance.Brightness(frame).enhance(1.0 - 0.58 * offline)

    return frame


def cell_grid(img: Image.Image):
    px = img.load()
    w, h = img.size
    rows = []
    for y in range(0, h, 2):
        row = []
        for x in range(w):
            top = quantize(px[x, y])
            bottom = quantize(px[x, min(y + 1, h - 1)])
            if max(top) < COLOR_STEP and max(bottom) < COLOR_STEP:
                row.append(None)
            else:
                row.append((top, bottom))
        rows.append(row)
    return rows


def encode_cells(cells) -> str:
    out = []
    last_fg = None
    last_bg = None
    for cell in cells:
        if cell is None:
            if last_bg != (0, 0, 0):
                out.append(BLACK)
                last_bg = (0, 0, 0)
            out.append(" ")
            last_fg = None
            continue
        top, bottom = cell
        if top != last_fg:
            out.append(fg(top))
            last_fg = top
        if bottom != last_bg:
            out.append(bg(bottom))
            last_bg = bottom
        out.append("▀")
    return "".join(out)


def changed_count(previous, current) -> int:
    if previous is None or len(previous) != len(current):
        return sum(len(row) for row in current)
    changed = 0
    for old_row, new_row in zip(previous, current):
        if len(old_row) != len(new_row):
            changed += len(new_row)
            continue
        changed += sum(1 for old, new in zip(old_row, new_row) if old != new)
    return changed


def render_full(grid, left: int, header_lines: list[str], footer: str) -> str:
    out = [HOME, BLACK]
    for index, line in enumerate(header_lines, start=1):
        out.extend([cursor(index, 1), line, RESET, BLACK, CLEAR_EOL])
    image_row = len(header_lines) + 1
    for index, row in enumerate(grid):
        out.extend(
            [
                cursor(image_row + index, 1),
                BLACK,
                " " * left,
                encode_cells(row),
                RESET,
                BLACK,
                CLEAR_EOL,
            ]
        )
    footer_row = image_row + len(grid)
    out.extend([cursor(footer_row, 1), footer, RESET, BLACK, CLEAR_EOL])
    return "".join(out)


def render_diff(previous, current, left: int, image_row: int) -> str:
    out = []
    for row_index, (old_row, new_row) in enumerate(zip(previous, current)):
        x = 0
        width = len(new_row)
        while x < width:
            if x < len(old_row) and old_row[x] == new_row[x]:
                x += 1
                continue
            start = x
            x += 1
            while x < width and (x >= len(old_row) or old_row[x] != new_row[x]):
                x += 1
            run = new_row[start:x]
            out.extend(
                [
                    cursor(image_row + row_index, left + start + 1),
                    encode_cells(run),
                    RESET,
                    BLACK,
                ]
            )
    return "".join(out)


def main() -> int:
    source = Image.open(SKIN).convert("RGB")
    base = fit(source)
    last_size = shutil.get_terminal_size()
    motion = Motion()
    previous_grid = None
    previous_header = None
    previous_footer = None
    previous_left = None
    start = time.perf_counter()
    last_tick = start
    next_frame = start

    sys.stdout.write(ALT_ON + CLEAR + HIDE + WRAP_OFF + BLACK)
    sys.stdout.flush()

    try:
        while running:
            now = time.perf_counter()
            dt = max(0.001, min(now - last_tick, 0.05))
            last_tick = now

            size = shutil.get_terminal_size()
            resized = size != last_size
            if resized:
                last_size = size
                base = fit(source)
                previous_grid = None
                previous_left = None
                sys.stdout.write(CLEAR)

            state = read_state()
            name = str(state.get("state", "IDLE")).upper()
            detail = str(state.get("detail", ""))[:100]
            provider = str(state.get("provider", "unknown"))
            model = str(state.get("model", "unknown"))
            levels = motion.update(name, dt)

            frame = animate(base, levels, now - start)
            grid = cell_grid(frame)
            cols, _rows = size
            left = max(0, (cols - len(grid[0])) // 2) if grid and grid[0] else 0

            header_lines = [
                "\033[38;2;0;240;255m24K // GPT-DOUG MAX // "
                + ("24K MASTER TERMINAL SAMPLE" if VISUAL_PRESET in {"24k", "24k-master", "ultra"} else "SMOOTH LIVE SKIN")
                + "\033[0m"
                f"  \033[38;2;80;255;120m[{name}]\033[0m",
                f"\033[38;2;255;70;220m{provider} // {model}\033[0m  {detail}",
            ]
            footer = (
                "\033[38;2;255;220;70mSMOOTH BUS\033[0m  "
                f"target={FPS:.0f}fps  cols={len(grid[0]) if grid else 0}  "
                f"quant={COLOR_STEP}  CTRL+C=visual-off"
            )

            total = max(1, sum(len(row) for row in grid))
            changed = changed_count(previous_grid, grid)
            ratio = changed / total

            must_full = (
                previous_grid is None
                or previous_left != left
                or ratio >= DIFF_FULL_THRESHOLD
                or resized
            )

            image_row = len(header_lines) + 1
            output = []

            if must_full:
                output.append(render_full(grid, left, header_lines, footer))
            else:
                if previous_header != header_lines:
                    for idx, line in enumerate(header_lines, start=1):
                        output.extend([cursor(idx, 1), line, RESET, BLACK, CLEAR_EOL])
                output.append(render_diff(previous_grid, grid, left, image_row))
                if previous_footer != footer:
                    footer_row = image_row + len(grid)
                    output.extend([cursor(footer_row, 1), footer, RESET, BLACK, CLEAR_EOL])

            if output:
                sys.stdout.write("".join(output))
                sys.stdout.flush()

            previous_grid = grid
            previous_header = header_lines
            previous_footer = footer
            previous_left = left

            next_frame += FRAME_TIME
            remaining = next_frame - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            else:
                # Drop missed visual deadlines instead of building a lag queue.
                next_frame = time.perf_counter()

        return 0
    finally:
        sys.stdout.write(RESET + WRAP_ON + SHOW + ALT_OFF)
        sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
