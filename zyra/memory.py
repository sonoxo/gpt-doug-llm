from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
import uuid


@dataclass
class MemoryRecord:
    content: str
    memory_type: str = "episodic"
    source: str = "agent"
    confidence: float = 1.0
    trust_level: str = "untrusted"
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ZyraMemory:
    def __init__(self) -> None:
        self._records: dict[str, MemoryRecord] = {}

    def remember(self, record: MemoryRecord) -> MemoryRecord:
        if not 0.0 <= record.confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")
        self._records[record.id] = record
        return record

    def recall(self, record_id: str) -> Optional[MemoryRecord]:
        return self._records.get(record_id)

    def search(self, query: str) -> list[MemoryRecord]:
        query = query.lower()
        return [
            record
            for record in self._records.values()
            if query in record.content.lower()
            or any(query in tag.lower() for tag in record.tags)
        ]

    def forget(self, record_id: str) -> bool:
        return self._records.pop(record_id, None) is not None

    def all(self) -> list[MemoryRecord]:
        return list(self._records.values())
