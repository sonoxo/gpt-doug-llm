#!/usr/bin/env python3
"""GPT-Doug Supreme Visual V4.

Terminal-native cinematic avatar renderer.

Design goals:
- Preserve the canonical RGB portrait instead of replacing it with generated FX.
- Keep the synthetic particle swarm disabled.
- Keep binary rain strictly behind the subject matte.
- Add living mannerisms: breath, blink, gaze, brows, jaw/mouth, thought focus.
- Interpolate states so 15 FPS looks smooth instead of stepped.
- Differential-paint terminal cells to avoid flooding Terminal.app.
"""
from __future__ import annotations

import json
import math
import os
import random
import shutil
import signal
import sys
import time
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageOps
except ImportError as exc:
    raise SystemExit("Pillow is required: python3 -m pip install pillow") from exc

STATE_FILE = Path.home() / ".gpt-doug" / "max-shell-state.json"
MODE_FILE = Path.home() / ".gpt-doug" / "blackhouse-mode"

SKIN_CANDIDATES = [
    Path(os.environ["GPT_DOUG_SKIN"]).expanduser() if os.environ.get("GPT_DOUG_SKIN") else None,
    Path.home() / "Pictures" / "gptdoug-alive-v2.png",
    Path.home() / "Pictures" / "gptdoug-alive.png",
]
SKIN = next((p for p in SKIN_CANDIDATES if p and p.exists()), None)
if SKIN is None:
    raise SystemExit(
        "GPT-Doug skin missing. Set GPT_DOUG_SKIN or save "
        "~/Pictures/gptdoug-alive-v2.png"
    )

FPS = max(5.0, min(float(os.environ.get("GPT_DOUG_VISUAL_FPS", "15")), 30.0))
FRAME_TIME = 1.0 / FPS
MAX_COLS = max(80, min(int(os.environ.get("GPT_DOUG_VISUAL_COLS", "132")), 180))
COLOR_STEP = max(4, min(int(os.environ.get("GPT_DOUG_COLOR_STEP", "8")), 32))
MATRIX_ENABLED = os.environ.get("GPT_DOUG_MATRIX", "1").lower() not in {"0", "off", "false", "no"}
MATRIX_RATE = max(2.0, min(float(os.environ.get("GPT_DOUG_MATRIX_FPS", "6")), FPS))
BRIGHTNESS = max(0.8, min(float(os.environ.get("GPT_DOUG_BRIGHTNESS", "1.20")), 1.8))
SATURATION = max(0.8, min(float(os.environ.get("GPT_DOUG_SATURATION", "1.18")), 1.8))
SHARPNESS = max(0.8, min(float(os.environ.get("GPT_DOUG_SHARPNESS", "1.15")), 2.0))

RESET = "\033[0m"
HOME = "\033[H"
CLEAR = "\033[2J"
HIDE = "\033[?25l"
SHOW = "\033[?25h"
ALT_ON = "\033[?1049h"
ALT_OFF = "\033[?1049l"
WRAP_OFF = "\033[?7l"
WRAP_ON = "\033[?7h"
CLEAR_EOL = "\033[K"
BLACK_BG = "\033[48;2;0;0;0m"

CYAN = "\033[38;2;0;240;255m"
MAGENTA = "\033[38;2;255;55;220m"
GREEN = "\033[38;2;60;255;145m"
YELLOW = "\033[38;2;255;220;70m"
WHITE = "\033[38;2;235;245;255m"
DIM = "\033[38;2;115;125;135m"

running = True


def stop(*_args):
    global running
    running = False


signal.signal(signal.SIGINT, stop)
signal.signal(signal.SIGTERM, stop)


def cursor(row: int, col: int = 1) -> str:
    return f"\033[{row};{col}H"


def fg(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"\033[38;2;{r};{g};{b}m"


def bg(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"\033[48;2;{r};{g};{b}m"


def quantize(rgb):
    step = COLOR_STEP
    return tuple(min(255, (int(v) // step) * step) for v in rgb)


def read_bus() -> dict:
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {
        "state": "IDLE",
        "detail": "GPT-Doug visual cortex online",
        "provider": "none",
        "model": "unknown",
    }


def read_manual_mode() -> str:
    try:
        mode = MODE_FILE.read_text(encoding="utf-8").strip().lower()
        return mode if mode else "auto"
    except Exception:
        return "auto"


def resolve_mode(bus: dict) -> str:
    manual = read_manual_mode()
    known = {
        "auto", "idle", "listen", "think", "talk", "act",
        "eureka", "power", "error",
    }
    if manual not in known:
        manual = "auto"
    if manual != "auto":
        return manual

    state = str(bus.get("state", "IDLE")).strip().lower()
    mapping = {
        "ready": "idle",
        "idle": "idle",
        "listen": "listen",
        "think": "think",
        "talk": "talk",
        "act": "act",
        "power": "power",
        "error": "error",
        "offline": "idle",
    }
    return mapping.get(state, "idle")


def fit_source(source: Image.Image) -> Image.Image:
    cols, lines = shutil.get_terminal_size((180, 56))
    target_w = min(MAX_COLS, max(80, cols - 4))
    target_h = max(36, (max(20, lines - 4)) * 2)

    scale = min(target_w / source.width, target_h / source.height)
    w = max(48, int(source.width * scale))
    h = max(36, int(source.height * scale))
    if h % 2:
        h -= 1

    out = source.resize((w, h), Image.Resampling.LANCZOS)
    out = ImageEnhance.Brightness(out).enhance(BRIGHTNESS)
    out = ImageEnhance.Color(out).enhance(SATURATION)
    out = ImageEnhance.Sharpness(out).enhance(SHARPNESS)
    return out


def matte_from_source(img: Image.Image) -> Image.Image:
    """Mask true background black while preserving original RGB fragments."""
    gray = ImageOps.grayscale(img)
    # Preserve dim facial pixels and original floating RGB fragments.
    matte = gray.point(lambda p: 255 if p >= 8 else 0)
    matte = matte.filter(ImageFilter.GaussianBlur(0.42))
    return matte


def region_warp(
    img: Image.Image,
    box,
    *,
    sx: float = 1.0,
    sy: float = 1.0,
    dx: float = 0.0,
    dy: float = 0.0,
    brightness: float = 1.0,
) -> Image.Image:
    x1, y1, x2, y2 = box
    crop = img.crop(box)

    if brightness != 1.0:
        crop = ImageEnhance.Brightness(crop).enhance(brightness)

    cw, ch = max(1, x2 - x1), max(1, y2 - y1)
    nw = max(2, int(cw * sx))
    nh = max(2, int(ch * sy))

    crop = crop.resize((nw, nh), Image.Resampling.BICUBIC)

    px = int((x1 + x2 - nw) / 2 + dx)
    py = int((y1 + y2 - nh) / 2 + dy)

    mask = Image.new("L", (nw, nh), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle(
        (0, 0, nw - 1, nh - 1),
        radius=max(2, min(nw, nh) // 6),
        fill=235,
    )
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, min(nw, nh) // 26)))

    out = img.copy()
    out.paste(crop, (px, py), mask)
    return out


def blink_curve(t: float) -> float:
    phase = t % 4.65
    if phase < 0.105:
        return math.sin(math.pi * phase / 0.105)
    if 0.205 <= phase < 0.285:
        return 0.58 * math.sin(math.pi * (phase - 0.205) / 0.080)
    return 0.0


class Motion:
    names = ("listen", "think", "talk", "act", "eureka", "power", "error")

    def __init__(self):
        self.level = {name: 0.0 for name in self.names}

    def update(self, mode: str, dt: float):
        alpha = 1.0 - math.exp(-7.2 * max(0.001, min(dt, 0.09)))
        for name in self.names:
            target = 1.0 if name == mode else 0.0
            self.level[name] += (target - self.level[name]) * alpha
        return self.level


class BinaryRain:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.rng = random.Random(24024)
        self.columns = []
        self.tick = 0

    def resize(self, width: int, height: int):
        if width == self.width and height == self.height:
            return
        self.width = width
        self.height = height
        self.columns = []
        for _x in range(width):
            self.columns.append(
                {
                    "head": self.rng.uniform(-height, height),
                    "speed": self.rng.uniform(0.45, 1.25),
                    "length": self.rng.randint(4, 13),
                    "seed": self.rng.randint(0, 100000),
                }
            )

    def step(self):
        self.tick += 1
        for col in self.columns:
            col["head"] += col["speed"]
            if col["head"] - col["length"] > self.height:
                col["head"] = self.rng.uniform(-self.height * 0.65, -2.0)
                col["speed"] = self.rng.uniform(0.45, 1.25)
                col["length"] = self.rng.randint(4, 13)

    def cell(self, x: int, y: int, energy: float):
        if not MATRIX_ENABLED:
            return ("txt", " ", (0, 0, 0))

        col = self.columns[x]
        head = int(col["head"])
        distance = head - y

        if distance < 0 or distance > col["length"]:
            return ("txt", " ", (0, 0, 0))

        bit = "1" if ((x * 13 + y * 29 + self.tick + col["seed"]) & 1) else "0"

        if distance == 0:
            color = (190, 255, 220)
        elif distance <= 2:
            color = (20, int(min(255, 240 * energy)), 110)
        else:
            fade = max(0.14, 1.0 - distance / (col["length"] + 1))
            color = (
                0,
                int(min(255, 185 * fade * energy)),
                int(min(255, 72 * fade * energy)),
            )

        return ("txt", bit, quantize(color))


def apply_cinematic_mannerisms(base: Image.Image, levels: dict, mode: str, t: float):
    frame = base.copy()
    w, h = frame.size

    # Tuned for the canonical centered GPT-Doug portrait.
    head = (int(w * 0.27), int(h * 0.055), int(w * 0.73), int(h * 0.67))
    shoulders = (int(w * 0.13), int(h * 0.60), int(w * 0.87), int(h * 0.97))
    left_eye = (int(w * 0.35), int(h * 0.30), int(w * 0.47), int(h * 0.43))
    right_eye = (int(w * 0.53), int(h * 0.30), int(w * 0.65), int(h * 0.43))
    left_brow = (int(w * 0.32), int(h * 0.25), int(w * 0.48), int(h * 0.34))
    right_brow = (int(w * 0.52), int(h * 0.25), int(w * 0.68), int(h * 0.34))
    mouth = (int(w * 0.39), int(h * 0.51), int(w * 0.61), int(h * 0.65))

    listen = levels["listen"]
    think = levels["think"]
    talk = levels["talk"]
    act = levels["act"]
    eureka = levels["eureka"]
    power = levels["power"]
    error = levels["error"]

    # Chest/shoulder breath.
    breath = math.sin(t * 1.10)
    frame = region_warp(
        frame,
        shoulders,
        sy=1.0 + breath * 0.008,
        dy=breath * 0.65,
        brightness=1.0 + max(0.0, breath) * 0.018,
    )

    # Slow living head sway and state-specific focus.
    head_dx = (
        math.sin(t * 0.55) * 0.42
        + listen * math.sin(t * 0.95) * 0.55
        + think * math.sin(t * 0.65) * 0.30
    )
    head_dy = math.sin(t * 0.79) * 0.28
    frame = region_warp(frame, head, dx=head_dx, dy=head_dy)

    # Blink + gaze emphasis.
    blink = blink_curve(t)
    eye_sy = max(0.16, 1.0 - 0.82 * blink - 0.035 * talk)

    gaze = think * math.sin(t * 1.4) * 0.45
    left_eye_light = 1.08 + 0.25 * listen + 0.12 * think + 0.12 * talk + 0.48 * power + 0.32 * eureka
    right_eye_light = 1.08 + 0.25 * listen + 0.12 * think + 0.12 * talk + 0.48 * power + 0.32 * eureka

    frame = region_warp(
        frame,
        left_eye,
        sy=eye_sy,
        dx=gaze,
        brightness=left_eye_light,
    )
    frame = region_warp(
        frame,
        right_eye,
        sy=eye_sy,
        dx=gaze,
        brightness=right_eye_light,
    )

    # Brows carry thought / intention.
    brow_lift = think * 1.7 + talk * 0.55 + act * 0.75 + power * 2.2 + eureka * 1.35
    frame = region_warp(frame, left_brow, dy=-brow_lift, brightness=1.0 + brow_lift * 0.025)
    frame = region_warp(frame, right_brow, dy=-brow_lift, brightness=1.0 + brow_lift * 0.025)

    # Multi-frequency pseudo-visemes for smoother speech.
    voice_wave = (
        0.50
        + 0.23 * math.sin(t * 10.3)
        + 0.13 * math.sin(t * 16.9 + 0.8)
        + 0.08 * math.sin(t * 23.8 + 1.6)
    )
    mouth_open = max(0.04, min(0.95, voice_wave)) * talk

    if mouth_open > 0.012:
        frame = region_warp(
            frame,
            mouth,
            sx=1.0 - 0.040 * mouth_open,
            sy=1.0 + 0.30 * mouth_open,
            dy=0.75 * mouth_open,
            brightness=1.04 + 0.04 * mouth_open,
        )

    # ACT adds a tiny jaw set instead of a noisy whole-frame effect.
    if act > 0.02:
        frame = region_warp(
            frame,
            mouth,
            sy=1.0 - 0.028 * act,
            dy=0.35 * act,
            brightness=1.03,
        )

    # State energy remains subject-local.
    if power + eureka > 0.02:
        pulse = abs(math.sin(t * 6.2))
        frame = ImageEnhance.Brightness(frame).enhance(
            1.0 + (0.07 + 0.06 * pulse) * power + 0.07 * eureka
        )
        frame = ImageEnhance.Contrast(frame).enhance(
            1.0 + 0.08 * power + 0.05 * eureka
        )

        if power > 0.15:
            bloom = frame.filter(ImageFilter.GaussianBlur(1.8 + 0.8 * pulse))
            frame = Image.blend(frame, bloom, min(0.075, 0.025 + power * 0.045))

    if error > 0.02:
        red = Image.new("RGB", frame.size, (255, 0, 25))
        frame = Image.blend(frame, red, min(0.08, error * 0.08))

    return frame


def subject_grid(img: Image.Image):
    mask = matte_from_source(img)
    p = img.load()
    m = mask.load()
    w, h = img.size

    rows = []
    for y in range(0, h, 2):
        y2 = min(y + 1, h - 1)
        row = []
        for x in range(w):
            if max(m[x, y], m[x, y2]) < 22:
                row.append(None)
            else:
                row.append(("img", quantize(p[x, y]), quantize(p[x, y2])))
        rows.append(row)
    return rows


def compose(img: Image.Image, rain: BinaryRain, mode: str):
    subject = subject_grid(img)
    if not subject:
        return subject

    height = len(subject)
    width = len(subject[0])
    rain.resize(width, height)

    energy = {
        "idle": 0.90,
        "listen": 1.00,
        "think": 1.10,
        "talk": 1.00,
        "act": 1.12,
        "eureka": 1.22,
        "power": 1.30,
        "error": 0.70,
    }.get(mode, 0.90)

    grid = []
    for y, row in enumerate(subject):
        out = []
        for x, cell in enumerate(row):
            out.append(cell if cell is not None else rain.cell(x, y, energy))
        grid.append(out)
    return grid


def encode_cells(cells) -> str:
    out = []
    last_fg = None
    last_bg = None

    for cell in cells:
        if cell[0] == "img":
            top, bottom = cell[1], cell[2]
            if top != last_fg:
                out.append(fg(top))
                last_fg = top
            if bottom != last_bg:
                out.append(bg(bottom))
                last_bg = bottom
            out.append("▀")
        else:
            char, color = cell[1], cell[2]
            if last_bg != (0, 0, 0):
                out.append(BLACK_BG)
                last_bg = (0, 0, 0)
            if color != last_fg:
                out.append(fg(color))
                last_fg = color
            out.append(char)

    return "".join(out)


def full_render(grid, left: int, header: list[str], footer: str) -> str:
    out = [HOME, BLACK_BG]

    for idx, line in enumerate(header, start=1):
        out += [cursor(idx, 1), line, RESET, BLACK_BG, CLEAR_EOL]

    image_row = len(header) + 1

    for y, row in enumerate(grid):
        out += [
            cursor(image_row + y, 1),
            BLACK_BG,
            " " * left,
            encode_cells(row),
            RESET,
            BLACK_BG,
            CLEAR_EOL,
        ]

    out += [
        cursor(image_row + len(grid), 1),
        footer,
        RESET,
        BLACK_BG,
        CLEAR_EOL,
    ]

    return "".join(out)


def diff_render(previous, current, left: int, image_row: int) -> str:
    out = []

    for y, (old, new) in enumerate(zip(previous, current)):
        x = 0
        width = len(new)

        while x < width:
            if x < len(old) and old[x] == new[x]:
                x += 1
                continue

            start = x
            x += 1

            while x < width and (x >= len(old) or old[x] != new[x]):
                x += 1

            out += [
                cursor(image_row + y, left + start + 1),
                encode_cells(new[start:x]),
                RESET,
                BLACK_BG,
            ]

    return "".join(out)


def main() -> int:
    source = Image.open(SKIN).convert("RGB")
    base = fit_source(source)

    size = shutil.get_terminal_size()
    motion = Motion()
    rain = BinaryRain()

    previous = None
    previous_left = None
    previous_header = None
    previous_footer = None

    started = time.perf_counter()
    last_tick = started
    next_frame = started
    last_matrix = started

    sys.stdout.write(ALT_ON + CLEAR + HIDE + WRAP_OFF + BLACK_BG)
    sys.stdout.flush()

    try:
        while running:
            now = time.perf_counter()
            dt = max(0.001, min(now - last_tick, 0.09))
            last_tick = now

            new_size = shutil.get_terminal_size()
            resized = new_size != size

            if resized:
                size = new_size
                base = fit_source(source)
                previous = None
                previous_left = None
                sys.stdout.write(CLEAR)

            bus = read_bus()
            mode = resolve_mode(bus)
            levels = motion.update(mode, dt)

            if now - last_matrix >= (1.0 / MATRIX_RATE):
                rain.step()
                last_matrix = now

            frame = apply_cinematic_mannerisms(
                base,
                levels,
                mode,
                now - started,
            )

            grid = compose(frame, rain, mode)

            cols, _rows = size
            width = len(grid[0]) if grid else 0
            left = max(0, (cols - width) // 2)

            provider = str(bus.get("provider", "none"))
            model = str(bus.get("model", "unknown"))
            detail = str(bus.get("detail", ""))[:84]

            header = [
                CYAN + "24K // GPT-DOUG SUPREME VISUAL V4" + RESET
                + "  " + GREEN + f"[{mode.upper()}]" + RESET,
                MAGENTA + f"{provider} // {model}" + RESET
                + "  " + DIM + detail + RESET,
            ]

            footer = (
                YELLOW + "VISUAL CORTEX" + RESET
                + f"  {int(FPS)}fps  {width}cols  "
                + GREEN + "AUTO" + RESET
                + "  "
                + DIM + "blink breath gaze brow jaw binary-depth" + RESET
            )

            image_row = len(header) + 1
            must_full = previous is None or previous_left != left or resized

            output = []

            if must_full:
                output.append(full_render(grid, left, header, footer))
            else:
                if previous_header != header:
                    for idx, line in enumerate(header, start=1):
                        output += [cursor(idx, 1), line, RESET, BLACK_BG, CLEAR_EOL]

                output.append(diff_render(previous, grid, left, image_row))

                if previous_footer != footer:
                    output += [
                        cursor(image_row + len(grid), 1),
                        footer,
                        RESET,
                        BLACK_BG,
                        CLEAR_EOL,
                    ]

            if output:
                sys.stdout.write("".join(output))
                sys.stdout.flush()

            previous = grid
            previous_left = left
            previous_header = header
            previous_footer = footer

            next_frame += FRAME_TIME
            remaining = next_frame - time.perf_counter()

            if remaining > 0:
                time.sleep(remaining)
            else:
                next_frame = time.perf_counter()

        return 0
    finally:
        sys.stdout.write(RESET + WRAP_ON + SHOW + ALT_OFF)
        sys.stdout.flush()


if __name__ == "__main__":
    raise SystemExit(main())
