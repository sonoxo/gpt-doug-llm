(() => {
  "use strict";
  document.body.classList.add("tactical-ui");
  const workspace=document.querySelector(".workspace");
  const top=document.querySelector(".top");
  if(!workspace||!top) return;

  let lastSnapshot=null;
  let lastAt=0;
  let paletteIndex=0;
  const logBuffer=[];
  const commands=[];

  const strip=document.createElement("section");
  strip.className="tactical-strip";
  strip.setAttribute("data-no-translate","true");
  strip.innerHTML=`
    <div class="tac-kpi good">OPS CONDITION<b id="tacCondition">CHECKING</b></div>
    <div class="tac-kpi info">LIVE FABRIC<b id="tacFabric">CONNECTING</b></div>
    <div class="tac-kpi info">PALANTIR<b id="tacPalantir">CHECKING</b></div>
    <div class="tac-kpi good">SOURCE POLICY<b>PUBLIC / AUTH</b></div>
    <div class="tac-kpi">DATA AGE<b id="tacAge">—</b></div>
    <div class="tac-kpi warn">EVENT BUFFER<b id="tacEvents">0</b></div>
    <div class="tac-kpi info">DATA LINK<b id="tacLink">CHECKING</b></div>
    <div class="tac-kpi info">UTC<b id="tacUtc">—</b></div>
  `;
  workspace.prepend(strip);

  const ribbon=document.createElement("section");
  ribbon.className="tactical-ribbon";
  ribbon.setAttribute("data-no-translate","true");
  ribbon.innerHTML=`
    <strong>SITREP</strong>
    <span class="ribbon-feed" id="tacRibbon">Initializing tactical situational-awareness layer…</span>
    <span class="ribbon-state" id="tacRibbonState">SYNC</span>
  `;
  strip.insertAdjacentElement("afterend",ribbon);

  const map=document.querySelector('[data-pane="map"]');
  if(map){
    const bearing=document.createElement("div");
    bearing.className="tac-bearing";
    bearing.setAttribute("aria-hidden","true");
    bearing.innerHTML=["270 W","300","330","000 N","030","060","090 E","120","150"].map(x=>"<span>"+x+"</span>").join("");
    map.appendChild(bearing);

    const grid=document.createElement("div");
    grid.className="tac-grid-labels";grid.setAttribute("aria-hidden","true");
    grid.innerHTML=["A","B","C","D","E","F"].map(x=>"<span>"+x+"</span>").join("");
    map.appendChild(grid);

    const scan=document.createElement("div");scan.className="map-scan";scan.setAttribute("aria-hidden","true");map.appendChild(scan);

    const stack=document.createElement("div");
    stack.className="tac-status-stack";
    stack.innerHTML='<span>MAP <b>PUBLIC</b></span><span>GEO <b>COARSE</b></span><span>ACTION <b>DISCONNECTED</b></span>';
    map.appendChild(stack);
  }

  const log=document.createElement("section");
  log.className="tactical-log";log.id="tacticalLog";
  log.innerHTML=`
    <div class="tactical-log-head">SITREP // LIVE EVENT BUS <button type="button" id="tacticalLogClose">CLOSE</button></div>
    <div id="tacticalLogRows"></div>
  `;
  document.body.appendChild(log);
  document.getElementById("tacticalLogClose").addEventListener("click",()=>log.classList.remove("open"));

  const hotkeys=document.createElement("nav");
  hotkeys.className="tactical-hotkeys";hotkeys.setAttribute("data-no-translate","true");
  hotkeys.innerHTML=`
    <button type="button" data-hot="map">1 MAP</button>
    <button type="button" data-hot="sim">2 SIM</button>
    <button type="button" data-hot="schematic">3 SCHEMATIC</button>
    <button type="button" data-hot="palantir">4 PAL</button>
    <button type="button" data-hot="sitrep">L SITREP</button>
    <button type="button" data-hot="palette">⌘K CMD</button>
  `;
  document.body.appendChild(hotkeys);

  const palette=document.createElement("section");
  palette.className="tactical-palette";palette.id="tacticalPalette";
  palette.innerHTML=`
    <div class="tactical-palette-box">
      <div class="tactical-palette-head">TACTICAL COMMAND PALETTE <span style="margin-left:auto;color:#708677">ESC CLOSE</span></div>
      <input id="tacticalPaletteInput" autocomplete="off" placeholder="Search safe operator commands…">
      <div class="tactical-palette-list" id="tacticalPaletteList"></div>
    </div>
  `;
  document.body.appendChild(palette);

  function text(id,value){const e=document.getElementById(id);if(e)e.textContent=value}

  function renderLog(){
    const host=document.getElementById("tacticalLogRows");if(!host)return;
    host.textContent="";
    for(const item of logBuffer.slice(0,30)){
      const row=document.createElement("div");
      row.className="tactical-log-row "+(item.level||"info");
      row.textContent="["+new Date(item.at).toLocaleTimeString()+"] "+item.message;
      host.appendChild(row);
    }
    text("tacEvents",String(logBuffer.length));
    text("tacRibbon",logBuffer[0]?.message||"Live fabric synchronized");
  }

  function pushLog(message,level="info",at=Date.now()){
    if(!message)return;
    const key=message+"|"+Math.floor(at/15000);
    if(logBuffer.some(x=>x.key===key))return;
    logBuffer.unshift({key,message,level,at});
    if(logBuffer.length>80)logBuffer.length=80;
    renderLog();
  }

  function applySnapshot(s){
    if(!s||s.schema!=="xunia.maven.live.v1")return;
    lastSnapshot=s;lastAt=Date.parse(s.generated_at)||Date.now();
    const reachable=Number(s.ops?.summary?.reachable||0);
    const total=Number(s.ops?.summary?.total||0);
    const degraded=Number(s.ops?.summary?.degraded||0);
    const condition=degraded===0?"GREEN":degraded<=2?"AMBER":"RED";
    text("tacCondition",condition);
    const conditionEl=document.getElementById("tacCondition")?.parentElement;
    if(conditionEl) conditionEl.className="tac-kpi "+(condition==="GREEN"?"good":condition==="AMBER"?"warn":"bad");
    text("tacFabric","LIVE #"+s.sequence);
    text("tacLink",total?Math.round((reachable/total)*100)+"%":"—");
    const p=s.palantir||{};
    text("tacPalantir",p.connected?(p.ontology_bound?"BOUND":"CONNECTED"):(p.configured?"ERROR":"STANDBY"));
    text("tacRibbonState",condition+" · "+(lastAt?"FRESH":"WAIT"));
    for(const evt of s.events||[]) pushLog(evt.message,evt.level||"info",lastAt);
    if((s.events||[]).length===0&&logBuffer.length===0) pushLog("MAVEN live fabric synchronized","good",lastAt);
  }

  function connect(){
    if(!("EventSource" in window)){text("tacFabric","POLLING");return}
    try{
      const es=new EventSource("https://xunia-ops-api.onrender.com/api/live");
      es.addEventListener("open",()=>{text("tacFabric","ONLINE");pushLog("Live SSE fabric connected","good")});
      es.addEventListener("snapshot",e=>{try{applySnapshot(JSON.parse(e.data))}catch{}});
      es.addEventListener("error",()=>{text("tacFabric","DEGRADED");pushLog("Live fabric degraded; platform fallback remains available","warn")});
    }catch{text("tacFabric","DEGRADED")}
  }

  document.querySelectorAll(".panel-head").forEach(head=>{
    if(!head.querySelector(".panel-pin")){
      const pin=document.createElement("button");pin.type="button";pin.className="panel-pin";pin.textContent="PIN";
      head.appendChild(pin);
      pin.addEventListener("click",()=>{
        const panel=head.closest(".panel");if(!panel)return;
        const active=panel.classList.toggle("pinned");pin.classList.toggle("active",active);pin.textContent=active?"PINNED":"PIN";
      });
    }
    if(head.querySelector(".panel-focus"))return;
    const btn=document.createElement("button");btn.type="button";btn.className="panel-focus";btn.textContent="FOCUS";
    head.appendChild(btn);
    btn.addEventListener("click",()=>{
      const panel=head.closest(".panel");if(!panel)return;
      const focused=panel.classList.toggle("focused");btn.textContent=focused?"EXIT":"FOCUS";
    });
  });

  function activatePane(name){
    if(matchMedia("(max-width:900px)").matches){
      const btn=document.querySelector('[data-mobile-pane="'+name+'"]');btn?.click();return;
    }
    if(name==="palantir"){
      const pal=document.querySelector('[data-pane="palantir"]');
      if(pal){
        document.querySelectorAll(".panel.focused").forEach(p=>p.classList.remove("focused"));
        pal.classList.add("focused");
      }
      return;
    }
    const panel=document.querySelector('[data-pane="'+name+'"]');
    if(!panel)return;
    document.querySelectorAll(".panel.focused").forEach(p=>p.classList.remove("focused"));
    panel.classList.add("focused");
    const b=panel.querySelector(".panel-focus");if(b)b.textContent="EXIT";
  }

  function exitFocus(){
    document.querySelectorAll(".panel.focused").forEach(p=>{
      p.classList.remove("focused");const b=p.querySelector(".panel-focus");if(b)b.textContent="FOCUS";
    });
  }

  function refreshPublic(){
    document.getElementById("mapRefresh")?.click();
    pushLog("Manual public-data refresh requested","info");
  }

  commands.push(
    {name:"Focus Map",hint:"1",run:()=>activatePane("map")},
    {name:"Focus Synthetic Lab",hint:"2",run:()=>activatePane("sim")},
    {name:"Open Infrastructure Schematic",hint:"3",run:()=>document.getElementById("infraSchematicToggle")?.click()},
    {name:"Focus Palantir Live",hint:"4",run:()=>activatePane("palantir")},
    {name:"Open SITREP Event Bus",hint:"L",run:()=>log.classList.add("open")},
    {name:"Refresh Public Data",hint:"R",run:refreshPublic},
    {name:"Toggle Low-Light Display",hint:"N",run:()=>document.body.classList.toggle("low-light")},
    {name:"Exit Focus Mode",hint:"ESC",run:exitFocus}
  );

  function renderPalette(filter=""){
    const list=document.getElementById("tacticalPaletteList");list.textContent="";
    const items=commands.filter(c=>c.name.toLowerCase().includes(filter.toLowerCase()));
    paletteIndex=Math.max(0,Math.min(paletteIndex,Math.max(0,items.length-1)));
    items.forEach((cmd,i)=>{
      const b=document.createElement("button");b.type="button";b.className="tactical-command"+(i===paletteIndex?" active":"");
      b.innerHTML="<strong>"+cmd.name+"</strong><kbd>"+cmd.hint+"</kbd>";
      b.addEventListener("click",()=>{closePalette();cmd.run()});list.appendChild(b);
    });
  }

  function openPalette(){
    palette.classList.add("open");paletteIndex=0;const input=document.getElementById("tacticalPaletteInput");input.value="";renderPalette();setTimeout(()=>input.focus(),0);
  }
  function closePalette(){palette.classList.remove("open")}
  document.getElementById("tacticalPaletteInput").addEventListener("input",e=>{paletteIndex=0;renderPalette(e.target.value)});

  palette.addEventListener("click",e=>{if(e.target===palette)closePalette()});

  hotkeys.addEventListener("click",e=>{
    const action=e.target.closest("button")?.dataset.hot;if(!action)return;
    if(action==="sitrep"){log.classList.toggle("open");return}
    if(action==="palette"){openPalette();return}
    if(action==="schematic"){document.getElementById("infraSchematicToggle")?.click();return}
    activatePane(action);
  });

  document.addEventListener("keydown",e=>{
    const typing=/INPUT|TEXTAREA|SELECT/.test(document.activeElement?.tagName||"");
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();openPalette();return}
    if(palette.classList.contains("open")){
      if(e.key==="Escape"){closePalette();return}
      if(e.key==="ArrowDown"||e.key==="ArrowUp"){
        e.preventDefault();paletteIndex+=e.key==="ArrowDown"?1:-1;const f=document.getElementById("tacticalPaletteInput").value;renderPalette(f);return
      }
      if(e.key==="Enter"){
        const active=document.querySelector(".tactical-command.active");active?.click();return
      }
      return;
    }
    if(typing)return;
    if(e.key==="1")activatePane("map");
    if(e.key==="2")activatePane("sim");
    if(e.key==="3")document.getElementById("infraSchematicToggle")?.click();
    if(e.key==="4")activatePane("palantir");
    if(e.key.toLowerCase()==="l")log.classList.toggle("open");
    if(e.key.toLowerCase()==="r")refreshPublic();
    if(e.key.toLowerCase()==="n")document.body.classList.toggle("low-light");
    if(e.key==="Escape")exitFocus();
  });

  setInterval(()=>{
    text("tacUtc",new Date().toISOString().slice(11,19)+"Z");
    text("tacAge",lastAt?Math.max(0,Math.floor((Date.now()-lastAt)/1000))+"s":"—");
  },1000);

  connect();
  pushLog("TACTICAL MAX UI ACTIVE // situational-awareness mode","good");
  pushLog("Public/authorized source fusion active","good");
  pushLog("Target generation, weapon control and autonomous external action remain disconnected","info");
})();