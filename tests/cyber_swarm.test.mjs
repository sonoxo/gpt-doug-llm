import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {ROLES,TACTICS,ALLOWED_FUNCTIONS,analyzeStage,validateCurriculum,scoreChoice,buildReport} from '../docs/cyber-swarm/engine.mjs';
const data=JSON.parse(fs.readFileSync(new URL('../docs/cyber-swarm/curriculum.json',import.meta.url),'utf8'));

test('all 15 canonical enterprise tactics covered with 6 NIST functions',()=>{
  const result=validateCurriculum(data);assert.deepEqual(result.errors,[]);assert.equal(result.ok,true);
  assert.equal(result.coverage.tactics,15);assert.equal(result.coverage.nist,6);assert.equal(result.coverage.roles,6);
  assert.equal(TACTICS.length,15);assert.equal(ALLOWED_FUNCTIONS.length,6);
});
test('six deterministic roles produce evidence and never live actions',()=>{
  for(const row of data.scenarios){
    const runs=ROLES.map((_,i)=>analyzeStage(row,i));
    assert.equal(new Set(runs.map(x=>x.role)).size,6);
    assert.ok(runs.every(x=>x.status==='SIMULATED'&&x.body&&x.evidence));
  }
});
test('training gate requires six completed roles plus correct analyst answer',()=>{
  for(const row of data.scenarios){
    assert.equal(scoreChoice(row,row.answer).correct,true);
    assert.equal(scoreChoice(row,(row.answer+1)%3).correct,false);
    assert.equal(buildReport(row,5,row.answer).result,'INCOMPLETE_OR_REVIEW_REQUIRED');
    assert.equal(buildReport(row,6,(row.answer+1)%3).result,'INCOMPLETE_OR_REVIEW_REQUIRED');
    const report=buildReport(row,6,row.answer);
    assert.equal(report.result,'TRAINING_COMPLETE');assert.equal(report.real_world_actions,0);
    assert.equal(report.automated_agents_spawned,0);
  }
});
test('tampered or mismatched curriculum fails closed',()=>{
  assert.equal(validateCurriculum({...data,mode:'live-attack'}).ok,false);
  assert.equal(validateCurriculum({...data,scenarios:data.scenarios.slice(1)}).ok,false);
  assert.equal(validateCurriculum({...data,provenance:{...data.provenance,no_live_targets:false}}).ok,false);
});
test('all sources are official HTTPS links and all lab IDs are unique',()=>{
  for(const row of data.scenarios){assert.match(row.source,/^https:\/\/attack\.mitre\.org\/tactics\/TA\d{4}\/$/);assert.ok(row.signals.every(s=>!s.includes('curl ')));}
  assert.ok(data.provenance.sources.every(s=>new URL(s.url).protocol==='https:'));
});
