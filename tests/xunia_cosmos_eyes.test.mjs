import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {FEEDS,POLL_MS,parseWind,parseMag,parseKp,parseXray,flareClass,parseAurora,classifyFreshness,mapPoint,timestamp} from "../docs/darkweb/cosmos/feed-core.mjs";
const now=Date.parse("2026-11-22T02:30:00Z");
const t="2026-11-22T02:29:00Z";
test("five NOAA public instrument endpoints use TLS and have no keys or targets",()=>{
 assert.equal(Object.keys(FEEDS).length,5);assert.equal(POLL_MS,120000);
 for(const url of Object.values(FEEDS)){assert.ok(url.startsWith("https://"));assert.ok(!/apikey=|api_key=|token=|password=|target=/i.test(url));}
});
test("ISO timestamps are UTC and invalid or missing timestamps are rejected",()=>{
 assert.equal(timestamp("2026-11-22T02:29:00"),now-60000);
 assert.equal(timestamp(t),now-60000);assert.equal(timestamp("nonsense"),null);assert.equal(timestamp(null),null);
});
test("real-time solar wind and magnetic field readings are normalized without fabricated values",()=>{
 const wind=parseWind([{time_tag:t,speed:"441.5",density:"4.2"},{time_tag:"n/a",speed:990},{time_tag:"2026-11-22T02:20:00Z",speed:"409",density:null}]);
 assert.equal(wind.series.length,2);assert.equal(wind.latest.speed,441.5);assert.equal(wind.latest.density,4.2);
 const mag=parseMag([{time_tag:t,bz_gsm:"-6.3",bt:"12.1"}]);
 assert.equal(mag.latest.bz,-6.3);assert.equal(mag.latest.bt,12.1);
 assert.throws(()=>parseWind({items:[]}),/format/);assert.throws(()=>parseMag("oops"),/format/);
});
test("Kp supports 2026 object format and older header-row schema",()=>{
 assert.equal(parseKp([{time_tag:t,Kp:3.67}]).latest.kp,3.67);
 assert.equal(parseKp([["time_tag","Kp"],[t,"4.3"]]).latest.kp,4.3);
 assert.equal(parseKp([{time_tag:t,Kp:300}]).latest,null);
});
test("GOES long-band X-rays and real solar flare classes",()=>{
 const d=parseXray([{time_tag:t,flux:9e-6,energy:"0.05-0.4nm"},{time_tag:t,flux:2.7e-5,energy:"0.1-0.8nm",satellite:"19"}]);
 assert.equal(d.series.length,1);assert.equal(flareClass(d.latest.flux),"M2.7");
 assert.equal(flareClass(1.2e-4),"X1.2");assert.equal(flareClass(null),"—");
 assert.equal(flareClass(-1),"—");
});
test("OVATION uses only source grid locations and rejects invalid data",()=>{
 const d=parseAurora({"Observation Time":"2026-11-22T02:00:00Z","Forecast Time":"2026-11-22T02:30:00Z",coordinates:[[220,65,70],[40,-60,14],[-240,90,80],[10,12,4]]});
 assert.equal(d.points.length,2);assert.deepEqual(d.points[0],{lon:-140,lat:65,intensity:70});
 assert.deepEqual(mapPoint([-140,65][0],65),{x:40*1000/360,y:25*500/180});
 assert.throws(()=>parseAurora({coordinates:[]}),/missing observation/);
 assert.throws(()=>parseAurora({foo:1}),/format/);
});
test("NASA/JPL terms are respected: no browser CAD API request or fake asteroid coordinates",()=>{
 const html=readFileSync(new URL("../docs/darkweb/cosmos/index.html",import.meta.url),"utf8");
 const js=readFileSync(new URL("../docs/darkweb/cosmos/cosmos.mjs",import.meta.url),"utf8");
 assert.ok(html.includes('https://cneos.jpl.nasa.gov/ca/'));
 assert.ok(!html.includes('connect-src \'self\' https://services.swpc.noaa.gov https://ssd-api.jpl.nasa.gov'));
 assert.ok(!js.includes('ssd-api.jpl.nasa.gov'));
 assert.ok(!Object.keys(FEEDS).includes("neo"));
});
test("freshness gates distinguish observation time from device clock",()=>{
 assert.equal(classifyFreshness(now-20*60000,"wind",now),"CURRENT");
 assert.equal(classifyFreshness(now-60*60000,"wind",now),"STALE");
 assert.equal(classifyFreshness(now+3600000,"kp",now),"FUTURE");
 assert.equal(classifyFreshness(NaN,"mag",now),"UNKNOWN");
});
test("COSMOS EYES static app has source-bound CSP and no synthetic values",()=>{
 const html=readFileSync(new URL("../docs/darkweb/cosmos/index.html",import.meta.url),"utf8");
 const js=readFileSync(new URL("../docs/darkweb/cosmos/cosmos.mjs",import.meta.url),"utf8");
 for(const s of ['Content-Security-Policy','id="aurora-map"','id="neo-list"','id="sun-image"','id="refresh"','id="feeds"'])assert.ok(html.includes(s),s);
 assert.match(html,/not live telescope detections/i);assert.match(html,/does not detect aliens\/UAPs/i);
 for(const forbidden of ["innerHTML","WebSocket(","eval(","localStorage","sessionStorage","setInterval(()=>location.reload"])assert.ok(!js.includes(forbidden),forbidden);
 assert.ok(js.includes("Promise.all(jobs.map(collect))"));
});
