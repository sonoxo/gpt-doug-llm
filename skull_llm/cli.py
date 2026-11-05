"""Terminal entrypoint for SKULL-LLM."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
import urllib.parse

from .runtime import SkullConfig, SkullEngine


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="skull-llm", description="GPT-DOUG local neural intelligence")
    cmds = root.add_subparsers(dest="command", required=True)
    ask = cmds.add_parser("ask", help="run local Ollama reasoning with ontology and memory")
    ask.add_argument("task", nargs="+")
    ask.add_argument("--model", default=os.environ.get("SKULL_MODEL"))
    ask.add_argument("--depth", type=int, choices=[1, 2, 3], default=2)
    ask.add_argument("--remember", action="store_true", help="opt in to writing episodic memory")
    ask.add_argument("--json", action="store_true", dest="as_json")
    cmds.add_parser("doctor", help="inspect dependency and Ollama readiness")
    train = cmds.add_parser("train", help="train a small byte-level Transformer from local text")
    train.add_argument("corpus", help="authorized local UTF-8 text file")
    train.add_argument("--out", default="skull-local.pt")
    train.add_argument("--steps", type=int, default=100)
    train.add_argument("--batch-size", type=int, default=8)
    train.add_argument("--context", type=int, default=128)
    train.add_argument("--dim", type=int, default=128)
    train.add_argument("--layers", type=int, default=2)
    train.add_argument("--heads", type=int, default=4)
    train.add_argument("--lr", type=float, default=3e-4)
    train.add_argument("--seed", type=int, default=42)
    sample = cmds.add_parser("sample", help="sample a locally trained checkpoint")
    sample.add_argument("checkpoint")
    sample.add_argument("prompt")
    sample.add_argument("--tokens", type=int, default=80)
    sample.add_argument("--temperature", type=float, default=0.8)
    sample.add_argument("--top-k", type=int, default=40)
    return root


def doctor() -> dict:
    from ai_killswitch import status as stop_status
    from agents.llm_backend import OllamaProvider

    url = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    parsed = urllib.parse.urlsplit(url)
    local = (
        parsed.scheme == "http"
        and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        and parsed.username is None
        and parsed.password is None
        and parsed.path in {"", "/"}
        and not parsed.query and not parsed.fragment
    )
    state = OllamaProvider().health() if local else {
        "configured": False, "model_available": False,
        "message": "Non-loopback endpoint rejected",
    }
    stopped = bool(stop_status().get("stopped"))
    return {
        "project": "SKULL-LLM", "local_only": True, "stopped": stopped,
        "ollama": state, "pytorch_installed": importlib.util.find_spec("torch") is not None,
        "ready_for_inference": bool(
            not stopped and local and state.get("configured") and state.get("model_available")
        ),
        "neural_checkpoint_pretrained": False,
    }


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "doctor":
            print(json.dumps(doctor(), indent=2))
            return 0
        if args.command == "ask":
            config = SkullConfig(model=args.model, depth=args.depth, remember=args.remember)
            result = SkullEngine(config=config).run(" ".join(args.task))
            print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) if args.as_json
                  else result.answer)
            return 0
        if args.command == "train":
            from .train import train_file

            result = train_file(
                args.corpus, args.out, steps=args.steps, batch_size=args.batch_size,
                context=args.context, dim=args.dim, layers=args.layers,
                heads=args.heads, learning_rate=args.lr, seed=args.seed,
            )
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "sample":
            from .train import sample_file

            print(sample_file(
                args.checkpoint, args.prompt, new_tokens=args.tokens,
                temperature=args.temperature, top_k=args.top_k,
            ))
            return 0
    except (OSError, RuntimeError, ValueError, ImportError) as exc:
        print(json.dumps({"ok": False, "error": type(exc).__name__,
                          "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    return 2
