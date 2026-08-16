from __future__ import annotations

import json
import time
from pathlib import Path


DEFAULT_PATH = (
    Path.home()
    / ".gpt-doug"
    / "memory-v5.jsonl"
)


class Memory:
    def __init__(self, path: Path | None = None):
        self.path = path or DEFAULT_PATH
        self.path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

    def add(
        self,
        kind: str,
        content: str,
        metadata: dict | None = None,
    ) -> None:
        record = {
            "timestamp": time.time(),
            "kind": kind,
            "content": content,
            "metadata": metadata or {},
        }

        with self.path.open(
            "a",
            encoding="utf-8",
        ) as handle:
            handle.write(
                json.dumps(
                    record,
                    ensure_ascii=False,
                )
                + "\n"
            )

    def recent(self, limit: int = 25) -> list[dict]:
        if not self.path.exists():
            return []

        records: list[dict] = []

        for line in self.path.read_text(
            encoding="utf-8",
        ).splitlines()[-limit:]:
            try:
                records.append(json.loads(line))
            except Exception:
                continue

        return records
