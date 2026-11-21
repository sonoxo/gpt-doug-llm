/* XUNIA CL1 Synapse: simulated sensory interpretation, not a neural interface.
   No implant API, brain recording or stimulation, microphone, camera, vibration,
   medical device control, external network requests or actual smell/taste.
*/
(()=>{
"use strict";
const $=id=>document.getElementById(id),TAU=Math.PI*2,clamp=(x,a,b)=>Math.max(a,Math.min(b,x));
const SENSES=["vision","sound","touch","smell","taste"],VIEWS=["synapse","cortex","field"];
const state={items:[],byId:new Map(),domain:"molecules",selected:"",search:"",view:"synapse",
 senses:new Set(SENSES),intensity:55,zoom:1,yaw:.16,tilt:.48,phase:0,paused:!!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
 reduced:!!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches,
 audio:false,context:null,voices:new Set(),pulses:[],pointer:null,drag:null,hit:[],selectedNode:0,
 ready:false,frame:0,events:0,lastTime:0,lastDraw:0};
const canvas=$("neuralCanvas"),ctx=canvas?.getContext("2d");
const nodes=Array.from({length:56},(_,i)=>{const a=i*2.39996323,r=Math.sqrt((i+.5)/56);return {id:i,x:Math.cos(a)*r,y:Math.sin(a)*r*.8,z:((i*13)%19-9)/13};});
const edges=nodes.flatMap((n,i)=>[{a:i,b:(i+1)%56},{a:i,b:(i+7)%56}]);
function code(s){let h=2166136261;for(const c of s){h^=c.charCodeAt(0);h=Math.imul(h,16777619)}return h>>>0;}
function status(t){$("actionStatus").textContent=String(t)}
function commandStatus(t){$("commandStatus").textContent=String(t)}
function log(t){const line=document.createElement("div"),time=document.createElement("time");line.className="event";
 time.textContent=new Date().toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"});
 line.append(time,document.createTextNode(String(t)));$("eventLog").prepend(line);
 while($("eventLog").children.length>7)$("eventLog").lastChild.remove();
 $("eventCount").textContent=++state.events+" EVENTS";}
function permitted(url){try{const u=new URL(url);return u.protocol==="https:"&&
 ["nssdc.gsfc.nasa.gov","ssd.jpl.nasa.gov","api.nasa.gov","cdms.astro.uni-koeln.de",
 "pubchem.ncbi.nlm.nih.gov","www.palantir.com","aws.amazon.com",
 "docs.aws.amazon.com","www.anduril.com"].includes(u.hostname);}catch(_){return false;}}
function parseCatalogs(m,p,f){
 if(m.schema!=="xunia.cl1.molecules.v1"||!Array.isArray(m.molecules)||m.molecules.length<30)throw Error("INVALID MOLECULAR CATALOG");
 if(p.schema!=="xunia.cl1.planet-twins.v1"||!Array.isArray(p.planets)||p.planets.length!==8)throw Error("INVALID PLANETARY CATALOG");
 if(f.schema!=="xunia.cl1.fusion-ontology.v1"||!Array.isArray(f.nodes)||f.nodes.length<20)throw Error("INVALID ONTOLOGY");
 const list=[];
 for(const item of m.molecules){
  if(!item.id||!item.name||!item.formula||!item.description||!permitted(item.source_url))throw Error("INVALID MOLECULE REFERENCE");
  list.push({id:"molecule:"+item.id,domain:"molecules",name:item.name,subtitle:item.formula,
   description:item.description,kind:"Molecular structure",status:item.status,url:item.source_url,
   provenance:"Curated chemistry model / illustrative 3D geometry"});
 }
 for(const item of p.planets){
  const url=item.physical_source||"https://nssdc.gsfc.nasa.gov/planetary/factsheet/";
  if(!item.id||!item.name||!item.description||!permitted(url))throw Error("INVALID NASA REFERENCE");
  list.push({id:"planet:"+item.id,domain:"planets",name:item.name,subtitle:"NASA/JPL",
   description:item.description,kind:"Planet",status:"nasa-reference",url,
   provenance:"NASA/JPL planet reference; sensory mapping is illustrative"});
 }
 for(const item of f.nodes){
  if(!item.id||!item.name||!item.description||!["cloud","ops","ontology"].includes(item.group))throw Error("INVALID FUSION OBJECT");
  const url=permitted(item.source_url)?item.source_url:"https://www.palantir.com/docs/foundry/ontologies/ontologies-overview";
  list.push({id:"ontology:"+item.id,domain:"ontology",name:item.name,subtitle:item.group.toUpperCase(),
   description:item.description,kind:item.kind,status:item.status,url,
   provenance:"Local proposed, synthetic, or schema ontology object"});
 }
 if(new Set(list.map(v=>v.id)).size!==list.length)throw Error("DUPLICATE OBJECT IDENTIFIER");
 return list;
}
function current(){return state.byId.get(state.selected)}
function listObjects(){
 const list=$("sourceList");list.replaceChildren();
 const items=state.items.filter(i=>i.domain===state.domain&&
  (!state.search||(i.name+" "+i.subtitle+" "+i.description+" "+i.id).toLowerCase().includes(state.search)));
 for(const i of items.slice(0,150)){
  const b=document.createElement("button"),name=document.createElement("span"),meta=document.createElement("small");
  b.type="button";b.dataset.object=i.id;b.setAttribute("aria-pressed",String(state.selected===i.id));
  name.textContent=i.name;meta.textContent=i.subtitle;b.append(name,meta);
  b.addEventListener("click",()=>select(i.id));list.append(b);
 }
 if(!items.length){const p=document.createElement("p");p.className="empty";p.textContent="No matching objects.";list.append(p);}
 $("catalogState").textContent=items.length+" OBJECTS";
}
function inspect(){
 const i=current();if(!i)return;
 $("objectName").textContent=i.name;$("objectType").textContent=String(i.kind).toUpperCase();
 $("objectDescription").textContent=i.description;
 $("objectId").textContent=i.id;$("objectDomain").textContent=i.domain.toUpperCase();
 $("objectProvenance").textContent=i.provenance;
 $("evidenceTag").textContent=String(i.status).toUpperCase().replaceAll("-"," / ");
 $("objectSource").href=i.url;
 $("visionText").textContent=state.senses.has("vision")?"Procedural neural network linked to selected object ID; not recorded neural activity.":"Channel disabled.";
 $("soundText").textContent=state.senses.has("sound")?(state.audio?"Original, low-volume spatial sound pulses armed.":"Optional audio off until manually enabled."):"Channel disabled.";
 $("touchText").textContent=state.senses.has("touch")?"Pointer/touch movement produces visible pressure waves; there is no physical haptic output.":"Channel disabled.";
 $("smellText").textContent=state.senses.has("smell")?"Imagined cool mineral ambience / conceptual vocabulary, NOT a measured odor property or actual scent.":"Channel disabled.";
 $("tasteText").textContent=state.senses.has("taste")?"Imagined neutral crystalline palette / metaphor only, NOT real flavor or evidence that the object is safe to taste.":"Channel disabled.";
}
function select(id){
 if(!state.byId.has(id))return false;
 state.selected=id;const i=current();
 state.domain=i.domain;state.search="";$("sourceSearch").value="";$("sourceType").value=i.domain;
 state.selectedNode=code(id)%nodes.length;listObjects();inspect();draw();
 log("Selected "+i.name+" / "+i.domain+" public ontology");return true;
}
function changeDomain(domain){
 if(!["molecules","planets","ontology"].includes(domain))return false;
 const item=state.items.find(i=>i.domain===domain);return item?select(item.id):false;
}
function view(mode){
 if(!VIEWS.includes(mode))return false;
 state.view=mode;document.querySelectorAll("[data-view]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.view===mode)));
 draw();log("Synthetic neural view / "+mode);return true;
}
function viewport(){
 const box=canvas.getBoundingClientRect(),w=Math.max(220,Math.floor(box.width||640)),h=Math.max(280,Math.floor(box.height||490)),dpi=Math.min(window.devicePixelRatio||1,2);
 if(canvas.width!==Math.round(w*dpi)||canvas.height!==Math.round(h*dpi)){canvas.width=Math.round(w*dpi);canvas.height=Math.round(h*dpi);}
 ctx.setTransform(dpi,0,0,dpi,0,0);return {w,h};
}
function project(n,w,h){
 const cy=Math.cos(state.yaw),sy=Math.sin(state.yaw),x=n.x*cy-n.z*sy,z=n.x*sy+n.z*cy,s=Math.min(w,h)*state.zoom;
 return {id:n.id,x:w*.5+x*s*.36,y:h*.5+(n.y*Math.cos(state.tilt)-z*Math.sin(state.tilt))*s*.32,z,r:4+(z+1)*1.5};
}
function draw(){
 if(!state.ready||!ctx)return;
 const {w,h}=viewport();
 const gr=ctx.createRadialGradient(w*.5,h*.5,3,w*.5,h*.5,Math.max(w,h)*.72);
 gr.addColorStop(0,"#1c3251");gr.addColorStop(.5,"#101e36");gr.addColorStop(1,"#050c16");
 ctx.fillStyle=gr;ctx.fillRect(0,0,w,h);
 ctx.strokeStyle="rgba(200,231,254,.06)";ctx.lineWidth=.7;
 for(let x=0;x<w;x+=37){ctx.beginPath();ctx.moveTo(x,0);ctx.lineTo(x,h);ctx.stroke();}
 for(let y=0;y<h;y+=37){ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();}
 const pts=nodes.map(n=>project(n,w,h));state.hit=pts;
 if(state.senses.has("vision")){
  if(state.view==="cortex"){
   ctx.beginPath();ctx.ellipse(w*.5,h*.5,w*.29,h*.29,state.yaw*.15,0,TAU);
   ctx.fillStyle="rgba(176,203,250,.07)";ctx.fill();ctx.lineWidth=2;ctx.strokeStyle="rgba(216,237,253,.23)";ctx.stroke();
  }
  if(state.view==="field"){
   const p=pts[state.selectedNode];for(let k=1;k<=5;k++){
    ctx.beginPath();ctx.ellipse(p.x,p.y,k*35*state.zoom,k*20*state.zoom,state.yaw,0,TAU);
    ctx.strokeStyle="rgba(195,236,243,"+(.32-k*.047)+")";ctx.stroke();
   }
  }
  for(const e of edges){
   const a=pts[e.a],b=pts[e.b],chosen=e.a===state.selectedNode||e.b===state.selectedNode;
   ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
   ctx.strokeStyle=chosen?"rgba(225,254,250,.6)":"rgba(146,179,235,.21)";ctx.lineWidth=chosen?1.45:.8;ctx.stroke();
   if(!state.paused&&state.intensity>0){
    const t=(state.phase*.15+(e.a+e.b)*.061)%1;
    ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,chosen?2.5:1.2,0,TAU);
    ctx.fillStyle=chosen?"#dffff7":"#8aabd3";ctx.fill();
   }
  }
  for(const p of pts.slice().sort((a,b)=>a.z-b.z)){
   const isSelected=p.id===state.selectedNode,r=p.r*(isSelected?1.7:1);
   const g=ctx.createRadialGradient(p.x-r*.32,p.y-r*.32,0,p.x,p.y,r);
   g.addColorStop(0,"#fff");g.addColorStop(.28,isSelected?"#d9fff4":"#d2e5fc");
   g.addColorStop(1,isSelected?"#37798d":"#2e4470");
   ctx.shadowBlur=isSelected?23:10;ctx.shadowColor=isSelected?"#e2fff5":"#b3c4f6";
   ctx.fillStyle=g;ctx.beginPath();ctx.arc(p.x,p.y,r,0,TAU);ctx.fill();ctx.shadowBlur=0;
   if(isSelected){ctx.beginPath();ctx.arc(p.x,p.y,r+7,0,TAU);ctx.strokeStyle="#d8fcfa";ctx.stroke();}
  }
  for(const pulse of state.pulses){
   const p=pts[pulse.id],radius=8+pulse.age*90*state.intensity/100;
   ctx.beginPath();ctx.arc(p.x,p.y,radius,0,TAU);
   ctx.strokeStyle="rgba(215,255,240,"+clamp(1-pulse.age/1.6,0,.85)+")";ctx.lineWidth=1.3;ctx.stroke();
  }
 }
 if(state.pointer&&state.senses.has("touch")){
  ctx.beginPath();ctx.arc(state.pointer.x,state.pointer.y,19+state.intensity*.22,0,TAU);
  ctx.strokeStyle="rgba(221,255,252,.6)";ctx.stroke();
  ctx.beginPath();ctx.arc(state.pointer.x,state.pointer.y,3.5,0,TAU);ctx.fillStyle="#fff";ctx.fill();
 }
 ctx.font="10px ui-monospace,Menlo,monospace";ctx.fillStyle="#adc9d5";
 ctx.fillText("SOURCE / "+(current()?.name||"—").slice(0,35).toUpperCase(),13,h-37);
 canvas.dataset.nodes=String(nodes.length);canvas.dataset.links=String(edges.length);
 canvas.dataset.view=state.view;canvas.dataset.object=state.selected;canvas.dataset.frames=String(++state.frame);
 $("fieldStatus").textContent=nodes.length+" NODES / "+edges.length+" LINKS / "+state.view.toUpperCase();
}
function frequency(){return 160+code(state.selected)%350;}
function note(){
 if(!state.audio||!state.senses.has("sound")||!state.context)return;
 try{
  const a=state.context,now=a.currentTime,o=a.createOscillator(),g=a.createGain();
  const p=typeof a.createStereoPanner==="function"?a.createStereoPanner():null;
  o.type="sine";o.frequency.value=frequency();
  g.gain.setValueAtTime(.0001,now);
  g.gain.linearRampToValueAtTime(Math.max(.0001,.009*state.intensity/100),now+.035);
  g.gain.exponentialRampToValueAtTime(.0001,now+.42);
  o.connect(g);if(p){p.pan.value=(code(state.selected)%160-80)/100;g.connect(p);p.connect(a.destination);}else g.connect(a.destination);
  o.start(now);o.stop(now+.45);state.voices.add(o);
  o.onended=()=>{state.voices.delete(o);o.disconnect();g.disconnect();p?.disconnect();};
 }catch(_){status("SOUND PULSE UNAVAILABLE");}
}
function pulse(report=true){
 if(!state.ready)return;
 state.pulses.push({id:state.selectedNode,age:0});
 if(state.pulses.length>12)state.pulses.shift();
 draw();if(state.audio)note();if(report)log("Synthetic neural pulse at node "+state.selectedNode);
}
async function silence(){
 state.audio=false;for(const o of state.voices){try{o.stop()}catch(_){}}state.voices.clear();
 const audio=state.context;state.context=null;
 if(audio){try{await audio.close()}catch(_){}}
 if(window.speechSynthesis)window.speechSynthesis.cancel();
 $("audioToggle").setAttribute("aria-pressed","false");$("audioToggle").textContent="♪ ENABLE AUDIO";
 $("audioStatus").textContent="AUDIO OFF / SPEECH STOPPED";inspect();
}
async function toggleAudio(){
 if(state.audio){await silence();log("Audio disabled");return;}
 if(!state.senses.has("sound")){status("ENABLE HEARING CHANNEL FIRST");return;}
 const Audio=window.AudioContext||window.webkitAudioContext;
 if(!Audio){status("WEB AUDIO UNSUPPORTED");return;}
 try{
  const a=new Audio();await a.resume();state.context=a;state.audio=true;
  $("audioToggle").setAttribute("aria-pressed","true");$("audioToggle").textContent="♪ AUDIO ACTIVE";
  $("audioStatus").textContent="OPT-IN ORIGINAL LOW-VOLUME TONES";
  inspect();log("Audio enabled by user");}
 catch(_){await silence();status("BROWSER AUDIO BLOCKED");}
}
function speak(){
 const item=current();if(!item)return;
 if(!state.senses.has("sound")){status("HEARING CHANNEL DISABLED");return;}
 if(!window.speechSynthesis||!window.SpeechSynthesisUtterance){status("SPEECH UNSUPPORTED");return;}
 window.speechSynthesis.cancel();
 const utterance=new SpeechSynthesisUtterance(item.name+". "+item.description.slice(0,160)+". This is a software simulation.");
 utterance.rate=.9;utterance.volume=.5;window.speechSynthesis.speak(utterance);
 $("audioStatus").textContent="USER-REQUESTED BROWSER SPEECH / SYSTEM VOICE";
 log("Speech requested; voice processing depends on user's browser");
}
function channels(){
 state.senses=new Set(Array.from(document.querySelectorAll("[data-sense]:checked")).map(x=>x.dataset.sense));
 if(!state.senses.has("sound"))silence();
 inspect();draw();log("Five-channel routing updated / simulation only");
}
function resetChannels(){
 state.senses=new Set(SENSES);
 document.querySelectorAll("[data-sense]").forEach(x=>x.checked=true);
 inspect();draw();log("Sensory channels reset / audio remains opt-in");
}
function pause(value){
 state.paused=!!value;$("pause").setAttribute("aria-pressed",String(state.paused));
 $("pause").textContent=state.paused?"RESUME MOTION":"PAUSE MOTION";draw();
}
function savePng(){
 draw();try{const url=canvas.toDataURL("image/png");
  if(!url.startsWith("data:image/png;base64,"))throw Error("Unsupported PNG");
  const a=document.createElement("a");a.href=url;a.download="xunia-cl1-sensory-synapse.png";
  document.body.appendChild(a);a.click();a.remove();status("SIMULATION PNG EXPORTED");
 }catch(_){status("PNG EXPORT UNAVAILABLE");}
}
function exportJson(){
 const item=current();if(!item)return;
 const data={schema:"xunia.cl1.sensory-session.v1",boundary:"No neural interface, stimulation, smell, taste or other physical sensation. Conceptual mapping only.",
  object:{id:item.id,name:item.name,reference:item.url,status:item.status,provenance:item.provenance},
  channels:Array.from(state.senses),view:state.view,intensity:state.intensity,selected_node:state.selectedNode,local_events:state.events};
 const u=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
 const a=document.createElement("a");a.href=u;a.download="xunia-cl1-sensory-session.json";
 document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1100);
 status("SESSION JSON EXPORTED / NO SENSOR DATA");
}
function selfTest(){
 const ok=state.ready&&state.items.length>=60&&["molecules","planets","ontology"].every(x=>state.items.some(i=>i.domain===x))&&
  !!current()&&canvas.dataset.nodes==="56"&&canvas.dataset.links==="112"&&
  state.items.every(i=>permitted(i.url));
 status(ok?"CL1 SELF-TEST PASS / 3 SOURCE CATALOGS / 56 NODES / 112 LINKS":"CL1 SELF-TEST FAILED / SOURCE OR RENDER");
 return ok;
}
function command(text){
 const line=String(text||"").trim().replace(/^\//,""),k=line.indexOf(" "),op=(k<0?line:line.slice(0,k)).toLowerCase(),arg=k<0?"":line.slice(k+1).trim();
 if(op==="help"){commandStatus("/domain molecules|planets|ontology · /find TEXT · /select NAME · /view synapse|cortex|field · /pulse · /intensity 0..100 · /pause · /play · /health · /export · /capture · /reset");return;}
 if(op==="domain"){commandStatus(changeDomain(arg)?"DOMAIN / "+arg.toUpperCase():"INVALID DOMAIN");return;}
 if(op==="find"){state.search=arg.toLowerCase();$("sourceSearch").value=arg;listObjects();commandStatus("FILTERED / "+$("catalogState").textContent);return;}
 if(op==="select"){const found=state.items.find(i=>i.name.toLowerCase()===arg.toLowerCase()||i.id.toLowerCase()===arg.toLowerCase());commandStatus(found&&select(found.id)?"SELECTED / "+found.name:"NOT FOUND");return;}
 if(op==="view"){commandStatus(view(arg)?"MODE / "+arg.toUpperCase():"INVALID VIEW");return;}
 if(op==="pulse"){pulse();commandStatus("VISUAL PULSE EMITTED");return;}
 if(op==="intensity"){const n=Number(arg);if(!arg||!Number.isInteger(n)||n<0||n>100){commandStatus("INTENSITY MUST BE 0..100");return;}state.intensity=n;$("intensity").value=String(n);$("intensityValue").textContent=n+"%";draw();commandStatus("SIMULATED INTENSITY / "+n+"%");return;}
 if(op==="pause"||op==="play"){pause(op==="pause");commandStatus(op==="pause"?"MOTION PAUSED":"MOTION PLAYING");return;}
 if(op==="health"){commandStatus(selfTest()?"CL1 SELF-TEST PASS":"CL1 SELF-TEST FAILED");return;}
 if(op==="export"){exportJson();commandStatus("SESSION EXPORTED");return;}
 if(op==="capture"){savePng();commandStatus("PNG CAPTURE REQUESTED");return;}
 if(op==="reset"){resetChannels();view("synapse");state.zoom=1;state.yaw=.16;state.tilt=.48;draw();commandStatus("CL1 SYNAPSE RESET");return;}
 commandStatus("UNKNOWN COMMAND / TYPE /help");
}
function mouse(e){const b=canvas.getBoundingClientRect();return {x:e.clientX-b.left,y:e.clientY-b.top};}
function hit(p){let chosen=null,dist=25;for(const n of state.hit){const v=Math.hypot(n.x-p.x,n.y-p.y);if(v<dist){dist=v;chosen=n;}}return chosen;}
function bind(){
 $("sourceType").addEventListener("change",e=>changeDomain(e.target.value));
 $("sourceSearch").addEventListener("input",e=>{state.search=e.target.value.toLowerCase().trim();listObjects()});
 document.querySelectorAll("[data-view]").forEach(x=>x.addEventListener("click",()=>view(x.dataset.view)));
 document.querySelectorAll("[data-sense]").forEach(x=>x.addEventListener("change",channels));
 $("resetChannels").addEventListener("click",resetChannels);
 $("intensity").addEventListener("input",e=>{state.intensity=Number(e.target.value);$("intensityValue").textContent=state.intensity+"%";draw()});
 $("pulse").addEventListener("click",()=>pulse());
 $("pause").addEventListener("click",()=>pause(!state.paused));
 $("zoomIn").addEventListener("click",()=>{state.zoom=clamp(state.zoom*1.16,.6,1.8);draw()});
 $("zoomOut").addEventListener("click",()=>{state.zoom=clamp(state.zoom/1.16,.6,1.8);draw()});
 $("recenter").addEventListener("click",()=>{state.yaw=.16;state.tilt=.48;state.zoom=1;draw()});
 $("audioToggle").addEventListener("click",toggleAudio);
 $("speak").addEventListener("click",speak);
 $("silence").addEventListener("click",()=>{silence();log("All sound stopped by user")});
 $("savePng").addEventListener("click",savePng);
 $("exportJson").addEventListener("click",exportJson);
 $("selfTest").addEventListener("click",selfTest);
 $("commandForm").addEventListener("submit",e=>{e.preventDefault();command($("commandInput").value);$("commandInput").value=""});
 canvas.addEventListener("pointerdown",e=>{if(e.button!==0)return;const p=mouse(e);state.drag={...p,total:0};state.pointer=p;canvas.setPointerCapture?.(e.pointerId);canvas.focus();draw()});
 canvas.addEventListener("pointermove",e=>{
  const p=mouse(e);if(state.senses.has("touch")){state.pointer=p;draw();}
  if(!state.drag)return;
  const dx=p.x-state.drag.x,dy=p.y-state.drag.y;
  state.drag.total+=Math.hypot(dx,dy);state.drag.x=p.x;state.drag.y=p.y;
  if(state.drag.total>4){state.yaw+=dx*.009;state.tilt=clamp(state.tilt+dy*.004,-1.25,1.25);draw();}
 });
 canvas.addEventListener("pointerup",e=>{const d=state.drag;state.drag=null;if(d&&d.total<8){const n=hit(mouse(e));if(n)state.selectedNode=n.id;pulse();}state.pointer=null;draw()});
 canvas.addEventListener("pointerleave",()=>{if(!state.drag){state.pointer=null;draw()}});
 for(const type of ["pointercancel","lostpointercapture"])canvas.addEventListener(type,()=>{state.drag=null;state.pointer=null;draw()});
 canvas.addEventListener("wheel",e=>{e.preventDefault();state.zoom=clamp(state.zoom*(e.deltaY<0?1.1:.9),.6,1.8);draw()},{passive:false});
 canvas.addEventListener("keydown",e=>{
  if(e.key==="ArrowRight"||e.key==="ArrowDown")state.selectedNode=(state.selectedNode+1)%nodes.length;
  else if(e.key==="ArrowLeft"||e.key==="ArrowUp")state.selectedNode=(state.selectedNode+nodes.length-1)%nodes.length;
  else if(e.key==="Enter"){e.preventDefault();pulse();return;}else return;
  e.preventDefault();draw();
 });
 window.addEventListener("resize",draw);
 document.addEventListener("keydown",e=>{if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("commandInput").focus()}});
 document.addEventListener("visibilitychange",()=>{if(document.hidden)silence()});
 window.addEventListener("pagehide",()=>silence());
}
function loop(t){
 const dt=state.lastTime?Math.min(.09,(t-state.lastTime)/1000):0;state.lastTime=t;
 if(state.ready&&!state.paused&&!state.reduced&&!document.hidden){
  state.phase+=dt*(.25+state.intensity/125);
  state.pulses=state.pulses.map(p=>({id:p.id,age:p.age+dt})).filter(p=>p.age<1.6);
  if(t-state.lastDraw>55){draw();state.lastDraw=t;}
 }
 window.requestAnimationFrame(loop);
}
async function boot(){
 bind();if(!ctx){status("CANVAS UNSUPPORTED");return;}
 try{
  const paths=["../molecules/catalogs/seed.json","../cosmos/planets/catalog.json","../fusion/ontology.json"];
  const responses=await Promise.all(paths.map(path=>fetch(path,{credentials:"omit"})));
  if(responses.some(r=>!r.ok))throw Error("SOURCE FILE NOT AVAILABLE");
  const data=await Promise.all(responses.map(r=>r.json()));
  state.items=parseCatalogs(...data);state.byId=new Map(state.items.map(i=>[i.id,i]));
  state.ready=true;$("sourceCount").textContent=String(state.items.length);
  select("molecule:water");
  $("meshLabel").textContent="3 SOURCE CATALOGS · SYNTHETIC CONNECTIONS";
  status("CL1 ONLINE / ZERO NEURAL IMPLANTS OR PHYSICAL STIMULATION");
  log("Three same-origin source catalogs loaded; interface ready");
  if(state.paused)pause(true);
  window.requestAnimationFrame(loop);
 }catch(err){
  $("catalogState").textContent="SOURCE ERROR";$("fieldStatus").textContent="SOURCE ERROR";
  status("CATALOG LOAD FAILED / "+String(err.message).slice(0,100));log("Catalog failed; no data fabricated");
 }
}
boot();
})();