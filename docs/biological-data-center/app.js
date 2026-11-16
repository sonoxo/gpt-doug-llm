/* XUNIA / CL1 BIOLOGICAL DATA CENTER
 * Public Pages = static, evidence-labelled spatial ontology.
 * Local operator = optional same-origin read-only telemetry from localhost Python.
 * No cloud model calls, private account access or dependencies.
 */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const canvas = $("world");
  const ctx = canvas?.getContext("2d");
  const reduceMotion = window.matchMedia?.("(prefers-reduced-motion: reduce)").matches ?? false;
  const COLORS = {CORE:"#eaf4f2",NEURAL:"#9ce6da",IMMUNE:"#c4b1e8",MEMORY:"#d3dce7",CIRCULATION:"#b5edd8",GOVERNANCE:"#e4c8a1"};
  const SERVICES = ["ollama","cl1","jukebox","aura","nexus"];
  const state = {model:null,selected:"bio-core",layer:"ALL",yaw:0.18,pitch:0.28,zoom:1,panX:0,panY:0,
    points:[],drag:null,labels:true,frame:0,w:900,h:580,signals:null,genome:null,genomeSearch:"",
    live:false,disposed:false};
  const clamp = (v,a,b) => Math.min(b,Math.max(a,v));
  const byNode = id => state.model?.nodes.find(n=>n.id===id);
  const localOrigin = ["127.0.0.1","localhost"].includes(location.hostname);
  const show = (id, value) => { const el=$(id); if(el) el.textContent=String(value); };
  const statusFor = id => {
    if (id==="bank") return "NO BANK ADAPTER";
    if (id==="vault") return "SEALED / NOT UNLOCKED";
    if (id==="foundry") return "NOT CONNECTED";
    if (!state.live || !state.signals) return "NOT MEASURED";
    return state.signals.services?.[id] ?? "NOT MEASURED";
  };

  function resetCamera(){
    Object.assign(state,{yaw:.18,pitch:.28,zoom:1,panX:0,panY:0,layer:"ALL"});
    paintLayers();
  }

  function paintLayers(){
    const layers=$("layers");
    layers.replaceChildren();
    for(const layer of state.model.layers){
      const btn=document.createElement("button");
      btn.type="button";btn.className=layer===state.layer?"active":"";
      const caption=document.createElement("span");caption.textContent=layer;
      const count=document.createElement("small");
      count.textContent=String(layer==="ALL"?state.model.nodes.length:state.model.nodes.filter(n=>n.layer===layer).length);
      btn.append(caption,count);
      btn.addEventListener("click",()=>{
        state.layer=layer;
        if(layer!=="ALL" && byNode(state.selected)?.layer!==layer){
          state.selected=state.model.nodes.find(n=>n.layer===layer)?.id||"bio-core";
        }
        paintLayers();paintInspector();
      });
      layers.appendChild(btn);
    }
  }

  function choose(id){
    const node=byNode(id);if(!node)return;
    state.selected=node.id;
    if(state.layer!=="ALL" && node.layer!==state.layer){state.layer="ALL";paintLayers();}
    paintInspector();
  }

  function paintInspector(){
    const n=byNode(state.selected);if(!n)return;
    show("nodeTitle",n.name);
    show("nodeLayer",n.layer);
    show("nodeOrgan",n.organ);
    show("nodeEvidence",n.source_state==="main"?"SOURCE IN MAIN":n.source_state==="feature-branch"?"FEATURE BRANCH / NOT MERGED":n.source_state==="new-pr"?"NEW PROPOSED SOURCE":"CONCEPT ONLY");
    show("nodeSignal",statusFor(n.id));
    show("nodeSource",n.source);
    show("nodeDescription",n.description);
    const stateEl=$("nodeState");
    stateEl.textContent=n.source_state==="main"?"SOURCE DOCUMENTED":"NOT YET ON MAIN";
    stateEl.classList.toggle("main",n.source_state==="main");
    const edges=state.model.edges.filter(e=>e.from===n.id||e.to===n.id);
    const container=$("connections");container.replaceChildren();
    for(const edge of edges.slice(0,15)){
      const id=edge.from===n.id?edge.to:edge.from;
      const other=byNode(id);if(!other)continue;
      const btn=document.createElement("button");btn.type="button";
      btn.textContent=(other.name.length>22?other.name.slice(0,22)+"…":other.name)+" / "+edge.type.replaceAll("-"," ");
      btn.addEventListener("click",()=>choose(id));container.appendChild(btn);
    }
  }

  function paintTelemetry(){
    const container=$("services");container.replaceChildren();
    for(const id of SERVICES){
      const node=byNode(id);if(!node)continue;
      const btn=document.createElement("button");btn.type="button";
      const name=document.createElement("span");name.textContent=node.name.split(" ")[0];
      const value=statusFor(id);
      const status=document.createElement("em");status.textContent=value;
      status.className=value==="LISTENING"?"up":value==="OFFLINE"?"down":"unknown";
      btn.append(name,status);
      btn.addEventListener("click",()=>choose(id));
      container.appendChild(btn);
    }
    const mode=$("telemetryMode");
    mode.classList.toggle("live",state.live);
    mode.textContent=state.live?"LOCAL CL1 TELEMETRY / TCP PROBES":"PUBLIC STATIC ONTOLOGY / NOT LIVE";
    if(state.live && state.signals){
      const m=state.signals.host;
      show("hostMetrics",
        "LOCAL SAMPLE "+state.signals.timestamp_utc+" UTC"+
        " · HOST LOAD (1M): "+(m?.load_1m??"UNAVAILABLE")+
        " · CPU COUNT: "+(m?.logical_cpu_count??"UNAVAILABLE")+
        " · FREE DISK: "+(m?.disk_free_gb??"UNAVAILABLE")+" GiB"+
        ". TCP LISTENING does not verify process identity.");
    } else {
      show("hostMetrics","Public GitHub Pages cannot read private Mac telemetry. Run the optional local CL1 server to see actual loopback and host-load readings.");
    }
    paintInspector();
  }

  async function pollLocal(){
    if(!localOrigin)return;
    try{
      const r=await fetch("/api/telemetry",{cache:"no-store",credentials:"omit"});
      if(!r.ok)throw new Error("Local server not available");
      const p=await r.json();
      if(p.schema!=="xunia.cl1.local-telemetry.v1" || p.source!=="127.0.0.1" || p.public===true)throw new Error("Unknown telemetry schema");
      state.signals=p;state.live=true;
    }catch(_){state.signals=null;state.live=false;}
    paintTelemetry();
  }

  function setSize(){
    const rect=canvas.getBoundingClientRect();
    const dpr=Math.min(window.devicePixelRatio||1,2);
    state.w=Math.max(rect.width,40);state.h=Math.max(rect.height,40);
    canvas.width=Math.floor(state.w*dpr);canvas.height=Math.floor(state.h*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }

  function projected(n){
    // Treat all graph coordinates as untrusted data. One NaN must never blank
    // the entire nucleus or block selection and graph rendering.
    const [nx,ny,nz]=n.xyz.map(Number);
    const x=Number.isFinite(nx)?nx:0;
    const y=Number.isFinite(ny)?ny:0;
    const z=Number.isFinite(nz)?nz:0;
    const yaw=Number.isFinite(state.yaw)?state.yaw:0;
    const pitch=Number.isFinite(state.pitch)?state.pitch:0;
    const cosYaw=Math.cos(yaw), sinYaw=Math.sin(yaw);
    const cosPitch=Math.cos(pitch), sinPitch=Math.sin(pitch);
    let horizontal=x*cosYaw-z*sinYaw;
    const rotatedDepth=x*sinYaw+z*cosYaw;
    const yy=y*cosPitch-rotatedDepth*sinPitch;
    const depth=y*sinPitch+rotatedDepth*cosPitch;
    const scale=Math.min(state.w/22,state.h/14)*state.zoom;
    const perspective=1/Math.max(.7,1+depth*.018);
    if(!Number.isFinite(horizontal)) horizontal=x;
    const px=state.w/2+state.panX+horizontal*scale*perspective;
    const py=state.h/2+state.panY-yy*scale*.77*perspective;
    return {x:Number.isFinite(px)?px:state.w/2,
      y:Number.isFinite(py)?py:state.h/2,depth,node:n};
  }

  function drawMesh(){
    const w=state.w,h=state.h,t=state.frame;
    ctx.clearRect(0,0,w,h);
    for(let i=0;i<98;i++){
      const x=(i*217+53)%1009/1009*w,y=(i*151+29)%997/997*h;
      const shimmer=reduceMotion?.17:(.15+.13*Math.sin(t*.014+i));
      ctx.fillStyle="rgba(221,243,239,"+shimmer.toFixed(3)+")";
      ctx.fillRect(x,y,1.1,1.1);
    }
    const visible=state.model.nodes.filter(n=>state.layer==="ALL"||n.layer===state.layer);
    state.points=visible.map(projected);
    const positions=new Map(state.points.map(p=>[p.node.id,p]));
    const core=positions.get("bio-core");

    if(core){
      ctx.save();
      ctx.globalCompositeOperation="screen";
      const pulse=reduceMotion?1:1+.06*Math.sin(t*.036);
      for(let ring=0;ring<5;ring++){
        ctx.beginPath();ctx.ellipse(core.x,core.y,35*pulse+ring*18,27*pulse+ring*21,Math.sin(t*.003)*.22,0,Math.PI*2);
        ctx.strokeStyle="rgba(176,226,231,"+(.20-ring*.026)+")";ctx.lineWidth=1.2;ctx.stroke();
      }
      // Contracting tendrils are *simulated display geometry*, not biosignals.
      for(let arm=0;arm<13;arm++){
        const phase=arm*Math.PI*2/13;
        ctx.beginPath();
        for(let p=0;p<=44;p++){
          const u=p/44, radius=u*(86+24*pulse),angle=phase+.24*Math.sin(u*4+t*.009+arm);
          const x=core.x+radius*Math.cos(angle),y=core.y+radius*.66*Math.sin(angle);
          if(p===0)ctx.moveTo(x,y);else ctx.lineTo(x,y);
        }
        ctx.strokeStyle=arm%3===0?"rgba(211,201,245,.22)":"rgba(173,245,224,.19)";
        ctx.lineWidth=1.2;ctx.stroke();
      }
      const g=ctx.createRadialGradient(core.x,core.y,3,core.x,core.y,90);
      g.addColorStop(0,"rgba(213,250,242,.38)");g.addColorStop(.3,"rgba(133,222,208,.12)");g.addColorStop(1,"rgba(133,222,208,0)");
      ctx.fillStyle=g;ctx.beginPath();ctx.arc(core.x,core.y,90,0,Math.PI*2);ctx.fill();
      ctx.restore();
    }

    for(const edge of state.model.edges){
      const a=positions.get(edge.from),b=positions.get(edge.to);if(!a||!b)continue;
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
      ctx.strokeStyle="rgba(144,198,195,.22)";ctx.lineWidth=1;ctx.stroke();
      const time=reduceMotion?.4:(t*.0035+(edge.from.length+edge.to.length)*.09)%1;
      const x=a.x+(b.x-a.x)*time,y=a.y+(b.y-a.y)*time;
      ctx.fillStyle="rgba(214,250,241,.7)";ctx.beginPath();ctx.arc(x,y,1.9,0,Math.PI*2);ctx.fill();
    }
    for(const p of state.points.slice().sort((a,b)=>b.depth-a.depth)){
      const selected=p.node.id===state.selected, color=COLORS[p.node.layer]||"#b3cbd0";
      ctx.shadowColor=color;ctx.shadowBlur=selected?22:12;
      ctx.beginPath();ctx.arc(p.x,p.y,selected?9.5:5.7,0,Math.PI*2);
      ctx.strokeStyle=selected?"#fff":color;ctx.lineWidth=selected?2.2:1;ctx.stroke();
      ctx.shadowBlur=0;ctx.beginPath();ctx.arc(p.x,p.y,selected?4.2:2.8,0,Math.PI*2);ctx.fillStyle=color;ctx.fill();
      if(state.labels){
        const text=p.node.name.length>19?p.node.name.slice(0,19)+"…":p.node.name;
        ctx.font=(selected?"bold 11px":"10px")+" ui-monospace,Menlo,monospace";
        p.labelWidth=ctx.measureText(text).width+16;
        ctx.fillStyle=selected?"rgba(15,39,37,.97)":"rgba(9,23,25,.82)";
        ctx.fillRect(p.x+10,p.y-12,p.labelWidth,23);
        ctx.textAlign="left";ctx.textBaseline="middle";
        ctx.fillStyle=color;ctx.fillText(text,p.x+18,p.y);
      } else p.labelWidth=0;
    }
    // Expose a non-sensitive renderer health marker for real-browser smoke tests.
    // It represents frame rendering, never the state of external services.
    canvas.dataset.renderedNodes = String(state.points.length);
    canvas.dataset.renderedEdges = String(state.model.edges.length);
    canvas.dataset.renderFrames = String(state.frame + 1);
    show("camera","ORBIT "+Math.round(state.yaw*180/Math.PI)+"° / TILT "+Math.round(state.pitch*180/Math.PI)+"° / ZOOM "+state.zoom.toFixed(2));
    state.frame++;
    if(!reduceMotion && !state.disposed)requestAnimationFrame(drawMesh);
  }

  function nearest(x,y){
    let best=null,score=Infinity;
    for(const p of state.points){
      const dx=x-p.x,dy=y-p.y,d=Math.hypot(dx,dy);
      const inLabel=state.labels && dx>=9 && dx<=12+p.labelWidth && Math.abs(dy)<=12;
      if((d<23||inLabel)&&d<score){score=d;best=p.node;}
    }
    return best;
  }
  function xy(e){const r=canvas.getBoundingClientRect();return{x:e.clientX-r.left,y:e.clientY-r.top};}
  canvas.addEventListener("pointerdown",e=>{
    if(e.button!==0)return;
    const p=xy(e);state.drag={...p};
    canvas.setPointerCapture(e.pointerId);
    const n=nearest(p.x,p.y);if(n)choose(n.id);
    canvas.focus();
  });
  canvas.addEventListener("pointermove",e=>{
    if(!state.drag)return;
    const p=xy(e),dx=p.x-state.drag.x,dy=p.y-state.drag.y;
    if(Math.abs(dx)+Math.abs(dy)>1){
      state.yaw+=dx*.008;state.pitch=clamp(state.pitch-dy*.006,-1.2,1.2);
      state.drag=p;if(reduceMotion)drawMesh();
    }
  });
  for(const event of ["pointerup","pointercancel","lostpointercapture"]){
    canvas.addEventListener(event,()=>{state.drag=null;});
  }
  canvas.addEventListener("wheel",e=>{
    e.preventDefault();state.zoom=clamp(state.zoom*(e.deltaY<0?1.10:.91),.45,3);
    if(reduceMotion)drawMesh();
  },{passive:false});
  canvas.addEventListener("keydown",e=>{
    if(e.key==="ArrowLeft")state.yaw-=.16;
    else if(e.key==="ArrowRight")state.yaw+=.16;
    else if(e.key==="ArrowUp")state.pitch=clamp(state.pitch+.10,-1.2,1.2);
    else if(e.key==="ArrowDown")state.pitch=clamp(state.pitch-.10,-1.2,1.2);
    else if(e.key==="+"||e.key==="=")state.zoom=clamp(state.zoom*1.12,.45,3);
    else if(e.key==="-")state.zoom=clamp(state.zoom/1.12,.45,3);
    else if(e.key==="Tab"){
      const visible=state.model.nodes.filter(n=>state.layer==="ALL"||n.layer===state.layer);
      choose(visible[(visible.findIndex(n=>n.id===state.selected)+1)%visible.length].id);
    }else return;
    e.preventDefault();if(reduceMotion)drawMesh();
  });
  for(const button of document.querySelectorAll("[data-view]")){
    button.addEventListener("click",()=>{
      const action=button.dataset.view;
      if(action==="left")state.yaw-=.2;
      if(action==="right")state.yaw+=.2;
      if(action==="zoomout")state.zoom=clamp(state.zoom/1.16,.45,3);
      if(action==="zoomin")state.zoom=clamp(state.zoom*1.16,.45,3);
      if(action==="reset")resetCamera();
      if(action==="labels")state.labels=!state.labels;
      if(reduceMotion)drawMesh();
    });
  }
  $("refreshStatus").addEventListener("click",()=>{pollLocal();});
  $("find").addEventListener("input",e=>{
    const q=e.target.value.trim().toLowerCase();if(!q)return;
    const n=state.model.nodes.find(n=>n.name.toLowerCase().includes(q)||n.id.includes(q)||n.organ.includes(q));
    if(n)choose(n.id);
  });

  async function loadGenome(){
    const status=$("genomeStatus");
    status.textContent="Loading the dated public GitHub repository snapshot…";
    try{
      const r=await fetch("../ecosystem-observatory/snapshot.json",{cache:"no-store",credentials:"omit"});
      if(!r.ok)throw new Error("source unavailable");
      const p=await r.json();
      if(!Array.isArray(p.repositories)||typeof p.snapshotDate!=="string")throw new Error("invalid source");
      state.genome=p;state.genomeSearch="";
      $("genomeSearch").disabled=false;
      $("openGenome").disabled=true;
      paintGenome();
    }catch(_){status.textContent="Public repository snapshot not available. No private repositories were queried.";}
  }
  function paintGenome(){
    const box=$("genomeResults");box.replaceChildren();
    const p=state.genome;if(!p)return;
    const q=$("genomeSearch").value.trim().toLowerCase();
    const filtered=p.repositories.filter(item=>{
      return [item.id,item.name,item.category].some(v=>String(v||"").toLowerCase().includes(q));
    });
    $("genomeStatus").textContent="SNAPSHOT "+p.snapshotDate+" / "+filtered.length+" matching of "+p.repositories.length+" public repository records. Static evidence; not live runtime integration.";
    for(const item of filtered.slice(0,120)){
      const id=String(item.id||"");const uri=String(item.url||"");
      if(!/^https:\/\/github\.com\/sonoxo\/[A-Za-z0-9_.-]+$/.test(uri))continue;
      const a=document.createElement("a");a.href=uri;a.target="_blank";a.rel="noopener noreferrer";
      const title=document.createElement("strong");title.textContent=id;
      const sub=document.createElement("small");sub.textContent=String(item.category||"Unclassified")+" · "+String(item.classificationBasis||"not verified");
      a.append(title,sub);box.appendChild(a);
    }
  }
  $("openGenome").addEventListener("click",loadGenome);
  $("genomeSearch").addEventListener("input",paintGenome);

  async function boot(){
    if(!ctx){show("telemetryMode","CANVAS UNAVAILABLE");return;}
    try{
      const r=await fetch("./ontology.json",{credentials:"omit",cache:"no-store"});
      if(!r.ok)throw new Error("ontology missing");
      const data=await r.json();
      if(data.schema!=="xunia.cl1.biological-data-center.v1"||
        !Array.isArray(data.nodes)||!Array.isArray(data.edges)||!Array.isArray(data.layers)){
        throw new Error("unsupported ontology");
      }
      state.model=data;
      show("nodeCount",data.nodes.length);
      show("edgeCount",data.edges.length);
      paintLayers();paintInspector();paintTelemetry();setSize();drawMesh();
      window.addEventListener("resize",()=>{setSize();if(reduceMotion)drawMesh();});
      if(localOrigin){pollLocal();setInterval(pollLocal,6000);}
    }catch(error){
      // Never disguise a broken Canvas as a healthy interactive data center.
      // Publicly display only the category; details stay in the browser console.
      console.error("XUNIA CL1: spatial initialization failed", error);
      // Diagnostics contain only a bounded JS error class/message, not any
      // local telemetry or account data. Needed to debug real browser issues.
      canvas.dataset.renderFailure = (String(error?.name||"Error")+": "+
        String(error?.message||"unknown")).slice(0,180);
      show("telemetryMode","SPATIAL RENDER FAILED — OPEN BROWSER CONSOLE");
      show("hostMetrics","Architecture unavailable; local telemetry was not altered.");
    }
  }
  window.addEventListener("pagehide",()=>{state.disposed=true;});
  boot();
})();
