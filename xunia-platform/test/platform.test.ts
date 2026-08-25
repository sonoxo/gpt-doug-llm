import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { mkdtempSync } from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { OntologyStore } from '../src/ontology.js';
import { AipEngine, ModelGateway } from '../src/aip.js';
import { createPlatformHandler } from '../src/server.js';
import { AuthPolicy, RateLimiter } from '../src/security.js';

test('ontology stores objects, relations, deletes, and persists', () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), 'xunia-ontology-'));
  const file = path.join(dir, 'ontology.json');
  const ontology = new OntologyStore(file);
  ontology.upsertObject({ id: 'site:a', type: 'Site', properties: { name: 'A' } });
  ontology.upsertObject({ id: 'service:b', type: 'Service', properties: { name: 'B' } });
  ontology.upsertLink({ id: 'link:1', type: 'HOSTS', from: 'site:a', to: 'service:b', properties: {} });
  assert.equal(ontology.search('service').length, 1);
  assert.equal(ontology.neighbors('site:a')[0].object?.id, 'service:b');
  assert.throws(() => ontology.deleteObject('site:a'), /object_has_links/);
  assert.equal(ontology.deleteObject('site:a', true), true);
  const reloaded = new OntologyStore(file);
  assert.equal(reloaded.getObject('site:a'), null);
  assert.equal(reloaded.getObject('service:b')?.id, 'service:b');
});

test('AIP grounds requests, requires approval for writes, persists, and hash-chains audit', async () => {
  const dir = mkdtempSync(path.join(os.tmpdir(), 'xunia-aip-'));
  const stateFile = path.join(dir, 'aip.json');
  const ontology = new OntologyStore();
  ontology.seed();
  const aip = new AipEngine(ontology, new ModelGateway('', ''), stateFile);
  const run = await aip.run('xunia-analyst', 'Analyze service:sonoxo and record telemetry.', ['service:sonoxo'], 'test-user');
  assert.equal(run.agentId, 'xunia-analyst');
  assert.match(run.response, /AIP analysis/);
  assert.equal(run.context.length, 1);
  assert.ok(run.steps.some((step) => step.tool === 'ontology.search' && step.status === 'executed'));
  assert.ok(run.steps.some((step) => step.tool === 'ontology.neighbors' && step.status === 'executed'));
  assert.ok(run.steps.some((step) => step.tool === 'telemetry.write' && step.status === 'approval_required'));
  assert.equal(aip.verifyAuditChain().ok, true);
  const reloaded = new AipEngine(ontology, new ModelGateway('', ''), stateFile);
  assert.equal(reloaded.getRun(run.id)?.id, run.id);
  assert.equal(reloaded.verifyAuditChain().ok, true);
});

test('HTTP platform enforces RBAC and exposes readiness', async (t) => {
  const ontology = new OntologyStore();
  ontology.seed();
  const aip = new AipEngine(ontology, new ModelGateway('', ''));
  const policy = new AuthPolicy(true, JSON.stringify({
    'viewer-token': { role: 'viewer', subject: 'viewer' },
    'operator-token': { role: 'operator', subject: 'operator' },
    'admin-token': { role: 'admin', subject: 'admin' }
  }));
  const handler = createPlatformHandler(ontology, aip, policy, new RateLimiter(1000));
  const server = createServer((req, res) => void handler(req, res));
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise<void>((resolve) => server.close(() => resolve())));
  const address = server.address();
  assert.ok(address && typeof address === 'object');
  const base = `http://127.0.0.1:${address.port}`;

  const health = await fetch(`${base}/health`).then((res) => res.json()) as { ok: boolean };
  assert.equal(health.ok, true);
  const ready = await fetch(`${base}/ready`);
  assert.equal(ready.status, 200);

  assert.equal((await fetch(`${base}/api/ontology`)).status, 401);
  assert.equal((await fetch(`${base}/api/ontology`, { headers: { authorization: 'Bearer viewer-token' } })).status, 200);
  assert.equal((await fetch(`${base}/api/aip/run`, {
    method: 'POST', headers: { authorization: 'Bearer viewer-token', 'content-type': 'application/json' }, body: JSON.stringify({ message: 'test' })
  })).status, 403);

  const runResponse = await fetch(`${base}/api/aip/run`, {
    method: 'POST', headers: { authorization: 'Bearer operator-token', 'content-type': 'application/json' }, body: JSON.stringify({ message: 'Analyze service:sonoxo' })
  });
  assert.equal(runResponse.status, 201);
  const run = await runResponse.json() as { run: { id: string } };
  assert.ok(run.run.id);

  const create = await fetch(`${base}/api/ontology/objects`, {
    method: 'POST', headers: { authorization: 'Bearer admin-token', 'content-type': 'application/json' }, body: JSON.stringify({ id: 'site:test', type: 'Site', properties: { ready: true } })
  });
  assert.equal(create.status, 201);
  const audit = await fetch(`${base}/api/aip/audit/verify`, { headers: { authorization: 'Bearer viewer-token' } }).then((res) => res.json()) as { ok: boolean };
  assert.equal(audit.ok, true);
});
