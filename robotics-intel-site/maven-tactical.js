(() => {
  "use strict";
  document.body.classList.add("tactical-ui");
  const workspace=document.querySelector(".workspace");
  const top=document.querySelector(".top");
  if(!workspace||!top) return;

  let lastSnapshot=null;
  let lastAt=0;
  const logBuffer=[];

  const strip=document.createElement("section");
  strip.className="tactical-strip";
  strip.setAttribute("data-no-translate","true");
  strip.innerHTML=`
    <div class="tac-kpi good">OPS CONDITION<b id="tacCondition">CHECKING</b></div>
    <div class="tac-kpi info">LIVE FABRIC<b id="tacFabric">CONNECTING</b></div>
    <div class="tac-kpi info">PALANTIR<b id="tacPalantir">CHECKING</b></div>
    <div class="tac-kpi good">SOURCE POLICY<b>PUBLIC / AUTH</b></div>
    <div class="tac-kpi">DATA AGE<b id="tacAge">—</b></div>
    <div class="tac-kpi warn">OPEN EVENTS<b id="tacEvents">0</b></div>
    <div class="tac-kpi info">UTC<b id="tacUtc">—</b></div>
  `;
  workspace.prepend(strip);

  const log=document.createElement("section");
  log.className="tactical-log";
  log.id="tacticalLog";
  log.innerHTML=`
    <div class="tactical-log-head">SITREP // EVENT BUS <button type="button" id="tacticalLogClose">CLOSE</button></div>
    <div id="tacticalLogRows"></div>
  `;
  document.body.appendChild(log);
  document.getElementById("tacticalLogClose").addEventListener("click",()=>log.classList.remove("open"));

  const hotkeys=document.createElement("nav");
  hotkeys.className="tactical-hotkeys";
  hotkeys.setAttribute("data-no-translate","true");
  hotkeys.innerHTML=`
    <button type="button" data-hot="map">1 MAP</button>
    <button type="button" data-hot="sim">2 SIM</button>
    <button type="button" data-hot="media">3 MEDIA</button>
    <button type="button" data-hot="palantir">4 PAL</button>
    <button type="button" data-hot="sitrep">L SITREP</button>
  `;
  document.body.appendChild(hotkeys);

  function text(id,value){const e=document.getElementById(id);if(e)e.textContent=value}

  function renderLog(){
    const host=document.getElementById("tacticalLogRows");if(!host)return;
    host.textContent="";
    for(const item of logBuffer.slice(0,24)){
      const row=document.createElement("div");
      row.className="tactical-log-row "+(item.level||"info");
      row.textContent="["+new Date(item.at).toLocaleTimeString()+"] "+item.message;
      host.appendChild(row);
    }
    text("tacEvents",String(logBuffer.length));
  }

  function pushLog(message,level="info",at=Date.now()){
    if(!message)return;
    const key=message+"|"+Math.floor(at/15000);
    if(logBuffer.some(x=>x.key===key))return;
    logBuffer.unshift({key,message,level,at});
    if(logBuffer.length>60)logBuffer.length=60;
    renderLog();
  }

  function applySnapshot(s){
    if(!s||s.schema!=="xunia.maven.live.v1")return;
    lastSnapshot=s;lastAt=Date.parse(s.generated_at)||Date.now();
    const degraded=Number(s.ops?.summary?.degraded||0);
    const condition=degraded===0?"GREEN":degraded<=2?"AMBER":"RED";
    text("tacCondition",condition);
    const conditionEl=document.getElementById("tacCondition")?.parentElement;
    if(conditionEl) conditionEl.className="tac-kpi "+(condition==="GREEN"?"good":condition==="AMBER"?"warn":"bad");
    text("tacFabric","LIVE #"+s.sequence);
    const p=s.palantir||{};
    text("tacPalantir",p.connected?(p.ontology_bound?"BOUND":"CONNECTED"):(p.configured?"ERROR":"STANDBY"));
    for(const evt of s.events||[]) pushLog(evt.message,evt.level||"info",lastAt);
    if((s.events||[]).length===0&&logBuffer.length===0) pushLog("MAVEN live fabric synchronized","good",lastAt);
  }

  function connect(){
    if(!("EventSource" in window)){text("tacFabric","POLLING");return}
    try{
      const es=new EventSource("https://xunia-ops-api.onrender.com/api/live");
      es.addEventListener("open",()=>text("tacFabric","ONLINE"));
      es.addEventListener("snapshot",e=>{try{applySnapshot(JSON.parse(e.data))}catch{}});
      es.addEventListener("error",()=>text("tacFabric","DEGRADED"));
    }catch{text("tacFabric","DEGRADED")}
  }

  document.querySelectorAll(".panel-head").forEach(head=>{
    if(head.querySelector(".panel-focus"))return;
    const btn=document.createElement("button");
    btn.type="button";btn.className="panel-focus";btn.textContent="FOCUS";
    head.appendChild(btn);
    btn.addEventListener("click",()=>{
      const panel=head.closest(".panel");if(!panel)return;
      const focused=panel.classList.toggle("focused");
      btn.textContent=focused?"EXIT":"FOCUS";
    });
  });

  function activatePane(name){
    if(matchMedia("(max-width:900px)").matches){
      const btn=document.querySelector('[data-mobile-pane="'+name+'"]');btn?.click();return;
    }
    if(name==="palantir"){document.getElementById("palantirModeToggle")?.click();return}
    const panel=document.querySelector('[data-pane="'+name+'"]');
    if(!panel)return;
    document.querySelectorAll(".panel.focused").forEach(p=>p.classList.remove("focused"));
    panel.classList.add("focused");
    const b=panel.querySelector(".panel-focus");if(b)b.textContent="EXIT";
  }

  hotkeys.addEventListener("click",e=>{
    const action=e.target.closest("button")?.dataset.hot;if(!action)return;
    if(action==="sitrep"){log.classList.toggle("open");return}
    activatePane(action);
  });

  document.addEventListener("keydown",e=>{
    if(/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||""))return;
    if(e.key==="1")activatePane("map");
    if(e.key==="2")activatePane("sim");
    if(e.key==="3")activatePane("media");
    if(e.key==="4")activatePane("palantir");
    if(e.key.toLowerCase()==="l")log.classList.toggle("open");
    if(e.key==="Escape")document.querySelectorAll(".panel.focused").forEach(p=>p.classList.remove("focused"));
  });

  setInterval(()=>{
    text("tacUtc",new Date().toISOString().slice(11,19)+"Z");
    text("tacAge",lastAt?Math.max(0,Math.floor((Date.now()-lastAt)/1000))+"s":"—");
  },1000);

  connect();
  pushLog("TACTICAL UI ACTIVE // situational awareness mode","good");
  pushLog("Target generation and weapon control remain disconnected","info");
})();