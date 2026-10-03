from __future__ import annotations

import json
import os
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Callable, Iterable

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / "runtime"
RUNTIME.mkdir(exist_ok=True)
INDEX_FILE = RUNTIME / "hdd-index.jsonl"
META_FILE = RUNTIME / "hdd-index-meta.json"

CATEGORY_EXTENSIONS = {
    "code": {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".c", ".cc", ".cpp", ".h", ".hpp",
        ".rs", ".go", ".rb", ".php", ".swift", ".kt", ".kts", ".scala", ".sh", ".zsh", ".fish",
        ".sql", ".html", ".css", ".scss", ".vue", ".svelte", ".ipynb", ".yaml", ".yml", ".toml",
        ".json", ".xml",
    },
    "documents": {".txt", ".md", ".rtf", ".pdf", ".doc", ".docx", ".odt", ".pages", ".epub"},
    "spreadsheets": {".csv", ".tsv", ".xls", ".xlsx", ".ods", ".numbers"},
    "audio": {".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".aiff", ".mid", ".midi"},
    "video": {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"},
    "images": {".png", ".jpg", ".jpeg", ".gif", ".webp", ".heic", ".tif", ".tiff", ".svg", ".psd"},
    "archives": {".zip", ".tar", ".gz", ".tgz", ".bz2", ".xz", ".7z", ".rar", ".dmg", ".iso"},
    "models_data": {".parquet", ".feather", ".arrow", ".sqlite", ".db", ".bin", ".onnx", ".pt", ".pth", ".safetensors", ".gguf"},
    "apps_packages": {".app", ".pkg", ".deb", ".rpm"},
}

SKIP_DIR_NAMES = {
    ".git", ".svn", ".hg", "node_modules", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache",
    ".pytest_cache", ".cache", "Caches", "Cache", "DerivedData", ".Trash", "Trash",
}


def category_for(path: Path) -> str:
    ext = path.suffix.lower()
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if ext in extensions:
            return category
    return "other"


def _is_hidden(path: Path) -> bool:
    return any(part.startswith(".") and part not in {".", ".."} for part in path.parts)


def _stat_record(path: Path, root: Path) -> dict[str, Any] | None:
    try:
        st = path.stat()
        if not path.is_file():
            return None
        return {
            "path": str(path),
            "relative_path": str(path.relative_to(root)) if path != root else path.name,
            "name": path.name,
            "extension": path.suffix.lower(),
            "category": category_for(path),
            "size": int(st.st_size),
            "modified": float(st.st_mtime),
        }
    except (OSError, PermissionError, ValueError):
        return None


def _iter_files(
    root: Path,
    blocked: Callable[[Path], bool],
    include_hidden: bool,
    max_files: int,
) -> Iterable[Path]:
    count = 0
    stack = [root]
    while stack and count < max_files:
        current = stack.pop()
        if blocked(current):
            continue
        try:
            with os.scandir(current) as it:
                for entry in it:
                    if count >= max_files:
                        break
                    try:
                        p = Path(entry.path)
                        if blocked(p):
                            continue
                        if not include_hidden and (entry.name.startswith(".") or _is_hidden(p.relative_to(root))):
                            continue
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            if entry.name in SKIP_DIR_NAMES:
                                continue
                            stack.append(p)
                        elif entry.is_file(follow_symlinks=False):
                            count += 1
                            yield p
                    except (OSError, PermissionError, ValueError):
                        continue
        except (OSError, PermissionError, NotADirectoryError):
            continue


def build_index(
    root: Path,
    blocked: Callable[[Path], bool],
    *,
    max_files: int = 25000,
    workers: int = 8,
    include_hidden: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    max_files = max(1, min(int(max_files), 100000))
    workers = max(1, min(int(workers), 32))
    started = time.time()

    paths = list(_iter_files(root, blocked, include_hidden, max_files))
    records: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=workers, thread_name_prefix="gptdoug-hdd") as pool:
        futures = [pool.submit(_stat_record, path, root) for path in paths]
        for future in as_completed(futures):
            rec = future.result()
            if rec:
                records.append(rec)

    records.sort(key=lambda item: item["path"].lower())
    tmp = INDEX_FILE.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    tmp.replace(INDEX_FILE)

    meta = {
        "root": str(root),
        "indexed_files": len(records),
        "workers": workers,
        "include_hidden": bool(include_hidden),
        "max_files": max_files,
        "started_at": started,
        "finished_at": time.time(),
        "duration_seconds": round(time.time() - started, 3),
        "content_read": False,
        "cloud_egress": False,
    }
    META_FILE.write_text(json.dumps(meta, indent=2), encoding="utf-8")
    return {"ok": True, **meta, "summary": summarize_records(records)}


def load_records(limit: int | None = None) -> list[dict[str, Any]]:
    if not INDEX_FILE.exists():
        return []
    records: list[dict[str, Any]] = []
    with INDEX_FILE.open("r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if limit is not None and len(records) >= limit:
                break
            try:
                records.append(json.loads(line))
            except Exception:
                continue
    return records


def index_meta() -> dict[str, Any] | None:
    try:
        return json.loads(META_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def summarize_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    categories = Counter(rec.get("category", "other") for rec in records)
    extensions = Counter(rec.get("extension", "") or "[none]" for rec in records)
    total_bytes = sum(int(rec.get("size", 0) or 0) for rec in records)
    return {
        "files": len(records),
        "bytes": total_bytes,
        "gigabytes": round(total_bytes / (1024 ** 3), 3),
        "categories": dict(categories.most_common()),
        "top_extensions": dict(extensions.most_common(20)),
    }


def summary() -> dict[str, Any]:
    records = load_records()
    return {"meta": index_meta(), "summary": summarize_records(records)}


def search_index(
    query: str = "",
    *,
    category: str | None = None,
    extension: str | None = None,
    limit: int = 100,
) -> dict[str, Any]:
    query_lower = query.strip().lower()
    extension_norm = extension.strip().lower() if extension else None
    if extension_norm and not extension_norm.startswith("."):
        extension_norm = "." + extension_norm
    limit = max(1, min(int(limit), 500))
    results = []
    for rec in load_records():
        if query_lower and query_lower not in rec.get("path", "").lower():
            continue
        if category and rec.get("category") != category:
            continue
        if extension_norm and rec.get("extension") != extension_norm:
            continue
        results.append(rec)
        if len(results) >= limit:
            break
    return {"query": query, "category": category, "extension": extension_norm, "count": len(results), "results": results}


def large_files(limit: int = 50, min_bytes: int = 100 * 1024 * 1024) -> dict[str, Any]:
    limit = max(1, min(int(limit), 200))
    min_bytes = max(0, int(min_bytes))
    records = [r for r in load_records() if int(r.get("size", 0)) >= min_bytes]
    records.sort(key=lambda r: int(r.get("size", 0)), reverse=True)
    return {"count": min(len(records), limit), "min_bytes": min_bytes, "results": records[:limit]}


def recent_files(limit: int = 50) -> dict[str, Any]:
    limit = max(1, min(int(limit), 200))
    records = load_records()
    records.sort(key=lambda r: float(r.get("modified", 0)), reverse=True)
    return {"count": min(len(records), limit), "results": records[:limit]}


def duplicate_candidates(limit_groups: int = 50) -> dict[str, Any]:
    """Metadata-only duplicate candidates; does not hash or read file contents."""
    groups: dict[tuple[int, str], list[dict[str, Any]]] = defaultdict(list)
    for rec in load_records():
        size = int(rec.get("size", 0) or 0)
        if size <= 0:
            continue
        groups[(size, rec.get("name", "").lower())].append(rec)
    dupes = [items for items in groups.values() if len(items) > 1]
    dupes.sort(key=lambda items: (len(items), int(items[0].get("size", 0))), reverse=True)
    limit_groups = max(1, min(int(limit_groups), 100))
    return {
        "method": "same-name-and-size metadata candidate only; no content hashing",
        "groups": dupes[:limit_groups],
        "count": min(len(dupes), limit_groups),
    }
