// GLASS ONION // COSMOS EYES
// Public-source adapters. No simulated measurements or generated extraterrestrial events.
export const FEEDS=Object.freeze({
  wind:"https://services.swpc.noaa.gov/json/rtsw/rtsw_wind_1m.json",
  mag:"https://services.swpc.noaa.gov/json/rtsw/rtsw_mag_1m.json",
  kp:"https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json",
  xray:"https://services.swpc.noaa.gov/json/goes/primary/xrays-1-day.json",
  aurora:"https://services.swpc.noaa.gov/json/ovation_aurora_latest.json"
});
export const POLL_MS=120000;
export const DISPLAY_LIMIT=2200;
export const LIMITS=Object.freeze({wind:45*60000,mag:45*60000,kp:6*3600000,xray:60*60000,aurora:3*3600000});
const str=(v,n=170)=>typeof v==="string"?v.trim().slice(0,n):"";
const numeric=v=>v===null||v===undefined||v===""?null:Number.isFinite(Number(v))?Number(v):null;
const first=(o,keys)=>keys.map(k=>o?.[k]).find(v=>numeric(v)!==null);
export function timestamp(raw){
 if(typeof raw==="number")return Number.isFinite(raw)?raw:null;
 if(typeof raw!=="string"||!raw.trim())return null;
 const s=raw.trim(),iso=/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?$/.test(s)?s+"Z":s;
 const n=Date.parse(iso);return Number.isFinite(n)?n:null;
}
function recent(records,select,cap=1600){
 if(!Array.isArray(records))throw new Error("Unexpected data source format");
 const out=[];
 for(const raw of records.slice(-cap)){const r=select(raw);if(r)out.push(r);}
 return out.sort((a,b)=>a.t-b.t);
}
function record(raw,fields){
 const t=timestamp(raw?.time_tag||raw?.time||raw?.timestamp);
 if(!t)return null;
 const v=fields(raw);return v?{t,...v}:null;
}
export function parseWind(data){
 const series=recent(data,r=>record(r,x=>{
  const speed=numeric(first(x,["speed","speed_km_s","speed_kms"]));
  const density=numeric(first(x,["density","proton_density"]));
  if(speed===null&&density===null)return null;
  return {speed:speed!==null&&speed>=0&&speed<5000?speed:null,density:density!==null&&density>=0&&density<100000?density:null};
 }));
 return {series,latest:series.at(-1)||null};
}
export function parseMag(data){
 const series=recent(data,r=>record(r,x=>{
  const bz=numeric(first(x,["bz_gsm","bz","bz_gse"]));
  const bt=numeric(first(x,["bt","bt_total"]));
  if(bz===null&&bt===null)return null;
  return {bz:bz!==null&&Math.abs(bz)<3000?bz:null,bt:bt!==null&&bt>=0&&bt<3000?bt:null};
 }));
 return {series,latest:series.at(-1)||null};
}
export function parseKp(data){
 if(!Array.isArray(data))throw new Error("Unexpected Kp format");
 const rows=data.length&&Array.isArray(data[0])&&typeof data[0][0]==="string"&&!timestamp(data[0][0])
  ?data.slice(1).map(row=>Object.fromEntries(data[0].map((k,i)=>[k,row[i]]))):data;
 const series=recent(rows,r=>record(r,x=>{
  const kp=numeric(first(x,["Kp","kp","kp_index","estimated_kp"]));
  return kp!==null&&kp>=0&&kp<=9?{kp}:null;
 }));
 return {series,latest:series.at(-1)||null};
}
export function parseXray(data){
 const all=recent(data,r=>record(r,x=>{
  const flux=numeric(first(x,["flux","observed_flux"]));
  if(flux===null||flux<0||flux>1)return null;
  return {flux,energy:str(x.energy,40),satellite:str(String(x.satellite??""),16)};
 }),5000);
 const preferred=all.filter(x=>/0\.1\s*-\s*0\.8\s*nm/i.test(x.energy));
 const series=preferred.length?preferred:all;
 return {series,latest:series.at(-1)||null};
}
export function flareClass(flux){
 if(typeof flux!=="number"||!Number.isFinite(flux)||flux<=0)return "—";
 const bases=[["X",1e-4],["M",1e-5],["C",1e-6],["B",1e-7],["A",1e-8]];
 for(const [label,value] of bases)if(flux>=value)return label+(flux/value).toFixed(1);
 return "<A1";
}
export function parseAurora(data){
 if(!data||!Array.isArray(data.coordinates))throw new Error("Unexpected NOAA aurora format");
 const observed=timestamp(data["Observation Time"]||data.observation_time||data.observationTime);
 const forecast=timestamp(data["Forecast Time"]||data.forecast_time||data.forecastTime);
 if(!observed&&!forecast)throw new Error("Aurora feed missing observation/forecast times");
 const points=[];
 // Data are indexed on a one-degree grid; threshold and sampling bound DOM size.
 for(const point of data.coordinates){
  if(!Array.isArray(point)||point.length<3)continue;
  let [lon,lat,intensity]=point.map(numeric);
  if(lon===null||lat===null||intensity===null||lat < -90||lat>90||lon < -180||lon>360||intensity<0||intensity>100)continue;
  if(lon>180)lon-=360;
  if(intensity<8)continue;
  points.push({lon,lat,intensity});
 }
 points.sort((a,b)=>b.intensity-a.intensity);
 return {observed,forecast,points:points.slice(0,DISPLAY_LIMIT),totalAboveThreshold:points.length};
}
export function classifyFreshness(time,kind,now=Date.now()){
 const age=now-time;
 if(!Number.isFinite(time)||!Number.isFinite(age))return "UNKNOWN";
 if(age< -15*60000)return "FUTURE";
 if(age>LIMITS[kind])return "STALE";
 return "CURRENT";
}
export function mapPoint(lon,lat){
 if(!Number.isFinite(lon)||!Number.isFinite(lat)||lon < -180||lon>180||lat < -90||lat>90)throw new Error("Invalid world coordinate");
 return {x:(lon+180)*1000/360,y:(90-lat)*500/180};
}
export function summary(data){
 return Object.fromEntries(Object.entries(data).map(([kind,value])=>[kind,kind==="aurora"?value?.points.length??0:value?.series.length??0]));
}
