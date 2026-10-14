"""Local-first Sonoxo S-Brain CLI over the durable ontology/evidence engine."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional, Sequence

from .s_brain import Evidence, SBrain


def parser_factory() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="gpt-sonoxo-s-brain", description=(
        "Offline evidence brain + opt-in model inference; actual SAGIQI MLM weights supported"
    ))
    parser.add_argument("--db", default=None, help="local SQLite knowledge store")
    parser.add_argument("--ontology", default=None, help="optional local ontology JSON file")
    sub = parser.add_subparsers(dest="command", required=True)

    remember = sub.add_parser("remember", help="explicitly record a source-attributed statement")
    remember.add_argument("--subject", required=True)
    remember.add_argument("--predicate", required=True)
    remember.add_argument("--value", required=True)
    remember.add_argument("--source-id", required=True)
    remember.add_argument("--source-uri", required=True)
    remember.add_argument("--observed-at", default=None, help="ISO-8601 with timezone")
    remember.add_argument("--confidence", type=float, default=0.5,
                          help="caller assessment, not independent verification")

    ask = sub.add_parser("ask", help="ontology-first, evidence-only retrieval")
    ask.add_argument("question")
    ask.add_argument("--limit", type=int, default=8)
    ask.add_argument("--live", action="store_true", help="opt-in generative model synthesis")
    ask.add_argument("--model", default=None, help="optional configured model name")

    council = sub.add_parser("council", help="registered local Ollama model comparisons")
    council.add_argument("question")
    council.add_argument("--models", required=True, help="1-4 locally installed model IDs")
    council.add_argument("--reviewers", default="", help="optional local review models")

    mask = sub.add_parser("fill-mask", help="predict one token with trained neural weights")
    mask.add_argument("--checkpoint", required=True)
    mask.add_argument("--text", required=True, help="must contain exactly one [MASK]")
    mask.add_argument("--top-k", type=int, default=5)

    sub.add_parser("heartbeat", help="verify local SQLite integrity and uncertainty")
    sub.add_parser("status", help="show local readiness without calling a remote model")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parser_factory().parse_args(argv)
    try:
        ontology = None
        if args.ontology:
            from .ontology import OntologyIndex
            ontology = OntologyIndex(args.ontology)
        with SBrain(database=args.db, ontology=ontology) as brain:
            if args.command == "remember":
                output = brain.remember(Evidence(
                    subject=args.subject, predicate=args.predicate, value=args.value,
                    source_id=args.source_id, source_uri=args.source_uri,
                    observed_at=args.observed_at, confidence=args.confidence,
                ))
            elif args.command == "ask":
                output = (brain.ask_live(args.question, model=args.model) if args.live
                          else brain.query(args.question, limit=args.limit))
            elif args.command == "fill-mask":
                output = brain.fill_mask(args.checkpoint, args.text, top_k=args.top_k)
            elif args.command == "council":
                from gpt_doug_mlm.almighty_ensemble import register_local_ollama
                from gpt_doug_mlm.providers import ProviderRegistry
                models = [x.strip() for x in args.models.split(",") if x.strip()]
                reviewers = [x.strip() for x in args.reviewers.split(",") if x.strip()]
                registry = ProviderRegistry()
                register_local_ollama(registry, list(dict.fromkeys([*models, *reviewers])))
                output = brain.council(args.question, proposers=models,
                                       reviewers=reviewers, registry=registry)
            else:
                output = brain.heartbeat()
                if args.command == "status":
                    output["mode"] = "offline-first"
                    output["capabilities"] = [
                        "source-attributed SQLite memory", "ontology-first recall",
                        "evidence conflict and transition flags", "opt-in SAGIQI model",
                        "explicitly registered model council", "local heartbeat",
                    ]
        print(json.dumps(output, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (OSError, ValueError, TypeError, RuntimeError, KeyError, ImportError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__,
                          "message": str(exc)[:400]}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
