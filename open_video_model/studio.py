"""Minimal localhost-only GPT-DOUG Motion-1 Studio: generate real GIFs from trained weights.

No cloud, account, public listener, paid inference API or JS framework.
Run: python -m open_video_model studio
"""
from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import BoundedSemaphore
import json
from pathlib import Path
import re
import secrets
import webbrowser

DEFAULT_CHECKPOINT = Path.home() / ".local/share/gpt-doug/motion-1/motion1.pt"
STATUS_FILE = DEFAULT_CHECKPOINT.parent / "setup-status"
TRAIN_LOG = DEFAULT_CHECKPOINT.parent / "training.log"
RENDER_LOCK = BoundedSemaphore(1)


def pipeline_status() -> dict:
    """Return stage and numbers only; never expose local logs or filesystem paths."""
    ready = DEFAULT_CHECKPOINT.is_file()
    stage = "ready" if ready else "not-started"
    if not ready:
        try:
            candidate = STATUS_FILE.read_text(encoding="utf-8").strip()
            if candidate in ("installing", "training", "failed", "not-started"):
                stage = candidate
        except OSError:
            pass
    steps = total = None
    if stage in ("training", "ready", "failed"):
        try:
            with TRAIN_LOG.open("rb") as source:
                end = source.seek(0, 2)
                source.seek(max(0, end - 8192))
                last_lines = source.read().decode("utf-8", "replace")
            matches = re.findall(r"Motion-1\s*\|\s*(\d+)/(\d+)\s*\|\s*loss=", last_lines)
            if matches:
                steps, total = map(int, matches[-1])
        except OSError:
            pass
    return {"stage": stage, "completed_steps": steps, "total_steps": total}



SITE_DIR = Path(__file__).resolve().parents[1] / "docs" / "motion-1"
OUTPUT_DIR = Path.home() / ".local/share/gpt-doug/motion-1/renders"
RENDER_NAME = re.compile(r"^motion1-[0-9a-f]{16}\.gif$")
MIME = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}


class MotionHandler(BaseHTTPRequestHandler):
    def respond(self, code: int, body: bytes, mime: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def json_response(self, code: int, data: dict) -> None:
        self.respond(code, json.dumps(data, separators=(",", ":")).encode("utf-8"), "application/json")

    def origin_ok(self) -> bool:
        origin = self.headers.get("Origin", "")
        host = self.headers.get("Host", "")
        port = self.server.server_port
        valid_hosts = {f"127.0.0.1:{port}", f"localhost:{port}"}
        return host in valid_hosts and (not origin or origin in {f"http://{h}" for h in valid_hosts})

    def do_GET(self) -> None:
        if not self.origin_ok():
            self.json_response(403, {"error": "Only local studio origins are allowed"})
            return
        path = self.path.split("?", 1)[0]
        if path == "/api/health":
            self.json_response(200, {
                "ok": True, "local": True, "name": "GPT-DOUG Motion-1",
                "trained_checkpoint_present": DEFAULT_CHECKPOINT.is_file(),
                "generation_requires_training": True,
                "remote_inference": False,
                "pipeline": pipeline_status(),
            })
        elif path in MIME:
            filename, mime = MIME[path]
            file = SITE_DIR / filename
            if not file.is_file():
                self.json_response(404, {"error": "Studio website asset missing"})
                return
            self.respond(200, file.read_bytes(), mime)
        elif path.startswith("/renders/"):
            name = path.removeprefix("/renders/")
            if not RENDER_NAME.fullmatch(name):
                self.json_response(404, {"error": "Render not found"})
                return
            file = OUTPUT_DIR / name
            if not file.is_file() or file.is_symlink() or file.stat().st_size > 15_000_000:
                self.json_response(404, {"error": "Render not found"})
                return
            self.respond(200, file.read_bytes(), "image/gif")
        else:
            self.json_response(404, {"error": "Not found"})

    def do_POST(self) -> None:
        if not self.origin_ok():
            self.json_response(403, {"error": "Only local studio origins are allowed"})
            return
        route = self.path.split("?", 1)[0]
        if route not in ("/api/generate", "/api/preview"):
            self.json_response(404, {"error": "Unknown operation"})
            return
        try:
            length = int(self.headers.get("Content-Length", "-1"))
            if not 1 <= length <= 4096:
                raise ValueError("Request must be JSON under 4 KB")
            request = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(request, dict):
                raise ValueError("JSON object required")
            prompt = request.get("prompt", "")
            seed = request.get("seed", 42)
            fps = request.get("fps", 8)
            if not isinstance(prompt, str) or not 1 <= len(prompt.strip()) <= 400:
                raise ValueError("Prompt must contain 1-400 characters")
            if type(seed) is not int or not 0 <= seed <= 2**31-1:
                raise ValueError("Seed outside supported range")
            if type(fps) is not int or not 1 <= fps <= 30:
                raise ValueError("FPS must be an integer from 1-30")
            if route == "/api/generate" and not DEFAULT_CHECKPOINT.is_file():
                self.json_response(409, {"error": "No trained checkpoint. Run python -m open_video_model train first."})
                return
            OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
            filename = "motion1-" + secrets.token_hex(8) + ".gif"
            if not RENDER_LOCK.acquire(blocking=False):
                self.json_response(429, {"error": "A local render is already running."})
                return
            try:
                from .generate import render
                receipt = render(prompt=prompt, output=OUTPUT_DIR / filename,
                             checkpoint=DEFAULT_CHECKPOINT if route == "/api/generate" else None,
                             seed=seed, fps=fps, preview=route == "/api/preview")
            finally:
                RENDER_LOCK.release()
            self.json_response(200, {"ok": True, "url": "/renders/" + filename,
                                     "preview_not_ml": receipt["preview_not_ml"], "receipt": receipt})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self.json_response(400, {"error": str(exc)[:300]})
        except ImportError:
            self.json_response(503, {"error": "Model dependencies are installing; the browser-only preview works immediately."})
        except (RuntimeError, OSError, FileNotFoundError) as exc:
            # Paths and platform internals need not be shown to a browser.
            print("Local render error:", type(exc).__name__)
            self.json_response(500, {"error": "Local model generation failed. Check the Terminal error and checkpoint."})


def serve(port: int = 8792, open_browser: bool = True) -> None:
    if not 1024 <= port <= 65535:
        raise ValueError("port must be 1024-65535")
    if not (SITE_DIR / "index.html").is_file():
        raise FileNotFoundError("Studio source assets missing in docs/motion-1")
    server = ThreadingHTTPServer(("127.0.0.1", port), MotionHandler)
    server.daemon_threads = True
    link = f"http://127.0.0.1:{port}/"
    print("GPT-DOUG MOTION-1 LOCAL STUDIO // " + link, flush=True)
    print("The browser loads before free dependencies and training finish.", flush=True)
    if open_browser:
        webbrowser.open(link)
    try:
        server.serve_forever(poll_interval=.3)
    except KeyboardInterrupt:
        print("\nStudio stopped.")
    finally:
        server.server_close()
