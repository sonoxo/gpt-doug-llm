"""Generate genuine Motion-1 DDPM clips from trained weights, or labeled synthetic demo.

Outputs GIF using Pillow; MP4 is optional through free FFmpeg.
No hosted inference endpoints, no external models or API keys.
"""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import tempfile

import torch
from PIL import Image

from .data import synthetic_clip
from .model import prompt_tokens
from .train import load_checkpoint, select_device


def video_frames(video: torch.Tensor) -> list[Image.Image]:
    if video.ndim != 4 or video.shape[0] != 3:
        raise ValueError("Expected video [RGB, frames, height, width]")
    _, frames, height, width = video.shape
    result = []
    for i in range(frames):
        rgb = ((video[:, i].detach().float().cpu().clamp(-1, 1) + 1) * 127.5)
        raw = rgb.permute(1, 2, 0).to(torch.uint8).contiguous().flatten().tolist()
        result.append(Image.frombytes("RGB", (width, height), bytes(raw)))
    return result


def save_video(frames: list[Image.Image], output: Path, fps: int = 8) -> Path:
    if not 1 <= fps <= 30 or not frames:
        raise ValueError("FPS must be 1-30 and frames nonempty")
    output = Path(output).expanduser()
    if output.suffix.lower() not in {".gif", ".mp4"}:
        raise ValueError("Output must end in .gif or .mp4")
    if output.is_symlink():
        raise ValueError("Refusing to overwrite symlink output")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.suffix.lower() == ".gif":
        frames[0].save(output, save_all=True, append_images=frames[1:],
                       duration=round(1000 / fps), loop=0, disposal=2, optimize=False)
    else:
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise RuntimeError("MP4 requires free FFmpeg. Install with: brew install ffmpeg. GIF works without FFmpeg.")
        with tempfile.TemporaryDirectory(prefix="gpt-doug-motion1-") as directory:
            folder = Path(directory)
            for index, frame in enumerate(frames):
                frame.save(folder / f"{index:05d}.png")
            command = [ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                       "-framerate", str(fps), "-i", str(folder / "%05d.png"),
                       "-c:v", "libx264", "-pix_fmt", "yuv420p",
                       "-movflags", "+faststart", str(output)]
            subprocess.run(command, check=True, timeout=120)
    return output


def render(*, prompt: str, output: Path, checkpoint: Path | None = None,
           seed: int = 42, fps: int = 8, device_name: str = "auto",
           preview: bool = False) -> dict:
    if not prompt.strip() or len(prompt) > 400:
        raise ValueError("Prompt must contain 1-400 characters")
    if not 0 <= seed <= 2**31-1:
        raise ValueError("Seed must be in range 0..2**31-1")
    if preview:
        model_used = "synthetic geometric preview (NOT AI generation)"
        video = synthetic_clip(prompt, 8, 32, seed=seed)
        origin = "original procedural moving-shape generator"
        steps = 0
    else:
        if checkpoint is None:
            raise ValueError("Trained checkpoint required for neural generation")
        device = select_device(device_name)
        model, payload = load_checkpoint(checkpoint, device=device)
        tokens = torch.tensor([prompt_tokens(prompt, model.cfg.vocab)],
                              dtype=torch.long, device=device)
        video = model.sample(tokens, seed=seed)
        model_used = "GPT-DOUG Motion-1 original DDPM"
        origin = payload.get("data_origin", "unknown")
        steps = payload["trained_steps"]
    frames = video_frames(video)
    result = save_video(frames, output, fps=fps)
    details = {
        "model": model_used, "output": str(result.resolve()),
        "prompt": prompt, "seed": seed, "fps": fps,
        "frames": len(frames), "size": frames[0].size,
        "train_data_origin": origin, "trained_steps": steps,
        "preview_not_ml": bool(preview),
        "quality": "Research-scale; not a pretrained cinematic foundation model",
        "api_calls": 0, "cost_usd_per_generation": 0,
    }
    receipt = result.with_suffix(".json")
    receipt.write_text(json.dumps(details, indent=2) + "\n", encoding="utf-8")
    return details
