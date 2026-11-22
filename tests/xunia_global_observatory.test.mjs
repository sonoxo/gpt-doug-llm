import test from "node:test";
import assert from "node:assert/strict";
import {readFileSync} from "node:fs";
import {FEEDS,REFRESH_MS,parseUSGS,parseNASA,parseCISA,filterEvents,project,validCoordinates} from "../docs/darkweb/global/feed-core.mjs";

const observed=Date.parse("2026-11-21T23:00:00Z");
const usgs={metadata:{generated:observed},features:[
 {id:"abc1",geometry:{type:"Point",coordinates:[-70,40,4]},properties:{title:"M 4.9 - test",mag:4.9,time:observed,url:"https://earthquake.usgs.gov/earthquakes/eventpage/abc1"}},
 {id:"abc1",geometry:{type:"Point",coordinates:[-70,40]},properties:{title:"duplicate",mag:2,time:observed}},
 {id:"bad",geometry:{type:"Point",coordinates:[999,30]},properties:{time:observed}},
 {id:"abc2",geometry:{type:"Point",coordinates:[140,-20]},properties:{title:"M 2.0 - other",mag:2,time:observed-3600000,url:"https://attacker.invalid"}}]};
const nasa={events:[
 {id:"EONET1",title:"Wildfires / sample",categories:[{id:"wildfires",title:"Wildfires"}],geometry:[{type:"Point",coordinates:[10,30],date:"2026-11-20T23:00:00Z"},{type:"Point",coordinates:[12,32],date:"2026-11-21T23:00:00Z"}]},
 {id:"POLY",title:"Polygon event",categories:[],geometry:[{type:"Polygon",coordinates:[[[10,30],[11,30],[10,31]]],date:"2026-11-21T23:00:00Z"}]}]};
const cisa={vulnerabilities:[{cveID:"CVE-2026-12345",vulnerabilityName:"Public vulnerability",vendorProject:"Vendor",product:"Product",dateAdded:"2026-11-20"},{cveID:"CVE-2026-0001",vulnerabilityName:"Older",vendorProject:"Other",product:"Tool",dateAdded:"2026-10-11"},{cveID:"OTHER",dateAdded:"2026-11-21"}]};

test("official-source endpoints have no tokens, target parameters or commercial dependencies",()=>{
 assert.equal(REFRESH_MS,300000);
 for(const [name,url] of Object.entries(FEEDS)){
  assert.match(url,/^https:\/\//);assert.ok(["usgs","nasa","cisa"].includes(name));assert.ok(!/token=|apikey=|api_key=|target=/i.test(url));
 }
});
test("USGS geolocations are real source coordinates, deduped and URL-bound",()=>{
 const out=parseUSGS(usgs);assert.equal(out.length,2);assert.equal(out[0].id,"usgs:abc1");
 assert.deepEqual(out[0].coords,[-70,40]);assert.equal(out[0].magnitude,4.9);
 assert.equal(out[1].url,"https://earthquake.usgs.gov/earthquakes/");
 assert.throws(()=>parseUSGS({foo:1}),/format changed/);
});
test("NASA uses latest valid point only; polygon does not generate a fake centroid",()=>{
 const out=parseNASA(nasa);assert.equal(out.events.length,1);assert.equal(out.unmapped,1);
 assert.deepEqual(out.events[0].coords,[12,32]);assert.equal(out.events[0].category,"Wildfires");
 assert.equal(out.events[0].url,"https://eonet.gsfc.nasa.gov/api/v3/events/EONET1");
 assert.throws(()=>parseNASA({events:null}),/format changed/);
});
test("CISA records stay nongeographic with only CVE source URLs",()=>{
 const out=parseCISA(cisa);assert.equal(out.length,2);assert.equal(out[0].id,"CVE-2026-12345");
 assert.ok(!("coords" in out[0]));assert.ok(out.every(x=>x.url.startsWith("https://www.cve.org/CVERecord?id=")));
 assert.throws(()=>parseCISA({vulnerabilities:null}),/format changed/);
});
test("location projection maps world bounds; rejects invalid source coordinates",()=>{
 assert.deepEqual(project([-180,90]),{x:0,y:0});assert.deepEqual(project([180,-90]),{x:1000,y:500});
 assert.deepEqual(project([0,0]),{x:500,y:250});assert.equal(validCoordinates([181,0]),false);
 assert.throws(()=>project([181,0]),/Invalid geographic/);
});
test("filters are geographic, time-window-aware, thresholded and case-insensitive",()=>{
 const events=[...parseUSGS(usgs),...parseNASA(nasa).events],now=observed+1000;
 assert.equal(filterEvents(events,{now}).length,3);
 assert.equal(filterEvents(events,{kind:"usgs",minMagnitude:4.5,now}).length,1);
 assert.equal(filterEvents(events,{kind:"nasa",query:"wildfires",now}).length,1);
 assert.equal(filterEvents(events,{timeWindow:"day",now}).length,2);
 assert.equal(filterEvents(events,{query:"<img>",now}).length,0);
});
test("static interface enforces explicit live-source-only geolocation and CSP",()=>{
 const html=readFileSync(new URL("../docs/darkweb/global/index.html",import.meta.url),"utf8");
 const app=readFileSync(new URL("../docs/darkweb/global/global.mjs",import.meta.url),"utf8");
 for(const v of ["Content-Security-Policy",'id="world"','id="source-cisa"','id="source-usgs"','id="source-nasa"','id="auto"','id="export"'])
   assert.ok(html.includes(v),v);
 assert.match(html,/No cyberattack dots are inferred/);
 assert.ok(app.includes("fetch(FEEDS[name]"));
 assert.ok(!app.includes("innerHTML"));
 assert.ok(!app.includes("localStorage"));
 assert.ok(!app.includes("WebSocket("));
});
