#!/usr/bin/env python3
"""SKULL-LLM // Photo-grade terminal ASCII converter (100% local).

Use a photographic skull reference for real anatomy. Text detail follows
image brightness and bone boundaries; no anatomically invented outline.

Requires: python3 -m pip install Pillow
Example: python3 skull_ascii_ultra.py ~/Pictures/skull.png --width 112 --color amber
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
from typing import Sequence
from urllib.request import Request, urlopen

try:
    from PIL import Image, ImageChops, ImageEnhance, ImageFilter, ImageOps, ImageStat
except ImportError:
    print("Pillow is required: python3 -m pip install Pillow", file=sys.stderr)
    raise SystemExit(2)

# Dark -> light. These ASCII symbols were arranged by approximate optical ink coverage.
DENSE = " .`'^\",:;Il!i><~+_-?][}{1)(|\\/tfjrxnuvczXYUJCLQ0OZmwqpdbkhao*#MW&8%B@$"
NORMAL = " .,:;irsXA253hMHGS#9B&@"
SHORT = " .:-=+*#%@"
PALETTES = {
    "amber": (240, 190, 125),
    "ice": (135, 225, 245),
    "green": (115, 238, 159),
    "bone": (236, 228, 208),
}


def _background_to_black(im: Image.Image) -> Image.Image:
    """Matte a photographed skull against black without inverting its cavities.

    For white backdrops, subtract white-ish background rather than inverting
    bone brightness. Shadowed orbital and nasal apertures must remain dark.
    """
    rgb = im.convert("RGB")
    w, h = rgb.size
    corners = [rgb.getpixel((x, y)) for x,y in
               ((0,0),(w-1,0),(0,h-1),(w-1,h-1))]
    gray = ImageOps.grayscale(rgb)
    if min(sum(px)/3 for px in corners) > 215:
        matte = Image.new("L", rgb.size)
        matte.putdata([min(255, max(0, (255 - min(px) - 12) * 7)) for px in rgb.getdata()])
        return ImageChops.multiply(gray, matte)
    return gray


DEMO_URL = "https://upload.wikimedia.org/wikipedia/commons/4/4c/Skullfront.png"
DEMO_CREDIT = (
    "Human skull photograph by Xerto (Cyril NOVEL), Wikimedia Commons, "
    "CC BY-SA 3.0: https://commons.wikimedia.org/wiki/File:Skullfront.png"
)


def demo_image() -> Path:
    """Explicit --demo: download a licensed real skull photo once and cache it.

    Limit download bytes, validate image, remove lower reflection; preserve
    required attribution in accompanying text.
    """
    target_dir = Path.home() / "Library" / "Caches" / "gpt-doug-skull"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / "skullfront-cropped.png"
    if target.exists() and target.stat().st_size > 10000:
        return target
    request = Request(DEMO_URL, headers={"User-Agent": "GPT-DOUG-SKULL-ASCII/1.0 (Wikimedia Commons preview)"})
    with urlopen(request, timeout=25) as response:
        if response.status != 200:
            raise ValueError("Could not retrieve the Wikimedia sample")
        data = response.read(4 * 1024 * 1024 + 1)
    if len(data) > 4 * 1024 * 1024:
        raise ValueError("Sample image exceeded download limit")
    from io import BytesIO
    with Image.open(BytesIO(data)) as raw:
        if raw.width * raw.height > 12_000_000:
            raise ValueError("Sample exceeds pixel limit")
        raw = raw.convert("RGB")
        raw = raw.crop((0, 0, raw.width, int(raw.height * 0.71)))
        raw.save(target, format="PNG", optimize=True)
    (target_dir / "PHOTO-LICENSE.txt").write_text(DEMO_CREDIT + "\n", encoding="utf-8")
    return target


def _crop_subject(im: Image.Image, *, margin: float = 0.08) -> Image.Image:
    """Remove obvious uniform outer area, preserving bone contours."""
    gray = im.convert("L")
    # If both upper corners are near-black, the high-contrast skull is bright.
    threshold = max(18, int(ImageStat.Stat(gray).mean[0] * 0.20))
    binary = gray.point(lambda v: 255 if v > threshold else 0)
    bbox = binary.getbbox()
    if not bbox:
        return im
    x1, y1, x2, y2 = bbox
    iw, ih = im.size
    # Refuse overly aggressive crops: photograph may already fill frame.
    if (x2-x1) * (y2-y1) < 0.07 * iw * ih:
        return im
    bx, by = max(5, int((x2-x1)*margin)), max(5, int((y2-y1)*margin))
    return im.crop((max(0,x1-bx), max(0,y1-by), min(iw,x2+bx), min(ih,y2+by)))


def _prepared_image(
    image_path: Path, *, width: int, pixel_aspect: float, crop: bool,
    contrast: float, gamma: float, sharpness: float, edge: float,
) -> Image.Image:
    if image_path.stat().st_size > 80 * 1024 * 1024:
        raise ValueError("File over 80MB; resize it before conversion")
    with Image.open(image_path) as handle:
        handle.verify()
    with Image.open(image_path) as handle:
        if handle.width * handle.height > 48_000_000:
            raise ValueError("Image exceeds 48 megapixels")
        # Transparent references must be matted on black for terminal use.
        rgba = handle.convert("RGBA")
        background = Image.new("RGBA", rgba.size, (0, 0, 0, 255))
        rgba = Image.alpha_composite(background, rgba)
        im = _background_to_black(rgba.convert("RGB"))
    if crop:
        im = _crop_subject(im)
    # Preserve anatomy even when a source is unusually tall.
    height = max(12, int(round(im.height / im.width * width * pixel_aspect)))
    if height > 220:
        raise ValueError("Result is too tall; lower --width or use --aspect")
    im = im.resize((width, height), Image.Resampling.LANCZOS)
    im = ImageOps.autocontrast(im, cutoff=0.6)
    im = ImageEnhance.Contrast(im).enhance(contrast)
    if sharpness:
        im = im.filter(ImageFilter.UnsharpMask(radius=0.85, percent=int(110 * sharpness), threshold=3))
    if edge:
        grad = im.filter(ImageFilter.FIND_EDGES)
        grad = grad.point(lambda v: min(255, int(v * edge)))
        im = ImageChops.subtract(im, grad)
    if abs(gamma - 1.0) > 0.001:
        # gamma < 1 brightens midtones for visible bone texture on black terminals
        lut = [min(255, int(255 * ((n/255) ** gamma))) for n in range(256)]
        im = im.point(lut)
    return im


def ascii_image(image_path: Path, *, width: int=100, style: str="dense", crop: bool=True,
                aspect: float=0.47, contrast: float=1.2, gamma: float=0.88,
                sharpness: float=0.8, edge: float=0.23) -> tuple[str, Image.Image]:
    """Return 100% copyable ASCII and the processed grayscale raster."""
    if not 40 <= width <= 200 or not 0.3 <= aspect <= 0.7:
        raise ValueError("width must be 40..200 and aspect 0.3..0.7")
    if not 0.1 <= contrast <= 4 or not 0.3 <= gamma <= 3:
        raise ValueError("contrast or gamma out of bounds")
    if not 0 <= edge <= 1 or not 0 <= sharpness <= 2:
        raise ValueError("edge or sharpness out of bounds")
    raster = _prepared_image(image_path, width=width, pixel_aspect=aspect,
                             crop=crop, contrast=contrast, gamma=gamma,
                             sharpness=sharpness, edge=edge)
    ramp = {"dense": DENSE, "normal": NORMAL, "short": SHORT}[style]
    values = list(raster.get_flattened_data() if hasattr(raster, "get_flattened_data") else raster.getdata())
    chars = [ramp[min(len(ramp)-1, v * len(ramp)//256)] for v in values]
    lines = ["".join(chars[i*width:(i+1)*width]).rstrip() for i in range(raster.height)]
    return "\n".join(lines), raster


def colorize(ascii_text: str, raster: Image.Image, palette: str) -> str:
    if palette == "none":
        return ascii_text
    if palette not in PALETTES:
        raise ValueError("Unknown palette")
    base = PALETTES[palette]
    lines = ascii_text.splitlines()
    matrix = list(raster.get_flattened_data() if hasattr(raster, "get_flattened_data") else raster.getdata())
    columns = raster.width
    output = []
    for y, line in enumerate(lines):
        pixels = []
        last = None
        for x, ch in enumerate(line):
            if ch == " ":
                pixels.append(" ")
                continue
            amount = max(0.35, matrix[y*columns+x] / 255)
            rgb = tuple(min(255, int(c * amount)) for c in base)
            if rgb != last:
                pixels.append(f"\033[38;2;{rgb[0]};{rgb[1]};{rgb[2]}m")
                last = rgb
            pixels.append(ch)
        output.append("".join(pixels)+"\033[0m")
    return "\n".join(output)


def main(argv: Sequence[str] | None=None) -> int:
    ap = argparse.ArgumentParser(description="SKULL-LLM photographic anatomical ASCII for Mac Terminal")
    ap.add_argument("image", type=Path, nargs="?", help="skull image (png/jpg/webp), or use --demo")
    ap.add_argument("--demo", action="store_true", help="download real licensed skull reference to local cache")
    ap.add_argument("--width", type=int, default=None, help="columns, default terminal width up to 108")
    ap.add_argument("--style", choices=["dense","normal","short"], default="dense")
    ap.add_argument("--color", choices=["none",*PALETTES], default="none")
    ap.add_argument("--contrast", type=float, default=1.20)
    ap.add_argument("--gamma", type=float, default=0.88)
    ap.add_argument("--sharpness", type=float, default=0.8)
    ap.add_argument("--edge", type=float, default=0.23)
    ap.add_argument("--aspect", type=float, default=0.47, help="character width/height")
    ap.add_argument("--no-crop", action="store_true")
    ap.add_argument("--save", type=Path, help="save copyable plain ASCII (.txt)")
    args = ap.parse_args(argv)
    try:
        if args.demo:
            path = demo_image()
            print("Source: " + DEMO_CREDIT, file=sys.stderr)
        elif args.image is not None:
            path = args.image.expanduser().resolve()
        else:
            raise ValueError("Supply an image or --demo")
        if not path.is_file():
            raise ValueError(f"Image not found: {path}")
        width = args.width or min(108,max(40,shutil.get_terminal_size((110,40)).columns-2))
        art, raster = ascii_image(path,width=width,style=args.style,crop=not args.no_crop,
                                  aspect=args.aspect,contrast=args.contrast,gamma=args.gamma,
                                  sharpness=args.sharpness,edge=args.edge)
        if args.save:
            destination = args.save.expanduser()
            destination.parent.mkdir(parents=True, exist_ok=True)
            header = ("# " + DEMO_CREDIT + "\n") if args.demo else ""
            destination.write_text(header + art + '\n', encoding="utf-8")
            print("Saved ASCII: " + str(destination), file=sys.stderr)
        print(colorize(art,raster,args.color))
    except (OSError, ValueError, KeyError) as exc:
        print(f"SKULL-ASCII ERROR: {exc}",file=sys.stderr)
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())