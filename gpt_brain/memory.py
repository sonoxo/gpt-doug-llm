from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any, Optional, Union

_TOKEN = re.compile(r"[A-Za-z0-9_:-]{2,}")
_SECRET = re.compile(
    r"(?:"
    r"sk-[A-Za-z0-9_-]{16,}|"
    r"gh[pousr]_[A-Za-z0-9_]{20,}|"
    r"api[_-]?key\s*[:=]\s*[^\s]{12,}|"
    r"password\s*[:=]\s*[^\s]{8,}|"
    r"bearer\s+[A-Za-z0-9._~+/-]{16,}"
    r")",
    re.IGNORECASE,
)


def _tokens(text: str) -> set[str]:
    return {m.group(0).lower() for m in _TOKEN.finditer(text or "")}


def _contains_secret(value: str) -> bool:
    return bool(_SECRET.search(value or ""))


class BrainMemory:
    """Append-only episodic/semantic/procedural memory with lexical recall.

    This deliberately stores concise artifacts and provenance, not hidden model
    chain-of-thought. Secret-looking values are rejected before persistence.
    """

    VALID_KINDS = {"episodic", "semantic", "procedural", "preference", "decision"}

    def __init__(self, path: Optional[Union[str, Path]] = None) -> None:
        self.path = Path(path or (Path.home() / ".gpt-doug" / "brain-memory-v1.jsonl"))
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def add(
        self,
        kind: str,
        content: str,
        *,
        provenance: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        if kind not in self.VALID_KINDS:
            raise ValueError(f"unsupported memory kind: {kind}")
        if not content or not content.strip():
            raise ValueError("memory content must be non-empty")
        if not provenance or not provenance.strip():
            raise ValueError("memory provenance is required")

        metadata = metadata or {}
        metadata_text = json.dumps(metadata, ensure_ascii=False, default=str)
        if (
            _contains_secret(content)
            or _contains_secret(provenance)
            or _contains_secret(metadata_text)
        ):
            raise ValueError("secret-like content is not permitted in brain memory")

        record = {
            "ts": time.time(),
            "kind": kind,
            "content": content.strip(),
            "provenance": provenance.strip(),
            "metadata": metadata,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        return record

    def records(self, limit: Optional[int] = None) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
        return rows[-limit:] if limit else rows

    def recall(self, query: str, limit: int = 8) -> list[dict[str, Any]]:
        q = _tokens(query)
        if not q:
            return self.records(limit)
        scored: list[tuple[float, dict[str, Any]]] = []
        for row in self.records():
            c = _tokens(str(row.get("content", "")))
            overlap = len(q & c)
            if overlap == 0:
                continue
            score = overlap / max(len(q), 1)
            if row.get("kind") == "procedural":
                score += 0.08
            if row.get("kind") == "decision":
                score += 0.04
            scored.append((score, row))
        scored.sort(key=lambda item: (item[0], item[1].get("ts", 0)), reverse=True)
        return [dict(row, recall_score=round(score, 4)) for score, row in scored[:limit]]

    def ingest_transcript(self, text: str, *, provenance: str) -> int:
        """Import a transcript/export as bounded episodic chunks.

        All chunks are validated before the first write so a secret-like value
        cannot leave a partially imported transcript behind.
        """
        text = (text or "").strip()
        if not text:
            return 0
        if not provenance or not provenance.strip():
            raise ValueError("memory provenance is required")
        if _contains_secret(provenance):
            raise ValueError("secret-like provenance is not permitted")

        role_re = re.compile(r"^(user|assistant|system)\s*:\s*", re.IGNORECASE)
        chunks: list[str] = []
        current: list[str] = []
        for raw in text.splitlines():
            line = raw.rstrip()
            if role_re.match(line) and current:
                chunks.append("\n".join(current).strip())
                current = [line]
            elif line.strip() or current:
                current.append(line)
        if current:
            chunks.append("\n".join(current).strip())
        if len(chunks) == 1 and len(chunks[0]) > 6000:
            paragraphs = [
                paragraph.strip()
                for paragraph in re.split(r"\n\s*\n", chunks[0])
                if paragraph.strip()
            ]
            chunks = paragraphs or chunks

        prepared = [chunk[:6000] for chunk in chunks if chunk]
        if any(_contains_secret(chunk) for chunk in prepared):
            raise ValueError("secret-like content is not permitted in brain memory")

        for chunk in prepared:
            self.add(
                "episodic",
                chunk,
                provenance=provenance,
                metadata={"imported": True},
            )
        return len(prepared)
