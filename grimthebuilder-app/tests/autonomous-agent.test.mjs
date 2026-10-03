import test from 'node:test';
import assert from 'node:assert/strict';
import {
  AutonomousWorkflowError,
  buildRepairPrompt,
  runAutonomousWorkflow,
} from '../public/autonomous-agent.js';

function base(overrides = {}) {
  return {
    prompt: 'Build a working app',
    mode: 'build',
    generate: async ({ mode }) => ({ message: mode, operations: [{ op: 'write_file', path: 'index.html', content: '<h1>ok</h1>' }] }),
    apply: async () => {},
    inspect: async () => ({ kind: 'static', needsInstall: false }),
    install: async () => ({ detail: 'skipped' }),
    start: async () => ({ kind: 'static', previewUrl: '/preview/app/' }),
    verify: async () => ({ verified: true, detail: 'preview works' }),
    ...overrides,
  };
}

test('runs generate, apply, inspect, start and verify in order', async () => {
  const calls = [];
  const result = await runAutonomousWorkflow(base({
    generate: async ({ mode }) => { calls.push(`generate:${mode}`); return { message: 'done', operations: [] }; },
    apply: async () => calls.push('apply'),
    inspect: async () => { calls.push('inspect'); return { kind: 'static', needsInstall: false }; },
    install: async () => calls.push('install'),
    start: async () => { calls.push('start'); return { kind: 'static' }; },
    verify: async () => { calls.push('verify'); return { verified: true }; },
  }));
  assert.deepEqual(calls, ['generate:build', 'apply', 'inspect', 'start', 'verify']);
  assert.equal(result.verified, true);
  assert.equal(result.repairs, 0);
});

test('installs declared dependencies before starting', async () => {
  const calls = [];
  await runAutonomousWorkflow(base({
    generate: async () => ({ message: 'done', operations: [] }),
    apply: async () => calls.push('apply'),
    inspect: async () => { calls.push('inspect'); return { kind: 'node', needsInstall: true }; },
    install: async () => { calls.push('install'); return { detail: 'installed' }; },
    start: async () => { calls.push('start'); return {}; },
    verify: async () => ({ verified: true }),
  }));
  assert.deepEqual(calls, ['apply', 'inspect', 'install', 'start']);
});

test('repairs a verified runtime failure and then succeeds', async () => {
  const modes = [];
  const applied = [];
  let checks = 0;
  const result = await runAutonomousWorkflow(base({
    generate: async ({ mode, prompt }) => {
      modes.push(mode);
      if (mode === 'fix') assert.match(prompt, /FAILED STAGE: verify/);
      return { message: mode, operations: [{ op: 'write_file', path: 'server.mjs', content: mode }] };
    },
    apply: async (operations, mode) => applied.push({ operations, mode }),
    verify: async () => ({ verified: ++checks > 1, detail: checks > 1 ? 'healthy' : 'health failed', logs: 'port closed' }),
  }));
  assert.deepEqual(modes, ['build', 'fix']);
  assert.equal(applied.length, 2);
  assert.equal(result.repairs, 1);
  assert.equal(result.verified, true);
});

test('stops after three repair attempts', async () => {
  let generations = 0;
  await assert.rejects(
    runAutonomousWorkflow(base({
      generate: async () => { generations += 1; return { message: 'x', operations: [] }; },
      verify: async () => ({ verified: false, detail: 'still broken' }),
    })),
    error => {
      assert.ok(error instanceof AutonomousWorkflowError);
      assert.equal(error.attempts, 3);
      assert.equal(error.stage, 'verify');
      return true;
    },
  );
  assert.equal(generations, 4);
});

test('plan mode never starts or verifies a runtime', async () => {
  let runtimeCalls = 0;
  const result = await runAutonomousWorkflow(base({
    mode: 'plan',
    generate: async () => ({ message: 'plan', operations: [] }),
    start: async () => { runtimeCalls += 1; },
    verify: async () => { runtimeCalls += 1; },
  }));
  assert.equal(runtimeCalls, 0);
  assert.equal(result.verified, false);
});

test('cancellation is honored before model generation', async () => {
  const controller = new AbortController();
  controller.abort();
  await assert.rejects(
    runAutonomousWorkflow(base({ signal: controller.signal })),
    error => error.name === 'AbortError',
  );
});

test('repair prompt contains bounded failure evidence', () => {
  const prompt = buildRepairPrompt({
    originalPrompt: 'Build a server',
    failure: { stage: 'start', detail: 'crashed', logs: 'EADDRINUSE' },
    repairAttempt: 2,
  });
  assert.match(prompt, /REPAIR ATTEMPT 2 OF 3/);
  assert.match(prompt, /FAILED STAGE: start/);
  assert.match(prompt, /EADDRINUSE/);
});
