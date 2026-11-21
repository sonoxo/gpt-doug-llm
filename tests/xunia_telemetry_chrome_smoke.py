#!/usr/bin/env python3
"""Real Chromium CL1 linear/kinetic/ontology telemetry smoke tests."""
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
      const kinetic=$("kineticCanvas"),linear=$("linearCanvas"),ontology=$("ontologyCanvas");
      check($("objectCount").textContent==="16","scientific ontology not loaded");
      check($("ontologyList").querySelectorAll("button").length===16,"ontology list incomplete");
      check(kinetic.dataset.nodes==="216","model node grid missing");
      check(kinetic.dataset.edges==="402","transport edges missing");
      check(ontology.dataset.nodes==="16"&&ontology.dataset.links==="17","typed links not drawn");
      check(Number(linear.dataset.samples)>=5,"initial linear history missing");
      check(linear.dataset.metric==="flux","initial flux trace not selected");
      check($("metricSelect").options.length===7,"typed metric schema incomplete");
      check($("globalState").textContent.startsWith("SIMULATION"),"false live telemetric label");
      if(window.matchMedia("(prefers-reduced-motion: reduce)").matches){
        check($("playPause").textContent.includes("RESUME"),"motion accessibility violated");
      }
      if($("playPause").textContent.includes("PAUSE"))$("playPause").click();
      check($("playPause").textContent.includes("RESUME"),"pause control failed");
      const before=Number(kinetic.dataset.tick);
      $("stepThirty").click();
      check(Number(kinetic.dataset.tick)>=before+30,"manual solver step not applied");
      check(Number($("fluxValue").textContent)>0,"flow telemetry did not populate");
      check(Number($("tubesValue").textContent)>0,"tube count did not adapt");
      check(Number(linear.dataset.samples)>5,"linear trace failed to update");
      $("metricSelect").value="conductance";
      $("metricSelect").dispatchEvent(new Event("change",{bubbles:true}));
      check(linear.dataset.metric==="conductance","metric selector did not change plot");
      check($("metricUnit").textContent==="dimensionless","metric unit not sourced");
      $("commandInput").value="/wall 8 6";$("commandForm").requestSubmit();
      check($("commandStatus").textContent.includes("GRAPH CHANGED"),"kinetic barrier edit failed");
      $("commandInput").value="/food 9 4";$("commandForm").requestSubmit();
      check($("commandStatus").textContent.includes("GRAPH CHANGED"),"nutrient edit failed");
      $("commandInput").value="/step 15";$("commandForm").requestSubmit();
      check(Number(kinetic.dataset.tick)>=before+45,"step command did not drive simulator");
      document.querySelector('button[data-focus-mode="ontology"]').click();
      check(document.querySelector('button[data-focus-mode="ontology"]').getAttribute("aria-pressed")==="true","ontology focus control failed");
      const trail=document.querySelector('button[data-object="trail"]');check(!!trail,"source trail node unavailable");
      trail.click();
      check(ontology.dataset.selected==="trail","source ontology selection not synced");
      check($("selectedEvidence").textContent==="OBSERVED BIOLOGY","source evidence distinction lost");
      check($("selectedSource").href.startsWith("https://"),"selected scientific reference invalid");
      $("commandInput").value="/metric delta";$("commandForm").requestSubmit();
      check(linear.dataset.metric==="delta","derived flux time series not available");
      $("commandInput").value="/health";$("commandForm").requestSubmit();
      check($("commandStatus").textContent.includes("PASSED"),"telemetry self-test failed: "+$("actionStatus").textContent);
      const T=window.CL1TelemetryEngine,M=window.PhysarumModel;
      check(!!T&&!!M,"shared model/telemetry engine missing");
      const test=M.create(),trace=[];T.capture(test,trace);M.step(test,12);T.capture(test,trace);
      check(T.exportCSV(trace).includes("step,flux,tubes"),"numeric CSV export broken");
      const json=JSON.parse(T.exportJSON(trace,{metrics:[]},test));
      check(json.evidence==="SIMULATED_NOT_MEASURED","source provenance not in export");
      check(T.vectors(test).some(v=>v.magnitude>0),"kinetic particle vectors unavailable");
      const png=kinetic.toDataURL("image/png");
      check(png.startsWith("data:image/png;base64,")&&png.length>1900,"kinetic PNG rendering unavailable");
      document.documentElement.dataset.telemetrySmoke="pass";
    }catch(err){
      document.documentElement.dataset.telemetrySmoke="fail";
      document.documentElement.dataset.telemetryError=String(err.message).slice(0,240);
    }
  },1500);
});
"""


class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        return


def run_browser(chrome: str, reduced: bool, url: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="cl1-telemetry-profile-") as profile:
        args = [
            chrome, "--headless", "--no-sandbox", "--disable-extensions",
            "--disable-background-networking", "--disable-default-apps",
            "--disable-sync", "--no-first-run", "--disable-dev-shm-usage",
            "--window-size=1680,1120", "--virtual-time-budget=6200",
            f"--user-data-dir={profile}", "--dump-dom",
        ]
        if reduced:
            args.append("--force-prefers-reduced-motion=reduce")
        args.append(url)
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=78,
            env={**os.environ, "NO_PROXY": "127.0.0.1,localhost",
                 "no_proxy": "127.0.0.1,localhost"},
        )
        if result.returncode or 'data-telemetry-smoke="pass"' not in result.stdout:
            tag = re.search(r"<html\b[^>]*>", result.stdout)
            print(
                "CL1 TELEMETRY Chromium FAIL",
                tag.group(0) if tag else result.stdout[-450:],
                result.stderr[-600:],
                file=sys.stderr,
            )
            return False
    print(
        "CL1 TELEMETRY Chromium OK:",
        "reduced-motion" if reduced else "normal-motion",
        "216 transport nodes, seven metrics, three synchronized canvases,"
        " 16 source ontology objects, barrier edits and deterministic trace",
    )
    return True


def main() -> int:
    chrome = next(
        (path for name in (
            "chromium", "google-chrome", "chromium-browser",
            "google-chrome-stable",
        ) if (path := shutil.which(name))), None,
    )
    if not chrome:
        print("CL1 TELEMETRY: Chrome missing", file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-telemetry-smoke-") as temp:
        root = Path(temp)
        shutil.copytree(DOCS / "telemetry", root / "telemetry")
        physarum = root / "physarum"
        physarum.mkdir(parents=True)
        for name in ("model.js", "ontology.json"):
            shutil.copy2(DOCS / "physarum" / name, physarum / name)
        page = root / "telemetry" / "index.html"
        html = page.read_text(encoding="utf-8")
        anchor = '<script defer src="./atlas.js"></script>'
        if anchor not in html:
            raise ValueError("Telemetry boot script not found")
        page.write_text(
            html.replace(anchor, anchor + '<script defer src="./probe.js"></script>'),
            encoding="utf-8",
        )
        (root / "telemetry" / "probe.js").write_text(PROBE, encoding="utf-8")
        server = ThreadingHTTPServer(
            ("127.0.0.1", 0), partial(Handler, directory=str(root))
        )
        server.daemon_threads = True
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/telemetry/"
            return 0 if run_browser(chrome, False, url) and run_browser(
                chrome, True, url
            ) else 1
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)


if __name__ == "__main__":
    raise SystemExit(main())
