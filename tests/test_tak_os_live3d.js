'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path=require('node:path');
const O=require(path.resolve(__dirname,'../docs/tak-os/live-3d/ontology.js'));
const clock=Date.parse('2026-10-13T18:00:00Z');
const ts='2026-10-13T17:30:00Z';
test('no observations are seeded in a new ontology',()=>{
 const graph=new O.Ontology(()=>clock);
 assert.equal(graph.records.size,0);assert.equal(graph.current('usgs').length,0);
 assert.equal(graph.status('usgs').state,'NOT_CONNECTED');
 assert.equal(graph.exportJsonLD()['@graph'].length,5); // Source types only, no events.
});
test('USGS position and source record timestamps are verified, never fabricated',()=>{
 const payload={features:[{id:'us100',properties:{place:'Recorded event',time:clock-1800000,mag:4.4,url:'https://earthquake.usgs.gov/earthquakes/eventpage/us100'},geometry:{type:'Point',coordinates:[-123,42,11]}},
 {id:'invalid',properties:{time:clock},geometry:{type:'Point',coordinates:[200,95,2]}}]};
 const records=O.parseUsgs(payload,ts);
 assert.equal(records.length,1);assert.equal(records[0].geometry.point.lat,42);
 assert.equal(records[0].sourceUrl,'https://earthquake.usgs.gov/earthquakes/eventpage/us100');
 assert.equal(records[0].observationTime,new Date(ts).toISOString());assert.equal(records[0].properties.depthKm,11);
});
test('NASA EONET source geometry, time, polygon centroid declared as derived',()=>{
 const payload={events:[{id:'EONET-1',title:'Real provider test fixture',closed:null,categories:[{id:'wildfires'}],geometry:[{date:ts,type:'Polygon',coordinates:[[[-77,38],[-76,38],[-76,37],[-77,37],[-77,38]]]}]}]};
 const records=O.parseEonet(payload,ts);
 assert.equal(records[0].type,'Wildfire');assert.equal(records[0].geometry.type,'Polygon');
 assert.equal(records[0].geometry.geometryDerived,'centroid_for_label_only');
 assert.equal(records[0].observationTime,new Date(ts).toISOString());
});
test('NOAA Kp parses official object and table layouts, rejects fictional values',()=>{
 const payload=[{time_tag:ts,kp_index:4.4},{time_tag:'bad',kp_index:5}];
 assert.equal(O.parseNoaa(payload,ts)[0].properties.kp,4.4);
 assert.equal(O.parseNoaa([['time_tag','Kp'],[ts,'5.67']],ts)[0].properties.kp,5.67);
 assert.throws(()=>O.parseNoaa([{time_tag:ts,kp_index:15}],ts));
});
test('civil orbital elements are CelesTrak source records, not invented live GPS',()=>{
 const payload=[{OBJECT_NAME:'ISS (ZARYA)',NORAD_CAT_ID:25544,EPOCH:ts,MEAN_MOTION:15.4},
 {OBJECT_NAME:'COSMOS 1234',NORAD_CAT_ID:111,EPOCH:ts,MEAN_MOTION:15},
 {OBJECT_NAME:'NOAA 1',NORAD_CAT_ID:11,EPOCH:'2005-01-01T00:00:00Z',MEAN_MOTION:14}];
 const records=O.parseOrbits(payload,ts,clock);
 assert.equal(records.length,1);assert.equal(records[0].type,'CivilOrbitalElementSet');
 assert.equal(records[0].geometry,null);assert.equal(records[0].accuracy,'predicted_not_live_position');
});
test('NOAA and CelesTrak zone-less timestamps mean UTC, not the client timezone',()=>{
 const noaa=O.parseNoaa([{time_tag:'2026-10-13 17:30:00',kp_index:4.7}],ts);
 assert.equal(noaa[0].observationTime,'2026-10-13T17:30:00.000Z');
 const satellite=O.parseOrbits([{OBJECT_NAME:'ISS (ZARYA)',NORAD_CAT_ID:25544,EPOCH:'2026-10-13T17:30:00',MEAN_MOTION:15}],ts,clock);
 assert.equal(satellite[0].observationTime,'2026-10-13T17:30:00.000Z');
 assert.ok(satellite[0].properties.omm.EPOCH.endsWith('Z'));
});
test('3D OSM buildings extrude ONLY if height tag exists',()=>{
 const elements=[{type:'way',id:100,tags:{building:'yes',height:'42 ft'},geometry:[{lat:37,lon:-77},{lat:37.001,lon:-77},{lat:37.001,lon:-77.001}]},
 {type:'way',id:101,tags:{building:'yes','building:levels':'99'},geometry:[{lat:37,lon:-77},{lat:37.001,lon:-77},{lat:37.001,lon:-77.001}]}];
 const records=O.parseBuildings({elements},ts);
 assert.equal(records.length,2);assert.equal(records[0].properties.heightMeters,12.8);
 assert.equal(records[1].properties.heightMeters,null);
 assert.equal(O.heightMeters('9999'),null);assert.equal(O.heightMeters('-3'),null);
});
test('fetch failure removes data from current map while retaining archived provenance',()=>{
 let now=clock;const graph=new O.Ontology(()=>now);const records=O.parseUsgs({features:[{id:'q',properties:{time:clock,mag:2.6},geometry:{type:'Point',coordinates:[-77,37]}}]},ts);
 graph.ingest('usgs',records,new Date(clock).toISOString());
 assert.equal(graph.current('usgs').length,1);
 graph.failure('usgs',Error('offline'));
 assert.equal(graph.current('usgs').length,0);assert.equal(graph.all().length,1);
 assert.equal(graph.exportJsonLD()['@graph'].find(x=>x['@type']==='tak:Earthquake')['tak:currentlyVerified'],false);
 now+=360000;graph.ingest('usgs',records,ts);assert.equal(graph.status('usgs').state,'STALE');
});
test('ontology export has explicit linked sources and timestamps',()=>{
 const graph=new O.Ontology(()=>clock);
 const p=O.parseNoaa([{time_tag:ts,kp_index:3.5}],ts);
 graph.ingest('noaa',p,ts);
 const exportValue=graph.exportJsonLD();const record=exportValue['@graph'].find(x=>x['@type']==='tak:GeomagneticIndex');
 assert.equal(record['prov:wasDerivedFrom']['@id'],'urn:tak-os:source:noaa');
 assert.equal(record['tak:observedAt'],new Date(ts).toISOString());
 assert.equal(record['tak:geometry'],null);
});

const I=require(path.resolve(__dirname,'../docs/tak-os/live-3d/iphone-grid.js'));
test('iPhone resource budget preserves bounded GPU load',()=>{
 const phone=I.chooseProfile({width:393,dpr:3,coarse:true,iosPhone:true});
 const desktop=I.chooseProfile({width:1440,dpr:2,coarse:false});
 assert.equal(phone.mobile,true);
 assert.ok(phone.resolutionScale<desktop.resolutionScale);
 assert.ok(phone.tileCacheSize<desktop.tileCacheSize);
 assert.ok(phone.orbitTickMs>desktop.orbitTickMs);
 assert.equal(I.chooseProfile({width:844,dpr:3,coarse:true,iosPhone:true}).mobile,true);
 assert.equal(I.chooseProfile({width:390,coarse:false}).mobile,false);
 assert.equal(I.chooseProfile({width:390,coarse:true,saveData:true}).resolutionScale,0.58);
});
test('cloud feed status is calculated only from actual feed status',()=>{
 assert.equal(I.summarize({usgs:'NOT_CONNECTED'}).online,0);
 const v=I.summarize({usgs:'OK',eonet:'STALE',noaa:'ERROR',orbit:'CONNECTING',buildings:'OK'});
 assert.equal(v.online,1);assert.equal(v.total,4);
 assert.equal(v.stale,1);assert.equal(v.failed,1);
 assert.match(v.label,/1\/4/);
 assert.equal(I.summarize({usgs:'ERROR'}).label,'PUBLIC CLOUD: NO CURRENT SOURCES');
});
test('coordinate grid is reference geometry, never generated observations',()=>{
 const lines=I.graticule(30);
 assert.ok(lines.length>=15);
 for(const line of lines){
  assert.equal(line.length%2,0);
  for(let i=0;i<line.length;i+=2){
   assert.ok(line[i]>=-180&&line[i]<=180);
   assert.ok(line[i+1]>=-90&&line[i+1]<=90);
  }
 }
 assert.throws(()=>I.graticule(7));
});

const fs=require('node:fs');
test('iPhone displays full-viewport globe with panels closed by default',()=>{
 const css=fs.readFileSync(path.resolve(__dirname,'../docs/tak-os/live-3d/iphone-grid.css'),'utf8');
 const html=fs.readFileSync(path.resolve(__dirname,'../docs/tak-os/live-3d/index.html'),'utf8');
 const js=fs.readFileSync(path.resolve(__dirname,'../docs/tak-os/live-3d/live-earth.js'),'utf8');
 assert.ok(css.includes('#globe{position:fixed!important;inset:0!important'));
 assert.ok(css.includes('.leftpanel,.rightpanel,.leftpanel.hidden,.rightpanel.open{display:none!important}'));
 assert.ok(css.includes('.leftpanel.mobile-open,.rightpanel.mobile-open'));
 assert.ok(css.includes('env(safe-area-inset-bottom'));
 for(const action of ['map','layers','intel'])assert.ok(html.includes('data-mobile-panel="'+action+'"'));
 for(const action of ['zoom-in','zoom-out','center'])assert.ok(html.includes('data-map-action="'+action+'"'));
 assert.ok(html.includes('data-close-panel'));
 assert.ok(js.includes("setCamera(mobileProfile.mobile?'north-america':'earth')"));
 assert.ok(js.includes("button.addEventListener('click',()=>switchMobilePanel('map'))"));
});
test('Streets overlay only requests source tiles on user action, never synthetic telemetry',()=>{
 const html=fs.readFileSync(path.resolve(__dirname,'../docs/tak-os/live-3d/index.html'),'utf8');
 const js=fs.readFileSync(path.resolve(__dirname,'../docs/tak-os/live-3d/live-earth.js'),'utf8');
 const sw=fs.readFileSync(path.resolve(__dirname,'../docs/tak-os/live-3d/sw.js'),'utf8');
 assert.ok(html.includes('id="street-mobile"'));
 assert.ok(html.includes('id="street-toggle"'));
 assert.ok(js.includes('function toggleStreets()'));
 assert.ok(js.includes('new C.UrlTemplateImageryProvider'));
 assert.ok(js.includes('https://tile.openstreetmap.org/{z}/{x}/{y}.png'));
 assert.ok(js.includes('OpenStreetMap contributors'));
 assert.ok(js.includes("addEventListener('click',toggleStreets)"));
 assert.ok(!sw.includes('tile.openstreetmap.org'));
 assert.ok(js.includes('Preset city, not device GPS.'));
});
