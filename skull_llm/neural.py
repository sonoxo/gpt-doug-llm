"""Small, trainable decoder-only Transformer for SKULL-LLM.

This is a from-scratch reference network, *not* a pretrained foundation model.
For practical answers use SKULL-LLM's open-weight Ollama inference runtime.
Optional dependency: pip install -e '.[skull]'.
"""
from __future__ import annotations

from dataclasses import dataclass

import torch
from torch import nn
from torch.nn import functional as F


@dataclass(frozen=True)
class NeuralConfig:
    vocab_size: int = 256   # UTF-8 byte tokens: no external tokenizer
    dim: int = 256
    layers: int = 4
    heads: int = 4
    max_seq_len: int = 256
    dropout: float = 0.0

    def __post_init__(self) -> None:
        if not 2 <= self.vocab_size <= 65536:
            raise ValueError("vocab_size must be 2..65536")
        if not 32 <= self.dim <= 4096 or not 1 <= self.layers <= 48:
            raise ValueError("invalid model dimensions")
        if not 1 <= self.heads <= 64 or self.dim % self.heads:
            raise ValueError("dim must be divisible by heads")
        if (self.dim // self.heads) % 2:
            raise ValueError("attention head dimension must be even for rotary embeddings")
        if not 8 <= self.max_seq_len <= 8192 or not 0 <= self.dropout < 1:
            raise ValueError("invalid context window or dropout")


class RMSNorm(nn.Module):
    def __init__(self, dim: int) -> None:
        super().__init__()
        self.weight = nn.Parameter(torch.ones(dim))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        scale = torch.rsqrt(x.float().pow(2).mean(-1, keepdim=True) + 1e-6)
        return (x.float() * scale).to(x.dtype) * self.weight


def _rotate(x: torch.Tensor, cos: torch.Tensor, sin: torch.Tensor) -> torch.Tensor:
    even, odd = x[..., ::2], x[..., 1::2]
    return torch.stack((even * cos - odd * sin, even * sin + odd * cos), -1).flatten(-2)


class CausalAttention(nn.Module):
    def __init__(self, cfg: NeuralConfig) -> None:
        super().__init__()
        self.heads = cfg.heads
        self.head_dim = cfg.dim // cfg.heads
        self.dropout = cfg.dropout
        self.qkv = nn.Linear(cfg.dim, cfg.dim * 3, bias=False)
        self.out = nn.Linear(cfg.dim, cfg.dim, bias=False)
        self.register_buffer(
            "inv_freq",
            1 / (10000 ** (torch.arange(0, self.head_dim, 2).float() / self.head_dim)),
            persistent=False,
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, seq, dim = x.shape
        qkv = self.qkv(x).reshape(batch, seq, 3, self.heads, self.head_dim)
        q, k, v = qkv.unbind(dim=2)
        q, k, v = (tensor.transpose(1, 2) for tensor in (q, k, v))
        positions = torch.arange(seq, device=x.device, dtype=self.inv_freq.dtype)
        angles = torch.outer(positions, self.inv_freq.to(device=x.device))
        cos, sin = angles.cos()[None, None], angles.sin()[None, None]
        q, k = _rotate(q, cos, sin), _rotate(k, cos, sin)
        attended = F.scaled_dot_product_attention(
            q, k, v, is_causal=True, dropout_p=self.dropout if self.training else 0.0
        )
        return self.out(attended.transpose(1, 2).contiguous().view(batch, seq, dim))


class SwiGLU(nn.Module):
    def __init__(self, cfg: NeuralConfig) -> None:
        super().__init__()
        hidden = (8 * cfg.dim // 3 + 63) // 64 * 64
        self.gate = nn.Linear(cfg.dim, hidden, bias=False)
        self.up = nn.Linear(cfg.dim, hidden, bias=False)
        self.down = nn.Linear(hidden, cfg.dim, bias=False)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.down(F.silu(self.gate(x)) * self.up(x))


class DecoderBlock(nn.Module):
    def __init__(self, cfg: NeuralConfig) -> None:
        super().__init__()
        self.attn_norm = RMSNorm(cfg.dim)
        self.attn = CausalAttention(cfg)
        self.ffn_norm = RMSNorm(cfg.dim)
        self.ffn = SwiGLU(cfg)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attn(self.attn_norm(x))
        return x + self.ffn(self.ffn_norm(x))


class SkullTransformer(nn.Module):
    """Causal decoder with rotary embeddings, RMSNorm, SwiGLU and tied weights."""

    def __init__(self, cfg: NeuralConfig) -> None:
        super().__init__()
        self.cfg = cfg
        self.embedding = nn.Embedding(cfg.vocab_size, cfg.dim)
        self.blocks = nn.ModuleList(DecoderBlock(cfg) for _ in range(cfg.layers))
        self.norm = RMSNorm(cfg.dim)
        self.output = nn.Linear(cfg.dim, cfg.vocab_size, bias=False)
        self.output.weight = self.embedding.weight
        self.apply(self._init_weights)

    @staticmethod
    def _init_weights(module: nn.Module) -> None:
        if isinstance(module, (nn.Linear, nn.Embedding)):
            nn.init.normal_(module.weight, mean=0.0, std=0.02)

    def forward(
        self, tokens: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        if tokens.ndim != 2 or tokens.size(1) < 1 or tokens.size(1) > self.cfg.max_seq_len:
            raise ValueError("tokens must be [batch, 1..max_seq_len]")
        if tokens.dtype not in (torch.int32, torch.int64):
            raise ValueError("tokens must contain integer token IDs")
        if targets is not None and targets.shape != tokens.shape:
            raise ValueError("targets must match tokens shape")
        x = self.embedding(tokens)
        for block in self.blocks:
            x = block(x)
        logits = self.output(self.norm(x))
        loss = None
        if targets is not None:
            loss = F.cross_entropy(
                logits.reshape(-1, logits.size(-1)), targets.reshape(-1), ignore_index=-100
            )
        return logits, loss

    @torch.no_grad()
    def generate(
        self, tokens: torch.Tensor, max_new_tokens: int = 64,
        temperature: float = 0.8, top_k: int = 40,
    ) -> torch.Tensor:
        if tokens.ndim != 2 or tokens.size(1) < 1:
            raise ValueError("prompt needs at least one token")
        if not 1 <= max_new_tokens <= 2048 or temperature <= 0 or top_k < 1:
            raise ValueError("invalid sampling configuration")
        self.eval()
        for _ in range(max_new_tokens):
            logits, _ = self(tokens[:, -self.cfg.max_seq_len:])
            next_logits = logits[:, -1, :].float() / temperature
            k = min(top_k, next_logits.shape[-1])
            minimum = torch.topk(next_logits, k).values[:, -1:]
            next_logits = next_logits.masked_fill(next_logits < minimum, float("-inf"))
            token = torch.multinomial(torch.softmax(next_logits, dim=-1), 1)
            tokens = torch.cat((tokens, token), dim=1)
        return tokens

    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())
