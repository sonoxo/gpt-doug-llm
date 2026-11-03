"""GPT-DOUG Motion-1 public/authorized training clips.

Synthetic clips are original moving geometric primitives (no downloads).
Folder clips accept local JPG/PNG frames and a caption.txt per scene.
"""
from __future__ import annotations

import math
from pathlib import Path
import random
import re

import torch
from torch import Tensor
from PIL import Image

from .model import MotionConfig

CAPTIONS = (
    "red circle moving right",
    "red circle moving left",
    "blue square moving right",
    "blue square moving left",
    "green circle moving up",
    "green circle moving down",
    "yellow square moving up",
    "yellow square moving down",
    "purple circle moving diagonally",
    "orange square moving diagonally",
)

COLORS = {
    "red": (1.0, -0.25, -0.35), "blue": (-0.45, 0.20, 1.0),
    "green": (-0.35, 0.95, 0.10), "yellow": (1.0, 0.85, -0.35),
    "purple": (0.55, -0.20, 1.0), "orange": (1.0, 0.30, -0.40),
}


def synthetic_clip(prompt: str, frames: int, size: int, seed: int = 0) -> Tensor:
    """Generate a real moving-shape training example with tensor output [3,T,H,W]."""
    if not 4 <= frames <= 16 or not 16 <= size <= 64:
        raise ValueError("synthetic clip dimensions out of bounds")
    words = set(re.findall(r"[a-z]+", prompt.lower()))
    color = next((COLORS[w] for w in COLORS if w in words), COLORS["red"])
    is_square = "square" in words
    direction_x = -1 if "left" in words else 1 if "right" in words else 0
    direction_y = -1 if "up" in words else 1 if "down" in words else 0
    if "diagonally" in words:
        direction_x, direction_y = 1, -1
    rng = random.Random(seed)
    radius = rng.uniform(.15, .22)
    offset = rng.uniform(-.14, .14)
    grid_y, grid_x = torch.meshgrid(
        torch.linspace(-1, 1, size), torch.linspace(-1, 1, size), indexing="ij"
    )
    output = torch.full((3, frames, size, size), -.94, dtype=torch.float32)
    for t in range(frames):
        pos = t / (frames - 1)
        cx = offset + direction_x * (pos - .5) * 1.15
        cy = -offset + direction_y * (pos - .5) * 1.15
        if is_square:
            mask = (grid_x - cx).abs().maximum((grid_y - cy).abs()) <= radius
        else:
            mask = ((grid_x - cx) ** 2 + (grid_y - cy) ** 2) <= radius ** 2
        for channel, value in enumerate(color):
            output[channel, t, mask] = value
    return output


class FolderClipSet:
    """Read only scene folders explicitly supplied by the operator."""

    def __init__(self, root: Path, cfg: MotionConfig):
        self.root = Path(root).expanduser().resolve(strict=True)
        self.cfg = cfg
        self.scenes = []
        if not self.root.is_dir():
            raise ValueError("dataset directory is missing")
        for scene in sorted(self.root.iterdir()):
            if not scene.is_dir() or scene.is_symlink():
                continue
            caption_file = scene / "caption.txt"
            if not caption_file.is_file() or caption_file.is_symlink():
                continue
            caption = caption_file.read_text(encoding="utf-8").strip()
            if not 1 <= len(caption) <= 400:
                continue
            frames_dir = scene / "frames"
            if not frames_dir.is_dir() or frames_dir.is_symlink():
                continue
            images = [p for p in sorted(frames_dir.iterdir())
                      if p.is_file() and not p.is_symlink() and p.suffix.lower() in (".png", ".jpg", ".jpeg")
                      and p.stat().st_size <= 8_000_000]
            if len(images) >= cfg.frames:
                self.scenes.append((caption, images))
        if not self.scenes:
            raise ValueError("No approved scene directories with caption.txt and enough local PNG/JPG frames")

    def __len__(self) -> int:
        return len(self.scenes)

    def sample(self, index: int) -> tuple[str, Tensor]:
        caption, frames = self.scenes[index % len(self.scenes)]
        result = []
        for i in range(self.cfg.frames):
            offset = round(i * (len(frames) - 1) / max(self.cfg.frames - 1, 1))
            with Image.open(frames[offset]) as pic:
                rgb = pic.convert("RGB").resize((self.cfg.size, self.cfg.size), Image.Resampling.BICUBIC)
                # Pillow conversion avoids optional NumPy; output channels in [-1,1].
                pixels = torch.tensor(list(rgb.getdata()), dtype=torch.float32)
            result.append((pixels.reshape(self.cfg.size, self.cfg.size, 3)
                           .permute(2, 0, 1) / 127.5 - 1))
        return caption, torch.stack(result, dim=1)


def make_training_batch(cfg: MotionConfig, batch_size: int, step: int,
                        scenes: FolderClipSet | None = None) -> tuple[Tensor, list[str]]:
    if not 1 <= batch_size <= 16:
        raise ValueError("batch size outside 1-16")
    clips = []
    prompts = []
    for i in range(batch_size):
        if scenes is None:
            caption = CAPTIONS[(step * batch_size + i) % len(CAPTIONS)]
            clip = synthetic_clip(caption, cfg.frames, cfg.size, seed=step * 397 + i)
        else:
            caption, clip = scenes.sample(step * batch_size + i)
        prompts.append(caption)
        clips.append(clip)
    return torch.stack(clips), prompts
