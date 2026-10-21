"""Offline, cross-host REA evidence verification; no network, writes, or agent launches.

Manifests and evidence may be copied between approved machines. Byte hashes show
file integrity only: they are not signatures or proof of source authenticity.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat

MAX_MANIFESTS = 32
MAX_MANIFEST_BYTES = 1024 * 1024
MAX_EVIDENCE_BYTES = 64 * 1024 * 1024
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")
_EVIDENCE = re.compile(r"[0-9]{2}\.json\Z")


def _load(path: Path, limit: int):
    if path.is_symlink():
        raise ValueError("regular non-symlink file required")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError("regular non-symlink file required")
        raw = stream.read(limit + 1)
    if not raw or len(raw) > limit:
        raise ValueError("empty or oversized file")
    return raw, json.loads(raw)


def _check_one(value: str) -> dict:
    path = Path(value).expanduser()
    result: dict = {"integrity": "BLOCKED", "manifest": str(path),
                    "validated_jobs": 0, "declared_jobs": 0}
    try:
        if not path.is_absolute():
            raise ValueError("manifest path must be absolute")
        raw, manifest = _load(path, MAX_MANIFEST_BYTES)
        result["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
        if not isinstance(manifest, dict) or manifest.get("system") != "SONOXO_GPT_CHAOS_REA_SWARM":
            raise ValueError("unknown evidence schema")
        if manifest.get("schema_version") != 1:
            raise ValueError("unknown schema version")
        rows = manifest.get("results")
        if not isinstance(rows, list) or not 1 <= len(rows) <= 8:
            raise ValueError("invalid job inventory")
        if manifest.get("state") not in ("PASS", "BLOCKED"):
            raise ValueError("unrecognized run state")
        seen: set[str] = set()
        blocked = 0
        result["declared_jobs"] = len(rows)
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError("invalid job record")
            ident, state = row.get("id"), row.get("state")
            if not isinstance(ident, str) or not re.fullmatch(r"[0-9]{2}", ident):
                raise ValueError("invalid job identifier")
            if ident in seen:
                raise ValueError("duplicate job identifier")
            seen.add(ident)
            if state == "BLOCKED":
                blocked += 1
                if "evidence" in row or "sha256" in row:
                    raise ValueError("blocked job claims evidence")
                continue
            if state != "PASS":
                raise ValueError("unknown job state")
            filename, digest, size = row.get("evidence"), row.get("sha256"), row.get("bytes")
            if filename != ident + ".json" or not _EVIDENCE.fullmatch(str(filename)):
                raise ValueError("unsafe evidence filename")
            if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
                raise ValueError("invalid evidence digest")
            if type(size) is not int or not 0 < size <= MAX_EVIDENCE_BYTES:
                raise ValueError("invalid evidence byte count")
            data, decoded = _load(path.parent / filename, MAX_EVIDENCE_BYTES)
            if len(data) != size or hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("evidence integrity mismatch")
            if not isinstance(decoded, (dict, list)):
                raise ValueError("invalid evidence document")
            result["validated_jobs"] += 1
        if (blocked == 0) != (manifest["state"] == "PASS"):
            raise ValueError("inconsistent run state")
        result["integrity"] = "VERIFIED" if blocked == 0 else "PARTIAL"
        result["blocked_jobs"] = blocked
    except (OSError, UnicodeError, ValueError, TypeError) as exc:
        result["reason"] = str(exc)[:200]
    return result


def verify_manifests(paths: list[str]) -> dict:
    """Verify up to 32 relocated run bundles, without trusting producer locations."""
    if not 1 <= len(paths) <= MAX_MANIFESTS:
        raise ValueError("provide between 1 and 32 manifest paths")
    if len(paths) != len(set(paths)):
        raise ValueError("duplicate manifest path")
    manifests = [_check_one(p) for p in paths]
    states = {m["integrity"] for m in manifests}
    return {
        "system": "SONOXO_REA_EVIDENCE_FEDERATION",
        "schema_version": 1,
        "integrity": ("BLOCKED" if "BLOCKED" in states else
                      "PARTIAL" if "PARTIAL" in states else "VERIFIED"),
        "manifest_count": len(manifests),
        "validated_jobs": sum(m["validated_jobs"] for m in manifests),
        "manifests": manifests,
        "boundary": "offline_sha256_integrity_only_not_authenticity_or_live_status",
        "remote_requests": 0,
        "remote_actions": 0,
    }


def run_cli(args) -> int:
    try:
        result = verify_manifests(args.manifest)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["integrity"] == "VERIFIED" else 1
    except (ValueError, OSError) as exc:
        print(json.dumps({"system": "SONOXO_REA_EVIDENCE_FEDERATION",
                          "integrity": "BLOCKED", "reason": str(exc)[:200]}))
        return 1
