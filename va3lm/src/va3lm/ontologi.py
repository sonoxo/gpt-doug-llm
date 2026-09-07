from __future__ import annotations

import re
import shlex
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Iterable

ONTOLOGI_VERSION = "1.0"
SEED_TYPES = {"Agent", "Capability", "Claim", "Concept", "Evidence", "Rule", "Source", "System"}
RELATION_TYPES = {"CORROBORATES", "DERIVED_FROM", "EVIDENCES", "GOVERNS", "REQUIRES", "SUPPORTS", "TEACHES", "USES"}
SEED_STATES = {"CANDIDATE", "VERIFIED", "REJECTED"}

CORE_ONTOLOGI = r'''ONTOLOGI 1.0
SEED agent:virginia Agent "Virginia is the local RVIA reasoning and coding runtime." status=VERIFIED confidence=1.0 tags=virginia,rvia,reasoning,coding
SEED system:rvia System "RVIA routes governed missions through evidence and audit stages." status=VERIFIED confidence=1.0 tags=rvia,mission,governance,audit
SEED concept:ontology Concept "Ontology represents knowledge as typed entities, typed relationships, governed actions, and evidence." status=VERIFIED confidence=1.0 tags=ontology,graph,knowledge
SEED concept:provenance Concept "Knowledge should preserve where it came from and distinguish verified evidence from candidates." status=VERIFIED confidence=1.0 tags=provenance,evidence,trust
SEED concept:ontologi Concept "ONTologi is the seed language used by Virginia and RVIA to encode, connect, retrieve, and govern knowledge." status=VERIFIED confidence=1.0 tags=ontologi,language,seeds,learning
SEED capability:seed_retrieval Capability "Retrieve the most relevant ontology seeds for a mission before planning." status=VERIFIED confidence=1.0 tags=memory,retrieval,reasoning
SEED capability:governed_learning Capability "Stage new knowledge as candidate seeds and promote only with evidence." status=VERIFIED confidence=1.0 tags=learning,governance,evidence
SEED source:repo_ontology Source "va3lm/src/va3lm/ontology.py" status=VERIFIED confidence=1.0 tags=source,ontology,repo
SEED source:repo_rvia Source "va3lm/src/va3lm/rvia.py" status=VERIFIED confidence=1.0 tags=source,rvia,repo
SEED source:video_wzgkc6Iegx8 Source "https://www.youtube.com/watch?v=wzgkc6Iegx8" status=CANDIDATE confidence=0.0 tags=source,video,pending-verification
LINK agent:virginia USES concept:ontologi
LINK system:rvia USES concept:ontologi
LINK concept:ontologi REQUIRES concept:provenance
LINK concept:ontologi SUPPORTS capability:seed_retrieval
LINK concept:ontologi SUPPORTS capability:governed_learning
LINK source:repo_ontology EVIDENCES concept:ontology
LINK source:repo_rvia EVIDENCES system:rvia
'''


@dataclass(frozen=True)
class Seed:
    id: str
    type: str
    text: str
    status: str = "CANDIDATE"
    confidence: float = 0.0
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class Link:
    source: str
    relation: str
    target: str


@dataclass(frozen=True)
class Program:
    version: str
    seeds: tuple[Seed, ...]
    links: tuple[Link, ...]


class OntologiError(ValueError):
    pass


def _options(tokens: Iterable[str]) -> dict[str, str]:
    result: dict[str, str] = {}
    for token in tokens:
        if "=" not in token:
            raise OntologiError(f"Expected key=value option, got: {token}")
        key, value = token.split("=", 1)
        result[key] = value
    return result


def parse(source: str) -> Program:
    version: str | None = None
    seeds: list[Seed] = []
    links: list[Link] = []

    for line_number, raw in enumerate(source.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            raise OntologiError(f"Line {line_number}: {exc}") from exc
        if not tokens:
            continue
        keyword = tokens[0].upper()

        if keyword == "ONTOLOGI":
            if len(tokens) != 2:
                raise OntologiError(f"Line {line_number}: ONTOLOGI requires one version")
            version = tokens[1]
            continue

        if keyword == "SEED":
            if len(tokens) < 4:
                raise OntologiError(f"Line {line_number}: SEED requires id, type, and text")
            opts = _options(tokens[4:])
            tags = tuple(filter(None, opts.get("tags", "").split(",")))
            try:
                confidence = float(opts.get("confidence", "0"))
            except ValueError as exc:
                raise OntologiError(f"Line {line_number}: invalid confidence") from exc
            seeds.append(
                Seed(
                    id=tokens[1],
                    type=tokens[2],
                    text=tokens[3],
                    status=opts.get("status", "CANDIDATE").upper(),
                    confidence=confidence,
                    tags=tags,
                )
            )
            continue

        if keyword == "LINK":
            if len(tokens) != 4:
                raise OntologiError(f"Line {line_number}: LINK requires source, relation, target")
            links.append(Link(tokens[1], tokens[2].upper(), tokens[3]))
            continue

        raise OntologiError(f"Line {line_number}: unknown keyword {tokens[0]}")

    if version is None:
        raise OntologiError("Missing ONTOLOGI version header")
    program = Program(version=version, seeds=tuple(seeds), links=tuple(links))
    validate(program)
    return program


def validate(program: Program) -> None:
    if program.version != ONTOLOGI_VERSION:
        raise OntologiError(f"Unsupported ONTologi version: {program.version}")
    ids: set[str] = set()
    for seed in program.seeds:
        if seed.id in ids:
            raise OntologiError(f"Duplicate seed id: {seed.id}")
        ids.add(seed.id)
        if seed.type not in SEED_TYPES:
            raise OntologiError(f"Unsupported seed type: {seed.type}")
        if seed.status not in SEED_STATES:
            raise OntologiError(f"Unsupported seed status: {seed.status}")
        if not 0.0 <= seed.confidence <= 1.0:
            raise OntologiError(f"Seed confidence must be 0..1: {seed.id}")
    for link in program.links:
        if link.relation not in RELATION_TYPES:
            raise OntologiError(f"Unsupported relation type: {link.relation}")
        if link.source not in ids or link.target not in ids:
            raise OntologiError(f"Link endpoint missing: {link.source} -> {link.target}")


def compile_graph(program: Program) -> dict:
    return {
        "language": "ONTologi",
        "version": program.version,
        "seeds": [
            {
                "id": seed.id,
                "type": seed.type,
                "text": seed.text,
                "status": seed.status,
                "confidence": seed.confidence,
                "tags": list(seed.tags),
            }
            for seed in program.seeds
        ],
        "links": [
            {"source": link.source, "relation": link.relation, "target": link.target}
            for link in program.links
        ],
    }


def _terms(value: str) -> set[str]:
    return set(re.findall(r"[a-z0-9_]+", value.lower()))


class OntologiEngine:
    """Small provenance-aware seed memory for Virginia/RVIA planning context."""

    def __init__(self, program: Program) -> None:
        validate(program)
        self.program = program

    @classmethod
    def load_default(cls) -> "OntologiEngine":
        repo_seed = Path(__file__).resolve().parents[2] / "knowledge" / "core.ontologi"
        source = repo_seed.read_text(encoding="utf-8") if repo_seed.exists() else CORE_ONTOLOGI
        return cls(parse(source))

    def retrieve(self, query: str, limit: int = 6, verified_only: bool = False) -> list[dict]:
        query_terms = _terms(query)
        scored: list[tuple[float, Seed]] = []
        for seed in self.program.seeds:
            if seed.status == "REJECTED" or (verified_only and seed.status != "VERIFIED"):
                continue
            haystack = _terms(" ".join((seed.id, seed.text, *seed.tags)))
            overlap = len(query_terms & haystack)
            if overlap == 0:
                continue
            trust_bonus = 0.25 if seed.status == "VERIFIED" else 0.0
            score = overlap + seed.confidence + trust_bonus
            scored.append((score, seed))
        scored.sort(key=lambda item: (-item[0], item[1].id))
        return [
            {
                "id": seed.id,
                "type": seed.type,
                "text": seed.text,
                "status": seed.status,
                "confidence": seed.confidence,
                "tags": list(seed.tags),
                "score": round(score, 3),
            }
            for score, seed in scored[: max(1, min(limit, 20))]
        ]

    def context(self, query: str, limit: int = 6) -> dict:
        seeds = self.retrieve(query, limit=limit)
        selected = {item["id"] for item in seeds}
        links = [
            {"source": link.source, "relation": link.relation, "target": link.target}
            for link in self.program.links
            if link.source in selected or link.target in selected
        ]
        return {
            "language": "ONTologi",
            "version": self.program.version,
            "query": query,
            "seeds": seeds,
            "links": links,
            "candidateKnowledgePresent": any(seed["status"] == "CANDIDATE" for seed in seeds),
        }

    def stage_seed(self, seed_id: str, seed_type: str, text: str, *, tags: Iterable[str] = ()) -> Seed:
        if any(seed.id == seed_id for seed in self.program.seeds):
            raise OntologiError(f"Seed already exists: {seed_id}")
        seed = Seed(seed_id, seed_type, text, status="CANDIDATE", confidence=0.0, tags=tuple(tags))
        candidate = Program(self.program.version, self.program.seeds + (seed,), self.program.links)
        validate(candidate)
        self.program = candidate
        return seed

    def promote_seed(self, seed_id: str, *, confidence: float, evidence_ids: Iterable[str]) -> Seed:
        evidence = tuple(evidence_ids)
        if confidence < 0.7 or not evidence:
            raise OntologiError("Promotion requires confidence >= 0.7 and at least one evidence id")
        seeds = list(self.program.seeds)
        for index, seed in enumerate(seeds):
            if seed.id != seed_id:
                continue
            promoted = replace(seed, status="VERIFIED", confidence=confidence)
            seeds[index] = promoted
            self.program = Program(self.program.version, tuple(seeds), self.program.links)
            validate(self.program)
            return promoted
        raise OntologiError(f"Unknown seed: {seed_id}")
