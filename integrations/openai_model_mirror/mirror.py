"""Approved OpenAI Hugging Face model mirroring with optional local REA inspection.

Only public, ungated, permissively licensed models in the verified openai
organization are eligible. Nothing accesses hosted proprietary model weights.
No inference code or downloaded model code is executed by this module.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "gpt-doug.openai-model-mirror.v1"
ALLOW_LICENSES = frozenset({"apache-2.0", "mit", "bsd-2-clause", "bsd-3-clause", "cc0-1.0"})
REPO_RE = re.compile(r"^openai/[A-Za-z0-9][A-Za-z0-9._-]{0,95}$")
SHA_RE = re.compile(r"^[0-9a-f]{40}$")
REA_FORMATS = {".safetensors", ".gguf"}
WEIGHT_FORMATS = {".safetensors", ".gguf", ".bin", ".pt", ".pth", ".ckpt", ".msgpack", ".h5"}
MAX_CATALOG = 5000
MAX_FILES = 3000
DEFAULT_ROOT = Path.home() / ".cache" / "gpt-doug" / "openai-models"


class MirrorError(RuntimeError):
    """Fail closed on unverified repository identity, authorization, or storage."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _hub():
    try:
        from huggingface_hub import HfApi, snapshot_download
    except ImportError as exc:
        raise MirrorError("Install the free huggingface_hub package to use the official model Hub") from exc
    return HfApi(), snapshot_download


def valid_repo(repo_id: str) -> str:
    if not isinstance(repo_id, str) or not REPO_RE.fullmatch(repo_id):
        raise MirrorError("only exact openai/<model> Hugging Face repository IDs are accepted")
    return repo_id


def license_for(info: Any) -> str | None:
    tags = getattr(info, "tags", None) or []
    for tag in tags:
        if isinstance(tag, str) and tag.startswith("license:"):
            return tag[8:].lower()
    card = getattr(info, "card_data", None)
    value = card.get("license") if isinstance(card, dict) else getattr(card, "license", None)
    return value.lower() if isinstance(value, str) else None


def catalog(api: Any) -> list[dict[str, Any]]:
    """Read the official HF OpenAI organization. No model bytes are downloaded."""
    records: list[dict[str, Any]] = []
    observed: set[str] = set()
    for info in api.list_models(author="openai", limit=None, full=True, cardData=True, token=False):
        if len(records) >= MAX_CATALOG:
            raise MirrorError("official OpenAI catalog exceeds validation limit; cannot claim complete inventory")
        repo_id = valid_repo(info.id)
        if repo_id in observed:
            raise MirrorError("duplicate repository in official organization catalog")
        observed.add(repo_id)
        sha = getattr(info, "sha", None)
        if not isinstance(sha, str) or not SHA_RE.fullmatch(sha):
            raise MirrorError("catalog entry lacks a pinned revision: " + repo_id)
        gated = getattr(info, "gated", False)
        disabled = getattr(info, "disabled", False)
        private = getattr(info, "private", False)
        license_name = license_for(info)
        allowed = gated in (False, None) and not disabled and not private and license_name in ALLOW_LICENSES
        records.append({
            "repo_id": repo_id,
            "sha": sha,
            "license": license_name,
            "eligible": allowed,
            "reason": "permissive-public" if allowed else "gated/private/disabled or license not approved",
            "hub_url": "https://huggingface.co/" + repo_id,
        })
    return sorted(records, key=lambda x: x["repo_id"])


def _file_size(sibling: Any) -> int | None:
    value = getattr(sibling, "size", None)
    if type(value) is int and value >= 0:
        return value
    lfs = getattr(sibling, "lfs", None)
    size = lfs.get("size") if isinstance(lfs, dict) else getattr(lfs, "size", None)
    return size if type(size) is int and size >= 0 else None


def _safe_name(name: Any) -> bool:
    if not isinstance(name, str) or not name or "\\" in name or "\x00" in name:
        return False
    rel = PurePosixPath(name)
    return rel.as_posix() == name and not rel.is_absolute() and bool(rel.parts) and all(part not in {"", ".", ".."} for part in rel.parts)


def select_models(records: list[dict[str, Any]], *, all_models: bool, models: str | None) -> list[dict[str, Any]]:
    if all_models == bool(models):
        raise MirrorError("select either --all or --models openai/name[,openai/name]")
    known = {item["repo_id"]: item for item in records}
    if all_models:
        return records
    names = [valid_repo(x.strip()) for x in models.split(",")]
    if not names or len(names) != len(set(names)):
        raise MirrorError("no or duplicate requested models")
    missing = set(names) - set(known)
    if missing:
        raise MirrorError("not found in verified official OpenAI catalog: " + ", ".join(sorted(missing)))
    return [known[name] for name in names]


def plan(api: Any, selected: list[dict[str, Any]]) -> dict[str, Any]:
    entries: list[dict[str, Any]] = []
    total_bytes = 0
    for item in selected:
        entry = dict(item)
        if entry["eligible"]:
            try:
                info = api.model_info(item["repo_id"], revision=item["sha"], files_metadata=True, token=False)
                if getattr(info, "sha", None) != item["sha"] or getattr(info, "id", None) != item["repo_id"]:
                    raise MirrorError("pinned identity changed")
                if (license_for(info) != item["license"] or getattr(info, "gated", False) not in (False, None)
                    or getattr(info, "private", False) or getattr(info, "disabled", False)):
                    raise MirrorError("license or access changed")
                siblings = getattr(info, "siblings", None)
                if not isinstance(siblings, list) or len(siblings) > MAX_FILES:
                    raise MirrorError("missing or oversized file inventory")
                files = []
                for s in siblings:
                    name = getattr(s, "rfilename", None)
                    size = _file_size(s)
                    if not _safe_name(name) or size is None:
                        raise MirrorError("unsafe file name or unknown file size")
                    files.append((name, size))
                if len(files) != len(set(name for name, _ in files)):
                    raise MirrorError("duplicate file name")
                if not any(PurePosixPath(name).suffix.lower() in WEIGHT_FORMATS for name, _ in files):
                    raise MirrorError("no recognized weight artifact in repository")
                entry["size_bytes"] = sum(size for _, size in files)
                entry["file_count"] = len(files)
                total_bytes += entry["size_bytes"]
            except (MirrorError, ValueError, OSError) as exc:
                entry["eligible"] = False
                entry["reason"] = str(exc)
        entries.append(entry)
    return {
        "schema": SCHEMA,
        "status": "planned-no-download",
        "fetched_at": utc_now(),
        "selected": len(entries),
        "eligible": sum(bool(item["eligible"]) for item in entries),
        "blocked": sum(not item["eligible"] for item in entries),
        "total_bytes": total_bytes,
        "models": entries,
    }


def validate_budget(manifest: dict[str, Any], root: Path, max_gb: float, *, allow_partial: bool) -> None:
    if not (0 < max_gb <= 100000):
        raise MirrorError("--max-gb must be a positive, bounded storage allocation")
    if manifest["blocked"] and not allow_partial:
        raise MirrorError("some repositories could not be approved; review the plan or pass --allow-partial")
    if manifest["eligible"] == 0:
        raise MirrorError("no approved models in this plan")
    if manifest["total_bytes"] > int(max_gb * 1_000_000_000):
        raise MirrorError("model snapshot sizes exceed your explicit storage budget")
    existing = root.expanduser().resolve()
    while not existing.exists():
        if existing == existing.parent:
            raise MirrorError("cannot resolve storage volume")
        existing = existing.parent
    if shutil.disk_usage(existing).free < manifest["total_bytes"] + 256 * 1024 * 1024:
        raise MirrorError("insufficient free space for planned download")


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as f:
        temp_name = f.name
        json.dump(value, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(temp_name, path)


def _hashed_files(path: Path) -> list[dict[str, Any]]:
    results = []
    for item in sorted(path.rglob("*")):
        if ".cache" in item.relative_to(path).parts:
            continue
        if item.is_symlink():
            raise MirrorError("a downloaded artifact is a symlink")
        if not item.is_file():
            continue
        digest = hashlib.sha256()
        with item.open("rb") as data:
            for chunk in iter(lambda: data.read(4 * 1024 * 1024), b""):
                digest.update(chunk)
        results.append({"path": item.relative_to(path).as_posix(), "bytes": item.stat().st_size, "sha256": digest.hexdigest()})
    return results


def sync_models(manifest: dict[str, Any], root: Path, max_gb: float, *, yes: bool, allow_partial: bool,
                snapshot_download: Any) -> dict[str, Any]:
    if not yes:
        raise MirrorError("explicit --yes is required; plan and check licenses/storage first")
    validate_budget(manifest, root, max_gb, allow_partial=allow_partial)
    root = root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    receipts = []
    for model in manifest["models"]:
        if not model["eligible"]:
            receipts.append({"repo_id": model["repo_id"], "status": "skipped", "reason": model["reason"]})
            continue
        dest = root / model["repo_id"]
        old_manifest = root / ".manifests" / (model["repo_id"].split("/", 1)[1] + ".json")
        if dest.exists() and any(dest.iterdir()):
            if not old_manifest.is_file():
                raise MirrorError("non-empty model directory without a verified receipt; move it aside")
            try:
                old = json.loads(old_manifest.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise MirrorError("existing model receipt is unreadable") from exc
            if old.get("revision") != model["sha"]:
                raise MirrorError("existing model uses a different revision; archive it before changing versions")
        dest.mkdir(parents=True, exist_ok=True)
        # Official HF client downloads a pinned snapshot; no downloaded code is executed.
        snapshot_download(repo_id=model["repo_id"], revision=model["sha"],
                          local_dir=str(dest), token=False, max_workers=4)
        files = _hashed_files(dest)
        if not any(PurePosixPath(f["path"]).suffix.lower() in WEIGHT_FORMATS for f in files):
            raise MirrorError("download completed without a recognized model weight file")
        receipt = {"schema": SCHEMA, "repo_id": model["repo_id"], "revision": model["sha"],
                   "license": model["license"], "downloaded_at": utc_now(), "status": "mirrored-local",
                   "source": model["hub_url"], "files": files, "command_execution": False,
                   "rea_supported_files": [f["path"] for f in files if PurePosixPath(f["path"]).suffix.lower() in REA_FORMATS]}
        _write_json(root / ".manifests" / (model["repo_id"].split("/", 1)[1] + ".json"), receipt)
        receipts.append({"repo_id": model["repo_id"], "status": "mirrored-local", "files": len(files)})
    return {"schema": SCHEMA, "results": receipts, "root": str(root), "scope": "public-openai-models-only"}


def inspect_with_rea(root: Path, model: str, *, rea_bin: str | None = None,
                     max_files: int = 100) -> dict[str, Any]:
    valid_repo(model)
    root = root.expanduser().resolve(strict=True)
    metadata = root / ".manifests" / (model.split("/", 1)[1] + ".json")
    try:
        receipt = json.loads(metadata.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MirrorError("no verified local model mirror manifest") from exc
    if receipt.get("schema") != SCHEMA or receipt.get("repo_id") != model:
        raise MirrorError("model mirror manifest does not match")
    if not receipt.get("files"):
        raise MirrorError("empty model mirror receipt")
    rea = rea_bin or shutil.which("rea")
    if not rea or not Path(rea).is_file():
        raise MirrorError("REA not installed; get rea-agents from morluto/rea")
    files = [f["path"] for f in receipt["files"] if PurePosixPath(f["path"]).suffix.lower() in REA_FORMATS]
    if not files:
        raise MirrorError("REA only supports local .safetensors and .gguf weight metadata")
    if not 0 < max_files <= 1000 or len(files) > max_files:
        raise MirrorError("number of REA files exceeds --max-files; explicitly increase limit")
    reports = []
    for rel in files:
        if not _safe_name(rel):
            raise MirrorError("unsafe model file name in manifest")
        model_dir = root / model
        if model_dir.is_symlink() or not model_dir.resolve().is_relative_to(root):
            raise MirrorError("model directory escaped approved root")
        file = model_dir / rel
        if file.is_symlink() or not file.is_file() or not file.resolve().is_relative_to(model_dir.resolve()):
            raise MirrorError("model artifact missing or escaped mirrored directory")
        # Integrity check before inspection, including weights, not only header hashes.
        expected = next(f["sha256"] for f in receipt["files"] if f["path"] == rel)
        h = hashlib.sha256()
        with file.open("rb") as data:
            for chunk in iter(lambda: data.read(4 * 1024 * 1024), b""):
                h.update(chunk)
        if h.hexdigest() != expected:
            raise MirrorError("model weight changed since mirror: " + rel)
        with tempfile.TemporaryDirectory() as temp:
            evidence = Path(temp) / "evidence.json"
            try:
                completed = subprocess.run([str(rea), "inspect-model-artifact", str(file),
                                            "--detail", "summary", "--evidence_output", str(evidence), "--json"],
                                           capture_output=True, timeout=180, check=False)
            except subprocess.TimeoutExpired as exc:
                raise MirrorError("REA model inspection exceeded timeout") from exc
            if completed.returncode != 0 or len(completed.stdout) > 1024 * 1024:
                raise MirrorError("REA failed or emitted an oversized summary")
            try:
                summary = json.loads(completed.stdout)
            except ValueError as exc:
                raise MirrorError("REA did not return valid JSON") from exc
            if not isinstance(summary, dict) or not evidence.is_file():
                raise MirrorError("REA did not produce summary and evidence")
            saved = root / ".rea-evidence" / model.split("/", 1)[1] / (rel.replace("/", "__") + ".json")
            if evidence.stat().st_size > 32 * 1024 * 1024:
                raise MirrorError("REA evidence exceeds bounded output policy")
            saved.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(evidence, saved)
            reports.append({"path": rel, "evidence_path": str(saved), "summary": summary})
    return {"schema": SCHEMA, "model": model, "status": "rea-static-inspection", "results": reports,
            "decoded_weights": False, "recreated_proprietary_model": False}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Mirror and statically inspect publicly licensed OpenAI weights")
    commands = p.add_subparsers(dest="command", required=True)
    commands.add_parser("catalog", help="Read official public Hugging Face model metadata")
    for name in ("plan", "sync"):
        sub = commands.add_parser(name)
        choice = sub.add_mutually_exclusive_group(required=True)
        choice.add_argument("--all", action="store_true")
        choice.add_argument("--models", help="comma-separated exact openai/<model> IDs")
        if name == "sync":
            sub.add_argument("--root", type=Path, default=DEFAULT_ROOT)
            sub.add_argument("--max-gb", type=float, required=True)
            sub.add_argument("--yes", action="store_true")
            sub.add_argument("--allow-partial", action="store_true")
    inspect = commands.add_parser("inspect")
    inspect.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    inspect.add_argument("--model", required=True)
    inspect.add_argument("--max-files", type=int, default=100)
    args = p.parse_args(argv)
    try:
        if args.command == "inspect":
            result = inspect_with_rea(args.root, args.model, max_files=args.max_files)
        else:
            api, download = _hub()
            records = catalog(api)
            if args.command == "catalog":
                result = {"schema": SCHEMA, "source": "https://huggingface.co/openai",
                          "count": len(records), "models": records, "downloaded": False}
            else:
                selected = select_models(records, all_models=args.all, models=args.models)
                manifest = plan(api, selected)
                if args.command == "plan":
                    result = manifest
                else:
                    result = sync_models(manifest, args.root, args.max_gb, yes=args.yes,
                                         allow_partial=args.allow_partial, snapshot_download=download)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
