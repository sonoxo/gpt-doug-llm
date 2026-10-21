import { test } from 'node:test';
import assert from 'node:assert/strict';
import { digest, verifyBundle } from '../docs/rea-kraken/app.mjs';

function file(name, value) {
  const raw = new TextEncoder().encode(value);
  return {name, size: raw.length, async text(){return value;}, async arrayBuffer(){return raw.buffer}};
}
async function bundle() {
  const evidence = '{"kind":"synthetic"}';
  const raw = new TextEncoder().encode(evidence);
  const manifest = JSON.stringify({system:'SONOXO_GPT_CHAOS_REA_SWARM',schema_version:1,state:'PASS',results:[{id:'01',state:'PASS',evidence:'01.json',bytes:raw.length,sha256:await digest(raw)}]});
  return [file('manifest.json',manifest),file('01.json',evidence)];
}
test('validates synthetic bundle with no network',async()=>{
  const r=await verifyBundle(await bundle());
  assert.equal(r.status,'VERIFIED');assert.equal(r.verified,1);
});
test('rejects tampered evidence',async()=>{
  const b=await bundle();b[1]=file('01.json','{"kind":"modified"}');
  await assert.rejects(()=>verifyBundle(b),/mismatch/);
});
test('rejects traversal and duplicate file names',async()=>{
  const b=await bundle();
  await assert.rejects(()=>verifyBundle([...b,b[1]]),/unique/);
  const manifest=JSON.parse(await b[0].text());manifest.results[0].evidence='../outside';
  await assert.rejects(()=>verifyBundle([file('manifest.json',JSON.stringify(manifest)),b[1]]),/filename/);
});
test('distinguishes blocked outcomes from verified evidence',async()=>{
  const m=JSON.stringify({system:'SONOXO_GPT_CHAOS_REA_SWARM',schema_version:1,state:'BLOCKED',results:[{id:'01',state:'BLOCKED'}]});
  const r=await verifyBundle([file('manifest.json',m)]);
  assert.equal(r.status,'PARTIAL');assert.equal(r.verified,0);
});
