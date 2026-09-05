from __future__ import annotations

import os

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse

app = FastAPI(title="XUNIA Forge Control Plane", version="0.1.0")
LITELLM = os.getenv("LITELLM_URL", "http://gateway:4000")
SEARXNG = os.getenv("SEARXNG_URL", "http://search:8080")


@app.get("/api/health")
async def health():
    async with httpx.AsyncClient(timeout=4) as client:
        async def probe(url):
            try:
                return (await client.get(url)).status_code < 500
            except httpx.HTTPError:
                return False

        gateway = await probe(f"{LITELLM}/health/liveliness")
        search = await probe(f"{SEARXNG}/")
    return {
        "control": True,
        "gateway": gateway,
        "search": search,
        "ready": gateway and search,
    }


@app.get("/api/search")
async def research(q: str = Query(min_length=2, max_length=300)):
    async with httpx.AsyncClient(timeout=20) as client:
        try:
            response = await client.get(
                f"{SEARXNG}/search",
                params={"q": q, "format": "json", "safesearch": 1},
            )
        except httpx.HTTPError as exc:
            raise HTTPException(502, "Research service unavailable") from exc
    if response.status_code != 200:
        raise HTTPException(502, "Research provider rejected the request")
    rows = response.json().get("results", [])[:10]
    return {
        "query": q,
        "results": [
            {
                "title": row.get("title"),
                "url": row.get("url"),
                "content": row.get("content"),
                "engine": row.get("engine"),
            }
            for row in rows
        ],
    }


@app.get("/", response_class=HTMLResponse)
def home():
    return '''<!doctype html><meta name="viewport" content="width=device-width"><title>XUNIA Forge</title><style>body{background:#05070a;color:#d7eeee;font:15px ui-monospace,monospace;max-width:1000px;margin:60px auto;padding:20px}h1{color:#66ff9f}section{border:1px solid #204149;background:#0a1115;padding:20px;margin:14px 0}input{width:70%;padding:12px;background:#060a0d;color:white;border:1px solid #28717d}button{padding:12px;background:#66ff9f;border:0}a{color:#42dcff}.ok{color:#66ff9f}.bad{color:#ff6572}</style><h1>XUNIA FORGE // SUPERTOOL</h1><section id="health">Checking services…</section><section><h2>Private research</h2><input id="q" placeholder="Research a technical topic"><button onclick="go()">SEARCH</button><div id="r"></div></section><section><b>Gateway</b> http://127.0.0.1:4000/v1<br><b>SearXNG</b> http://127.0.0.1:8088<br><b>Continue</b> use continue/config.yaml</section><script>async function h(){let x=await fetch('/api/health').then(r=>r.json());health.innerHTML=Object.entries(x).map(([k,v])=>`<b class="${v?'ok':'bad'}">${k.toUpperCase()}: ${v?'ONLINE':'OFFLINE'}</b>`).join(' · ')}async function go(){r.textContent='Searching…';let x=await fetch('/api/search?q='+encodeURIComponent(q.value)).then(v=>v.json());r.innerHTML=(x.results||[]).map(v=>`<p><a target="_blank" rel="noopener" href="${v.url}">${v.title}</a><br>${v.content||''}</p>`).join('')||'No results'}h()</script>'''
