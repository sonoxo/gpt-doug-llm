from __future__ import annotations

import ast
import hashlib
import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from va3lm.ontologi import Link, OntologiEngine, OntologiError, Program, Seed, validate

FORGE_VERSION = "1.0"
ALLOWED_EXTENSIONS = {".md", ".txt", ".py", ".json", ".yaml", ".yml", ".toml", ".ontologi"}


@dataclass(frozen=True)
class ForgeArtifact:
    path: str
    content: str
    verified_source: bool = False
    tags: tuple[str, ...] = ()


class SeedForge:
    """Convert repository knowledge artifacts into provenance-linked candidate ONTologi seeds."""

    def __init__(self, engine: OntologiEngine) -> None:
        self.engine = engine

    @staticmethod
    def _safe_repo_path(path: str) -> str:
        candidate = PurePosixPath(path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise OntologiError("Seed Forge source path must stay inside the repository")
        if candidate.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise OntologiError(f"Unsupported Seed Forge source type: {candidate.suffix or '<none>'}")
        return candidate.as_posix()

    @staticmethod
    def _fingerprint(value: str) -> str:
        normalized = re.sub(r"\s+", " ", value).strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    @staticmethod
    def _source_id(path: str) -> str:
        return f"source:forge:{SeedForge._fingerprint(path)}"

    @staticmethod
    def _clean_statement(value: str) -> str | None:
        value = re.sub(r"\s+", " ", value).strip(" -#*`\t\r\n")
        if not 24 <= len(value) <= 360:
            return None
        if value.startswith(("http://", "https://")):
            return value
        if re.match(r"^(from|import|def|class|return|if|for|while|try|except)\b", value):
            return None
        return value

    @classmethod
    def _python_statements(cls, content: str) -> list[str]:
        try:
            tree = ast.parse(content)
        except SyntaxError:
            return []
        statements: list[str] = []
        for node in [tree, *ast.walk(tree)]:
            if not isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            doc = ast.get_docstring(node, clean=True)
            if not doc:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+|\n+", doc):
                cleaned = cls._clean_statement(sentence)
                if cleaned:
                    statements.append(cleaned)
        return statements

    @classmethod
    def _text_statements(cls, content: str) -> list[str]:
        statements: list[str] = []
        for raw in content.splitlines():
            line = raw.strip()
            if not line or line.startswith(("```", "<!--")):
                continue
            cleaned = cls._clean_statement(line)
            if cleaned:
                statements.append(cleaned)
        return statements

    @classmethod
    def extract_statements(cls, path: str, content: str) -> list[str]:
        safe_path = cls._safe_repo_path(path)
        if PurePosixPath(safe_path).suffix.lower() == ".py":
            statements = cls._python_statements(content)
        else:
            statements = cls._text_statements(content)
        deduped: list[str] = []
        seen: set[str] = set()
        for statement in statements:
            fingerprint = cls._fingerprint(statement)
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            deduped.append(statement)
        return deduped

    def ingest(self, artifact: ForgeArtifact, *, max_seeds: int = 8) -> dict:
        path = self._safe_repo_path(artifact.path)
        statements = self.extract_statements(path, artifact.content)[: max(1, min(max_seeds, 24))]
        existing_by_id = {seed.id: seed for seed in self.engine.program.seeds}
        existing_text = {self._fingerprint(seed.text): seed.id for seed in self.engine.program.seeds}
        source_id = self._source_id(path)
        seeds = list(self.engine.program.seeds)
        links = list(self.engine.program.links)

        if source_id not in existing_by_id:
            source_seed = Seed(
                id=source_id,
                type="Source",
                text=path,
                status="VERIFIED" if artifact.verified_source else "CANDIDATE",
                confidence=1.0 if artifact.verified_source else 0.0,
                tags=("seed-forge", "repo-source", *artifact.tags),
            )
            seeds.append(source_seed)
            existing_by_id[source_id] = source_seed

        created: list[str] = []
        duplicates: list[str] = []
        for statement in statements:
            fingerprint = self._fingerprint(statement)
            duplicate_id = existing_text.get(fingerprint)
            if duplicate_id:
                duplicates.append(duplicate_id)
                continue
            seed_id = f"claim:forge:{fingerprint}"
            candidate = Seed(
                id=seed_id,
                type="Claim",
                text=statement,
                status="CANDIDATE",
                confidence=0.0,
                tags=("seed-forge", "candidate", *artifact.tags),
            )
            seeds.append(candidate)
            links.append(Link(seed_id, "DERIVED_FROM", source_id))
            existing_text[fingerprint] = seed_id
            created.append(seed_id)

        program = Program(self.engine.program.version, tuple(seeds), tuple(links))
        validate(program)
        self.engine.program = program
        return {
            "forgeVersion": FORGE_VERSION,
            "sourceId": source_id,
            "sourceStatus": existing_by_id[source_id].status,
            "createdSeedIds": created,
            "duplicateSeedIds": duplicates,
            "created": len(created),
            "duplicates": len(duplicates),
            "statementsConsidered": len(statements),
            "automaticPromotion": False,
        }

    def ingest_many(self, artifacts: Iterable[ForgeArtifact], *, max_seeds_per_artifact: int = 8) -> list[dict]:
        return [self.ingest(artifact, max_seeds=max_seeds_per_artifact) for artifact in artifacts]

    def promote(self, seed_id: str, *, confidence: float, evidence_ids: Iterable[str]) -> Seed:
        evidence = tuple(evidence_ids)
        if not evidence:
            raise OntologiError("Seed Forge promotion requires verified evidence")
        seed_by_id = {seed.id: seed for seed in self.engine.program.seeds}
        for evidence_id in evidence:
            item = seed_by_id.get(evidence_id)
            if item is None or item.type not in {"Evidence", "Source"} or item.status != "VERIFIED":
                raise OntologiError(f"Seed Forge evidence is not verified: {evidence_id}")
        return self.engine.promote_seed(seed_id, confidence=confidence, evidence_ids=evidence)

    def queue(self) -> list[dict]:
        provenance = {
            link.source: link.target
            for link in self.engine.program.links
            if link.relation == "DERIVED_FROM"
        }
        return [
            {
                "id": seed.id,
                "text": seed.text,
                "status": seed.status,
                "sourceId": provenance.get(seed.id),
            }
            for seed in self.engine.program.seeds
            if seed.type == "Claim" and seed.status == "CANDIDATE"
        ]
