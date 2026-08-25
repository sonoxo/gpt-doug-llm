import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { createSonoxoServer } from '../apps/sonoxo/server.js';

process.env.NODE_ENV = 'test';

test('GET health and POST harvest persist telemetry with redaction', async () => {
  const root = mkdtempSync(join(tmpdir(), 'sonoxo-'));
  const dbPath = join(root, 'database.sql');
  const logPath = join(root, '.xray', 'harvest', 'sonoxo.json');
  const app = createSonoxoServer({ dbPath, harvestLog: logPath });

  await new Promise<void>((resolve) => app.server.listen(0, '127.0.0.1', resolve));
  const address = app.server.address();
  assert.ok(address && typeof address !== 'string');
  const base = `http://127.0.0.1:${address.port}/api/sonoxo/harvest`;

  const health = await fetch(base);
  assert.equal(health.status, 200);
  assert.deepEqual(await health.json(), { ok: true, service: 'sonoxo', environment: 'dev', region: 'virginia-local', events: 0 });

  const harvest = await fetch(base, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ type: 'media.transcoded', source: 'local-dev', payload: { frames: 144, apiKey: 'do-not-log' } }),
  });
  assert.equal(harvest.status, 202);
  assert.equal(app.store.count(), 1);

  const summary = JSON.parse(readFileSync(logPath, 'utf8'));
  assert.equal(summary.accepted, 1);
  assert.equal(summary.event.payload.apiKey, '[REDACTED]');
  assert.equal(summary.totalEvents, 1);

  await app.close();
});

test('POST rejects malformed events', async () => {
  const root = mkdtempSync(join(tmpdir(), 'sonoxo-invalid-'));
  const app = createSonoxoServer({ dbPath: join(root, 'database.sql'), harvestLog: join(root, '.xray', 'harvest', 'sonoxo.json') });
  await new Promise<void>((resolve) => app.server.listen(0, '127.0.0.1', resolve));
  const address = app.server.address();
  assert.ok(address && typeof address !== 'string');
  const response = await fetch(`http://127.0.0.1:${address.port}/api/sonoxo/harvest`, { method: 'POST', body: JSON.stringify({ payload: {} }) });
  assert.equal(response.status, 400);
  await app.close();
});
