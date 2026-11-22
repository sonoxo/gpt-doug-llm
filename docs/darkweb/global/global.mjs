import {FEEDS,REFRESH_MS,parseUSGS,parseNASA,parseCISA,filterEvents,project,freshLabel} from "./feed-core.mjs";

const $=id=>document.getElementById(id);
const NS="http://www.w3.org/2000/svg";
const state={usgs:[],nasa:[],cisa:[],unmapped:0,health:{usgs:false,nasa:false,cisa:false},
  selected:null,refreshing:false,lastAttempt:0,view:{x:0,y:0,w:1000,h:500}};
const sourceNames={usgs:"USGS",nasa:"NASA EONET",cisa:"CISA KEV"};
const create=(tag,className,text)=>{const el=document.createElement(tag);if(className)el.className=className;if(text!==undefined)el.textContent=String(text);return el;};
const attr=(el,map)=>{for(const [key,val] of Object.entries(map))el.setAttribute(key,String(val));return el;};
const svg=(tag,map)=>attr(document.createElementNS(NS,tag),map);
const formatDate=value=>Number.isFinite(value)?new Date(value).toLocaleString():"Unknown";
const filters=()=>({kind:$("layer").value,timeWindow:$("window").value,minMagnitude:Number($("magnitude").value),
  query:$("event-search").value,now:Date.now()});
const visibleEvents=()=>filterEvents([...state.usgs,...state.nasa],filters()).sort((a,b)=>b.observed-a.observed);

function renderGrid(){
 const grid=$("grid-lines");
 for(let x=0;x<=1000;x+=100)grid.append(svg("line",{x1:x,y1:0,x2:x,y2:500,class:"grid-line"}));
 for(let y=0;y<=500;y+=50)grid.append(svg("line",{x1:0,y1:y,x2:1000,y2:y,class:y===250?"grid-equator":"grid-line"}));
}
function setView(x,y,w){
 w=Math.min(1000,Math.max(240,w));const h=w/2;
 const next={x:Math.min(Math.max(0,x),1000-w),y:Math.min(Math.max(0,y),500-h),w,h};
 state.view=next;$("world").setAttribute("viewBox",[next.x,next.y,next.w,next.h].join(" "));
}
function zoom(scale,cx,cy){
 const old=state.view,w=Math.min(1000,Math.max(240,old.w*scale)),h=w/2;
 const px=cx??old.x+old.w/2,py=cy??old.y+old.h/2;
 setView(px-(px-old.x)*w/old.w,py-(py-old.y)*h/old.h,w);
}
function initMap(){
 renderGrid();
 $("zoom-in").addEventListener("click",()=>zoom(.75));
 $("zoom-out").addEventListener("click",()=>zoom(1.3));
 $("zoom-reset").addEventListener("click",()=>setView(0,0,1000));
 const el=$("world");let drag=null;
 el.addEventListener("pointerdown",e=>{if(e.button!==0||e.target.classList.contains("marker"))return;
   drag={x:e.clientX,y:e.clientY,view:{...state.view}};el.setPointerCapture(e.pointerId);el.classList.add("dragging");});
 el.addEventListener("pointermove",e=>{if(!drag)return;
   const bounds=el.getBoundingClientRect(),v=drag.view;
   setView(v.x-(e.clientX-drag.x)*v.w/bounds.width,v.y-(e.clientY-drag.y)*v.h/bounds.height,v.w);});
 const done=()=>{drag=null;el.classList.remove("dragging");};
 el.addEventListener("pointerup",done);el.addEventListener("pointercancel",done);
 el.addEventListener("wheel",e=>{e.preventDefault();
  const rect=el.getBoundingClientRect(),v=state.view;
  zoom(e.deltaY<0?.8:1.25,v.x+(e.clientX-rect.left)/rect.width*v.w,v.y+(e.clientY-rect.top)/rect.height*v.h);
 },{passive:false});
}
function selectEvent(event){
 state.selected=event.id;
 const box=$("selected");box.replaceChildren();box.hidden=false;
 const top=create("strong",null,event.title);
 const sub=create("p",null,sourceNames[event.feed]+" · "+event.category+" · "+formatDate(event.observed)+" · "+event.coords[1].toFixed(3)+"° lat / "+event.coords[0].toFixed(3)+"° lon");
 const url=create("a",null,"VIEW ORIGINAL SOURCE ↗");url.href=event.url;url.target="_blank";url.rel="noopener noreferrer";
 const close=create("button",null,"CLOSE ×");close.type="button";close.addEventListener("click",()=>{state.selected=null;box.hidden=true;renderEvents();});
 box.append(top,sub,url,close);renderMarkers(visibleEvents());
 document.querySelectorAll(".event").forEach(el=>el.classList.toggle("active",el.dataset.id===event.id));
}
function renderMarkers(events){
 const parent=$("markers");parent.replaceChildren();
 const limited=events.slice(0,450);
 const active=limited.find(e=>e.id===state.selected);
 for(const e of limited){
   const p=project(e.coords);
   const size=e.feed==="usgs"?Math.min(7.5,Math.max(2.4,2.6+(e.magnitude??0)*.55)):4;
   const marker=svg("circle",{cx:p.x,cy:p.y,r:size,class:"marker "+e.feed+(e.id===state.selected?" active":""),tabindex:0,role:"button","aria-label":e.title});
   const title=svg("title",{});title.textContent=e.title;marker.append(title);
   marker.addEventListener("click",ev=>{ev.stopPropagation();selectEvent(e);});
   marker.addEventListener("keydown",ev=>{if(ev.key==="Enter"||ev.key===" "){ev.preventDefault();selectEvent(e);}});
   parent.append(marker);
 }
 $("map-total").textContent=limited.length+" / "+events.length+" filtered, mapped"+(events.length>limited.length?" (450-point display cap)":"");
 if(active){const p=project(active.coords);const ring=svg("circle",{cx:p.x,cy:p.y,r:12,class:"marker-ring",stroke:"#ffffff"});parent.append(ring);}
}
function renderEvents(){
 const filtered=visibleEvents(),list=$("event-list");
 $("stream-count").textContent=filtered.length+" MATCHING";
 $("stream-status").textContent=filtered.length?filtered.length+" verified-coordinate event record(s) match the current filters. Showing up to 65 in the list.":(Object.values(state.health).some(Boolean)?"No matching geolocated observations in loaded feeds.":"No usable geographic sources; inspect source integrity below.");
 renderMarkers(filtered);
 list.replaceChildren();
 for(const event of filtered.slice(0,65)){
  const button=create("button","event "+event.feed+(event.id===state.selected?" active":""),undefined);
  button.type="button";button.dataset.id=event.id;
  const top=create("span","eyebrow");top.append(create("span",null,event.feed==="usgs"?"EARTHQUAKE / USGS":"NATURAL EVENT / NASA"),create("span",null,freshLabel(event.observed)));
  button.append(top,create("strong",null,event.title),create("small",null,event.category+" · "+formatDate(event.observed)));
  button.addEventListener("click",()=>selectEvent(event));list.append(button);
 }
 if(state.selected&&!filtered.some(e=>e.id===state.selected)){state.selected=null;$("selected").hidden=true;}
 $("export").disabled=filtered.length===0;
}
function renderCyber(){
 const list=$("cisa-list");list.replaceChildren();
 for(const v of state.cisa.slice(0,24)){
  const item=create("div","cve");
  const a=create("a",null,"SOURCE ↗");a.href=v.url;a.target="_blank";a.rel="noopener noreferrer";
  item.append(a,create("strong",null,v.id),create("p",null,v.title),create("small",null,v.vendor+" / "+v.product+" · Added "+(v.added||"unknown")));
  list.append(item);
 }
 $("cisa-status").textContent=state.health.cisa?state.cisa.length+" KEV records loaded; showing 24 most recently added. Feed updates are not live attack telemetry.":"CISA unavailable or not yet loaded. No substitute records.";
}
function renderMetrics(){
 const sum=state.usgs.length+state.nasa.length;
 $("count-global").textContent=sum.toLocaleString();$("count-usgs").textContent=state.usgs.length.toLocaleString();
 $("count-nasa").textContent=state.nasa.length.toLocaleString();$("count-cisa").textContent=state.cisa.length.toLocaleString();
 $("last-refreshed").textContent=state.lastAttempt?new Date(state.lastAttempt).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"}):"—";
 const healthy=Object.values(state.health).filter(Boolean).length;
 $("network-dot").className="status-light "+(healthy===3?"good":"bad");
 $("network-label").textContent=healthy+"/3 PUBLIC FEEDS AVAILABLE";
}
function health(name,ok,message){
 state.health[name]=ok;
 const badge=$("source-"+name);badge.className="source-health "+(ok?"good":"bad");badge.textContent=ok?"RECEIVED":"FAILED";
 $("timestamp-"+name).textContent=message;
}
async function fetchFeed(name){
 const controller=new AbortController();const timeout=setTimeout(()=>controller.abort(),18000);
 try{
  const response=await fetch(FEEDS[name],{mode:"cors",cache:"no-store",signal:controller.signal});
  if(!response.ok)throw new Error("HTTP "+response.status);
  const doc=await response.json(),received=Date.now();
  if(name==="usgs")state.usgs=parseUSGS(doc);
  if(name==="nasa"){const parsed=parseNASA(doc);state.nasa=parsed.events;state.unmapped=parsed.unmapped;}
  if(name==="cisa")state.cisa=parseCISA(doc);
  const original=name==="usgs"&&Number.isFinite(doc?.metadata?.generated)?"; publisher generated "+formatDate(doc.metadata.generated):"";
  health(name,true,"Received "+formatDate(received)+original+(name==="nasa"&&state.unmapped?"; "+state.unmapped+" events without point geometry excluded":""));
 }catch(error){
  if(name==="usgs")state.usgs=[];if(name==="nasa"){state.nasa=[];state.unmapped=0;}if(name==="cisa")state.cisa=[];
  health(name,false,"Fetch failed ("+(error?.name==="AbortError"?"timeout":"network / format error")+"). Refresh to retry.");
 }finally{clearTimeout(timeout);}
}
async function refresh(){
 if(state.refreshing)return;
 state.refreshing=true;$("refresh").disabled=true;$("refresh").textContent="REFRESHING…";
 state.lastAttempt=Date.now();
 await Promise.all(["usgs","nasa","cisa"].map(fetchFeed));
 state.refreshing=false;$("refresh").disabled=false;$("refresh").textContent="↻ REFRESH NOW";
 renderMetrics();renderEvents();renderCyber();
}
function exportJSON(){
 const items=visibleEvents();
 const payload={workspace:"XUNIA GLASS ONION / GLOBAL OBSERVATORY",exported_at:new Date().toISOString(),
  scope:"PUBLIC_GEOLOCATED_NATURAL_EVENTS_ONLY_NOT_CYBER_ATTACK_TELEMETRY",
  sources:Object.keys(FEEDS).map(key=>({id:key,url:FEEDS[key],received:state.health[key]})),
  filters:filters(),observations:items};
 const blob=new Blob([JSON.stringify(payload,null,2)],{type:"application/json"});
 const url=URL.createObjectURL(blob),a=document.createElement("a");a.href=url;a.download="xunia-global-observatory.json";
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
}
initMap();
["layer","window","magnitude"].forEach(id=>$(id).addEventListener("change",renderEvents));
$("event-search").addEventListener("input",renderEvents);
$("refresh").addEventListener("click",refresh);
$("export").addEventListener("click",exportJSON);
$("export").disabled=true;
setInterval(()=>{if($("auto").checked&&document.visibilityState!=="hidden")refresh();},REFRESH_MS);
document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible"&&$("auto").checked&&Date.now()-state.lastAttempt>=REFRESH_MS)refresh();});
refresh();
