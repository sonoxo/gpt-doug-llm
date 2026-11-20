#!/usr/bin/env python3
"""Headless Chromium verifies actual CL1 molecule controls, canvas and source labels."""
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

DOCS = Path(__file__).resolve().parents[1] / "docs"
PROBE = r"""
window.addEventListener("load", () => {
  setTimeout(() => {
    try {
      const $ = id => document.getElementById(id);
      const check = (condition, message) => {if (!condition) throw Error(message)};
      const canvas = $("moleculeCanvas"),graph = $("bondGraph");
      check($("totalMolecules").textContent === "33", "curated molecule catalog not loaded");
      check($("totalElements").textContent === "8", "element representation mismatch");
      check($("moleculeName").textContent === "Water", "default Water molecule not selected");
      check($("moleculeFormula").textContent === "H2O", "formula mismatch");
      check(canvas.dataset.renderedAtoms === "3", "ball and stick atoms not rendered");
      check(graph.dataset.atoms === "3", "bond topology diagram not rendered");
      check($("importState").textContent.includes("NOT RUN"), "optional PubChem placeholder not recognized");
      document.querySelector('[data-mode="space"]').click();
      check(canvas.dataset.mode === "space", "space fill rendering mode failed");
      const initial = Number(canvas.dataset.frames);
      $("zoomIn").click();
      check(Number(canvas.dataset.frames) > initial, "zoom not interactive");
      $("consoleInput").value = "/select Benzene";
      $("consoleForm").requestSubmit();
      check($("moleculeName").textContent === "Benzene", "console select failed");
      check($("moleculeFormula").textContent === "C6H6", "aromatic formula wrong");
      check(canvas.dataset.renderedAtoms === "12", "benzene 12 atom instances not drawn");
      $("query").value = "meth";
      $("query").dispatchEvent(new Event("input", {bubbles:true}));
      check(Number($("resultCount").textContent.split("/")[0].trim()) >= 3,
        "molecule search filtering broken");
      $("resetFilter").click();
      check($("resultCount").textContent.startsWith("33"), "filter reset failed");
      document.querySelector('[data-id="glycine"]').click();
      check($("moleculeName").textContent === "Glycine", "click molecule list failed");
      check($("referenceTag").textContent === "CHEM / REFERENCE", "chemistry evidence boundary missing");
      $("consoleInput").value = "/select Water";
      $("consoleForm").requestSubmit();
      const rect=graph.getBoundingClientRect();
      graph.dispatchEvent(new MouseEvent("click", {
        bubbles:true,
        clientX:rect.left+rect.width/2,
        clientY:rect.top+rect.height/2
      }));
      check($("selectedAtomTag").textContent.includes("O"), "atom graph click failed");
      const png = canvas.toDataURL("image/png");
      check(png.startsWith("data:image/png;base64,") && png.length > 1000,
        "molecule canvas is not a real rendered PNG");
      $("selfTest").click();
      check($("actionStatus").textContent.includes("SELF-TEST PASS"),
        "local molecule self-test failed");
      $("consoleInput").value = "/health";
      $("consoleForm").requestSubmit();
      check($("consoleStatus").textContent.includes("SELF-TEST PASS"),
        "health console command failed");
      document.documentElement.dataset.moleculesSmoke="pass";
    } catch(error) {
      document.documentElement.dataset.moleculesSmoke="fail";
      document.documentElement.dataset.moleculesError=String(error.message).slice(0,180);
    }
  }, 1600);
});
"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        return


def main() -> int:
    chrome = next(
        (path for name in (
            "chromium", "google-chrome", "chromium-browser", "google-chrome-stable"
        ) if (path := shutil.which(name))), None,
    )
    if not chrome:
        print("MOLECULES: Chromium missing", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-molecule-") as temp:
        root = Path(temp)
        dest = root / "molecules"
        shutil.copytree(DOCS / "molecules", dest)
        html_path = dest / "index.html"
        html = html_path.read_text(encoding="utf-8")
        anchor = '<script defer src="./molecules.js"></script>'
        assert anchor in html
        html_path.write_text(
            html.replace(anchor, anchor + '<script defer src="./probe.js"></script>'),
            encoding="utf-8",
        )
        (dest / "probe.js").write_text(PROBE, encoding="utf-8")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(root))
        )
        server.daemon_threads = True
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/molecules/"
            with tempfile.TemporaryDirectory(prefix="cl1-molecules-profile-") as profile:
                process = subprocess.run(
                    [chrome, "--headless", "--no-sandbox", "--disable-extensions",
                     "--disable-background-networking", "--disable-default-apps",
                     "--disable-sync", "--no-first-run", "--disable-dev-shm-usage",
                     "--window-size=1650,1050", "--virtual-time-budget=5900",
                     f"--user-data-dir={profile}", "--dump-dom", url],
                    text=True, capture_output=True, timeout=65,
                    env={**os.environ, "NO_PROXY": "127.0.0.1,localhost",
                         "no_proxy": "127.0.0.1,localhost"},
                )
            if process.returncode:
                print("MOLECULES: Chrome exit", process.returncode,
                      process.stderr[-600:], file=sys.stderr)
                return 1
            if 'data-molecules-smoke="pass"' not in process.stdout:
                element = re.search(r"<html\b[^>]*>", process.stdout)
                print(
                    "MOLECULES: DOM interaction failure",
                    element.group(0) if element else process.stdout[-400:],
                    process.stderr[-450:],
                    file=sys.stderr,
                )
                return 1
            print("CL1 MOLECULES CHROME OK: 33 compounds, atom/bond viewer, chemistry source status, 3D modes, search, PNG, graph selection, health")
            return 0
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
