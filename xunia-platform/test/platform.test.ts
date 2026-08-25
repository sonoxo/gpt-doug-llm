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

class CapturingGateway extends ModelGateway {
  seen: unknown[] = [];
  constructor() { super('', ''); }
  override async complete(_system: string, message: string, context: unknown[]) {
    this.seen = context;
    return `captured:${message}`;
  }
}

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
  assert.ok(run.context.length >= 3);
  assert.ok(run.steps.some((step) => step.tool === 'ontology.search' && step.status === 'executed'));
  assert.ok(run.steps.some((step) => step.tool === 'ontology.neighbors' && step.status === 'executed'));
  assert.ok(run.steps.some((step) => step.tool === 'telemetry.write' && step.status === 'approval_required'));
  assert.equal(aip.verifyAuditChain().ok, true);
  const reloaded = new AipEngine(ontology, new ModelGateway('', ''), stateFile);
  assert.equal(reloaded.getRun(run.id)?.id, run.id);
  assert.equal(reloaded.verifyAuditChain().ok, true);
});

test('AIP sends ontology grounding outputs to the model before completion', async () => {
  const ontology = new OntologyStore();
  ontology.seed();
  const gateway = new CapturingGateway();
  const aip = new AipEngine(ontology, gateway);
  const run = await aip.run('xunia-analyst', 'Analyze service:sonoxo and its connected objects.', [], 'grounding-test');
  const groundedSources = gateway.seen.flatMap((entry) => {
    if (!entry || typeof entry !== 'object') return [];
    const source = (entry as { source?: unknown }).source;
    return typeof source === 'string' ? [source] : [];
  });
  assert.ok(groundedSources.includes('ontology.search'));
  assert.ok(groundedSources.includes('ontology.neighbors'));
  assert.deepEqual(run.context, gateway.seen);
});

test('AIP atomically claims approval steps before awaiting side effects', async () => {
  const ontology = new OntologyStore();
  const aip = new AipEngine(ontology, new ModelGateway('', ''));
  let calls = 0;
  let release!: () => void;
  const hold = new Promise<void>((resolve) => { release = resolve; });

  aip.tools.register({
    name: 'test.write',
    description: 'Controlled side-effect test tool.',
    risk: 'medium',
    execute: async () => {
      calls += 1;
      await hold;
      return { ok: true };
    }
  });
  aip.registerAgent({
    id: 'test-operator',
    name: 'Test Operator',
    system: 'test',
    tools: ['test.write'],
    approvalFor: ['medium']
  });

  const run = {
    id: 'run-concurrency',
    agentId: 'test-operator',
    message: 'test',
    createdAt: new Date().toISOString(),
    context: [],
    response: 'test',
    steps: [{ id: 'step-write', tool: 'test.write', input: {}, reason: 'test', status: 'approval_required' as const }]
  };
  aip.runs.set(run.id, run);

  const first = aip.approve(run.id, 'step-write', 'admin-a');
  await Promise.resolve();
  await assert.rejects(() => aip.approve(run.id, 'step-write', 'admin-b'), /step_not_approvable/);
  release();
  await first;
  assert.equal(calls, 1);
  assert.equal(run.steps[0].status, 'executed');
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
