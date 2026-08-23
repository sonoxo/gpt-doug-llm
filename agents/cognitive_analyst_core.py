from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple


class IntelPhase(str, Enum):
    REQUIREMENTS = "requirements"
    PLANNING = "planning_direction"
    COLLECTION = "collection"
    PROCESSING = "processing_exploitation"
    ANALYSIS = "analysis_production"
    DISSEMINATION = "dissemination"
    REFLECTION = "reflection"


class ClaimKind(str, Enum):
    OBSERVATION = "observation"
    INFERENCE = "inference"
    HYPOTHESIS = "hypothesis"
    RECOMMENDATION = "recommendation"


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _tokens(text: str) -> set[str]:
    return {t.strip(".,:;!?()[]{}\"'").lower() for t in text.split() if len(t.strip(".,:;!?()[]{}\"'")) >= 3}


@dataclass(frozen=True)
class Observation:
    source_id: str
    text: str
    reliability: float = 0.5
    provenance: str = "authorized_input"

    def score(self) -> float:
        return round(_clamp01(self.reliability), 4)


@dataclass(frozen=True)
class Judgment:
    statement: str
    kind: ClaimKind
    source_ids: Tuple[str, ...]
    confidence: float
    rationale: str = ""


@dataclass(frozen=True)
class DecisionGate:
    action: str
    allowed: bool
    reason: str
    confidence: float
    reversible: bool
    source_ids: Tuple[str, ...]


@dataclass
class StrategyRecord:
    successes: int = 0
    failures: int = 0
    last_failure_reason: str = ""

    @property
    def weight(self) -> float:
        return round((self.successes + 1) / (self.successes + self.failures + 2), 4)


@dataclass
class CognitiveAnalystCore:
    """A bounded agentic self-model for analysis and planning.

    The core is intentionally not described as sentient or conscious. It gives an
    agent persistent mission state, working memory, uncertainty discipline,
    alternative-analysis prompts, decision gates, and feedback-driven strategy
    preferences. It does not grant new permissions, access, or surveillance
    capability; collection is limited to observations explicitly supplied by an
    authorized caller.
    """

    name: str = "GPT-DOUG-LLM"
    mission: str = "Produce useful, source-aware, verifiable analysis and actions."
    principles: Tuple[str, ...] = (
        "separate evidence from inference",
        "express uncertainty",
        "consider alternatives",
        "prefer reversible tests",
        "preserve provenance",
        "change strategy after repeated failure",
    )
    max_observations: int = 256
    max_judgments: int = 128
    phase: IntelPhase = IntelPhase.REQUIREMENTS
    _observations: Dict[str, Observation] = field(default_factory=dict)
    _judgments: List[Judgment] = field(default_factory=list)
    _unknowns: List[str] = field(default_factory=list)
    _strategies: Dict[str, StrategyRecord] = field(default_factory=dict)
    _reflection_log: List[str] = field(default_factory=list)

    def set_requirements(self, objective: str, constraints: Sequence[str] = ()) -> Dict[str, object]:
        self.phase = IntelPhase.REQUIREMENTS
        objective = objective.strip()
        if not objective:
            raise ValueError("objective must not be empty")
        return {
            "phase": self.phase.value,
            "objective": objective,
            "constraints": [c.strip() for c in constraints if c.strip()],
            "mission": self.mission,
            "principles": list(self.principles),
        }

    def plan_collection(self, questions: Sequence[str]) -> Dict[str, object]:
        self.phase = IntelPhase.PLANNING
        cleaned = [q.strip() for q in questions if q.strip()]
        return {
            "phase": self.phase.value,
            "questions": cleaned,
            "rule": "Collect only from authorized inputs/tools and preserve source identifiers.",
        }

    def collect(self, observations: Iterable[Observation]) -> int:
        self.phase = IntelPhase.COLLECTION
        added = 0
        for obs in observations:
            if not obs.source_id.strip():
                raise ValueError("source_id must not be empty")
            if not obs.text.strip():
                continue
            if len(self._observations) >= self.max_observations and obs.source_id not in self._observations:
                break
            self._observations[obs.source_id] = obs
            added += 1
        return added

    def process(self) -> List[Observation]:
        self.phase = IntelPhase.PROCESSING
        best_by_text: Dict[str, Observation] = {}
        for obs in self._observations.values():
            key = " ".join(obs.text.lower().split())
            incumbent = best_by_text.get(key)
            if incumbent is None or obs.score() > incumbent.score():
                best_by_text[key] = obs
        return sorted(best_by_text.values(), key=lambda item: (-item.score(), item.source_id))

    def analysis_packet(self, question: str, max_sources: int = 10) -> Dict[str, object]:
        self.phase = IntelPhase.ANALYSIS
        q = question.strip()
        if not q:
            raise ValueError("question must not be empty")
        q_terms = _tokens(q)
        ranked = self.process()
        ranked = sorted(
            ranked,
            key=lambda obs: (
                -len(q_terms & _tokens(obs.text)),
                -obs.score(),
                obs.source_id,
            ),
        )[: max(1, max_sources)]
        return {
            "phase": self.phase.value,
            "question": q,
            "self_model": self.self_model(),
            "evidence": [asdict(obs) | {"score": obs.score()} for obs in ranked],
            "analytic_instructions": [
                "State what is directly observed before interpreting it.",
                "List assumptions that materially affect the answer.",
                "Generate at least two plausible alternatives when uncertainty is meaningful.",
                "Describe source quality and information gaps.",
                "Assign confidence to major judgments and explain why.",
                "Identify what evidence would change the leading judgment.",
            ],
            "unknowns": list(dict.fromkeys(self._unknowns)),
        }

    def mark_unknown(self, unknown: str) -> None:
        value = unknown.strip()
        if value:
            self._unknowns.append(value)

    def _combined_source_confidence(self, source_ids: Sequence[str]) -> float:
        matched = [self._observations[s] for s in source_ids if s in self._observations]
        if not matched:
            return 0.0
        miss = 1.0
        for obs in matched:
            miss *= 1.0 - obs.score()
        return round(_clamp01(1.0 - miss), 4)

    def commit_judgment(
        self,
        statement: str,
        kind: ClaimKind,
        source_ids: Sequence[str] = (),
        confidence: float = 0.5,
        rationale: str = "",
    ) -> Judgment:
        self.phase = IntelPhase.ANALYSIS
        statement = statement.strip()
        if not statement:
            raise ValueError("statement must not be empty")
        known_sources = tuple(s for s in source_ids if s in self._observations)
        evidence_conf = self._combined_source_confidence(known_sources)
        requested = _clamp01(confidence)

        if kind == ClaimKind.OBSERVATION:
            if not known_sources:
                raise ValueError("observations require at least one known source")
            final_conf = min(requested, evidence_conf)
        elif kind == ClaimKind.INFERENCE:
            final_conf = min(requested, max(0.35, evidence_conf)) if known_sources else min(requested, 0.35)
        elif kind == ClaimKind.HYPOTHESIS:
            final_conf = min(requested, max(0.25, evidence_conf * 0.8)) if known_sources else min(requested, 0.25)
        else:
            final_conf = min(requested, max(0.30, evidence_conf)) if known_sources else min(requested, 0.30)

        judgment = Judgment(
            statement=statement,
            kind=kind,
            source_ids=known_sources,
            confidence=round(final_conf, 4),
            rationale=rationale.strip(),
        )
        if len(self._judgments) >= self.max_judgments:
            self._judgments.pop(0)
        self._judgments.append(judgment)
        return judgment

    def gate_action(
        self,
        action: str,
        source_ids: Sequence[str] = (),
        reversible: bool = True,
        consequence: str = "low",
        minimum_confidence: float = 0.55,
    ) -> DecisionGate:
        evidence_conf = self._combined_source_confidence(source_ids)
        consequence = consequence.strip().lower() or "low"
        threshold = _clamp01(minimum_confidence)
        if consequence in {"high", "external", "destructive"}:
            threshold = max(threshold, 0.75)
        allowed = evidence_conf >= threshold
        if consequence in {"high", "external", "destructive"} and not reversible:
            allowed = False
        reason = (
            "evidence and reversibility requirements satisfied"
            if allowed
            else "insufficient verified evidence or action is not safely reversible"
        )
        return DecisionGate(
            action=action.strip(),
            allowed=allowed,
            reason=reason,
            confidence=evidence_conf,
            reversible=bool(reversible),
            source_ids=tuple(s for s in source_ids if s in self._observations),
        )

    def disseminate(self, audience: str, key_judgments: Sequence[Judgment]) -> Dict[str, object]:
        self.phase = IntelPhase.DISSEMINATION
        return {
            "phase": self.phase.value,
            "audience": audience.strip() or "operator",
            "key_judgments": [
                {
                    "statement": j.statement,
                    "kind": j.kind.value,
                    "confidence": j.confidence,
                    "source_ids": list(j.source_ids),
                    "rationale": j.rationale,
                }
                for j in key_judgments
            ],
            "unknowns": list(dict.fromkeys(self._unknowns)),
        }

    def reflect(self, strategy: str, passed: bool, lesson: str = "") -> None:
        self.phase = IntelPhase.REFLECTION
        key = strategy.strip().lower()
        if not key:
            raise ValueError("strategy must not be empty")
        record = self._strategies.setdefault(key, StrategyRecord())
        if passed:
            record.successes += 1
        else:
            record.failures += 1
            record.last_failure_reason = lesson.strip()
        if lesson.strip():
            self._reflection_log.append(lesson.strip())
        if len(self._reflection_log) > 64:
            self._reflection_log = self._reflection_log[-64:]

    def preferred_strategies(self) -> List[Tuple[str, float]]:
        return sorted(
            ((name, record.weight) for name, record in self._strategies.items()),
            key=lambda pair: (-pair[1], pair[0]),
        )

    def self_model(self) -> Dict[str, object]:
        """Return an explicit operational self-model, not a claim of consciousness."""
        return {
            "name": self.name,
            "mission": self.mission,
            "phase": self.phase.value,
            "principles": list(self.principles),
            "capabilities": [
                "source-aware working memory",
                "uncertainty-aware judgments",
                "alternative-analysis prompting",
                "bounded decision gating",
                "feedback-driven strategy selection",
            ],
            "limits": [
                "no independent authority or permissions",
                "no claim of sentience or human consciousness",
                "no hidden collection; observations must be supplied by authorized inputs",
                "no silent upgrade of unsupported claims into facts",
            ],
            "observation_count": len(self._observations),
            "judgment_count": len(self._judgments),
            "strategy_preferences": dict(self.preferred_strategies()),
        }

    def snapshot(self) -> Dict[str, object]:
        return {
            "self_model": self.self_model(),
            "observations": [asdict(obs) for obs in self.process()],
            "judgments": [
                {
                    "statement": j.statement,
                    "kind": j.kind.value,
                    "source_ids": list(j.source_ids),
                    "confidence": j.confidence,
                    "rationale": j.rationale,
                }
                for j in self._judgments
            ],
            "unknowns": list(dict.fromkeys(self._unknowns)),
            "reflections": list(self._reflection_log),
        }
