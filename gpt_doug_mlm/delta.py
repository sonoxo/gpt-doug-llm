"""GPT-Delta: reversible, parameter-efficient adaptation of SAGIQI's real MLM.

Only a low-rank output residual learns. The parent model is frozen, its
safetensors checkpoint is hash-verified, and a new candidate is NOT activated
until a human explicitly approves measured hold-out + replay safeguards.
No autonomous code changes, downloading, telemetry, physical I/O or remote use.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import random
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Sequence

import torch
from torch import Tensor, nn
from torch.nn import functional as F

from ai_killswitch import require_ai_allowed
from gpt_doug_mlm.almighty_sonoxo import (
    MASK, SPECIAL, AlmightySonoxoMLM, WordTokenizer, _read_corpus,
    _sha256, load_model, mask_batch, tokenize,
)

DELTA_MODEL_ID = "gpt-delta-mlm-sagiqi"
SCHEMA = "sonoxo.delta-mlm.v1"
MAX_ADAPTER_BYTES = 40_000_000
MAX_RANK = 32


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json_atomic(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise ValueError("refusing symlinked output")
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".delta-", suffix=".json",
                                     mode="w", encoding="utf-8", delete=False) as stream:
        scratch = Path(stream.name)
        json.dump(obj, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        os.replace(scratch, path)
    finally:
        scratch.unlink(missing_ok=True)


@dataclass(frozen=True)
class DeltaConfig:
    rank: int = 8
    alpha: float = 8.0

    def validate(self, d_model: int, vocab_size: int) -> None:
        if not isinstance(self.rank, int) or not 1 <= self.rank <= min(MAX_RANK, d_model):
            raise ValueError("rank must be between 1 and 32 and <= model dimension")
        if not isinstance(self.alpha, (int, float)) or not math.isfinite(self.alpha):
            raise ValueError("alpha must be finite")
        if not 0 < self.alpha <= 64:
            raise ValueError("alpha must be between 0 and 64")
        if vocab_size < 6:
            raise ValueError("missing model vocabulary")


class DeltaAdapter(nn.Module):
    """Frozen bidirectional Transformer plus a trainable low-rank logits update."""

    def __init__(self, parent: AlmightySonoxoMLM, config: DeltaConfig):
        super().__init__()
        config.validate(parent.config.d_model, parent.config.vocab_size)
        self.parent = parent.eval()
        for parameter in self.parent.parameters():
            parameter.requires_grad_(False)
        self.down = nn.Linear(parent.config.d_model, config.rank, bias=False)
        self.up = nn.Linear(config.rank, parent.config.vocab_size, bias=False)
        self.config = config
        # Identity at initialization: adapter does not change parent output.
        nn.init.normal_(self.down.weight, mean=0.0, std=0.02)
        nn.init.zeros_(self.up.weight)

    def adapter_parameters(self):
        return list(self.down.parameters()) + list(self.up.parameters())

    def forward(self, input_ids: Tensor, attention_mask: Optional[Tensor] = None) -> Tensor:
        if input_ids.ndim != 2 or input_ids.dtype != torch.long:
            raise ValueError("input IDs must be a batch of torch.long token IDs")
        if input_ids.size(1) > self.parent.config.max_len or input_ids.size(1) < 2:
            raise ValueError("input length outside configured context")
        if attention_mask is None:
            attention_mask = input_ids.ne(0)
        with torch.no_grad():
            positions = torch.arange(input_ids.size(1), device=input_ids.device).unsqueeze(0)
            embeddings = self.parent.token_embedding(input_ids) + self.parent.position_embedding(positions)
            encoded = self.parent.encoder(embeddings, src_key_padding_mask=~attention_mask.bool())
            features = self.parent.layer_norm(encoded)
            parent_logits = self.parent.mlm_head(features)
        return parent_logits + self.up(self.down(features)) * (self.config.alpha / self.config.rank)


def _tensorize(lines: Sequence[str], tokenizer: WordTokenizer, length: int) -> Tensor:
    sequences = [tokenizer.encode(line, length) for line in lines]
    width = max(len(ids) for ids in sequences)
    return torch.tensor([ids + [0] * (width - len(ids)) for ids in sequences], dtype=torch.long)


def _score(model: DeltaAdapter, texts: Sequence[str], tokenizer: WordTokenizer,
           seed: int, batch_size: int = 16) -> float:
    if not texts:
        raise ValueError("evaluation requires non-empty text")
    model.eval()
    rng = random.Random(seed)
    total, token_count = 0.0, 0
    with torch.no_grad():
        for pos in range(0, len(texts), batch_size):
            sample = _tensorize(texts[pos:pos + batch_size], tokenizer,
                                model.parent.config.max_len)
            masked, labels = mask_batch(sample, vocab_size=model.parent.config.vocab_size,
                                        rng=rng, probability=0.30)
            targets = int(labels.ne(-100).sum())
            if targets == 0:
                continue
            logits = model(masked)
            sum_loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1),
                                       ignore_index=-100, reduction="sum")
            total += float(sum_loss)
            token_count += targets
    if not token_count:
        raise ValueError("evaluation contains no in-vocabulary masked tokens")
    return round(total / token_count, 6)


def _unknown_ratio(rows: Sequence[str], tokenizer: WordTokenizer) -> float:
    tokens = [x for line in rows for x in tokenize(line) if x not in SPECIAL]
    if not tokens:
        return 1.0
    return round(sum(x not in tokenizer.ids for x in tokens) / len(tokens), 6)


def train_delta(
    base_dir: str | Path, corpus: str | Path, output_dir: str | Path, *,
    replay: Optional[str | Path] = None, epochs: int = 12, batch_size: int = 12,
    rank: int = 8, alpha: float = 8.0, learning_rate: float = 0.02,
    min_gain: float = 0.001, max_regression: float = 0.08,
    max_unknown_ratio: float = 0.15, seed: int = 2026,
) -> dict[str, Any]:
    """Train candidate weights only; benchmark gains, never auto-activate."""
    require_ai_allowed("GPT-Delta start adaptation")
    if not 1 <= epochs <= 60 or not 1 <= batch_size <= 128:
        raise ValueError("invalid bounded training configuration")
    if not 0 < learning_rate <= 0.1:
        raise ValueError("learning rate must be in (0,0.1]")
    if not 0 <= min_gain <= 5 or not 0 <= max_regression <= 5:
        raise ValueError("invalid evaluation thresholds")
    if not 0 <= max_unknown_ratio <= 1:
        raise ValueError("invalid OOV threshold")
    root = Path(base_dir)
    destination = Path(output_dir)
    if root.resolve() == destination.resolve():
        raise ValueError("adapter output must not overwrite parent checkpoint")
    parent, tokenizer, parent_manifest = load_model(root)
    config = DeltaConfig(rank, alpha)
    adapter = DeltaAdapter(parent, config)
    lines = _read_corpus(Path(corpus))
    rng = random.Random(seed)
    order = list(range(len(lines)))
    rng.shuffle(order)
    valid_count = max(2, len(lines) // 5)
    held_out = [lines[i] for i in order[:valid_count]]
    train_lines = [lines[i] for i in order[valid_count:]]
    replay_lines = _read_corpus(Path(replay)) if replay is not None else []
    unknown = _unknown_ratio(lines, tokenizer)
    parent_val = _score(adapter, held_out, tokenizer, seed + 10)
    parent_replay = _score(adapter, replay_lines, tokenizer, seed + 11) if replay_lines else None
    optimizer = torch.optim.AdamW(adapter.adapter_parameters(), lr=learning_rate,
                                  weight_decay=0.005)
    history = []
    torch.manual_seed(seed)
    for epoch in range(epochs):
        require_ai_allowed("GPT-Delta training epoch")
        indexes = list(range(len(train_lines)))
        rng.shuffle(indexes)
        adapter.train()
        step_loss, steps = 0.0, 0
        for first in range(0, len(indexes), batch_size):
            require_ai_allowed("GPT-Delta training batch")
            batch = _tensorize([train_lines[i] for i in indexes[first:first + batch_size]],
                               tokenizer, parent.config.max_len)
            inputs, labels = mask_batch(batch, vocab_size=parent.config.vocab_size,
                                        rng=rng, probability=0.30)
            if not labels.ne(-100).any():
                continue
            logits = adapter(inputs)
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), labels.reshape(-1),
                                   ignore_index=-100)
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(adapter.adapter_parameters(), max_norm=1.0)
            optimizer.step()
            step_loss += float(loss.detach())
            steps += 1
        history.append(round(step_loss / max(steps, 1), 6))
    require_ai_allowed("GPT-Delta candidate evaluation")
    after_val = _score(adapter, held_out, tokenizer, seed + 10)
    after_replay = _score(adapter, replay_lines, tokenizer, seed + 11) if replay_lines else None
    gain = round(parent_val - after_val, 6)
    regression = round(after_replay - parent_replay, 6) if replay_lines else None
    source_digest = _sha256(Path(corpus))
    replay_digest = _sha256(Path(replay)) if replay is not None else None
    gates = {
        "held_out_gain": gain >= min_gain,
        "replay_provided": bool(replay_lines),
        "independent_replay": replay_digest is not None and replay_digest != source_digest,
        "replay_regression": regression is not None and regression <= max_regression,
        "vocabulary_coverage": unknown <= max_unknown_ratio,
    }
    require_ai_allowed("GPT-Delta candidate save")
    destination.mkdir(parents=True, exist_ok=True)
    if (destination / "adapter.safetensors").is_symlink():
        raise ValueError("refusing symlinked adapter checkpoint")
    from safetensors.torch import save_file
    with tempfile.NamedTemporaryFile(dir=destination, prefix=".delta-", suffix=".safetensors",
                                     delete=False) as stream:
        scratch = Path(stream.name)
    try:
        save_file({"down.weight": adapter.down.weight.detach().contiguous().cpu(),
                   "up.weight": adapter.up.weight.detach().contiguous().cpu()}, str(scratch))
        os.replace(scratch, destination / "adapter.safetensors")
    finally:
        scratch.unlink(missing_ok=True)
    payload = {
        "schema": SCHEMA,
        "model_id": DELTA_MODEL_ID,
        "parent_model_id": parent_manifest["model_id"],
        "parent_weights_sha256": parent_manifest["weights_sha256"],
        "adapter_weights_sha256": _sha256(destination / "adapter.safetensors"),
        "candidate_created_at": _now(),
        "status": "candidate-not-promoted",
        "configuration": asdict(config),
        "train_corpus_sha256": source_digest,
        "replay_corpus_sha256": replay_digest,
        "training": {
            "seed": seed, "epochs": epochs, "train_examples": len(train_lines),
            "held_out_examples": len(held_out), "replay_examples": len(replay_lines),
            "adapter_parameters": sum(p.numel() for p in adapter.adapter_parameters()),
            "loss_history": history,
        },
        "evaluation": {
            "parent_new_loss": parent_val, "delta_new_loss": after_val,
            "held_out_gain": gain, "parent_replay_loss": parent_replay,
            "delta_replay_loss": after_replay, "replay_regression": regression,
            "unknown_ratio": unknown, "min_gain": min_gain,
            "max_regression": max_regression, "max_unknown_ratio": max_unknown_ratio,
            "gates": gates, "eligible_for_review": all(gates.values()),
        },
        "limitations": [
            "small masked-token model, not a conversational LLM",
            "parent vocabulary is frozen: unseen words map to UNK",
            "hold-out/replay metrics are a local smoke test, not generalization proof",
            "no model promotion or external deployment without explicit operator action",
        ],
    }
    _json_atomic(destination / "manifest.json", payload)
    return payload


def load_delta(base_dir: str | Path, candidate_dir: str | Path) -> tuple[DeltaAdapter, WordTokenizer, dict[str, Any]]:
    """Verify parent+adapter hashes before loading weights-only candidate."""
    require_ai_allowed("GPT-Delta checkpoint load")
    parent, tokenizer, parent_manifest = load_model(base_dir)
    root = Path(candidate_dir)
    manifest_path = root / "manifest.json"
    weights = root / "adapter.safetensors"
    if not manifest_path.is_file() or manifest_path.stat().st_size > 1_000_000:
        raise ValueError("missing or oversize adapter manifest")
    if not weights.is_file() or weights.stat().st_size > MAX_ADAPTER_BYTES:
        raise ValueError("missing or oversize adapter checkpoint")
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA or payload.get("model_id") != DELTA_MODEL_ID:
        raise ValueError("unsupported GPT-Delta manifest")
    if payload.get("parent_weights_sha256") != parent_manifest.get("weights_sha256"):
        raise ValueError("parent checkpoint mismatch; adapter cannot be applied")
    if payload.get("adapter_weights_sha256") != _sha256(weights):
        raise ValueError("adapter digest mismatch")
    config = DeltaConfig(**payload["configuration"])
    delta = DeltaAdapter(parent, config)
    from safetensors.torch import load_file
    tensors = load_file(str(weights), device="cpu")
    if set(tensors) != {"down.weight", "up.weight"}:
        raise ValueError("unexpected adapter tensors")
    delta.down.load_state_dict({"weight": tensors["down.weight"]}, strict=True)
    delta.up.load_state_dict({"weight": tensors["up.weight"]}, strict=True)
    delta.eval()
    return delta, tokenizer, payload


def fill_delta(base_dir: str | Path, candidate_dir: str | Path, sentence: str,
               top_k: int = 5) -> dict[str, Any]:
    require_ai_allowed("GPT-Delta token prediction")
    model, tokenizer, manifest = load_delta(base_dir, candidate_dir)
    if not 1 <= top_k <= 20 or tokenize(sentence).count(MASK) != 1:
        raise ValueError("require one [MASK] and top_k 1..20")
    ids = tokenizer.encode(sentence, model.parent.config.max_len)
    mask_token = tokenizer.ids[MASK]
    if mask_token not in ids:
        raise ValueError("masked token truncated by context length")
    with torch.no_grad():
        logits = model(torch.tensor([ids], dtype=torch.long))[0, ids.index(mask_token)].clone()
        logits[:len(SPECIAL)] = -float("inf")
        probs = torch.softmax(logits, dim=-1)
        scores, indices = probs.topk(min(top_k, len(tokenizer.vocab) - len(SPECIAL)))
    return {
        "model_id": DELTA_MODEL_ID,
        "status": manifest["status"],
        "input": sentence,
        "candidates": [
            {"token": tokenizer.vocab[int(i)], "probability": round(float(p), 6)}
            for p, i in zip(scores, indices)
        ],
        "source": "verified-local-adapter-weights",
        "not_independently_verified": True,
    }


def promote_delta(base_dir: str | Path, candidate_dir: str | Path,
                  registry: str | Path, *, corpus: Optional[str | Path] = None,
                  replay: Optional[str | Path] = None, approve: bool = False) -> dict[str, Any]:
    """Operator-approved local pointer change only. No remote system is touched."""
    require_ai_allowed("GPT-Delta local promotion")
    if not approve:
        raise PermissionError("explicit --approve required for promotion")
    if corpus is None or replay is None:
        raise ValueError("promotion requires training corpus and independent replay corpus")
    model, tokenizer, manifest = load_delta(base_dir, candidate_dir)
    if (_sha256(Path(corpus)) != manifest["train_corpus_sha256"] or
            _sha256(Path(replay)) != manifest["replay_corpus_sha256"]):
        raise ValueError("evaluation corpora do not match candidate provenance")
    source_rows = _read_corpus(Path(corpus))
    replay_rows = _read_corpus(Path(replay))
    seed = int(manifest["training"]["seed"])
    positions = list(range(len(source_rows)))
    random.Random(seed).shuffle(positions)
    held_out = [source_rows[i] for i in positions[:max(2, len(source_rows) // 5)]]
    # Recalculate the two hold-out scores using the actual saved candidate weights.
    baseline = DeltaAdapter(model.parent, model.config)
    observed = {
        "parent_new_loss": _score(baseline, held_out, tokenizer, seed + 10),
        "delta_new_loss": _score(model, held_out, tokenizer, seed + 10),
        "parent_replay_loss": _score(baseline, replay_rows, tokenizer, seed + 11),
        "delta_replay_loss": _score(model, replay_rows, tokenizer, seed + 11),
        "unknown_ratio": _unknown_ratio(source_rows, tokenizer),
    }
    logged = manifest["evaluation"]
    if any(abs(observed[key] - float(logged[key])) > 0.001 for key in observed):
        raise ValueError("recorded evaluation metrics differ from actual checkpoints")
    independently_recomputed = (
        (observed["parent_new_loss"] - observed["delta_new_loss"] >= float(logged["min_gain"]))
        and (observed["delta_replay_loss"] - observed["parent_replay_loss"] <= float(logged["max_regression"]))
        and (observed["unknown_ratio"] <= float(logged["max_unknown_ratio"]))
        and manifest["train_corpus_sha256"] != manifest["replay_corpus_sha256"]
    )
    if not independently_recomputed:
        raise ValueError("independent promotion evaluation failed")
    if not manifest["evaluation"]["eligible_for_review"] or not all(
        manifest["evaluation"]["gates"].values()
    ):
        raise ValueError("evaluation gates failed; candidate cannot be promoted")
    registry_path = Path(registry)
    if registry_path.exists():
        prior = json.loads(registry_path.read_text(encoding="utf-8"))
        if prior.get("schema") != "sonoxo.delta-pointer.v1":
            raise ValueError("unsupported activation registry")
        history = list(prior.get("history", []))
        if len(history) > 25:
            history = history[-25:]
        old_active = prior.get("active_candidate")
    else:
        history = []
        old_active = None
    if old_active is not None:
        history.append(old_active)
    data = {
        "schema": "sonoxo.delta-pointer.v1",
        "active_candidate": str(Path(candidate_dir).resolve()),
        "parent_weights_sha256": manifest["parent_weights_sha256"],
        "adapter_weights_sha256": manifest["adapter_weights_sha256"],
        "approved_at": _now(),
        "operator_approved": True,
        "history": history[-25:],
        "deployment_performed": False,
    }
    _json_atomic(registry_path, data)
    return data


def rollback_delta(registry: str | Path, *, approve: bool = False) -> dict[str, Any]:
    require_ai_allowed("GPT-Delta local rollback")
    if not approve:
        raise PermissionError("explicit --approve required for rollback")
    path = Path(registry)
    if not path.is_file() or path.is_symlink():
        raise ValueError("missing or unsafe activation registry")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "sonoxo.delta-pointer.v1":
        raise ValueError("invalid pointer schema")
    history = data.get("history", [])
    data["active_candidate"] = history.pop() if history else None
    data["history"] = history
    data["approved_at"] = _now()
    data["deployment_performed"] = False
    _json_atomic(path, data)
    return data
