/* XUNIA COSMOS / CL1 // no-key astronomy catalog spatial explorer.
 * All positions are schematic, NOT true-to-scale or navigation-safe.
 * No browser egress to NASA/ESA; optional imports are pre-generated local files.
 */
(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const canvas = $("space");
  const ctx = canvas?.getContext("2d");
  const reduced = !!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
  const SECTORS = {
    STRUCTURES: "#dbe8f1", GALAXIES:"#c8c1ed", BLACK_HOLES:"#e1e1ed",
    SOLAR_SYSTEM:"#b4f0e2", STARS:"#f6dfb9", EXOPLANETS:"#88d9ea",
    NEBULAE:"#d7a7c9", MISSIONS:"#b2c8d7"
  };
  const CATALOGS = [
    ["nasa","./catalogs/nasa.json","nasaStatus"],
    ["gaia","./catalogs/gaia.json","gaiaStatus"]
  ];
  const MAX_DRAW = 1500, MAX_EDGES = 2200;
  const clamp = (a,lo,hi) => Math.max(lo,Math.min(hi,a));
  const number = (x,d=0) => Number.isFinite(Number(x)) ? Number(x) : d;
  const state = {
    nodes:[],edges:[],nodeById:new Map(),selected:"universe",
    sector:"ALL",yaw:.22,pitch:.22,zoom:1,panX:0,panY:0,
    width:800,height:500,points:[],drag:null,labels:true,frame:0,
    canvasValid:false,loaded:false,quiet:false,
    nkMode:"observe",nkPower:50,nkPaused:false,nkTick:0
  };
  const show = (id,text) => { const e=$(id); if(e)e.textContent=String(text); };
  function fail(message) {
    console.error("XUNIA COSMOS",message);
    show("canvasNotice","SPATIAL RENDER FAILED / "+String(message).slice(0,95));
    if(canvas)canvas.dataset.renderFailure=String(message).slice(0,155);
    state.quiet=true;
  }
  function mergeCatalog(data,category){
    if(!data || data.schema!=="xunia.cosmos.catalog.v1" ||
      !Array.isArray(data.nodes) || !Array.isArray(data.edges))throw Error("Invalid "+category+" catalog schema");
    for(const node of data.nodes.slice(0,6000)){
      if(!node || typeof node.id!=="string" || node.id.length>110 ||
         typeof node.name!=="string" || node.name.length>170 ||
         typeof node.sector!=="string" || !Array.isArray(node.layout) ||
         node.layout.length!==3 || state.nodeById.has(node.id))continue;
      const entry={...node,
        layout:node.layout.map(x=>number(x,0)),source_catalog:category};
      if(entry.layout.some(x=>!Number.isFinite(x)))continue;
      state.nodeById.set(entry.id,entry);
      state.nodes.push(entry);
    }
    const valid=new Set(state.nodeById.keys());
    const seen=new Set(state.edges.map(e=>e.source+"|"+e.target));
    for(const edge of data.edges.slice(0,10000)){
      if(!edge || !valid.has(edge.source) || !valid.has(edge.target) ||
        edge.source===edge.target)continue;
      const key=edge.source+"|"+edge.target;
      if(!seen.has(key)){state.edges.push({
        source:edge.source,target:edge.target,
        relation:String(edge.relation||"related").slice(0,90)
      });seen.add(key);}
    }
  }
  function selectedNode(){return state.nodeById.get(state.selected);}
  function visibleNodes(){
    const candidates=state.nodes.filter(n=>state.sector==="ALL"||n.sector===state.sector);
    // Core seed nodes remain in front of large imported catalog subsets.
    return candidates.slice(0,MAX_DRAW);
  }
  function updateStats(){
    show("visibleCount",visibleNodes().length+" / "+state.nodes.length);
    show("edgeCount",state.edges.length);
  }
  function layers(){
    const box=$("sectorFilters");box.replaceChildren();
    const sectors=["ALL",...Object.keys(SECTORS)];
    for(const sector of sectors){
      const b=document.createElement("button");b.type="button";
      b.className=sector===state.sector?"active":"";
      const caption=document.createElement("span");caption.textContent=sector.replaceAll("_"," ");
      const count=document.createElement("small");
      count.textContent=String(sector==="ALL"?state.nodes.length:state.nodes.filter(n=>n.sector===sector).length);
      b.append(caption,count);
      b.addEventListener("click",()=>{
        state.sector=sector;
        if(sector!=="ALL" && selectedNode()?.sector!==sector){
          state.selected=state.nodes.find(n=>n.sector===sector)?.id||"universe";
        }
        layers();inspect();updateStats();if(reduced)draw();
      });
      box.appendChild(b);
    }
  }
  function safeSource(url) {
    try {
      const u=new URL(url);
      return u.protocol==="https:" &&
        ["science.nasa.gov","exoplanetarchive.ipac.caltech.edu",
         "gea.esac.esa.int","ssd-api.jpl.nasa.gov"].includes(u.hostname);
    }catch(_){return false;}
  }
  function choose(id){
    if(!state.nodeById.has(id))return;
    state.selected=id;
    if(state.sector!=="ALL" && selectedNode()?.sector!==state.sector){
      state.sector="ALL";layers();
    }
    inspect();if(reduced)draw();
  }
  function inspect(){
    const node=selectedNode();if(!node)return;
    show("objectKind",node.sector.replaceAll("_"," "));
    show("objectName",node.name);
    show("objectDescription",node.description||"Catalog record; consult source for details.");
    show("objectEvidence",node.evidence||"Source labeled; no live telemetry");
    show("objectParent",node.parent?(state.nodeById.get(node.parent)?.name||node.parent):"None / context root");
    show("objectRA",Number.isFinite(node.ra_deg)?node.ra_deg.toFixed(4)+"°":"Not recorded");
    show("objectDec",Number.isFinite(node.dec_deg)?node.dec_deg.toFixed(4)+"°":"Not recorded");
    const pc = node.distance_pc??node.distance_pc_estimate;
    show("objectDistance",Number.isFinite(pc)?pc+" parsecs (catalog / approximate)":"Not recorded");
    const a=$("objectSource");
    if(safeSource(node.source_url)){
      a.href=node.source_url;a.hidden=false;
      a.textContent="VIEW "+(node.source_label||"OFFICIAL SOURCE").toUpperCase()+" ↗";
    }else{a.hidden=true;}
    const neighbors=$("neighbors");neighbors.replaceChildren();
    const adjacent=state.edges.filter(e=>e.source===node.id||e.target===node.id).slice(0,35);
    if(adjacent.length===0){const text=document.createElement("span");text.textContent="No explicit relationships in current subset.";neighbors.appendChild(text);}
    for(const edge of adjacent){
      const other=state.nodeById.get(edge.source===node.id?edge.target:edge.source);
      if(!other)continue;
      const b=document.createElement("button");b.type="button";
      b.textContent=other.name+" / "+edge.relation;
      b.addEventListener("click",()=>choose(other.id));neighbors.appendChild(b);
    }
  }
  function search(){
    const term=$("search").value.trim().toLowerCase();
    const box=$("searchResults");box.replaceChildren();
    if(!term)return;
    const matches=state.nodes.filter(n=>
      n.name.toLowerCase().includes(term) || n.id.toLowerCase().includes(term)
    ).slice(0,10);
    for(const node of matches){
      const b=document.createElement("button");b.type="button";
      b.textContent=node.name+" · "+node.sector.replaceAll("_"," ");
      b.addEventListener("click",()=>{choose(node.id);focus();});
      box.appendChild(b);
    }
    if(!matches.length){
      const msg=document.createElement("span");msg.textContent="No match in imported/curated subset.";
      box.appendChild(msg);
    }
  }
  function resize(){
    const r=canvas.getBoundingClientRect();
    state.width=Math.max(40,r.width);state.height=Math.max(40,r.height);
    const dpr=Math.min(window.devicePixelRatio||1,2);
    canvas.width=Math.round(state.width*dpr);canvas.height=Math.round(state.height*dpr);
    ctx.setTransform(dpr,0,0,dpr,0,0);
  }
  function project(n){
    const coords=Array.isArray(n.layout)?n.layout:[0,0,0];
    const [x,y,z]=coords.map(v=>number(v,0));
    const yaw=number(state.yaw,0),pitch=number(state.pitch,0);
    const horiz=x*Math.cos(yaw)-z*Math.sin(yaw);
    const depth1=x*Math.sin(yaw)+z*Math.cos(yaw);
    const vertical=y*Math.cos(pitch)-depth1*Math.sin(pitch);
    const depth=y*Math.sin(pitch)+depth1*Math.cos(pitch);
    const scale=Math.min(state.width/28,state.height/21)*number(state.zoom,1);
    const perspective=1/Math.max(.6,1+depth*.015);
    const px=state.width/2+state.panX+horiz*scale*perspective;
    const py=state.height/2+state.panY-vertical*scale*.85*perspective;
    return {node:n,
      x:Number.isFinite(px)?px:state.width/2,
      y:Number.isFinite(py)?py:state.height/2,
      depth:Number.isFinite(depth)?depth:0};
  }
  function sphere(p,r,color,selected){
    ctx.save();ctx.shadowColor=color;ctx.shadowBlur=selected?22:10;
    ctx.beginPath();ctx.arc(p.x,p.y,r,0,2*Math.PI);
    ctx.strokeStyle=selected?"#f8ffff":color;ctx.lineWidth=selected?2.6:1.2;ctx.stroke();
    ctx.shadowBlur=0;
    ctx.beginPath();ctx.arc(p.x,p.y,selected?3.7:2.2,0,2*Math.PI);
    ctx.fillStyle=color;ctx.fill();
    ctx.restore();
  }

  // Illustrative geometry only: neither measured fields nor actual signals.
  function drawNonKinetic(lookup){
    if(state.nkMode==="observe" || state.nkPower===0)return;
    const p=lookup.get(state.selected);
    if(!p)return;
    const power=state.nkPower/100;
    const radius=28+75*power;
    const time=(state.nkPaused?state.nkTick:(state.nkTick=state.frame))*.035;
    ctx.save();
    ctx.lineWidth=1.3;
    if(state.nkMode==="signal"){
      for(let i=0;i<4;i++){
        const spread=((time*.36+i/4)%1);
        ctx.beginPath();ctx.arc(p.x,p.y,14+radius*spread,0,2*Math.PI);
        ctx.strokeStyle="rgba(131,241,219,"+(0.55*(1-spread)).toFixed(3)+")";ctx.stroke();
      }
      let linked=0;
      for(const edge of state.edges){
        if(linked>=30)break;
        const id=edge.source===state.selected?edge.target:
          edge.target===state.selected?edge.source:null;
        const other=id&&lookup.get(id);if(!other)continue;
        linked++;
        ctx.beginPath();ctx.moveTo(p.x,p.y);ctx.lineTo(other.x,other.y);
        ctx.strokeStyle="rgba(137,241,224,.48)";ctx.stroke();
        const phase=(time*.3+linked*.16)%1;
        ctx.beginPath();ctx.arc(p.x+(other.x-p.x)*phase,p.y+(other.y-p.y)*phase,2.7,0,2*Math.PI);
        ctx.fillStyle="#b0fbed";ctx.fill();
      }
    }else if(state.nkMode==="gravity"){
      for(let i=0;i<5;i++){
        const rad=20+i*radius/5;
        ctx.beginPath();ctx.ellipse(p.x,p.y,rad,rad*.58,time*.045+i*.16,0,2*Math.PI);
        ctx.strokeStyle="rgba(202,196,244,"+(0.58-i*.075).toFixed(3)+")";ctx.stroke();
      }
      ctx.beginPath();ctx.arc(p.x,p.y,12+power*10,0,Math.PI*2);
      ctx.strokeStyle="rgba(238,230,255,.75)";ctx.lineWidth=2;ctx.stroke();
    }else if(state.nkMode==="field"){
      for(let i=0;i<16;i++){
        const angle=(Math.PI*2*i)/16+time*.015;
        const inner=11,outer=radius+24;
        const x1=p.x+inner*Math.cos(angle),y1=p.y+inner*Math.sin(angle);
        const x2=p.x+outer*Math.cos(angle),y2=p.y+outer*Math.sin(angle);
        const bend=(i%2===0?1:-1)*outer*.32;
        ctx.beginPath();ctx.moveTo(x1,y1);
        ctx.quadraticCurveTo(p.x+(outer*.56)*Math.cos(angle+.3)+bend*.16,
          p.y+(outer*.56)*Math.sin(angle+.3)-bend*.16,x2,y2);
        ctx.strokeStyle="rgba(138,204,255,.51)";ctx.stroke();
        ctx.beginPath();ctx.arc(x2,y2,1.5,0,2*Math.PI);
        ctx.fillStyle="#b7ebff";ctx.fill();
      }
    }
    ctx.restore();
  }

  function draw(){
    if(!ctx||!state.loaded||state.quiet)return;
    try{
      ctx.clearRect(0,0,state.width,state.height);
      const t=state.frame;
      // Deterministic, non-measured background starfield.
      for(let i=0;i<160;i++){
        const x=((i*1877+101)%991)/991*state.width;
        const y=((i*601+29)%983)/983*state.height;
        const flicker=reduced?.20:(.20+.16*Math.sin(i+t*.009));
        ctx.fillStyle="rgba(206,231,243,"+flicker.toFixed(3)+")";
        ctx.fillRect(x,y,1+(i%7===0),1+(i%7===0));
      }
      const nodes=visibleNodes();
      state.points=nodes.map(project);
      const lookup=new Map(state.points.map(p=>[p.node.id,p]));
      const root=lookup.get("universe")||lookup.get("solar-system");
      if(root){
        const rx=Number.isFinite(root.x)?root.x:state.width/2;
        const ry=Number.isFinite(root.y)?root.y:state.height/2;
        ctx.save();
        const g=ctx.createRadialGradient(rx,ry,3,rx,ry,180);
        g.addColorStop(0,"rgba(217,251,247,.14)");
        g.addColorStop(.40,"rgba(161,201,238,.065)");
        g.addColorStop(1,"rgba(117,167,207,0)");
        ctx.fillStyle=g;ctx.beginPath();ctx.arc(rx,ry,180,0,Math.PI*2);ctx.fill();
        for(let ring=0;ring<5;ring++){
          ctx.beginPath();ctx.ellipse(rx,ry,39+ring*30,27+ring*18,
            reduced?0:t*.0007,0,2*Math.PI);
          ctx.lineWidth=1;ctx.strokeStyle="rgba(171,222,219,"+(.18-ring*.027)+")";ctx.stroke();
        }
        ctx.restore();
      }
      let drawnEdges=0;
      for(const edge of state.edges){
        if(drawnEdges>=MAX_EDGES)break;
        const a=lookup.get(edge.source),b=lookup.get(edge.target);if(!a||!b)continue;
        drawnEdges++;
        ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
        ctx.lineWidth=.85;ctx.strokeStyle="rgba(146,184,201,.25)";ctx.stroke();
        if(!reduced){
          const phase=(t*.003+edge.source.length*.07+edge.target.length*.05)%1;
          ctx.fillStyle="#8ce4d5";ctx.globalAlpha=.52;
          ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*phase,a.y+(b.y-a.y)*phase,1.4,0,2*Math.PI);ctx.fill();
          ctx.globalAlpha=1;
        }
      }
      drawNonKinetic(lookup);
      const selected=state.selected;
      const showCount=state.points.length<=80?50:15;
      const labelCandidates=state.points.slice(0,showCount);
      if(!labelCandidates.some(p=>p.node.id===selected)){
        const found=lookup.get(selected);if(found)labelCandidates.push(found);
      }
      const labelIds=new Set(labelCandidates.map(p=>p.node.id));
      for(const p of state.points.slice().sort((a,b)=>b.depth-a.depth)){
        const focus=p.node.id===selected;
        const col=SECTORS[p.node.sector]||"#d0e0e8";
        sphere(p,focus?8.0:Math.max(2.8,3.5*Math.min(state.zoom,1.7)),col,focus);
        if(state.labels && labelIds.has(p.node.id)){
          const label=p.node.name.length>22?p.node.name.slice(0,22)+"…":p.node.name;
          ctx.font=(focus?"bold 11px":"10px")+" Menlo,Consolas,monospace";
          const labelWidth=ctx.measureText(label).width+12;
          p.labelWidth=labelWidth;
          ctx.fillStyle=focus?"rgba(16,40,50,.96)":"rgba(9,22,32,.85)";
          ctx.fillRect(p.x+8,p.y-11,labelWidth,22);
          ctx.fillStyle=col;ctx.textAlign="left";ctx.textBaseline="middle";
          ctx.fillText(label,p.x+14,p.y);
        }else{p.labelWidth=0;}
      }
      canvas.dataset.renderedNodes=String(state.points.length);
      canvas.dataset.renderedEdges=String(drawnEdges);
      canvas.dataset.renderFrames=String(state.frame+1);
      canvas.dataset.renderFailure="";
      show("camera","YAW "+Math.round(state.yaw*180/Math.PI)+"° / PITCH "+Math.round(state.pitch*180/Math.PI)+"° / ZOOM "+state.zoom.toFixed(2));
      state.frame++;
      if(!reduced)window.requestAnimationFrame(draw);
    }catch(error){fail(error?.name+": "+error?.message);}
  }
  function nearest(x,y){
    let found=null,best=Infinity;
    for(const p of state.points){
      const dx=x-p.x,dy=y-p.y,d=Math.hypot(dx,dy);
      const label=state.labels && dx>7 && dx<10+(p.labelWidth||0) && Math.abs(dy)<12;
      if((d<18||label)&&d<best){best=d;found=p.node;}
    }
    return found;
  }
  function focus(){
    const node=selectedNode();if(!node)return;
    const p=project(node);
    state.panX+=state.width/2-p.x;state.panY+=state.height/2-p.y;
    if(reduced)draw();
  }
  function toolbar(action){
    if(action==="left")state.yaw-=.19;
    if(action==="right")state.yaw+=.19;
    if(action==="zoomout")state.zoom=clamp(state.zoom/1.17,.38,4);
    if(action==="zoomin")state.zoom=clamp(state.zoom*1.17,.38,4);
    if(action==="reset")Object.assign(state,{yaw:.22,pitch:.22,zoom:1,panX:0,panY:0,sector:"ALL"});
    if(action==="focus")focus();
    if(action==="labels")state.labels=!state.labels;
    layers();updateStats();
    if(reduced)draw();
  }
  function pointerXY(e){
    const r=canvas.getBoundingClientRect();
    return {x:e.clientX-r.left,y:e.clientY-r.top};
  }
  canvas.addEventListener("pointerdown",e=>{
    if(e.button!==0)return;
    const p=pointerXY(e);state.drag=p;
    canvas.setPointerCapture(e.pointerId);
    const node=nearest(p.x,p.y);if(node)choose(node.id);
    canvas.focus();
  });
  canvas.addEventListener("pointermove",e=>{
    if(!state.drag)return;
    const p=pointerXY(e),dx=p.x-state.drag.x,dy=p.y-state.drag.y;
    if(dx||dy){
      state.yaw+=dx*.008;
      state.pitch=clamp(state.pitch-dy*.006,-1.2,1.2);
      state.drag=p;if(reduced)draw();
    }
  });
  for(const ev of ["pointerup","pointercancel","lostpointercapture"]){
    canvas.addEventListener(ev,()=>{state.drag=null;});
  }
  canvas.addEventListener("wheel",e=>{
    e.preventDefault();state.zoom=clamp(state.zoom*(e.deltaY<0?1.1:.9),.38,4);
    if(reduced)draw();
  },{passive:false});
  canvas.addEventListener("keydown",e=>{
    const k=e.key;
    if(k==="ArrowLeft")state.yaw-=.14;
    else if(k==="ArrowRight")state.yaw+=.14;
    else if(k==="ArrowUp")state.pitch=clamp(state.pitch+.11,-1.2,1.2);
    else if(k==="ArrowDown")state.pitch=clamp(state.pitch-.11,-1.2,1.2);
    else if(k==="+"||k==="=")state.zoom=clamp(state.zoom*1.1,.38,4);
    else if(k==="-")state.zoom=clamp(state.zoom/1.1,.38,4);
    else if(k==="Enter")focus();
    else if(k==="Tab"){
      const all=visibleNodes();
      const index=all.findIndex(n=>n.id===state.selected);
      if(all.length)choose(all[(index+1)%all.length].id);
    }else if(k==="/"){$("search").focus();}
    else return;
    e.preventDefault();if(reduced)draw();
  });
  document.querySelectorAll("[data-cam]").forEach(b=>{
    b.addEventListener("click",()=>toolbar(b.dataset.cam));
  });
  $("search").addEventListener("input",search);
  $("catalogInfo").addEventListener("click",()=>{
    const p=$("importHelp");p.classList.toggle("hidden");
    $("catalogInfo").textContent=p.classList.contains("hidden")?"HOW TO IMPORT MORE DATA":"HIDE IMPORT INSTRUCTIONS";
  });

  function labMessage(message){show("nkStatus",message);}
  function setMode(mode){
    if(!["observe","signal","gravity","field"].includes(mode))return false;
    state.nkMode=mode;
    document.querySelectorAll("[data-nk-mode]").forEach(b=>{
      b.setAttribute("aria-pressed",String(b.dataset.nkMode===mode));
    });
    labMessage(mode.toUpperCase()+" / simulated scene effect · no real-world output");
    if(reduced)draw();
    return true;
  }
  function setFieldPower(value){
    const n=Number(value);
    if(!Number.isFinite(n)||n<0||n>100)return false;
    state.nkPower=n;
    $("nkPower").value=String(n);
    show("nkPowerValue",Math.round(n)+"%");
    if(reduced)draw();
    return true;
  }
  function setFieldPaused(paused){
    state.nkPaused=paused;
    if(!paused)state.nkTick=state.frame;
    $("nkPause").textContent=paused?"RESUME FIELD":"PAUSE FIELD";
    $("nkPause").setAttribute("aria-pressed",String(paused));
    labMessage(paused?"FIELD FROZEN / software-only scene":"FIELD PLAYING / software-only scene");
    if(reduced)draw();
  }
  function runNonKineticCommand(raw){
    const line=String(raw||"").trim().replace(/^\//,"");
    if(!line){labMessage("EMPTY COMMAND / try /help");return;}
    const firstSpace=line.indexOf(" ");
    const command=(firstSpace<0?line:line.slice(0,firstSpace)).toLowerCase();
    const arg=(firstSpace<0?"":line.slice(firstSpace+1)).trim();
    if(command==="help"){
      labMessage("/go NAME · /mode observe|signal|gravity|field · /orbit DEGREES · /zoom 0.38–4 · /power 0–100 · /filter SECTOR · /pause · /play · /reset");
    }else if(command==="go"){
      const name=arg.toLowerCase();
      const node=name&&state.nodes.find(n=>n.name.toLowerCase()===name) ||
        (name&&state.nodes.find(n=>n.name.toLowerCase().includes(name)||n.id.toLowerCase()===name));
      if(!node){labMessage("NOT FOUND / choose a cataloged object");return;}
      choose(node.id);focus();labMessage("FOCUSED "+node.name+" / simulated camera");
    }else if(command==="mode"){
      if(!setMode(arg.toLowerCase()))labMessage("INVALID MODE / observe, signal, gravity, field");
    }else if(command==="orbit"){
      const deg=Number(arg);
      if(!arg||!Number.isFinite(deg)||Math.abs(deg)>360){labMessage("ORBIT RANGE / −360 to +360 degrees");return;}
      state.yaw+=deg*Math.PI/180;labMessage("CAMERA ORBIT / "+deg+"°");
    }else if(command==="zoom"){
      const zoom=Number(arg);
      if(!arg||!Number.isFinite(zoom)||zoom<.38||zoom>4){labMessage("ZOOM RANGE / 0.38 to 4");return;}
      state.zoom=zoom;labMessage("CAMERA ZOOM / "+zoom.toFixed(2));
    }else if(command==="power"){
      if(!arg||!setFieldPower(arg)){labMessage("FIELD INTENSITY / 0 to 100");return;}
      labMessage("VIRTUAL INTENSITY / "+Math.round(state.nkPower)+"%");
    }else if(command==="filter"){
      const sector=arg.toUpperCase().replace(/[\s-]+/g,"_");
      if(sector!=="ALL"&&!Object.hasOwn(SECTORS,sector)){
        labMessage("UNKNOWN SECTOR / choose one of the domain filters");return;
      }
      state.sector=sector;
      if(sector!=="ALL"&&selectedNode()?.sector!==sector){
        state.selected=state.nodes.find(n=>n.sector===sector)?.id||"universe";
      }
      layers();inspect();updateStats();labMessage("FILTER / "+sector.replaceAll("_"," "));
    }else if(command==="pause"){setFieldPaused(true);
    }else if(command==="play"){setFieldPaused(false);
    }else if(command==="reset"){
      toolbar("reset");setMode("observe");setFieldPower(50);setFieldPaused(false);
      labMessage("RESET / scene and non-kinetic controls");
    }else{labMessage("UNKNOWN COMMAND / enter /help");}
    if(reduced)draw();
  }
  function wireNonKineticLab(){
    document.querySelectorAll("[data-nk-mode]").forEach(button=>
      button.addEventListener("click",()=>setMode(button.dataset.nkMode)));
    $("nkPower").addEventListener("input",event=>{
      setFieldPower(event.target.value);
      labMessage("VIRTUAL INTENSITY / "+Math.round(state.nkPower)+"%");
    });
    $("nkPause").addEventListener("click",()=>setFieldPaused(!state.nkPaused));
    $("nkForm").addEventListener("submit",event=>{
      event.preventDefault();
      runNonKineticCommand($("nkCommand").value);
      $("nkCommand").value="";
    });
    document.addEventListener("keydown",event=>{
      const edit=/^(INPUT|TEXTAREA)$/.test(document.activeElement?.tagName||"");
      if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==="k"){
        event.preventDefault();$("nkCommand").focus();
      }else if(event.key==="Escape"&&document.activeElement===$("nkCommand")){
        event.preventDefault();canvas.focus();
      }else if(event.key==="/"&&!edit&&!event.ctrlKey&&!event.metaKey){
        event.preventDefault();$("nkCommand").focus();
      }
    });
  }
  wireNonKineticLab();

  async function loadOptional(name,url,statusId){
    try{
      const r=await fetch(url,{cache:"no-store",credentials:"omit"});
      if(!r.ok)throw Error("not imported");
      const catalog=await r.json();
      const before=state.nodes.length;
      mergeCatalog(catalog,name);
      show(statusId,(state.nodes.length-before)+" RECORDS LOADED");
    }catch(_){
      show(statusId,"NOT IMPORTED / OPTIONAL");
    }
  }
  async function boot(){
    if(!ctx){show("canvasNotice","2D CANVAS NOT AVAILABLE IN THIS BROWSER");return;}
    try{
      const r=await fetch("./catalogs/seed.json",{cache:"no-store",credentials:"omit"});
      if(!r.ok)throw Error("curated ontology missing");
      const seed=await r.json();
      mergeCatalog(seed,"curated");
      if(!state.nodeById.has("universe"))throw Error("missing cosmic root");
      show("seedCount",seed.nodes.length);
      await Promise.all(CATALOGS.map(([name,url,id])=>loadOptional(name,url,id)));
      state.loaded=true;
      layers();inspect();updateStats();resize();draw();
      window.addEventListener("resize",()=>{resize();if(reduced)draw();});
      show("canvasNotice","SCHEMATIC 3D / "+state.nodes.length+" CATALOGED OBJECTS LOADED / NOT TO SCALE");
    }catch(error){fail(error?.name+": "+error?.message);}
  }
  $("refreshCatalogs").addEventListener("click",async()=>{
    for(const [name,url,id] of CATALOGS)await loadOptional(name,url,id);
    layers();updateStats();if(reduced)draw();
  });
  boot();
})();