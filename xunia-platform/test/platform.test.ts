import test from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { OntologyStore } from '../src/ontology.js';
import { AipEngine, ModelGateway } from '../src/aip.js';
import { handler } from '../src/server.js';

test('ontology stores objects and validated relations', () => {
  const ontology = new OntologyStore();
  ontology.upsertObject({ id: 'site:a', type: 'Site', properties: { name: 'A' } });
  ontology.upsertObject({ id: 'service:b', type: 'Service', properties: { name: 'B' } });
  ontology.upsertLink({ id: 'link:1', type: 'HOSTS', from: 'site:a', to: 'service:b', properties: {} });
  assert.equal(ontology.search('service').length, 1);
  assert.equal(ontology.neighbors('site:a')[0].object?.id, 'service:b');
  assert.throws(() => ontology.upsertLink({ id: 'bad', type: 'LINK', from: 'missing', to: 'service:b', properties: {} }), /link_endpoint_missing/);
});

test('AIP grounds requests and audits tool execution', async () => {
  const ontology = new OntologyStore();
  ontology.seed();
  const aip = new AipEngine(ontology, new ModelGateway('', ''));
  const run = await aip.run('xunia-analyst', 'Analyze service:sonoxo and its connected objects.', ['service:sonoxo']);
  assert.equal(run.agentId, 'xunia-analyst');
  assert.match(run.response, /AIP analysis/);
  assert.equal(run.context.length, 1);
  assert.ok(run.steps.some((step) => step.tool === 'ontology.search' && step.status === 'executed'));
  assert.ok(run.steps.some((step) => step.tool === 'ontology.neighbors' && step.status === 'executed'));
  assert.ok(aip.audits.some((record) => record.event === 'run_completed'));
});

test('HTTP platform exposes health and AIP inventory', async (t) => {
  const server = createServer((req, res) => void handler(req, res));
  await new Promise<void>((resolve) => server.listen(0, '127.0.0.1', resolve));
  t.after(() => new Promise<void>((resolve) => server.close(() => resolve())));
  const address = server.address();
  assert.ok(address && typeof address === 'object');
  const base = `http://127.0.0.1:${address.port}`;
  const health = await fetch(`${base}/health`).then((res) => res.json()) as { ok: boolean; agents: number };
  assert.equal(health.ok, true);
  assert.ok(health.agents >= 2);
  const agents = await fetch(`${base}/api/aip/agents`).then((res) => res.json()) as { agents: unknown[] };
  assert.ok(agents.agents.length >= 2);
});
