from __future__ import annotations

import json
import os
import re
import sqlite3
from pathlib import Path


TEXT_SUFFIXES = {
    ".py", ".js", ".jsx", ".ts", ".tsx",
    ".html", ".css",
    ".md", ".txt",
    ".toml", ".yaml", ".yml",
    ".json", ".jsonl",
    ".sh", ".zsh",
    ".sql", ".ini", ".cfg",
}

SKIP_DIRS = {
    ".git",
    ".venv",
    ".venv-mlx",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    "dist",
    "build",
}

MAX_BYTES = 5 * 1024 * 1024
CHUNK_LINES = 70
OVERLAP_LINES = 15


class KnowledgeStore:
    def __init__(
        self,
        root: Path | str = ".doug/knowledge",
    ):
        self.root = Path(root)
        self.root.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.db_path = (
            self.root / "knowledge.sqlite3"
        )

    def _connect(self):
        conn = sqlite3.connect(
            str(self.db_path)
        )

        conn.row_factory = sqlite3.Row

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL,
                source TEXT NOT NULL,
                locator TEXT NOT NULL,
                text TEXT NOT NULL
            )
            """
        )

        try:
            conn.execute(
                """
                CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts
                USING fts5(
                    text,
                    path,
                    source UNINDEXED,
                    locator UNINDEXED
                )
                """
            )
            fts = True
        except sqlite3.OperationalError:
            fts = False

        return conn, fts

    @staticmethod
    def _secret(path: Path) -> bool:
        name = path.name.lower()

        if name == ".env":
            return True

        if name.startswith(".env."):
            return True

        if path.suffix.lower() in {
            ".pem",
            ".key",
            ".p12",
            ".pfx",
        }:
            return True

        return ".ssh" in {
            part.lower()
            for part in path.parts
        }

    @staticmethod
    def _source(relative: str) -> str:
        normalized = relative.replace(
            "\\",
            "/",
        )

        if normalized.startswith(
            ".doug/ontology/"
        ):
            return "ontology"

        if "workers/knowledge/" in normalized:
            return "seed_knowledge"

        return "repository"

    def _files(self, repo_root: Path):
        for directory, dirs, files in os.walk(
            str(repo_root)
        ):
            current = Path(directory)

            dirs[:] = [
                item
                for item in dirs
                if item not in SKIP_DIRS
            ]

            # Runtime .doug is indexed separately.
            if current == repo_root:
                dirs[:] = [
                    item
                    for item in dirs
                    if item != ".doug"
                ]

            for filename in files:
                path = current / filename

                if self._secret(path):
                    continue

                if (
                    path.suffix.lower()
                    not in TEXT_SUFFIXES
                ):
                    continue

                try:
                    if (
                        path.stat().st_size
                        > MAX_BYTES
                    ):
                        continue
                except OSError:
                    continue

                yield path

        ontology = (
            repo_root
            / ".doug"
            / "ontology"
        )

        if ontology.exists():
            for path in ontology.rglob(
                "*.jsonl"
            ):
                if path.is_file():
                    yield path

    def _chunks(
        self,
        path: Path,
        relative: str,
    ):
        if (
            path.name == "pages.jsonl"
            and relative.startswith(
                ".doug/ontology/documents/"
            )
        ):
            for raw in path.read_text(
                encoding="utf-8",
                errors="replace",
            ).splitlines():
                if not raw.strip():
                    continue

                try:
                    record = json.loads(raw)
                except Exception:
                    continue

                text = str(
                    record.get("text") or ""
                ).strip()

                if not text:
                    continue

                source_file = record.get(
                    "source_file",
                    relative,
                )

                page = record.get("page")

                locator = (
                    f"{source_file}#page={page}"
                )

                yield locator, text

            return

        if path.suffix.lower() == ".jsonl":
            for number, raw in enumerate(
                path.read_text(
                    encoding="utf-8",
                    errors="replace",
                ).splitlines(),
                start=1,
            ):
                if raw.strip():
                    yield (
                        f"line:{number}",
                        raw.strip(),
                    )

            return

        lines = path.read_text(
            encoding="utf-8",
            errors="replace",
        ).splitlines()

        start = 0

        while start < len(lines):
            end = min(
                start + CHUNK_LINES,
                len(lines),
            )

            text = "\n".join(
                lines[start:end]
            ).strip()

            if text:
                yield (
                    f"lines:{start + 1}-{end}",
                    text,
                )

            if end >= len(lines):
                break

            start = max(
                start + 1,
                end - OVERLAP_LINES,
            )

    def rebuild(
        self,
        repo_root: Path | str = ".",
    ):
        repo_root = Path(
            repo_root
        ).resolve()

        conn, fts = self._connect()

        conn.execute(
            "DELETE FROM chunks"
        )

        if fts:
            conn.execute(
                "DELETE FROM chunks_fts"
            )

        files = 0
        chunks = 0

        seen = set()

        for path in self._files(repo_root):
            try:
                relative = str(
                    path.resolve().relative_to(
                        repo_root
                    )
                )
            except Exception:
                continue

            if relative in seen:
                continue

            seen.add(relative)
            files += 1

            source = self._source(
                relative
            )

            try:
                records = self._chunks(
                    path,
                    relative,
                )

                for locator, text in records:
                    conn.execute(
                        """
                        INSERT INTO chunks(
                            path,
                            source,
                            locator,
                            text
                        )
                        VALUES (?, ?, ?, ?)
                        """,
                        (
                            relative,
                            source,
                            locator,
                            text,
                        ),
                    )

                    if fts:
                        conn.execute(
                            """
                            INSERT INTO chunks_fts(
                                text,
                                path,
                                source,
                                locator
                            )
                            VALUES (?, ?, ?, ?)
                            """,
                            (
                                text,
                                relative,
                                source,
                                locator,
                            ),
                        )

                    chunks += 1

            except Exception:
                continue

        conn.commit()
        conn.close()

        return {
            "files": files,
            "chunks": chunks,
            "fts5": fts,
            "database": str(
                self.db_path
            ),
        }

    def status(self):
        conn, fts = self._connect()

        chunks = conn.execute(
            "SELECT COUNT(*) FROM chunks"
        ).fetchone()[0]

        sources = {
            row["source"]: row["count"]
            for row in conn.execute(
                """
                SELECT
                    source,
                    COUNT(*) AS count
                FROM chunks
                GROUP BY source
                """
            )
        }

        conn.close()

        return {
            "chunks": chunks,
            "sources": sources,
            "fts5": fts,
            "database": str(
                self.db_path
            ),
        }

    @staticmethod
    def _fts_expression(query: str):
        tokens = re.findall(
            r"[A-Za-z0-9_]{2,}",
            query,
        )[:12]

        if not tokens:
            return None

        return " OR ".join(
            f'"{token}"'
            for token in tokens
        )

    def search(
        self,
        query: str,
        limit: int = 10,
    ):
        conn, fts = self._connect()

        rows = []

        if fts:
            expression = (
                self._fts_expression(
                    query
                )
            )

            if expression:
                try:
                    rows = conn.execute(
                        """
                        SELECT
                            path,
                            source,
                            locator,
                            text,
                            bm25(chunks_fts)
                                AS score
                        FROM chunks_fts
                        WHERE chunks_fts
                            MATCH ?
                        ORDER BY score
                        LIMIT ?
                        """,
                        (
                            expression,
                            int(limit),
                        ),
                    ).fetchall()
                except sqlite3.OperationalError:
                    rows = []

        if not rows:
            like = (
                "%"
                + query.lower()
                + "%"
            )

            rows = conn.execute(
                """
                SELECT
                    path,
                    source,
                    locator,
                    text,
                    0.0 AS score
                FROM chunks
                WHERE
                    lower(text) LIKE ?
                    OR lower(path) LIKE ?
                LIMIT ?
                """,
                (
                    like,
                    like,
                    int(limit),
                ),
            ).fetchall()

        result = [
            dict(row)
            for row in rows
        ]

        conn.close()
        return result

    def context(
        self,
        query: str,
        limit: int = 10,
        max_chars: int = 14000,
    ):
        results = self.search(
            query,
            limit=limit,
        )

        if not results:
            return (
                "(no matching local "
                "knowledge retrieved)"
            )

        blocks = []
        size = 0

        for item in results:
            block = (
                "["
                + item["source"]
                + "] "
                + item["path"]
                + " "
                + item["locator"]
                + "\n"
                + item["text"]
            )

            if (
                size + len(block)
                > max_chars
            ):
                break

            blocks.append(block)
            size += len(block)

        return "\n\n---\n\n".join(
            blocks
        )
