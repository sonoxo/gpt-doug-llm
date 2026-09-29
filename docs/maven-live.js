(() => {
  "use strict";
  const API="https://xunia-ops-api.onrender.com";
  const rail=document.getElementById("commandRail");
  const railToggle=document.getElementById("opsRailToggle");
  let lastGeneratedAt=null;
  let lastSnapshot=null;
  let source=null;
  let failures=0;
  let fallbackTimer=null;
  const eventBuffer=[];

  function addTopPill(){
    const header=document.querySelector("header");
    if(!header||document.getElementById("mavenLivePill")) return;
    const pill=document.createElement("span");
    pill.id="mavenLivePill";
    pill.className="pill";
    pill.textContent="LIVE BUS CONNECTING";
    const boundary=[...header.querySelectorAll(".pill")].find(x=>x.textContent.includes("TARGETING"));
    header.insertBefore(pill,boundary||null);
  }

  function buildCard(){
    if(!rail||document.getElementById("mavenLiveCard")) return;
    const card=document.createElement("div");
    card.className="card";
    card.id="mavenLiveCard";
    card.innerHTML=`
      <h2>MAVEN LIVE FABRIC</h2>
      <div class="live-grid">
        <div class="live-kpi good"><span>STREAM</span><b id="liveStreamState">CONNECTING</b></div>
        <div class="live-kpi info"><span>SEQUENCE</span><b id="liveSeq">—</b></div>
        <div class="live-kpi good"><span>XUNIA OPS</span><b id="liveOps">—</b></div>
        <div class="live-kpi info"><span>PALANTIR</span><b id="livePalantir">—</b></div>
        <div class="live-kpi info"><span>USGS</span><b id="liveQuakes">—</b></div>
        <div class="live-kpi"><span>FRESHNESS</span><b id="liveAge">—</b></div>
      </div>
      <div class="live-event-list" id="liveEventList"></div>
      <div class="live-policy">PUBLIC / AUTHORIZED SOURCES · COARSE PUBLIC GEO · NO PERSON TRACKING · NO TARGETING · NO WEAPON CONTROL</div>
    `;
    const cards=rail.querySelectorAll(".card");
    if(cards.length>1) cards[1].insertAdjacentElement("afterend",card);
    else rail.appendChild(card);
  }

  function buildTicker(){
    if(document.getElementById("mavenLiveBar")) return;
    const bar=document.createElement("div");
    bar.id="mavenLiveBar";
    bar.className="live-fabric-bar";
    bar.setAttribute("data-no-translate","true");
    bar.innerHTML=`
      <span class="live-dot" aria-hidden="true"></span>
      <span class="live-fabric-label">MAVEN LIVE</span>
      <span class="live-fabric-ticker" id="liveTicker">Connecting live event fabric…</span>
      <span class="live-fabric-age" id="liveBarAge">—</span>
      <button class="live-fabric-open" type="button">OPEN</button>
    `;
    document.body.appendChild(bar);
    bar.querySelector("button").addEventListener("click",()=>railToggle?.click());
  }

  function text(id,value){
    const el=document.getElementById(id);
    if(el) el.textContent=value;
  }

  function setConnected(connected,degraded=false){
    const bar=document.getElementById("mavenLiveBar");
    if(bar){
      bar.classList.toggle("connected",connected&&!degraded);
      bar.classList.toggle("degraded",degraded);
    }
    text("liveStreamState",connected?(degraded?"DEGRADED":"LIVE"):"OFFLINE");
    const pill=document.getElementById("mavenLivePill");
    if(pill){
      pill.textContent=connected?(degraded?"LIVE BUS DEGRADED":"LIVE BUS ONLINE"):"LIVE BUS OFFLINE";
      pill.classList.toggle("ok",connected&&!degraded);
      pill.classList.toggle("off",!connected);
    }
  }

  function appendEvent(evt,generatedAt){
    if(!evt||!evt.message) return;
    const key=[evt.type,evt.message,generatedAt].join("|");
    if(eventBuffer.some(x=>x.key===key)) return;
    eventBuffer.unshift({key,evt,generatedAt});
    if(eventBuffer.length>40) eventBuffer.length=40;
    renderEvents();
  }

  function renderEvents(){
    const host=document.getElementById("liveEventList");
    if(host){
      host.textContent="";
      for(const item of eventBuffer.slice(0,16)){
        const row=document.createElement("div");
        row.className="live-event "+(item.evt.level||"info");
        const t=document.createElement("time");
        t.textContent=new Date(item.generatedAt||Date.now()).toLocaleTimeString();
        row.appendChild(t);
        row.appendChild(document.createTextNode(item.evt.message));
        host.appendChild(row);
      }
    }
    const ticker=document.getElementById("liveTicker");
    if(ticker){
      ticker.textContent=eventBuffer.length
        ? eventBuffer.slice(0,3).map(x=>x.evt.message).join("  •  ")
        : "Live fabric online · awaiting state changes";
    }
  }

  function updatePalantir(snapshot){
    const p=snapshot.palantir||{};
    text("livePalantir",p.connected?(p.ontology_bound?"BOUND":"CONNECTED"):(p.configured?"ERROR":"STANDBY"));
    text("palMode",p.mode||"UNKNOWN");
    text("palConnected",p.connected?"YES":"NO");
    text("palOntology",p.ontology_bound?"BOUND":p.configured?"NOT FOUND":"WAITING FOR TENANT");
    text("palObjects",p.object_type_count??"—");
    text("palActions",p.action_type_count??"—");
  }

  function applySnapshot(snapshot){
    if(!snapshot||snapshot.schema!=="xunia.maven.live.v1") return;
    lastSnapshot=snapshot;
    lastGeneratedAt=Date.parse(snapshot.generated_at)||Date.now();
    failures=0;

    const ops=snapshot.ops||{};
    const summary=ops.summary||{};
    const degraded=Number(summary.degraded||0)>0;
    setConnected(true,degraded);
    text("liveSeq","#"+snapshot.sequence);
    text("liveOps",(summary.reachable??"—")+"/"+(summary.total??"—"));
    text("liveQuakes",String((snapshot.earthquakes||[]).length)+" SIGNIFICANT");
    updatePalantir(snapshot);

    for(const evt of snapshot.events||[]) appendEvent(evt,snapshot.generated_at);
    if(!(snapshot.events||[]).length&&eventBuffer.length===0){
      appendEvent({type:"system",level:"good",message:"MAVEN live fabric synchronized"},snapshot.generated_at);
    }
  }

  async function fallbackSnapshot(){
    try{
      const r=await fetch(API+"/api/live/snapshot",{cache:"no-store"});
      if(!r.ok) throw new Error("HTTP "+r.status);
      applySnapshot(await r.json());
      setConnected(true,Number(lastSnapshot?.ops?.summary?.degraded||0)>0);
    }catch{
      setConnected(false,true);
    }
  }

  function startFallback(){
    if(fallbackTimer) return;
    fallbackSnapshot();
    fallbackTimer=setInterval(fallbackSnapshot,30000);
  }

  function stopFallback(){
    if(!fallbackTimer) return;
    clearInterval(fallbackTimer);
    fallbackTimer=null;
  }

  function connect(){
    if(!("EventSource" in window)){startFallback();return}
    try{
      source=new EventSource(API+"/api/live");
      source.addEventListener("open",()=>{failures=0;stopFallback();setConnected(true,false)});
      source.addEventListener("snapshot",evt=>{
        try{applySnapshot(JSON.parse(evt.data))}catch{}
      });
      source.addEventListener("error",()=>{
        failures++;
        setConnected(false,true);
        if(failures>=3) startFallback();
      });
    }catch{
      startFallback();
    }
  }

  function updateAge(){
    if(!lastGeneratedAt){
      text("liveAge","—");text("liveBarAge","—");return;
    }
    const age=Math.max(0,Math.floor((Date.now()-lastGeneratedAt)/1000));
    text("liveAge",age+"s");
    text("liveBarAge",age+"s");
    const stale=age>45;
    if(stale) setConnected(false,true);
  }

  addTopPill();
  buildCard();
  buildTicker();
  connect();
  setInterval(updateAge,1000);
  window.addEventListener("online",()=>{if(!source||source.readyState===2)connect()});
  window.addEventListener("offline",()=>setConnected(false,true));
})();