#!/usr/bin/env python3
"""Guarded integration boundary for Devin Enterprise.

This initial adapter intentionally does not make network requests. Confirm the
current Devin API endpoint, schema, and authentication requirements, then add
an approved transport implementation and tests before enabling submission.
"""
import argparse
import json
import os
import sys


def build_request(title: str, prompt: str) -> dict:
    if not os.environ.get("DEVIN_API_KEY"):
        raise ValueError("DEVIN_API_KEY is required; no request was sent.")
    if not title.strip() or not prompt.strip():
        raise ValueError("Title and prompt must not be empty.")
    return {
        "status": "prepared_not_sent",
        "provider": "devin-enterprise",
        "title": title.strip(),
        "prompt": prompt.strip(),
        "message": "Request prepared only. Verify the current Devin API contract before implementing transport."
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--title", required=True)
    parser.add_argument("--prompt", required=True)
    args = parser.parse_args()
    try:
        result = build_request(args.title, args.prompt)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
