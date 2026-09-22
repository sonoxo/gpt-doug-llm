#!/usr/bin/env python3
"""GPT-Doug Black House V3 // terminal-native living avatar.

Goals:
- Keep the canonical RGB portrait recognizable and bright.
- Use actual terminal 0/1 characters for a Matrix-style binary rain background.
- Animate mannerisms (breathing, blink, brows, eyes, mouth, swarm, power).
- Follow GPT-Doug MAX state automatically, with manual mode overrides.
- Stay practical at 15 FPS using quantized cells + differential painting.
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
    from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
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
        "GPT-Doug portrait missing. Set GPT_DOUG_SKIN or save "
        "~/Pictures/gptdoug-alive-v2.png"
    )

FPS = max(5.0, min(float(os.environ.get("GPT_DOUG_VISUAL_FPS", "15")), 30.0))
FRAME_TIME = 1.0 / FPS
MAX_COLS = max(72, min(int(os.environ.get("GPT_DOUG_VISUAL_COLS", "120")), 180))
COLOR_STEP = max(4, min(int(os.environ.get("GPT_DOUG_COLOR_STEP", "8")), 32))
MATRIX_ENABLED = os.environ.get("GPT_DOUG_MATRIX", "1").lower() not in {"0", "off", "false", "no"}
MATRIX_RATE = max(2.0, min(float(os.environ.get("GPT_DOUG_MATRIX_FPS", "6")), FPS))

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
MAGENTA = "\033[38;2;255;50;220m"
GREEN = "\033[38;2;60;255;140m"
YELLOW = "\033[38;2;255;220;60m"
WHITE = "\033[38;2;235;245;255m"

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


def q(rgb):
    step = COLOR_STEP
    return tuple(min(255, (int(v) // step) * step) for v in rgb)


def read_bus() -> dict:
    try:
        value = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        if isinstance(value, dict):
            return value
    except Exception:
        pass
    return {
        "state": "IDLE",
        "detail": "Black House online",
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
    known = {"auto", "idle", "listen", "think", "talk", "act", "eureka", "swarm", "power", "error"}
    if manual not in known:
        manual = "auto"
    if manual != "auto":
        return manual

    state = str(bus.get("state", "IDLE")).strip().lower()
    mapping = {
        "idle": "idle",
        "ready": "idle",
        "listen": "listen",
        "think": "think",
        "talk": "talk",
        "act": "act",
        "power": "power",
        "error": "error",
        "offline": "idle",
    }
    return mapping.get(state, "idle")


def fit_source(source: Image.Image):
    cols, lines = shutil.get_terminal_size((160, 54))
    width = min(MAX_COLS, max(72, cols - 2))
    # Two source pixels per terminal row. Leave four UI rows.
    hpx_max = max(32, (max(18, lines - 4)) * 2)
    scale = min(width / source.width, hpx_max / source.height)
    w = max(40, int(source.width * scale))
    h = max(32, int(source.height * scale))
    if h % 2:
        h -= 1
    return source.resize((w, h), Image.Resampling.LANCZOS)


def soft_subject_mask(img: Image.Image) -> Image.Image:
    """Keep the portrait + its RGB particles; let true black become binary rain."""
    gray = img.convert("L")
    # Threshold low enough to preserve the luminous RGB particle field.
    mask = gray.point(lambda p: 255 if p >= 12 else 0)
    return mask.filter(ImageFilter.GaussianBlur(0.55))


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

    out = img.copy()
    mask = Image.new("L", (nw, nh), 0)
    d = ImageDraw.Draw(mask)
    d.rounded_rectangle((0, 0, nw - 1, nh - 1), radius=max(2, min(nw, nh) // 7), fill=230)
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, min(nw, nh) // 24)))
    out.paste(crop, (px, py), mask)
    return out


def blink_amount(t: float) -> float:
    phase = t % 4.8
    if phase < 0.115:
        return math.sin(math.pi * phase / 0.115)
    if 0.205 <= phase < 0.29:
        return 0.58 * math.sin(math.pi * (phase - 0.205) / 0.085)
    return 0.0


class Motion:
    names = ("listen", "think", "talk", "act", "eureka", "swarm", "power", "error")

    def __init__(self):
        self.level = {name: 0.0 for name in self.names}

    def update(self, mode: str, dt: float):
        # Smooth mode transitions even at 15 FPS.
        a = 1.0 - math.exp(-7.5 * max(0.001, min(dt, 0.08)))
        for name in self.names:
            target = 1.0 if name == mode else 0.0
            self.level[name] += (target - self.level[name]) * a
        return self.level


class MatrixRain:
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
        for x in range(width):
            self.columns.append(
                {
                    "head": self.rng.uniform(-height, height),
                    "speed": self.rng.uniform(0.55, 1.5),
                    "length": self.rng.randint(5, 16),
                    "phase": self.rng.randint(0, 9999),
                }
            )

    def step(self):
        self.tick += 1
        for col in self.columns:
            col["head"] += col["speed"]
            if col["head"] - col["length"] > self.height:
                col["head"] = self.rng.uniform(-self.height * 0.7, -2.0)
                col["speed"] = self.rng.uniform(0.55, 1.5)
                col["length"] = self.rng.randint(5, 16)

    def cell(self, x: int, y: int, intensity: float = 1.0):
        if not MATRIX_ENABLED or not self.columns:
            return ("txt", " ", (0, 0, 0))
        col = self.columns[x]
        head = int(col["head"])
        d = head - y
        if d < 0 or d > col["length"]:
            return ("txt", " ", (0, 0, 0))

        bit = "1" if ((x * 17 + y * 31 + self.tick + col["phase"]) & 1) else "0"
        if d == 0:
            color = (190, 255, 220)
        elif d <= 2:
            color = (40, int(255 * intensity), 130)
        else:
            fade = max(0.16, 1.0 - d / (col["length"] + 1))
            color = (0, int(210 * fade * intensity), int(90 * fade * intensity))
        return ("txt", bit, q(color))


class Swarm:
    def __init__(self):
        self.rng = random.Random(42)
        self.particles = []

    def resize(self, w: int, h: int):
        desired = max(40, min(150, w))
        if len(self.particles) == desired:
            return
        self.particles = []
        colors = [
            (0, 230, 255),
            (255, 35, 90),
            (70, 255, 150),
            (255, 255, 255),
        ]
        for _ in range(desired):
            self.particles.append(
                [
                    self.rng.uniform(0, w),
                    self.rng.uniform(0, h),
                    self.rng.uniform(-0.18, 0.18),
                    self.rng.uniform(-0.22, 0.10),
                    self.rng.choice(colors),
                    self.rng.uniform(0.4, 1.0),
                ]
            )

    def draw(self, img: Image.Image, amount: float):
        if amount <= 0.01:
            return img
        w, h = img.size
        self.resize(w, h)
        out = img.copy()
        d = ImageDraw.Draw(out)
        cx, cy = w / 2, h / 2
        for p in self.particles:
            x, y, vx, vy, color, phase = p
            # Orbit slightly around the avatar, not random teleporting.
            dx, dy = x - cx, y - cy
            x += vx + (-dy) * 0.0008 * amount
            y += vy + dx * 0.0008 * amount
            if x < 0:
                x += w
            elif x >= w:
                x -= w
            if y < 0:
                y += h
            elif y >= h:
                y -= h
            p[0], p[1] = x, y
            size = 1 if phase < 0.75 else 2
            c = tuple(min(255, int(v * (0.65 + 0.35 * amount))) for v in color)
            d.rectangle((int(x), int(y), int(x) + size, int(y) + size), fill=c)
        return out


def avatar_frame(base: Image.Image, levels: dict, mode: str, t: float, swarm: Swarm):
    frame = base.copy()
    w, h = frame.size

    head = (int(w * 0.27), int(h * 0.06), int(w * 0.73), int(h * 0.66))
    shoulders = (int(w * 0.13), int(h * 0.61), int(w * 0.87), int(h * 0.97))
    left_eye = (int(w * 0.35), int(h * 0.31), int(w * 0.47), int(h * 0.43))
    right_eye = (int(w * 0.53), int(h * 0.31), int(w * 0.65), int(h * 0.43))
    left_brow = (int(w * 0.32), int(h * 0.25), int(w * 0.48), int(h * 0.34))
    right_brow = (int(w * 0.52), int(h * 0.25), int(w * 0.68), int(h * 0.34))
    mouth = (int(w * 0.39), int(h * 0.52), int(w * 0.61), int(h * 0.65))

    listen = levels["listen"]
    think = levels["think"]
    talk = levels["talk"]
    act = levels["act"]
    eureka = levels["eureka"]
    swarm_level = levels["swarm"]
    power = levels["power"]
    error = levels["error"]

    # Preserve the full-picture brightness instead of dimming inactive states.
    frame = ImageEnhance.Brightness(frame).enhance(1.18 + 0.08 * power + 0.05 * eureka)
    frame = ImageEnhance.Color(frame).enhance(1.20 + 0.12 * power)
    frame = ImageEnhance.Contrast(frame).enhance(1.06)

    breath = math.sin(t * 1.15)
    frame = region_warp(
        frame,
        shoulders,
        sy=1.0 + breath * 0.007,
        dy=breath * 0.55,
        brightness=1.0 + max(0.0, breath) * 0.025,
    )

    # Gentle living head motion, stronger while listening/thinking.
    frame = region_warp(
        frame,
        head,
        dx=math.sin(t * 0.58) * (0.35 + 0.45 * listen + 0.18 * think),
        dy=math.sin(t * 0.82) * 0.30,
    )

    blink = blink_amount(t)
    eye_sy = max(0.15, 1.0 - blink * 0.80 - talk * 0.035)
    eye_light = 1.12 + 0.24 * listen + 0.16 * think + 0.14 * talk + 0.55 * power + 0.25 * eureka
    frame = region_warp(frame, left_eye, sy=eye_sy, brightness=eye_light)
    frame = region_warp(frame, right_eye, sy=eye_sy, brightness=eye_light)

    brow = think * 1.7 + talk * 0.65 + act * 0.8 + power * 2.5 + eureka * 1.4
    frame = region_warp(frame, left_brow, dy=-brow, brightness=1.0 + brow * 0.03)
    frame = region_warp(frame, right_brow, dy=-brow, brightness=1.0 + brow * 0.03)

    speech = (
        0.52
        + 0.24 * math.sin(t * 10.4)
        + 0.13 * math.sin(t * 16.7 + 0.65)
        + 0.07 * math.sin(t * 23.0 + 1.6)
    )
    mouth_open = max(0.04, min(0.95, speech)) * talk
    if mouth_open > 0.015:
        frame = region_warp(
            frame,
            mouth,
            sx=1.0 - 0.035 * mouth_open,
            sy=1.0 + 0.28 * mouth_open,
            dy=0.75 * mouth_open,
            brightness=1.06,
        )

    # Colored aura remains subtle so the portrait still looks like the original.
    if power + eureka > 0.02:
        aura = frame.filter(ImageFilter.GaussianBlur(2.2))
        frame = Image.blend(frame, aura, min(0.10, 0.035 + 0.05 * (power + eureka)))

    if error > 0.02:
        red = Image.new("RGB", frame.size, (255, 0, 30))
        frame = Image.blend(frame, red, min(0.11, error * 0.11))

    particle_amount = 0.16 + 0.32 * act + 0.68 * swarm_level + 0.75 * power + 0.45 * eureka
    frame = swarm.draw(frame, particle_amount)
    return frame


def subject_cells(img: Image.Image):
    mask = soft_subject_mask(img)
    p = img.load()
    m = mask.load()
    w, h = img.size
    rows = []
    for y in range(0, h, 2):
        row = []
        y2 = min(y + 1, h - 1)
        for x in range(w):
            if max(m[x, y], m[x, y2]) < 24:
                row.append(None)
            else:
                row.append(("img", q(p[x, y]), q(p[x, y2])))
        rows.append(row)
    return rows


def compose_grid(img: Image.Image, matrix: MatrixRain, mode: str):
    subject = subject_cells(img)
    if not subject:
        return subject
    h = len(subject)
    w = len(subject[0])
    matrix.resize(w, h)

    matrix_intensity = 1.0
    if mode in {"think", "act"}:
        matrix_intensity = 1.12
    elif mode in {"swarm", "power", "eureka"}:
        matrix_intensity = 1.30
    elif mode == "error":
        matrix_intensity = 0.72

    grid = []
    for y, row in enumerate(subject):
        out = []
        for x, cell in enumerate(row):
            out.append(cell if cell is not None else matrix.cell(x, y, matrix_intensity))
        grid.append(out)
    return grid


def encode_run(cells):
    out = []
    last_fg = None
    last_bg = None
    for cell in cells:
        kind = cell[0]
        if kind == "img":
            top, bottom = cell[1], cell[2]
            if top != last_fg:
                out.append(fg(top))
                last_fg = top
            if bottom != last_bg:
                out.append(bg(bottom))
                last_bg = bottom
            out.append("▀")
        else:
            ch, color = cell[1], cell[2]
            if last_bg != (0, 0, 0):
                out.append(BLACK_BG)
                last_bg = (0, 0, 0)
            if color != last_fg:
                out.append(fg(color))
                last_fg = color
            out.append(ch)
    return "".join(out)


def render_full(grid, left: int, header, footer):
    out = [HOME, BLACK_BG]
    for idx, line in enumerate(header, start=1):
        out += [cursor(idx, 1), line, RESET, BLACK_BG, CLEAR_EOL]
    image_row = len(header) + 1
    for y, row in enumerate(grid):
        out += [
            cursor(image_row + y, 1),
            BLACK_BG,
            " " * left,
            encode_run(row),
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


def render_diff(previous, current, left: int, image_row: int):
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
                encode_run(new[start:x]),
                RESET,
                BLACK_BG,
            ]
    return "".join(out)


def main():
    source = Image.open(SKIN).convert("RGB")
    base = fit_source(source)
    size = shutil.get_terminal_size()
    motion = Motion()
    matrix = MatrixRain()
    swarm = Swarm()

    previous = None
    previous_left = None
    previous_header = None
    previous_footer = None

    started = time.perf_counter()
    last = started
    next_frame = started
    last_matrix = started

    sys.stdout.write(ALT_ON + CLEAR + HIDE + WRAP_OFF + BLACK_BG)
    sys.stdout.flush()

    try:
        while running:
            now = time.perf_counter()
            dt = max(0.001, min(now - last, 0.08))
            last = now

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
                matrix.step()
                last_matrix = now

            frame = avatar_frame(base, levels, mode, now - started, swarm)
            grid = compose_grid(frame, matrix, mode)

            cols, _lines = size
            width = len(grid[0]) if grid else 0
            left = max(0, (cols - width) // 2)

            provider = str(bus.get("provider", "none"))
            model = str(bus.get("model", "unknown"))
            detail = str(bus.get("detail", ""))[:88]

            header = [
                CYAN + "24K // GPT-DOUG BLACK HOUSE V3 // LIVING TERMINAL" + RESET
                + "  " + GREEN + f"[{mode.upper()}]" + RESET,
                MAGENTA + f"{provider} // {model}" + RESET
                + "  " + WHITE + detail + RESET,
            ]
            footer = (
                YELLOW + "BLACK HOUSE" + RESET
                + f"  {int(FPS)}fps  {width}cols  "
                + GREEN
                + "doug-auto idle listen think talk eureka swarm power say"
                + RESET
            )

            image_row = len(header) + 1
            must_full = previous is None or previous_left != left or resized

            output = []
            if must_full:
                output.append(render_full(grid, left, header, footer))
            else:
                if previous_header != header:
                    for idx, line in enumerate(header, start=1):
                        output += [cursor(idx, 1), line, RESET, BLACK_BG, CLEAR_EOL]
                output.append(render_diff(previous, grid, left, image_row))
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
                # Never accumulate a render backlog.
                next_frame = time.perf_counter()
    finally:
        sys.stdout.write(RESET + WRAP_ON + SHOW + ALT_OFF)
        sys.stdout.flush()


if __name__ == "__main__":
    main()
