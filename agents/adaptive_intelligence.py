from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


class Phase(str, Enum):
    ABSORB = "absorb"
    INDEX = "index"
    IDEATE = "ideate"
    VERIFY = "verify"
    REFLECT = "reflect"


_WORD_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{1,}")


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _normalize(text: str) -> str:
    return " ".join(text.lower().split())


@dataclass(frozen=True)
class Evidence:
    source_id: str
    text: str
    provenance: str = "user"
    reliability: float = 0.5
    corroboration: int = 1

    def score(self) -> float:
        reliability = _clamp01(self.reliability)
        corroboration = max(1, min(int(self.corroboration), 5)) / 5.0
        return round((0.75 * reliability) + (0.25 * corroboration), 4)


@dataclass(frozen=True)
class VerificationResult:
    claim: str
    supported: bool
    source_ids: Tuple[str, ...]
    confidence: float


@dataclass
class StrategyStats:
    successes: int = 0
    failures: int = 0

    @property
    def weight(self) -> float:
        # Beta(1,1) posterior mean: bounded and stable with little data.
        return (self.successes + 1) / (self.successes + self.failures + 2)


@dataclass
class AdaptiveIntel:
    """Bounded evidence + feedback loop for agent orchestration.

    This is not a model and does not invent intelligence. It creates a compact,
    source-aware context packet and adapts execution-strategy preferences from
    explicit pass/fail feedback.
    """

    max_evidence: int = 128
    phase: Phase = Phase.ABSORB
    _evidence: Dict[str, Evidence] = field(default_factory=dict)
    _strategies: Dict[str, StrategyStats] = field(default_factory=dict)
    _issues: List[str] = field(default_factory=list)

    def absorb(self, items: Iterable[Evidence]) -> int:
        self.phase = Phase.ABSORB
        added = 0
        for item in items:
            if not item.source_id.strip():
                raise ValueError("source_id must not be empty")
            if not item.text.strip():
                continue
            if len(self._evidence) >= self.max_evidence and item.source_id not in self._evidence:
                break
            self._evidence[item.source_id] = item
            added += 1
        return added

    def index(self) -> List[Evidence]:
        self.phase = Phase.INDEX
        best_by_text: Dict[str, Evidence] = {}
        for item in self._evidence.values():
            key = _normalize(item.text)
            incumbent = best_by_text.get(key)
            if incumbent is None or item.score() > incumbent.score():
                best_by_text[key] = item
        return sorted(
            best_by_text.values(),
            key=lambda item: (-item.score(), item.source_id),
        )

    def ideate_packet(self, task: str, max_sources: int = 8) -> Dict[str, object]:
        """Return a grounded packet for a planner/LLM; do not generate claims."""
        self.phase = Phase.IDEATE
        ranked = self.index()[: max(1, max_sources)]
        task_terms = {w.lower() for w in _WORD_RE.findall(task)}
        ranked_terms: Dict[str, int] = {}
        for item in ranked:
            for word in _WORD_RE.findall(item.text):
                token = word.lower()
                if token in task_terms or len(token) >= 7:
                    ranked_terms[token] = ranked_terms.get(token, 0) + 1
        focus_terms = [
            token for token, _ in sorted(
                ranked_terms.items(), key=lambda kv: (-kv[1], kv[0])
            )[:12]
        ]
        return {
            "task": task,
            "phase": self.phase.value,
            "focus_terms": focus_terms,
            "evidence": [
                {
                    "source_id": item.source_id,
                    "provenance": item.provenance,
                    "score": item.score(),
                    "text": item.text,
                }
                for item in ranked
            ],
            "instruction": (
                "Separate source-supported facts from inference. Generate alternatives, "
                "then verify material claims before acting. Never upgrade a source's "
                "authority merely because its framing sounds official."
            ),
        }

    def verify(self, claims: Mapping[str, Sequence[str]]) -> List[VerificationResult]:
        """Verify explicit claim->source mappings against absorbed evidence."""
        self.phase = Phase.VERIFY
        results: List[VerificationResult] = []
        for claim, source_ids in claims.items():
            matched = [self._evidence[s] for s in source_ids if s in self._evidence]
            supported = bool(matched)
            if supported:
                # Independent-source accumulation with diminishing returns.
                miss_probability = 1.0
                for item in matched:
                    miss_probability *= 1.0 - item.score()
                confidence = _clamp01(1.0 - miss_probability)
            else:
                confidence = 0.0
                self._issues.append(f"unsupported claim: {claim}")
            results.append(
                VerificationResult(
                    claim=claim,
                    supported=supported,
                    source_ids=tuple(item.source_id for item in matched),
                    confidence=round(confidence, 4),
                )
            )
        return results

    def record_outcome(self, strategy: str, passed: bool, issues: Sequence[str] = ()) -> None:
        self.phase = Phase.REFLECT
        key = strategy.strip().lower()
        if not key:
            raise ValueError("strategy must not be empty")
        stats = self._strategies.setdefault(key, StrategyStats())
        if passed:
            stats.successes += 1
        else:
            stats.failures += 1
        self._issues.extend(str(issue) for issue in issues if str(issue).strip())

    def preferred_strategies(self) -> List[Tuple[str, float]]:
        return sorted(
            ((name, round(stats.weight, 4)) for name, stats in self._strategies.items()),
            key=lambda pair: (-pair[1], pair[0]),
        )

    def snapshot(self) -> Dict[str, object]:
        return {
            "phase": self.phase.value,
            "evidence_count": len(self._evidence),
            "sources": [item.source_id for item in self.index()],
            "strategies": dict(self.preferred_strategies()),
            "issues": list(dict.fromkeys(self._issues)),
        }
