#!/usr/bin/env python3
"""Real Chromium smoke for XUNIA HQ's living CL1 spatial core."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"

PROBE = r"""
window.addEventListener("load", () => {
  setTimeout(() => {
    try {
      const $ = id => document.getElementById(id);
      const test = (check, text) => { if (!check) throw Error(text); };
      const canvas = $("cl1-live-canvas");
      test(canvas?.dataset.renderedNodes === "8", "eight portal nodes not rendered");
      test($("cl1-live-enter").getAttribute("href") === "./cosmos/", "wrong default portal");
      test(document.querySelectorAll("[data-cl1-portal]").length === 8, "portal buttons missing");
      test($("cl1-live-audio").getAttribute("aria-pressed") === "false", "sound auto-started");
      const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
      test(($("cl1-live-pause").getAttribute("aria-pressed") === "true") === reduced,
        "reduced motion not honored by initial scene");
      document.querySelector('[data-cl1-portal="xenology"]').click();
      test(canvas.dataset.selectedPortal === "xenology", "portal select did not update canvas");
      test($("cl1-live-enter").getAttribute("href") === "./cosmos/xenology/",
        "selected portal points to wrong destination");
      $("cl1-live-pause").click();
      test(canvas.dataset.renderedNodes === "8", "pause destroyed scene");
      document.querySelector('[data-cl1-mode="shaggoth"]').click();
      test(canvas.dataset.mode === "shaggoth", "Shaggoth simulation mode failed");
      $("cl1-live-energy").value = "85";
      $("cl1-live-energy").dispatchEvent(new Event("input", {bubbles:true}));
      test($("cl1-live-energy-value").textContent === "85%", "virtual energy slider failed");
      const capture = canvas.toDataURL("image/png");
      test(capture.startsWith("data:image/png;base64,") && capture.length > 1800,
        "scene canvas cannot generate an actual PNG");
      const before = Number(canvas.dataset.renderedFrames);
      $("cl1-live-zoom-in").click();
      test(Number(canvas.dataset.renderedFrames) > before, "zoom did not redraw scene");
      canvas.dispatchEvent(new KeyboardEvent("keydown", {
        key:"ArrowRight", bubbles:true, cancelable:true
      }));
      test(canvas.dataset.selectedPortal === "planets", "keyboard portal selection failed");
      document.querySelector('[data-cl1-mode="signal"]').click();
      test(canvas.dataset.mode === "signal", "signal mode failed");
      $("cl1-live-recenter").click();
      test($("cl1-live-message").textContent.length > 0, "no system status");
      document.documentElement.dataset.liveCoreSmoke = "pass";
    } catch (error) {
      document.documentElement.dataset.liveCoreSmoke = "fail";
      document.documentElement.dataset.liveCoreError = String(error.message).slice(0, 200);
    }
  }, 1100);
});
"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        return


def run_chrome(chrome: str, root: Path, reduced: bool, url: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="cl1-core-chrome-") as profile:
        cmd = [
            chrome, "--headless", "--no-sandbox", "--disable-extensions",
            "--disable-background-networking", "--disable-default-apps",
            "--disable-sync", "--no-first-run", "--disable-dev-shm-usage",
            "--window-size=1640,1000", "--virtual-time-budget=4700",
            f"--user-data-dir={profile}", "--dump-dom",
        ]
        if reduced:
            cmd.append("--force-prefers-reduced-motion=reduce")
        cmd.append(url)
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60,
            env={**os.environ, "NO_PROXY":"127.0.0.1,localhost",
                 "no_proxy":"127.0.0.1,localhost"},
        )
        if proc.returncode:
            print("HQ LIVE CORE: Chromium exited", proc.returncode,
                  proc.stderr[-700:], file=sys.stderr)
            return False
        if 'data-live-core-smoke="pass"' not in proc.stdout:
            found = re.search(r"<html\b[^>]*>", proc.stdout)
            print("HQ LIVE CORE: DOM smoke failed", found.group(0) if found else "no HTML",
                  "stdout tail:", proc.stdout[-900:],
                  "stderr:", proc.stderr[-250:], file=sys.stderr)
            return False
    print("HQ LIVE CORE CHROME OK:", "reduced-motion" if reduced else "interactive",
          "8 portals / Shaggoth / camera / PNG / keyboard")
    return True


def main() -> int:
    chrome = next(
        (p for name in ("chromium", "google-chrome", "chromium-browser", "google-chrome-stable")
         if (p := shutil.which(name))),
        None,
    )
    if not chrome:
        print("HQ LIVE CORE: Chrome or Chromium missing", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-living-") as temp:
        root = Path(temp)
        for name in (
            "cl1-live.js", "cl1-live.css", "zyra-theme.css",
            "museum.css", "museum.js", "zyra-shell-v2.js",
            "xunia-motion.js", "xunia-motion.css", "favicon.svg",
        ):
            source = DOCS / name
            if source.exists():
                shutil.copy2(source, root / name)
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        anchor = '<script src="./cl1-live.js" defer></script>'
        if anchor not in html:
            print("HQ LIVE CORE: launch script missing", file=sys.stderr)
            return 1
        html = html.replace(anchor, anchor + '\n<script src="./probe.js" defer></script>')
        (root / "index.html").write_text(html, encoding="utf-8")
        (root / "probe.js").write_text(PROBE, encoding="utf-8")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(root))
        )
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/"
            if not run_chrome(chrome, root, False, url):
                return 1
            if not run_chrome(chrome, root, True, url):
                return 1
            return 0
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
