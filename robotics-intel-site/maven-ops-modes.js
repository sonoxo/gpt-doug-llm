(() => {
  "use strict";
  const sim=document.querySelector('[data-pane="sim"]');
  const simboard=sim?.querySelector(".simboard");
  if(!sim||!simboard) return;

  const modebar=document.createElement("div");
  modebar.className="ops-modebar";
  modebar.setAttribute("data-no-translate","true");
  modebar.innerHTML=
    '<button type="button" data-ops-mode="training" class="active">TRAINING</button>'+
    '<button type="button" data-ops-mode="tac" class="tac">TAC OPS SIM</button>'+
    '<button type="button" data-ops-mode="spec" class="spec">SPEC OPS SIM</button>'+
    '<button type="button" data-ops-mode="def" class="def">DEFENSIVE OPS</button>';

  const hud=document.createElement("div");
  hud.className="ops-hud";
  hud.innerHTML=
    '<div class="info">MODE<b id="opsModeLabel">TRAINING</b></div>'+
    '<div class="good">SIM UNITS<b id="opsUnits">0</b></div>'+
    '<div class="good">DEFENSE<b id="opsDefense">READY</b></div>'+
    '<div class="warn">EXTERNAL ACTION<b>OFF</b></div>';

  const arsenal=document.createElement("div");
  arsenal.className="ops-arsenal";
  arsenal.setAttribute("data-no-translate","true");
  arsenal.innerHTML=
    '<button class="def" type="button" data-ops-fx="aegis">AEGIS BARRIER</button>'+
    '<button class="def" type="button" data-ops-fx="decoy">DECOY SWARM</button>'+
    '<button class="sig" type="button" data-ops-fx="jam">SIGNAL JAM</button>'+
    '<button class="def" type="button" data-ops-fx="repair">REPAIR FIELD</button>'+
    '<button class="fx" type="button" data-ops-fx="photon">PHOTON SWARM</button>'+
    '<button class="spec" type="button" data-ops-fx="prism">PRISM SPLIT</button>'+
    '<button class="spec" type="button" data-ops-fx="void">VOID WAVE</button>'+
    '<button class="fx" type="button" data-ops-fx="starfall">STARFALL</button>';

  const note=document.createElement("div");
  note.className="ops-mode-note";
  note.textContent="SIMULATION-ONLY CAPABILITY LAYER · FICTIONAL EFFECTS · NO REAL TARGETING · NO FIRE-CONTROL · NO EXTERNAL WEAPON OR VEHICLE LINK.";

  sim.querySelector(".stats")?.before(modebar);
  simboard.before(hud);
  sim.querySelector(".arsenal")?.after(arsenal,note);

  const overlay=document.createElement("canvas");
  overlay.className="ops-overlay";
  overlay.setAttribute("aria-hidden","true");
  simboard.appendChild(overlay);
  const ctx=overlay.getContext("2d");

  let w=1,h=1,dpr=1,last=performance.now(),mode="training";
  let effects=[];
  const units=Array.from({length:8},(_,i)=>({
    x:.18+(i%4)*.2,y:.3+Math.floor(i/4)*.34,
    vx:(i%2?1:-1)*(.018+(i%3)*.004),vy:((i%3)-1)*.004,
    phase:i*.61
  }));

  function resize(){
    const r=simboard.getBoundingClientRect();
    dpr=Math.min(devicePixelRatio||1,1.6);w=Math.max(1,r.width);h=Math.max(1,r.height);
    overlay.width=Math.round(w*dpr);overlay.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  new ResizeObserver(resize).observe(simboard);

  function log(msg){
    const feed=document.getElementById("eventFeed");
    if(!feed) return;
    const row=document.createElement("div");
    row.innerHTML='<span class="time">'+new Date().toLocaleTimeString()+'</span> '+msg;
    feed.prepend(row);
    while(feed.children.length>24) feed.removeChild(feed.lastChild);
  }

  function setMode(next){
    mode=next;
    const label={training:"TRAINING",tac:"TAC OPS SIM",spec:"SPEC OPS SIM",def:"DEFENSIVE OPS"}[next]||"TRAINING";
    document.getElementById("opsModeLabel").textContent=label;
    document.getElementById("opsUnits").textContent=next==="training"?"0":String(units.length);
    document.getElementById("opsDefense").textContent=next==="def"?"HARDENED":"READY";
    modebar.querySelectorAll("[data-ops-mode]").forEach(b=>b.classList.toggle("active",b.dataset.opsMode===next));
    simboard.classList.remove("ops-tac","ops-spec","ops-def");
    if(next!=="training") simboard.classList.add("ops-"+next);
    log(label+" enabled in synthetic scenario space");
  }

  function addFx(type){
    const now=performance.now();
    effects.push({type,start:now,duration:type==="aegis"?7000:type==="repair"?6000:4200,phase:Math.random()*Math.PI*2});
    if(type==="aegis") document.getElementById("opsDefense").textContent="AEGIS ACTIVE";
    if(type==="repair") document.getElementById("opsDefense").textContent="RECOVERY FIELD";
    log(type.toUpperCase().replaceAll("_"," ")+" deployed as synthetic visual effect");
  }

  function update(dt,ts){
    if(mode==="training") return;
    const pace=mode==="spec"?.55:mode==="def"?.35:1;
    for(const u of units){
      u.x+=u.vx*pace*dt/1000;u.y+=u.vy*pace*dt/1000;
      if(u.x<.08||u.x>.92)u.vx*=-1;if(u.y<.18||u.y>.86)u.vy*=-1;
    }
    effects=effects.filter(e=>ts-e.start<e.duration);
    if(!effects.some(e=>e.type==="aegis"||e.type==="repair")){
      document.getElementById("opsDefense").textContent=mode==="def"?"HARDENED":"READY";
    }
  }

  function drawGrid(color){
    ctx.strokeStyle=color;ctx.lineWidth=1;
    for(let x=0;x<w;x+=48){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke()}
    for(let y=0;y<h;y+=48){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke()}
  }

  function drawUnits(ts){
    if(mode==="training") return;
    for(let i=0;i<units.length;i++){
      const u=units[i],x=u.x*w,y=u.y*h+Math.sin(ts*.003+u.phase)*2;
      const color=mode==="spec"?"#c8a4ff":mode==="def"?"#9cffaa":"#82e8ff";
      ctx.strokeStyle=color;ctx.fillStyle=color;ctx.lineWidth=1.2;
      ctx.beginPath();ctx.arc(x,y,5,0,Math.PI*2);ctx.stroke();
      ctx.fillRect(x-1,y-1,2,2);
      ctx.font="7px monospace";ctx.fillText("SIM-"+String(i+1).padStart(2,"0"),x+8,y-6);
    }
  }

  function drawFx(ts){
    for(const e of effects){
      const p=Math.min(1,(ts-e.start)/e.duration);
      if(e.type==="aegis"){
        ctx.strokeStyle="rgba(156,255,170,"+(1-p)+")";ctx.lineWidth=2;
        ctx.beginPath();ctx.arc(w*.5,h*.52,Math.min(w,h)*(.18+.04*Math.sin(ts*.006)),0,Math.PI*2);ctx.stroke();
      }else if(e.type==="decoy"){
        ctx.fillStyle="rgba(130,232,255,"+(1-p)+")";
        for(let i=0;i<12;i++){const a=i*Math.PI/6+ts*.001;ctx.beginPath();ctx.arc(w*.5+Math.cos(a)*w*.28,h*.5+Math.sin(a)*h*.22,3,0,Math.PI*2);ctx.fill()}
      }else if(e.type==="jam"){
        ctx.strokeStyle="rgba(130,232,255,"+(1-p)*.7+")";
        for(let i=0;i<7;i++){const y=((i/7)+p)%1*h;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y+Math.sin(ts*.01+i)*8);ctx.stroke()}
      }else if(e.type==="repair"){
        ctx.fillStyle="rgba(156,255,170,"+(1-p)*.14+")";ctx.fillRect(0,0,w,h);
      }else if(e.type==="photon"){
        ctx.fillStyle="rgba(255,209,102,"+(1-p)+")";
        for(let i=0;i<24;i++){const a=i*.7+e.phase;const rr=p*Math.max(w,h)*.55;ctx.beginPath();ctx.arc(w*.5+Math.cos(a)*rr,h*.5+Math.sin(a)*rr,2.4,0,Math.PI*2);ctx.fill()}
      }else if(e.type==="prism"){
        ctx.strokeStyle="rgba(200,164,255,"+(1-p)+")";
        for(let i=0;i<8;i++){ctx.beginPath();ctx.moveTo(w*.5,h*.5);ctx.lineTo((i/7)*w,(i%2?0:h));ctx.stroke()}
      }else if(e.type==="void"){
        ctx.strokeStyle="rgba(200,164,255,"+(1-p)+")";ctx.lineWidth=3;
        ctx.beginPath();ctx.arc(w*.5,h*.5,p*Math.min(w,h)*.65,0,Math.PI*2);ctx.stroke();
      }else if(e.type==="starfall"){
        ctx.strokeStyle="rgba(255,177,29,"+(1-p)+")";
        for(let i=0;i<11;i++){const x=((i*.091+p*.37)%1)*w;const y=((p+i*.08)%1)*h;ctx.beginPath();ctx.moveTo(x-18,y-28);ctx.lineTo(x,y);ctx.stroke()}
      }
    }
  }

  function frame(ts){
    const dt=Math.min(40,ts-last);last=ts;
    ctx.clearRect(0,0,w,h);
    if(mode==="tac") drawGrid("rgba(124,231,255,.06)");
    if(mode==="spec") drawGrid("rgba(200,164,255,.05)");
    if(mode==="def") drawGrid("rgba(156,255,170,.06)");
    update(dt,ts);drawUnits(ts);drawFx(ts);
    requestAnimationFrame(frame);
  }

  modebar.addEventListener("click",e=>{const b=e.target.closest("[data-ops-mode]");if(b)setMode(b.dataset.opsMode)});
  arsenal.addEventListener("click",e=>{const b=e.target.closest("[data-ops-fx]");if(b)addFx(b.dataset.opsFx)});

  function showSimAndMode(next){
    const btn=document.querySelector('[data-mobile-pane="sim"]');
    if(matchMedia("(max-width:900px)").matches) btn?.click();
    setMode(next);
    sim.scrollIntoView({block:"nearest",inline:"nearest"});
  }

  const top=document.querySelector(".top");
  if(top&&!document.getElementById("mavenTacOpsQuick")){
    const defs=[
      ["mavenTacOpsQuick","TACTICAL SIM","tac"],
      ["mavenSpecOpsQuick","STEALTH SIM","spec"],
      ["mavenDefOpsQuick","DEFENSE SIM","def"]
    ];
    defs.forEach(([id,label,next])=>{
      const b=document.createElement("button");
      b.id=id;b.type="button";b.className="chip";b.textContent=label;
      b.addEventListener("click",()=>showSimAndMode(next));
      top.appendChild(b);
    });
  }

  window.addEventListener("message",evt=>{
    if(!["https://xunia.org","https://www.xunia.org"].includes(evt.origin)) return;
    if(evt.data?.type!=="maven-ui") return;
    if(evt.data.action==="open-tac") showSimAndMode("tac");
    if(evt.data.action==="open-spec") showSimAndMode("spec");
    if(evt.data.action==="open-def") showSimAndMode("def");
  });

  resize();setMode("training");requestAnimationFrame(frame);
})();