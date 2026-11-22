// GLASS ONION / GLOBAL OBSERVATORY. Pure, no credentials or backend access.
export const FEEDS=Object.freeze({
  usgs:"https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
  nasa:"https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=200",
  cisa:"https://raw.githubusercontent.com/cisagov/kev-data/develop/known_exploited_vulnerabilities.json"
});
export const REFRESH_MS=300000;
const text=(v,n=180)=>typeof v==="string"?v.trim().slice(0,n):"";
const num=v=>typeof v==="number"&&Number.isFinite(v)?v:null;
const time=v=>{const d=typeof v==="number"?v:Date.parse(v||"");return Number.isFinite(d)&&d>0?d:null;};
export function validCoordinates(coords){
  return Array.isArray(coords)&&num(coords[0])!==null&&num(coords[1])!==null&&coords[0]>=-180&&coords[0]<=180&&coords[1]>=-90&&coords[1]<=90;
}
export function project(coords){
  if(!validCoordinates(coords))throw new Error("Invalid geographic coordinates");
  return {x:(coords[0]+180)*1000/360,y:(90-coords[1])*500/180};
}
const dedupe=(arr)=>{const seen=new Set();return arr.filter(x=>{if(seen.has(x.id))return false;seen.add(x.id);return true;});};
export function parseUSGS(doc){
  if(!doc||!Array.isArray(doc.features))throw new Error("USGS feed format changed");
  const events=[];
  for(const f of doc.features.slice(0,1600)){
    const p=f?.properties||{},g=f?.geometry,id=text(f?.id,90);
    if(!id||g?.type!=="Point"||!validCoordinates(g.coordinates))continue;
    const observed=time(p.time),magnitude=num(p.mag);
    if(!observed)continue;
    events.push({id:"usgs:"+id,kind:"earthquake",feed:"usgs",title:text(p.title)||"USGS recorded earthquake",
      observed,coords:g.coordinates.slice(0,2),category:"Earthquake",magnitude,
      url:/^https:\/\/earthquake\.usgs\.gov\//.test(p.url||"")?p.url:"https://earthquake.usgs.gov/earthquakes/",
      detail:magnitude!==null?"Magnitude "+magnitude.toFixed(1):"Magnitude not reported"});
  }
  return dedupe(events).sort((a,b)=>b.observed-a.observed).slice(0,600);
}
export function parseNASA(doc){
  if(!doc||!Array.isArray(doc.events))throw new Error("NASA EONET feed format changed");
  const events=[];let unmapped=0;
  for(const e of doc.events.slice(0,500)){
    const id=text(e?.id,90);if(!id)continue;
    const locations=Array.isArray(e.geometry)?e.geometry:[];
    const point=locations.slice().reverse().find(g=>g.type==="Point"&&validCoordinates(g.coordinates));
    if(!point){unmapped++;continue;}
    const observed=time(point.date)||time(e.closed);
    if(!observed)continue;
    const cats=Array.isArray(e.categories)?e.categories:[];
    const category=text(cats[0]?.title,70)||"Natural event";
    const slug=encodeURIComponent(id);
    events.push({id:"nasa:"+id,kind:"natural",feed:"nasa",title:text(e.title)||"NASA tracked natural event",
      observed,coords:point.coordinates.slice(0,2),category,magnitude:null,
      url:"https://eonet.gsfc.nasa.gov/api/v3/events/"+slug,detail:"Open EONET event · "+category});
  }
  return {events:dedupe(events).sort((a,b)=>b.observed-a.observed),unmapped};
}
export function parseCISA(doc){
  if(!doc||!Array.isArray(doc.vulnerabilities))throw new Error("CISA KEV feed format changed");
  return doc.vulnerabilities.map(v=>{
    const cve=text(v?.cveID,22);
    if(!/^CVE-\d{4}-\d{4,}$/i.test(cve))return null;
    return {id:cve,feed:"cisa",title:text(v.vulnerabilityName)||cve,
      vendor:text(v.vendorProject,90),product:text(v.product,90),added:text(v.dateAdded,15),
      url:"https://www.cve.org/CVERecord?id="+encodeURIComponent(cve)};
  }).filter(Boolean).sort((a,b)=>b.added.localeCompare(a.added)||a.id.localeCompare(b.id)).slice(0,150);
}
export function filterEvents(events,{kind="all",query="",timeWindow="all",minMagnitude=0,now=Date.now()}={}){
  const q=String(query).trim().toLowerCase().slice(0,120);
  const since=timeWindow==="day"?now-86400000:timeWindow==="week"?now-604800000:null;
  return events.filter(e=>(kind==="all"||e.feed===kind)
   &&(since===null||e.observed>=since)
   &&(e.kind!=="earthquake"||(e.magnitude??0)>=minMagnitude)
   &&(!q||[e.title,e.category,e.detail,e.id].some(v=>String(v).toLowerCase().includes(q))));
}
export function freshLabel(observed,now=Date.now()){
  if(!Number.isFinite(observed))return "Unknown observation time";
  const mins=Math.max(0,Math.round((now-observed)/60000));
  return mins<60?mins+"m ago":mins<1440?Math.floor(mins/60)+"h ago":Math.floor(mins/1440)+"d ago";
}
