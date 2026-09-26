#!/usr/bin/env python3
"""ZYRA-MSS exhaustive PPUBS reader.

Enumerates every unique patent/publication exposed by a Patent Public Search
result set, downloads the corresponding USPTO PDFs, SHA-256 hashes them,
extracts full text, and stores a searchable SQLite FTS5 corpus.

The 100-worker model is logical work partitioning; network concurrency is capped
at six. COMPLETE is emitted only when every discovered PDF was processed.
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import re
import shutil
import sqlite3
import subprocess
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

PPUBS = "https://ppubs.uspto.gov"
BASIC = PPUBS + "/basic/"
EXTERNAL = PPUBS + "/pubwebapp/external.html"
IMAGE_PPUBS = "https://image-ppubs.uspto.gov"
# USPTO's documented direct-PDF format intentionally has no .pdf suffix.
PDF_BASE = IMAGE_PPUBS + "/dirsearch-public/print/downloadPdf/{}"
DOC_RE = re.compile(r"\bUS[-\s]?(\d{7,11})[-\s]?([A-Z]\d)\b", re.I)
MAX_NET = 6
ROLE_BANDS = [
    (1, 20, "source/provenance"),
    (21, 35, "ontology-normalization"),
    (36, 50, "readiness"),
    (51, 60, "defensive-cyber"),
    (61, 70, "logistics-continuity"),
    (71, 80, "policy-access"),
    (81, 90, "software-assurance"),
    (91, 96, "incident-analysis"),
    (97, 99, "adversarial-review"),
    (100, 100, "decision-packet"),
]


@dataclass
class Doc:
    document_number: str
    pdf_url: str
    row_text: str = ""
    page: int = 0


def now():
    return datetime.now(timezone.utc).isoformat()


def worker(i):
    wid = (i % 100) + 1
    role = next(r for a, b, r in ROLE_BANDS if a <= wid <= b)
    return {"worker_id": wid, "role": role, "authority": "RECOMMEND_ONLY"}


def number(text):
    m = DOC_RE.search(text or "")
    return f"US-{m.group(1)}-{m.group(2).upper()}" if m else None


def pdf_number(docno):
    m = DOC_RE.search(docno or "")
    return m.group(1) if m else None


def canonical_pdf_url(docno):
    raw = pdf_number(docno)
    return PDF_BASE.format(raw) if raw else ""


def chrome():
    for p in [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
    ]:
        if Path(p).exists():
            return p
    return None


def _launch(playwright, headed):
    kw = {"headless": not headed}
    exe = chrome()
    if exe:
        kw["executable_path"] = exe
    return playwright.chromium.launch(**kw)


def _collect_rows(page, pageno):
    """Collect document numbers and, when available, the row's real PDF link."""
    found = {}
    rows = page.locator("tr")
    for i in range(rows.count()):
        row = rows.nth(i)
        try:
            text = row.inner_text(timeout=1200).strip()
        except Exception:
            continue
        docno = number(text)
        if not docno:
            continue

        pdf_url = canonical_pdf_url(docno)
        try:
            links = row.locator("a", has_text=re.compile(r"^\s*PDF\s*$", re.I))
            if links.count():
                href = links.first.get_attribute("href")
                if href and not href.lower().startswith("javascript:"):
                    pdf_url = urljoin(page.url, href)
        except Exception:
            pass

        if pdf_url:
            found[docno] = Doc(docno, pdf_url, text, pageno)
    return found


def _next_button(page):
    candidates = [
        page.locator("button[aria-label*='next' i]:visible"),
        page.locator("a[aria-label*='next' i]:visible"),
        page.locator("button[title*='next' i]:visible"),
        page.locator("a[title*='next' i]:visible"),
        page.get_by_text(re.compile(r"^\s*navigate_next\s*$", re.I)),
        page.get_by_text(re.compile(r"^\s*next\s*$", re.I)),
    ]
    for c in candidates:
        try:
            if not c.count():
                continue
            n = c.last
            if not n.is_visible():
                continue
            if n.get_attribute("disabled") is not None:
                continue
            if n.get_attribute("aria-disabled") == "true":
                continue
            return n
        except Exception:
            continue
    return None


def _paginate(page, max_pages, found):
    seen = set()
    for pageno in range(1, max_pages + 1):
        page_found = _collect_rows(page, pageno)
        found.update(page_found)
        keys = list(page_found)
        fp = "|".join(keys[:3] + keys[-3:]) + f":{len(keys)}"
        print(f"🔎 PPUBS page {pageno}: {len(page_found)} row document(s), {len(found)} unique total")
        if fp in seen:
            break
        seen.add(fp)

        nxt = _next_button(page)
        if nxt is None:
            break
        try:
            nxt.click(timeout=10000)
            page.wait_for_timeout(1300)
        except Exception:
            break
    return found


def _discover_basic(page, query, max_pages):
    page.goto(BASIC, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(1500)

    inputs = page.locator("input:visible")
    if inputs.count() < 2:
        raise RuntimeError(f"PPUBS Basic form not detected (visible inputs={inputs.count()})")
    inputs.nth(1).fill(query)

    searches = page.get_by_role("button", name=re.compile(r"^\s*Search\s*$", re.I))
    if not searches.count():
        raise RuntimeError("PPUBS Basic Search button not detected")
    searches.last.click(timeout=10000)

    try:
        page.get_by_text(re.compile(r"Search results", re.I)).first.wait_for(timeout=30000)
    except Exception:
        page.wait_for_timeout(5000)

    found = {}
    _paginate(page, max_pages, found)
    return found


def _discover_external(page, query, max_pages):
    url = f"{EXTERNAL}?q={quote(query)}&db=USPAT,US-PGPUB&type=queryString"
    page.goto(url, wait_until="domcontentloaded", timeout=120000)
    page.wait_for_timeout(4000)
    found = {}
    _paginate(page, max_pages, found)
    return found


def discover(query, max_pages, headed, debug_dir):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("Install Playwright first: python3 -m pip install playwright") from e

    debug_dir = Path(debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)
    found = {}
    cookie = ""
    with sync_playwright() as p:
        b = _launch(p, headed)
        ctx = b.new_context()
        page = ctx.new_page()
        try:
            print("🌐 PPUBS discovery mode: Basic Search / Everything")
            found = _discover_basic(page, query, max_pages)
            if not found:
                print("⚠️ Basic Search yielded 0 documents; trying USPTO external search URL...")
                found = _discover_external(page, query, max_pages)

            if not found:
                try:
                    (debug_dir / "discovery-debug.html").write_text(page.content(), encoding="utf-8")
                    page.screenshot(path=str(debug_dir / "discovery-debug.png"), full_page=True)
                    (debug_dir / "discovery-debug.txt").write_text(
                        f"url={page.url}\ntitle={page.title()}\n\n{page.locator('body').inner_text()[:20000]}",
                        encoding="utf-8",
                    )
                except Exception:
                    pass
            cookie = "; ".join(f"{c['name']}={c['value']}" for c in ctx.cookies())
        finally:
            b.close()
    return list(found.values()), cookie


def sha(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def download(doc, out, cookie):
    p = out / "pdf" / (re.sub(r"[^A-Za-z0-9_.-]", "_", doc.document_number) + ".pdf")
    p.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": "Mozilla/5.0 ZYRA-MSS-public-patent-research/1.1",
        "Accept": "application/pdf,application/octet-stream;q=0.9,*/*;q=0.8",
        "Referer": PPUBS + "/",
    }
    if cookie:
        headers["Cookie"] = cookie

    urls = []
    if doc.pdf_url:
        urls.append(doc.pdf_url)
    canonical = canonical_pdf_url(doc.document_number)
    if canonical and canonical not in urls:
        urls.append(canonical)

    last_error = None
    for url in urls:
        try:
            if p.exists():
                p.unlink()
            with urlopen(Request(url, headers=headers), timeout=90) as r, p.open("wb") as f:
                shutil.copyfileobj(r, f)
            if p.read_bytes()[:5] != b"%PDF-":
                raise RuntimeError("response was not a PDF")
            return {
                "document_number": doc.document_number,
                "pdf_url": url,
                "pdf_path": str(p),
                "bytes": p.stat().st_size,
                "sha256": sha(p),
                "status": "downloaded",
            }
        except Exception as e:
            last_error = f"{type(e).__name__}: {e}"
            try:
                if p.exists():
                    p.unlink()
            except Exception:
                pass

    return {
        "document_number": doc.document_number,
        "pdf_url": canonical or doc.pdf_url,
        "status": "failed",
        "error": last_error or "no usable PDF URL",
    }


def extract(pdf, text):
    text.parent.mkdir(parents=True, exist_ok=True)
    exe = shutil.which("pdftotext")
    if exe:
        r = subprocess.run([exe, "-layout", str(pdf), str(text)], capture_output=True)
        if r.returncode == 0 and text.exists():
            return "pdftotext"
    try:
        from pypdf import PdfReader

        text.write_text(
            "\n\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages),
            encoding="utf-8",
        )
        return "pypdf"
    except Exception as e:
        raise RuntimeError("Install poppler (pdftotext) or pypdf") from e


def load_discovered(out):
    path = out / "discovered.jsonl"
    if not path.exists():
        return []
    docs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            docno = data.get("document_number")
            if not docno:
                continue
            # Always refresh the direct URL so old manifests with the wrong host
            # are repaired automatically.
            data["pdf_url"] = canonical_pdf_url(docno)
            docs.append(Doc(**{k: data.get(k) for k in ("document_number", "pdf_url", "row_text", "page")}))
        except Exception:
            continue
    return docs


def write_summary(out, *, query, discovered, indexed, failed, workers, failures=None):
    failures = failures or []
    summary = {
        "schema": "xunia.zyra-mss.uspto-corpus.v1",
        "source": PPUBS,
        "query": query,
        "discovered": discovered,
        "indexed": indexed,
        "failed": failed,
        "complete": indexed == discovered and failed == 0 and discovered > 0,
        "logical_worker_count": 100,
        "actual_network_concurrency": workers,
        "generated_at": now(),
        "failure_samples": [
            {"document_number": r.get("document_number"), "error": r.get("error"), "pdf_url": r.get("pdf_url")}
            for r in failures[:5]
        ],
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return summary


def process_docs(docs, out, *, query, workers, delay, cookie=""):
    if not docs:
        print("❌ No discovered USPTO documents are available to process")
        return 2

    workers = max(1, min(workers, MAX_NET))

    # Fail-fast preflight: prove one real PDF works before launching thousands of
    # requests. This prevents another 3,000+ request failure storm.
    print(f"🧪 PDF preflight: {docs[0].document_number}")
    probe = download(docs[0], out, cookie)
    if probe.get("status") != "downloaded":
        print(f"❌ PDF preflight failed: {probe.get('error')}")
        print(f"   URL: {probe.get('pdf_url')}")
        write_summary(
            out,
            query=query,
            discovered=len(docs),
            indexed=0,
            failed=len(docs),
            workers=0,
            failures=[probe],
        )
        return 3
    print(f"✅ PDF preflight passed: {probe.get('bytes', 0)} bytes")

    results = [probe]
    remaining = docs[1:]
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futs = [pool.submit(download, d, out, cookie) for d in remaining]
        total = len(docs)
        done = 1
        if total == 1:
            print("⬇️ 1/1")
        for f in cf.as_completed(futs):
            results.append(f.result())
            done += 1
            if done % 25 == 0 or done == total:
                print(f"⬇️ {done}/{total}")
            if delay:
                time.sleep(delay)

    results.sort(key=lambda x: x["document_number"])
    db = out / "corpus.sqlite3"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    con.execute(
        "CREATE TABLE documents(document_number TEXT PRIMARY KEY,pdf_url TEXT,pdf_path TEXT,text_path TEXT,sha256 TEXT,bytes INTEGER,text_chars INTEGER,worker_id INTEGER,worker_role TEXT,processed_at TEXT)"
    )
    con.execute("CREATE VIRTUAL TABLE documents_fts USING fts5(document_number,body)")

    indexed = 0
    failed = []
    for i, r in enumerate(results):
        r["logical_worker"] = worker(i)
        if r["status"] != "downloaded":
            failed.append(r)
            continue
        try:
            pdf = Path(r["pdf_path"])
            text = out / "text" / (pdf.stem + ".txt")
            method = extract(pdf, text)
            body = text.read_text(encoding="utf-8", errors="replace")
            w = r["logical_worker"]
            r.update(
                status="indexed",
                text_path=str(text),
                text_chars=len(body),
                extractor=method,
                processed_at=now(),
            )
            con.execute(
                "INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    r["document_number"],
                    r["pdf_url"],
                    r["pdf_path"],
                    r["text_path"],
                    r["sha256"],
                    r["bytes"],
                    r["text_chars"],
                    w["worker_id"],
                    w["role"],
                    r["processed_at"],
                ),
            )
            con.execute("INSERT INTO documents_fts VALUES(?,?)", (r["document_number"], body))
            indexed += 1
        except Exception as e:
            r.update(status="failed", error=f"extract/index: {type(e).__name__}: {e}")
            failed.append(r)

    con.commit()
    con.close()
    (out / "results.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in results),
        encoding="utf-8",
    )
    (out / "failures.jsonl").write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in failed),
        encoding="utf-8",
    )
    summary = write_summary(
        out,
        query=query,
        discovered=len(docs),
        indexed=indexed,
        failed=len(failed),
        workers=workers,
        failures=failed,
    )
    print(f"🏁 discovered={len(docs)} indexed={indexed} failed={len(failed)} complete={summary['complete']}")
    if failed:
        first = failed[0]
        print(f"⚠️ first failure: {first.get('document_number')} :: {first.get('error')}")
    return 0 if summary["complete"] else 1


def crawl(a):
    out = Path(a.output).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    docs, cookie = discover(a.query, a.max_pages, a.headed, out)
    (out / "discovered.jsonl").write_text(
        "".join(json.dumps(asdict(d), sort_keys=True) + "\n" for d in docs),
        encoding="utf-8",
    )
    print(f"📚 discovered {len(docs)} unique PPUBS PDFs")

    if not docs:
        summary = {
            "schema": "xunia.zyra-mss.uspto-corpus.v1",
            "source": PPUBS,
            "query": a.query,
            "discovered": 0,
            "indexed": 0,
            "failed": 0,
            "complete": False,
            "logical_worker_count": 100,
            "actual_network_concurrency": 0,
            "generated_at": now(),
            "error": "PPUBS discovery returned zero documents",
            "debug_files": [
                str(out / "discovery-debug.html"),
                str(out / "discovery-debug.png"),
                str(out / "discovery-debug.txt"),
            ],
        }
        (out / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("❌ PPUBS discovery returned 0 documents; debug capture written to output directory")
        return 2

    return process_docs(docs, out, query=a.query, workers=a.workers, delay=a.delay, cookie=cookie)


def retry(a):
    out = Path(a.output).expanduser().resolve()
    docs = load_discovered(out)
    if not docs:
        print(f"❌ No discovery manifest found at {out / 'discovered.jsonl'}")
        print("Run the crawl/mega command once to discover the PPUBS result set.")
        return 2
    print(f"♻️ Reusing {len(docs)} already-discovered documents; no USPTO search recrawl")
    return process_docs(docs, out, query=a.query, workers=a.workers, delay=a.delay)


def search(a):
    db = Path(a.database).expanduser()
    if not db.exists():
        print(f"❌ Corpus database not found: {db}")
        print("Run: scripts/zyra-mss-uspto-reader mega")
        return 2
    con = sqlite3.connect(db)
    exists = con.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='documents_fts'"
    ).fetchone()
    if not exists:
        con.close()
        print("❌ Corpus exists but is incomplete; documents_fts has not been built")
        print("Run: scripts/zyra-mss-uspto-reader retry")
        return 2
    rows = con.execute(
        "SELECT document_number,snippet(documents_fts,1,'[',']',' … ',20) FROM documents_fts WHERE documents_fts MATCH ? LIMIT ?",
        (a.terms, a.limit),
    ).fetchall()
    con.close()
    for n, s in rows:
        print(f"{n}\n  {s}\n")
    return 0 if rows else 1


def doctor(a):
    root = Path(a.output).expanduser()
    summary = root / "summary.json"
    if not summary.exists():
        print(f"❌ No crawl summary yet: {summary}")
        print("Run: scripts/zyra-mss-uspto-reader mega")
        return 2
    s = json.loads(summary.read_text())
    print(json.dumps(s, indent=2, sort_keys=True))
    if s.get("failure_samples"):
        print("\nFailure sample(s):")
        for f in s["failure_samples"]:
            print(f"- {f.get('document_number')}: {f.get('error')}")
    return 0 if s.get("complete") else 1


def main():
    p = argparse.ArgumentParser(prog="zyra-mss-uspto-reader")
    sp = p.add_subparsers(dest="cmd", required=True)

    c = sp.add_parser("crawl")
    c.add_argument("--query", default="palantir")
    c.add_argument("--output", default="~/.config/gpt-doug/zyra-mss-uspto-palantir")
    c.add_argument("--max-pages", type=int, default=10000)
    c.add_argument("--workers", type=int, default=6)
    c.add_argument("--delay", type=float, default=.02)
    c.add_argument("--headed", action="store_true")
    c.set_defaults(fn=crawl)

    r = sp.add_parser("retry")
    r.add_argument("--query", default="palantir")
    r.add_argument("--output", default="~/.config/gpt-doug/zyra-mss-uspto-palantir")
    r.add_argument("--workers", type=int, default=6)
    r.add_argument("--delay", type=float, default=.02)
    r.set_defaults(fn=retry)

    s = sp.add_parser("search")
    s.add_argument("terms")
    s.add_argument("--database", default="~/.config/gpt-doug/zyra-mss-uspto-palantir/corpus.sqlite3")
    s.add_argument("--limit", type=int, default=20)
    s.set_defaults(fn=search)

    d = sp.add_parser("doctor")
    d.add_argument("--output", default="~/.config/gpt-doug/zyra-mss-uspto-palantir")
    d.set_defaults(fn=doctor)

    a = p.parse_args()
    raise SystemExit(a.fn(a))


if __name__ == "__main__":
    main()
