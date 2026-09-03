from __future__ import annotations

import math
import re
import threading
import time
from collections import Counter
from dataclasses import asdict, dataclass

TOKEN_RE = re.compile(r"[A-Za-z0-9_./:-]+")
SESSION_RE = re.compile(r"[^A-Za-z0-9_.:-]+")

MEMORY_PROFILE = "gpt-doug-max-memory-v1"
MEMORY_METHOD = "MEM1_INSPIRED_DETERMINISTIC_CONSOLIDATION"
MEMORY_REFERENCE = "https://github.com/MIT-MI/MEM1"


def _tokens(text: str) -> set[str]:
    return {token.lower() for token in TOKEN_RE.findall(text) if len(token) > 1}


def _similarity(left: str, right: str) -> float:
    a = _tokens(left)
    b = _tokens(right)
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _importance(text: str) -> float:
    lowered = text.lower()
    score = 0.35
    signals = {
        "must": 0.20,
        "always": 0.18,
        "never": 0.18,
        "require": 0.15,
        "goal": 0.12,
        "decision": 0.12,
        "error": 0.10,
        "failed": 0.10,
        "fix": 0.08,
        "security": 0.10,
        "deploy": 0.08,
        "test": 0.06,
    }
    for token, weight in signals.items():
        if token in lowered:
            score += weight
    if any(char.isdigit() for char in text):
        score += 0.05
    return min(1.0, score)


def _clean(text: str, limit: int = 900) -> str:
    value = " ".join(text.strip().split())
    return value[:limit]


def _safe_session_id(value: str | None) -> str:
    cleaned = SESSION_RE.sub("-", (value or "default").strip())[:96].strip("-")
    return cleaned or "default"


@dataclass
class MemoryRecord:
    id: int
    kind: str
    text: str
    importance: float
    hits: int
    created_at: float
    updated_at: float


class CompactMemory:
    """Bounded, model-agnostic long-horizon memory.

    The design is inspired by the public MEM1 idea of repeatedly consolidating prior
    memory with new observations instead of replaying an ever-growing transcript.
    This implementation is independent, deterministic, and does not reproduce MEM1
    training code or weights.
    """

    def __init__(self, session_id: str, max_items: int = 24, max_chars: int = 6000):
        self.session_id = _safe_session_id(session_id)
        self.max_items = max(4, int(max_items))
        self.max_chars = max(1200, int(max_chars))
        self.records: list[MemoryRecord] = []
        self.observations = 0
        self.observed_chars = 0
        self._next_id = 1
        self._lock = threading.RLock()

    def add(self, text: str, *, kind: str = "observation", importance: float | None = None) -> MemoryRecord | None:
        value = _clean(text)
        if not value:
            return None
        now = time.time()
        with self._lock:
            self.observations += 1
            self.observed_chars += len(value)
            duplicate = max(self.records, key=lambda item: _similarity(item.text, value), default=None)
            if duplicate is not None and _similarity(duplicate.text, value) >= 0.72:
                duplicate.hits += 1
                duplicate.updated_at = now
                duplicate.importance = min(1.0, max(duplicate.importance, importance or _importance(value)) + 0.03)
                if len(value) > len(duplicate.text):
                    duplicate.text = value
                self._consolidate()
                return duplicate

            record = MemoryRecord(
                id=self._next_id,
                kind=kind,
                text=value,
                importance=float(importance if importance is not None else _importance(value)),
                hits=1,
                created_at=now,
                updated_at=now,
            )
            self._next_id += 1
            self.records.append(record)
            self._consolidate()
            return record

    def _consolidate(self) -> None:
        now = time.time()

        def retention(item: MemoryRecord) -> float:
            age_hours = max(0.0, (now - item.updated_at) / 3600.0)
            recency = 1.0 / (1.0 + age_hours / 24.0)
            reinforcement = min(1.0, math.log2(item.hits + 1) / 4.0)
            return item.importance * 0.62 + reinforcement * 0.23 + recency * 0.15

        while len(self.records) > self.max_items or sum(len(item.text) for item in self.records) > self.max_chars:
            if len(self.records) <= 1:
                break
            victim = min(self.records, key=retention)
            self.records.remove(victim)

    def retrieve(self, query: str, *, limit: int = 8, max_chars: int = 3200) -> list[MemoryRecord]:
        query_tokens = _tokens(query)
        now = time.time()
        with self._lock:
            def rank(item: MemoryRecord) -> float:
                item_tokens = _tokens(item.text)
                lexical = len(query_tokens & item_tokens) / max(1, len(query_tokens | item_tokens))
                age_hours = max(0.0, (now - item.updated_at) / 3600.0)
                recency = 1.0 / (1.0 + age_hours / 48.0)
                reinforcement = min(1.0, item.hits / 4.0)
                return lexical * 0.58 + item.importance * 0.24 + recency * 0.10 + reinforcement * 0.08

            ranked = sorted(self.records, key=rank, reverse=True)
            selected: list[MemoryRecord] = []
            used = 0
            for item in ranked:
                if len(selected) >= max(1, limit):
                    break
                cost = len(item.text)
                if selected and used + cost > max_chars:
                    continue
                selected.append(item)
                used += cost
            return selected

    def context(self, query: str, *, limit: int = 8, max_chars: int = 3200) -> str:
        items = self.retrieve(query, limit=limit, max_chars=max_chars)
        if not items:
            return "No prior compact memory for this session."
        return "\n".join(f"- [{item.kind}; importance={item.importance:.2f}; hits={item.hits}] {item.text}" for item in items)

    def status(self) -> dict:
        with self._lock:
            current_chars = sum(len(item.text) for item in self.records)
            compression = self.observed_chars / max(1, current_chars)
            kinds = Counter(item.kind for item in self.records)
            return {
                "profile": MEMORY_PROFILE,
                "method": MEMORY_METHOD,
                "reference": MEMORY_REFERENCE,
                "sessionId": self.session_id,
                "records": len(self.records),
                "maxRecords": self.max_items,
                "currentChars": current_chars,
                "maxChars": self.max_chars,
                "observations": self.observations,
                "observedChars": self.observed_chars,
                "compressionRatio": round(compression, 3),
                "kinds": dict(kinds),
            }

    def snapshot(self, query: str = "") -> dict:
        with self._lock:
            records = self.retrieve(query or "memory", limit=self.max_items, max_chars=self.max_chars)
            return {"status": self.status(), "records": [asdict(item) for item in records]}

    def clear(self) -> None:
        with self._lock:
            self.records.clear()
            self.observations = 0
            self.observed_chars = 0
            self._next_id = 1


class MemoryManager:
    def __init__(self, *, max_sessions: int = 128, max_items: int = 24, max_chars: int = 6000):
        self.max_sessions = max(1, int(max_sessions))
        self.max_items = max_items
        self.max_chars = max_chars
        self._sessions: dict[str, CompactMemory] = {}
        self._lock = threading.RLock()

    def get(self, session_id: str | None = None) -> CompactMemory:
        key = _safe_session_id(session_id)
        with self._lock:
            if key not in self._sessions:
                if len(self._sessions) >= self.max_sessions:
                    oldest_key = min(
                        self._sessions,
                        key=lambda name: max((r.updated_at for r in self._sessions[name].records), default=0.0),
                    )
                    self._sessions.pop(oldest_key, None)
                self._sessions[key] = CompactMemory(key, self.max_items, self.max_chars)
            return self._sessions[key]

    def clear(self, session_id: str | None = None) -> bool:
        key = _safe_session_id(session_id)
        with self._lock:
            memory = self._sessions.get(key)
            if memory is None:
                return False
            memory.clear()
            return True

    def status(self) -> dict:
        with self._lock:
            return {
                "profile": MEMORY_PROFILE,
                "method": MEMORY_METHOD,
                "sessions": len(self._sessions),
                "maxSessions": self.max_sessions,
                "records": sum(len(memory.records) for memory in self._sessions.values()),
            }


memory_manager = MemoryManager()
