"""Run actual local GPT-Almighty-Sonoxo-MLM-SAGIQI model training/inference."""
from __future__ import annotations

import argparse
import json


def parser_factory() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gpt-almighty-sonoxo-mlm",
        description="Real trainable masked Transformer; offline and checkpointed",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    train = sub.add_parser("train", help="train an actual masked LM on a local text corpus")
    train.add_argument("--corpus", required=True, help="UTF-8 file with >=8 text lines")
    train.add_argument("--output", required=True, help="checkpoint directory")
    train.add_argument("--epochs", type=int, default=6)
    train.add_argument("--batch-size", type=int, default=12)
    train.add_argument("--vocab-size", type=int, default=256)
    train.add_argument("--sequence-length", type=int, default=48)
    train.add_argument("--dimension", type=int, default=48)
    train.add_argument("--layers", type=int, default=2)
    train.add_argument("--heads", type=int, default=4)
    train.add_argument("--seed", type=int, default=42)

    predict = sub.add_parser("fill-mask", help="infer trained weights, no model download")
    predict.add_argument("--model", required=True, help="directory with .safetensors + manifest")
    predict.add_argument("--text", required=True, help="sentence with exactly one [MASK]")
    predict.add_argument("--top-k", type=int, default=5)

    inspect = sub.add_parser("inspect", help="verify checksum and report checkpoint metadata")
    inspect.add_argument("--model", required=True)

    council = sub.add_parser("council", help="run explicitly selected, locally installed Ollama models")
    council.add_argument("--task", required=True)
    council.add_argument("--models", required=True, help="comma-separated exact installed Ollama model IDs")
    council.add_argument("--reviewers", default="", help="optional comma-separated local reviewer models")
    council.add_argument("--evidence-json", default=None, help="local JSON array of {source_id,content,provenance}")
    return parser


def main(argv: list[str] | None = None) -> int:
    options = parser_factory().parse_args(argv)
    try:
        from gpt_doug_mlm.almighty_sonoxo import fill_mask, load_model, train_model
        if options.command == "council":
            from pathlib import Path
            from gpt_doug_mlm.almighty_ensemble import (
                Source, SonoxoModelCouncil, register_local_ollama,
            )
            from gpt_doug_mlm.providers import ProviderRegistry
            proposers = [name.strip() for name in options.models.split(",") if name.strip()]
            reviewers = [name.strip() for name in options.reviewers.split(",") if name.strip()]
            evidence = []
            if options.evidence_json:
                file = Path(options.evidence_json)
                if not file.is_file() or file.stat().st_size > 500000:
                    raise ValueError("evidence must be local JSON below 500KB")
                data = json.loads(file.read_text(encoding="utf-8"))
                if not isinstance(data, list):
                    raise ValueError("evidence must be a JSON array")
                evidence = [Source(**row) for row in data]
            registry = ProviderRegistry()
            register_local_ollama(registry, list(dict.fromkeys([*proposers, *reviewers])))
            result = SonoxoModelCouncil(registry).evaluate(
                options.task, proposer_models=proposers,
                reviewer_models=reviewers, evidence=evidence,
            )
        elif options.command == "train":
            result = train_model(
                options.corpus,
                options.output,
                epochs=options.epochs,
                batch_size=options.batch_size,
                max_vocab=options.vocab_size,
                max_len=options.sequence_length,
                d_model=options.dimension,
                num_layers=options.layers,
                num_heads=options.heads,
                ff_dim=options.dimension * 2,
                seed=options.seed,
            )
        elif options.command == "fill-mask":
            model, tokenizer, _ = load_model(options.model)
            result = fill_mask(model, tokenizer, options.text, top_k=options.top_k)
        else:
            model, tokenizer, manifest = load_model(options.model)
            result = {
                "model_id": manifest["model_id"],
                "status": manifest["status"],
                "checkpoint_verified": True,
                "parameter_count": manifest["training"]["parameters"],
                "vocab_size": len(tokenizer.vocab),
                "layers": model.config.num_layers,
                "training": manifest["training"],
                "limitations": manifest["limitations"],
            }
        print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ImportError, RuntimeError, ValueError, TypeError, KeyError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__, "message": str(exc)}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
