#!/usr/bin/env python3
"""GPT Doug vibe-coding platform server.

Serves the frontend, streams chat responses from a local Ollama model,
and manages simple file-based "projects" that can be generated, saved,
and previewed statically — all on one origin so there's no CORS to fight.
"""

import atexit
import json
import mimetypes
import os
import re
import signal
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

from agents import agent_chain
from web import auth
from web import crypto_store
from web import ideas
from web import paid_tasks
from web import stripe_checkout
from web import users
from web import worker
from agents import llm_backend
from web import twilio_webhook
from web.runner import ProjectRunner
from zyra import Zyra

DIR = os.path.dirname(os.path.abspath(__file__))
PROJECTS_DIR = os.path.join(DIR, "projects")
MODEL = llm_backend.DEFAULT_MODEL
PORT = int(os.environ.get("PORT", "8787"))
SERVER_STARTED_AT = time.time()

# Set to enable the /twilio/sms webhook. Left unset, the endpoint stays
# disabled (404) rather than silently accepting unsigned requests.
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
# Public base URL Twilio actually hits (e.g. https://doug.example.com) —
# required because Twilio signs the *exact* URL it called, not the path.
TWILIO_PUBLIC_URL = os.environ.get("TWILIO_PUBLIC_URL", "").rstrip("/")

# Public base URL this server is reachable at, used to build Stripe
# Checkout success/cancel redirect URLs (e.g. the ngrok tunnel URL).
PUBLIC_URL = os.environ.get("PUBLIC_URL", "").rstrip("/")

# Shared watchdog: same audit log (~/.gpt-doug/zyra-audit.jsonl) used by the
# gpt-doug-llm terminal client, so both surfaces write to one audit trail.
# No HMAC key here (this app doesn't have the CLI's Astral identity setup),
# so events are logged unsigned — still fail-closed on blocked verdicts.
zyra = Zyra()
runner = ProjectRunner()

# In-memory registry of background agent-chain jobs. Each job runs the
# planner->executor->reviewer chain in its own thread since a single run
# can take minutes against local models; the HTTP layer only ever starts a
# job and polls its status, never blocks a request on the full chain.
_agent_jobs_lock = threading.Lock()
_agent_jobs: dict[str, dict] = {}


def _run_agent_job(job_id, task):
    def on_event(event):
        with _agent_jobs_lock:
            _agent_jobs[job_id]["events"].append(event)

    try:
        trace = agent_chain.run(task, on_event=on_event)
        with _agent_jobs_lock:
            _agent_jobs[job_id]["status"] = "done"
            _agent_jobs[job_id]["trace"] = trace
    except Exception as err:  # noqa: BLE001
        with _agent_jobs_lock:
            _agent_jobs[job_id]["status"] = "error"
            _agent_jobs[job_id]["error"] = str(err)


def _run_paid_task(task_id):
    """Runs once Stripe's webhook confirms real payment — never before."""
    record = paid_tasks.get(task_id)
    if not record:
        return
    paid_tasks.set_status(task_id, "processing")
    try:
        trace = agent_chain.run(record["task"])
        paid_tasks.set_status(task_id, "done", run_id=trace["run_id"], result=trace.get("transcript", ""))
    except Exception as err:  # noqa: BLE001
        paid_tasks.set_status(task_id, "failed", result=str(err))

SYSTEM_PROMPT = (
    "You are GPT Doug, an optimistic local-first AI builder. Your signal word "
    "is EUREKA. Help users design, code, debug, explain, and launch useful "
    "software. Be direct, imaginative, technically accurate, and honest about "
    "limitations. Protect privacy. Never claim an action happened unless it "
    "actually did. Ask before destructive operations, publishing private "
    "material, spending money, or contacting people. Keep humans in command.\n\n"
    "When the user asks you to build, create, scaffold, or generate a file or "
    "project, output each file as its own fenced code block. Immediately "
    "before the opening ``` of each file you intend the user to save, add a "
    "line in exactly this format: // filename: path/to/file.ext (use "
    "'# filename: path' instead for languages where // is not a comment, "
    "such as Python, shell, or YAML). Only add a filename marker to blocks "
    "meant to be saved as real files — not to short illustrative snippets. "
    "After the code blocks, briefly summarize what you built. For normal "
    "conversation that isn't a build request, do not use filename markers."
)

# Matches the tuning in gpt-doug-llm/Modelfile so both surfaces reason the
# same way; callers may still override per-request via payload["options"].
DEFAULT_OLLAMA_OPTIONS = {"temperature": 0.7, "num_ctx": 8192}

NAME_RE = re.compile(r"^[a-zA-Z0-9_-]{1,64}$")
MAX_BODY_BYTES = 10 * 1024 * 1024  # 10MB — generous for source files, small enough to bound abuse

# Custom header required on every state-changing request. Cross-origin
# fetch() calls that set a non-"simple" header (this one) force the browser
# to send a CORS preflight first; since we never answer with an
# Access-Control-Allow-Origin header, the browser blocks the real request
# before it reaches us. This closes the "text/plain simple-request" CSRF
# path a malicious page could otherwise use to write files here silently.
CSRF_HEADER = "X-Doug-Client"

os.makedirs(PROJECTS_DIR, exist_ok=True)


def safe_project_path(name, *parts):
    """Resolve a path inside a single project, refusing anything that
    would escape that project's own directory (not just the shared
    projects/ root — cross-project paths like '../other-project/x' are
    rejected too)."""
    if not NAME_RE.match(name):
        return None
    root = os.path.realpath(PROJECTS_DIR)
    base = os.path.realpath(os.path.join(root, name))
    if os.path.commonpath([root, base]) != root or base == root:
        return None
    target = os.path.realpath(os.path.join(base, *parts)) if parts else base
    if os.path.commonpath([base, target]) != base:
        return None
    return target


def list_files(base):
    out = []
    for root, _dirs, files in os.walk(base):
        for f in files:
            full = os.path.join(root, f)
            rel = os.path.relpath(full, base)
            out.append(rel.replace(os.sep, "/"))
    return sorted(out)


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        pass

    def _json(self, code, payload):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            return json.loads(raw or b"{}")
        except json.JSONDecodeError:
            return None

    def _csrf_ok(self):
        return self.headers.get(CSRF_HEADER) is not None

    def _authed(self):
        token = auth.parse_cookie(self.headers.get("Cookie", ""), "doug_session")
        return auth.valid_session(token)

    def _current_username(self):
        """The logged-in *person* (users.py), distinct from the single
        operator password gate above. None if no personal account is
        active — callers fall back to a generic owner in that case."""
        token = auth.parse_cookie(self.headers.get("Cookie", ""), "doug_user")
        return users.current_user(token)

    def _set_session_cookie(self, token):
        # Secure omitted: this runs behind a TLS-terminating tunnel/proxy in
        # deployed use, but also needs to work over plain http://localhost
        # in local dev, where a Secure cookie would silently never be sent.
        self.send_header("Set-Cookie", f"doug_session={token}; HttpOnly; SameSite=Lax; Max-Age={auth.SESSION_TTL}; Path=/")

    def _respond_with_user_cookie(self, token):
        body = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Set-Cookie", f"doug_user={token}; HttpOnly; SameSite=Lax; Max-Age={users.SESSION_TTL}; Path=/")
        self.end_headers()
        self.wfile.write(body)

    # ---------- GET ----------

    UNAUTH_PATHS = {
        "/login", "/login.js", "/app.css", "/ads.txt", "/feed", "/feed.js", "/api/ideas/feed",
        "/buy", "/buy.js", "/paid-task.html", "/paid-task.js",
    }

    PAID_TASK_STATUS_RE = re.compile(r"^/api/paid-tasks/[a-f0-9]{12}$")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        is_unauth = path in self.UNAUTH_PATHS or self.PAID_TASK_STATUS_RE.match(path)
        if not is_unauth and not self._authed():
            if path.startswith("/api/"):
                return self._json(401, {"error": "not logged in"})
            self.send_response(302)
            self.send_header("Location", "/login")
            self.send_header("Content-Length", "0")
            self.end_headers()
            return

        if path in ("/", "/index.html"):
            return self._serve_file(os.path.join(DIR, "index.html"), "text/html; charset=utf-8")
        if path == "/app.js":
            return self._serve_file(os.path.join(DIR, "app.js"), "application/javascript; charset=utf-8")
        if path == "/app.css":
            return self._serve_file(os.path.join(DIR, "app.css"), "text/css; charset=utf-8")

        if path == "/api/health":
            status = llm_backend.health()
            status.update({
                "zyra_active": True,
                "zyra_policy_version": Zyra.POLICY_VERSION,
                "zyra_audit_path": str(zyra.audit_path),
            })
            return self._json(200, status)

        if path == "/api/projects":
            names = sorted(
                d for d in os.listdir(PROJECTS_DIR)
                if os.path.isdir(os.path.join(PROJECTS_DIR, d))
            )
            return self._json(200, {"projects": names})

        m = re.match(r"^/api/agents/run/([a-f0-9]{12})$", path)
        if m:
            with _agent_jobs_lock:
                job = _agent_jobs.get(m.group(1))
            if not job:
                return self._json(404, {"error": "job not found"})
            return self._json(200, job)

        if path == "/api/agents/runs":
            entries = []
            if os.path.isdir(agent_chain.RUNS_DIR):
                for fname in sorted(os.listdir(agent_chain.RUNS_DIR), reverse=True):
                    if not fname.endswith(".json"):
                        continue
                    try:
                        with open(os.path.join(agent_chain.RUNS_DIR, fname)) as f:
                            trace = json.load(f)
                    except (OSError, json.JSONDecodeError):
                        continue
                    entries.append({
                        "run_id": trace.get("run_id"),
                        "task": trace.get("task"),
                        "started_at": trace.get("started_at"),
                        "duration_s": trace.get("duration_s"),
                        "passed": (trace.get("review") or {}).get("passed"),
                    })
            return self._json(200, {"runs": entries})

        m = re.match(r"^/api/agents/runs/([a-f0-9]{12})$", path)
        if m:
            fpath = os.path.join(agent_chain.RUNS_DIR, f"{m.group(1)}.json")
            if not os.path.isfile(fpath):
                return self._json(404, {"error": "run not found"})
            with open(fpath) as f:
                return self._json(200, json.load(f))

        if path == "/api/users/me":
            username = self._current_username()
            return self._json(200, {"username": username})

        if path == "/api/worker/status":
            return self._json(200, worker.status())

        if path == "/api/ideas":
            return self._json(200, {"ideas": ideas.list_all()})

        if path == "/api/ideas/feed":
            return self._json(200, {"ideas": ideas.list_all(status="shipped")})

        m = re.match(r"^/api/ideas/([a-f0-9]{12})$", path)
        if m:
            idea = ideas.get(m.group(1))
            if not idea:
                return self._json(404, {"error": "idea not found"})
            return self._json(200, idea)

        if path == "/agents":
            return self._serve_file(os.path.join(DIR, "agents.html"), "text/html; charset=utf-8")
        if path == "/agents.js":
            return self._serve_file(os.path.join(DIR, "agents.js"), "application/javascript; charset=utf-8")

        if path == "/feed":
            return self._serve_file(os.path.join(DIR, "feed.html"), "text/html; charset=utf-8")
        if path == "/feed.js":
            return self._serve_file(os.path.join(DIR, "feed.js"), "application/javascript; charset=utf-8")

        if path == "/ads.txt":
            body = b"google.com, pub-4726887877045421, DIRECT, f08c47fec0942fa0\n"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)

        if path == "/buy":
            return self._serve_file(os.path.join(DIR, "buy.html"), "text/html; charset=utf-8")
        if path == "/buy.js":
            return self._serve_file(os.path.join(DIR, "buy.js"), "application/javascript; charset=utf-8")
        if path == "/paid-task.html":
            return self._serve_file(os.path.join(DIR, "paid-task.html"), "text/html; charset=utf-8")
        if path == "/paid-task.js":
            return self._serve_file(os.path.join(DIR, "paid-task.js"), "application/javascript; charset=utf-8")

        if path == "/api/paid-tasks/all":
            return self._json(200, {"tasks": paid_tasks.list_all()})

        m = re.match(r"^/api/paid-tasks/([a-f0-9]{12})$", path)
        if m:
            task = paid_tasks.get(m.group(1))
            if not task:
                return self._json(404, {"error": "task not found"})
            return self._json(200, task)

        if path == "/login":
            return self._serve_file(os.path.join(DIR, "login.html"), "text/html; charset=utf-8")
        if path == "/login.js":
            return self._serve_file(os.path.join(DIR, "login.js"), "application/javascript; charset=utf-8")

        if path == "/dashboard":
            return self._serve_file(os.path.join(DIR, "dashboard.html"), "text/html; charset=utf-8")
        if path == "/dashboard.js":
            return self._serve_file(os.path.join(DIR, "dashboard.js"), "application/javascript; charset=utf-8")

        if path == "/api/dashboard":
            running = {r["name"]: r for r in runner.list_running()}
            projects = []
            for d in sorted(os.listdir(PROJECTS_DIR)):
                base = os.path.join(PROJECTS_DIR, d)
                if not os.path.isdir(base):
                    continue
                files = list_files(base)
                projects.append({
                    "name": d,
                    "file_count": len(files),
                    "running": running.get(d),
                })
            return self._json(200, {
                "projects": projects,
                "server_uptime_s": round(time.time() - SERVER_STARTED_AT, 1),
                "ollama": llm_backend.health(),
            })

        m = re.match(r"^/api/projects/([^/]+)/files$", path)
        if m:
            base = safe_project_path(m.group(1))
            if base is None or not os.path.isdir(base):
                return self._json(404, {"error": "project not found"})
            return self._json(200, {"files": list_files(base)})

        m = re.match(r"^/api/projects/([^/]+)/run$", path)
        if m:
            base = safe_project_path(m.group(1))
            if base is None or not os.path.isdir(base):
                return self._json(404, {"error": "project not found"})
            files = list_files(base)
            logs = [f"$ scanning project '{m.group(1)}'", f"found {len(files)} file(s)"]
            entry = None
            for candidate in ("index.html", "public/index.html"):
                if candidate in files:
                    entry = candidate
                    break
            if entry:
                logs.append(f"entry point: {entry}")
                logs.append("build ok")
                return self._json(200, {
                    "ok": True,
                    "logs": logs,
                    "preview_url": f"/preview/{m.group(1)}/{entry}",
                })
            logs.append("no index.html found — nothing to preview yet")
            return self._json(200, {"ok": False, "logs": logs, "preview_url": None})

        m = re.match(r"^/api/projects/([^/]+)/status$", path)
        if m:
            base = safe_project_path(m.group(1))
            if base is None or not os.path.isdir(base):
                return self._json(404, {"error": "project not found"})
            return self._json(200, runner.status(m.group(1)))

        m = re.match(r"^/preview/([^/]+)/(.*)$", path)
        if m:
            base = safe_project_path(m.group(1))
            rel = m.group(2) or "index.html"
            target = safe_project_path(m.group(1), rel)
            if base is None or target is None or not os.path.isfile(target):
                return self._json(404, {"error": "file not found"})
            mime = mimetypes.guess_type(target)[0] or "application/octet-stream"
            return self._serve_project_file(target, mime)

        self._json(404, {"error": "not found"})

    def _serve_project_file(self, path, content_type):
        """Like _serve_file, but transparently decrypts project files that
        were encrypted at rest by crypto_store."""
        if not os.path.isfile(path):
            return self._json(404, {"error": "not found"})
        with open(path, "rb") as f:
            raw = f.read()
        try:
            body = crypto_store.decrypt_bytes(raw)
        except ValueError as err:
            return self._json(500, {"error": str(err)})
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _serve_file(self, path, content_type):
        if not os.path.isfile(path):
            return self._json(404, {"error": "not found"})
        with open(path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ---------- POST ----------

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # Twilio's webhook can't send our custom CSRF header, and doesn't
        # need to: its own request signature (checked in _handle_twilio_sms)
        # is the auth boundary for this one route.
        if path == "/twilio/sms":
            try:
                return self._handle_twilio_sms()
            except ValueError as err:
                return self._json(413, {"error": str(err)})

        if path == "/api/auth/login":
            return self._handle_login()

        # Stripe's webhook can't send our custom CSRF header either; its
        # own request signature (checked in _handle_stripe_webhook) is the
        # auth boundary for this route, same pattern as Twilio above.
        if path == "/webhook/stripe":
            return self._handle_stripe_webhook()

        # Anonymous buyers aren't logged in and never will be — this is the
        # one write endpoint the public can hit, deliberately narrow (just
        # creates a pending-payment record + a Stripe Checkout redirect,
        # nothing runs until the webhook confirms real payment).
        if path == "/api/paid-tasks":
            return self._handle_create_paid_task()

        if not self._csrf_ok():
            return self._json(403, {"error": f"missing required {CSRF_HEADER} header"})

        if not self._authed():
            return self._json(401, {"error": "not logged in"})

        try:
            return self._route_post(path)
        except ValueError as err:
            return self._json(413, {"error": str(err)})

    def _handle_login(self):
        ip = self.client_address[0]
        if auth.rate_limited(ip):
            return self._json(429, {"error": "too many attempts, try again shortly"})
        payload = self._read_json()
        password = (payload or {}).get("password", "")
        if not auth.check_password(password):
            return self._json(401, {"error": "invalid password"})
        token = auth.create_session()
        body = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._set_session_cookie(token)
        self.end_headers()
        self.wfile.write(body)

    def _route_post(self, path):
        if path == "/api/chat":
            return self._handle_chat(stream=False)
        if path == "/api/chat/stream":
            return self._handle_chat(stream=True)

        if path == "/api/projects":
            payload = self._read_json()
            if not payload or not NAME_RE.match(payload.get("name", "")):
                return self._json(400, {"error": "invalid project name (use letters, numbers, - or _)"})
            base = safe_project_path(payload["name"])
            if os.path.exists(base):
                return self._json(200, {"ok": True, "name": payload["name"], "created": False})
            os.makedirs(base, exist_ok=True)
            return self._json(201, {"ok": True, "name": payload["name"], "created": True})

        m = re.match(r"^/api/projects/([^/]+)/files$", path)
        if m:
            payload = self._read_json()
            base = safe_project_path(m.group(1))
            if base is None:
                return self._json(400, {"error": "invalid project name"})
            os.makedirs(base, exist_ok=True)
            files = (payload or {}).get("files", [])
            written = []
            for f in files:
                rel = f.get("path", "").lstrip("/")
                content = f.get("content", "")
                target = safe_project_path(m.group(1), rel)
                if target is None or not rel:
                    continue
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with open(target, "wb") as out:
                    out.write(crypto_store.encrypt_bytes(content.encode("utf-8")))
                written.append(rel)
            return self._json(200, {"ok": True, "written": written})

        if path == "/api/agents/run":
            payload = self._read_json()
            task = (payload or {}).get("task", "").strip()
            if not task:
                return self._json(400, {"error": "task is required"})
            if len(task) > 4000:
                return self._json(400, {"error": "task too long (max 4000 chars)"})
            verdict = zyra.inspect(task, direction="input")
            if not verdict.allowed:
                reason = "; ".join(verdict.reasons) or "blocked by policy"
                return self._json(403, {"error": f"Zyra blocked this request: {reason}"})

            job_id = uuid.uuid4().hex[:12]
            with _agent_jobs_lock:
                _agent_jobs[job_id] = {"status": "running", "task": task, "events": [], "started_at": time.time()}
            thread = threading.Thread(target=_run_agent_job, args=(job_id, task), daemon=True)
            thread.start()
            return self._json(202, {"job_id": job_id})

        if path == "/api/users/signup":
            ip = self.client_address[0]
            if users.rate_limited(ip):
                return self._json(429, {"error": "too many attempts, try again shortly"})
            payload = self._read_json()
            try:
                token = users.signup((payload or {}).get("username", ""), (payload or {}).get("password", ""))
            except ValueError as err:
                return self._json(400, {"error": str(err)})
            return self._respond_with_user_cookie(token)

        if path == "/api/users/login":
            ip = self.client_address[0]
            if users.rate_limited(ip):
                return self._json(429, {"error": "too many attempts, try again shortly"})
            payload = self._read_json()
            try:
                token = users.login((payload or {}).get("username", ""), (payload or {}).get("password", ""))
            except ValueError as err:
                return self._json(401, {"error": str(err)})
            return self._respond_with_user_cookie(token)

        if path == "/api/ideas":
            payload = self._read_json()
            run_id = (payload or {}).get("run_id", "")
            title = (payload or {}).get("title", "").strip()
            if not run_id or not title:
                return self._json(400, {"error": "run_id and title are required"})
            fpath = os.path.join(agent_chain.RUNS_DIR, f"{run_id}.json")
            if not os.path.isfile(fpath):
                return self._json(404, {"error": "run not found"})
            with open(fpath) as f:
                trace = json.load(f)
            owner = self._current_username() or "operator"
            idea = ideas.create(title, trace.get("task", ""), trace.get("transcript", ""), owner=owner, run_id=run_id)
            return self._json(201, idea)

        m = re.match(r"^/api/ideas/([a-f0-9]{12})/status$", path)
        if m:
            payload = self._read_json()
            status = (payload or {}).get("status", "")
            try:
                idea = ideas.set_status(m.group(1), status)
            except ValueError as err:
                return self._json(400, {"error": str(err)})
            if not idea:
                return self._json(404, {"error": "idea not found"})
            return self._json(200, idea)

        m = re.match(r"^/api/projects/([^/]+)/start$", path)
        if m:
            base = safe_project_path(m.group(1))
            if base is None or not os.path.isdir(base):
                return self._json(404, {"error": "project not found"})
            return self._json(200, runner.start(m.group(1), base))

        m = re.match(r"^/api/projects/([^/]+)/stop$", path)
        if m:
            base = safe_project_path(m.group(1))
            if base is None or not os.path.isdir(base):
                return self._json(404, {"error": "project not found"})
            return self._json(200, runner.stop(m.group(1)))

        self._json(404, {"error": "not found"})

    # ---------- twilio ----------

    def _handle_twilio_sms(self):
        if not TWILIO_AUTH_TOKEN or not TWILIO_PUBLIC_URL:
            return self._json(404, {"error": "twilio webhook not configured"})

        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length) if length else b""
        params = twilio_webhook.parse_form(raw)

        signature = self.headers.get("X-Twilio-Signature", "")
        url = TWILIO_PUBLIC_URL + "/twilio/sms"
        if not twilio_webhook.validate_signature(TWILIO_AUTH_TOKEN, url, params, signature):
            return self._json(403, {"error": "invalid twilio signature"})

        body = params.get("Body", "").strip()
        sender = params.get("From", "")
        verdict = zyra.inspect(body, direction="input")
        if not verdict.allowed:
            reply = "Message blocked by policy."
        else:
            reply = self._sms_reply(verdict.text or body)
        zyra.inspect(reply, direction="output")

        xml = twilio_webhook.twiml_message(reply) if reply else twilio_webhook.twiml_empty()
        self.send_response(200)
        self.send_header("Content-Type", "text/xml; charset=utf-8")
        self.send_header("Content-Length", str(len(xml)))
        self.end_headers()
        self.wfile.write(xml)

    def _sms_reply(self, text):
        """Non-streaming call, trimmed to a single SMS-friendly reply."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT + "\n\nYou are replying over SMS: keep it under 300 characters, plain text, no code blocks or filename markers."},
            {"role": "user", "content": text},
        ]
        try:
            result = llm_backend.chat_once(messages, MODEL, DEFAULT_OLLAMA_OPTIONS)
        except urllib.error.URLError:
            return "Doug is offline right now — try again shortly."
        return result.get("message", {}).get("content", "").strip()[:1500]

    # ---------- payments ----------

    def _handle_create_paid_task(self):
        if not stripe_checkout.enabled():
            return self._json(404, {"error": "payments not configured"})
        if not PUBLIC_URL:
            return self._json(500, {"error": "PUBLIC_URL not configured — can't build Stripe redirect URLs"})

        payload = self._read_json()
        task_description = (payload or {}).get("task", "").strip()
        if not task_description:
            return self._json(400, {"error": "task is required"})
        if len(task_description) > 2000:
            return self._json(400, {"error": "task too long (max 2000 chars)"})

        record = paid_tasks.create(task_description)
        success_url = f"{PUBLIC_URL}/paid-task.html?id={record['id']}"
        cancel_url = f"{PUBLIC_URL}/buy?cancelled=1"
        try:
            session = stripe_checkout.create_checkout_session(record["id"], task_description, success_url, cancel_url)
        except RuntimeError as err:
            return self._json(502, {"error": str(err)})

        paid_tasks.set_session_id(record["id"], session["id"])
        return self._json(201, {"task_id": record["id"], "checkout_url": session["url"]})

    def _handle_stripe_webhook(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > MAX_BODY_BYTES:
            raise ValueError("request body too large")
        raw = self.rfile.read(length) if length else b""

        sig_header = self.headers.get("Stripe-Signature", "")
        try:
            event = stripe_checkout.verify_webhook_signature(raw, sig_header)
        except ValueError as err:
            return self._json(400, {"error": f"webhook verification failed: {err}"})

        if event.get("type") == "checkout.session.completed":
            session = event["data"]["object"]
            task_id = (session.get("metadata") or {}).get("task_id")
            if task_id:
                record = paid_tasks.mark_paid(task_id)
                if record and record["status"] == "paid":
                    thread = threading.Thread(target=_run_paid_task, args=(task_id,), daemon=True)
                    thread.start()

        return self._json(200, {"received": True})

    # ---------- chat ----------

    def _handle_chat(self, stream):
        payload = self._read_json()
        if payload is None:
            return self._json(400, {"error": "invalid json"})
        messages = payload.get("messages", [])
        model = payload.get("model", MODEL)

        last_user = next((m.get("content", "") for m in reversed(messages) if m.get("role") == "user"), "")
        verdict = zyra.inspect(last_user, direction="input")
        if not verdict.allowed:
            reason = "; ".join(verdict.reasons) or "blocked by policy"
            return self._blocked_chat_response(stream, f"Zyra blocked this request: {reason}")

        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + list(messages)

        options = {**DEFAULT_OLLAMA_OPTIONS, **payload.get("options", {})}

        if not stream:
            try:
                result = llm_backend.chat_once(messages, model, options)
            except urllib.error.URLError as err:
                return self._json(502, {"error": f"Unable to reach the model backend: {err}"})
            body = json.dumps(result).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no")
        self.end_headers()

        full_reply = []
        try:
            for event in llm_backend.chat_stream(messages, model, options):
                token = event.get("message", {}).get("content", "")
                if token:
                    full_reply.append(token)
                self._sse_send(event)
                if event.get("done"):
                    break
        except (BrokenPipeError, ConnectionResetError):
            pass
        except urllib.error.URLError as err:
            try:
                self._sse_send({"error": f"Unable to reach the model backend: {err}"})
                self._sse_send({"done": True})
            except Exception:
                pass
        except Exception as err:  # noqa: BLE001
            try:
                self._sse_send({"error": str(err)})
            except Exception:
                pass
        finally:
            # Output is streamed live for responsiveness, so this audit pass
            # runs after the fact rather than gating delivery — it still logs
            # secrets/policy hits in what the model produced. The backend
            # generator owns and closes its own upstream connection.
            zyra.inspect("".join(full_reply), direction="output")

    def _blocked_chat_response(self, stream, message):
        if not stream:
            return self._json(403, {"error": message})
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self._sse_send({"message": {"role": "assistant", "content": message}, "done": False})
        self._sse_send({"done": True})

    def _sse_send(self, obj):
        data = f"data: {json.dumps(obj)}\n\n".encode()
        self.wfile.write(data)
        self.wfile.flush()


def _shutdown(*_args):
    runner.stop_all()
    sys.exit(0)


if __name__ == "__main__":
    atexit.register(runner.stop_all)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)
    server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"GPT Doug running at http://localhost:{PORT}")
    print(auth.startup_message())
    worker.start()
    print("Autonomous marketplace worker started (polls every 15s for unclaimed draft ideas).")
    try:
        server.serve_forever()
    finally:
        runner.stop_all()
