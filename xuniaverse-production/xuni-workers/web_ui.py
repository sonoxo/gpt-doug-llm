#!/usr/bin/env python3
"""
Minimal web front end for the Xuni agent daemon.

Serves a single page to submit a prompt as a task (same task-file contract
the daemon already consumes) and poll for its result. No framework, no new
dependencies — stdlib http.server only, so it runs anywhere Python does.

This does NOT replace the daemon. It is a thin client: POST /submit writes
a task file to xuni-workers/tasks/, GET /result/<id> reads back whatever
the daemon already wrote to xuni-workers/results/.
"""
import hmac
import json
import os
import re
import secrets
import threading
import time
import uuid
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Even with a valid token, unlimited request rate is still a gap — this
# is a real defense-in-depth follow-on to the auth work: a leaked or
# guessed token shouldn't let someone hammer the daemon with unlimited
# claude -p dispatches (each one costs real usage). Simple sliding-window
# counter per client IP, held in memory (this process is the only writer).
RATE_LIMIT_MAX = 20
RATE_LIMIT_WINDOW_S = 60
_rate_lock = threading.Lock()
_rate_hits = defaultdict(deque)


def _rate_limited(client_ip: str) -> bool:
    now = time.time()
    with _rate_lock:
        hits = _rate_hits[client_ip]
        while hits and now - hits[0] > RATE_LIMIT_WINDOW_S:
            hits.popleft()
        if len(hits) >= RATE_LIMIT_MAX:
            return True
        hits.append(now)
        return False

# Task IDs come straight off the URL path for GET /result/<id>. Without
# validation, an id like "../../../../etc/hosts" lets a request read any
# file on disk whose name happens to end in .json (real, confirmed via a
# live curl --path-as-is request against this server during review).
_SAFE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "xuni-workers" / "tasks"
RESULTS_DIR = ROOT / "xuni-workers" / "results"
TOKEN_PATH = ROOT / "xuni-workers" / "live" / "webui.token"
PORT = 8765

for d in (TASKS_DIR, RESULTS_DIR, TOKEN_PATH.parent):
    d.mkdir(parents=True, exist_ok=True)


def _load_or_create_token() -> str:
    """Every request must present this token — binding to 127.0.0.1 alone
    doesn't stop other local processes/users on the same machine, and the
    path-traversal bug found in this session's review showed unauthenticated
    localhost access is a real attack surface, not a theoretical one."""
    if TOKEN_PATH.exists():
        existing = TOKEN_PATH.read_text().strip()
        if existing:
            return existing
    token = secrets.token_urlsafe(32)
    TOKEN_PATH.write_text(token)
    os.chmod(TOKEN_PATH, 0o600)
    return token


AUTH_TOKEN = _load_or_create_token()

INDEX_HTML = """<!doctype html>
<html><head><meta charset="utf-8"><title>Xuni Agent</title>
<style>
body{font-family:system-ui,sans-serif;max-width:680px;margin:2.5rem auto;padding:0 1rem;color:#1c2a1f;}
textarea{width:100%;min-height:110px;font-family:inherit;font-size:.95rem;padding:.6rem;box-sizing:border-box;}
button{padding:.55rem 1.1rem;font-weight:600;cursor:pointer;background:#3f6b4f;color:#fff;border:none;border-radius:4px;}
pre{background:#f2f0e8;padding:1rem;border-radius:6px;white-space:pre-wrap;font-size:.85rem;overflow-x:auto;}
.status{color:#6b6f63;font-size:.85rem;margin:.5rem 0;}
</style></head>
<body>
<h1>Xuni Agent</h1>
<p>Type a task for Doug. It goes through the real daemon: Zyra guard &rarr; claude -p --agent doug.</p>
<textarea id="prompt" placeholder="e.g. list the files in this repo"></textarea><br><br>
<button onclick="submitTask()">Send to Doug</button>
<div class="status" id="status"></div>
<pre id="output"></pre>
<script>
const TOKEN = new URLSearchParams(window.location.search).get('token') || '';
function authed(url, opts){
  opts = opts || {};
  opts.headers = Object.assign({}, opts.headers, {'X-Auth-Token': TOKEN});
  return fetch(url, opts);
}
async function submitTask(){
  const prompt = document.getElementById('prompt').value.trim();
  const status = document.getElementById('status');
  const output = document.getElementById('output');
  if(!prompt){ status.textContent = 'Enter a prompt first.'; return; }
  output.textContent = '';
  status.textContent = 'Submitting...';
  const res = await authed('/submit', {method:'POST', body: JSON.stringify({prompt})});
  if(res.status === 401){ status.textContent = 'Not authorized — missing or wrong token.'; return; }
  const {id} = await res.json();
  status.textContent = 'Task ' + id + ' queued. Waiting for result...';
  for(let i=0;i<120;i++){
    await new Promise(r=>setTimeout(r,1000));
    const r = await authed('/result/' + id);
    if(r.status === 200){
      const data = await r.json();
      status.textContent = data.blocked_by ? 'Blocked by Zyra' : ('Done in ' + data.duration_seconds + 's');
      output.textContent = JSON.stringify(data, null, 2);
      return;
    }
  }
  status.textContent = 'Timed out waiting for result.';
}
</script>
</body></html>
"""


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep stdout clean; daemon.log pattern already covers this

    def _authorized(self, query: dict) -> bool:
        """Constant-time comparison so response timing can't be used to
        guess the token a character at a time."""
        supplied = self.headers.get("X-Auth-Token") or (query.get("token", [""])[0])
        return hmac.compare_digest(supplied or "", AUTH_TOKEN)

    def do_GET(self):
        if _rate_limited(self.client_address[0]):
            self._send(429, b'{"error":"rate limited"}', "application/json")
            return

        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        if not self._authorized(query):
            self._send(401, b'{"error":"unauthorized"}', "application/json")
            return

        if path == "/":
            self._send(200, INDEX_HTML.encode(), "text/html")
        elif path.startswith("/result/"):
            task_id = path[len("/result/"):]
            if not _SAFE_ID_RE.match(task_id):
                self._send(400, b'{"error":"invalid task id"}', "application/json")
                return
            result_path = RESULTS_DIR / f"{task_id}.json"
            if result_path.exists():
                self._send(200, result_path.read_bytes(), "application/json")
            else:
                self._send(404, b'{"status":"pending"}', "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        if _rate_limited(self.client_address[0]):
            self._send(429, b'{"error":"rate limited"}', "application/json")
            return
        if not self._authorized({}):
            self._send(401, b'{"error":"unauthorized"}', "application/json")
            return
        if urlparse(self.path).path != "/submit":
            self._send(404, b"not found", "text/plain")
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._send(400, b'{"error":"invalid json"}', "application/json")
            return
        prompt = body.get("prompt", "").strip()
        if not prompt:
            self._send(400, b'{"error":"missing prompt"}', "application/json")
            return
        task_id = f"web-{uuid.uuid4().hex[:10]}"
        task = {"id": task_id, "prompt": prompt, "submitted_at": time.time(), "source": "web_ui"}
        (TASKS_DIR / f"{task_id}.json").write_text(json.dumps(task))
        self._send(200, json.dumps({"id": task_id}).encode(), "application/json")

    def _send(self, code, body, content_type):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"xuni web ui listening on http://127.0.0.1:{PORT}?token={AUTH_TOKEN}", flush=True)
    print(f"token also saved at {TOKEN_PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
