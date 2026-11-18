#!/usr/bin/env python3
"""Headless Chromium integration test for CL1 planetary orrery + sandbox controls.
Uses copied static files and an injected same-origin probe; no external network.
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
FORGE=ROOT/"docs"/"cosmos"/"planets"
PROBE=r"""
window.addEventListener("load",()=>{
  setTimeout(()=>{
    try {
      const el=id=>document.getElementById(id);
      const check=(value,msg)=>{if(!value)throw Error(msg)};
      check(el("orrery").dataset.renderedPlanets==="8","orrery does not render all eight");
      check(el("globe").dataset.renderedGlobe==="earth","default Earth not rendered");
      document.querySelector('[data-planet-id="mars"]').click();
      check(el("planetName").textContent==="Mars","Mars selection failed");
      el("createClone").click();
      check(el("cloneCount").textContent==="1","sandbox clone not created");
      check(el("recordType").textContent.includes("HYPOTHETICAL"),"clone reference separation failed");
      const diameter=el("cloneRadius");
      diameter.value="1.5";diameter.dispatchEvent(new Event("input",{bubbles:true}));
      check(el("diameter").textContent.includes("10,188"),"diameter sandbox tuning failed");
      const spin=el("cloneSpin");
      spin.value="-1";spin.dispatchEvent(new Event("input",{bubbles:true}));
      check(el("rotation").textContent.includes("-24.6"),"retrograde sandbox tuning failed");
      const input=el("commandInput");
      input.value="/date 2030-01-01";el("commandForm").requestSubmit();
      check(el("epochDate").value==="2030-01-01","date command failed");
      input.value="/planet Neptune";el("commandForm").requestSubmit();
      check(el("planetName").textContent==="Neptune","planet command failed");
      check(el("cloneCount").textContent==="1","source selection destroyed sandbox clone");
      document.querySelector("#cloneList button").click();
      check(el("planetName").textContent.includes("Mars CL1"),"clone re-selection failed");
      el("removeClone").click();
      check(el("cloneCount").textContent==="0","clone removal failed");
      check(el("planetName").textContent==="Mars","source restore failed");
      document.documentElement.dataset.planetSmoke="pass";
    }catch(e){
      document.documentElement.dataset.planetSmoke="fail";
      document.documentElement.dataset.planetSmokeError=String(e.message).slice(0,200);
    }
  },1200);
});
"""

class Handler(SimpleHTTPRequestHandler):
    def log_message(self,*args):
        return

def main()->int:
    chrome=next((p for name in ("chromium","google-chrome","chromium-browser","google-chrome-stable")
                 if (p:=shutil.which(name))),None)
    if chrome is None:
        print("CL1 PLANETS: Chromium missing",file=sys.stderr)
        return 2
    with tempfile.TemporaryDirectory(prefix="cl1-planets-") as temp:
        tmp=Path(temp)
        site=tmp/"cosmos"/"planets"
        shutil.copytree(FORGE,site)
        html=site/"index.html"
        text=html.read_text(encoding="utf-8")
        anchor='<script src="./planets.js" defer></script>'
        assert anchor in text
        html.write_text(text.replace(anchor,anchor+'\n<script src="./probe.js" defer></script>'),encoding="utf-8")
        (site/"probe.js").write_text(PROBE,encoding="utf-8")
        server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(tmp)))
        server.daemon_threads=True
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            url=f"http://127.0.0.1:{server.server_port}/cosmos/planets/"
            with tempfile.TemporaryDirectory(prefix="cl1-chrome-") as profile:
                proc=subprocess.run([
                    chrome,"--headless","--no-sandbox","--disable-extensions",
                    "--disable-background-networking","--disable-default-apps",
                    "--disable-sync","--no-first-run","--disable-dev-shm-usage",
                    "--window-size=1600,1050","--virtual-time-budget=5200",
                    f"--user-data-dir={profile}","--dump-dom",url
                ],capture_output=True,text=True,timeout=55,
                env={**os.environ,"NO_PROXY":"127.0.0.1,localhost",
                     "no_proxy":"127.0.0.1,localhost"})
            if proc.returncode:
                print("CL1 PLANETS: Chrome returned",proc.returncode,proc.stderr[-1000:],file=sys.stderr)
                return 1
            dom=proc.stdout
            required=['data-rendered-planets="8"','data-rendered-globe="',
                      'data-planet-smoke="pass"','id="createClone"','id="commandForm"']
            for marker in required:
                if marker not in dom:
                    tag=re.search(r'<html\b[^>]*>',dom)
                    print("CL1 PLANETS: missing",marker,"html",tag.group(0) if tag else "missing",file=sys.stderr)
                    print("Chrome stderr",proc.stderr[-700:],file=sys.stderr)
                    return 1
            print("CL1 PLANETS CHROME OK: 8 rendered orbits / sandbox clone / data tuning / command console")
            return 0
        finally:
            server.shutdown();server.server_close();thread.join(timeout=3)

if __name__=="__main__":
    raise SystemExit(main())
