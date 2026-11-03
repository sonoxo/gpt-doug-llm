"""GPT-DOUG Motion-1: original tiny text-conditioned spatiotemporal DDPM.

This is original training/inference code, not a checkpoint from Higgsfield or Wan.
Research scale by design: intended for 8-frame, 32x32 motion clips.
MIT-licensed under the repository LICENSE.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import math
import re

import torch
from torch import Tensor, nn
from torch.nn import functional as F


@dataclass(frozen=True)
class MotionConfig:
    frames: int = 8
    size: int = 32
    width: int = 24
    timesteps: int = 48
    vocab: int = 4096
    cond_dim: int = 64

    def validate(self) -> None:
        if self.frames not in (4, 8, 12, 16):
            raise ValueError("frames must be 4, 8, 12, or 16")
        if self.size not in (16, 32, 48, 64):
            raise ValueError("size must be 16, 32, 48, or 64")
        if self.width not in (8, 16, 24, 32, 48):
            raise ValueError("width must be 8, 16, 24, 32, or 48")
        if not 4 <= self.timesteps <= 128:
            raise ValueError("timesteps must be 4-128")
        if not 128 <= self.vocab <= 65536:
            raise ValueError("vocab must be 128-65536")
        if self.cond_dim % 2 or not 16 <= self.cond_dim <= 256:
            raise ValueError("cond_dim must be even and between 16-256")

    def to_dict(self) -> dict:
        return asdict(self)


def prompt_tokens(prompt: str, vocab: int = 4096, length: int = 16) -> list[int]:
    """Deterministic stable token hashing. NO external tokenizer/download needed.

    A trainable embedding learns associations only from captions in the training set.
    """
    if not 128 <= vocab <= 65536 or not 1 <= length <= 64:
        raise ValueError("invalid tokenizer dimensions")
    if not isinstance(prompt, str) or len(prompt) > 400:
        raise ValueError("prompt must be text of at most 400 characters")
    words = re.findall(r"[a-z0-9]+", prompt.lower())[:length]
    ids = [1 + int.from_bytes(hashlib.blake2b(w.encode(), digest_size=4).digest(), "big") % (vocab - 1) for w in words]
    return ids + [0] * (length - len(ids))


def time_encoding(t: Tensor, size: int) -> Tensor:
    if size % 2:
        raise ValueError("time embedding dimension must be even")
    half = size // 2
    freq = torch.exp(-math.log(10000) * torch.arange(half, device=t.device, dtype=torch.float32) / max(half - 1, 1))
    angles = t.float().unsqueeze(-1) * freq.unsqueeze(0)
    return torch.cat((angles.sin(), angles.cos()), dim=-1)


class ResidualMotionBlock(nn.Module):
    """Spatial + temporal convolution conditioned through a FiLM affine gate."""

    def __init__(self, width: int, condition_dim: int):
        super().__init__()
        self.norm = nn.GroupNorm(4, width)
        self.film = nn.Linear(condition_dim, width * 2)
        self.spatial = nn.Conv3d(width, width, kernel_size=(1, 3, 3), padding=(0, 1, 1))
        self.temporal = nn.Conv3d(width, width, kernel_size=(3, 1, 1), padding=(1, 0, 0))

    def forward(self, x: Tensor, condition: Tensor) -> Tensor:
        scale, shift = self.film(condition).chunk(2, dim=1)
        h = self.norm(x)
        h = h * (1 + scale[:, :, None, None, None]) + shift[:, :, None, None, None]
        h = self.spatial(F.silu(h))
        h = self.temporal(F.silu(h))
        return x + h * 0.35


class MotionDenoiser(nn.Module):
    def __init__(self, cfg: MotionConfig):
        super().__init__()
        cfg.validate()
        self.cfg = cfg
        self.text_embed = nn.Embedding(cfg.vocab, cfg.cond_dim, padding_idx=0)
        self.time_mlp = nn.Sequential(
            nn.Linear(cfg.cond_dim, cfg.cond_dim),
            nn.SiLU(),
            nn.Linear(cfg.cond_dim, cfg.cond_dim),
        )
        self.combine = nn.Sequential(
            nn.Linear(cfg.cond_dim * 2, cfg.cond_dim * 2), nn.SiLU(),
            nn.Linear(cfg.cond_dim * 2, cfg.cond_dim * 2),
        )
        self.input = nn.Conv3d(3, cfg.width, 3, padding=1)
        self.blocks = nn.ModuleList(ResidualMotionBlock(cfg.width, cfg.cond_dim * 2) for _ in range(3))
        self.output_norm = nn.GroupNorm(4, cfg.width)
        self.output = nn.Conv3d(cfg.width, 3, 3, padding=1)
        nn.init.zeros_(self.output.weight)
        nn.init.zeros_(self.output.bias)

    def forward(self, noisy_video: Tensor, timestep: Tensor, tokens: Tensor) -> Tensor:
        if noisy_video.ndim != 5 or noisy_video.shape[1] != 3:
            raise ValueError("video tensor must have shape [batch,3,frames,height,width]")
        batch = noisy_video.shape[0]
        if tokens.ndim != 2 or tokens.shape[0] != batch or timestep.shape != (batch,):
            raise ValueError("invalid conditioning dimensions")
        words = self.text_embed(tokens)
        mask = (tokens != 0).unsqueeze(-1)
        text_features = (words * mask).sum(dim=1) / mask.sum(dim=1).clamp(min=1)
        when = self.time_mlp(time_encoding(timestep, self.cfg.cond_dim))
        condition = self.combine(torch.cat((text_features, when), dim=-1))
        h = self.input(noisy_video)
        for block in self.blocks:
            h = block(h, condition)
        return self.output(F.silu(self.output_norm(h)))


class MotionDiffusion(nn.Module):
    """DDPM noise-prediction objective and ancestral reverse sampler."""

    def __init__(self, cfg: MotionConfig):
        super().__init__()
        cfg.validate()
        self.cfg = cfg
        self.denoiser = MotionDenoiser(cfg)
        betas = torch.linspace(0.0001, 0.02, cfg.timesteps, dtype=torch.float32)
        alphas = 1.0 - betas
        cumulative = torch.cumprod(alphas, dim=0)
        self.register_buffer("betas", betas)
        self.register_buffer("alphas", alphas)
        self.register_buffer("cumulative", cumulative)

    def loss(self, video: Tensor, tokens: Tensor) -> Tensor:
        if video.ndim != 5 or video.shape[1:] != (3, self.cfg.frames, self.cfg.size, self.cfg.size):
            raise ValueError("input video shape does not match model configuration")
        batch = video.shape[0]
        when = torch.randint(0, self.cfg.timesteps, (batch,), device=video.device)
        noise = torch.randn_like(video)
        cumulative = self.cumulative[when].reshape(batch, 1, 1, 1, 1)
        noisy = cumulative.sqrt() * video + (1.0 - cumulative).sqrt() * noise
        predicted = self.denoiser(noisy, when, tokens)
        return F.mse_loss(predicted, noise)

    @torch.inference_mode()
    def sample(self, tokens: Tensor, seed: int = 42) -> Tensor:
        if tokens.ndim != 2 or tokens.shape[0] != 1:
            raise ValueError("sampling supports one prompt at a time")
        cfg = self.cfg
        device = next(self.parameters()).device
        # RNG is restored so generation does not permanently reset global model RNG.
        with torch.random.fork_rng(devices=[] if device.type != "cuda" else [device]):
            torch.manual_seed(seed)
            video = torch.randn((1, 3, cfg.frames, cfg.size, cfg.size), device=device)
            for index in range(cfg.timesteps - 1, -1, -1):
                t = torch.tensor([index], device=device, dtype=torch.long)
                pred_noise = self.denoiser(video, t, tokens)
                alpha = self.alphas[index]
                cumulative = self.cumulative[index]
                avg = (video - (1 - alpha) / torch.sqrt(1 - cumulative) * pred_noise) / torch.sqrt(alpha)
                if index:
                    # Ancestral DDPM posterior variance.
                    previous = self.cumulative[index - 1]
                    variance = self.betas[index] * (1 - previous) / (1 - cumulative)
                    video = avg + variance.clamp(min=0).sqrt() * torch.randn_like(video)
                else:
                    video = avg
        return video.clamp(-1, 1).detach().cpu()[0]


def trained_parameter_count(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)
