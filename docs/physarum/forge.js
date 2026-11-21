/* XUNIA Physarum Forge: visual + SVG physicalization of an original,
 * qualitative, Tero-inspired adaptive transport model. No living culture,
 * neural interface or hardware actuation. Only local static JSON is fetched.
 */
(()=>{
"use strict";
const $=id=>document.getElementById(id),M=window.PhysarumModel,TAU=Math.PI*2;
const clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const canvas=$("physarumCanvas"),ctx=canvas?.getContext("2d"),plot=$("telemetryCanvas"),pctx=plot?.getContext("2d");
const state={graph:null,ontology:null,mode:"food",active:!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
 speed:48,showTrail:true,ready:false,phase:0,last:0,lastStep:0,history:[],
 pointer:null,down:false,keyboardId:0,visited:new Set(),actionCount:0,renderFrames:0};
function status(t){$("actionStatus").textContent=String(t);}
function consoleStatus(t){$("consoleStatus").textContent=String(t);}
function size(el,c){
 const b=el.getBoundingClientRect(),w=Math.max(200,Math.round(b.width||620)),h=Math.max(110,Math.round(b.height||410)),dpr=Math.min(window.devicePixelRatio||1,2);
 if(el.width!==Math.round(w*dpr)||el.height!==Math.round(h*dpr)){el.width=Math.round(w*dpr);el.height=Math.round(h*dpr);}
 c.setTransform(dpr,0,0,dpr,0,0);return {w,h};
}
function coords(w,h){
 const s=state.graph,scale=Math.min((w-70)/(s.cols-1),(h-85)/(s.rows-1));
 return {scale,x:(w-(s.cols-1)*scale)/2,y:(h-(s.rows-1)*scale)/2};
}
function project(n,p){return {x:p.x+n.x*p.scale,y:p.y+n.y*p.scale};}
function stats(){const s=M.stats(state.graph);
 $("tickCount").textContent=String(s.ticks);$("veinCount").textContent=String(s.active_tubes);
 $("foodCount").textContent=String(s.nutrient_count);$("flowCount").textContent=s.total_abs_flux.toFixed(3);
 $("fieldStatus").textContent=s.ticks+" STEPS / "+s.active_tubes+" ACTIVE TUBES";
 $("graphSummary").textContent=s.connected_nutrients+" OF "+s.nutrient_count+" NUTRIENT NODES REACHABLE THROUGH CURRENT GRID / "+
   s.blocked_nodes+" BARRIERS / QUALITATIVE UNITS";
 return s;
}
function drawBackground(w,h){
 const g=ctx.createRadialGradient(w*.5,h*.5,8,w*.5,h*.5,Math.max(w,h)*.75);
 g.addColorStop(0,"#182a24");g.addColorStop(.48,"#0c1d1e");g.addColorStop(1,"#050f15");
 ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
 ctx.strokeStyle="rgba(198,235,204,.04)";ctx.lineWidth=.65;
 for(let x=0;x<w;x+=34){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
 for(let y=0;y<h;y+=34){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
 for(let i=0;i<72;i++){
  const x=(i*721+103)%Math.max(w,1),y=(i*241+47)%Math.max(h,1);
  ctx.fillStyle="rgba(240,232,163,"+(.09+(i%4)*.032)+")";ctx.fillRect(x,y,1,1);
 }
}
function draw(){
 if(!state.ready||!ctx)return;
 const s=state.graph,{w,h}=size(canvas,ctx),p=coords(w,h);drawBackground(w,h);
 if(state.showTrail){
  for(const n of s.nodes){
   if(n.blocked||n.trail<.003)continue;
   const a=project(n,p),r=clamp(3+n.trail*130,3,19);
   const glow=ctx.createRadialGradient(a.x,a.y,1,a.x,a.y,r);
   glow.addColorStop(0,"rgba(194,221,116,"+clamp(n.trail*5,.04,.28)+")");
   glow.addColorStop(1,"rgba(194,221,116,0)");
   ctx.fillStyle=glow;ctx.beginPath();ctx.arc(a.x,a.y,r,0,TAU);ctx.fill();
  }
 }
 // Draw all available tubes as barely visible substrate links; reinforce flowing tubes.
 for(const e of s.edges){
  if(s.nodes[e.a].blocked||s.nodes[e.b].blocked)continue;
  const a=project(s.nodes[e.a],p),b=project(s.nodes[e.b],p);
  const thick=clamp(e.d*2.65,.5,9),alpha=clamp(.055+e.d*.36,.06,.96);
  ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
  ctx.strokeStyle="rgba(255,219,113,"+alpha+")";ctx.lineWidth=thick;
  ctx.lineCap="round";ctx.stroke();
  if(e.d>.24){
   ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
   ctx.strokeStyle="rgba(255,247,188,"+clamp(e.d*.15,.05,.42)+")";
   ctx.lineWidth=Math.max(.5,thick*.30);ctx.stroke();
  }
  if(Math.abs(e.q)>.012&&state.active){
   const f=((state.phase*.085+(e.a*31+e.b*11)*.035)%1);
   const t=e.q>=0?f:1-f;
   ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,clamp(1+Math.abs(e.q)*8,1,3),0,TAU);
   ctx.fillStyle="rgba(255,246,182,"+clamp(.2+Math.abs(e.q)*8,.2,.95)+")";ctx.fill();
  }
 }
 for(const n of s.nodes){
  const q=project(n,p);
  if(n.blocked){ctx.fillStyle="rgba(105,66,75,.85)";ctx.fillRect(q.x-6,q.y-6,12,12);
   ctx.strokeStyle="#bb8184";ctx.lineWidth=.8;ctx.strokeRect(q.x-6,q.y-6,12,12);}
 }
 for(const id of s.food){
  const n=s.nodes[id],q=project(n,p);
  const glow=ctx.createRadialGradient(q.x,q.y,1,q.x,q.y,23);
  glow.addColorStop(0,"rgba(255,235,116,.36)");glow.addColorStop(1,"rgba(255,235,116,0)");
  ctx.fillStyle=glow;ctx.beginPath();ctx.arc(q.x,q.y,23,0,TAU);ctx.fill();
  ctx.fillStyle="#ffe580";ctx.beginPath();ctx.arc(q.x,q.y,6.2,0,TAU);ctx.fill();
  ctx.strokeStyle="#fff9c7";ctx.stroke();ctx.font="bold 9px ui-monospace,Menlo,monospace";ctx.fillStyle="#fff3ab";
  ctx.fillText("FOOD",q.x+10,q.y-9);
 }
 {
  const n=s.nodes[s.origin],q=project(n,p);
  ctx.shadowBlur=23;ctx.shadowColor="#96f3e6";ctx.beginPath();ctx.arc(q.x,q.y,8,0,TAU);
  ctx.fillStyle="#a1f7e0";ctx.fill();ctx.shadowBlur=0;ctx.strokeStyle="#e1ffff";
  ctx.lineWidth=2;ctx.stroke();ctx.font="bold 9px ui-monospace,Menlo,monospace";
  ctx.fillStyle="#b2fff3";ctx.fillText("ORIGIN",q.x+11,q.y-10);
 }
 {
  const q=project(s.nodes[state.keyboardId],p);
  ctx.beginPath();ctx.arc(q.x,q.y,11,0,TAU);ctx.strokeStyle="rgba(255,255,255,.45)";
  ctx.lineWidth=1.2;ctx.setLineDash([3,3]);ctx.stroke();ctx.setLineDash([]);
 }
 ctx.font="10px ui-monospace,Menlo,monospace";ctx.fillStyle="#a9c1b4";ctx.fillText(
  "CITATION / TERO ET AL. 2010 · ALGORITHM-INSPIRED",12,h-39);
 canvas.dataset.nodes=String(s.nodes.length);canvas.dataset.edges=String(s.edges.length);
 canvas.dataset.ticks=String(s.tick);canvas.dataset.food=String(s.food.length);
 canvas.dataset.activeTubes=String(M.stats(s).active_tubes);canvas.dataset.frames=String(++state.renderFrames);
}
function telemetry(){
 if(!state.ready||!pctx)return;
 const {w,h}=size(plot,pctx);pctx.fillStyle="#0b1b20";pctx.fillRect(0,0,w,h);
 pctx.strokeStyle="rgba(225,230,193,.11)";pctx.lineWidth=1;
 for(let i=0;i<4;i++){const y=12+i*(h-22)/3;pctx.beginPath();pctx.moveTo(8,y);pctx.lineTo(w-9,y);pctx.stroke();}
 if(state.history.length<2)return;
 const ceiling=Math.max(10,...state.history.map(x=>x.veins))*1.08;
 pctx.beginPath();state.history.forEach((row,i)=>{
  const x=9+(i/Math.max(1,state.history.length-1))*(w-18);
  const y=h-10-row.veins/ceiling*(h-20);
  if(i===0)pctx.moveTo(x,y);else pctx.lineTo(x,y);
 });
 pctx.strokeStyle="#ffdf71";pctx.lineWidth=2;pctx.stroke();
 pctx.font="9px ui-monospace,Menlo,monospace";pctx.fillStyle="#a6c0b1";
 pctx.fillText("STRONG TUBE COUNT (SIMULATED)",9,12);
}
function update(){
 const m=stats();state.history.push({ticks:m.ticks,veins:m.active_tubes,flux:m.total_abs_flux});
 if(state.history.length>110)state.history.shift();
 telemetry();draw();
}
function advance(n=1){
 if(!state.ready)return;
 M.step(state.graph,n,{growth:Number($("growth").value)/100,decay:Number($("decay").value)/100});
 update();
}
function setPlay(running){
 state.active=!!running;$("playPause").setAttribute("aria-pressed",String(!running));
 $("playPause").textContent=running?"Ⅱ PAUSE":"▶ RESUME";
 status(running?"MODEL RUNNING / BROWSER ONLY":"MODEL PAUSED / BROWSER ONLY");
 draw();
}
function setBrush(mode){
 if(!["food","barrier","erase","origin"].includes(mode))return false;
 state.mode=mode;document.querySelectorAll("button[data-brush]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.brush===mode)));
 return true;
}
function apply(id,log=true){
 const s=state.graph,n=s.nodes[id];if(!n)return false;
 let ok=false;
 if(state.mode==="food")ok=M.addFood(s,id);
 else if(state.mode==="barrier")ok=M.barrier(s,id,true);
 else if(state.mode==="erase"){
   ok=M.barrier(s,id,false);
   if(s.food.includes(id)&&s.food.length>1){M.addFood(s,id);ok=true;}
 }
 else if(state.mode==="origin")ok=M.setOrigin(s,id);
 if(ok){if(log)status(state.mode.toUpperCase()+" / CELL "+n.x+","+n.y+" APPLIED");update();}
 else if(log)status("EDIT REJECTED / PROTECT ORIGIN, LAST FOOD, OR MAX 8 FOOD NODES");
 return ok;
}
function pointerNode(e){
 const box=canvas.getBoundingClientRect(),p=coords(box.width,box.height);
 return M.nearest(state.graph,(e.clientX-box.left-p.x)/p.scale,(e.clientY-box.top-p.y)/p.scale);
}
function download(filename,type,contents){
 const blob=new Blob([contents],{type}),url=URL.createObjectURL(blob),a=document.createElement("a");
 a.download=filename;a.href=url;document.body.appendChild(a);a.click();a.remove();
 window.setTimeout(()=>URL.revokeObjectURL(url),1500);
}
function exportSvg(){
 const s=M.svg(state.graph);
 download("cl1-physarum-180x120mm.svg","image/svg+xml",s);
 status("180 × 120 mm VECTOR BLUEPRINT EXPORTED / VERIFY PRINTER SCALE");
}
function exportJson(){
 const s=M.network(state.graph);
 const data={...s,ontology_file:"./ontology.json",edition:"CL1 PHYSA-01"};
 download("cl1-physarum-network.json","application/json",JSON.stringify(data,null,2)+"\n");
 status("TYPED CL1 GRAPH JSON EXPORTED / NO PHYSICAL INSTRUMENTS");
}
function savePng(){
 draw();try{
  const url=canvas.toDataURL("image/png");if(!url.startsWith("data:image/png;base64,"))throw Error("PNG unsupported");
  const a=document.createElement("a");a.download="cl1-physarum-living-network.png";a.href=url;document.body.appendChild(a);a.click();a.remove();
  status("SIMULATION PNG CAPTURED");
 }catch(_){status("BROWSER PNG EXPORT NOT AVAILABLE");}
}
function selfTest(){
 const graph=state.graph,ont=state.ontology;
 const ok=state.ready&&ont.schema==="xunia.cl1.physarum-ontology.v1"&&
  Array.isArray(ont.sources)&&ont.sources.length>=5&&
  graph.nodes.length===216&&graph.edges.length===402&&
  graph.food.length>0&&graph.food.every(id=>!graph.nodes[id].blocked)&&
  !graph.nodes[graph.origin].blocked&&
  graph.edges.every(e=>Number.isFinite(e.d)&&Number.isFinite(e.q)&&e.d>=.015)&&
  canvas.dataset.nodes==="216"&&canvas.dataset.edges==="402"&&
  M.network(graph).schema===M.SCHEMA&&M.svg(graph).includes('width="180mm"');
 status(ok?"CL1 SELF-TEST PASS / 216 NODES / 402 TUBES / SCIENCE SOURCED":
  "CL1 SELF-TEST FAILED / GRAPH OR SOURCE INVALID");
 return ok;
}
function command(value){
 const parts=String(value||"").trim().replace(/^\//,"").split(/\s+/).filter(Boolean);
 const op=(parts.shift()||"").toLowerCase(),args=parts;
 if(op==="help"){consoleStatus("/food X Y · /wall X Y · /erase X Y · /source X Y · /brush food|barrier|erase|origin · /step N · /play · /pause · /reset · /blueprint · /export · /health");return;}
 if(["food","wall","erase","source"].includes(op)){
  if(args.length!==2||!args.every(x=>/^\d{1,2}$/.test(x))){consoleStatus("COORDINATES X Y REQUIRED");return;}
  const [x,y]=args.map(Number),s=state.graph;
  if(x>=s.cols||y>=s.rows){consoleStatus("COORDINATES OUT OF GRID");return;}
  setBrush(({wall:"barrier",source:"origin"})[op]||op);
  consoleStatus(apply(M.nearest(s,x,y))?op.toUpperCase()+" NODE ADDED":"EDIT REFUSED");
  return;
 }
 if(op==="brush"){consoleStatus(setBrush(args[0])?"BRUSH "+args[0]:"INVALID BRUSH");return;}
 if(op==="step"){
  if(args.length!==1||!/^\d{1,4}$/.test(args[0])||Number(args[0])<1||Number(args[0])>500){consoleStatus("STEP COUNT MUST BE 1-500");return;}
  advance(Number(args[0]));consoleStatus("SIMULATED "+args[0]+" MODEL TICKS");return;
 }
 if(op==="play"||op==="pause"){setPlay(op==="play");consoleStatus(op.toUpperCase()+" / NON-KINETIC");return;}
 if(op==="reset"){M.resetConductance(state.graph);state.history=[];update();consoleStatus("MODEL CONDUCTIVITY RESET");return;}
 if(op==="health"){consoleStatus(selfTest()?"CL1 SELF-TEST PASS":"CL1 SELF-TEST FAILED");return;}
 if(op==="blueprint"){exportSvg();consoleStatus("PHYSICAL-SCALE SVG READY");return;}
 if(op==="export"){exportJson();consoleStatus("GRAPH JSON READY");return;}
 if(op==="capture"){savePng();consoleStatus("PNG REQUESTED");return;}
 consoleStatus("COMMAND NOT RECOGNIZED / TYPE /help");
}
function bind(){
 document.querySelectorAll("button[data-brush]").forEach(b=>b.addEventListener("click",()=>setBrush(b.dataset.brush)));
 $("playPause").addEventListener("click",()=>setPlay(!state.active));
 $("stepOne").addEventListener("click",()=>advance(1));
 $("stepThirty").addEventListener("click",()=>advance(30));
 $("resetNetwork").addEventListener("click",()=>{M.resetConductance(state.graph);state.history=[];update();status("CONDUCTANCE RESET / FOOD AND BARRIERS PRESERVED");});
 $("simSpeed").addEventListener("input",e=>{state.speed=Number(e.target.value);$("speedValue").textContent=state.speed+"%";});
 for(const [id,out] of [["growth","growthValue"],["decay","decayValue"]]){
  $(id).addEventListener("input",e=>{$(out).textContent=(Number(e.target.value)/100).toFixed(2)+"×";});
 }
 $("trailToggle").addEventListener("change",e=>{state.showTrail=e.target.checked;draw();});
 $("exportSvg").addEventListener("click",exportSvg);$("exportJson").addEventListener("click",exportJson);
 $("savePng").addEventListener("click",savePng);$("health").addEventListener("click",selfTest);
 $("consoleForm").addEventListener("submit",e=>{e.preventDefault();command($("consoleInput").value);$("consoleInput").value="";});
 canvas.addEventListener("pointerdown",e=>{
  if(e.button!==0||!state.ready)return;
  state.down=true;state.visited=new Set();
  canvas.setPointerCapture?.(e.pointerId);canvas.focus();
  const id=pointerNode(e);state.keyboardId=id;state.visited.add(id);apply(id);draw();
 });
 canvas.addEventListener("pointermove",e=>{
  if(!state.down||!state.ready||state.mode==="origin")return;
  const id=pointerNode(e);if(state.visited.has(id))return;
  state.keyboardId=id;state.visited.add(id);apply(id,false);draw();
 });
 for(const event of ["pointerup","pointercancel","lostpointercapture"])canvas.addEventListener(event,()=>{state.down=false;state.visited.clear();});
 canvas.addEventListener("keydown",e=>{
  const n=state.graph.nodes[state.keyboardId],w=state.graph.cols;
  const next=e.key==="ArrowLeft"?(n.x>0?state.keyboardId-1:state.keyboardId):
  e.key==="ArrowRight"?(n.x<w-1?state.keyboardId+1:state.keyboardId):
  e.key==="ArrowUp"?(n.y>0?state.keyboardId-w:state.keyboardId):
  e.key==="ArrowDown"?(n.y<state.graph.rows-1?state.keyboardId+w:state.keyboardId):null;
  if(next!==null){e.preventDefault();state.keyboardId=next;draw();}
  else if(e.key==="Enter"||e.key===" "){e.preventDefault();apply(state.keyboardId);}
 });
 document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("consoleInput").focus();}});
 window.addEventListener("resize",()=>{draw();telemetry();});
 document.addEventListener("visibilitychange",()=>{if(document.hidden)setPlay(false);});
}
function loadSources(ontology){
 const facts=$("facts"),sources=new Map(ontology.sources.map(s=>[s.id,s]));
 facts.replaceChildren();
 for(const fact of ontology.observational_facts){
  const section=document.createElement("section");section.className="fact";
  const title=document.createElement("strong"),p=document.createElement("p"),a=document.createElement("a");
  title.textContent=fact.title;p.textContent=fact.description;
  const src=sources.get(fact.source_id);
  a.href=src.url;a.textContent="PRIMARY / REVIEW SOURCE ↗";a.target="_blank";a.rel="noopener noreferrer";
  section.append(title,p,a);facts.append(section);
 }
 const bottom=$("sourceIndex");bottom.replaceChildren();
 for(const source of ontology.sources.slice(0,4)){
  const a=document.createElement("a");a.href=source.url;a.textContent=source.citation+" ↗";
  a.target="_blank";a.rel="noopener noreferrer";bottom.appendChild(a);
 }
 $("speciesNodes").textContent=String(ontology.nodes.length);
}
function animate(t){
 if(!state.ready)return;
 const dt=state.last?Math.min(.1,(t-state.last)/1000):0;state.last=t;
 if(state.active&&!document.hidden&&state.speed>0){
  const interval=Math.max(55,290-state.speed*2.2);
  if(t-state.lastStep>=interval){M.tick(state.graph,{growth:Number($("growth").value)/100,decay:Number($("decay").value)/100});
    state.lastStep=t;state.phase+=1;update();}
  else if(t-state.lastDraw>65){draw();state.lastDraw=t;}
 }
 window.requestAnimationFrame(animate);
}
async function boot(){
 bind();if(!ctx||!pctx){status("CANVAS UNSUPPORTED");return;}
 try{
  const res=await fetch("./ontology.json",{credentials:"omit"});if(!res.ok)throw Error("ONTOLOGY MISSING");
  const ontology=await res.json();
  if(ontology.schema!=="xunia.cl1.physarum-ontology.v1"||ontology.scientific_name!=="Physarum polycephalum"||
      !Array.isArray(ontology.nodes)||!Array.isArray(ontology.observational_facts)||ontology.sources.length<5)throw Error("ONTOLOGY SCHEMA INVALID");
  state.ontology=ontology;state.graph=M.create();state.keyboardId=state.graph.origin;
  state.ready=true;loadSources(ontology);update();
  if(!state.active)setPlay(false);
  status("CL1 PHYSA ONLINE / 216 NODES · BIO-INSPIRED SOFTWARE");
  window.requestAnimationFrame(animate);
 }catch(err){
  $("fieldStatus").textContent="SOURCE ERROR";
  status("PHYSARUM DATA COULD NOT LOAD / "+String(err.message).slice(0,90));
 }
}
boot();
})();