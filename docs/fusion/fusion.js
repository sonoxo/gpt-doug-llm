/* XUNIA FUSION // source-qualified science + proposed architecture + synthetic ops + semantic ontology.
   Original local visualization. No proprietary integrations, weapon controls or live surveillance.
*/
(()=>{
"use strict";
const $=id=>document.getElementById(id), PI=Math.PI,TAU=PI*2,RAD=PI/180,DAY=86400000;
const MIN=Date.parse("1800-01-01T00:00:00Z"),MAX=Date.parse("2050-12-31T00:00:00Z"),J2000=Date.UTC(2000,0,1,12);
const groups=["nasa","cloud","ops","ontology"];
const colors={nasa:"#91d8ff",cloud:"#f2bd7c",ops:"#ad9eff",ontology:"#9af5d4"};
const names={nasa:"NASA/JPL REFERENCE",cloud:"PROPOSED CLOUD",ops:"SYNTHETIC OBSERVATION",ontology:"LOCAL ONTOLOGY SCHEMA"};
const layouts=["fusion","orbits","architecture","operations"],domainInView={fusion:groups,orbits:["nasa"],architecture:["cloud","ontology"],operations:["ops","ontology"]};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v)),fmt=(v,d=0)=>Number(v).toLocaleString("en-US",{maximumFractionDigits:d});
const canvas=$("atlas"),ctx=canvas.getContext("2d"),emblem=$("emblem"),eCtx=emblem.getContext("2d");
const reduce=!!window.matchMedia?.("(prefers-reduced-motion: reduce)")?.matches;
const state={nodes:[],links:[],byId:new Map(),planets:[],schema:null,selected:null,domains:new Set(groups),view:"fusion",
  search:"",labels:true,edges:true,motion:!reduce,paused:reduce,yaw:.2,tilt:.75,zoom:1,epochMs:Date.UTC(2026,10,19),tempo:0,
  positions:[],hit:[],trace:new Set(),lastTime:0,lastDraw:0,phase:0,frame:0,ready:false,drag:null,dirty:true};
function status(text){$("actionStatus").textContent=String(text)}
function log(text){
  const box=$("eventLog"),row=document.createElement("div"),time=document.createElement("time");
  row.className="event-entry";time.textContent=new Date().toISOString().slice(11,19)+"Z";
  row.appendChild(time);row.appendChild(document.createTextNode(String(text)));
  box.prepend(row);
  while(box.childNodes.length>7)box.lastChild.remove();
}
function sourceAllowed(url){
  try{const u=new URL(url);return u.protocol==="https:"&&
    ["nssdc.gsfc.nasa.gov","ssd.jpl.nasa.gov","api.nasa.gov","aws.amazon.com",
      "docs.aws.amazon.com","www.anduril.com","www.palantir.com"].includes(u.hostname);}
  catch(_){return false;}
}
function validateLocal(obj,planets){
  if(obj.schema!=="xunia.cl1.fusion-ontology.v1"||!Array.isArray(obj.nodes)||!Array.isArray(obj.links))throw Error("ONTOLOGY SCHEMA");
  if(!Array.isArray(planets.planets)||planets.planets.length!==8||planets.schema!=="xunia.cl1.planet-twins.v1")throw Error("NASA PLANET SCHEMA");
  const ids=new Set();
  for(const n of obj.nodes){
    if(!n||typeof n.id!=="string"||ids.has(n.id)||!groups.includes(n.group)||
      !["proposed","synthetic","schema"].includes(n.status)||!n.name||typeof n.description!=="string"||
      (n.source_url&&!sourceAllowed(n.source_url)))throw Error("INVALID ONTOLOGY NODE");
    ids.add(n.id);
  }
  for(const p of planets.planets){
    if(!p||typeof p.id!=="string"||ids.has("nasa-"+p.id)||!Number.isFinite(p.diameter_km)||p.diameter_km<=0||
      !Array.isArray(p.elements_j2000)||p.elements_j2000.length!==6||!p.elements_j2000.every(Number.isFinite)||
      !Array.isArray(p.rates_per_century)||p.rates_per_century.length!==6||!p.rates_per_century.every(Number.isFinite)||
      !sourceAllowed(p.physical_source)||!sourceAllowed(p.orbital_source))throw Error("INVALID NASA REFERENCE");
    ids.add("nasa-"+p.id);
  }
  for(const l of obj.links){
    if(!ids.has(l.source)||!ids.has(l.target)||typeof l.type!=="string"||!l.basis)throw Error("DANGLING ONTOLOGY LINK");
  }
  return true;
}
function active(){
  let allowed=domainInView[state.view],found=state.nodes.filter(n=>allowed.includes(n.group)&&state.domains.has(n.group));
  if(state.search)found=found.filter(n=>(n.name+" "+n.kind+" "+n.description+" "+n.id).toLowerCase().includes(state.search));
  return found;
}
function canShow(id){return active().some(n=>n.id===id)}
function select(id){
  const n=state.byId.get(id);if(!n)return false;
  if(!canShow(id)){
    state.view="fusion";state.domains.add(n.group);state.search="";$("search").value="";
    document.querySelectorAll("[data-domain]").forEach(x=>x.checked=state.domains.has(x.dataset.domain));
    syncModes();
  }
  state.selected=id;inspect();draw();return true;
}
function selectNext(shift=1){
  const shown=active();if(!shown.length)return;
  const ix=shown.findIndex(x=>x.id===state.selected);
  select(shown[(ix+shift+shown.length)%shown.length].id);
}
function syncModes(){document.querySelectorAll("[data-view]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.view===state.view)))}
function changeView(mode){
  if(!layouts.includes(mode))return false;
  state.view=mode;syncModes();
  const shown=active();
  if(shown.length&&!shown.some(n=>n.id===state.selected))state.selected=shown[0].id;
  inspect();draw();log("View changed: "+mode+" / schematic only");return true;
}
function dateText(ms){return new Date(ms).toISOString().slice(0,10)}
function setEpoch(text){
  if(!/^\d{4}-\d{2}-\d{2}$/.test(text))return false;
  const ms=Date.parse(text+"T00:00:00Z");
  if(!Number.isFinite(ms)||ms<MIN||ms>MAX||dateText(ms)!==text)return false;
  state.epochMs=ms;state.tempo=0;$("tempo").value="0";$("epoch").value=text;
  inspect();draw();return true;
}
function positionAt(p,ms,angleOverride){
  const T=(ms-J2000)/DAY/36525,elements=p.elements_j2000.map((v,i)=>v+p.rates_per_century[i]*T);
  const [a,e,i,L,longPeri,longNode]=elements;
  if(a<=0||e<0||e>=1)return [0,0,0];
  let E=angleOverride;
  if(E===undefined){
    const M=((L-longPeri)%360+360)%360*RAD;
    E=M;
    for(let k=0;k<13;k++){const d=(E-e*Math.sin(E)-M)/(1-e*Math.cos(E));E-=d;if(Math.abs(d)<1e-12)break;}
  }
  const xx=a*(Math.cos(E)-e),yy=a*Math.sqrt(1-e*e)*Math.sin(E);
  const omega=(longPeri-longNode)*RAD,N=longNode*RAD,inc=i*RAD;
  const cw=Math.cos(omega),sw=Math.sin(omega),cn=Math.cos(N),sn=Math.sin(N),ci=Math.cos(inc),si=Math.sin(inc);
  return [(cw*cn-sw*sn*ci)*xx+(-sw*cn-cw*sn*ci)*yy,
          (cw*sn+sw*cn*ci)*xx+(-sw*sn+cw*cn*ci)*yy,
          (sw*si)*xx+(cw*si)*yy];
}
function surfaceSize(c,context){
  const rect=c.getBoundingClientRect(),w=Math.max(180,Math.round(rect.width||600)),h=Math.max(160,Math.round(rect.height||400));
  const dpr=Math.min(window.devicePixelRatio||1,2);
  if(c.width!==Math.round(w*dpr)||c.height!==Math.round(h*dpr)){
    c.width=Math.round(w*dpr);c.height=Math.round(h*dpr);
  }
  context.setTransform(dpr,0,0,dpr,0,0);
  return {w,h};
}
function worldToScreen(v,w,h){
  const [x,y,z]=v;
  const r=Math.hypot(x,y,z)||1,k=Math.log1p(r*1.4)/r;
  const X=x*k,Y=y*k,Z=z*k;
  const yaw=state.yaw,c=Math.cos(yaw),s=Math.sin(yaw);
  const xr=X*c-Y*s,yr=X*s+Y*c;
  const fac=Math.min(w,h)*.112*state.zoom;
  return {x:w*.49+xr*fac,y:h*.52-(yr*Math.sin(state.tilt)+Z*Math.cos(state.tilt))*fac};
}
function positionGraph(n,visibleIds,w,h){
  const group=n.group,peers=state.nodes.filter(x=>x.group===group&&visibleIds.has(x.id));
  const i=Math.max(0,peers.findIndex(p=>p.id===n.id)),count=Math.max(1,peers.length);
  const centers=state.view==="architecture"?
    {cloud:[.29,.51],ontology:[.74,.49]}:
    state.view==="operations"?
      {ops:[.31,.52],ontology:[.74,.51]}:
      {nasa:[.27,.31],cloud:[.74,.30],ops:[.28,.76],ontology:[.73,.75]};
  const [cx,cy]=centers[group]||[.5,.5];
  const theta=i*TAU/count+state.yaw;
  const rx=(state.view==="fusion"?.125:.17)*w*state.zoom,ry=(state.view==="fusion"?.13:.23)*h*state.zoom;
  const orbit=1+Math.floor(i/9)*.16;
  return {x:w*cx+Math.cos(theta)*rx*orbit,y:h*cy+Math.sin(theta)*ry*orbit*state.tilt};
}
function screenPositions(w,h){
  const shown=active(),visibleIds=new Set(shown.map(n=>n.id)),positions=new Map();
  for(const n of shown){
    let loc;
    if(state.view==="orbits"&&n.group==="nasa"){
      loc=worldToScreen(positionAt(n.planet,state.epochMs),w,h);
    }else{
      loc=positionGraph(n,visibleIds,w,h);
      if(state.view==="operations"&&n.group==="ops"&&n.id.startsWith("ops-track")){
        loc.x+=Math.sin(state.phase*.6+(n.id==="ops-track-a"?0:1.9))*Math.min(w,h)*.018;
        loc.y+=Math.cos(state.phase*.4+(n.id==="ops-track-a"?1.2:0))*Math.min(w,h)*.017;
      }
    }
    positions.set(n.id,{id:n.id,x:loc.x,y:loc.y,r:n.id===state.selected?10:7,domain:n.group});
  }
  return positions;
}
function backdrop(w,h){
  const gradient=ctx.createRadialGradient(w*.48,h*.48,4,w*.48,h*.48,Math.max(w,h)*.7);
  gradient.addColorStop(0,"#173047");gradient.addColorStop(.65,"#0b182a");gradient.addColorStop(1,"#030910");
  ctx.fillStyle=gradient;ctx.fillRect(0,0,w,h);
  ctx.lineWidth=.7;ctx.strokeStyle="#9ddbeb0c";
  for(let i=0;i<w;i+=36){ctx.beginPath();ctx.moveTo(i,0);ctx.lineTo(i,h);ctx.stroke();}
  for(let i=0;i<h;i+=36){ctx.beginPath();ctx.moveTo(0,i);ctx.lineTo(w,i);ctx.stroke();}
  for(let i=0;i<100;i++){
    const x=((i*887+71)%991)/991*w,y=((i*1973+17)%997)/997*h;
    ctx.fillStyle="rgba(206,238,247,"+(.12+(i%5)*.055)+")";ctx.fillRect(x,y,i%9===0?2:1,1);
  }
}
function drawOrbits(w,h){
  const center=worldToScreen([0,0,0],w,h);
  const sun=ctx.createRadialGradient(center.x,center.y,2,center.x,center.y,55);
  sun.addColorStop(0,"#fbf0be77");sun.addColorStop(.2,"#f7ca8a40");sun.addColorStop(1,"#f6cd7a00");
  ctx.fillStyle=sun;ctx.beginPath();ctx.arc(center.x,center.y,55,0,TAU);ctx.fill();
  ctx.fillStyle="#fff0c6";ctx.beginPath();ctx.arc(center.x,center.y,6,0,TAU);ctx.fill();
  ctx.fillStyle="#dce5df";ctx.font="10px ui-monospace,Menlo,monospace";ctx.fillText("SUN",center.x+10,center.y-8);
  for(const p of state.planets){
    if(!active().some(n=>n.id==="nasa-"+p.id))continue;
    ctx.beginPath();
    for(let j=0;j<=120;j++){
      const spot=worldToScreen(positionAt(p,state.epochMs,j/120*TAU),w,h);
      if(j===0)ctx.moveTo(spot.x,spot.y);else ctx.lineTo(spot.x,spot.y);
    }
    ctx.lineWidth=.75;ctx.strokeStyle="rgba(153,203,238,.23)";ctx.stroke();
  }
}
function draw(){
  if(!state.ready||!ctx)return;
  const {w,h}=surfaceSize(canvas,ctx);ctx.clearRect(0,0,w,h);backdrop(w,h);
  const position=screenPositions(w,h);state.positions=Array.from(position.values());
  if(state.view==="orbits")drawOrbits(w,h);
  if(state.view==="operations"){
    ctx.strokeStyle="#a69af52e";ctx.lineWidth=1.2;
    for(let k=1;k<=4;k++){ctx.beginPath();ctx.ellipse(w*.31,h*.52,k*w*.082,k*h*.087,-.15,0,TAU);ctx.stroke();}
    ctx.font="10px ui-monospace,Menlo,monospace";ctx.fillStyle="#b9a9ff";
    ctx.fillText("SYNTHETIC / NO SENSOR CONNECTION",15,h-22);
  }
  if(state.view==="architecture"){
    ctx.strokeStyle="#f0bd7e29";ctx.lineWidth=1.4;
    ctx.strokeRect(w*.06,h*.09,w*.42,h*.80);
    ctx.strokeRect(w*.56,h*.09,w*.38,h*.80);
    ctx.font="10px ui-monospace,Menlo,monospace";ctx.fillStyle="#c7bd9e";
    ctx.fillText("PROPOSED FABRIC / NOT AWS",w*.07,h*.14);
    ctx.fillText("LOCAL SEMANTIC SCHEMA",w*.57,h*.14);
  }
  if(state.edges){
    for(const e of state.links){
      const a=position.get(e.source),b=position.get(e.target);
      if(!a||!b)continue;
      const highlight=state.trace.has(e.source)||state.trace.has(e.target);
      ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);
      ctx.lineWidth=highlight?2:.9;
      ctx.strokeStyle=highlight?"rgba(204,255,231,.68)":"rgba(133,185,202,.20)";
      ctx.stroke();
      if(!state.paused&&state.motion){
        const t=(state.phase*.17+((e.source.length+e.target.length)%13)*.073)%1;
        ctx.fillStyle=highlight?"#ecfff1":"#7eacbd";
        ctx.beginPath();ctx.arc(a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,highlight?2.2:1.3,0,TAU);ctx.fill();
      }
    }
  }
  for(const n of active()){
    const p=position.get(n.id);if(!p)continue;
    const c=colors[n.group],sel=n.id===state.selected;
    ctx.save();ctx.shadowColor=c;ctx.shadowBlur=sel?25:12;
    ctx.fillStyle=c;ctx.beginPath();ctx.arc(p.x,p.y,p.r,0,TAU);ctx.fill();
    ctx.shadowBlur=0;ctx.strokeStyle=sel?"#f4fffb":"#f8ffff69";ctx.lineWidth=sel?2.5:1;
    ctx.beginPath();ctx.arc(p.x,p.y,p.r+3,0,TAU);ctx.stroke();
    if(state.labels||sel){
      ctx.fillStyle=sel?"#f4fffa":"#b5d2db";
      ctx.textAlign=p.x>w*.72?"right":"left";
      ctx.font=(sel?"bold ":"")+"10px ui-monospace,Menlo,monospace";
      ctx.fillText(n.name,p.x+(p.x>w*.72?-14:14),p.y-9,Math.min(150,w*.27));
    }
    ctx.restore();
  }
  canvas.dataset.nodes=String(position.size);
  canvas.dataset.links=String(state.links.filter(e=>position.has(e.source)&&position.has(e.target)).length);
  canvas.dataset.view=state.view;canvas.dataset.selected=state.selected||"";
  canvas.dataset.frames=String(++state.frame);
  $("mapStatus").textContent=position.size+" VISIBLE / "+state.view.toUpperCase()+" / LOCAL MODEL";
  state.dirty=false;
}
function drawEmblem(){
  if(!state.ready||!eCtx)return;
  const n=state.byId.get(state.selected);if(!n)return;
  const {w,h}=surfaceSize(emblem,eCtx),c=colors[n.group];
  eCtx.clearRect(0,0,w,h);
  const centerX=w/2,centerY=h/2,R=Math.min(w,h)*.29;
  const g=eCtx.createRadialGradient(centerX-R*.24,centerY-R*.25,1,centerX,centerY,R*1.2);
  g.addColorStop(0,"#e3fafe");g.addColorStop(.2,c);g.addColorStop(.7,"#265064");g.addColorStop(1,"#061320");
  eCtx.save();eCtx.shadowBlur=29;eCtx.shadowColor=c;eCtx.fillStyle=g;
  eCtx.beginPath();
  if(n.group==="cloud"){
    eCtx.moveTo(centerX,centerY-R);eCtx.lineTo(centerX+R,centerY-R*.5);eCtx.lineTo(centerX+R,centerY+R*.5);
    eCtx.lineTo(centerX,centerY+R);eCtx.lineTo(centerX-R,centerY+R*.5);eCtx.lineTo(centerX-R,centerY-R*.5);eCtx.closePath();
  }else if(n.group==="ontology"){
    for(let i=0;i<6;i++){const a=i*TAU/6-Math.PI/2;const x=centerX+Math.cos(a)*R,y=centerY+Math.sin(a)*R;if(i===0)eCtx.moveTo(x,y);else eCtx.lineTo(x,y);}eCtx.closePath();
  }else{eCtx.arc(centerX,centerY,R,0,TAU);}
  eCtx.fill();eCtx.shadowBlur=0;eCtx.strokeStyle="#e5f6fa";eCtx.lineWidth=1.5;eCtx.stroke();
  if(n.group==="nasa"&&n.planet?.ring_system){
    eCtx.save();eCtx.translate(centerX,centerY);eCtx.rotate(-.24);eCtx.beginPath();eCtx.ellipse(0,0,R*1.5,R*.36,0,0,TAU);eCtx.lineWidth=6;eCtx.strokeStyle="#b7dbe8b8";eCtx.stroke();eCtx.restore();
  }
  for(let i=0;i<3;i++){eCtx.beginPath();eCtx.ellipse(centerX,centerY,R*(1.22+i*.18),R*(.37+i*.08),i*.48,0,TAU);eCtx.lineWidth=.8;eCtx.strokeStyle="#a7ebef4e";eCtx.stroke();}
  eCtx.restore();emblem.dataset.selected=n.id;
}
const localTargets={nasa:"../cosmos/planets/",cloud:"../",ops:"../biological-data-center/",ontology:"../cosmos/"};
function inspect(){
  const n=state.byId.get(state.selected);if(!n)return;
  const count=state.links.filter(e=>e.source===n.id||e.target===n.id).length;
  $("entityName").textContent=n.name;
  $("entityClass").textContent=names[n.group];
  $("entityDescription").textContent=n.description;
  $("entityDomain").textContent=n.group.toUpperCase();
  $("entityTrust").textContent=n.status.toUpperCase();
  $("entityKind").textContent=n.kind;
  $("entityLinks").textContent=String(count);
  $("selectedState").textContent=n.status.toUpperCase();
  const box=$("related");box.replaceChildren();
  const links=state.links.filter(e=>e.source===n.id||e.target===n.id);
  if(!links.length){const p=document.createElement("span");p.className="empty";p.textContent="No declared connections";box.appendChild(p);}
  for(const e of links.slice(0,15)){
    const neighbor=state.byId.get(e.source===n.id?e.target:e.source);if(!neighbor)continue;
    const b=document.createElement("button");b.type="button";
    b.textContent=e.type+" · "+neighbor.name;b.title=e.basis;
    b.addEventListener("click",()=>select(neighbor.id));box.appendChild(b);
  }
  const facts=$("planetFacts");facts.hidden=n.group!=="nasa";
  if(n.planet){
    $("diameter").textContent=fmt(n.planet.diameter_km)+" km";
    $("gravity").textContent=fmt(n.planet.gravity_ms2,1)+" m/s²";
    $("period").textContent=fmt(n.planet.orbital_period_days,1)+" days";
    $("semimajor").textContent=fmt(n.planet.elements_j2000[0],3)+" AU";
  }
  const src=$("officialSource");src.hidden=!n.source_url;
  if(n.source_url&&sourceAllowed(n.source_url)){src.href=n.source_url;src.textContent="VIEW PUBLISHED "+n.group.toUpperCase()+" SOURCE ↗";}
  else{src.hidden=true;src.removeAttribute("href");}
  const page=$("localPage");page.href=localTargets[n.group];page.hidden=false;
  $("inspectorStatus").textContent="PROVENANCE / "+n.status.toUpperCase()+" · NO REMOTE CONTROL";
  drawEmblem();
}
function updateCounts(){
  $("nodeTotal").textContent=String(state.nodes.length);
  $("edgeTotal").textContent=String(state.links.length);
  $("nasaTotal").textContent=String(state.planets.length);
  for(const g of groups)$(g+"Count").textContent=String(state.nodes.filter(n=>n.group===g).length);
}
function resetFilters(){
  state.domains=new Set(groups);state.search="";$("search").value="";
  document.querySelectorAll("[data-domain]").forEach(x=>x.checked=true);
  changeView("fusion");log("All domain filters restored");
}
function applyFilter(){
  state.search=$("search").value.trim().toLowerCase();
  state.domains=new Set(Array.from(document.querySelectorAll("[data-domain]:checked")).map(x=>x.dataset.domain));
  const shown=active();if(shown.length&&!shown.some(n=>n.id===state.selected))state.selected=shown[0].id;
  if(shown.length)inspect();draw();
}
function trace(){
  const id=state.selected;if(!id)return;
  const one=state.links.filter(e=>e.source===id||e.target===id);
  const set=new Set([id]);
  for(const e of one){set.add(e.source);set.add(e.target);}
  state.trace=set;draw();log("Traced "+one.length+" typed edges around "+state.byId.get(id).name);
  status("LINEAGE / "+set.size+" OBJECTS / "+one.length+" DIRECT RELATIONSHIPS");
}
function exportJson(){
  const ids=new Set(active().map(n=>n.id));
  const data={schema:"xunia.cl1.fusion-export.v1",date:dateText(state.epochMs),view:state.view,
    disclaimer:"Sourced NASA measurements; proposed cloud design; synthetic operations; original ontology. No vendor integration.",
    objects:active().map(n=>({id:n.id,name:n.name,group:n.group,kind:n.kind,status:n.status,description:n.description,source_url:n.source_url||null,
      properties:n.planet?{diameter_km:n.planet.diameter_km,gravity_ms2:n.planet.gravity_ms2,orbital_period_days:n.planet.orbital_period_days,elements_j2000:n.planet.elements_j2000}:null})),
    links:state.links.filter(e=>ids.has(e.source)&&ids.has(e.target))};
  const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)+"\n"],{type:"application/json"}));
  const a=document.createElement("a");a.href=url;a.download="xunia-cl1-fusion-ontology.json";document.body.appendChild(a);a.click();a.remove();
  window.setTimeout(()=>URL.revokeObjectURL(url),1600);status("EXPORTED / "+data.objects.length+" OBJECTS / BROWSER DOWNLOAD");
}
function savePng(){
  draw();
  try{
    const url=canvas.toDataURL("image/png");if(!url.startsWith("data:image/png;base64,"))throw Error("NO IMAGE");
    const a=document.createElement("a");a.href=url;a.download="xunia-cl1-fusion-map.png";
    document.body.appendChild(a);a.click();a.remove();status("PNG MAP CAPTURED / BROWSER DOWNLOAD");
  }catch(_){status("PNG EXPORT NOT SUPPORTED IN THIS BROWSER");}
}
function selfTest(){
  if(!state.ready){status("SELF-TEST FAILED / CATALOG NOT READY");return false;}
  draw();
  const ids=new Set(state.nodes.map(n=>n.id)),valid=state.nodes.length>=25&&state.planets.length===8&&
    state.links.every(e=>ids.has(e.source)&&ids.has(e.target))&&
    state.nodes.every(n=>!n.source_url||sourceAllowed(n.source_url))&&
    Number(canvas.dataset.nodes)===active().length&&!!state.byId.get(state.selected)&&
    Number(emblem.width)>0;
  status(valid?"CL1 SELF-TEST PASS / 8 NASA PLANETS / TYPED LINKS / RENDER ONLINE":
    "CL1 SELF-TEST FAILED / INSPECT CATALOG OR RENDER");
  log(valid?"Local model checks passed":"Local model check failed");
  return valid;
}
function command(raw){
  const input=String(raw||"").trim().replace(/^\//,"");
  const sp=input.indexOf(" "),op=(sp<0?input:input.slice(0,sp)).toLowerCase(),arg=sp<0?"":input.slice(sp+1).trim();
  if(op==="help"){status("/find TEXT · /select ID or NAME · /view fusion|orbits|architecture|operations · /date YYYY-MM-DD · /trace · /export · /capture · /health · /reset");return;}
  if(op==="find"){$("search").value=arg;applyFilter();status("FILTERED / "+active().length+" OBJECTS");return;}
  if(op==="select"){
    const target=state.nodes.find(n=>n.id.toLowerCase()===arg.toLowerCase()||n.name.toLowerCase()===arg.toLowerCase());
    status(target&&select(target.id)?"SELECTED / "+target.name:"OBJECT NOT FOUND / USE EXACT ID OR NAME");return;
  }
  if(op==="view"){status(changeView(arg)?"VIEW / "+arg.toUpperCase():"INVALID VIEW");return;}
  if(op==="date"){status(setEpoch(arg)?"ORBIT DATE / "+arg:"INVALID DATE / 1800–2050");return;}
  if(op==="trace"){trace();return;}
  if(op==="export"){exportJson();return;}
  if(op==="capture"){savePng();return;}
  if(op==="health"){selfTest();return;}
  if(op==="reset"){resetFilters();status("GRAPH RESET / ALL DOMAINS");return;}
  status("UNKNOWN COMMAND / TYPE /help");
}
function canvasXY(e){const r=canvas.getBoundingClientRect();return {x:e.clientX-r.left,y:e.clientY-r.top};}
function wire(){
  document.querySelectorAll("[data-domain]").forEach(el=>el.addEventListener("change",applyFilter));
  document.querySelectorAll("[data-view]").forEach(b=>b.addEventListener("click",()=>changeView(b.dataset.view)));
  $("search").addEventListener("input",applyFilter);
  $("resetFilters").addEventListener("click",resetFilters);
  $("edgesToggle").addEventListener("change",e=>{state.edges=e.target.checked;draw()});
  $("labelsToggle").addEventListener("change",e=>{state.labels=e.target.checked;draw()});
  $("motionToggle").checked=!reduce;
  $("motionToggle").addEventListener("change",e=>{state.motion=e.target.checked&&!reduce;draw()});
  $("zoomIn").addEventListener("click",()=>{state.zoom=clamp(state.zoom*1.15,.55,2.2);draw()});
  $("zoomOut").addEventListener("click",()=>{state.zoom=clamp(state.zoom/1.15,.55,2.2);draw()});
  $("resetCamera").addEventListener("click",()=>{state.zoom=1;state.yaw=.2;state.tilt=.75;draw()});
  $("pause").addEventListener("click",()=>{
    state.paused=!state.paused;$("pause").setAttribute("aria-pressed",String(state.paused));
    $("pause").textContent=state.paused?"RESUME":"PAUSE";draw();
  });
  $("epoch").addEventListener("change",e=>{if(!setEpoch(e.target.value))status("INVALID NASA DATE")});
  $("advance").addEventListener("click",()=>{const ms=Math.min(MAX,state.epochMs+30*DAY);setEpoch(dateText(ms))});
  $("tempo").addEventListener("change",e=>{state.tempo=Number(e.target.value);log("Illustrative date playback / "+state.tempo+" days/sec")});
  $("trace").addEventListener("click",trace);
  $("exportJson").addEventListener("click",exportJson);
  $("savePng").addEventListener("click",savePng);
  $("selfTest").addEventListener("click",selfTest);
  $("commandForm").addEventListener("submit",e=>{e.preventDefault();command($("command").value);$("command").value=""});
  canvas.addEventListener("pointerdown",e=>{
    if(e.button!==0)return;const p=canvasXY(e);state.drag={x:p.x,y:p.y,total:0};canvas.setPointerCapture(e.pointerId);canvas.focus();
  });
  canvas.addEventListener("pointermove",e=>{
    if(!state.drag)return;
    const p=canvasXY(e),dx=p.x-state.drag.x,dy=p.y-state.drag.y;
    state.drag.total+=Math.hypot(dx,dy);state.drag.x=p.x;state.drag.y=p.y;
    if(state.drag.total>3){state.yaw+=dx*.007;state.tilt=clamp(state.tilt+dy*.003,.3,1.15);draw();}
  });
  canvas.addEventListener("pointerup",e=>{
    const old=state.drag;state.drag=null;if(!old||old.total>7)return;
    const p=canvasXY(e);let best=null,min=19;
    for(const x of state.positions){const d=Math.hypot(p.x-x.x,p.y-x.y);if(d<min){min=d;best=x;}}
    if(best)select(best.id);
  });
  for(const type of ["pointercancel","lostpointercapture"])canvas.addEventListener(type,()=>state.drag=null);
  canvas.addEventListener("wheel",e=>{e.preventDefault();state.zoom=clamp(state.zoom*(e.deltaY<0?1.09:.92),.55,2.2);draw()},{passive:false});
  canvas.addEventListener("keydown",e=>{
    if(e.key==="ArrowRight"||e.key==="ArrowDown"){e.preventDefault();selectNext(1);}
    else if(e.key==="ArrowLeft"||e.key==="ArrowUp"){e.preventDefault();selectNext(-1);}
    else if(e.key==="Enter"){e.preventDefault();inspect();}
  });
  document.addEventListener("keydown",e=>{
    if((e.metaKey||e.ctrlKey)&&e.key.toLowerCase()==="k"){e.preventDefault();$("command").focus();}
  });
  window.addEventListener("resize",draw);
}
function loop(now){
  const dt=state.lastTime?Math.min(.15,(now-state.lastTime)/1000):0;state.lastTime=now;
  if(state.ready){
    let changed=false;
    if(state.motion&&!state.paused&&!document.hidden){state.phase+=dt;changed=true;}
    if(state.tempo>0&&!state.paused&&!document.hidden){
      state.epochMs=Math.min(MAX,state.epochMs+dt*state.tempo*DAY);
      if(state.epochMs===MAX){state.tempo=0;$("tempo").value="0";log("JPL approximation range ended at 2050-12-31");}
      $("epoch").value=dateText(state.epochMs);changed=true;
    }
    if(changed&&now-state.lastDraw>=66){draw();state.lastDraw=now;}
  }
  window.requestAnimationFrame(loop);
}
async function boot(){
  wire();
  if(!ctx||!eCtx){status("CANVAS UNSUPPORTED / OPEN SOURCE DOCUMENTATION");return;}
  try{
    const [localResponse,nasaResponse]=await Promise.all([
      fetch("./ontology.json",{credentials:"omit"}),
      fetch("../cosmos/planets/catalog.json",{credentials:"omit"})
    ]);
    if(!localResponse.ok||!nasaResponse.ok)throw Error("SOURCE FILE UNAVAILABLE");
    const [obj,planets]=await Promise.all([localResponse.json(),nasaResponse.json()]);
    validateLocal(obj,planets);
    state.schema=obj;state.planets=planets.planets;
    const nasaNodes=planets.planets.map(p=>({id:"nasa-"+p.id,name:p.name,group:"nasa",kind:"Planet",status:"reference",
      description:p.description+" — Source-backed physical measurements; orbital position uses approximate JPL elements.",
      source_url:p.physical_source,planet:p}));
    state.nodes=[...nasaNodes,...obj.nodes];state.byId=new Map(state.nodes.map(n=>[n.id,n]));
    state.links=[...obj.links,...nasaNodes.flatMap(n=>[
      {source:n.id,target:"ont-world",type:"instanceOf",basis:"planet schema"},
      {source:n.id,target:"ont-source",type:"derivedFrom",basis:"NASA/JPL public catalog"}
    ])];
    state.ready=true;updateCounts();
    state.selected="nasa-earth";inspect();draw();
    log("NASA/JPL catalog loaded: 8 planets / historical orbital elements");
    log("Architecture and observation objects loaded as proposed/synthetic");
    log("Typed ontology initialized: "+state.nodes.length+" objects / "+state.links.length+" links");
    status("CL1 READY / SELECT NODES / 0 REMOTE SENSOR CONNECTIONS");
    window.requestAnimationFrame(loop);
  }catch(err){
    $("mapStatus").textContent="SOURCE UNAVAILABLE";
    status("FUSION ERROR / "+String(err.message).slice(0,100));
    log("Source failed to load; no data was fabricated.");
  }
}
boot();
})();
