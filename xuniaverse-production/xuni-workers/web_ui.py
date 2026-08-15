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
import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = ROOT / "xuni-workers" / "tasks"
RESULTS_DIR = ROOT / "xuni-workers" / "results"
PORT = 8765

for d in (TASKS_DIR, RESULTS_DIR):
    d.mkdir(parents=True, exist_ok=True)

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
async function submitTask(){
  const prompt = document.getElementById('prompt').value.trim();
  const status = document.getElementById('status');
  const output = document.getElementById('output');
  if(!prompt){ status.textContent = 'Enter a prompt first.'; return; }
  output.textContent = '';
  status.textContent = 'Submitting...';
  const res = await fetch('/submit', {method:'POST', body: JSON.stringify({prompt})});
  const {id} = await res.json();
  status.textContent = 'Task ' + id + ' queued. Waiting for result...';
  for(let i=0;i<120;i++){
    await new Promise(r=>setTimeout(r,1000));
    const r = await fetch('/result/' + id);
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

    def do_GET(self):
        path = urlparse(self.path).path
        if path == "/":
            self._send(200, INDEX_HTML.encode(), "text/html")
        elif path.startswith("/result/"):
            task_id = path[len("/result/"):]
            result_path = RESULTS_DIR / f"{task_id}.json"
            if result_path.exists():
                self._send(200, result_path.read_bytes(), "application/json")
            else:
                self._send(404, b'{"status":"pending"}', "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
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
    print(f"xuni web ui listening on http://127.0.0.1:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
