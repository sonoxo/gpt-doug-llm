import test from 'node:test';
import assert from 'node:assert/strict';
import { ensureInitialProject } from '../public/bootstrap.js';

test('keeps an existing project without reloading', async () => {
  let reloads = 0;
  const fetchImpl = async (url, options = {}) => {
    assert.equal(url, '/api/projects');
    assert.equal(options.method, undefined);
    return new Response(JSON.stringify({ projects: [{ id: 'existing-project' }] }), { status: 200 });
  };

  const result = await ensureInitialProject({ fetchImpl, reload: () => { reloads += 1; } });
  assert.equal(result.created, false);
  assert.equal(result.project.id, 'existing-project');
  assert.equal(reloads, 0);
});

test('creates the first static project and reloads once', async () => {
  const calls = [];
  let reloads = 0;
  const fetchImpl = async (url, options = {}) => {
    calls.push({ url, options });
    if (!options.method) {
      return new Response(JSON.stringify({ projects: [] }), { status: 200 });
    }
    return new Response(JSON.stringify({
      project: { id: 'gpt-doug-build-123456', name: 'GPT Doug Build', template: 'static' },
    }), { status: 201 });
  };

  const result = await ensureInitialProject({ fetchImpl, reload: () => { reloads += 1; } });
  assert.equal(result.created, true);
  assert.equal(result.project.id, 'gpt-doug-build-123456');
  assert.equal(reloads, 1);
  assert.equal(calls.length, 2);
  assert.equal(calls[1].options.method, 'POST');
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    name: 'GPT Doug Build',
    template: 'static',
  });
});

test('reports project creation failures', async () => {
  let count = 0;
  const fetchImpl = async () => {
    count += 1;
    if (count === 1) return new Response(JSON.stringify({ projects: [] }), { status: 200 });
    return new Response(JSON.stringify({ error: 'disk unavailable' }), { status: 500 });
  };

  await assert.rejects(
    ensureInitialProject({ fetchImpl, reload: () => {} }),
    /disk unavailable/,
  );
});
