#!/usr/bin/env python3
"""Headless Chromium UI smoke: CL1 xenology actual canvas, cards, filters and console.
No external network or paid service; tests temporary same-origin static catalog.
"""
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

ROOT=Path(__file__).resolve().parents[1]
XENO=ROOT/"docs"/"cosmos"/"xenology"
PROBE=r"""
window.addEventListener("load",()=>{
  setTimeout(()=>{
    try{
      const el=id=>document.getElementById(id);
      const assert=(yes,msg)=>{if(!yes)throw Error(msg)};
      assert(el("recordTotal").textContent==="36","catalog count wrong");
      assert(document.querySelectorAll(".entity-card").length===36,"all cards not rendered");
      assert(el("statShaggoth").textContent==="7","Shaggoth total wrong");
      assert(el("creatureCanvas").dataset.rendered==="true","concept scene not rendered");
      assert(el("graphCanvas").dataset.renderedNodes==="36","graph not rendered");
      document.querySelector('[data-entity-id="s-void-shaggoth"]').click();
      assert(el("selectedName").textContent==="Void Shaggoth","card not interactive");
      document.querySelector('[data-tab="relations"]').click();
      assert(el("tabBody").textContent.includes("editorial")&&el("tabBody").querySelectorAll("button").length>0,"relationships tab failed");
      el("query").value="Shaggoth";el("query").dispatchEvent(new Event("input",{bubbles:true}));
      assert(el("filteredTotal").textContent==="7","text search filters wrong");
      el("resetFilters").click();
      assert(el("filteredTotal").textContent==="36","reset filters failed");
      for(const input of document.querySelectorAll("#groupFilters input"))input.checked=input.value==="uap";
      document.querySelector("#groupFilters input").dispatchEvent(new Event("change",{bubbles:true}));
      assert(el("filteredTotal").textContent==="10","group filter failed");
      el("consoleInput").value="/select GOFAST";el("consoleForm").requestSubmit();
      assert(el("selectedName").textContent.includes("GOFAST"),"console select failed");
      el("consoleInput").value="/mode field";el("consoleForm").requestSubmit();
      assert(el("graphCanvas").dataset.mapMode==="field","map mode switch failed");
      el("consoleInput").value="/intensity 85";el("consoleForm").requestSubmit();
      assert(el("intensity").value==="85","intensity command failed");
      el("pauseScene").click();
      assert(el("pauseScene").textContent==="RESUME SCENE","pause failed");
      const png=el("creatureCanvas").toDataURL("image/png");
      assert(png.startsWith("data:image/png;base64,")&&png.length>300,
        "procedural scene did not encode to a real PNG");
      el("shareView").click();
      assert(window.location.hash.includes("entity=r-gofast-official-footage"),
        "share link did not store current selected entity");
      assert(el("viewUrl").value.includes("entity=r-gofast-official-footage"),
        "share field is not usable");
      history.replaceState(null,"","#entity=s-shaggoth-prime&tab=data&mode=field&zoom=1.75&intensity=45");
      window.dispatchEvent(new Event("hashchange"));
      assert(el("selectedName").textContent==="Shaggoth Prime",
        "deep-link restore did not select entity");
      assert(el("intensity").value==="45","deep-link intensity failed");
      assert(document.querySelector('[data-tab="data"]').getAttribute("aria-selected")==="true",
        "deep-link tab restore failed");
      assert(el("graphCanvas").dataset.mapMode==="field","deep-link graph mode failed");
      document.documentElement.dataset.xenologySmoke="pass";
    }catch(error){
      document.documentElement.dataset.xenologySmoke="fail";
      document.documentElement.dataset.xenologyError=String(error.message).slice(0,180);
    }
  },1550);
});
"""

class Handler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        return

def main()->int:
    chrome=next((p for name in ("chromium","google-chrome","chromium-browser","google-chrome-stable")
                 if (p:=shutil.which(name))),None)
    if not chrome:
        print("XENOLOGY: Chrome/Chromium missing",file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-xenology-") as tmp:
        root=Path(tmp)
        dest=root/"cosmos"/"xenology"
        shutil.copytree(XENO,dest)
        page=dest/"index.html"
        html=page.read_text(encoding="utf-8")
        target='<script defer src="./app.js"></script>'
        assert target in html
        page.write_text(html.replace(target,target+'<script defer src="./probe.js"></script>'),encoding="utf-8")
        (dest/"probe.js").write_text(PROBE,encoding="utf-8")
        server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(root)))
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}/cosmos/xenology/"
            with tempfile.TemporaryDirectory(prefix="cl1-xeno-chrome-") as profile:
                proc=subprocess.run([
                    chrome,"--headless","--no-sandbox","--disable-extensions",
                    "--disable-background-networking","--disable-default-apps",
                    "--disable-sync","--no-first-run","--disable-dev-shm-usage",
                    "--window-size=1660,1100","--virtual-time-budget=5600",
                    f"--user-data-dir={profile}","--dump-dom",url
                ],capture_output=True,text=True,timeout=55,
                   env={**os.environ,"NO_PROXY":"127.0.0.1,localhost","no_proxy":"127.0.0.1,localhost"})
            if proc.returncode:
                print("XENOLOGY: Chrome exited",proc.returncode,proc.stderr[-900:],file=sys.stderr)
                return 1
            dom=proc.stdout
            for marker in ('data-xenology-smoke="pass"', 'data-rendered="true"',
                           'id="consoleForm"', 'id="graphCanvas"'):
                if marker not in dom:
                    tag=re.search(r'<html\b[^>]*>',dom)
                    print("XENOLOGY: missing",marker,"html",tag.group(0) if tag else "missing",file=sys.stderr)
                    print("Chrome stderr",proc.stderr[-900:],file=sys.stderr)
                    return 1
            print("CL1 XENOLOGY CHROME OK: 36 cards / live canvas / search / graph / AARO / console / pause")
            return 0
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=3)

if __name__=="__main__":
    raise SystemExit(main())
