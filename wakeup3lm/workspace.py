from __future__ import annotations

import os
from pathlib import Path


SEARCH_SKIP_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "node_modules",
    "venv",
}
MAX_SEARCH_FILE_BYTES = 2_000_000
MAX_SEARCH_RESULTS = 200


class WorkspaceSecurityError(RuntimeError):
    pass


class WorkspaceFS:
    """Project-scoped filesystem used by Wakeup3lm IDE tools."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def resolve(self, relative_path: str) -> Path:
        candidate = (self.root / relative_path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise WorkspaceSecurityError("Path escapes Wakeup3lm workspace")
        return candidate

    def read_file(self, path: str) -> str:
        return self.resolve(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str) -> dict[str, object]:
        target = self.resolve(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        existed = target.exists()
        target.write_text(content, encoding="utf-8")
        return {"path": path, "created": not existed, "bytes": len(content.encode("utf-8"))}

    def delete_file(self, path: str) -> dict[str, object]:
        target = self.resolve(path)
        if target.is_dir():
            raise WorkspaceSecurityError("Directory deletion is not exposed by this tool")
        if not target.exists():
            return {"path": path, "deleted": False}
        target.unlink()
        return {"path": path, "deleted": True}

    def list_directory(self, path: str = ".") -> list[dict[str, object]]:
        target = self.resolve(path)
        return [
            {"name": child.name, "path": str(child.relative_to(self.root)), "directory": child.is_dir()}
            for child in sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        ]

    def search_files(self, query: str) -> list[str]:
        """Search bounded workspace text while pruning generated dependency trees.

        The previous recursive walk descended into every directory and could read
        arbitrarily large files. This implementation preserves repository-scoped
        search while pruning known generated trees, skipping oversized content,
        and returning immediately once the result contract is full.
        """
        query_lower = query.lower()
        matches: list[str] = []

        for current_root, directories, filenames in os.walk(self.root):
            directories[:] = [name for name in directories if name not in SEARCH_SKIP_DIRS]
            base = Path(current_root)
            for name in filenames:
                item = base / name
                try:
                    rel = str(item.relative_to(self.root))
                except ValueError:
                    continue

                if query_lower in rel.lower():
                    matches.append(rel)
                else:
                    try:
                        if item.stat().st_size > MAX_SEARCH_FILE_BYTES:
                            continue
                        if query_lower in item.read_text(encoding="utf-8", errors="ignore").lower():
                            matches.append(rel)
                    except OSError:
                        continue

                if len(matches) >= MAX_SEARCH_RESULTS:
                    return matches

        return matches
