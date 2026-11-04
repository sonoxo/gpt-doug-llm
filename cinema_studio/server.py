"""GPT-DOUG Cinema Studio local HTTP app: zero paid APIs, stdlib-only server.

Browser → validated job → serial FFmpeg/MLX-Gen worker → MP4 + manifest → gallery.
"""
from __future__ import annotations

from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import queue
import re
import secrets
import threading
import webbrowser

try:
    from . import engine
except ImportError:
    import engine  # python cinema_studio/server.py from repo checkout

WEB = Path(__file__).resolve().parent / "web"
ID_RE = re.compile(r"^[a-f0-9]{16}$")
MAX_BODY = 12 * 1024 * 1024
PORT = 8793


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Studio:
    def __init__(self, root: Path | None = None):
        self.root = root or engine.PROJECT_ROOT
        self.root.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.jobs: dict[str, dict] = {}
        self.queue: queue.Queue = queue.Queue(maxsize=12)
        self._load_previous()
        self.worker = threading.Thread(target=self._run, name="gpt-doug-cinema-worker", daemon=True)
        self.worker.start()

    def _load_previous(self):
        for folder in self.root.iterdir():
            if not folder.is_dir() or not ID_RE.fullmatch(folder.name) or folder.is_symlink():
                continue
            f = folder / "job.json"
            if not f.is_file() or f.is_symlink():
                continue
            try:
                item = json.loads(f.read_text(encoding="utf-8"))
                if item["id"] != folder.name or item["status"] not in {"queued", "running", "failed", "completed", "cancelled"}:
                    continue
                if item["status"] in ("running", "queued"):
                    item["status"] = "failed"
                    item["stage"] = "Interrupted by app shutdown; submit a new job to retry"
                self.jobs[folder.name] = item
            except (ValueError, KeyError, OSError, TypeError):
                continue

    def _persist(self, job: dict):
        folder = self.root / job["id"]
        folder.mkdir(parents=True, exist_ok=True)
        tmp = folder / "job.json.partial"
        tmp.write_text(json.dumps(job, indent=2) + "\n", encoding="utf-8")
        tmp.replace(folder / "job.json")

    def submit(self, payload: dict) -> dict:
        request = engine.normalize_request(payload)
        with self.lock:
            if self.queue.full():
                raise engine.StudioError("Queue full (12 pending jobs). Retry after a job finishes")
            name = secrets.token_hex(8)
            item = {"id": name, "status": "queued", "stage": "Waiting for local renderer",
                    "created": now(), "updated": now(), "mode": request["mode"],
                    "prompt": request["prompt"], "shots": len(request["shots"]), "error": None,
                    "video": None, "manifest": None}
            self.jobs[name] = item
            self._persist(item)
            self.queue.put_nowait((name, request))
            return dict(item)

    def update(self, job_id: str, **updates) -> None:
        with self.lock:
            current = self.jobs[job_id]
            current.update(updates, updated=now())
            self._persist(current)

    def _run(self):
        while True:
            job_id, request = self.queue.get()
            try:
                with self.lock:
                    if self.jobs[job_id]["status"] == "cancelled":
                        continue
                self.update(job_id, status="running", stage="Starting local renderer")
                folder = self.root / job_id
                report = engine.render(folder, request, callback=lambda stage:self.update(job_id, stage=stage))
                self.update(job_id, status="completed", stage="MP4 ready", video=f"/api/assets/{job_id}/final.mp4",
                            manifest=f"/api/assets/{job_id}/manifest.json", elapsed_seconds=report["elapsed_seconds"])
            except Exception as err:
                # Do not leak OS file paths or private prompts as traceback.
                message = str(err)
                message = message.replace(str(Path.home()), "~")
                self.update(job_id, status="failed", stage="Generation failed", error=message[-1700:])
            finally:
                self.queue.task_done()

    def get(self, job_id: str) -> dict | None:
        with self.lock:
            result = self.jobs.get(job_id)
            return dict(result) if result else None

    def list(self) -> list[dict]:
        with self.lock:
            return [dict(item) for item in sorted(self.jobs.values(), key=lambda i: i["created"], reverse=True)[:70]]

    def cancel(self, job_id: str) -> dict:
        with self.lock:
            item = self.jobs.get(job_id)
            if not item:
                raise engine.StudioError("Job does not exist")
            if item["status"] != "queued":
                raise engine.StudioError("Only queued jobs can be cancelled; close the app to interrupt running generation")
            self.update(job_id, status="cancelled", stage="Removed from queue")
            return dict(item)


class Handler(BaseHTTPRequestHandler):
    studio: Studio
    server_version = "GPTDOUGCinema/1.0"

    def _send(self, code: int, content: bytes, mime: str, disposition: str | None = None):
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        if mime.startswith("text/html"):
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; media-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'none'")
        if disposition:
            self.send_header("Content-Disposition", disposition)
        self.end_headers()
        try:
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, code: int, data: dict):
        self._send(code, json.dumps(data, separators=(",", ":")).encode("utf-8"), "application/json")

    def _allowed(self, require_origin=False) -> bool:
        port = self.server.server_port
        host = self.headers.get("Host", "")
        hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        origin = self.headers.get("Origin", "")
        return host in hosts and (origin in {f"http://{h}" for h in hosts} if require_origin else
                                  not origin or origin in {f"http://{h}" for h in hosts})

    def do_GET(self):
        if not self._allowed():
            return self._json(403, {"error": "Only local browser requests are accepted"})
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            return self._json(200, {"ok": True, "app": "GPT-DOUG Cinema Studio", "local": True,
                                    "renderer": engine.status(), "jobs": len(self.studio.jobs)})
        if path == "/api/jobs":
            return self._json(200, {"jobs": self.studio.list()})
        if path.startswith("/api/jobs/"):
            name = path.removeprefix("/api/jobs/")
            if not ID_RE.fullmatch(name):
                return self._json(404, {"error": "Unknown job"})
            job = self.studio.get(name)
            return self._json(200, {"job": job}) if job else self._json(404, {"error": "Unknown job"})
        match = re.fullmatch(r"/api/assets/([a-f0-9]{16})/(final\.mp4|manifest\.json)", path)
        if match:
            jid, filename = match.groups()
            job = self.studio.get(jid)
            if not job or job["status"] != "completed":
                return self._json(404, {"error": "Output not ready"})
            file = self.studio.root / jid / filename
            if not file.is_file() or file.is_symlink() or file.stat().st_size > 512*1024*1024:
                return self._json(404, {"error": "Output unavailable"})
            mime = "video/mp4" if filename.endswith(".mp4") else "application/json"
            disposition = f'attachment; filename="gpt-doug-{jid}.{filename.split(".")[-1]}"' if filename.endswith(".json") else None
            return self._send(200, file.read_bytes(), mime, disposition)
        files = {"/":("index.html", "text/html; charset=utf-8"),
                 "/app.js":("app.js", "text/javascript; charset=utf-8"),
                 "/style.css":("style.css", "text/css; charset=utf-8")}
        if path in files:
            name, mime = files[path]
            return self._send(200, (WEB / name).read_bytes(), mime)
        return self._json(404, {"error": "Unknown route"})

    def do_POST(self):
        if not self._allowed(require_origin=True):
            return self._json(403, {"error": "Cross-origin requests are not accepted"})
        path = self.path.split("?", 1)[0]
        if path not in ("/api/jobs", "/api/cancel"):
            return self._json(404, {"error": "Unknown API route"})
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 2 <= length <= MAX_BODY:
                raise engine.StudioError("Request must be under 12 MB")
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
            if path == "/api/jobs":
                item = self.studio.submit(payload)
                return self._json(202, {"job": item})
            if not isinstance(payload, dict) or not ID_RE.fullmatch(str(payload.get("id", ""))):
                raise engine.StudioError("Missing job identifier")
            item = self.studio.cancel(payload["id"])
            return self._json(200, {"job": item})
        except (ValueError, UnicodeError, json.JSONDecodeError, engine.StudioError) as exc:
            return self._json(400, {"error": str(exc)[:250]})


def serve(host: str = "127.0.0.1", port: int = PORT, browser: bool = True, root: Path | None = None):
    if host != "127.0.0.1":
        raise ValueError("Cinema Studio may only listen on 127.0.0.1")
    if not 1024 <= port <= 65535:
        raise ValueError("Invalid TCP port")
    studio = Studio(root)
    handler = type("LocalCinemaHandler", (Handler,), {"studio": studio})
    httpd = ThreadingHTTPServer((host, port), handler)
    httpd.daemon_threads = True
    url = f"http://127.0.0.1:{port}/"
    print("GPT-DOUG CINEMA STUDIO // LOCAL", url, flush=True)
    print("Free FFmpeg motion/image editor is available if ffmpeg is installed.", flush=True)
    if browser:
        webbrowser.open(url)
    try:
        httpd.serve_forever(poll_interval=.2)
    except KeyboardInterrupt:
        print("\nStudio stopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Free local GPT-DOUG video production studio")
    parser.add_argument("--port", type=int, default=PORT)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    serve(port=args.port, browser=not args.no_browser)
