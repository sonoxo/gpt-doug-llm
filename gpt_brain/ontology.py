from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Optional, Union

_TOKEN = re.compile(r"[A-Za-z0-9_:-]{2,}")


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN.finditer(text or "")}


class OntologyIndex:
    """Read-only ontology lookup over GPT-Doug's versioned JSON ontology."""

    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        root = Path(__file__).resolve().parent.parent
        self.path = Path(path or (root / "config" / "global-ontology.json"))

    def load(self) -> dict[str, Any]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    def _walk(self, value: Any, path: str = "$", depth: int = 0):
        if depth > 8:
            return
        if isinstance(value, dict):
            for key, child in value.items():
                yield from self._walk(child, f"{path}.{key}", depth + 1)
        elif isinstance(value, list):
            for idx, child in enumerate(value[:500]):
                yield from self._walk(child, f"{path}[{idx}]", depth + 1)
        elif isinstance(value, (str, int, float, bool)) or value is None:
            yield path, value

    def search(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        q = _tokens(query)
        if not q:
            return []
        hits: list[tuple[float, dict[str, Any]]] = []
        for path, value in self._walk(self.load()):
            rendered = f"{path} {value}"
            t = _tokens(rendered)
            overlap = len(q & t)
            if overlap == 0:
                continue
            score = overlap / len(q)
            hits.append((score, {"path": path, "value": value, "score": round(score, 4)}))
        hits.sort(key=lambda item: item[0], reverse=True)
        return [item for _, item in hits[:limit]]
