/* XUNIA CL1 LINEAR / KINETIC / ONTOLOGY ATLAS.
 * One same-origin Physarum transport simulator; no live sensors, physical
 * motion control, biomedical data, external APIs or training. Values are
 * dimensionless. Animated particles encode signed model flux Q.
 */
(()=>{
"use strict";
const $=id=>document.getElementById(id),TAU=Math.PI*2;
const M=window.PhysarumModel,T=window.CL1TelemetryEngine;
const clamp=(v,lo,hi)=>Math.max(lo,Math.min(hi,v));
const state={
  graph:null,ontology:null,registry:null,history:[],selected:"physarum",
  brush:"inspect",selectedCell:0,focus:"all",metric:"flux",
  kineticSpeed:52,showVectors:true,showParticles:true,phase:0,
  running:!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
  reduced:!!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
  ready:false,frame:0,hover:-1,hoverGraph:[],pointerDown:false,
  visited:new Set(),lastTime:0,lastStep:0,lastPaint:0
};
const kCanvas=$("kineticCanvas"),lCanvas=$("linearCanvas"),oCanvas=$("ontologyCanvas");
const kc=kCanvas?.getContext("2d"),lc=lCanvas?.getContext("2d"),oc=oCanvas?.getContext("2d");
function display(id,text){$(id).textContent=String(text);}
function setStatus(text){display("actionStatus",text)}
function cmdStatus(text){display("commandStatus",text)}
function fit(canvas,ctx,minW=200,minH=165){
 const box=canvas.getBoundingClientRect(),w=Math.max(minW,Math.floor(box.width||600)),h=Math.max(minH,Math.floor(box.height||360)),dpr=Math.min(window.devicePixelRatio||1,2);
 const width=Math.round(w*dpr),height=Math.round(h*dpr);
 if(canvas.width!==width||canvas.height!==height){canvas.width=width;canvas.height=height;}
 ctx.setTransform(dpr,0,0,dpr,0,0);
 return {w,h};
}
function line(ctx,x,y,x2,y2,color,width=1){
 ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(x2,y2);ctx.strokeStyle=color;ctx.lineWidth=width;ctx.stroke();
}
function dimBackground(ctx,w,h){
 const g=ctx.createRadialGradient(w*.5,h*.5,6,w*.5,h*.5,Math.max(w,h)*.75);
 g.addColorStop(0,"#193245");g.addColorStop(.58,"#0d2232");g.addColorStop(1,"#07111e");
 ctx.fillStyle=g;ctx.fillRect(0,0,w,h);
 ctx.strokeStyle="rgba(186,217,227,.055)";ctx.lineWidth=.8;
 for(let x=12;x<w;x+=32)line(ctx,x,0,x,h,"rgba(176,210,239,.055)",.5);
 for(let y=10;y<h;y+=32)line(ctx,0,y,w,y,"rgba(176,210,239,.055)",.5);
}
function modelTransform(w,h){
 const g=state.graph,scale=Math.min((w-62)/(g.cols-1),(h-85)/(g.rows-1));
 return {scale,x:(w-(g.cols-1)*scale)/2,y:(h-(g.rows-1)*scale)/2};
}
function atNode(n,p){return {x:p.x+n.x*p.scale,y:p.y+n.y*p.scale};}
function drawKinetic(){
 if(!state.ready||!kc)return;
 const {w,h}=fit(kCanvas,kc,280,280),g=state.graph,t=modelTransform(w,h);
 dimBackground(kc,w,h);
 // Continuous muted topology, with tube thickness representing modeled conductance.
 for(const e of g.edges){
  if(g.nodes[e.a].blocked||g.nodes[e.b].blocked)continue;
  const a=atNode(g.nodes[e.a],t),b=atNode(g.nodes[e.b],t);
  const width=clamp(.4+e.d*1.45,.45,7),alpha=clamp(.10+e.d*.30,.09,.84);
  line(kc,a.x,a.y,b.x,b.y,"rgba(160,212,238,"+alpha+")",width);
 }
 // Kinetic arrows indicate sign of simulated flux, not actual velocity.
 const vectors=T.vectors(g,120);
 if(state.showVectors){
  for(let i=0;i<vectors.length;i++){
   const v=vectors[i];if(v.magnitude<.0015)continue;
   const a=atNode(g.nodes[v.from],t),b=atNode(g.nodes[v.to],t);
   const x=a.x+(b.x-a.x)*.66,y=a.y+(b.y-a.y)*.66;
   const angle=Math.atan2(b.y-a.y,b.x-a.x);
   const size=clamp(2+v.relativeSpeed*4,2,6);
   kc.beginPath();kc.moveTo(x+Math.cos(angle)*size,y+Math.sin(angle)*size);
   kc.lineTo(x+Math.cos(angle+2.48)*size*.8,y+Math.sin(angle+2.48)*size*.8);
   kc.lineTo(x+Math.cos(angle-2.48)*size*.8,y+Math.sin(angle-2.48)*size*.8);
   kc.closePath();kc.fillStyle="rgba(177,242,225,"+clamp(.35+v.relativeSpeed*.6,.35,.97)+")";kc.fill();
  }
 }
 if(state.showParticles){
  for(let i=0;i<vectors.length;i++){
   const v=vectors[i];if(v.magnitude<.003)continue;
   const a=atNode(g.nodes[v.from],t),b=atNode(g.nodes[v.to],t);
   const speed=.1+v.relativeSpeed*1.6,position=(state.phase*speed+i*.271)%1;
   const x=a.x+(b.x-a.x)*position,y=a.y+(b.y-a.y)*position;
   kc.shadowColor="#c9fff0";kc.shadowBlur=v.relativeSpeed>0.4?12:4;
   kc.beginPath();kc.arc(x,y,1.15+v.relativeSpeed*2.2,0,TAU);
   kc.fillStyle="#e6fff4";kc.fill();kc.shadowBlur=0;
  }
 }
 for(const n of g.nodes){
  if(!n.blocked)continue;
  const p=atNode(n,t);kc.fillStyle="#7c5366";
  kc.fillRect(p.x-5.5,p.y-5.5,11,11);
 }
 for(const id of g.food){
  const p=atNode(g.nodes[id],t);
  const gradient=kc.createRadialGradient(p.x,p.y,1,p.x,p.y,23);
  gradient.addColorStop(0,"rgba(250,211,130,.42)");gradient.addColorStop(1,"rgba(250,211,130,0)");
  kc.fillStyle=gradient;kc.beginPath();kc.arc(p.x,p.y,23,0,TAU);kc.fill();
  kc.fillStyle="#f3ce87";kc.beginPath();kc.arc(p.x,p.y,6,0,TAU);kc.fill();
 }
 const origin=atNode(g.nodes[g.origin],t);
 kc.shadowColor="#b6fff4";kc.shadowBlur=16;kc.fillStyle="#a7fae5";
 kc.beginPath();kc.arc(origin.x,origin.y,7,0,TAU);kc.fill();kc.shadowBlur=0;
 const focus=atNode(g.nodes[state.selectedCell],t);
 kc.strokeStyle="rgba(255,255,255,.65)";kc.lineWidth=1;
 kc.setLineDash([3,3]);kc.beginPath();kc.arc(focus.x,focus.y,12,0,TAU);kc.stroke();kc.setLineDash([]);
 kc.fillStyle="#aacddd";kc.font="10px ui-monospace,Menlo,monospace";
 kc.fillText("VISUAL SPEED RELATIVE TO |Q| / SIGN GIVES DIRECTION",12,h-37);
 kCanvas.dataset.nodes=String(g.nodes.length);kCanvas.dataset.edges=String(g.edges.length);
 kCanvas.dataset.tick=String(g.tick);kCanvas.dataset.vectors=String(vectors.length);
 kCanvas.dataset.frames=String(++state.frame);
 display("kineticStatus",g.tick+" TICKS / "+vectors.length+" DIRECTION VECTORS");
}
function getMetric(){return state.registry.metrics.find(m=>m.id===state.metric);}
function drawLinear(){
 if(!state.ready||!lc)return;
 const {w,h}=fit(lCanvas,lc,220,190),left=48,right=w-15,top=23,bottom=h-30;
 lc.fillStyle="#081a28";lc.fillRect(0,0,w,h);
 const arr=state.history,key=state.metric,values=arr.map(r=>Number(r[key])||0);
 const minVal=values.length?Math.min(...values,0):0;
 const maxVal=values.length?Math.max(...values,0):1;
 const pad=Math.max(.05,(maxVal-minVal)*.11),lo=minVal-pad,hi=maxVal+pad;
 const pointY=value=>bottom-(value-lo)/(hi-lo)*Math.max(1,bottom-top);
 const pointX=i=>left+i/Math.max(1,arr.length-1)*(right-left);
 for(let k=0;k<=4;k++){
  const y=top+k*(bottom-top)/4;line(lc,left,y,right,y,"rgba(171,210,230,.18)",.8);
  const label=(hi-k*(hi-lo)/4).toFixed(2);
  lc.font="9px ui-monospace,Menlo,monospace";lc.fillStyle="#91b4c9";lc.fillText(label,6,y+3);
 }
 if(arr.length>1){
  lc.beginPath();arr.forEach((row,i)=>{
   const x=pointX(i),y=pointY(Number(row[key])||0);
   if(i===0)lc.moveTo(x,y);else lc.lineTo(x,y);
  });
  lc.strokeStyle="#aaf8e6";lc.lineWidth=2;lc.stroke();
  lc.lineTo(pointX(arr.length-1),bottom);lc.lineTo(pointX(0),bottom);lc.closePath();
  lc.fillStyle="rgba(101,221,210,.08)";lc.fill();
 }
 lc.font="10px ui-monospace,Menlo,monospace";lc.fillStyle="#9ab7c6";
 lc.fillText("STEP "+(arr[0]?.step||0),left,bottom+17);
 lc.textAlign="right";lc.fillText("STEP "+(arr[arr.length-1]?.step||0),right,bottom+17);lc.textAlign="left";
 const i=clamp(state.hover<0?arr.length-1:state.hover,0,Math.max(arr.length-1,0)),row=arr[i];
 if(row){
  const x=pointX(i),y=pointY(Number(row[key])||0);
  line(lc,x,top,x,bottom,"rgba(246,224,156,.35)",1);
  lc.beginPath();lc.arc(x,y,3.5,0,TAU);lc.fillStyle="#ffdfaa";lc.fill();
  display("rangeReadout","STEP "+row.step+" / "+key.toUpperCase()+" "+Number(row[key]).toFixed(4));
 }
 lCanvas.dataset.samples=String(arr.length);lCanvas.dataset.metric=key;
 display("traceStatus",arr.length+" SAMPLES · MAX "+T.CAP);
}
function ontologyPositions(w,h){
 const nodes=state.ontology.nodes,n=nodes.length,cx=w*.5,cy=h*.48,r=Math.min(w*.41,h*.40);
 return nodes.map((item,i)=>{
  const angle=i*TAU/n-Math.PI/2;
  const ring=(i%3===0?.54:1);
  return {x:cx+Math.cos(angle)*r*ring,y:cy+Math.sin(angle)*r*ring,id:item.id,verified:item.verified};
 });
}
function drawOntology(){
 if(!state.ready||!oc)return;
 const {w,h}=fit(oCanvas,oc,215,205);
 oc.fillStyle="#0b1d2b";oc.fillRect(0,0,w,h);
 const nodes=state.ontology.nodes,positions=ontologyPositions(w,h);
 const byId=new Map(positions.map(p=>[p.id,p]));
 state.hoverGraph=positions;
 for(const link of state.ontology.links){
  const a=byId.get(link.from),b=byId.get(link.to);if(!a||!b)continue;
  const focus=link.from===state.selected||link.to===state.selected;
  line(oc,a.x,a.y,b.x,b.y,focus?"rgba(196,246,222,.68)":"rgba(118,163,192,.28)",focus?1.7:.9);
 }
 for(let i=0;i<nodes.length;i++){
  const item=nodes[i],p=positions[i],selected=item.id===state.selected;
  oc.shadowColor=selected?"#ddfff7":"#92b9ec";oc.shadowBlur=selected?20:4;
  oc.beginPath();oc.arc(p.x,p.y,selected?8.5:5.3,0,TAU);
  oc.fillStyle=item.verified?"#9deee0":"#b1b6f6";oc.fill();oc.shadowBlur=0;
  if(selected){oc.strokeStyle="#fff";oc.lineWidth=1.8;oc.stroke();}
  const name=item.name.split(" ").slice(0,2).join(" ");
  oc.font=(selected?"bold ":"")+"9px ui-monospace,Menlo,monospace";
  oc.fillStyle=selected?"#f5fffa":"#91b5c6";
  oc.textAlign=p.x<w*.5?"right":"left";
  oc.fillText(name.slice(0,19),p.x+(p.x<w*.5?-10:10),p.y-8);
 }
 oc.textAlign="left";
 oCanvas.dataset.nodes=String(nodes.length);oCanvas.dataset.links=String(state.ontology.links.length);
 oCanvas.dataset.selected=state.selected;
 display("graphStatus",nodes.length+" OBJECTS / "+state.ontology.links.length+" LINKS");
}
function sourceFor(node){
 const sources=new Map(state.ontology.sources.map(s=>[s.id,s]));
 if(node.id==="trail")return sources.get("reid-2012")?.url;
 if(node.verified)return sources.get(node.id==="tubules"||node.id==="cytoplasm"?"tero-2007":"review-cognition-2023")?.url;
 return "../physarum/README.md";
}
function renderOntologyList(){
 const text=$("ontologyFilter").value.trim().toLowerCase(),list=$("ontologyList");
 list.replaceChildren();
 for(const n of state.ontology.nodes.filter(v=>!text||(v.name+" "+v.type+" "+v.description).toLowerCase().includes(text))){
  const b=document.createElement("button"),dot=document.createElement("span"),label=document.createElement("span"),meta=document.createElement("small");
  b.type="button";b.dataset.object=n.id;b.setAttribute("aria-pressed",String(n.id===state.selected));
  dot.className="object-dot"+(n.verified?"":" simulated");label.textContent=n.name;meta.textContent=n.type;
  b.append(dot,label,meta);b.addEventListener("click",()=>selectNode(n.id));list.appendChild(b);
 }
 if(!list.children.length){const empty=document.createElement("p");empty.className="empty";empty.textContent="No matching ontology objects.";list.append(empty);}
 display("ontologyCount",list.children.length+" OBJECTS");
}
function selectNode(id){
 const node=state.ontology.nodes.find(n=>n.id===id);if(!node)return false;
 state.selected=id;display("selectedName",node.name);display("selectedType",node.type);
 display("selectedDescription",node.description);
 display("selectedEvidence",node.verified?"OBSERVED BIOLOGY":"SYNTHETIC MODEL");
 const degree=state.ontology.links.filter(l=>l.from===id||l.to===id).length;
 display("selectedDegree",degree+" LINKED RELATIONSHIPS");
 const link=$("selectedSource");link.href=sourceFor(node);link.textContent=node.verified?"OPEN SCIENTIFIC SOURCE ↗":"OPEN SIMULATION DOCUMENTATION ↗";
 renderOntologyList();drawOntology();return true;
}
function updateReadouts(row){
 display("tickValue",String(row.step).padStart(4,"0"));
 display("fluxValue",row.flux.toFixed(3));
 display("tubesValue",row.tubes);
 display("conductanceValue",row.conductance.toFixed(3));
 display("deltaValue",(row.delta>=0?"+":"")+row.delta.toFixed(3));
 display("recordCount",state.history.length);
 display("globalState",state.running?"SIMULATION / RUNNING":"SIMULATION / PAUSED");
}
function sampleAndPaint(){
 const row=T.capture(state.graph,state.history);
 updateReadouts(row);
 drawKinetic();drawLinear();drawOntology();
}
function advance(steps=1){
 if(!state.ready)return;
 const n=clamp(Math.trunc(steps),1,500);
 for(let i=0;i<n;i++){
  M.tick(state.graph,{growth:Number($("growth").value)/100,decay:Number($("decay").value)/100});
  T.capture(state.graph,state.history);
 }
 state.hover=-1;const last=state.history[state.history.length-1];
 updateReadouts(last);drawKinetic();drawLinear();drawOntology();
}
function setRun(value){
 state.running=!!value;
 $("playPause").setAttribute("aria-pressed",String(!state.running));
 $("playPause").textContent=state.running?"Ⅱ PAUSE MODEL":"▶ RESUME MODEL";
 display("globalState",state.running?"SIMULATION / RUNNING":"SIMULATION / PAUSED");
 setStatus(state.running?"LOCAL MODEL RUNNING / NO HARDWARE":"LOCAL MODEL PAUSED / NO HARDWARE");
}
function reset(){
 state.graph=M.create();state.history=[];state.selectedCell=state.graph.origin;
 state.hover=-1;state.phase=0;
 sampleAndPaint();advance(4);
 setStatus("MODEL RESET / BOTH TELEMETRY AND TOPOLOGY RESTARTED");
}
function setBrush(name){
 if(!["inspect","food","barrier","erase"].includes(name))return false;
 state.brush=name;
 document.querySelectorAll("button[data-brush]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.brush===name)));
 return true;
}
function applyCell(id,log=true){
 const g=state.graph,n=g.nodes[id];if(!n)return false;
 state.selectedCell=id;
 if(state.brush==="inspect"){
  if(log)setStatus("CELL "+n.x+","+n.y+" / P "+n.pressure.toFixed(4)+" / TRAIL "+n.trail.toFixed(4));
  drawKinetic();return true;
 }
 let accepted=false;
 if(state.brush==="food")accepted=M.addFood(g,id);
 else if(state.brush==="barrier")accepted=M.barrier(g,id,true);
 else if(state.brush==="erase"){
  if(n.blocked)accepted=M.barrier(g,id,false);
  else if(g.food.includes(id)&&g.food.length>1)accepted=M.addFood(g,id);
 }
 if(accepted){
  // Editing changes simulated topology, not measurements. Same tick can
  // replace its own snapshot without generating a false future data point.
  const row=T.measure(g,state.history.at(-1));
  T.append(state.history,row);
  updateReadouts(row);drawLinear();drawKinetic();
 }
 if(log)setStatus(accepted?"EDITED "+n.x+","+n.y+" / "+state.brush.toUpperCase():"EDIT REFUSED / PROTECTED FOOD OR ORIGIN");
 return accepted;
}
function kineticHit(e){
 const box=kCanvas.getBoundingClientRect(),w=box.width,h=box.height,t=modelTransform(w,h);
 const x=(e.clientX-box.left-t.x)/t.scale,y=(e.clientY-box.top-t.y)/t.scale;
 return M.nearest(state.graph,x,y);
}
function setMetric(key){
 const item=state.registry.metrics.find(x=>x.id===key);
 if(!item)return false;
 state.metric=key;$("metricSelect").value=key;
 display("metricUnit",item.unit);display("metricDescription",item.description);
 display("metricEvidence",item.evidence.replaceAll("_"," / "));
 state.hover=-1;drawLinear();return true;
}
function setFocus(name){
 if(!["all","kinetic","linear","ontology"].includes(name))return false;
 state.focus=name;document.querySelectorAll("button[data-focus-mode]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.focusMode===name)));
 document.querySelector(".shell").dataset.focus=name;
 const dest=name==="kinetic"?kCanvas:name==="linear"?lCanvas:name==="ontology"?oCanvas:null;
 if(dest){dest.focus({preventScroll:true});}
 drawKinetic();drawLinear();drawOntology();return true;
}
function download(name,type,source){
 const blob=new Blob([source],{type}),url=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=url;a.download=name;
 document.body.appendChild(a);a.click();a.remove();
 window.setTimeout(()=>URL.revokeObjectURL(url),1250);
}
function exportCsv(){download("cl1-linear-telemetry.csv","text/csv",T.exportCSV(state.history));setStatus("MODEL TIME-SERIES CSV EXPORTED / LOCAL");}
function exportJson(){download("cl1-kinetic-ontology.json","application/json",T.exportJSON(state.history,state.registry,state.graph));setStatus("SOURCE-LABELED TELEMETRY JSON EXPORTED / LOCAL");}
function exportPng(){drawKinetic();try{
 const url=kCanvas.toDataURL("image/png");if(!url.startsWith("data:image/png;base64,"))throw Error("PNG not supported");
 const a=document.createElement("a");a.href=url;a.download="cl1-kinetic-flow.png";
 document.body.appendChild(a);a.click();a.remove();setStatus("KINETIC CANVAS PNG SAVED");
 }catch(_){setStatus("CANVAS EXPORT UNAVAILABLE");}
}
function selfTest(){
 const g=state.graph,r=state.registry,o=state.ontology;
 const ok=state.ready&&r.schema==="xunia.cl1.telemetry-ontology.v1"&&
  o.schema==="xunia.cl1.physarum-ontology.v1"&&
  g.nodes.length===216&&g.edges.length===402&&
  o.nodes.length===16&&o.links.length===17&&
  r.metrics.length===T.METRICS.length&&
  r.metrics.every(m=>T.METRICS.includes(m.id))&&
  state.history.length>=1&&state.history.length<=T.CAP&&
  Number.isFinite(state.history.at(-1).flux)&&
  kCanvas.dataset.nodes==="216"&&oCanvas.dataset.nodes==="16"&&
  lCanvas.dataset.samples===String(state.history.length)&&
  state.history.every(x=>Number.isFinite(x.flux))&&
  !state.registry.physical_actuation;
 setStatus(ok?"ATLAS SELF-TEST PASS / 3 CANVASES / 7 SIGNALS / 16 OBJECTS":"ATLAS SELF-TEST FAILED / INVALID SOURCE OR MODEL");
 return ok;
}
function runCommand(raw){
 const parts=String(raw||"").trim().replace(/^\//,"").split(/\s+/).filter(Boolean);
 const op=(parts.shift()||"").toLowerCase();
 if(op==="help"){cmdStatus("/step 1..500 · /metric flux|tubes|conductance|energy|motion|delta|pressure · /focus all|kinetic|linear|ontology · /food X Y · /wall X Y · /erase X Y · /select OBJECT-ID · /pause · /play · /reset · /export csv|json · /health");return;}
 if(op==="metric"){cmdStatus(setMetric(parts[0])?"LINEAR TRACE / "+parts[0]:"INVALID METRIC");return;}
 if(op==="focus"){cmdStatus(setFocus(parts[0])?"FOCUS / "+parts[0]:"INVALID VISUAL FOCUS");return;}
 if(op==="select"){cmdStatus(selectNode(parts.join(" "))?"ONTOLOGY FOCUS / "+parts.join(" "):"ONTOLOGY NODE NOT FOUND");return;}
 if(["food","wall","erase"].includes(op)){
  const [x,y]=parts.map(Number);
  if(parts.length!==2||parts.some(p=>!/^(0|[1-9]\d?)$/.test(p))||x>=state.graph.cols||y>=state.graph.rows){cmdStatus("INVALID COORDINATES / X 0..17, Y 0..11");return;}
  setBrush(op==="wall"?"barrier":op);cmdStatus(applyCell(M.nearest(state.graph,x,y))?"GRAPH CHANGED / "+op:"EDIT REFUSED");return;
 }
 if(op==="step"){
  if(parts.length!==1||!/^[1-9]\d{0,2}$/.test(parts[0])||Number(parts[0])>500){cmdStatus("STEP COUNT 1–500 REQUIRED");return;}
  advance(Number(parts[0]));cmdStatus("MODEL ADVANCED "+parts[0]+" TICKS");return;
 }
 if(op==="pause"||op==="play"){setRun(op==="play");cmdStatus(op.toUpperCase()+" / SOFTWARE ONLY");return;}
 if(op==="reset"){reset();cmdStatus("MODEL + TELEMETRY RESET");return;}
 if(op==="health"){cmdStatus(selfTest()?"ATLAS HEALTH CHECK PASSED":"ATLAS HEALTH CHECK FAILED");return;}
 if(op==="export"){if(parts[0]==="csv"){exportCsv();cmdStatus("CSV EXPORTED");}else if(parts[0]==="json"){exportJson();cmdStatus("JSON EXPORTED");}else cmdStatus("USE /export csv OR /export json");return;}
 cmdStatus("UNKNOWN COMMAND / TYPE /help");
}
function bind(){
 $("ontologyFilter").addEventListener("input",renderOntologyList);
 $("metricSelect").addEventListener("change",e=>setMetric(e.target.value));
 document.querySelectorAll("button[data-focus-mode]").forEach(b=>b.addEventListener("click",()=>setFocus(b.dataset.focusMode)));
 document.querySelectorAll("button[data-brush]").forEach(b=>b.addEventListener("click",()=>setBrush(b.dataset.brush)));
 $("vectorToggle").addEventListener("change",e=>{state.showVectors=e.target.checked;drawKinetic()});
 $("particleToggle").addEventListener("change",e=>{state.showParticles=e.target.checked;drawKinetic()});
 $("kineticSpeed").addEventListener("input",e=>{state.kineticSpeed=Number(e.target.value);display("kineticSpeedValue",state.kineticSpeed+"%");});
 $("growth").addEventListener("input",e=>display("growthValue",(Number(e.target.value)/100).toFixed(2)+"×"));
 $("decay").addEventListener("input",e=>display("decayValue",(Number(e.target.value)/100).toFixed(2)+"×"));
 $("playPause").addEventListener("click",()=>setRun(!state.running));
 $("stepOne").addEventListener("click",()=>advance(1));$("stepThirty").addEventListener("click",()=>advance(30));
 $("resetSimulation").addEventListener("click",reset);
 $("exportCSV").addEventListener("click",exportCsv);$("exportJSON").addEventListener("click",exportJson);
 $("exportPNG").addEventListener("click",exportPng);$("health").addEventListener("click",selfTest);
 $("commandForm").addEventListener("submit",e=>{e.preventDefault();runCommand($("commandInput").value);$("commandInput").value="";});
 kCanvas.addEventListener("pointerdown",e=>{if(!state.ready||e.button!==0)return;state.pointerDown=true;state.visited.clear();kCanvas.setPointerCapture?.(e.pointerId);
  const id=kineticHit(e);state.visited.add(id);applyCell(id);kCanvas.focus();});
 kCanvas.addEventListener("pointermove",e=>{if(!state.ready||!state.pointerDown||state.brush==="inspect")return;const id=kineticHit(e);
  if(state.visited.has(id))return;state.visited.add(id);applyCell(id,false);});
 for(const ev of ["pointerup","pointercancel","lostpointercapture"])kCanvas.addEventListener(ev,()=>{state.pointerDown=false;state.visited.clear();});
 kCanvas.addEventListener("keydown",e=>{
  const s=state.graph,n=s.nodes[state.selectedCell];
  let id=null;
  if(e.key==="ArrowLeft")id=n.x>0?state.selectedCell-1:state.selectedCell;
  if(e.key==="ArrowRight")id=n.x<s.cols-1?state.selectedCell+1:state.selectedCell;
  if(e.key==="ArrowUp")id=n.y>0?state.selectedCell-s.cols:state.selectedCell;
  if(e.key==="ArrowDown")id=n.y<s.rows-1?state.selectedCell+s.cols:state.selectedCell;
  if(id!==null){state.selectedCell=id;e.preventDefault();drawKinetic();}
  else if(e.key==="Enter"){e.preventDefault();applyCell(state.selectedCell);}
 });
 lCanvas.addEventListener("pointermove",e=>{
  const b=lCanvas.getBoundingClientRect(),usable=Math.max(1,b.width-63);
  const idx=Math.round(clamp((e.clientX-b.left-48)/usable,0,1)*Math.max(0,state.history.length-1));
  state.hover=idx;drawLinear();
 });
 lCanvas.addEventListener("pointerleave",()=>{state.hover=-1;drawLinear()});
 lCanvas.addEventListener("keydown",e=>{
  if(e.key!=="ArrowLeft"&&e.key!=="ArrowRight")return;
  e.preventDefault();const max=Math.max(0,state.history.length-1);
  state.hover=clamp((state.hover<0?max:state.hover)+(e.key==="ArrowRight"?1:-1),0,max);drawLinear();
 });
 oCanvas.addEventListener("click",e=>{
  const rect=oCanvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;
  let nearest=null,dist=24;for(const hit of state.hoverGraph){const d=Math.hypot(hit.x-x,hit.y-y);if(d<dist){dist=d;nearest=hit;}}
  if(nearest)selectNode(nearest.id);
 });
 oCanvas.addEventListener("keydown",e=>{
  if(!["ArrowLeft","ArrowRight","ArrowUp","ArrowDown","Enter"].includes(e.key))return;
  e.preventDefault();const nodes=state.ontology.nodes;const current=nodes.findIndex(n=>n.id===state.selected);
  if(e.key==="Enter"){selectNode(state.selected);return;}
  const dir=e.key==="ArrowLeft"||e.key==="ArrowUp"?-1:1;
  selectNode(nodes[(current+dir+nodes.length)%nodes.length].id);
 });
 document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("commandInput").focus();}});
 window.addEventListener("resize",()=>{drawKinetic();drawLinear();drawOntology()});
 document.addEventListener("visibilitychange",()=>{if(document.hidden)setRun(false)});
}
function animate(time){
 if(!state.ready)return;
 const dt=state.lastTime?Math.min(.10,(time-state.lastTime)/1000):0;state.lastTime=time;
 if(state.running&&!document.hidden){
  const interval=Math.max(95,390-state.kineticSpeed*2.2);
  if(time-state.lastStep>=interval){state.lastStep=time;advance(1);}
  if(time-state.lastPaint>=65){state.phase+=dt*(.5+state.kineticSpeed/90);drawKinetic();state.lastPaint=time;}
 }
 window.requestAnimationFrame(animate);
}
async function boot(){
 bind();if(!kc||!lc||!oc||!M||!T){setStatus("CANVAS OR MODEL ENGINE UNAVAILABLE");return;}
 try{
  const [oreg,treg]=await Promise.all([
    fetch("../physarum/ontology.json",{credentials:"omit"}),
    fetch("./registry.json",{credentials:"omit"})
  ]);
  if(!oreg.ok||!treg.ok)throw Error("LOCAL ONTOLOGY REGISTRY NOT AVAILABLE");
  const [ont,reg]=await Promise.all([oreg.json(),treg.json()]);
  if(ont.schema!=="xunia.cl1.physarum-ontology.v1"||ont.nodes.length!==16||ont.links.length!==17||
     reg.schema!=="xunia.cl1.telemetry-ontology.v1"||reg.metrics.length!==7||reg.physical_actuation!==false)throw Error("SOURCE ONTOLOGY SCHEMA INVALID");
  state.ontology=ont;state.registry=reg;state.graph=M.create();state.selectedCell=state.graph.origin;state.ready=true;
  display("objectCount",ont.nodes.length);
  for(const metric of reg.metrics){
   const option=document.createElement("option");option.value=metric.id;option.textContent=metric.label;$("metricSelect").append(option);
  }
  setMetric(reg.display.default_metric);
  selectNode("physarum");
  sampleAndPaint();advance(4);
  if(!state.running)setRun(false);
  setStatus("CL1 TELEMETRY ACTIVE / SINGLE LOCAL SIMULATION / NO PHYSICAL HARDWARE");
  window.requestAnimationFrame(animate);
 }catch(err){
  display("globalState","SOURCE ERROR");display("kineticStatus","SOURCE ERROR");
  setStatus("LOCAL DATA LOAD FAILED / "+String(err.message).slice(0,125));
 }
}
boot();
})();