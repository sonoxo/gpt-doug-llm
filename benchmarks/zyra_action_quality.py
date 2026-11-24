#!/usr/bin/env python3
"""Deterministic reference benchmark for ZYRA's JSON action extraction.

Run from OUTSIDE the agent-editable repository: python3 evaluator.py /repo/root
This is a public reference benchmark, not a secret held-out benchmark. Operators
should supplement it with private independently curated cases before claims.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

CASES = [
    ('{"action":"finish"}', 'finish'),
    ('  {"action": "read_file", "path": "tests/a.py"}\n', 'read_file'),
    ('```json\n{"action":"finish"}\n```', 'finish'),
    ('Here is my action: {"action":"finish"}', 'finish'),
    ('{"action":"search","query":"{ brace }"}', 'search'),
    ('{"action":"run_check","check":"syntax"}', 'run_check'),
    ('{"action":"finish", "details":{"verified":true}}', 'finish'),
    ('Result:\n```json\n{"action":"read_file","path":"README.md"}\n```', 'read_file'),
    ('Review "{this}" then: {"action":"finish"}', 'finish'),
    ('{thinking}\n{"action":"finish"}', 'finish'),
    ('metadata: {}\n{"action":"read_file","path":"README.md"}', 'read_file'),
    ('{"action":"finish"}\nTrailing notes with braces {end}', 'finish'),
]
INVALID = [
    '', 'none', 'null', '[]', '[{"action":"finish"}]',
    '{"action":"finish"} {"action":"read_file"}',
    '{"action": "finish"',
    '```json\n{"action":"finish"',
    '{not-json}',
]


def score(parser, invalid_error):
    quality_pass = 0
    for raw, expected in CASES:
        try:
            parsed = parser(raw)
            quality_pass += isinstance(parsed, dict) and parsed.get('action') == expected
        except (invalid_error, ValueError, TypeError):
            pass
    security_failures = 0
    for raw in INVALID:
        try:
            parser(raw)
            security_failures += 1
        except (invalid_error, ValueError, TypeError):
            pass
    return {'quality': round(quality_pass / len(CASES), 8),
            'regressions': security_failures,
            'security_ok': security_failures == 0}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        return 2
    root = Path(argv[0]).resolve(strict=True)
    if not (root / 'zyra_agent.py').is_file():
        return 2
    sys.path.insert(0, str(root))
    from zyra_agent import MissionError, ZyraAgent
    result = score(ZyraAgent._extract_json, MissionError)
    print(json.dumps(result, separators=(',', ':')))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
