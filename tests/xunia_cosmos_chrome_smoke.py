#!/usr/bin/env python3
"""Real Chrome smoke test: verify XUNIA COSMOS draws all curated objects.

No network egress: localhost static server, Chrome headless on a private temp profile.
"""
from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class StaticHandler(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


def main() -> int:
    chrome = next((p for name in (
        "google-chrome", "chromium", "chromium-browser", "google-chrome-stable"
    ) if (p := shutil.which(name))), None)
    if chrome is None:
        print("XUNIA COSMOS: headless Chrome/Chromium not found", file=sys.stderr)
        return 2
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), partial(StaticHandler, directory=str(DOCS))
    )
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/cosmos/"
        with tempfile.TemporaryDirectory(prefix="xunia-cosmos-") as profile:
            proc = subprocess.run([
                chrome, "--headless", "--no-sandbox", "--disable-extensions",
                "--disable-background-networking", "--disable-default-apps",
                "--disable-sync", "--no-first-run", "--disable-dev-shm-usage",
                "--window-size=1520,980", "--virtual-time-budget=2500",
                f"--user-data-dir={profile}", "--dump-dom", url,
            ], capture_output=True, text=True, timeout=40,
               env={**os.environ, "NO_PROXY":"127.0.0.1,localhost",
                    "no_proxy":"127.0.0.1,localhost"})
        if proc.returncode:
            print("XUNIA COSMOS: Chrome process failed", proc.stderr[-1400:], file=sys.stderr)
            return 1
        html = proc.stdout
        canvas = re.search(r'<canvas\b[^>]*\bid="space"[^>]*>', html)
        if canvas is None:
            print("XUNIA COSMOS: Canvas missing from browser DOM", file=sys.stderr)
            return 1
        data = canvas.group()
        for marker in ('data-rendered-nodes="55"', 'data-rendered-edges="54"',
                       'data-render-frames="'):
            if marker not in data:
                status = re.search(r'<[^>]+id="canvasNotice"[^>]*>.*?</[^>]+>',html,re.S)
                print("XUNIA COSMOS: map render failure:",marker,file=sys.stderr)
                print("Canvas:",data[:1200],file=sys.stderr)
                print("Notice:",status.group()[:600] if status else "missing",file=sys.stderr)
                return 1
        if "SPATIAL RENDER FAILED" in html:
            print("XUNIA COSMOS: app reported a browser error",file=sys.stderr)
            return 1
        if 'YAW 0° / PITCH 0° / ZOOM 1.00' in html:
            print("XUNIA COSMOS: camera footer did not update",file=sys.stderr)
            return 1
        print("XUNIA COSMOS Chrome OK: 55 drawn nodes / 54 connections / live camera")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
