#!/usr/bin/env python3
"""State-driven GPT-Doug MAX terminal skin.

This renderer is intentionally view-only. It watches ~/.gpt-doug/max-shell-state.json
and animates the canonical portrait without owning the command prompt. Keeping the
renderer and operator shell in separate PTYs prevents the input lockups/ghosting that
occur when two loops fight over the same terminal buffer.
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

FPS = max(10.0, min(float(os.environ.get("GPT_DOUG_VISUAL_FPS", "60")), 60.0))
FRAME_TIME = 1.0 / FPS
RESET = "\033[0m"
HOME = "\033[H"
CLEAR = "\033[2J"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
ALT_ON = "\033[?1049h"
ALT_OFF = "\033[?1049l"
BLACK = "\033[48;2;0;0;0m"

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
    return {"state": "IDLE", "detail": "waiting for GPT-Doug MAX", "provider": "unknown", "model": "unknown"}


def fg(rgb):
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


def bg(rgb):
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m"


def fit(img: Image.Image) -> Image.Image:
    cols, rows = shutil.get_terminal_size((180, 60))
    max_cols = max(50, cols - 2)
    max_rows = max(20, rows - 5)
    max_h_px = max_rows * 2
    scale = min(max_cols / img.width, max_h_px / img.height)
    w = max(24, int(img.width * scale))
    h = max(24, int(img.height * scale))
    if h % 2:
        h -= 1
    return img.resize((w, h), Image.Resampling.LANCZOS)


def zoom(img: Image.Image, scale: float, dx: float = 0.0, dy: float = 0.0) -> Image.Image:
    w, h = img.size
    nw, nh = max(2, int(w * scale)), max(2, int(h * scale))
    z = img.resize((nw, nh), Image.Resampling.BICUBIC)
    if scale >= 1:
        x = max(0, min((nw - w) // 2 + int(dx), nw - w))
        y = max(0, min((nh - h) // 2 + int(dy), nh - h))
        return z.crop((x, y, x + w, y + h))
    out = Image.new("RGB", (w, h), "black")
    out.paste(z, ((w - nw) // 2 + int(dx), (h - nh) // 2 + int(dy)))
    return out


def rgb_shift(img: Image.Image, amount: int) -> Image.Image:
    if not amount:
        return img
    r, g, b = img.split()
    return Image.merge("RGB", (ImageChops.offset(r, amount, 0), g, ImageChops.offset(b, -amount, 0)))


def tint(img: Image.Image, rgb: tuple[int, int, int], strength: float) -> Image.Image:
    layer = Image.new("RGB", img.size, rgb)
    return Image.blend(img, layer, max(0.0, min(strength, 0.75)))


def warp_region(img: Image.Image, box, *, sx=1.0, sy=1.0, dx=0.0, dy=0.0, brightness=1.0) -> Image.Image:
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
    mask = Image.new("L", (nw, nh), 255).filter(ImageFilter.GaussianBlur(max(1, min(nw, nh) // 18)))
    out.paste(crop, (px, py), mask)
    return out


def animate(base: Image.Image, state: str, t: float) -> Image.Image:
    state = state.upper()
    breathe = math.sin(t * 1.2)
    shake_x = shake_y = 0.0
    scale = 1.0 + breathe * 0.0035
    brightness = 1.0
    shift = 0

    if state == "LISTEN":
        scale += 0.003
        brightness = 1.04
    elif state == "THINK":
        shift = int(round(math.sin(t * 5.0) * 1.5))
        brightness = 1.03 + 0.03 * abs(math.sin(t * 2.5))
    elif state == "TALK":
        brightness = 1.04 + 0.025 * abs(math.sin(t * 8.0))
    elif state == "ACT":
        scale += 0.005 * abs(math.sin(t * 4.0))
        shift = int(round(math.sin(t * 8.0) * 1.5))
    elif state == "POWER":
        scale += 0.015 * abs(math.sin(t * 6.0))
        shift = int(2 + abs(math.sin(t * 8.0)) * 5)
        shake_x = math.sin(t * 31.0) * 2.0 + math.sin(t * 17.0)
        shake_y = math.sin(t * 27.0) * 1.5
        brightness = 1.10 + 0.14 * abs(math.sin(t * 7.0))
    elif state == "ERROR":
        shift = int(round(math.sin(t * 14.0) * 3.0))
    elif state == "OFFLINE":
        brightness = 0.45

    frame = zoom(base, scale, shake_x, shake_y)
    if shift:
        frame = rgb_shift(frame, shift)
    frame = ImageEnhance.Brightness(frame).enhance(brightness)

    w, h = frame.size
    left_eye = (int(w * 0.35), int(h * 0.30), int(w * 0.47), int(h * 0.43))
    right_eye = (int(w * 0.53), int(h * 0.30), int(w * 0.65), int(h * 0.43))
    mouth = (int(w * 0.39), int(h * 0.52), int(w * 0.61), int(h * 0.64))
    brows = [
        (int(w * 0.32), int(h * 0.25), int(w * 0.48), int(h * 0.34)),
        (int(w * 0.52), int(h * 0.25), int(w * 0.68), int(h * 0.34)),
    ]

    if state == "LISTEN":
        frame = warp_region(frame, left_eye, brightness=1.35)
        frame = warp_region(frame, right_eye, brightness=1.35)
    elif state == "THINK":
        lift = -1.2 - abs(math.sin(t * 2.0)) * 1.5
        for box in brows:
            frame = warp_region(frame, box, dy=lift, brightness=1.12)
    elif state == "TALK":
        mouth_open = 0.22 + 0.13 * math.sin(t * 10.5) + 0.08 * math.sin(t * 17.0 + 0.7)
        mouth_open = max(0.02, min(0.42, mouth_open))
        frame = warp_region(frame, mouth, sx=1.0 - mouth_open * 0.08, sy=1.0 + mouth_open, dy=mouth_open * 2.0, brightness=1.08)
        frame = warp_region(frame, left_eye, sy=0.98, brightness=1.15)
        frame = warp_region(frame, right_eye, sy=0.98, brightness=1.15)
    elif state == "POWER":
        frame = warp_region(frame, left_eye, brightness=1.65)
        frame = warp_region(frame, right_eye, brightness=1.65)
        frame = ImageEnhance.Contrast(frame).enhance(1.18)
        bloom = frame.filter(ImageFilter.GaussianBlur(2.0 + 2.0 * abs(math.sin(t * 7.0))))
        frame = Image.blend(frame, bloom, 0.08)
    elif state == "ERROR":
        frame = tint(frame, (255, 0, 0), 0.12)

    return frame


def ansi_render(img: Image.Image) -> str:
    cols, _rows = shutil.get_terminal_size((180, 60))
    px = img.load()
    w, h = img.size
    left = max(0, (cols - w) // 2)
    lines: list[str] = []
    for y in range(0, h, 2):
        line = [BLACK, " " * left]
        last_fg = last_bg = None
        for x in range(w):
            top = px[x, y]
            bottom = px[x, min(y + 1, h - 1)]
            if max(top) < 5 and max(bottom) < 5:
                line.append(BLACK + " ")
                last_fg = last_bg = None
                continue
            if top != last_fg:
                line.append(fg(top))
                last_fg = top
            if bottom != last_bg:
                line.append(bg(bottom))
                last_bg = bottom
            line.append("▀")
        line.append(RESET + BLACK + "\033[K")
        lines.append("".join(line))
    return "\n".join(lines)


def main() -> int:
    source = Image.open(SKIN).convert("RGB")
    base = fit(source)
    last_size = shutil.get_terminal_size()
    start = time.perf_counter()
    next_frame = start
    sys.stdout.write(ALT_ON + CLEAR + HIDE + BLACK)
    sys.stdout.flush()
    try:
        while running:
            now = time.perf_counter()
            size = shutil.get_terminal_size()
            if size != last_size:
                last_size = size
                base = fit(source)
                sys.stdout.write(CLEAR)

            state = read_state()
            name = str(state.get("state", "IDLE")).upper()
            detail = str(state.get("detail", ""))[:120]
            provider = str(state.get("provider", "unknown"))
            model = str(state.get("model", "unknown"))
            frame = animate(base, name, now - start)
            header = (
                "\033[38;2;0;240;255m24K // GPT-DOUG MAX // LIVE SKIN\033[0m"
                f"  \033[38;2;80;255;120m[{name}]\033[0m\n"
                f"\033[38;2;255;70;220m{provider} // {model}\033[0m  {detail}\033[K\n"
            )
            footer = (
                "\n\033[38;2;255;220;70mSTATE BUS\033[0m  "
                f"{STATE_FILE}  target={FPS:.0f}fps  CTRL+C=visual-off\033[K"
            )
            sys.stdout.write(HOME + BLACK + header + ansi_render(frame) + footer)
            sys.stdout.flush()

            next_frame += FRAME_TIME
            remaining = next_frame - time.perf_counter()
            if remaining > 0:
                time.sleep(remaining)
            else:
                next_frame = time.perf_counter()
        return 0
    finally:
        sys.stdout.write(RESET + SHOW + ALT_OFF)
        sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
