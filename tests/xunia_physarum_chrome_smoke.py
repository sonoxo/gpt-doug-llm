#!/usr/bin/env python3
"""Real Chromium Physarum Forge smoke test, normal and reduced-motion rendering."""
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
      const check=(ok,msg)=>{if(!ok)throw Error(msg)};
      const canvas=$("physarumCanvas");
      check($("speciesNodes").textContent==="16","sourced species ontology missing");
      check($("facts").children.length===5,"source-backed biological facts absent");
      check($("sourceIndex").children.length>=4,"scientific citations missing");
      check(canvas.dataset.nodes==="216","organism model nodes missing");
      check(canvas.dataset.edges==="402","adaptive network edges missing");
      check($("foodCount").textContent==="2","default nutrient model invalid");
      check(document.querySelectorAll("button[data-brush]").length===4,"editing controls missing");
      check($("exportSvg").textContent.includes("SVG"),"physical design export absent");
      if($("playPause").textContent.includes("PAUSE"))$("playPause").click();
      check($("playPause").textContent.includes("RESUME"),"pause interaction failed");
      $("consoleInput").value="/food 9 4";$("consoleForm").requestSubmit();
      check($("foodCount").textContent==="3","nutrition editing failed");
      $("consoleInput").value="/wall 10 4";$("consoleForm").requestSubmit();
      check($("graphSummary").textContent.includes("1 BARRIERS"),"obstacle model failed");
      $("consoleInput").value="/step 80";$("consoleForm").requestSubmit();
      check(Number($("tickCount").textContent)>=80,"simulation did not advance");
      check(Number($("veinCount").textContent)>0,"conductance did not adapt");
      check(canvas.dataset.ticks!=="0","Canvas not repainted after adaptation");
      $("growth").value="165";$("growth").dispatchEvent(new Event("input",{bubbles:true}));
      check($("growthValue").textContent==="1.65×","reinforcement slider broken");
      $("trailToggle").checked=false;
      $("trailToggle").dispatchEvent(new Event("change",{bubbles:true}));
      $("consoleInput").value="/health";$("consoleForm").requestSubmit();
      check($("consoleStatus").textContent.includes("SELF-TEST PASS"),"health validation failed: "+$("actionStatus").textContent);
      check(typeof window.PhysarumModel==="object","portable model module unavailable");
      const specimen=window.PhysarumModel.create();
      window.PhysarumModel.step(specimen,35);
      check(window.PhysarumModel.svg(specimen).includes('height="120mm"'),"vector model physical scale invalid");
      const png=canvas.toDataURL("image/png");
      check(png.startsWith("data:image/png;base64,")&&png.length>1800,"canvas PNG not rendered");
      check(document.querySelector("#sourceIndex a").href.startsWith("https://"),"research source links missing");
      document.documentElement.dataset.physarumSmoke="pass";
    }catch(error){
      document.documentElement.dataset.physarumSmoke="fail";
      document.documentElement.dataset.physarumError=String(error.message).slice(0,220);
    }
  },1400);
});
"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        return


def browser(chrome: str, reduced: bool, url: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="cl1-physarum-profile-") as profile:
        args = [
            chrome, "--headless", "--no-sandbox", "--disable-extensions",
            "--disable-background-networking", "--disable-default-apps",
            "--disable-sync", "--no-first-run", "--disable-dev-shm-usage",
            "--window-size=1680,1100", "--virtual-time-budget=5600",
            f"--user-data-dir={profile}", "--dump-dom",
        ]
        if reduced:
            args.append("--force-prefers-reduced-motion=reduce")
        args.append(url)
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=70,
            env={**os.environ, "NO_PROXY": "127.0.0.1,localhost",
                 "no_proxy": "127.0.0.1,localhost"},
        )
        if result.returncode or 'data-physarum-smoke="pass"' not in result.stdout:
            tag = re.search(r"<html\b[^>]*>", result.stdout)
            print(
                "CL1 PHYSARUM Chromium FAIL",
                tag.group(0) if tag else result.stdout[-450:],
                result.stderr[-500:],
                file=sys.stderr,
            )
            return False
    print(
        "CL1 PHYSARUM Chromium OK:",
        "reduced-motion" if reduced else "interactive",
        "216 nodes / 402 veins / 3 foods / obstacle / adaptation / vector SVG / health",
    )
    return True


def main() -> int:
    chrome = next(
        (p for name in (
            "chromium", "google-chrome", "chromium-browser",
            "google-chrome-stable",
        ) if (p := shutil.which(name))), None,
    )
    if not chrome:
        print("CL1 PHYSARUM: Chrome missing", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-physarum-smoke-") as temp:
        root = Path(temp)
        site = root / "physarum"
        shutil.copytree(DOCS / "physarum", site)
        html_path = site / "index.html"
        html = html_path.read_text(encoding="utf-8")
        anchor = '<script defer src="./forge.js"></script>'
        assert anchor in html
        html_path.write_text(
            html.replace(
                anchor,
                anchor + '<script defer src="./browser-probe.js"></script>',
            ),
            encoding="utf-8",
        )
        (site / "browser-probe.js").write_text(PROBE, encoding="utf-8")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(root))
        )
        server.daemon_threads = True
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/physarum/"
            return 0 if browser(chrome, False, url) and browser(
                chrome, True, url
            ) else 1
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
