#!/usr/bin/env python3
"""Real Chromium interaction test for source-qualified CL1 Fusion."""
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
window.addEventListener("load",()=>{
  setTimeout(()=>{
    try{
      const $=id=>document.getElementById(id);
      const check=(ok,message)=>{if(!ok)throw Error(message)};
      check($("nodeTotal").textContent==="29","combined graph has wrong object count");
      check($("edgeTotal").textContent==="43","typed graph has wrong link count");
      check($("nasaTotal").textContent==="8","NASA catalog missing");
      check($("atlas").dataset.nodes==="29","main Canvas failed initial rendering");
      check($("entityName").textContent==="Earth","source Earth default not selected");
      check($("entityTrust").textContent==="REFERENCE","NASA source not reference-labeled");
      document.querySelector('[data-view="orbits"]').click();
      check($("atlas").dataset.view==="orbits"&&$("atlas").dataset.nodes==="8",
        "sourced orbital view did not show eight planets");
      $("epoch").value="2030-01-01";
      $("epoch").dispatchEvent(new Event("change",{bubbles:true}));
      check($("epoch").value==="2030-01-01","JPL date control failed");
      document.querySelector('[data-view="architecture"]').click();
      check($("atlas").dataset.view==="architecture"&&$("atlas").dataset.nodes==="14",
        "AWS-style + ontology graph not rendered");
      document.querySelector('[data-view="operations"]').click();
      check($("atlas").dataset.view==="operations"&&$("atlas").dataset.nodes==="14",
        "synthetic operations graph not rendered");
      document.querySelector('[data-view="fusion"]').click();
      check($("atlas").dataset.nodes==="29","fusion restoration failed");
      $("command").value="/select cloud-index";$("commandForm").requestSubmit();
      check($("entityName").textContent==="Ontology Index","semantic inspector select failed");
      check($("entityTrust").textContent==="PROPOSED","cloud truth label failed");
      $("trace").click();
      check($("actionStatus").textContent.includes("LINEAGE"),"typed lineage traversal failed");
      $("search").value="Earth";$("search").dispatchEvent(new Event("input",{bubbles:true}));
      check($("atlas").dataset.nodes==="1","cross-layer search failed");
      $("resetFilters").click();
      check($("atlas").dataset.nodes==="29","filters did not reset");
      const img=$("atlas").toDataURL("image/png");
      check(img.startsWith("data:image/png;base64,")&&img.length>1500,
        "real Canvas PNG serialization failed");
      $("selfTest").click();
      check($("actionStatus").textContent.includes("SELF-TEST PASS"),
        "application self-test failed");
      $("command").value="/select ops-track-a";$("commandForm").requestSubmit();
      check($("entityTrust").textContent==="SYNTHETIC",
        "synthetic example was not separated from NASA source");
      const cmd=$("command");cmd.value="/health";$("commandForm").requestSubmit();
      check($("actionStatus").textContent.includes("SELF-TEST PASS"),"console health command failed");
      document.documentElement.dataset.fusionSmoke="pass";
    }catch(e){
      document.documentElement.dataset.fusionSmoke="fail";
      document.documentElement.dataset.fusionSmokeError=String(e.message).slice(0,200);
    }
  },1400);
});
"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        return


def main() -> int:
    chrome = next(
        (path for name in ("chromium", "google-chrome", "chromium-browser",
                           "google-chrome-stable") if (path := shutil.which(name))),
        None,
    )
    if not chrome:
        print("CL1 FUSION: Chrome/Chromium not available", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-fusion-") as temp:
        root = Path(temp)
        shutil.copytree(DOCS / "fusion", root / "fusion")
        planet_dir = root / "cosmos" / "planets"
        planet_dir.mkdir(parents=True)
        shutil.copy2(
            DOCS / "cosmos" / "planets" / "catalog.json",
            planet_dir / "catalog.json",
        )
        page = root / "fusion" / "index.html"
        html = page.read_text(encoding="utf-8")
        anchor = '<script src="./fusion.js" defer></script>'
        assert anchor in html
        page.write_text(
            html.replace(anchor, anchor + '<script src="./probe.js" defer></script>'),
            encoding="utf-8",
        )
        (root / "fusion" / "probe.js").write_text(PROBE, encoding="utf-8")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(root))
        )
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/fusion/"
            with tempfile.TemporaryDirectory(prefix="cl1-fusion-profile-") as profile:
                proc = subprocess.run(
                    [chrome, "--headless", "--no-sandbox", "--disable-extensions",
                     "--disable-background-networking", "--disable-default-apps",
                     "--disable-sync", "--no-first-run", "--disable-dev-shm-usage",
                     "--window-size=1600,1100", "--virtual-time-budget=5800",
                     f"--user-data-dir={profile}", "--dump-dom", url],
                    capture_output=True, text=True, timeout=60,
                    env={**os.environ, "NO_PROXY": "127.0.0.1,localhost",
                         "no_proxy": "127.0.0.1,localhost"},
                )
            if proc.returncode:
                print("CL1 FUSION: Browser exited", proc.returncode,
                      proc.stderr[-600:], file=sys.stderr)
                return 1
            if 'data-fusion-smoke="pass"' not in proc.stdout:
                html_tag = re.search(r"<html\b[^>]*>", proc.stdout)
                print("CL1 FUSION: UI test failed",
                      html_tag.group(0) if html_tag else proc.stdout[-500:],
                      proc.stderr[-600:], file=sys.stderr)
                return 1
            print("CL1 FUSION CHROME OK: 29 ontology objects / 43 links / four views / NASA data / provenance / PNG / commands")
            return 0
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
