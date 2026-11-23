import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {FEEDS,SOURCES,POLL_MS,THRESHOLDS,parseFeed,sourceTime,freshness,measuredValues,solarWindPressure,standoffEstimate,transitEstimate,derivedModel,sweepSignals,mapEvents,auroraCells,subsolarPoint,projectOrthographic,summarize} from "../docs/darkweb/fieldlab/model-core.mjs";
const now=Date.parse("2026-11-22T21:00:00Z"),oneMinute=new Date(now-60000).toISOString();
function samples(){
 return {
  wind:parseFeed("wind",[{time_tag:oneMinute,speed:"500",density:"4.0"}]),
  mag:parseFeed("mag",[{time_tag:oneMinute,bz_gsm:"-11",bt:"16"}]),
  kp:parseFeed("kp",[{time_tag:oneMinute,Kp:5.33}]),
  xray:parseFeed("xray",[{time_tag:oneMinute,energy:"0.1-0.8nm",flux:2e-5}]),
  aurora:parseFeed("aurora",{"Observation Time":oneMinute,"Forecast Time":new Date(now).toISOString(),coordinates:[[220,65,70],[30,30,12]]}),
  usgs:parseFeed("usgs",{metadata:{generated:now},features:[{id:"us123",geometry:{type:"Point",coordinates:[-65,20,9]},properties:{time:now-2*60000,mag:5.6,title:"M5.6 source event",url:"https://earthquake.usgs.gov/earthquakes/eventpage/us123"}}]}),
  nasa:parseFeed("nasa",{events:[{id:"EONET_x",title:"Public natural event",categories:[{title:"Wildfires"}],geometry:[{type:"Point",coordinates:[-10,45],date:new Date(now-4*86400000).toISOString()}]}]})
 };
}
test("seven agency endpoints are HTTPS, keyless, and never connect to military services",()=>{
 assert.equal(Object.keys(FEEDS).length,7);assert.equal(POLL_MS,120000);
 for(const [k,url] of Object.entries(FEEDS)){
  assert.ok(url.startsWith("https://"));assert.ok(!/(?:token|apikey|api_key|secret)=/i.test(url));assert.ok(SOURCES[k]?.agency);
 }
});
test("NASA reference: solar wind dynamic pressure uses physical units and input boundaries",()=>{
 assert.ok(Math.abs(solarWindPressure(4,500)-1.67262192)<1e-10);
 assert.equal(solarWindPressure(null,500),null);
 assert.equal(solarWindPressure(-1,500),null);
 assert.equal(solarWindPressure(4,0),null);
 assert.equal(solarWindPressure(500,500),null);
 const p=solarWindPressure(5,400);
 assert.ok(Math.abs(standoffEstimate(2)-10)<1e-12);
 assert.ok(standoffEstimate(p)>0);
 assert.equal(standoffEstimate(null),null);
 assert.ok(Math.abs(transitEstimate(500)-50)<1e-9);
 assert.equal(transitEstimate(0),null);
});
test("one-minute instrument values validated and observed timestamps preserved",()=>{
 const d=samples(),m=measuredValues(d,now);
 assert.equal(m.speed,500);assert.equal(m.density,4);
 assert.equal(m.bz,-11);assert.equal(m.kp,5.33);
 assert.equal(m.flare,"M2.0");
 assert.equal(m.observed.wind,now-60000);
 assert.equal(sourceTime("usgs",d.usgs),now);
 assert.equal(sourceTime("nasa",d.nasa),null);
 assert.equal(freshness("nasa",d.nasa,now),"CATALOG RECEIVED");
 assert.equal(freshness("wind",d.wind,now),"CURRENT");
});
test("stale instruments produce no observed model even when old measurements remain in memory",()=>{
 const d=samples(),later=now+12*3600000,m=measuredValues(d,later);
 assert.equal(m.speed,null);assert.equal(m.flux,null);
 assert.equal(derivedModel(d,{now:later}).pressure,null);
 assert.equal(auroraCells(d,later).length,0);
 assert.equal(sweepSignals(d,later).length,0);
 assert.equal(freshness("usgs",d.usgs,later),"STALE");
});
test("scenario calculations never overwrite original observed readings",()=>{
 const d=samples(),original=measuredValues(d,now);
 const real=derivedModel(d,{now}),hypo=derivedModel(d,{now,scenario:true,windSpeed:1000,windDensity:10});
 assert.ok(hypo.pressure>real.pressure);
 assert.ok(hypo.standoff<real.standoff);
 assert.match(hypo.mode,/SCENARIO/);assert.match(real.mode,/PUBLIC OBSERVATIONS/);
 assert.deepEqual(measuredValues(d,now),original);
});
test("SWEEP uses disclosed sensor thresholds and does not invent events or infer causation",()=>{
 const d=samples(),signals=sweepSignals(d,now);
 assert.ok(signals.some(x=>x.kind==="Kp"));
 assert.ok(signals.some(x=>x.kind==="Bz"));
 assert.ok(signals.some(x=>x.kind==="xray"));
 assert.ok(signals.some(x=>x.kind==="usgs"));
 assert.ok(signals.every(x=>x.source.startsWith("https://")&&x.observed<=now));
 assert.equal(THRESHOLDS.solarWind,600);
 const blank={};assert.equal(sweepSignals(blank,now).length,0);
});
test("USGS and NASA events use published coordinates; aurora grid only when model current",()=>{
 const d=samples(),geo=mapEvents(d,{now});
 assert.equal(geo.length,2);
 assert.ok(geo.some(x=>x.kind==="earthquake"&&x.lon===-65&&x.lat===20));
 assert.ok(geo.some(x=>x.kind==="natural"&&x.lon===-10&&x.lat===45));
 assert.equal(auroraCells(d,now).length,2);
 assert.equal(auroraCells(d,now+12*3600000).length,0);
 assert.equal(mapEvents(d,{now,earthquakes:false}).length,1);
 assert.equal(mapEvents(d,{now,natural:false}).length,1);
});
test("UTC solar geometry is seasonally plausible; orthographic projection has a true invisible back side",()=>{
 const equinox=subsolarPoint(Date.parse("2026-03-20T15:46:00Z"));
 assert.ok(Math.abs(equinox.lat)<1.1);
 const june=subsolarPoint(Date.parse("2026-06-21T08:00:00Z"));
 assert.ok(june.lat>22&&june.lat<24.5);
 const centered=projectOrthographic(20,-65,20,-65);assert.ok(Math.abs(centered.x)<1e-12&&Math.abs(centered.y)<1e-12&&Math.abs(centered.z-1)<1e-12&&centered.visible);
 assert.equal(projectOrthographic(20,115,20,-65).visible,false);
 assert.equal(projectOrthographic(95,0,0,0),null);
});
test("summary differentiates agency source time, current measured data and model proxy",()=>{
 const d=samples(),s=summarize(d,now);
 assert.equal(s.counts.quakes,1);assert.equal(s.counts.natural,1);assert.equal(s.counts.aurora,2);
 assert.equal(s.measured.speed,500);
 assert.ok(Math.abs(s.model.pressure-1.67262192)<1e-10);
 assert.match(s.caveat,/military systems/);
});
test("static browser console has explicit source boundaries and no simulated-weapon APIs",()=>{
 const html=readFileSync(new URL("../docs/darkweb/fieldlab/index.html",import.meta.url),"utf8");
 const js=readFileSync(new URL("../docs/darkweb/fieldlab/fieldlab.mjs",import.meta.url),"utf8");
 for(const id of ["earth","refresh","model-chart","scenario-mode","hyp-speed","hyp-density","feeds","signals","inspected","export"])
  assert.ok(html.includes('id="'+id+'"'),id);
 for(const domain of ["services.swpc.noaa.gov","earthquake.usgs.gov","eonet.gsfc.nasa.gov"])
  assert.ok(html.includes(domain));
 assert.match(html,/no live weapons/i);
 for(const banned of ["innerHTML","WebSocket(","eval(","navigator.usb","navigator.serial","localStorage","sessionStorage"])
  assert.ok(!js.includes(banned),banned);
});
