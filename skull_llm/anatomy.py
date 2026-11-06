"""Deterministic anatomy-inspired ASCII skull renderer for SKULL-LLM.

A stylized mathematical bone surface; not a medical CT, anatomical scan or
scientific reconstruction. For photo-based fidelity use a licensed local photo
with render_photo_ascii (optional Pillow). No network or remote upload.
"""
from __future__ import annotations

import math
from pathlib import Path

RAMP = " .:-=+*#%@"
PHOTO_RAMP = " .,:;irsXA253hMHGS#9B&@"


def render_anatomical_skull(
    width: int = 72,
    height: int = 36,
    *,
    light: float = -0.6,
) -> str:
    """Shade the cranium, orbit rims, nasal aperture, zygomas and mandible."""
    if not 32 <= width <= 110 or not 18 <= height <= 60:
        raise ValueError("skull dimensions must be 32..110 columns and 18..60 rows")
    if not -1.0 <= light <= 1.0:
        raise ValueError("light direction must be -1.0..1.0")
    picture: list[str] = []
    for row in range(height):
        line: list[str] = []
        for col in range(width):
            x = (col - (width - 1) / 2) / (width * 0.30)
            y = (row - (height - 1) / 2) / (height * 0.53)
            dome = 1 - (x / 0.90) ** 2 - ((y + 0.22) / 0.86) ** 2
            cheeks = 1 - (x / 0.83) ** 4 - ((y - 0.27) / 0.39) ** 4
            maxilla = 1 - (x / 0.51) ** 6 - ((y - 0.49) / 0.28) ** 6
            mandible = 1 - (x / 0.56) ** 4 - ((y - 0.64) / 0.30) ** 4
            if y < 0.12:
                inside = dome > 0
            elif y < 0.39:
                inside = dome > 0 or cheeks > 0
            elif y < 0.56:
                inside = maxilla > 0 or cheeks > 0
            else:
                inside = mandible > 0
            if not inside:
                line.append(" ")
                continue
            depth = max(
                0.0,
                dome if y < 0.22 else cheeks if y < 0.45 else
                maxilla if y < 0.56 else mandible,
            )
            surface = math.sqrt(depth)
            luminance = 0.53 + 0.30 * surface + 0.10 * (x * light - 0.6 * y)
            luminance += (
                0.018 * math.sin(38 * x + 11 * y) * math.sin(29 * y - 8 * x)
            )
            if y < -0.42 and abs(x - 0.065 * math.sin(12 * y)) < 0.024:
                luminance -= 0.17

            # Recessed orbital sockets bounded by illuminated bony rims.
            eye_x = abs(x) - 0.355
            orbit = (eye_x / 0.264) ** 2 + (
                (y + 0.08 + 0.018 * math.sin(10 * x)) / 0.19
            ) ** 2
            if orbit < 1:
                luminance = 0.025 + 0.11 * (1 - orbit)
                if 0.80 < orbit < 1 and y > -0.10:
                    luminance = 0.25
            elif 1 <= orbit < 1.40 and -0.33 < y < 0.11 and 0.1 < abs(x) < 0.75:
                luminance = max(luminance, 0.91 - 0.28 * (orbit - 1))
            if -0.34 < y < -0.235 and 0.14 < abs(x) < 0.65:
                luminance = min(1, luminance + 0.10)

            # Tapered nasal aperture with high-contrast bridge.
            if 0.12 < y < 0.48:
                taper = 0.065 + (y - 0.12) * 0.33
                if abs(x) < taper and y > 0.18:
                    luminance = 0.025
                elif abs(x) < taper + 0.038:
                    luminance = min(1, luminance + 0.19)
                elif abs(x) < 0.04 and y < 0.22:
                    luminance = 0.94

            # Raised zygomatic arches and receding temporal surfaces.
            if 0.13 < y < 0.43:
                arch = abs(x) - (0.585 - 0.13 * (y - 0.20))
                if abs(arch) < 0.055:
                    luminance = min(0.98, luminance + 0.20)
            if 0.24 < y < 0.56 and 0.59 < abs(x) < 0.80:
                luminance *= 0.52
            if 0.42 < y < 0.52 and 0.18 < abs(x) < 0.30:
                luminance = max(luminance, 0.80)

            # Maxillary tooth crowns, separations and oral shadow.
            if 0.51 < y < 0.77 and abs(x) < 0.41:
                arc = (abs(x) / 0.42) ** 2
                gap = abs((x + 0.40) / 0.105 - round((x + 0.40) / 0.105))
                luminance = 0.11 if gap < 0.075 else 0.89 - 0.22 * arc
                if 0.610 < y < 0.650:
                    luminance *= 0.14
            if 0.73 < y < 0.86 and abs(x) < 0.30:
                luminance = min(0.98, luminance + 0.12)
            if 0.68 < y < 0.83 and 0.38 < abs(x) < 0.51:
                luminance = 0.24
            if surface < 0.26:
                luminance *= 0.58
            value = max(0.0, min(1.0, luminance))
            line.append(RAMP[min(len(RAMP) - 1, int(value * (len(RAMP) - 1)))])
        picture.append("".join(line).rstrip())
    return "\n".join(picture)


def render_photo_ascii(path: str, *, width: int = 72, invert: bool = False) -> str:
    """Convert a user-provided local image to detailed ASCII, with Pillow.

    No image content is transmitted. Load only images whose origin you trust.
    """
    if not 32 <= width <= 110:
        raise ValueError("photo width must be 32..110 columns")
    try:
        from PIL import Image, ImageOps, ImageEnhance
    except ImportError as exc:
        raise RuntimeError(
            "Photo mode requires optional Pillow: python3 -m pip install Pillow"
        ) from exc
    filename = Path(path).expanduser()
    if not filename.is_file():
        raise ValueError("image file not found")
    if filename.stat().st_size > 20 * 1024 * 1024:
        raise ValueError("image exceeds 20 MiB maximum")
    with Image.open(filename) as source:
        source.verify()
    with Image.open(filename) as source:
        if source.width * source.height > 18_000_000:
            raise ValueError("image resolution exceeds 18 million pixels")
        image = ImageOps.grayscale(source)
        image = ImageOps.autocontrast(image, cutoff=1)
        image = ImageEnhance.Contrast(image).enhance(1.35)
        height = max(8, round(image.height / image.width * width * 0.52))
        if height > 150:
            raise ValueError("image aspect ratio too tall")
        image = image.resize((width, height))
        pixels = list(image.getdata())
    out = []
    for y in range(height):
        line = ""
        for shade in pixels[y * width : (y + 1) * width]:
            value = (255 - shade) if invert else shade
            line += PHOTO_RAMP[min(len(PHOTO_RAMP) - 1, int(value * len(PHOTO_RAMP) / 256))]
        out.append(line.rstrip())
    return "\n".join(out)
