"""Opt-in local training and checkpoint sampling for the small SKULL Transformer."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path

import torch

from .neural import NeuralConfig, SkullTransformer


def device_for_training() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def train_file(
    corpus: str,
    checkpoint: str,
    *,
    steps: int = 100,
    batch_size: int = 8,
    context: int = 128,
    dim: int = 128,
    layers: int = 2,
    heads: int = 4,
    learning_rate: float = 3e-4,
    seed: int = 42,
    device: str | None = None,
) -> dict:
    if not 1 <= steps <= 100000 or not 1 <= batch_size <= 256:
        raise ValueError("steps must be 1..100000 and batch size 1..256")
    if not 1e-6 <= learning_rate <= 0.1:
        raise ValueError("learning rate must be 0.000001..0.1")
    cfg = NeuralConfig(dim=dim, layers=layers, heads=heads, max_seq_len=context)
    source = Path(corpus).expanduser()
    if not source.is_file():
        raise ValueError("training corpus file does not exist")
    if source.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("corpus exceeds the 32 MiB reference trainer limit")
    raw = source.read_bytes()
    if len(raw) < context + 2:
        raise ValueError("corpus needs at least context + 2 UTF-8 bytes")
    torch.manual_seed(seed)
    selected_device = device or device_for_training()
    data = torch.tensor(list(raw), dtype=torch.long, device=selected_device)
    model = SkullTransformer(cfg).to(selected_device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    positions = torch.arange(context, device=selected_device)
    model.train()
    last_loss = None
    for _ in range(steps):
        starts = torch.randint(
            0, len(raw) - context, (batch_size,), device=selected_device
        )
        inputs = data[starts[:, None] + positions[None, :]]
        targets = data[starts[:, None] + positions[None, :] + 1]
        _, loss = model(inputs, targets)
        if loss is None or not bool(torch.isfinite(loss).item()):
            raise RuntimeError("training loss became non-finite")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()
        last_loss = float(loss.item())
    output = Path(checkpoint).expanduser()
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"config": asdict(cfg), "state_dict": model.cpu().state_dict(),
         "training_steps": steps, "training_bytes": len(raw)},
        output,
    )
    return {
        "checkpoint": str(output), "training_steps": steps, "training_bytes": len(raw),
        "parameters": model.parameter_count(), "final_training_loss": last_loss,
        "device": selected_device, "pretrained": False,
    }


def sample_file(
    checkpoint: str, prompt: str, *,
    new_tokens: int = 80, temperature: float = 0.8, top_k: int = 40,
) -> str:
    if not Path(checkpoint).expanduser().is_file():
        raise ValueError("checkpoint not found")
    # weights_only blocks arbitrary pickle object restoration; never load untrusted files.
    payload = torch.load(
        Path(checkpoint).expanduser(), map_location="cpu", weights_only=True
    )
    if not isinstance(payload, dict) or not isinstance(payload.get("config"), dict):
        raise ValueError("invalid SKULL-LLM checkpoint")
    cfg = NeuralConfig(**payload["config"])
    if cfg.vocab_size != 256:
        raise ValueError("byte-token model requires a vocabulary of 256")
    model = SkullTransformer(cfg)
    model.load_state_dict(payload["state_dict"], strict=True)
    data = (prompt.encode("utf-8") or b"\n")[-cfg.max_seq_len:]
    tokens = torch.tensor([list(data)], dtype=torch.long)
    generated = model.generate(
        tokens, max_new_tokens=new_tokens, temperature=temperature, top_k=top_k
    )
    return bytes(generated[0].tolist()).decode("utf-8", errors="replace")
