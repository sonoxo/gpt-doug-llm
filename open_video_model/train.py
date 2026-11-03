"""Local training for GPT-DOUG Motion-1 (PyTorch + Pillow, no cloud inference)."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import random
import time

import torch

from .data import FolderClipSet, make_training_batch
from .model import MotionConfig, MotionDiffusion, prompt_tokens, trained_parameter_count


DEFAULT_CHECKPOINT = Path.home() / ".local/share/gpt-doug/motion-1/motion1.pt"


def select_device(requested: str = "auto") -> torch.device:
    if requested not in ("auto", "cpu", "cuda", "mps"):
        raise ValueError("device must be auto, cpu, cuda or mps")
    if requested == "auto":
        if torch.backends.mps.is_available():
            return torch.device("mps")
        if torch.cuda.is_available():
            return torch.device("cuda")
        return torch.device("cpu")
    if requested == "mps" and not torch.backends.mps.is_available():
        raise RuntimeError("Apple Metal MPS unavailable; try --device cpu")
    if requested == "cuda" and not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU unavailable; try --device cpu")
    return torch.device(requested)


def save_checkpoint(model: MotionDiffusion, path: Path, trained_steps: int,
                    data_origin: str, final_loss: float) -> None:
    path = Path(path).expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.is_symlink():
        raise ValueError("Refusing to overwrite a symlink checkpoint")
    # Save state_dict only; never serialize Python executable model objects.
    obj = {
        "format": "gpt-doug-motion-1-checkpoint-v1",
        "license": "MIT (original implementation); dataset rights remain with owner",
        "config": model.cfg.to_dict(),
        "state_dict": {k: t.detach().cpu() for k, t in model.state_dict().items()},
        "trained_steps": int(trained_steps),
        "data_origin": data_origin,
        "final_loss": float(final_loss),
    }
    temp = path.with_name(path.name + ".partial")
    try:
        torch.save(obj, temp)
        temp.replace(path)
    finally:
        if temp.exists():
            temp.unlink()


def load_checkpoint(path: Path, device: torch.device | str = "cpu") -> tuple[MotionDiffusion, dict]:
    path = Path(path).expanduser()
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError("Checkpoint missing. Train Motion-1 before neural generation.")
    if path.stat().st_size > 120_000_000:
        raise ValueError("Checkpoint exceeds the approved size limit")
    # weights_only prevents pickled application objects from running during load.
    payload = torch.load(path, map_location="cpu", weights_only=True)
    if not isinstance(payload, dict) or payload.get("format") != "gpt-doug-motion-1-checkpoint-v1":
        raise ValueError("Unrecognized Motion-1 checkpoint")
    config_raw = payload.get("config")
    if not isinstance(config_raw, dict):
        raise ValueError("Checkpoint missing model config")
    cfg = MotionConfig(**config_raw)
    cfg.validate()
    model = MotionDiffusion(cfg)
    model.load_state_dict(payload["state_dict"], strict=True)
    model.to(device)
    model.eval()
    if not isinstance(payload.get("trained_steps"), int) or payload["trained_steps"] < 1:
        raise ValueError("Checkpoint has not been trained")
    return model, payload


def train(config: MotionConfig, *, steps: int = 500, batch_size: int = 2,
          lr: float = 0.0006, seed: int = 42,
          checkpoint: Path = DEFAULT_CHECKPOINT, dataset: Path | None = None,
          device_name: str = "auto", log_every: int = 25) -> dict:
    config.validate()
    if not 1 <= steps <= 100_000 or not 1 <= batch_size <= 16:
        raise ValueError("Training requires 1-100000 steps and batch size 1-16")
    if not 0 < lr <= .01:
        raise ValueError("Learning rate must be between 0 and .01")
    if not 0 <= seed <= 2**31 - 1:
        raise ValueError("Seed must be in range 0..2**31-1")
    device = select_device(device_name)
    random.seed(seed)
    torch.manual_seed(seed)
    scenes = FolderClipSet(dataset, config) if dataset else None
    data_origin = "synthetic original moving shapes" if scenes is None else "operator-supplied local frames"
    model = MotionDiffusion(config).to(device).train()
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.0001)
    start = time.monotonic()
    last_loss = 0.0
    for step in range(steps):
        batch, prompts = make_training_batch(config, batch_size, step, scenes)
        token_batch = torch.tensor([prompt_tokens(p, config.vocab) for p in prompts],
                                   dtype=torch.long, device=device)
        batch = batch.to(device)
        optimizer.zero_grad(set_to_none=True)
        loss = model.loss(batch, token_batch)
        if not torch.isfinite(loss):
            raise RuntimeError("Training diverged (nonfinite loss); checkpoint not saved")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        last_loss = float(loss.detach().cpu())
        if (step + 1) % log_every == 0 or step + 1 == steps:
            print(f"GPT-DOUG Motion-1 | {step + 1}/{steps} | loss={last_loss:.5f} | device={device}", flush=True)
    save_checkpoint(model, checkpoint, steps, data_origin, last_loss)
    return {
        "model": "GPT-DOUG Motion-1",
        "checkpoint": str(Path(checkpoint).expanduser().resolve()),
        "parameters": trained_parameter_count(model),
        "trained_steps": steps, "frames": config.frames, "resolution": config.size,
        "dataset": data_origin, "device": str(device), "loss": last_loss,
        "elapsed_seconds": round(time.monotonic() - start, 2),
        "license": "MIT (implementation)",
        "quality_notice": "Research-scale diffusion. Cinematic quality is not claimed.",
    }
