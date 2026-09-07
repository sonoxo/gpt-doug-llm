from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterable

from va3lm.ontologi import OntologiEngine
from va3lm.seed_forge import ALLOWED_EXTENSIONS, ForgeArtifact, SeedForge

HARVESTER_VERSION = "1.0"
DEFAULT_ROOTS = ("va3lm", "docs", "intel", "rvia-intel", "agents", "tools")
BLOCKED_PARTS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", "dist", "build"}
BLOCKED_FILENAMES = {".env", ".env.local", ".env.production", "credentials.json", "secrets.json", "token.json"}
BLOCKED_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}


class OntologiHarvester:
    """Scan approved repository knowledge roots and feed changed text artifacts into Seed Forge."""

    def __init__(self, engine: OntologiEngine) -> None:
        self.engine = engine
        self.forge = SeedForge(engine)

    @staticmethod
    def _digest(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _load_checkpoint(path: Path | None) -> dict[str, str]:
        if path is None or not path.exists():
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not all(isinstance(k, str) and isinstance(v, str) for k, v in data.items()):
            raise ValueError("Invalid ONTologi Harvester checkpoint")
        return data

    @staticmethod
    def _save_checkpoint(path: Path | None, checkpoint: dict[str, str]) -> None:
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(checkpoint, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    @staticmethod
    def _allowed_file(path: Path) -> bool:
        if path.name in BLOCKED_FILENAMES or path.suffix.lower() in BLOCKED_SUFFIXES:
            return False
        if path.suffix.lower() not in ALLOWED_EXTENSIONS:
            return False
        return not any(part in BLOCKED_PARTS for part in path.parts)

    def harvest(
        self,
        repo_root: Path,
        *,
        roots: Iterable[str] = DEFAULT_ROOTS,
        checkpoint_path: Path | None = None,
        max_files: int = 200,
        max_bytes_per_file: int = 512_000,
        max_seeds_per_file: int = 8,
    ) -> dict:
        root = repo_root.resolve()
        checkpoint = self._load_checkpoint(checkpoint_path)
        processed = 0
        unchanged = 0
        blocked = 0
        oversized = 0
        unreadable = 0
        created = 0
        duplicates = 0
        touched: list[str] = []

        candidates: list[Path] = []
        for relative_root in roots:
            target = (root / relative_root).resolve()
            if target != root and root not in target.parents:
                raise ValueError("Harvester root escaped repository boundary")
            if not target.exists():
                continue
            for path in target.rglob("*"):
                if path.is_file() and not path.is_symlink():
                    candidates.append(path)

        for path in sorted(set(candidates)):
            if processed >= max(1, max_files):
                break
            relative = path.relative_to(root)
            if not self._allowed_file(relative):
                blocked += 1
                continue
            if path.stat().st_size > max_bytes_per_file:
                oversized += 1
                continue
            try:
                content = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                unreadable += 1
                continue
            key = relative.as_posix()
            digest = self._digest(content)
            if checkpoint.get(key) == digest:
                unchanged += 1
                continue
            result = self.forge.ingest(
                ForgeArtifact(path=key, content=content, verified_source=False, tags=("harvested",)),
                max_seeds=max_seeds_per_file,
            )
            checkpoint[key] = digest
            processed += 1
            created += result["created"]
            duplicates += result["duplicates"]
            touched.append(key)

        self._save_checkpoint(checkpoint_path, checkpoint)
        return {
            "harvesterVersion": HARVESTER_VERSION,
            "processedFiles": processed,
            "unchangedFiles": unchanged,
            "blockedFiles": blocked,
            "oversizedFiles": oversized,
            "unreadableFiles": unreadable,
            "createdSeeds": created,
            "duplicateSeeds": duplicates,
            "touchedFiles": touched,
            "candidateQueueSize": len(self.forge.queue()),
            "automaticPromotion": False,
        }
