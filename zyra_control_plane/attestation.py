"""Signed autonomous-change attestations."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from pathlib import Path
from typing import Any


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


class AttestationSigner:
    def __init__(self, key_path: str | Path) -> None:
        self.key_path = Path(key_path)
        self.key_path.parent.mkdir(parents=True, exist_ok=True)
        if self.key_path.exists():
            self.key = self.key_path.read_bytes()
        else:
            self.key = secrets.token_bytes(32)
            self.key_path.write_bytes(self.key)
            try:
                self.key_path.chmod(0o600)
            except OSError:
                pass

    def sign(
        self,
        *,
        mission_id: str,
        prompt: str,
        commit_sha: str | None,
        model_route: str,
        changed_files: list[str],
        checks: list[dict[str, Any]],
        journal_head: str,
        artifact_digest: str | None = None,
        sbom_digest: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "schema": "zyra.attestation.v1",
            "created_at": time.time(),
            "mission_id": mission_id,
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "commit_sha": commit_sha,
            "model_route": model_route,
            "changed_files": sorted(changed_files),
            "checks": checks,
            "journal_head": journal_head,
            "artifact_digest": artifact_digest,
            "sbom_digest": sbom_digest,
        }
        digest = hashlib.sha256(_canonical(payload)).hexdigest()
        signature = hmac.new(self.key, digest.encode(), hashlib.sha256).hexdigest()
        return {**payload, "digest": digest, "signature": signature}

    def verify(self, attestation: dict[str, Any]) -> bool:
        base = {key: value for key, value in attestation.items() if key not in {"digest", "signature"}}
        digest = hashlib.sha256(_canonical(base)).hexdigest()
        signature = hmac.new(self.key, digest.encode(), hashlib.sha256).hexdigest()
        return hmac.compare_digest(str(attestation.get("digest", "")), digest) and hmac.compare_digest(
            str(attestation.get("signature", "")), signature
        )

    @staticmethod
    def write(path: str | Path, attestation: dict[str, Any]) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(attestation, indent=2, sort_keys=True) + "\n", encoding="utf-8")
