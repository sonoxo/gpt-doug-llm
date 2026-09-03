from __future__ import annotations

from pathlib import Path


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
        query_lower = query.lower()
        matches: list[str] = []
        for item in self.root.rglob("*"):
            if not item.is_file():
                continue
            rel = str(item.relative_to(self.root))
            if query_lower in rel.lower():
                matches.append(rel)
                continue
            try:
                if query_lower in item.read_text(encoding="utf-8", errors="ignore").lower():
                    matches.append(rel)
            except OSError:
                continue
        return matches[:200]
