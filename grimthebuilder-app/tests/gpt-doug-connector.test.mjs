import test from 'node:test';
import assert from 'node:assert/strict';
import {
  chatGptDoug,
  createAgentMessages,
  discoverGptDoug,
  normalizeBridgeUrl,
  parseAgentResult,
} from '../public/gpt-doug-connector.js';

test('normalizes loopback and HTTPS bridge URLs', () => {
  assert.equal(normalizeBridgeUrl('http://127.0.0.1:8791/'), 'http://127.0.0.1:8791');
  assert.equal(normalizeBridgeUrl('http://localhost:8791'), 'http://localhost:8791');
  assert.equal(normalizeBridgeUrl('https://bridge.example.com'), 'https://bridge.example.com');
  assert.throws(() => normalizeBridgeUrl('http://bridge.example.com'), /must use HTTPS/);
  assert.throws(() => normalizeBridgeUrl('http://127.0.0.1:8791/api'), /without a path/);
  assert.throws(() => normalizeBridgeUrl('http://user:secret@127.0.0.1:8791'), /credentials/);
});

test('discovers a healthy bridge and its allowed model', async () => {
  const calls = [];
  const fakeFetch = async (url, options) => {
    calls.push({ url, options });
    if (url.endsWith('/health')) {
      return new Response(JSON.stringify({ ok: true, model_ready: true, bridge: 'black-house' }), { status: 200 });
    }
    return new Response(JSON.stringify({ bridge: 'black-house', models: [{ name: 'qwen2.5-coder:7b' }] }), { status: 200 });
  };
  const result = await discoverGptDoug({
    baseUrl: 'http://127.0.0.1:8791',
    token: 'session-token',
    model: 'qwen2.5-coder:7b',
  }, fakeFetch);
  assert.equal(result.model, 'qwen2.5-coder:7b');
  assert.equal(result.bridge, 'black-house');
  assert.equal(calls.length, 2);
  assert.equal(calls[0].options.headers.Authorization, 'Bearer session-token');
});

test('sends a non-streaming JSON chat request with project scope', async () => {
  let captured;
  const fakeFetch = async (url, options) => {
    captured = { url, options };
    return new Response(JSON.stringify({
      done: true,
      message: { content: '{"message":"ok","operations":[]}' },
    }), { status: 200 });
  };
  const result = await chatGptDoug(
    { baseUrl: 'http://127.0.0.1:8791', model: 'qwen2.5-coder:7b' },
    [{ role: 'user', content: 'test' }],
    { projectId: 'hello-world', timeoutMs: 1000 },
    fakeFetch,
  );
  const payload = JSON.parse(captured.options.body);
  assert.equal(captured.url, 'http://127.0.0.1:8791/api/chat');
  assert.equal(captured.options.headers['X-Doug-Project'], 'hello-world');
  assert.equal(payload.stream, false);
  assert.equal(payload.format, 'json');
  assert.equal(payload.model, 'qwen2.5-coder:7b');
  assert.equal(result.done, true);
});

test('parses bounded file operations and blocks unsafe paths', () => {
  const parsed = parseAgentResult('```json\n{"message":"done","operations":[{"op":"write_file","path":"src/app.js","content":"ok"}]}\n```');
  assert.deepEqual(parsed.operations, [{ op: 'write_file', path: 'src/app.js', content: 'ok' }]);
  assert.throws(
    () => parseAgentResult('{"operations":[{"op":"write_file","path":"../escape","content":"x"}]}'),
    /unsafe file path/,
  );
  assert.throws(
    () => parseAgentResult('{"operations":[{"op":"delete_file","path":".grim"}]}'),
    /reserved file path/,
  );
});

test('builds a strict and bounded coding-agent prompt', () => {
  const messages = createAgentMessages({
    prompt: 'Build a dashboard',
    mode: 'build',
    files: [{ path: 'index.html', content: 'x'.repeat(30_000) }],
  });
  assert.equal(messages.length, 2);
  assert.match(messages[0].content, /Return ONLY one JSON object/);
  assert.match(messages[0].content, /reserved \.grim directory/);
  assert.ok(messages.reduce((total, message) => total + message.content.length, 0) < 22_000);
});

test('plan mode explicitly forbids file operations', () => {
  const messages = createAgentMessages({ prompt: 'Plan a dashboard', mode: 'plan', files: [] });
  assert.match(messages[0].content, /Return operations as an empty array/);
});
