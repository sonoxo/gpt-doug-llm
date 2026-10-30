"""Operator-owned CLI for GPT-Delta: train, evaluate, predict and rollback."""
from __future__ import annotations

import argparse
import json
from typing import Any


def _write(obj: Any) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False))


def parser_factory() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpt-delta", description="Local GPT-Delta MLM and evidence change layer")
    sub = parser.add_subparsers(dest="command", required=True)
    train = sub.add_parser("train", help="train a frozen-base low-rank candidate")
    train.add_argument("--base", required=True)
    train.add_argument("--corpus", required=True)
    train.add_argument("--replay", help="old-data retention corpus (required for promotion)")
    train.add_argument("--output", required=True)
    train.add_argument("--epochs", type=int, default=12)
    train.add_argument("--rank", type=int, default=8)
    train.add_argument("--alpha", type=float, default=8)
    train.add_argument("--learning-rate", type=float, default=0.02)
    train.add_argument("--min-gain", type=float, default=0.001)
    train.add_argument("--max-regression", type=float, default=0.08)
    pred = sub.add_parser("predict", help="one masked-token prediction from a candidate")
    pred.add_argument("--base", required=True)
    pred.add_argument("--candidate", required=True)
    pred.add_argument("--text", required=True)
    pred.add_argument("--top-k", type=int, default=5)
    inspect = sub.add_parser("inspect", help="verify parent + candidate checkpoint and report metrics")
    inspect.add_argument("--base", required=True)
    inspect.add_argument("--candidate", required=True)
    promote = sub.add_parser("promote", help="manually approve eligible, evaluated local pointer")
    promote.add_argument("--base", required=True)
    promote.add_argument("--candidate", required=True)
    promote.add_argument("--registry", required=True)
    promote.add_argument("--corpus", required=True)
    promote.add_argument("--replay", required=True)
    promote.add_argument("--approve", action="store_true")
    rollback = sub.add_parser("rollback", help="operator rollback of active local pointer")
    rollback.add_argument("--registry", required=True)
    rollback.add_argument("--approve", action="store_true")
    event = sub.add_parser("observe", help="record source-backed ontology status change")
    event.add_argument("--database", required=True)
    event.add_argument("--subject", required=True)
    event.add_argument("--predicate", required=True)
    event.add_argument("--value", required=True)
    event.add_argument("--source-id", required=True)
    event.add_argument("--source-uri", required=True)
    event.add_argument("--observed-at")
    event.add_argument("--confidence", type=float, default=0.5)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = parser_factory().parse_args(argv)
    try:
        if args.command == "observe":
            from gpt_doug_mlm.delta_evidence import observe_change
            _write(observe_change(database=args.database, subject=args.subject,
                                  predicate=args.predicate, value=args.value,
                                  source_id=args.source_id, source_uri=args.source_uri,
                                  observed_at=args.observed_at, confidence=args.confidence))
        else:
            from gpt_doug_mlm.delta import (
                fill_delta, load_delta, promote_delta, rollback_delta, train_delta,
            )
            if args.command == "train":
                result = train_delta(args.base, args.corpus, args.output,
                                     replay=args.replay, epochs=args.epochs, rank=args.rank,
                                     alpha=args.alpha, learning_rate=args.learning_rate,
                                     min_gain=args.min_gain,
                                     max_regression=args.max_regression)
            elif args.command == "predict":
                result = fill_delta(args.base, args.candidate, args.text, args.top_k)
            elif args.command == "inspect":
                _, _, manifest = load_delta(args.base, args.candidate)
                result = {"model_id": manifest["model_id"], "weights_verified": True,
                          "parent_weights_sha256": manifest["parent_weights_sha256"],
                          "status": manifest["status"], "evaluation": manifest["evaluation"],
                          "trainable_parameters": manifest["training"]["adapter_parameters"]}
            elif args.command == "promote":
                result = promote_delta(args.base, args.candidate, args.registry,
                                       corpus=args.corpus, replay=args.replay, approve=args.approve)
            else:
                result = rollback_delta(args.registry, approve=args.approve)
            _write(result)
        return 0
    except (OSError, ValueError, TypeError, PermissionError, RuntimeError, ImportError, KeyError) as exc:
        _write({"ok": False, "error": type(exc).__name__, "message": str(exc)})
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
