#!/usr/bin/env python3
"""Run GPT-Doug through the Anthropic Mythos provider profile."""

from __future__ import annotations

import argparse
import json

from agents.mythos_bridge import MythosProvider


def main() -> None:
    parser = argparse.ArgumentParser(prog="mythos-doug")
    parser.add_argument("prompt", nargs="?")
    parser.add_argument("--health", action="store_true")
    parser.add_argument("--max-tokens", type=int, default=4096)
    parser.add_argument("--temperature", type=float, default=0.7)
    args = parser.parse_args()

    provider = MythosProvider()
    if args.health:
        print(json.dumps(provider.health(), indent=2))
        return

    if not args.prompt:
        parser.error("prompt is required unless --health is used")

    result = provider.chat_once(
        [{"role": "user", "content": args.prompt}],
        None,
        {
            "max_tokens": args.max_tokens,
            "temperature": args.temperature,
        },
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
