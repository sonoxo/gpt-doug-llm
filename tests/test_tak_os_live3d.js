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
