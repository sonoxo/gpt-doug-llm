from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Iterable

from va3lm.ontologi import OntologiEngine, OntologiError, Program, Seed, validate

GARDEN_VERSION = "1.0"
MEMORY_STATES = {"ACTIVE", "STALE", "ARCHIVED"}


@dataclass(frozen=True)
class MemoryRecord:
    seed_id: str
    first_seen: str
    last_seen: str
    reinforcements: int = 0
    state: str = "ACTIVE"


class MemoryGarden:
    """Lifecycle manager for ONTologi seeds without bypassing evidence-gated verification."""

    def __init__(self, engine: OntologiEngine, records: dict[str, MemoryRecord] | None = None) -> None:
        self.engine = engine
        self.records = dict(records or {})

    @staticmethod
    def _iso(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=UTC)
        return value.astimezone(UTC).isoformat()

    @staticmethod
    def _dt(value: str) -> datetime:
        parsed = datetime.fromisoformat(value)
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)

    def observe(self, seed_ids: Iterable[str], *, now: datetime | None = None) -> list[MemoryRecord]:
        now_value = now or datetime.now(UTC)
        stamp = self._iso(now_value)
        known = {seed.id for seed in self.engine.program.seeds}
        updated: list[MemoryRecord] = []
        for seed_id in seed_ids:
            if seed_id not in known:
                raise OntologiError(f"Unknown seed: {seed_id}")
            current = self.records.get(seed_id)
            record = MemoryRecord(
                seed_id=seed_id,
                first_seen=current.first_seen if current else stamp,
                last_seen=stamp,
                reinforcements=current.reinforcements if current else 0,
                state="ACTIVE",
            )
            self.records[seed_id] = record
            updated.append(record)
        return updated

    def reinforce(self, seed_id: str, *, amount: float = 0.05, now: datetime | None = None) -> Seed:
        if not 0.0 < amount <= 0.25:
            raise OntologiError("Reinforcement amount must be > 0 and <= 0.25")
        seeds = list(self.engine.program.seeds)
        for index, seed in enumerate(seeds):
            if seed.id != seed_id:
                continue
            if seed.status == "REJECTED":
                raise OntologiError("Rejected seeds cannot be reinforced")
            ceiling = 1.0 if seed.status == "VERIFIED" else 0.69
            strengthened = replace(seed, confidence=min(ceiling, seed.confidence + amount))
            seeds[index] = strengthened
            program = Program(self.engine.program.version, tuple(seeds), self.engine.program.links)
            validate(program)
            self.engine.program = program
            self.observe([seed_id], now=now)
            record = self.records[seed_id]
            self.records[seed_id] = replace(record, reinforcements=record.reinforcements + 1)
            return strengthened
        raise OntologiError(f"Unknown seed: {seed_id}")

    def age(
        self,
        *,
        now: datetime | None = None,
        candidate_stale_days: int = 30,
        candidate_archive_days: int = 90,
        verified_decay_per_day: float = 0.002,
    ) -> dict:
        now_value = now or datetime.now(UTC)
        if candidate_stale_days < 1 or candidate_archive_days <= candidate_stale_days:
            raise OntologiError("Archive horizon must be greater than stale horizon")
        if not 0.0 <= verified_decay_per_day <= 0.02:
            raise OntologiError("Verified decay must be between 0 and 0.02 per day")

        seed_by_id = {seed.id: seed for seed in self.engine.program.seeds}
        seeds = list(self.engine.program.seeds)
        changed_confidence: list[str] = []
        stale: list[str] = []
        archived: list[str] = []

        for seed_id, record in list(self.records.items()):
            seed = seed_by_id.get(seed_id)
            if seed is None:
                continue
            days = max(0, (now_value - self._dt(record.last_seen)).days)
            state = record.state
            if seed.status == "CANDIDATE":
                if days >= candidate_archive_days:
                    state = "ARCHIVED"
                    archived.append(seed_id)
                elif days >= candidate_stale_days:
                    state = "STALE"
                    stale.append(seed_id)
            elif seed.status == "VERIFIED" and days > 0 and verified_decay_per_day > 0:
                new_confidence = max(0.7, seed.confidence - (days * verified_decay_per_day))
                if new_confidence != seed.confidence:
                    for index, item in enumerate(seeds):
                        if item.id == seed_id:
                            seeds[index] = replace(item, confidence=round(new_confidence, 6))
                            changed_confidence.append(seed_id)
                            break
            self.records[seed_id] = replace(record, state=state)

        program = Program(self.engine.program.version, tuple(seeds), self.engine.program.links)
        validate(program)
        self.engine.program = program
        return {
            "gardenVersion": GARDEN_VERSION,
            "staleSeedIds": sorted(stale),
            "archivedSeedIds": sorted(archived),
            "confidenceDecayedSeedIds": sorted(changed_confidence),
        }

    def contradictions(self) -> list[dict]:
        seed_by_id = {seed.id: seed for seed in self.engine.program.seeds}
        results: list[dict] = []
        for link in self.engine.program.links:
            if link.relation != "CONTRADICTS":
                continue
            left = seed_by_id[link.source]
            right = seed_by_id[link.target]
            if left.status == "REJECTED" or right.status == "REJECTED":
                continue
            results.append(
                {
                    "left": left.id,
                    "leftStatus": left.status,
                    "leftConfidence": left.confidence,
                    "right": right.id,
                    "rightStatus": right.status,
                    "rightConfidence": right.confidence,
                    "resolution": "REVIEW_REQUIRED",
                }
            )
        return results

    def archive(self, seed_id: str) -> MemoryRecord:
        if seed_id not in {seed.id for seed in self.engine.program.seeds}:
            raise OntologiError(f"Unknown seed: {seed_id}")
        record = self.records.get(seed_id)
        if record is None:
            raise OntologiError("Seed must be observed before it can be archived")
        archived = replace(record, state="ARCHIVED")
        self.records[seed_id] = archived
        return archived

    def active_seed_ids(self) -> list[str]:
        return sorted(seed_id for seed_id, record in self.records.items() if record.state == "ACTIVE")

    def snapshot(self) -> str:
        payload = {
            "gardenVersion": GARDEN_VERSION,
            "records": [asdict(self.records[key]) for key in sorted(self.records)],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_snapshot(cls, engine: OntologiEngine, payload: str) -> "MemoryGarden":
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise OntologiError("Invalid Memory Garden snapshot") from exc
        if data.get("gardenVersion") != GARDEN_VERSION:
            raise OntologiError("Unsupported Memory Garden snapshot version")
        records: dict[str, MemoryRecord] = {}
        for raw in data.get("records", []):
            record = MemoryRecord(**raw)
            if record.state not in MEMORY_STATES:
                raise OntologiError(f"Unsupported memory state: {record.state}")
            records[record.seed_id] = record
        return cls(engine, records)
