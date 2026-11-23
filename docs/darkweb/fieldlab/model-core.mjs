// SWARM • HIVE • SWEEP: independent public-source heliophysics and geophysical modeling.
// No weapon system telemetry, operational military data, or implied live targeting.
import {FEEDS as SWPC,parseWind,parseMag,parseKp,parseXray,parseAurora,flareClass,classifyFreshness} from "../cosmos/feed-core.mjs";
import {FEEDS as EARTH,parseUSGS,parseNASA} from "../global/feed-core.mjs";
export const FEEDS=Object.freeze({...SWPC,usgs:EARTH.usgs,nasa:EARTH.nasa});
export const SOURCES=Object.freeze({
 wind:{label:"L1 PLASMA",agency:"NOAA SWPC",kind:"INSTRUMENT"},
 mag:{label:"INTERPLANETARY B",agency:"NOAA SWPC",kind:"INSTRUMENT"},
 kp:{label:"PLANETARY Kp",agency:"NOAA SWPC",kind:"INDEX"},
 xray:{label:"GOES X-RAY",agency:"NOAA SWPC",kind:"INSTRUMENT"},
 aurora:{label:"OVATION AURORA",agency:"NOAA SWPC",kind:"FORECAST MODEL"},
 usgs:{label:"GLOBAL EARTHQUAKES",agency:"USGS",kind:"EVENT CATALOG"},
 nasa:{label:"EONET NATURAL EVENTS",agency:"NASA EONET",kind:"EVENT CATALOG"}
});
export const POLL_MS=120000;
export const THRESHOLDS=Object.freeze({kp:5,bz:-10,solarWind:600,flare:1e-5,quake:5});
const clamp=(v,min,max)=>Math.min(max,Math.max(min,v));
export const finite=n=>typeof n==="number"&&Number.isFinite(n);
export function validateFeedName(name){if(!Object.hasOwn(FEEDS,name))throw Error("Unknown public source");return FEEDS[name];}
export function parseFeed(name,doc){
 validateFeedName(name);
 switch(name){
  case "wind":return parseWind(doc);
  case "mag":return parseMag(doc);
  case "kp":return parseKp(doc);
  case "xray":return parseXray(doc);
  case "aurora":return parseAurora(doc);
  case "usgs":return {events:parseUSGS(doc),generated:finite(doc?.metadata?.generated)?doc.metadata.generated:null};
  case "nasa":return parseNASA(doc);
  default:throw Error("Unsupported source");
 }
}
export function sourceTime(name,data){
 if(!data)return null;
 switch(name){
  case "wind":case "mag":case "kp":case "xray":return data.latest?.t??null;
  case "aurora":return data.observed??null;
  case "usgs":return data.generated??null;
  case "nasa":return null; // EONET may contain longstanding open events; retrieval ≠ observation
  default:return null;
 }
}
export function freshness(name,data,now=Date.now()){
 if(!data)return "UNAVAILABLE";
 if(name==="nasa")return "CATALOG RECEIVED"; // each event carries its own timestamp
 const t=sourceTime(name,data);
 if(!finite(t))return name==="usgs"?"RECEIVED / SOURCE TIME UNKNOWN":"UNKNOWN";
 if(name==="usgs"){
  if(t>now+15*60000)return "FUTURE";
  return now-t>30*60000?"STALE":"CURRENT";
 }
 return classifyFreshness(t,name,now);
}
export function measuredValues(data,now=Date.now()){
 const current=k=>freshness(k,data[k],now)==="CURRENT"?data[k]:null;
 const wind=current("wind")?.latest,mag=current("mag")?.latest,kp=current("kp")?.latest,xray=current("xray")?.latest;
 return Object.freeze({
  speed:finite(wind?.speed)?wind.speed:null,
  density:finite(wind?.density)?wind.density:null,
  bz:finite(mag?.bz)?mag.bz:null,
  bt:finite(mag?.bt)?mag.bt:null,
  kp:finite(kp?.kp)?kp.kp:null,
  flux:finite(xray?.flux)?xray.flux:null,
  flare:finite(xray?.flux)?flareClass(xray.flux):null,
  observed:{wind:wind?.t??null,mag:mag?.t??null,kp:kp?.t??null,xray:xray?.t??null}
 });
}
// NASA CCMC proton-only ram-pressure calculation. Density [cm^-3], speed [km/s], P [nPa].
// Helium, thermal pressure, IMF orientation and boundary dynamics are intentionally omitted.
export function solarWindPressure(density,speed){
 if(!finite(density)||!finite(speed)||density<0.05||density>200||speed<150||speed>2000)return null;
 return 1.67262192e-6*density*speed*speed;
}
// Pressure-only sixth-root sensitivity, normalized by definition to 10 Earth radii at 2 nPa.
// This is a *scenario/teaching approximation*, not a measured magnetopause or Shue model.
export function standoffEstimate(pressure){
 if(!finite(pressure)||pressure<=0)return null;
 return 10*Math.pow(2/pressure,1/6);
}
export function transitEstimate(speed){
 if(!finite(speed)||speed<150||speed>2000)return null;
 return 1500000/speed/60; // nominal 1.5 million km L1-to-Earth; not a forecast
}
export function derivedModel(data,{scenario=false,windSpeed=null,windDensity=null,now=Date.now()}={}){
 const measured=measuredValues(data,now);
 const speed=scenario?windSpeed:measured.speed,density=scenario?windDensity:measured.density;
 const pressure=solarWindPressure(density,speed);
 return {mode:scenario?"SCENARIO / USER INPUT":"DERIVED / PUBLIC OBSERVATIONS",
  speed:finite(speed)?speed:null,density:finite(density)?density:null,
  pressure,standoff:standoffEstimate(pressure),transit:transitEstimate(speed),
  assumption:"Proton-only dynamic pressure; nominal L1 distance; sixth-root pressure-only standoff proxy. This is not a measured boundary or prediction.",
  modelSource:"https://ccmc.gsfc.nasa.gov/seaesfc/ATR-2022-01665.pdf"};
}
const isRecent=(t,now,ms)=>finite(t)&&t<=now+5*60000&&now-t>=-5*60000&&now-t<=ms;
export function sweepSignals(data,now=Date.now()){
 const measured=measuredValues(data,now),signals=[];
 const add=(kind,label,value,level,observed,detail,source)=>signals.push({kind,label,value,level,observed,detail,source});
 if(measured.kp!==null&&measured.kp>=THRESHOLDS.kp)
  add("Kp","Geomagnetic disturbance threshold","Kp "+measured.kp.toFixed(2),"elevated",measured.observed.kp,
   "Observed NOAA Kp is at least 5; not a forecast of specific infrastructure impact.",FEEDS.kp);
 if(measured.bz!==null&&measured.bz<=THRESHOLDS.bz)
  add("Bz","Southward interplanetary magnetic field",measured.bz.toFixed(1)+" nT","watch",measured.observed.mag,
   "Southward Bz can favor magnetospheric coupling; an isolated reading does not predict a storm.",FEEDS.mag);
 if(measured.speed!==null&&measured.speed>=THRESHOLDS.solarWind)
  add("wind","Elevated solar-wind speed",measured.speed.toFixed(0)+" km/s","watch",measured.observed.wind,
   "Speed-only threshold from public L1 plasma; not a forecast.",FEEDS.wind);
 if(measured.flux!==null&&measured.flux>=THRESHOLDS.flare)
  add("xray","M-class or stronger X-ray flux",flareClass(measured.flux),"elevated",measured.observed.xray,
   "Observed NOAA/GOES long-band X-ray flux crosses the M-class threshold.",FEEDS.xray);
 const events=freshness("usgs",data.usgs,now)==="CURRENT"&&Array.isArray(data.usgs?.events)?data.usgs.events:[];
 for(const event of events.filter(e=>finite(e.magnitude)&&e.magnitude>=THRESHOLDS.quake&&isRecent(e.observed,now,3600000)).slice(0,7))
  add("usgs","Recent earthquake report","M"+event.magnitude.toFixed(1),"event",event.observed,
   event.title,FEEDS.usgs);
 return signals.sort((a,b)=>(b.observed||0)-(a.observed||0));
}
export function mapEvents(data,{earthquakes=true,natural=true,minMagnitude=3.5,now=Date.now()}={}){
 const out=[];
 if(earthquakes&&Array.isArray(data.usgs?.events))
  for(const e of data.usgs.events){
   if(!Array.isArray(e.coords)||!finite(e.coords[0])||!finite(e.coords[1])||!finite(e.magnitude)||e.magnitude<minMagnitude||!isRecent(e.observed,now,86400000))continue;
   out.push({id:e.id,kind:"earthquake",lat:e.coords[1],lon:e.coords[0],observed:e.observed,label:e.title,
    value:e.magnitude,source:e.url,sourceType:"OBSERVED EVENT",category:e.category});
  }
 if(natural&&Array.isArray(data.nasa?.events))
  for(const e of data.nasa.events){
   if(!Array.isArray(e.coords)||!finite(e.coords[0])||!finite(e.coords[1]))continue;
   out.push({id:e.id,kind:"natural",lat:e.coords[1],lon:e.coords[0],observed:e.observed,label:e.title,
    value:null,source:e.url,sourceType:"OPEN EVENT CATALOG / LOCATION LAST REPORTED",category:e.category});
  }
 return out.slice(0,200).sort((a,b)=>b.observed-a.observed);
}
export function auroraCells(data,now=Date.now()){
 if(freshness("aurora",data.aurora,now)!=="CURRENT")return [];
 return data.aurora.points||[];
}
// IAU-style low-precision solar ephemeris for Earth illumination; not a spacecraft ephemeris.
export function subsolarPoint(utcMillis){
 if(!finite(utcMillis))throw Error("Invalid clock");
 const jd=utcMillis/86400000+2440587.5,n=jd-2451545.0,d=Math.PI/180;
 const L=(280.460+0.9856474*n)*d,g=(357.528+0.9856003*n)*d;
 const lambda=L+(1.915*Math.sin(g)+0.020*Math.sin(2*g))*d;
 const eps=(23.439-0.0000004*n)*d;
 const dec=Math.asin(Math.sin(eps)*Math.sin(lambda));
 const ra=Math.atan2(Math.cos(eps)*Math.sin(lambda),Math.cos(lambda));
 const T=n/36525;
 const gmst=(280.46061837+360.98564736629*n+0.000387933*T*T-T*T*T/38710000)*d;
 const longitude=Math.atan2(Math.sin(ra-gmst),Math.cos(ra-gmst));
 return {lat:dec/d,lon:longitude/d};
}
export function projectOrthographic(lat,lon,cameraLat,cameraLon){
 if(![lat,lon,cameraLat,cameraLon].every(finite)||Math.abs(lat)>90||Math.abs(lon)>180)return null;
 const d=Math.PI/180,p=lat*d,l=cameraLat*d,delta=(lon-cameraLon)*d;
 const x=Math.cos(p)*Math.sin(delta),y=Math.sin(p)*Math.cos(l)-Math.cos(p)*Math.cos(delta)*Math.sin(l);
 const z=Math.sin(p)*Math.sin(l)+Math.cos(p)*Math.cos(delta)*Math.cos(l);
 return {x,y,z,visible:z>0};
}
export function summarize(data,now=Date.now()){
 const measured=measuredValues(data,now),model=derivedModel(data,{now}),signals=sweepSignals(data,now);
 return {measured,model,signals,sourceStatuses:Object.fromEntries(Object.keys(FEEDS).map(k=>[k,freshness(k,data[k],now)])),
  counts:{quakes:data.usgs?.events?.length??0,natural:data.nasa?.events?.length??0,aurora:auroraCells(data,now).length},
  caveat:"Instrument measurements and reported events have individual timestamps; model calculations and UI motion are not observations of military systems."};
}
