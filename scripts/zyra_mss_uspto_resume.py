#!/usr/bin/env python3
"""Resume ZYRA-MSS USPTO corpus processing without re-downloading valid PDFs."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import zyra_mss_uspto_reader as reader


def cached_download(doc, out, cookie):
    out = Path(out)
    p = out / "pdf" / (re.sub(r"[^A-Za-z0-9_.-]", "_", doc.document_number) + ".pdf")
    if p.exists():
        try:
            with p.open("rb") as f:
                magic = f.read(5)
            if magic == b"%PDF-" and p.stat().st_size > 1024:
                return {
                    "document_number": doc.document_number,
                    "pdf_url": reader.canonical_pdf_url(doc.document_number) or doc.pdf_url,
                    "pdf_path": str(p),
                    "bytes": p.stat().st_size,
                    "sha256": reader.sha(p),
                    "status": "downloaded",
                    "cached": True,
                }
        except Exception:
            pass
        try:
            p.unlink()
        except Exception:
            pass
    return ORIGINAL_DOWNLOAD(doc, out, cookie)


ORIGINAL_DOWNLOAD = reader.download
reader.download = cached_download


def main():
    ap = argparse.ArgumentParser(prog="zyra-mss-uspto-resume")
    ap.add_argument("--output", default="~/.config/gpt-doug/zyra-mss-uspto-palantir")
    ap.add_argument("--query", default="palantir")
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--delay", type=float, default=.02)
    a = ap.parse_args()

    out = Path(a.output).expanduser().resolve()
    docs = reader.load_discovered(out)
    if not docs:
        print("❌ No discovery manifest found. Run the mega crawl first.")
        return 2

    cached = 0
    pdf_dir = out / "pdf"
    for d in docs:
        p = pdf_dir / (re.sub(r"[^A-Za-z0-9_.-]", "_", d.document_number) + ".pdf")
        try:
            if p.exists() and p.stat().st_size > 1024 and p.open("rb").read(5) == b"%PDF-":
                cached += 1
        except Exception:
            pass

    print(f"♻️ Resume manifest: {len(docs)} documents")
    print(f"💾 Valid cached PDFs: {cached}/{len(docs)}")
    print(f"🌐 Remaining network downloads: {len(docs) - cached}")
    return reader.process_docs(
        docs,
        out,
        query=a.query,
        workers=a.workers,
        delay=a.delay,
        cookie="",
    )


if __name__ == "__main__":
    raise SystemExit(main())
