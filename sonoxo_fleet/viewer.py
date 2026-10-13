"""Self-contained local portfolio viewer. No CDNs, network or remote controls."""
from __future__ import annotations

import json
from typing import Any


def render_dashboard(plan: dict[str, Any]) -> str:
    raw = json.dumps(plan, ensure_ascii=True, separators=(",", ":"), allow_nan=False)
    raw = raw.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    return _PAGE.replace("__PORTFOLIO_DATA__", raw)


_PAGE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>GPT-Doug | Sonoxo Fleet Atlas</title>
<style>
:root{font-family:system-ui,-apple-system,Segoe UI,Arial,sans-serif;color-scheme:dark;--bg:#09121f;--panel:#101f31;--card:#14283e;--line:#2c445a;--text:#eaf4fa;--muted:#9eb7c8;--aqua:#7cdee9;--orange:#fac27f}
*{box-sizing:border-box}html,body{background:var(--bg);color:var(--text);margin:0;min-height:100%}
header{display:flex;align-items:center;justify-content:space-between;padding:20px 28px;gap:12px;flex-wrap:wrap;background:#0d1c2f;border-bottom:1px solid var(--line)}
mark{background:#174457;color:#a5f0f8;border-radius:8px;padding:7px;font-weight:900;font-size:22px}
h1{font-size:17px;letter-spacing:.07em;margin:0}h2{font-size:15px;margin:0 0 10px;color:#d5e8f3}h3{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:#a4c0d3;margin:0}
.subtitle{color:var(--muted);font-size:12px;margin-top:5px}.pill{border-radius:18px;padding:6px 10px;background:#292820;border:1px solid #675438;color:var(--orange);font-size:11px;font-weight:bold}
.layout{max-width:1700px;margin:auto;padding:20px 24px}
.stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:20px}
.stat{border:1px solid var(--line);background:var(--panel);border-radius:12px;padding:16px}
.stat strong{font-size:29px;color:var(--aqua);display:block}.stat span{font-size:11px;color:var(--muted)}
.main{display:grid;grid-template-columns:minmax(0,1fr) 340px;gap:17px}
.panel{background:var(--panel);border:1px solid var(--line);padding:16px;border-radius:12px;min-width:0}
.topline{display:flex;justify-content:space-between;align-items:center;gap:14px;flex-wrap:wrap;margin-bottom:12px}
input,select,button{font:inherit;background:#152d44;color:var(--text);border:1px solid #38556e;border-radius:7px;padding:9px 10px}
button{cursor:pointer}button:hover,button:focus-visible,a:focus-visible{outline:2px solid var(--aqua);outline-offset:2px}
button.active{border-color:var(--aqua);background:#1b4960}
.search{min-width:220px;flex:1}
.filters{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:13px}
.small{font-size:11px;color:var(--muted);line-height:1.55}.muted{color:var(--muted)}
.tablewrap{max-height:670px;overflow:auto;border:1px solid var(--line);border-radius:8px}
table{width:100%;border-collapse:collapse;font-size:12px}
th{position:sticky;top:0;background:#1b334a;color:#a9c9dc;text-align:left;font-weight:700}
th,td{padding:10px 12px;border-bottom:1px solid #294156;vertical-align:top}
tbody tr:hover{background:#1b3448}
.name{font-weight:700}.role{font-size:10px;color:#a9c7d8}.mono{font-family:ui-monospace,SFMono-Regular,Consolas,monospace}
a{color:#8cdeef;text-decoration:none}a:hover{text-decoration:underline}
.category{display:inline-block;padding:3px 7px;border:1px solid #355e77;border-radius:12px;font-size:10px}
.category.core{color:#8ef0da;border-color:#3d877b}
ul{padding-left:17px;margin:10px 0;font-size:12px;color:#bed7e7;line-height:1.65}
.bar{height:8px;background:#213548;border-radius:10px;overflow:hidden;margin:6px 0 11px}
.bar span{height:100%;display:block;background:#73b7cc}
.prs{max-height:275px;overflow:auto}
.pr{font-size:11px;border-bottom:1px solid #263d51;padding:8px 0;display:block;line-height:1.35}
.warn{color:#efd39b;background:#2a2a24;border:1px solid #5c533a;padding:12px;border-radius:9px;font-size:11px;line-height:1.6}
.footer{padding:18px 28px;color:var(--muted);font-size:11px}
@media(max-width:1050px){.main{grid-template-columns:1fr}.stats{grid-template-columns:repeat(2,1fr)}}
@media(max-width:650px){.layout{padding:11px}.stats{grid-template-columns:repeat(2,1fr)}.stat strong{font-size:22px}.search{min-width:100%}td,th{padding:8px}}
</style></head>
<body>
<header><div style="display:flex;align-items:center;gap:12px"><mark>◎</mark>
<div><h1>GPT-DOUG / SONOXO FLEET ATLAS</h1>
<div class="subtitle">GitHub ecosystem inventory · review-gated upgrades · no forced merges</div></div></div>
<span class="pill">PUBLIC METADATA ONLY · READ-ONLY REPORT</span></header>
<div class="layout">
<section class="stats">
<div class="stat"><strong id="repoCount"></strong><span>Public repositories indexed</span></div>
<div class="stat"><strong id="coreCount"></strong><span>Priority integration repositories</span></div>
<div class="stat"><strong id="prCount"></strong><span>Observed open pull requests</span></div>
<div class="stat"><strong id="forkCount"></strong><span>Fork status not yet verified</span></div>
</section>
<div class="main"><main class="panel">
<div class="topline"><h2>Repository inventory</h2><span class="small" id="filtered"></span></div>
<div class="filters">
<input id="query" class="search" type="search" placeholder="Search repository, branch or subsystem" aria-label="Filter repository inventory">
<button type="button" data-mode="all" class="active">All</button>
<button type="button" data-mode="core">Priority</button>
<button type="button" data-mode="prs">Open PRs</button>
</div>
<div class="tablewrap"><table><thead><tr><th>Repository / subsystem</th><th>Base branch</th><th>Known PRs</th><th>Gate</th></tr></thead><tbody id="rows"></tbody></table></div>
<div class="small" style="padding-top:9px">Each repository is inventoried, not automatically updated. A separate tested PR is required for code changes. Source contains public metadata only.</div>
</main><aside class="panel">
<h2>Release safety gates</h2><ol id="gates" style="padding-left:20px;color:#c2d9e7;font-size:12px;line-height:1.7"></ol>
<h2>Branch distribution</h2><div id="branches" class="small"></div>
<h2>Observed pull requests</h2><div id="prList" class="prs"></div>
<div class="warn" style="margin-top:14px"><strong>Interpretation:</strong> Existing PRs are not merged merely because they appear here. CI failures, third-party license terms, default-branch differences, proprietary SDK access and release authorization require individual review. Patent references are research input, not executable licenses.</div>
<p class="small">Source date: <span id="date"></span> · snapshot hash: <span id="hash" class="mono"></span></p>
</aside></div></div>
<footer class="footer">GPT-Doug portfolio management · Independently generated from public Sonoxo metadata · No private repositories or credentials indexed.</footer>
<script>
"use strict";
const data=__PORTFOLIO_DATA__;
const $=id=>document.getElementById(id);
const state={mode:"all",query:""};
const rows=Array.isArray(data.repositories)?data.repositories:[];
function elt(name,text,className){const n=document.createElement(name);if(text!==undefined)n.textContent=String(text);if(className)n.className=className;return n}
function set(id,val){$(id).textContent=String(val)}
function render(){const list=rows.filter(r=>(state.mode==="all"||(state.mode==="core"&&r.priority==="core_review")||(state.mode==="prs"&&r.observed_open_prs>0))&&(!state.query||[r.repo,r.area,r.default_branch].join(" ").toLowerCase().includes(state.query)));const parent=$("rows");parent.replaceChildren();set("filtered",list.length+" / "+rows.length+" shown");
for(const r of list){const tr=elt("tr");const id=elt("td"),a=elt("a",r.repo.split("/")[1],"name");a.href="https://github.com/"+r.repo;a.target="_blank";a.rel="noopener noreferrer";id.append(a,elt("div",r.area,"role"));const branch=elt("td",r.default_branch,"mono");const pr=elt("td",r.observed_open_prs);const policy=elt("td");const tag=elt("span",r.priority==="core_review"?"Review PR":"Audit queue","category "+(r.priority==="core_review"?"core":""));policy.append(tag);tr.append(id,branch,pr,policy);parent.append(tr)}
}
$("query").oninput=e=>{state.query=e.target.value.toLowerCase().trim();render()};
for(const btn of document.querySelectorAll("[data-mode]"))btn.onclick=()=>{state.mode=btn.dataset.mode;for(const b of document.querySelectorAll("[data-mode]"))b.classList.toggle("active",b===btn);render()};
set("repoCount",data.repositories_indexed);set("coreCount",data.core_repositories);set("prCount",data.observed_open_prs);set("forkCount",data.fork_unknown);
set("date",data.source_date);set("hash",data.source_sha256.slice(0,16)+"…");
const gateList=$("gates");for(const gate of data.gate_order)gateList.append(elt("li",gate.replaceAll("_"," ")));
const branchRows=Object.entries(data.branches).sort((a,b)=>b[1]-a[1]);const max=branchRows.reduce((n,x)=>Math.max(n,x[1]),1);
for(const [branch,count] of branchRows){const item=elt("div");item.append(elt("div",branch+" · "+count),elt("div",undefined,"bar"));item.lastChild.append(elt("span"));item.lastChild.lastChild.style.width=(100*count/max).toFixed(2)+"%";$("branches").append(item)}
for(const pr of data.pull_requests.slice(0,200)){const a=elt("a",pr.title,"pr");a.href=pr.url;a.target="_blank";a.rel="noopener noreferrer";$("prList").append(a)}
render();
</script></body></html>"""
