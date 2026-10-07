(() => {
  "use strict";
  const frame=document.getElementById("mavenFrame");
  const shell=document.querySelector(".viewerShell");
  const header=document.querySelector("header");
  if(!frame||!shell||!header) return;

  const state={
    startedAt:0,
    loadedAt:0,
    loadMs:null,
    timeout:null,
    retries:0,
    online:navigator.onLine,
    ops:null,
    palantir:null
  };

  const pill=document.createElement("button");
  pill.type="button";
  pill.className="maven-system-pill warn";
  pill.id="mavenSystemPill";
  pill.innerHTML='<span class="dot"></span><span id="mavenSystemLabel">SYSTEM CHECK</span>';
  header.appendChild(pill);

  const loader=document.createElement("div");
  loader.className="maven-frame-loader";
  loader.id="mavenFrameLoader";
  loader.innerHTML=`
    <div class="maven-frame-loader-box">
      <div class="maven-frame-loader-title">MAVEN VIEW LOADING</div>
      <div class="maven-frame-loader-msg" id="mavenLoaderMsg">Connecting workspace…</div>
      <div class="maven-loader-track"><div class="maven-loader-bar"></div></div>
      <div class="maven-frame-loader-actions">
        <button type="button" id="mavenLoaderRetry">RETRY</button>
        <button type="button" id="mavenLoaderClose">HIDE</button>
      </div>
    </div>`;
  shell.appendChild(loader);

  const drawer=document.createElement("aside");
  drawer.className="maven-system-drawer";
  drawer.id="mavenSystemDrawer";
  drawer.innerHTML=`
    <div class="maven-system-head">
      <strong>SYSTEM HEALTH</strong>
      <button type="button" id="mavenSystemClose">CLOSE</button>
    </div>
    <div class="maven-health-grid">
      <div class="maven-health-card" id="healthNetwork">NETWORK<b>CHECKING</b></div>
      <div class="maven-health-card" id="healthFrame">VIEW FRAME<b>CHECKING</b></div>
      <div class="maven-health-card" id="healthOps">XUNIA OPS<b>CHECKING</b></div>
      <div class="maven-health-card" id="healthPalantir">PALANTIR<b>CHECKING</b></div>
    </div>
    <div class="maven-system-actions">
      <button type="button" id="mavenReloadView">RELOAD VIEW</button>
      <button type="button" id="mavenReconnect">RECHECK SERVICES</button>
      <button type="button" id="mavenGlobalView">GLOBAL PUBLIC MAP</button>
      <button type="button" id="mavenTacticalView">TACTICAL WORKSPACE</button>
    </div>
    <div class="maven-system-note" id="mavenSystemNote">Health checks use public service status only. No private credentials are exposed in this browser.</div>
  `;
  document.querySelector("main")?.appendChild(drawer);

  function setCard(id,label,stateClass=""){
    const el=document.getElementById(id);
    if(!el) return;
    el.className="maven-health-card "+stateClass;
    const b=el.querySelector("b");
    if(b) b.textContent=label;
  }

  function overall(){
    const bad=!state.online || state.ops===false;
    const warn=!bad && (state.palantir===false || state.loadMs===null);
    pill.className="maven-system-pill "+(bad?"bad":warn?"warn":"good");
    document.getElementById("mavenSystemLabel").textContent=bad?"SYSTEM DEGRADED":warn?"SYSTEM PARTIAL":"SYSTEM HEALTHY";
  }

  function showLoader(message){
    document.getElementById("mavenLoaderMsg").textContent=message;
    loader.classList.add("show");
  }

  function hideLoader(){
    loader.classList.remove("show");
  }

  function beginFrameLoad(){
    state.startedAt=performance.now();
    state.loadedAt=0;
    state.loadMs=null;
    clearTimeout(state.timeout);
    showLoader("Connecting "+(frame.title||"MAVEN workspace")+"…");
    setCard("healthFrame","LOADING","warn");
    state.timeout=setTimeout(()=>{
      if(state.loadedAt) return;
      showLoader("View is taking longer than expected. You can retry without leaving MAVEN.");
      setCard("healthFrame","TIMEOUT","warn");
      overall();
    },9000);
  }

  frame.addEventListener("load",()=>{
    state.loadedAt=performance.now();
    state.loadMs=Math.max(0,Math.round(state.loadedAt-state.startedAt));
    clearTimeout(state.timeout);
    setCard("healthFrame",state.loadMs+" ms","good");
    hideLoader();
    overall();
  });

  const originalSet=window.setMavenMode;
  if(typeof originalSet==="function"){
    window.setMavenMode=function(mode){
      beginFrameLoad();
      return originalSet(mode);
    };
  }

  async function check(){
    state.online=navigator.onLine;
    setCard("healthNetwork",state.online?"ONLINE":"OFFLINE",state.online?"good":"bad");
    try{
      const r=await fetch("https://xunia-ops-api.onrender.com/api/status",{cache:"no-store"});
      if(!r.ok) throw new Error("HTTP "+r.status);
      const d=await r.json();
      state.ops=Number(d.summary?.degraded||0)===0;
      setCard("healthOps",(d.summary?.reachable??"—")+"/"+(d.summary?.total??"—")+" REACHABLE",state.ops?"good":"warn");
    }catch{
      state.ops=false;
      setCard("healthOps","UNAVAILABLE","bad");
    }

    try{
      const r=await fetch("https://xunia-palantir-bridge.onrender.com/api/status",{cache:"no-store"});
      if(!r.ok) throw new Error("HTTP "+r.status);
      const d=await r.json();
      state.palantir=Boolean(d.connected);
      setCard("healthPalantir",d.connected?(d.ontology_bound?"BOUND":"CONNECTED"):(d.configured?"ERROR":"STANDBY"),d.connected?"good":"warn");
    }catch{
      state.palantir=false;
      setCard("healthPalantir","UNAVAILABLE","warn");
    }
    overall();
    document.getElementById("mavenSystemNote").textContent="Last check "+new Date().toLocaleTimeString()+" · view "+(state.loadMs===null?"pending":state.loadMs+" ms");
  }

  function reloadView(){
    state.retries++;
    beginFrameLoad();
    try{
      const u=new URL(frame.src,location.href);
      u.searchParams.set("cb",Date.now());
      frame.src=u.toString();
    }catch{
      frame.src=frame.src;
    }
  }

  pill.addEventListener("click",()=>drawer.classList.toggle("open"));
  document.getElementById("mavenSystemClose")?.addEventListener("click",()=>drawer.classList.remove("open"));
  document.getElementById("mavenLoaderRetry")?.addEventListener("click",reloadView);
  document.getElementById("mavenLoaderClose")?.addEventListener("click",hideLoader);
  document.getElementById("mavenReloadView")?.addEventListener("click",reloadView);
  document.getElementById("mavenReconnect")?.addEventListener("click",check);
  document.getElementById("mavenGlobalView")?.addEventListener("click",()=>document.getElementById("worldGridBtn")?.click());
  document.getElementById("mavenTacticalView")?.addEventListener("click",()=>document.querySelector('[data-mode="broadcast"]')?.click());

  addEventListener("online",()=>{state.online=true;check()},{passive:true});
  addEventListener("offline",()=>{state.online=false;check()},{passive:true});
  document.addEventListener("keydown",e=>{
    if(e.key==="Escape"&&drawer.classList.contains("open")) drawer.classList.remove("open");
  });

  beginFrameLoad();
  check();
  setInterval(check,30000);
})();
