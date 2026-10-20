import assert from 'node:assert/strict';
import test from 'node:test';
import {readFileSync} from 'node:fs';
import {AUTHORIZATION,CONTROLS,DRILLS,CHANNELS,readiness,newExercise,inject,advance,ontology,report} from '../docs/readyroom/policy.mjs';
test('no operational entitlement, CIA affiliation or hardware controls',()=>{
 for(const [key,value] of Object.entries(AUTHORIZATION)) if(typeof value==='boolean')assert.equal(value,false,key);
 assert.equal(readiness().eligible,false);
 assert.equal(readiness().authorization,'NOT AUTHORIZED');
});
test('controlled evidence states preserve missing versus measured',()=>{
 const x=readiness();assert.equal(x.total,CONTROLS.length);assert.equal(x.total,x.counts.measured+x.counts.planned+x.counts.missing);
 assert.ok(x.counts.missing>0);assert.ok(x.counts.measured>0);
 assert.equal(new Set(CONTROLS.map(c=>c.id)).size,CONTROLS.length);
});
test('all defensive drills are deterministic, bounded, and recover',()=>{
 for(const d of DRILLS){
  const start=newExercise(d.id),stressed=inject(start);
  for(const x of CHANNELS)assert.ok(stressed.metrics[x.id]<start.metrics[x.id]);
  const recovered=advance(stressed,100);
  assert.equal(recovered.day,100);
  for(const x of CHANNELS)assert.ok(recovered.metrics[x.id]>=stressed.metrics[x.id]&&recovered.metrics[x.id]<=100);
  assert.deepEqual(advance(stressed,100),recovered);
 }
});
test('invalid inputs fail closed',()=>{
 assert.throws(()=>newExercise('kinetic'),RangeError);
 assert.throws(()=>advance(newExercise(),0),RangeError);
 assert.throws(()=>advance(newExercise(),101),RangeError);
 assert.throws(()=>readiness([{state:'authorized'}]));
});
test('ontology and after-action reports retain synthetic provenance',()=>{
 const e=inject(newExercise());const g=ontology(e);const r=report(e);
 assert.equal(g.classification,'PUBLIC DEMO ONLY');assert.ok(g.nodes.every(x=>x.provenance));
 assert.equal(r.dataClass,'SYNTHETIC PUBLIC EXERCISE');assert.equal(r.authorization.authorityToOperate,false);
 assert.equal(r.ontology.schema,'xunia.readiness.ontology.v1');
});
test('public homepage and isolated demos are wired',()=>{
 const home=readFileSync('docs/index.html','utf8');
 const ready=readFileSync('docs/readyroom/index.html','utf8');
 const sim=readFileSync('docs/morpho-bit/index.html','utf8');
 assert.match(home,/href="\.\/readyroom\/"/);assert.match(home,/href="\.\/morpho-bit\/"/);
 assert.match(ready,/NOT GOVERNMENT CERTIFIED/);assert.match(ready,/policy\.mjs/);
 assert.match(sim,/SIMULATION ONLY/);assert.match(sim,/WARLENS/);
});
