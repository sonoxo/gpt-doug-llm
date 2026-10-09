"""Read-only adapters for the existing GPT-Doug brain and ontology files."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

_TOKEN = re.compile(r"[A-Za-z0-9_:-]{2,}")


def _tokens(value: str) -> set[str]:
    return set(t.lower() for t in _TOKEN.findall(value))


def _score(text: str, query: str) -> float:
    qt = _tokens(query)
    return round(len(_tokens(text) & qt) / len(qt), 4) if qt else 0.0


def read_legacy_memory(root: str | Path, query: str, limit: int = 6) -> list[dict[str, Any]]:
    """Opt-in read of .gpt-doug JSONL export; no sync or writes."""
    path = Path(root).expanduser() / ".gpt-doug" / "brain-memory-v1.jsonl"
    if not path.is_file():
        return []
    matches: list[dict[str, Any]] = []
    # Cap loaded lines and sizes to avoid accidentally reading huge exports.
    with path.open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            if index >= 10000:
                break
            if len(line) > 15000:
                continue
            try:
                row = json.loads(line)
            except (TypeError, ValueError):
                continue
            if not isinstance(row, dict) or not isinstance(row.get("content"), str):
                continue
            score = _score(row["content"], query)
            if score:
                matches.append({"kind": str(row.get("kind", "unknown"))[:30],
                                "content": row["content"][:4000],
                                "provenance": str(row.get("provenance", "unknown"))[:300],
                                "score": score})
    return sorted(matches, key=lambda x: x["score"], reverse=True)[:limit]


def read_ontology(repo_root: str | Path, query: str, limit: int = 8) -> list[dict[str, Any]]:
    path = Path(repo_root).expanduser() / "config" / "global-ontology.json"
    if not path.is_file():
        return []
    if path.stat().st_size > 5_000_000:
        return []
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    hits: list[dict[str, Any]] = []

    def walk(item: Any, location: str, depth: int = 0) -> None:
        if depth > 8 or len(hits) > 1000:
            return
        if isinstance(item, dict):
            for key, val in list(item.items())[:500]:
                walk(val, f"{location}.{key}", depth + 1)
        elif isinstance(item, list):
            for idx, val in enumerate(item[:500]):
                walk(val, f"{location}[{idx}]", depth + 1)
        elif isinstance(item, (str, int, float, bool)) or item is None:
            rendered = f"{location} {item}"
            score = _score(rendered, query)
            if score:
                hits.append({"path": location, "value": str(item)[:1000], "score": score})

    walk(obj, "$")
    return sorted(hits, key=lambda x: x["score"], reverse=True)[:limit]
