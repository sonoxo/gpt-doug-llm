import {FEEDS,POLL_MS,REFRESH_NEO_MS,parseWind,parseMag,parseKp,parseXray,parseAurora,parseNEO,flareClass,classifyFreshness,mapPoint} from "./feed-core.mjs";

const $=id=>document.getElementById(id),NS="http://www.w3.org/2000/svg";
const methods={wind:parseWind,mag:parseMag,kp:parseKp,xray:parseXray,aurora:parseAurora,neo:parseNEO};
const labels={wind:"SOLAR WIND",mag:"MAGNETIC FIELD",kp:"PLANETARY KP",xray:"GOES X-RAY",aurora:"OVATION AURORA",neo:"JPL CLOSE APPROACHES"};
const state={data:{},meta:{},running:false,latestRequest:0,lastNeoRequest:0};
const el=(tag,cls,value)=>{const node=document.createElement(tag);if(cls)node.className=cls;if(value!==undefined)node.textContent=String(value);return node;};
const svg=(tag,attrs={})=>{const e=document.createElementNS(NS,tag);for(const [k,v] of Object.entries(attrs))e.setAttribute(k,String(v));return e;};
const utc=t=>Number.isFinite(t)?new Date(t).toISOString().slice(0,19).replace("T"," ")+" UTC":"—";
const number=(n,d=0)=>typeof n==="number"&&Number.isFinite(n)?n.toFixed(d):"—";
const put=(id,value)=>{$(id).textContent=value;};
function originTime(kind){
 const d=state.data[kind];return kind==="aurora"?d?.observed:kind==="neo"?state.meta[kind]?.received:d?.latest?.t;
}
function status(kind){
 const m=state.meta[kind],data=state.data[kind];
 if(!m||!m.ok||!data)return "FAILED";
 if(kind==="neo")return "FORECAST";
 return classifyFreshness(originTime(kind),kind);
}
function sourceStatus(){
 const frag=document.createDocumentFragment();
 for(const kind of Object.keys(FEEDS)){
  const m=state.meta[kind],statusValue=status(kind);
  const card=el("div","feed"),top=el("div","feed-top");
  const link=el("a",null,labels[kind]+" ↗");link.href=FEEDS[kind];link.target="_blank";link.rel="noopener noreferrer";
  const flag=el("span","indicator "+(statusValue==="CURRENT"||statusValue==="FORECAST"?"current":statusValue==="FAILED"?"failed":""),statusValue);
  top.append(link,flag);card.append(top);
  let sub="Not fetched yet";
  if(m?.ok)sub="Retrieved "+utc(m.received)+" · source "+utc(originTime(kind))+(kind==="neo"?" (forecast catalog; receipt ≠ observation)":"");
  if(m&&!m.ok)sub="Unavailable: "+m.error+" · no values substituted";
  if(m?.ok&&statusValue==="STALE")sub+=" · STALE: outside freshness window";
  card.append(el("p",null,sub));frag.append(card);
 }
 $("feeds").replaceChildren(frag);
 const available=Object.keys(FEEDS).filter(k=>status(k)==="CURRENT"||status(k)==="FORECAST").length;
 put("overall-state",available+"/"+Object.keys(FEEDS).length+" SOURCES VALID");
 $("status-light").className=available===6?"online":available?"partial":"";
}
function applyMetric(id,value,kind){put(id,status(kind)==="CURRENT"?value:"—");}
function initializeGrid(){
 const g=$("lat-lines");
 for(let x=0;x<=1000;x+=100)g.append(svg("line",{x1:x,y1:0,x2:x,y2:500}));
 for(let y=0;y<=500;y+=50)g.append(svg("line",{x1:0,y1:y,x2:1000,y2:y}));
}
function paintAurora(){
 const d=state.data.aurora,valid=status("aurora")==="CURRENT";
 const group=$("aurora-points");group.replaceChildren();
 if(valid){
  const frag=document.createDocumentFragment();
  for(const p of d.points){
   const mapped=mapPoint(p.lon,p.lat),intensity=p.intensity;
   const color=intensity>=55?"#daff6b":intensity>=25?"#5affd5":"#36b9df";
   const c=svg("circle",{cx:mapped.x,cy:mapped.y,r:intensity>=55?3.8:intensity>=25?2.6:1.8,fill:color,opacity:Math.min(.88,Math.max(.25,intensity/100)),class:"aurora-dot"+(intensity>=55?" high":"")});
   const tip=svg("title");tip.textContent="NOAA OVATION intensity "+intensity+" at "+p.lat+"° latitude, "+p.lon+"° longitude";c.append(tip);
   frag.append(c);
  }
  group.append(frag);
 }
 put("metric-aurora",valid?String(d.points.length):"—");
 put("aurora-state",valid?"CURRENT MODEL · "+d.points.length+" GRID CELLS":"NO CURRENT AURORA MODEL · "+status("aurora"));
 put("aurora-observed","OBSERVED: "+utc(d?.observed));put("aurora-forecast","FORECAST: "+utc(d?.forecast));
}
function drawPlot(id,values){
 const poly=$(id),box=poly.ownerSVGElement,group=box.querySelector(".plotgrid");
 if(!group.childNodes.length){
  const frag=document.createDocumentFragment();
  for(let y=15;y<=110;y+=24)frag.append(svg("line",{x1:0,y1:y,x2:600,y2:y}));
  group.append(frag);
 }
 if(!Array.isArray(values)||values.length<2){poly.setAttribute("points","");return;}
 const v=values.filter(Number.isFinite).slice(-150);
 if(v.length<2){poly.setAttribute("points","");return;}
 const min=Math.min(...v),max=Math.max(...v),span=Math.max(max-min,.00000001);
 const points=v.map((n,i)=>(10+i*580/(v.length-1)).toFixed(1)+","+(110-(n-min)*93/span).toFixed(1)).join(" ");
 poly.setAttribute("points",points);
}
function metrics(){
 const wind=state.data.wind?.latest,mag=state.data.mag?.latest,kp=state.data.kp?.latest,xray=state.data.xray?.latest;
 applyMetric("metric-speed",number(wind?.speed,0),"wind");applyMetric("wind-speed",number(wind?.speed,0)+" km/s","wind");
 applyMetric("wind-density",number(wind?.density,1)+" /cc","wind");
 applyMetric("metric-bz",number(mag?.bz,1),"mag");applyMetric("mag-bz",number(mag?.bz,1)+" nT","mag");
 applyMetric("metric-kp",number(kp?.kp,1),"kp");applyMetric("kp-value",number(kp?.kp,2),"kp");
 applyMetric("metric-flare",flareClass(xray?.flux),"xray");applyMetric("xray-value",flareClass(xray?.flux),"xray");
 put("metric-neo",status("neo")==="FORECAST"?String(state.data.neo.length):"—");
 if(status("wind")==="CURRENT")drawPlot("wind-line",state.data.wind.series.map(x=>x.speed).filter(Number.isFinite));
 else drawPlot("wind-line",[]);
 if(status("kp")==="CURRENT")drawPlot("kp-line",state.data.kp.series.map(x=>x.kp).filter(Number.isFinite));
 else drawPlot("kp-line",[]);
 put("wind-state","WIND "+status("wind")+" · "+utc(wind?.t)+" / MAG "+status("mag")+" · "+utc(mag?.t));
 put("radiation-state","Kp "+status("kp")+" · "+utc(kp?.t)+" / X-RAY "+status("xray")+" · "+utc(xray?.t));
 paintAurora();
}
function renderNEO(){
 const panel=$("neo-list");panel.replaceChildren();
 if(status("neo")!=="FORECAST"){put("neo-state","NASA/JPL catalog unavailable; no simulated asteroid flybys.");return;}
 const d=state.data.neo;
 for(const item of d.slice(0,20)){
  const row=el("div","neo-row"),name=el("strong",null,item.designation),date=el("span",null,item.date),dist=el("span",null,number(item.distanceAu,5)+" AU"),speed=el("small",null,number(item.speedKms,1)+" km/s");
  row.append(name,date,dist,speed);panel.append(row);
 }
 if(d.length===0)panel.append(el("p","source-status","No close approaches in the current JPL response."));
 put("neo-state","NASA/JPL close-approach forecast · "+d.length+" returned entries · retrieved "+utc(state.meta.neo.received)+" · NOT live observation");
}
function render(){metrics();renderNEO();sourceStatus();}
async function collect(kind){
 const controller=new AbortController(),timeout=setTimeout(()=>controller.abort(),18000);
 try{
  const response=await fetch(FEEDS[kind],{mode:"cors",cache:"no-store",signal:controller.signal});
  if(!response.ok)throw new Error("HTTP "+response.status);
  const raw=await response.json(),data=methods[kind](raw);
  if(kind!=="aurora"&&kind!=="neo"&&!data.latest)throw new Error("No valid instrument measurements");
  state.data[kind]=data;state.meta[kind]={ok:true,received:Date.now()};
 }catch(error){
  state.data[kind]=null;state.meta[kind]={ok:false,received:Date.now(),error:error?.name==="AbortError"?"request timeout":error instanceof Error?error.message:"fetch failed"};
 }finally{clearTimeout(timeout);}
}
async function update(){
 if(state.running)return;
 state.running=true;put("refresh","SYNCING…");$("refresh").disabled=true;
 const now=Date.now();state.latestRequest=now;
 const jobs=Object.keys(FEEDS).filter(kind=>kind!=="neo"||!state.lastNeoRequest||now-state.lastNeoRequest>=REFRESH_NEO_MS);
 if(jobs.includes("neo"))state.lastNeoRequest=now;
 await Promise.all(jobs.map(collect));
 render();state.running=false;$("refresh").disabled=false;put("refresh","↻ SYNCHRONIZE FEEDS");
}
function refreshClock(){put("local-clock",new Date().toLocaleString([], {hour:"2-digit",minute:"2-digit",second:"2-digit",timeZoneName:"short"}));}
function initSDO(){
 const image=$("sun-image");
 image.addEventListener("load",()=>{put("sun-status","NASA SDO image retrieved · acquisition age unknown");});
 image.addEventListener("error",()=>{image.hidden=true;put("sun-status","NASA SDO image unavailable · no substitute");});
 if(image.complete&&image.naturalWidth>0)put("sun-status","NASA SDO image retrieved · acquisition age unknown");
}
initializeGrid();initSDO();refreshClock();setInterval(refreshClock,1000);
$("refresh").addEventListener("click",update);
setInterval(()=>{if(document.visibilityState==="visible")update();},POLL_MS);
document.addEventListener("visibilitychange",()=>{if(document.visibilityState==="visible"&&Date.now()-state.latestRequest>=POLL_MS)update();});
sourceStatus();update();
