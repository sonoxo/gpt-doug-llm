#!/usr/bin/env python3
"""Real Chromium/Chrome smoke test for the XUNIA Biological Data Center.

No external network, automation services, credentials, or paid dependencies.
Uses existing local server, checks real DOM after JS/CSS/Canvas rendering.
"""
from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "xunia_bio_cl1.py"


def main() -> int:
    chrome = next((path for name in (
        "google-chrome", "chromium", "chromium-browser", "google-chrome-stable"
    ) if (path := shutil.which(name))), None)
    if chrome is None:
        print("XUNIA: real browser smoke test requires Chromium or Google Chrome", file=sys.stderr)
        return 2
    spec = importlib.util.spec_from_file_location("xunia_bio_chrome_server", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import local Bio server")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    server = ThreadingHTTPServer(("127.0.0.1", 0), module.BioHandler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/biological-data-center/"
        with tempfile.TemporaryDirectory(prefix="xunia-bio-smoke-") as tmp:
            command = [
                chrome, "--headless", "--no-sandbox",
                "--disable-extensions", "--disable-background-networking",
                "--disable-default-apps", "--disable-sync",
                "--disable-dev-shm-usage", "--no-first-run",
                "--disable-features=MediaRouter",
                "--window-size=1500,1000",
                "--virtual-time-budget=2300",
                f"--user-data-dir={tmp}", "--dump-dom", url,
            ]
            proc = subprocess.run(command, capture_output=True, text=True,
                                  timeout=35, env={**os.environ, "NO_PROXY":"127.0.0.1,localhost"})
        html = proc.stdout
        if proc.returncode != 0:
            print("XUNIA: browser failed:", proc.stderr[-2500:], file=sys.stderr)
            return 1
        match = re.search(r'<canvas\b[^>]*\bid="world"[^>]*>', html)
        if match is None:
            print("XUNIA: canvas element missing from Chrome-rendered DOM", file=sys.stderr)
            return 1
        canvas = match.group()
        expected = ('data-rendered-nodes="30"', 'data-rendered-edges="43"')
        for marker in expected:
            if marker not in canvas:
                print("XUNIA: Chrome did not render the full ontology:", marker,
                      file=sys.stderr)
                print("XUNIA canvas:", canvas[:1000], file=sys.stderr)
                status = re.search(r'<[^>]+id="telemetryMode"[^>]*>.*?</[^>]+>', html, re.S)
                print("XUNIA status:", status.group(0)[:500] if status else "absent", file=sys.stderr)
                errors = [line for line in proc.stderr.splitlines()
                          if any(key in line for key in ("CONSOLE", "TypeError", "Uncaught", "ERROR"))]
                print("Chrome diagnostics:", "\n".join(errors[-15:])[-2200:], file=sys.stderr)
                return 1
        if 'ORBIT 0° / TILT 0°' in html:
            print("XUNIA: camera telemetry remained unchanged after rendering", file=sys.stderr)
            return 1
        if "SPATIAL RENDER FAILED" in html:
            print("XUNIA: page reported a spatial rendering failure", file=sys.stderr)
            return 1
        print("XUNIA Chrome Canvas: 30 nodes / 43 relationships rendered; camera updated")
        return 0
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
