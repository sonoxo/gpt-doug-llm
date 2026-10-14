"""GPT-Almighty-Sonoxo-MLM-SAGIQI: a *trainable* masked language model.

A compact bidirectional Transformer learns token-distribution weights from a
caller-supplied UTF-8 corpus. This is a genuine masked-language-model objective
(not a chatbot, a pretrained foundation model, or a claim of superintelligence).

Inference is local. Model artifacts are saved in the non-pickle safetensors
format and verified against a SHA-256 manifest before loading. No network,
autonomous self-modification, data collection, or tool execution is performed.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import re
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence

try:
    import torch
    from torch import Tensor, nn
    from torch.nn import functional as F
except ImportError as exc:  # optional dependency for this model only
    raise ImportError("Install the mlm extra: pip install -e '.[mlm]'") from exc

MODEL_ID = "gpt-almighty-sonoxo-mlm-sagiqi"
FORMAT_VERSION = 1
PAD, UNK, MASK, CLS, SEP = "[PAD]", "[UNK]", "[MASK]", "[CLS]", "[SEP]"
SPECIAL = (PAD, UNK, MASK, CLS, SEP)
TOKEN_RE = re.compile(r"\[MASK\]|[A-Za-z0-9]+(?:[-'][A-Za-z0-9]+)*|[^\w\s]", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    """Tokenize public text deterministically; preserve only the [MASK] token."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    parts = TOKEN_RE.findall(text)
    return [MASK if part.upper() == MASK else part.lower() for part in parts]


class WordTokenizer:
    """Small self-contained word-level tokenizer learned with the checkpoint."""

    def __init__(self, vocab: Sequence[str]) -> None:
        self.vocab = list(vocab)
        if (self.vocab[:len(SPECIAL)] != list(SPECIAL)
                or len(set(self.vocab)) != len(self.vocab)
                or not len(SPECIAL) < len(self.vocab) <= 4096
                or any(not isinstance(v, str) or not v for v in self.vocab)):
            raise ValueError("invalid vocabulary or special-token order")
        self.ids = {token: index for index, token in enumerate(self.vocab)}

    @classmethod
    def fit(cls, lines: Sequence[str], max_vocab: int = 512) -> "WordTokenizer":
        if not len(SPECIAL) + 1 <= max_vocab <= 4096:
            raise ValueError("vocabulary size must be between 6 and 4096")
        freqs: Counter[str] = Counter()
        for line in lines:
            freqs.update(t for t in tokenize(line) if t != MASK)
        # Tie-break alphabetically for reproducibility.
        top = sorted(freqs.items(), key=lambda pair: (-pair[1], pair[0]))[:max_vocab - len(SPECIAL)]
        if not top:
            raise ValueError("training text has no usable tokens")
        return cls([*SPECIAL, *(t for t, _ in top)])

    def encode(self, text: str, max_len: int) -> list[int]:
        tokens = tokenize(text)
        if not 8 <= max_len <= 256:
            raise ValueError("max_len must be between 8 and 256")
        tokens = tokens[:max_len - 2]
        return [self.ids[CLS], *[self.ids.get(t, self.ids[UNK]) for t in tokens], self.ids[SEP]]


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int
    max_len: int = 64
    d_model: int = 64
    num_heads: int = 4
    num_layers: int = 2
    ff_dim: int = 128

    def validate(self) -> None:
        if not 6 <= self.vocab_size <= 4096:
            raise ValueError("vocab_size outside supported range")
        if not 8 <= self.max_len <= 256:
            raise ValueError("max_len outside supported range")
        if not 16 <= self.d_model <= 256 or self.d_model % self.num_heads:
            raise ValueError("invalid model width/head configuration")
        if not 1 <= self.num_heads <= 16 or not 1 <= self.num_layers <= 6:
            raise ValueError("invalid attention head/layer count")
        if not 32 <= self.ff_dim <= 1024:
            raise ValueError("ff_dim outside supported range")


class AlmightySonoxoMLM(nn.Module):
    """Trainable bidirectional Transformer encoder with a token-classification head."""

    def __init__(self, config: ModelConfig):
        super().__init__()
        config.validate()
        self.config = config
        self.token_embedding = nn.Embedding(config.vocab_size, config.d_model, padding_idx=0)
        self.position_embedding = nn.Embedding(config.max_len, config.d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.num_heads,
            dim_feedforward=config.ff_dim,
            batch_first=True,
            dropout=0.0,
            activation="gelu",
            norm_first=False,
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=config.num_layers,
                                              enable_nested_tensor=False)
        self.layer_norm = nn.LayerNorm(config.d_model)
        self.mlm_head = nn.Linear(config.d_model, config.vocab_size)

    def forward(self, input_ids: Tensor, attention_mask: Tensor | None = None) -> Tensor:
        if input_ids.ndim != 2 or input_ids.size(1) > self.config.max_len:
            raise ValueError("expected batched token IDs inside configured max_len")
        if input_ids.dtype != torch.long:
            raise TypeError("input_ids must have dtype torch.long")
        if attention_mask is None:
            attention_mask = input_ids.ne(0)
        positions = torch.arange(input_ids.size(1), device=input_ids.device).unsqueeze(0)
        features = self.token_embedding(input_ids) + self.position_embedding(positions)
        states = self.encoder(features, src_key_padding_mask=~attention_mask.bool())
        return self.mlm_head(self.layer_norm(states))


def _padded(lines: Sequence[str], tokenizer: WordTokenizer, max_len: int) -> Tensor:
    sequences = [tokenizer.encode(line, max_len) for line in lines]
    max_tokens = max(len(row) for row in sequences)
    return torch.tensor([row + [0] * (max_tokens - len(row)) for row in sequences],
                        dtype=torch.long)


def mask_batch(
    original: Tensor,
    *,
    vocab_size: int,
    rng: random.Random,
    probability: float = 0.20,
) -> tuple[Tensor, Tensor]:
    """BERT-style 80/10/10 dynamic masking, with >=1 target per eligible row."""
    if original.ndim != 2 or original.dtype != torch.long:
        raise ValueError("original token batch must be 2-D torch.long")
    if not 0 < probability <= 1:
        raise ValueError("mask probability must be in (0, 1]")
    if vocab_size <= len(SPECIAL):
        raise ValueError("no non-special vocabulary tokens")
    inputs = original.clone()
    targets = torch.full_like(original, -100)
    for row in range(original.size(0)):
        eligible = [i for i in range(original.size(1)) if int(original[row, i]) >= len(SPECIAL)]
        if not eligible:
            continue
        selected = [i for i in eligible if rng.random() < probability]
        if not selected:
            selected = [rng.choice(eligible)]
        for position in selected:
            targets[row, position] = original[row, position]
            chance = rng.random()
            if chance < 0.8:
                inputs[row, position] = 2  # MASK
            elif chance < 0.9:
                inputs[row, position] = rng.randrange(len(SPECIAL), vocab_size)
    return inputs, targets


def _sha256(filename: Path) -> str:
    digest = hashlib.sha256()
    with filename.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_corpus(filename: Path) -> list[str]:
    if not filename.is_file() or filename.stat().st_size > 8_000_000:
        raise ValueError("corpus must be an existing UTF-8 file no larger than 8 MB")
    lines = [line.strip() for line in filename.read_text(encoding="utf-8").splitlines()]
    lines = [line for line in lines if len(tokenize(line)) >= 3]
    if len(lines) < 8:
        raise ValueError("at least eight lines containing three or more tokens are required")
    return lines


def train_model(
    corpus: str | Path,
    destination: str | Path,
    *,
    epochs: int = 6,
    batch_size: int = 12,
    learning_rate: float = 0.003,
    max_vocab: int = 256,
    max_len: int = 48,
    d_model: int = 48,
    num_heads: int = 4,
    num_layers: int = 2,
    ff_dim: int = 96,
    seed: int = 42,
) -> dict[str, Any]:
    """Train in the local process; checkpoint model weights and source provenance."""
    from ai_killswitch import require_ai_allowed
    require_ai_allowed("GPT-Almighty-Sonoxo MLM training")
    if not 1 <= epochs <= 50 or not 1 <= batch_size <= 256:
        raise ValueError("epochs or batch_size out of range")
    if not 0 < learning_rate <= 0.01:
        raise ValueError("invalid learning rate")
    source = Path(corpus)
    lines = _read_corpus(source)
    rng = random.Random(seed)
    indices = list(range(len(lines)))
    rng.shuffle(indices)
    pivot = max(1, len(lines) // 5)
    val_lines = [lines[i] for i in indices[:pivot]]
    train_lines = [lines[i] for i in indices[pivot:]]
    tokenizer = WordTokenizer.fit(train_lines, max_vocab=max_vocab)
    config = ModelConfig(len(tokenizer.vocab), max_len, d_model,
                         num_heads, num_layers, ff_dim)
    config.validate()
    torch.manual_seed(seed)
    model = AlmightySonoxoMLM(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=learning_rate)
    train_history: list[float] = []
    validation_history: list[float] = []

    for epoch in range(epochs):
        require_ai_allowed("GPT-Almighty-Sonoxo MLM training epoch")
        order = list(range(len(train_lines)))
        rng.shuffle(order)
        model.train()
        sum_loss = 0.0
        batches = 0
        for first in range(0, len(order), batch_size):
            require_ai_allowed("GPT-Almighty-Sonoxo MLM training batch")
            batch = _padded([train_lines[i] for i in order[first:first + batch_size]],
                            tokenizer, max_len)
            masked, targets = mask_batch(batch, vocab_size=config.vocab_size, rng=rng)
            if not targets.ne(-100).any():
                continue
            logits = model(masked)
            loss = F.cross_entropy(logits.reshape(-1, config.vocab_size), targets.reshape(-1),
                                   ignore_index=-100)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            sum_loss += float(loss.detach())
            batches += 1
        train_history.append(round(sum_loss / max(1, batches), 5))

        model.eval()
        sum_val, val_batches = 0.0, 0
        # Fixed per-epoch validation seed makes masked examples reproducible.
        val_rng = random.Random(seed + 1)
        with torch.no_grad():
            for start in range(0, len(val_lines), batch_size):
                batch = _padded(val_lines[start:start + batch_size], tokenizer, max_len)
                masked, targets = mask_batch(batch, vocab_size=config.vocab_size, rng=val_rng)
                if not targets.ne(-100).any():
                    continue
                logits = model(masked)
                loss = F.cross_entropy(logits.reshape(-1, config.vocab_size), targets.reshape(-1),
                                       ignore_index=-100)
                sum_val += float(loss.detach())
                val_batches += 1
        validation_history.append(round(sum_val / max(1, val_batches), 5))

    from safetensors.torch import save_file
    target = Path(destination)
    target.mkdir(parents=True, exist_ok=True)
    weights_path = target / "model.safetensors"
    manifest_path = target / "manifest.json"
    with tempfile.NamedTemporaryFile(dir=target, prefix=".model-", suffix=".safetensors",
                                     delete=False) as scratch:
        temp_path = Path(scratch.name)
    try:
        save_file({key: value.detach().contiguous().cpu()
                   for key, value in model.state_dict().items()}, str(temp_path))
        os.replace(temp_path, weights_path)
    finally:
        temp_path.unlink(missing_ok=True)
    payload: dict[str, Any] = {
        "schema": "sonoxo.al-mighty-mlm.v1",
        "model_id": MODEL_ID,
        "objective": "bidirectional-masked-language-modeling",
        "status": "locally-trained-research-prototype",
        "format_version": FORMAT_VERSION,
        "config": asdict(config),
        "vocab": tokenizer.vocab,
        "corpus_sha256": _sha256(source),
        "weights_sha256": _sha256(weights_path),
        "training": {
            "seed": seed,
            "epochs": epochs,
            "examples": len(train_lines),
            "held_out_examples": len(val_lines),
            "parameters": sum(parameter.numel() for parameter in model.parameters()),
            "train_loss": train_history,
            "validation_loss": validation_history,
        },
        "limitations": [
            "trained only on the supplied local text",
            "masked-token prediction, not instruction-following chat",
            "not pretrained, AGI, superintelligence or a biological device",
            "no autonomous data collection or self-modification",
        ],
    }
    with tempfile.NamedTemporaryFile(dir=target, prefix=".manifest-", suffix=".json",
                                     mode="w", encoding="utf-8", delete=False) as scratch:
        tmp_manifest = Path(scratch.name)
        json.dump(payload, scratch, indent=2, ensure_ascii=False, allow_nan=False)
    os.replace(tmp_manifest, manifest_path)
    return payload


def load_model(destination: str | Path) -> tuple[AlmightySonoxoMLM, WordTokenizer, dict[str, Any]]:
    """Validate and load *weights-only*, avoiding pickle deserialization."""
    from ai_killswitch import require_ai_allowed
    require_ai_allowed("GPT-Almighty-Sonoxo MLM checkpoint load")
    from safetensors.torch import load_file
    folder = Path(destination)
    manifest_path = folder / "manifest.json"
    weights_path = folder / "model.safetensors"
    if not manifest_path.is_file() or manifest_path.stat().st_size > 2_000_000:
        raise ValueError("missing or oversize manifest")
    if not weights_path.is_file() or weights_path.stat().st_size > 250_000_000:
        raise ValueError("missing or oversize checkpoint")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("model_id") != MODEL_ID or payload.get("format_version") != FORMAT_VERSION:
        raise ValueError("incompatible model manifest")
    config = ModelConfig(**payload["config"])
    config.validate()
    tokenizer = WordTokenizer(payload["vocab"])
    if config.vocab_size != len(tokenizer.vocab):
        raise ValueError("vocabulary/model mismatch")
    if payload.get("weights_sha256") != _sha256(weights_path):
        raise ValueError("checkpoint digest mismatch")
    model = AlmightySonoxoMLM(config)
    state = load_file(str(weights_path), device="cpu")
    model.load_state_dict(state, strict=True)
    model.eval()
    return model, tokenizer, payload


def fill_mask(
    model: AlmightySonoxoMLM,
    tokenizer: WordTokenizer,
    sentence: str,
    top_k: int = 5,
) -> dict[str, Any]:
    """Predict a token at exactly one [MASK] position; never emit chat claims."""
    from ai_killswitch import require_ai_allowed
    require_ai_allowed("GPT-Almighty-Sonoxo MLM inference")
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be in 1..20")
    if tokenize(sentence).count(MASK) != 1:
        raise ValueError("sentence must contain exactly one [MASK] token")
    ids = tokenizer.encode(sentence, model.config.max_len)
    if tokenizer.ids[MASK] not in ids:
        raise ValueError("mask was truncated by max_len")
    tensor = torch.tensor([ids], dtype=torch.long)
    with torch.no_grad():
        logits = model(tensor)[0, ids.index(tokenizer.ids[MASK])]
        logits = logits.clone()
        logits[:len(SPECIAL)] = -float("inf")
        probabilities = torch.softmax(logits, dim=-1)
        values, indices = probabilities.topk(min(top_k, model.config.vocab_size - len(SPECIAL)))
    return {
        "model_id": MODEL_ID,
        "input": sentence,
        "candidates": [
            {"token": tokenizer.vocab[int(i)], "probability": round(float(p), 6)}
            for p, i in zip(values, indices)
        ],
        "task": "masked-token prediction",
        "source": "trained-local-weights",
    }


def register_as_provider(
    registry: Any,
    model: AlmightySonoxoMLM,
    tokenizer: WordTokenizer,
) -> str:
    """Opt-in integration with GPT-Doug's existing ProviderRegistry interface.

    The review/propose methods return token-completion suggestions only. This
    model cannot replace a text-generating conversation model in the council.
    """
    from gpt_doug_mlm.providers import CallableProvider

    def evaluate(text: str) -> str:
        if MASK not in tokenize(text):
            return "masked-language-model only: include exactly one [MASK]"
        outcome = fill_mask(model, tokenizer, text, top_k=5)
        return json.dumps(outcome, sort_keys=True)

    registry.register(CallableProvider(name=MODEL_ID, propose_fn=evaluate, review_fn=evaluate))
    return MODEL_ID
