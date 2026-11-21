#!/usr/bin/env python3
"""Real headless Chromium test: five-sense source-qualified CL1 Synapse simulation."""
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
      const check=(condition,message)=>{if(!condition)throw Error(message)};
      const canvas=$("neuralCanvas");
      check($("sourceCount").textContent==="62","three source catalogs did not load");
      check(canvas.dataset.nodes==="56","neural node count mismatch");
      check(canvas.dataset.links==="112","synthetic edge count mismatch");
      check($("objectName").textContent==="Water","initial object not selected");
      check($("catalogState").textContent.includes("33"),"molecular catalog not listed");
      check($("audioToggle").getAttribute("aria-pressed")==="false","audio autoplays");
      check($("audioStatus").textContent.includes("AUDIO OFF"),"audio initial state mislabeled");
      check(document.querySelectorAll("[data-sense]").length===5,"missing five senses");
      check(document.querySelectorAll("button[data-view]").length===3,"missing views");
      document.querySelector('[data-view="cortex"]').click();
      check(canvas.dataset.view==="cortex","cortex mode failed");
      document.querySelector('[data-view="field"]').click();
      check(canvas.dataset.view==="field","field mode failed");
      $("sourceType").value="planets";
      $("sourceType").dispatchEvent(new Event("change",{bubbles:true}));
      check($("catalogState").textContent.includes("8"),"NASA source domain failed");
      $("commandInput").value="/select Earth";$("commandForm").requestSubmit();
      check($("objectName").textContent==="Earth","command select failed");
      check($("objectDomain").textContent==="PLANETS","NASA provenance omitted");
      const smell=document.querySelector('[data-sense="smell"]');smell.checked=false;
      smell.dispatchEvent(new Event("change",{bubbles:true}));
      check($("smellText").textContent.includes("disabled"),"smell channel routing failed");
      $("resetChannels").click();
      check(smell.checked,"channel restore failed");
      $("intensity").value="75";
      $("intensity").dispatchEvent(new Event("input",{bubbles:true}));
      check($("intensityValue").textContent==="75%","signal intensity control failed");
      const frames=Number(canvas.dataset.frames);$("zoomIn").click();
      check(Number(canvas.dataset.frames)>frames,"camera zoom did not repaint");
      canvas.dispatchEvent(new KeyboardEvent("keydown",{key:"ArrowRight",bubbles:true,cancelable:true}));
      $("pulse").click();
      check($("eventLog").children.length>0,"visual pulse did not log event");
      $("commandInput").value="/domain ontology";$("commandForm").requestSubmit();
      check($("catalogState").textContent.includes("21"),"semantic ontology domain failed");
      $("commandInput").value="/health";$("commandForm").requestSubmit();
      check($("commandStatus").textContent.includes("SELF-TEST PASS"),"built-in self-test failed");
      const png=canvas.toDataURL("image/png");
      check(png.startsWith("data:image/png;base64,")&&png.length>1800,"canvas PNG serialization failed");
      check($("objectSource").href.startsWith("https://"),"source reference unavailable");
      document.documentElement.dataset.synapseSmoke="pass";
    }catch(error){
      document.documentElement.dataset.synapseSmoke="fail";
      document.documentElement.dataset.synapseError=String(error.message).slice(0,250);
    }
  },1400);
});
"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        return


def run_chrome(chrome: str, root: Path, reduced: bool, url: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="xunia-synapse-profile-") as profile:
        args = [
            chrome, "--headless", "--no-sandbox", "--disable-extensions",
            "--disable-background-networking", "--disable-default-apps",
            "--disable-sync", "--no-first-run", "--disable-dev-shm-usage",
            "--window-size=1550,1100", "--virtual-time-budget=5000",
            f"--user-data-dir={profile}", "--dump-dom",
        ]
        if reduced:
            args.append("--force-prefers-reduced-motion=reduce")
        args.append(url)
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=65,
            env={**os.environ, "NO_PROXY": "127.0.0.1,localhost",
                 "no_proxy": "127.0.0.1,localhost"},
        )
        if proc.returncode or 'data-synapse-smoke="pass"' not in proc.stdout:
            tag = re.search(r"<html\b[^>]*>", proc.stdout)
            print("CL1 SYNAPSE Chromium failure",
                  tag.group(0) if tag else proc.stdout[-450:],
                  proc.stderr[-600:], file=sys.stderr)
            return False
    print("CL1 SYNAPSE Chrome OK:", "reduced motion" if reduced else "interactive",
          "62 objects / 56 nodes / 112 links / 5 channels / NASA / ontology / PNG")
    return True


def main() -> int:
    chrome = next(
        (path for name in (
            "chromium", "google-chrome", "chromium-browser", "google-chrome-stable"
        ) if (path := shutil.which(name))), None,
    )
    if not chrome:
        print("CL1 SYNAPSE: Chrome/Chromium missing", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-synapse-") as temp:
        root = Path(temp)
        target = root / "synapse"
        shutil.copytree(DOCS / "synapse", target)
        for source in (
            "molecules/catalogs/seed.json",
            "cosmos/planets/catalog.json",
            "fusion/ontology.json",
        ):
            dest = root / source
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(DOCS / source, dest)
        html_path = target / "index.html"
        html = html_path.read_text(encoding="utf-8")
        anchor = '<script defer src="./synapse.js"></script>'
        if anchor not in html:
            raise ValueError("Missing synapse boot script")
        html_path.write_text(
            html.replace(anchor, anchor + '<script defer src="./probe.js"></script>'),
            encoding="utf-8",
        )
        (target / "probe.js").write_text(PROBE, encoding="utf-8")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(root))
        )
        server.daemon_threads = True
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/synapse/"
            return 0 if (
                run_chrome(chrome, root, False, url)
                and run_chrome(chrome, root, True, url)
            ) else 1
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
