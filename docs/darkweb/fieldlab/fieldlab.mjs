// SWARM: parallel public data fetches; HIVE: validated state and provenance;
// SWEEP: deterministic physics thresholds, with no military telemetry or weapon control.
import {FEEDS,SOURCES,POLL_MS,parseFeed,sourceTime,freshness,measuredValues,derivedModel,sweepSignals,mapEvents,auroraCells,standoffEstimate,subsolarPoint,summarize,finite} from "./model-core.mjs";
import {EarthRenderer} from "./earth-renderer.mjs";
const $=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
const data={},sources={},state={running:false,lastRefresh:0,scenario:false,paused:false,orbit:false};
const text=(id,value)=>{$(id).textContent=String(value);};
const el=(tag,cls,content)=>{const e=document.createElement(tag);if(cls)e.className=cls;if(content!==undefined)e.textContent=String(content);return e;};
const fmt=(x,d=1)=>finite(x)?x.toFixed(d):"—";
const utc=t=>finite(t)?new Date(t).toISOString().replace("T"," ").slice(0,19)+" UTC":"UNAVAILABLE";
let renderer=null;
try{renderer=new EarthRenderer($("earth"),event=>selectEvent(event));}
catch(e){text("globe-status","CANVAS UNAVAILABLE — LIVE DATA STILL ACCESSIBLE");}

function selectEvent(e){
 const box=$("inspected");box.replaceChildren();
 box.append(el("h3",null,e.label),el("p",null,e.sourceType+" · "+e.category));
 const table=el("dl");
 const rows=[["COORDINATES",e.lat.toFixed(3)+"° / "+e.lon.toFixed(3)+"°"],["EVENT TIME",utc(e.observed)],["TYPE",e.kind.toUpperCase()],["MAGNITUDE",e.kind==="earthquake"?fmt(e.value,1):"NOT APPLICABLE"],["PROVENANCE",e.kind==="earthquake"?"USGS":"NASA EONET"]];
 for(const [key,value] of rows)table.append(el("dt",null,key),el("dd",null,value));
 box.append(table);
 const link=el("a",null,"OPEN OFFICIAL SOURCE ↗");
 try{const url=new URL(e.source);if(url.protocol==="https:"&&["earthquake.usgs.gov","eonet.gsfc.nasa.gov"].includes(url.hostname)){link.href=url.href;link.target="_blank";link.rel="noopener noreferrer";box.append(link);}}catch{}
}
function currentDataCount(){
 return Object.keys(FEEDS).filter(k=>sources[k]?.ok&&(freshness(k,data[k])==="CURRENT"||freshness(k,data[k])==="CATALOG RECEIVED"||freshness(k,data[k])==="RECEIVED / SOURCE TIME UNKNOWN")).length;
}
function showTelemetry(){
 const m=measuredValues(data);
 for(const [id,value,d] of [["speed",m.speed,0],["density",m.density,1],["bz",m.bz,1],["kp",m.kp,2]])text(id,fmt(value,d));
 text("flare",m.flare??"—");
 const model=derivedModel(data,{scenario:state.scenario,windSpeed:Number($("hyp-speed").value),windDensity:Number($("hyp-density").value)});
 text("pressure",fmt(model.pressure,2));
 text("dyn-pressure",fmt(model.pressure,2));text("standoff",fmt(model.standoff,2));
 text("transit",fmt(model.transit,1));
 text("model-state",model.mode);
 $("model-state").className=state.scenario?"simulated":"";
 drawModelChart(model.pressure);
}
function drawModelChart(pressure){
 const svg=$("model-chart"),grid=svg.querySelector(".model-grid"),curve=$("model-curve"),dot=$("model-dot");
 grid.replaceChildren();
 const x1=47,x2=570,y1=37,y2=163,pmin=.2,pmax=16;
 const toX=p=>x1+(p-pmin)/(pmax-pmin)*(x2-x1);
 const toY=r=>y2-(r-6)/(15-6)*(y2-y1);
 for(const p of [1,2,4,6,8,10,12,14,16]){
  const x=toX(p);grid.append(sv("line",{x1:x,y1:30,x2:x,y2:164}));
  const label=sv("text",{x,y:177,fill:"#9cb8bd","font-family":"monospace","font-size":10,"text-anchor":"middle"});label.textContent=String(p);grid.append(label);
 }
 for(const r of [6,8,10,12,14]){
  const y=toY(r);grid.append(sv("line",{x1:46,y1:y,x2:573,y2:y}));
  const label=sv("text",{x:10,y:y+4,fill:"#9cb8bd","font-family":"monospace","font-size":10});label.textContent=String(r);grid.append(label);
 }
 const path=[];
 for(let i=0;i<=170;i++){const p=pmin+(pmax-pmin)*i/170,rad=standoffEstimate(p);path.push((i?"L":"M")+toX(p).toFixed(2)+" "+toY(rad).toFixed(2));}
 curve.setAttribute("d",path.join(" "));
 if(finite(pressure)&&pressure>=pmin&&pressure<=pmax){dot.setAttribute("cx",toX(pressure));dot.setAttribute("cy",toY(standoffEstimate(pressure)));}
 else{dot.setAttribute("cx","-100");dot.setAttribute("cy","-100");}
}
function sv(tag,attrs){const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));return e;}
function updateView(){
 showTelemetry();updateFeedList();updateSweep();
 const visible=mapEvents(data,{earthquakes:$("layer-quakes").checked,natural:$("layer-nasa").checked,minMagnitude:3.5});
 const cells=auroraCells(data);
 renderer?.setData(cells,visible);
 const count=visible.length;
 text("map-record-count",count+" PUBLIC EVENTS MAPPED + "+cells.length+" AURORA MODEL CELLS");
 text("aurora-time","NOAA MODEL OBSERVED: "+utc(data.aurora?.observed));
 if(renderer)text("globe-status",cells.length+" AURORA / "+count+" GEO EVENTS · SELECT MARKERS");
 const total=currentDataCount();
 text("source-count",total+"/7 VALIDATED/CATALOG SOURCES");
 text("health",total===7?"ALL PUBLIC SOURCES":total?"PARTIAL / "+total+" OF 7":"NO VERIFIED FEEDS");
 $("health").className=total===7?"all-good":total?"partial":"down";
 $("export").disabled=!Object.values(sources).some(x=>x.ok);
}
function updateFeedList(){
 const root=$("feeds"),frag=document.createDocumentFragment();
 for(const [key,url] of Object.entries(FEEDS)){
  const meta=sources[key],f=freshness(key,data[key]),div=el("div","feed");
  const anchor=el("a",null,SOURCES[key].label+" ↗");anchor.href=url;anchor.rel="noopener noreferrer";anchor.target="_blank";
  const ok=meta?.ok&&["CURRENT","CATALOG RECEIVED","RECEIVED / SOURCE TIME UNKNOWN"].includes(f);
  const label=el("span",ok?"current":meta?.ok?"stale":"error",meta?(meta.ok?f:"FAILED"):"NOT FETCHED");
  div.append(anchor,label);
  let details;
  if(!meta)details=SOURCES[key].agency+" / "+SOURCES[key].kind+" · not requested";
  else if(!meta.ok)details=SOURCES[key].agency+" · "+meta.error+" · no data used";
  else{
   const source=sourceTime(key,data[key]);
   details=SOURCES[key].agency+" · "+SOURCES[key].kind+" · "+
     (source!==null?"source "+utc(source):"source event times vary")+" · retrieved "+utc(meta.received);
  }
  div.append(el("p",null,details));frag.append(div);
 }
 root.replaceChildren(frag);
}
function updateSweep(){
 const root=$("signals"),items=sweepSignals(data),frag=document.createDocumentFragment();
 if(!items.length){
  const valid=["wind","mag","kp","xray"].filter(k=>freshness(k,data[k])==="CURRENT").length;
  const msg=valid?"No configured public thresholds crossed in the currently validated measurements.":"No recent qualified measurements for threshold assessment; this is not an all-clear.";
  frag.append(el("p","empty",msg));
 }
 for(const signal of items){
  const card=el("div","signal "+signal.level),head=el("div","sigtitle");
  head.append(el("strong",null,signal.label),el("span",null,signal.value));card.append(head);
  card.append(el("p",null,signal.detail+" · "+utc(signal.observed)));
  const a=el("a",null,"OFFICIAL SOURCE ↗");a.href=signal.source;a.target="_blank";a.rel="noopener noreferrer";card.append(a);frag.append(card);
 }
 root.replaceChildren(frag);
}
async function collect(key){
 const ac=new AbortController();const timer=setTimeout(()=>ac.abort(),18000);
 try{
  const resp=await fetch(FEEDS[key],{mode:"cors",cache:"no-store",signal:ac.signal});
  if(!resp.ok)throw Error("HTTP "+resp.status);
  const doc=await resp.json();
  const parsed=parseFeed(key,doc);
  if(["wind","mag","kp","xray"].includes(key)&&!parsed.latest)throw Error("No valid instrument records");
  data[key]=parsed;sources[key]={ok:true,received:Date.now()};
 }catch(e){
  data[key]=null;
  const error=e?.name==="AbortError"?"18s source timeout":e instanceof Error?e.message.slice(0,120):"Source failed";
  sources[key]={ok:false,received:Date.now(),error};
 }finally{clearTimeout(timer);updateView();}
}
async function sweepFeeds(){
 if(state.running)return;
 state.running=true;state.lastRefresh=Date.now();$("refresh").disabled=true;text("refresh","SYNCING SOURCES...");
 text("last-sync","SWARM FETCH IN PROGRESS");
 try{await Promise.all(Object.keys(FEEDS).map(collect));}
 finally{
  state.running=false;$("refresh").disabled=false;text("refresh","↻ FETCH PUBLIC FEEDS");
  text("last-sync","LAST COMPLETED POLL: "+utc(Date.now()));updateView();
 }
}
function setScenario(){
 state.scenario=$("scenario-mode").checked;
 $("hyp-speed").disabled=!state.scenario;$("hyp-density").disabled=!state.scenario;
 showTelemetry();
}
function updateHyp(){
 text("hyp-speed-label",$("hyp-speed").value+" km/s");
 text("hyp-density-label",Number($("hyp-density").value).toFixed(1)+" /cc");
 if(state.scenario)showTelemetry();
}
function downloadSnapshot(){
 const snap=summarize(data);
 const file={
  schema:"XUNIA_SWARM_HIVE_SWEEP_PUBLIC_SCIENCE_V1",export_time:new Date().toISOString(),
  provenance:"USGS, NOAA Space Weather Prediction Center and NASA EONET public data",
  palantir_foundry_connection:"NONE",military_telemetry:"NONE",
  snapshot:snap,scenario_active:state.scenario,
  scenario_model:state.scenario?derivedModel(data,{scenario:true,windSpeed:Number($("hyp-speed").value),windDensity:Number($("hyp-density").value)}):null,
  latest_events:mapEvents(data).slice(0,150),
  source_records:Object.fromEntries(Object.keys(FEEDS).map(k=>[k,{url:FEEDS[k],agency:SOURCES[k].agency,
   retrieval:sources[k]?.received??null,source_timestamp:sourceTime(k,data[k]),status:freshness(k,data[k]),error:sources[k]?.error??null}]))
 };
 const blob=new Blob([JSON.stringify(file,null,2)],{type:"application/json"}),href=URL.createObjectURL(blob);
 const a=document.createElement("a");a.href=href;a.download="xunia-public-swamhive-physics-snapshot.json";
 document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(href),1500);
}
$("refresh").addEventListener("click",sweepFeeds);
for(const [id,layer] of [["layer-aurora","aurora"],["layer-quakes","earthquakes"],["layer-nasa","natural"],["layer-grid","graticule"]])
 $(id).addEventListener("change",()=>{renderer?.setLayer(layer,$(id).checked);updateView();});
$("rotate-left").addEventListener("click",()=>renderer?.rotate(0,-18));
$("rotate-right").addEventListener("click",()=>renderer?.rotate(0,18));
$("zoom-in").addEventListener("click",()=>renderer?.zoom(.12));
$("zoom-out").addEventListener("click",()=>renderer?.zoom(-.12));
$("reset-camera").addEventListener("click",()=>{renderer?.reset();state.orbit=false;$("auto-orbit").setAttribute("aria-pressed","false");text("auto-orbit","CAMERA ORBIT: OFF");});
$("auto-orbit").addEventListener("click",()=>{
 state.orbit=!state.orbit;renderer?.setOrbit(state.orbit);
 $("auto-orbit").setAttribute("aria-pressed",String(state.orbit));
 text("auto-orbit","CAMERA ORBIT: "+(state.orbit?"ON":"OFF"));
});
$("freeze").addEventListener("click",()=>{
 state.paused=!state.paused;renderer?.setPaused(state.paused);
 $("freeze").setAttribute("aria-pressed",String(state.paused));
 text("freeze","PAUSE VISUAL: "+(state.paused?"ON":"OFF"));
});
$("scenario-mode").addEventListener("change",setScenario);
for(const id of ["hyp-speed","hyp-density"])$(id).addEventListener("input",updateHyp);
$("export").addEventListener("click",downloadSnapshot);
$("export").disabled=true;
text("timestamp",utc(Date.now()));
setInterval(()=>{text("timestamp",utc(Date.now()));if(!state.scenario)showTelemetry();},60000);
setInterval(()=>{if(document.visibilityState==="visible")sweepFeeds();},POLL_MS);
document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible"&&Date.now()-state.lastRefresh>=POLL_MS)sweepFeeds();});
updateView();sweepFeeds();
