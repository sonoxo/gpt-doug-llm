"""GPT-Delta evidence intake: append only *material changes* to S-Brain.

Never treats ingested source assertions as independently verified facts.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from ai_killswitch import require_ai_allowed


def observe_change(
    *, database: str | Path, subject: str, predicate: str, value: str,
    source_id: str, source_uri: str, observed_at: Optional[str] = None,
    confidence: float = 0.5,
) -> dict[str, Any]:
    require_ai_allowed("GPT-Delta evidence intake")
    # Reuse existing S-Brain ontology, deduplication and provenance protection.
    from gpt_brain.s_brain import Evidence, SBrain
    fact = Evidence(subject, predicate, value, source_id, source_uri,
                    observed_at=observed_at, confidence=confidence)
    clean = fact.normalized()
    with SBrain(database) as brain:
        old = [row for row in brain._all_records()
               if row["subject"].casefold() == clean["subject"].casefold()
               and row["predicate"].casefold() == clean["predicate"].casefold()]
        if any(row["value"] == clean["value"] and row["source_id"] == clean["source_id"]
               and row["source_uri"] == clean["source_uri"] for row in old):
            return {
                "event": "duplicate", "material": False,
                "subject": subject, "predicate": predicate, "stored": False,
                "independently_verified": False,
            }
        event = "new" if not old else "changed"
        disagreement = bool(old and any(row["value"] != clean["value"] for row in old))
        stored = brain.remember(fact)
        return {
            "event": event, "material": event in {"new", "changed"},
            "subject": clean["subject"], "predicate": clean["predicate"],
            "evidence_id": stored["id"], "source_id": clean["source_id"],
            "stored": stored["inserted"], "contradictory_values": disagreement,
            "previous_source_ids": sorted({row["source_id"] for row in old}),
            "independently_verified": False,
        }
