from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from pypdf import PdfReader


class DocumentIngestor:
    """
    Deterministic PDF ingestion with page-level provenance.

    This layer extracts source text only.
    It does not infer entities or relationships.
    """

    def __init__(self, root: Path | str = ".doug/ontology"):
        self.root = Path(root)
        self.documents_root = self.root / "documents"
        self.documents_root.mkdir(
            parents=True,
            exist_ok=True,
        )

    @staticmethod
    def sha256(path: Path) -> str:
        digest = hashlib.sha256()

        with path.open("rb") as fh:
            for chunk in iter(
                lambda: fh.read(1024 * 1024),
                b"",
            ):
                digest.update(chunk)

        return digest.hexdigest()

    def ingest_pdf(
        self,
        path: Path | str,
    ) -> Dict[str, Any]:
        path = Path(path).expanduser().resolve()

        if not path.exists():
            raise FileNotFoundError(path)

        if not path.is_file():
            raise ValueError(
                f"Not a file: {path}"
            )

        if path.suffix.lower() != ".pdf":
            raise ValueError(
                "PDF files only."
            )

        sha256 = self.sha256(path)
        document_id = f"doc_{sha256[:16]}"

        document_dir = (
            self.documents_root / document_id
        )

        manifest_path = (
            document_dir / "manifest.json"
        )

        pages_path = (
            document_dir / "pages.jsonl"
        )

        if manifest_path.exists():
            manifest = json.loads(
                manifest_path.read_text(
                    encoding="utf-8"
                )
            )

            manifest["already_ingested"] = True
            return manifest

        document_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        reader = PdfReader(str(path))

        page_records: List[Dict[str, Any]] = []
        total_chars = 0
        text_pages = 0
        empty_pages = 0

        for index, page in enumerate(
            reader.pages,
            start=1,
        ):
            extraction_error = None

            try:
                text = page.extract_text() or ""
            except Exception as exc:
                text = ""
                extraction_error = (
                    f"{type(exc).__name__}: {exc}"
                )

            text = (
                text.replace("\x00", "")
                .strip()
            )

            if text:
                text_pages += 1
            else:
                empty_pages += 1

            total_chars += len(text)

            page_records.append(
                {
                    "document_id": document_id,
                    "page": index,
                    "source_file": path.name,
                    "sha256": sha256,
                    "char_count": len(text),
                    "text": text,
                    "extraction_error": (
                        extraction_error
                    ),
                }
            )

        with pages_path.open(
            "w",
            encoding="utf-8",
        ) as fh:
            for record in page_records:
                fh.write(
                    json.dumps(
                        record,
                        ensure_ascii=False,
                    )
                    + "\n"
                )

        manifest = {
            "document_id": document_id,
            "filename": path.name,
            "source_path": str(path),
            "sha256": sha256,
            "page_count": len(page_records),
            "text_pages": text_pages,
            "empty_pages": empty_pages,
            "char_count": total_chars,
            "pages_file": str(pages_path),
            "ingested_at": (
                datetime.now(timezone.utc)
                .isoformat()
            ),
            "already_ingested": False,
        }

        manifest_path.write_text(
            json.dumps(
                manifest,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        return manifest

    def list_documents(
        self,
    ) -> List[Dict[str, Any]]:
        documents = []

        for manifest_path in sorted(
            self.documents_root.glob(
                "*/manifest.json"
            )
        ):
            try:
                documents.append(
                    json.loads(
                        manifest_path.read_text(
                            encoding="utf-8"
                        )
                    )
                )
            except Exception:
                continue

        return documents
