#!/usr/bin/env python3
"""ZYRA-MSS exhaustive PPUBS reader.

Enumerates every PDF exposed by a Patent Public Search result set, downloads it,
SHA-256 hashes it, extracts full text, and stores a searchable SQLite FTS5 corpus.
The 100-worker model is logical work partitioning; network concurrency is capped
at six. COMPLETE is emitted only when every discovered PDF was processed.
"""
from __future__ import annotations

import argparse, concurrent.futures as cf, hashlib, json, re, shutil, sqlite3, subprocess, time
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urljoin
from urllib.request import Request, urlopen

PPUBS = "https://ppubs.uspto.gov"
EXTERNAL = PPUBS + "/pubwebapp/external.html"
DOC_RE = re.compile(r"\bUS[-\s]?(\d{7,11})[-\s]?([A-Z]\d)\b", re.I)
MAX_NET = 6
ROLE_BANDS = [(1,20,"source/provenance"),(21,35,"ontology-normalization"),(36,50,"readiness"),(51,60,"defensive-cyber"),(61,70,"logistics-continuity"),(71,80,"policy-access"),(81,90,"software-assurance"),(91,96,"incident-analysis"),(97,99,"adversarial-review"),(100,100,"decision-packet")]

@dataclass
class Doc:
    document_number: str
    pdf_url: str
    row_text: str = ""
    page: int = 0


def now(): return datetime.now(timezone.utc).isoformat()
def worker(i):
    wid=(i%100)+1; role=next(r for a,b,r in ROLE_BANDS if a<=wid<=b)
    return {"worker_id":wid,"role":role,"authority":"RECOMMEND_ONLY"}
def number(text):
    m=DOC_RE.search(text or ""); return f"US-{m.group(1)}-{m.group(2).upper()}" if m else None

def chrome():
    for p in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome","/Applications/Chromium.app/Contents/MacOS/Chromium"]:
        if Path(p).exists(): return p
    return None

def discover(query, max_pages, headed):
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        raise RuntimeError("Install Playwright first: python3 -m pip install playwright") from e
    url=f"{EXTERNAL}?q={quote(query)}&db=USPAT,US-PGPUB&type=queryString"
    found={}; cookie=""
    with sync_playwright() as p:
        kw={"headless":not headed}; exe=chrome()
        if exe: kw["executable_path"]=exe
        b=p.chromium.launch(**kw); ctx=b.new_context(); page=ctx.new_page()
        page.goto(url,wait_until="domcontentloaded",timeout=120000); page.wait_for_timeout(2500)
        seen=set()
        for pageno in range(1,max_pages+1):
            rows=page.locator("tr"); page_numbers=[]
            for i in range(rows.count()):
                row=rows.nth(i)
                try: text=row.inner_text(timeout=1200).strip()
                except Exception: continue
                links=row.locator("a",has_text=re.compile(r"^\s*PDF\s*$",re.I))
                if not links.count(): continue
                href=links.first.get_attribute("href"); docno=number(text)
                if href and docno:
                    found[docno]=Doc(docno,urljoin(page.url,href),text,pageno); page_numbers.append(docno)
            fp="|".join(page_numbers[:5])+f":{len(page_numbers)}"
            if fp in seen: break
            seen.add(fp)
            nxt=None
            for c in [page.locator("button[aria-label*='next' i],a[aria-label*='next' i]"),page.locator("button[title*='next' i],a[title*='next' i]"),page.get_by_text(re.compile(r"^\s*next\s*$",re.I))]:
                try:
                    if c.count() and c.first.is_visible(): nxt=c.first; break
                except Exception: pass
            if nxt is None or nxt.get_attribute("disabled") is not None or nxt.get_attribute("aria-disabled")=="true": break
            try: nxt.click(timeout=10000); page.wait_for_timeout(1200)
            except Exception: break
        cookie="; ".join(f"{c['name']}={c['value']}" for c in ctx.cookies()); b.close()
    return list(found.values()), cookie

def sha(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def download(doc,out,cookie):
    p=out/"pdf"/(re.sub(r"[^A-Za-z0-9_.-]","_",doc.document_number)+".pdf"); p.parent.mkdir(parents=True,exist_ok=True)
    headers={"User-Agent":"ZYRA-MSS-public-patent-research/1.0","Accept":"application/pdf,*/*;q=0.8"}
    if cookie: headers["Cookie"]=cookie
    try:
        with urlopen(Request(doc.pdf_url,headers=headers),timeout=90) as r,p.open("wb") as f: shutil.copyfileobj(r,f)
        if p.read_bytes()[:5]!=b"%PDF-": raise RuntimeError("not a PDF")
        return {"document_number":doc.document_number,"pdf_url":doc.pdf_url,"pdf_path":str(p),"bytes":p.stat().st_size,"sha256":sha(p),"status":"downloaded"}
    except Exception as e:
        return {"document_number":doc.document_number,"pdf_url":doc.pdf_url,"status":"failed","error":f"{type(e).__name__}: {e}"}

def extract(pdf,text):
    text.parent.mkdir(parents=True,exist_ok=True)
    exe=shutil.which("pdftotext")
    if exe:
        r=subprocess.run([exe,"-layout",str(pdf),str(text)],capture_output=True)
        if r.returncode==0 and text.exists(): return "pdftotext"
    try:
        from pypdf import PdfReader
        text.write_text("\n\n".join((p.extract_text() or "") for p in PdfReader(str(pdf)).pages),encoding="utf-8")
        return "pypdf"
    except Exception as e: raise RuntimeError("Install poppler (pdftotext) or pypdf") from e

def crawl(a):
    out=Path(a.output).expanduser().resolve(); out.mkdir(parents=True,exist_ok=True)
    docs,cookie=discover(a.query,a.max_pages,a.headed)
    (out/"discovered.jsonl").write_text("".join(json.dumps(asdict(d),sort_keys=True)+"\n" for d in docs),encoding="utf-8")
    print(f"📚 discovered {len(docs)} PPUBS PDFs")
    if not docs: return 2
    results=[]; workers=max(1,min(a.workers,MAX_NET))
    with cf.ThreadPoolExecutor(max_workers=workers) as pool:
        futs=[pool.submit(download,d,out,cookie) for d in docs]
        for i,f in enumerate(cf.as_completed(futs),1):
            results.append(f.result())
            if i%25==0 or i==len(futs): print(f"⬇️ {i}/{len(futs)}")
            if a.delay: time.sleep(a.delay)
    results.sort(key=lambda x:x["document_number"])
    con=sqlite3.connect(out/"corpus.sqlite3"); con.execute("CREATE TABLE IF NOT EXISTS documents(document_number TEXT PRIMARY KEY,pdf_url TEXT,pdf_path TEXT,text_path TEXT,sha256 TEXT,bytes INTEGER,text_chars INTEGER,worker_id INTEGER,worker_role TEXT,processed_at TEXT)"); con.execute("CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(document_number,body)"); con.execute("DELETE FROM documents_fts")
    indexed=0; failed=[]
    for i,r in enumerate(results):
        r["logical_worker"]=worker(i)
        if r["status"]!="downloaded": failed.append(r); continue
        try:
            pdf=Path(r["pdf_path"]); text=out/"text"/(pdf.stem+".txt"); method=extract(pdf,text); body=text.read_text(encoding="utf-8",errors="replace"); w=r["logical_worker"]
            r.update(status="indexed",text_path=str(text),text_chars=len(body),extractor=method,processed_at=now())
            con.execute("INSERT OR REPLACE INTO documents VALUES(?,?,?,?,?,?,?,?,?,?)",(r["document_number"],r["pdf_url"],r["pdf_path"],r["text_path"],r["sha256"],r["bytes"],r["text_chars"],w["worker_id"],w["role"],r["processed_at"])); con.execute("INSERT INTO documents_fts VALUES(?,?)",(r["document_number"],body)); indexed+=1
        except Exception as e: r.update(status="failed",error=str(e)); failed.append(r)
    con.commit(); con.close()
    (out/"results.jsonl").write_text("".join(json.dumps(r,sort_keys=True)+"\n" for r in results),encoding="utf-8")
    summary={"schema":"xunia.zyra-mss.uspto-corpus.v1","source":PPUBS,"query":a.query,"discovered":len(docs),"indexed":indexed,"failed":len(failed),"complete":indexed==len(docs) and not failed,"logical_worker_count":100,"actual_network_concurrency":workers,"generated_at":now()}
    (out/"summary.json").write_text(json.dumps(summary,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(f"🏁 discovered={len(docs)} indexed={indexed} failed={len(failed)} complete={summary['complete']}")
    return 0 if summary["complete"] else 1

def search(a):
    con=sqlite3.connect(Path(a.database).expanduser()); rows=con.execute("SELECT document_number,snippet(documents_fts,1,'[',']',' … ',20) FROM documents_fts WHERE documents_fts MATCH ? LIMIT ?",(a.terms,a.limit)).fetchall(); con.close()
    for n,s in rows: print(f"{n}\n  {s}\n")
    return 0 if rows else 1

def doctor(a):
    root=Path(a.output).expanduser(); s=json.loads((root/"summary.json").read_text()); print(json.dumps(s,indent=2,sort_keys=True)); return 0 if s.get("complete") else 1

def main():
    p=argparse.ArgumentParser(prog="zyra-mss-uspto-reader"); sp=p.add_subparsers(dest="cmd",required=True)
    c=sp.add_parser("crawl"); c.add_argument("--query",default="palantir"); c.add_argument("--output",default="~/.config/gpt-doug/zyra-mss-uspto-palantir"); c.add_argument("--max-pages",type=int,default=10000); c.add_argument("--workers",type=int,default=6); c.add_argument("--delay",type=float,default=.02); c.add_argument("--headed",action="store_true"); c.set_defaults(fn=crawl)
    s=sp.add_parser("search"); s.add_argument("terms"); s.add_argument("--database",default="~/.config/gpt-doug/zyra-mss-uspto-palantir/corpus.sqlite3"); s.add_argument("--limit",type=int,default=20); s.set_defaults(fn=search)
    d=sp.add_parser("doctor"); d.add_argument("--output",default="~/.config/gpt-doug/zyra-mss-uspto-palantir"); d.set_defaults(fn=doctor)
    a=p.parse_args(); raise SystemExit(a.fn(a))
if __name__=="__main__": main()
