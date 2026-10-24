'use strict';
const test=require('node:test'),assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path');
const F=require('../docs/tak-os/live-3d/live-freshness.js');
test('live public ontology preserves source times, observation ages and attribution',()=>{
 const P={usgs:{label:'USGS',url:'https://earthquake.usgs.gov',intervalMs:120000},buildings:{label:'OSM',url:'https://www.openstreetmap.org',intervalMs:0}};
 const sample={usgs:{state:'OK',fetchedAt:'2026-10-22T18:00:00Z'},buildings:{state:'NOT_CONNECTED'}};
 const store={status:k=>sample[k],current:k=>k==='usgs'?[{observationTime:'2026-10-22T17:55:00Z'}]:[]};
 const v=F.publicSnapshot(store,P,Date.parse('2026-10-22T18:01:00Z'));
 assert.equal(v.scope,'public_read_only');assert.equal(v.connectedContinuous,1);assert.equal(v.continuousTotal,1);
 assert.equal(v.sources[0].fetchAgeSeconds,60);assert.equal(v.sources[0].latestObservationAgeSeconds,360);
 assert.equal(v.sources[1].onDemand,true);assert.equal(v.sources[1].state,'NOT_CONNECTED');
 assert.equal(v['@graph'][0]['@id'],'urn:tak-os:source:usgs');assert.equal(v.privateTakIncluded,false);
});
test('future or malformed source timestamps cannot declare source current',()=>{
 const s={status:()=>({state:'OK',fetchedAt:'2099-01-01T00:00:00Z'}),current:()=>[]};
 const v=F.publicSnapshot(s,{usgs:{label:'x',url:'https://example.org',intervalMs:30000}},Date.parse('2026-10-22T00:00:00Z'));
 assert.equal(v.sources[0].state,'ERROR');assert.equal(v.sources[0].fetchedAtUtc,null);
 assert.equal(v.connectedContinuous,0);
});
test('private TAK projection only accepts proven totals, never exports identities',()=>{
 const now=Date.parse('2026-10-22T18:00:05Z');
 const info={schema:'gpt-doug.tak-private-metrics.v1',status:'current',sourceScope:'aggregate_all_tak_clients',mTLSVerifiedByPrivateGateway:true,sampledAtUtc:'2026-10-22T18:00:00Z',sampleAgeSeconds:3,
 metrics:{numClients:3,bytesRead:100,bytesWritten:200,numReads:7,numWrites:8,uid:'secret_UID',callsign:'PRIVATE'}};
 const v=F.privateSnapshot(info,now);
 assert.equal(v.freshness,'CURRENT');assert.equal(v.effectiveAgeSeconds,5);assert.equal(v.itakOnlyClientCount,null);
 assert.equal(v.readings.numClients,3);assert.equal(v['@graph'].length,6);
 assert.ok(!JSON.stringify(v).includes('PRIVATE'));assert.ok(!JSON.stringify(v).includes('secret_UID'));
 const stale=F.privateSnapshot(info,now+32000);assert.equal(stale.freshness,'STALE');
 assert.throws(()=>F.privateSnapshot({...info,mTLSVerifiedByPrivateGateway:false},now));
 assert.throws(()=>F.privateSnapshot({...info,metrics:{...info.metrics,numClients:1.5}},now));
});
test('iPhone has visible dynamic date and source-ontology controls, not credential export',()=>{
 const root=path.resolve(__dirname,'../docs/tak-os/live-3d');
 const html=fs.readFileSync(path.join(root,'index.html'),'utf8');
 const logic=fs.readFileSync(path.join(root,'live-earth.js'),'utf8');
 const sw=fs.readFileSync(path.join(root,'sw.js'),'utf8');
 assert.match(html,/id="live-date-time"/);assert.match(html,/id="live-source-ontology"/);
 assert.match(logic,/setInterval\(updateLiveDate,1000\)/);
 assert.match(logic,/freshnessTools\.privateSnapshot\(info\)/);
 assert.match(logic,/freshnessTools\.publicSnapshot\(store,PROVIDERS\)/);
 assert.ok(sw.includes("'./live-freshness.js'"));
 assert.ok(!sw.includes('api/v1/itak/metrics'));
});
