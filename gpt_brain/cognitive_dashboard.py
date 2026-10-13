"""Local-only visual inspection of synthetic and BioPineal research evidence.

No network fetching, outside assets, auth tokens, remote binding or data capture.
The service is started explicitly and stopped with Ctrl+C.
"""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from urllib.parse import parse_qs, urlsplit

from ai_killswitch import require_ai_allowed
from .evidence_fusion import build_demo_graph, fuse, validated_observations

DEFAULT_QUERY = "BioPineal patent evidence verification"

HTML = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>GPT-Doug | Cognitive Research Lab</title>
<style>
:root{color-scheme:dark;font:14px system-ui,Arial,sans-serif;background:#070e1b;color:#e6effa}
*{box-sizing:border-box}
body{max-width:1250px;margin:0 auto;padding:30px 22px}
header{display:flex;gap:22px;justify-content:space-between;align-items:center;border-bottom:1px solid #23374e;padding-bottom:22px}
.brand{font-weight:800;font-size:1.55rem;letter-spacing:.02em}
.brand span{color:#57cedc}.muted,small{color:#91a7c0}
.pill{border:1px solid #355e76;background:#0e2538;color:#8de4dc;border-radius:20px;padding:7px 12px;font-weight:650;font-size:.83rem}
.intro{padding:23px 0;display:flex;flex-wrap:wrap;gap:20px;justify-content:space-between;align-items:center}
h1{font-size:1.5rem;line-height:1.2;margin:0 0 8px}h2{font-size:1.02rem;margin:0 0 15px}
p{margin:0;line-height:1.55}.panel{border:1px solid #27405b;background:#0d1b2d;border-radius:15px;padding:18px}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-bottom:16px}
.value{font-size:1.9rem;font-weight:800;margin-top:8px;color:#e7f6ff}
.workers{display:grid;grid-template-columns:repeat(4,1fr);gap:13px;margin-bottom:16px}
.workers .panel{min-height:137px}.worker-state{color:#a7d6e3;font-size:1.2rem;font-weight:700;margin-top:14px}
.workspace{display:grid;grid-template-columns:minmax(0,1.7fr) minmax(280px,1fr);gap:16px}
.search{width:100%;display:flex;gap:10px;margin:0 0 16px}
input{width:100%;font:inherit;background:#091625;color:#e6effa;border:1px solid #31526c;border-radius:9px;padding:12px}
button{font:inherit;white-space:nowrap;border:0;border-radius:9px;padding:10px 18px;background:#74d6dc;color:#062233;font-weight:750;cursor:pointer}
button:disabled{opacity:.5;cursor:not-allowed}
.warn{color:#ffca8d}.good{color:#8ce6b9}
table{border-collapse:collapse;width:100%;font-size:.82rem}
th,td{padding:10px 7px;border-bottom:1px solid #27405b;text-align:left;overflow-wrap:anywhere}
th{color:#94adc2}
.scroll{max-height:390px;overflow:auto}
.notice{margin-top:14px;padding:12px;border-radius:9px;background:#261f1a;border:1px solid #624e38;color:#f6d7a8}
ul{padding-left:18px;margin:8px 0}li{margin-bottom:9px;line-height:1.5}
footer{font-size:.84rem;color:#92a9c2;border-top:1px solid #23374e;margin-top:24px;padding-top:18px}
@media(max-width:980px){.stats,.workers{grid-template-columns:repeat(2,1fr)}.workspace{grid-template-columns:1fr}}
@media(max-width:540px){.stats,.workers{grid-template-columns:1fr 1fr}body{padding:16px}.search{flex-wrap:wrap}button{width:100%}}
</style></head><body>
<header><div class="brand">GPT-DOUG <span>/ COGNITIVE LAB</span></div>
<div class="pill">OFFLINE DEMO · LOCALHOST</div></header>
<section class="intro"><div><h1>Research intelligence workspace</h1>
<p class="muted">Provenance-linked analysis of permitted demo observations. No model calls, no global feeds.</p></div>
<div id="state" class="pill" role="status" aria-live="polite">Checking local research engine</div></section>
<form id="question-form" class="search">
<label for="question" class="muted" style="align-self:center">Question</label>
<input id="question" maxlength="512" value="BioPineal patent evidence verification" aria-label="Evidence research question" required>
<button type="submit" id="evaluate">Evaluate</button>
</form>
<div class="stats">
<div class="panel"><small>Matched observations</small><div class="value" id="matched">—</div></div>
<div class="panel"><small>Declared sources</small><div class="value" id="sources">—</div></div>
<div class="panel"><small>Conflicts</small><div class="value" id="conflicts">—</div></div>
<div class="panel"><small>Stale readings</small><div class="value" id="stale">—</div></div>
</div>
<div class="workers">
<section class="panel"><h2>Evidence curator</h2><small>Query-aware matching</small><div id="w-curator" class="worker-state">Pending</div></section>
<section class="panel"><h2>Consistency critic</h2><small>Contradictions and disagreements</small><div id="w-critic" class="worker-state">Pending</div></section>
<section class="panel"><h2>Freshness reviewer</h2><small>Age of observations</small><div id="w-fresh" class="worker-state">Pending</div></section>
<section class="panel"><h2>Governance auditor</h2><small>Source and action policy</small><div id="w-govern" class="worker-state">Pending</div></section>
</div>
<div class="workspace">
<section class="panel"><h2>Bounded evidence stream</h2><div class="scroll"><table>
<thead><tr><th>Metric</th><th>Reported value</th><th>Source</th><th>State</th></tr></thead>
<tbody id="evidence"></tbody></table></div></section>
<section class="panel"><h2>Audit findings</h2><ul id="issues"></ul>
<div class="notice" id="trust">All evidence sources are declared, not independently authenticated.</div>
<h2 style="margin-top:20px">Human review steps</h2><ul id="steps"></ul></section>
</div>
<footer>Research-only demonstration. Does not connect to live physical sensors or externally verify patents.
Checksum integrity is not source authenticity. No autonomous external actions, paid API calls, or automatic ontology promotion.</footer>
<script>
const byId=id=>document.getElementById(id);
function setText(id,value){byId(id).textContent=String(value)}
function addTextRow(tbody,fields){
 const row=document.createElement('tr');
 fields.forEach(field=>{const cell=document.createElement('td');cell.textContent=String(field);row.appendChild(cell)});
 tbody.appendChild(row);
}
function fillList(id,items){
 const list=byId(id);list.replaceChildren();
 items.forEach(item=>{const li=document.createElement('li');li.textContent=String(item);list.appendChild(li)});
}
async function evaluate(){
 const q=byId('question').value.trim();
 if(q.length<3||q.length>512){setText('state','Question must be 3–512 characters');return}
 byId('evaluate').disabled=true;setText('state','Analyzing local demo evidence');
 try{
  const response=await fetch('/api/brief?q='+encodeURIComponent(q),{cache:'no-store'});
  if(!response.ok)throw Error('Research request rejected: '+response.status);
  const data=await response.json(), workers=data.workers;
  const curator=workers.evidence_curator, critic=workers.consistency_critic;
  const fresh=workers.freshness_reviewer, gov=workers.governance_auditor;
  setText('matched',curator.matched_count);
  setText('sources',gov.declared_source_count);
  setText('conflicts',critic.length);
  setText('stale',fresh.stale);
  setText('w-curator',curator.matched_count+' matched');
  setText('w-critic',critic.length?'Review needed':'No conflicts flagged');
  setText('w-fresh',fresh.stale+' stale');
  setText('w-govern',gov.source_authenticity_verified?'Verified':'Unverified source');
  const body=byId('evidence');body.replaceChildren();
  curator.evidence.forEach(e=>addTextRow(body,[e.metric,e.value,e.source_id,e.source_authenticity]));
  if(!curator.evidence.length)addTextRow(body,['No matching evidence','—','—','UNVERIFIED']);
  fillList('issues',data.issues);
  fillList('steps',data.next_review_steps);
  setText('trust',data.summary+' This does not establish independent authenticity.');
  setText('state','Offline assessment complete');
 }catch(e){setText('state','Local research unavailable')}
 finally{byId('evaluate').disabled=false}
}
byId('question-form').addEventListener('submit',e=>{e.preventDefault();evaluate()});
evaluate();
</script></body></html>"""

def build_server(port: int = 8777, *, graph: dict | None = None,
                 default_question: str = DEFAULT_QUERY) -> ThreadingHTTPServer:
    """Create a loopback-only, read-only research demo service."""
    require_ai_allowed("cognitive research console startup")
    if type(port) is not int or not 0 <= port <= 65535:
        raise ValueError("port must be a TCP port (0 reserved for tests)")
    if not isinstance(default_question, str) or not 3 <= len(default_question) <= 512:
        raise ValueError("invalid research question")
    graph = graph if graph is not None else build_demo_graph()
    validated_observations(graph)
    class Handler(BaseHTTPRequestHandler):
        def _send(self, code: int, data: bytes, content_type: str):
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy",
                             "default-src 'none'; connect-src 'self'; "
                             "script-src 'unsafe-inline'; style-src 'unsafe-inline'; form-action 'self'")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.end_headers()
            self.wfile.write(data)
        def _error(self, code, message):
            self._send(code, json.dumps({"error": message}).encode("utf-8"),
                       "application/json; charset=utf-8")
        def do_GET(self):
            if len(self.path) > 1500:
                self._error(414, "URI too long")
                return
            bound_port = self.server.server_address[1]
            allowed_hosts = {"127.0.0.1", "localhost",
                             "127.0.0.1:" + str(bound_port),
                             "localhost:" + str(bound_port)}
            if self.headers.get("Host", "") not in allowed_hosts:
                self._error(403, "localhost-only host header required")
                return
            parts = urlsplit(self.path)
            if parts.path == "/" and not parts.query:
                self._send(200, HTML.encode("utf-8"), "text/html; charset=utf-8")
            elif parts.path == "/api/brief":
                try:
                    params = parse_qs(parts.query, keep_blank_values=True,
                                      strict_parsing=False, max_num_fields=3)
                    if set(params) - {"q"} or len(params.get("q", [])) > 1:
                        raise ValueError("unknown query parameters")
                    question = params.get("q", [default_question])[0]
                    result = fuse(graph, question)
                    self._send(200, json.dumps(result).encode("utf-8"),
                               "application/json; charset=utf-8")
                except (ValueError, PermissionError):
                    self._error(400, "invalid question or cooperative AI stop is active")
            else:
                self._error(404, "not found")
        def log_message(self, fmt, *args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    server.daemon_threads = True
    return server

def serve_demo(port: int = 8777) -> None:
    server = build_server(port)
    print("GPT-Doug research demo: http://127.0.0.1:%d/" %
          server.server_address[1], flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
