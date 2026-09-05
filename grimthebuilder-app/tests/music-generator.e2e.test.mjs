import test from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtemp, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import net from 'node:net';
import { fileURLToPath } from 'node:url';
import { WebSocket } from 'ws';

const HERE = path.dirname(fileURLToPath(import.meta.url));
const APP_ROOT = path.resolve(HERE, '..');

async function freePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.once('error', reject);
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address();
      server.close(() => resolve(port));
    });
  });
}

async function waitFor(url, timeoutMs = 15000) {
  const until = Date.now() + timeoutMs;
  let last;
  while (Date.now() < until) {
    try {
      const r = await fetch(url);
      if (r.ok) return r;
      last = new Error(`HTTP ${r.status}`);
    } catch (err) { last = err; }
    await new Promise(r => setTimeout(r, 150));
  }
  throw last || new Error(`Timed out waiting for ${url}`);
}

async function json(url, options = {}) {
  const r = await fetch(url, { headers: { 'content-type': 'application/json', ...(options.headers || {}) }, ...options });
  const data = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

async function terminalRoundTrip(url) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(url);
    const timer = setTimeout(() => { ws.close(); reject(new Error('terminal round-trip timed out')); }, 8000);
    let output = '';
    ws.on('message', raw => {
      const msg = JSON.parse(String(raw));
      if (msg.type === 'ready') ws.send(JSON.stringify({ type: 'stdin', data: 'printf "GRIM_TERM_OK\\n"\n' }));
      if (msg.type === 'terminal') {
        output += msg.text || '';
        if (output.includes('GRIM_TERM_OK')) {
          clearTimeout(timer);
          ws.close();
          resolve(output);
        }
      }
      if (msg.type === 'error') {
        clearTimeout(timer);
        ws.close();
        reject(new Error(msg.message));
      }
    });
    ws.on('error', err => { clearTimeout(timer); reject(err); });
  });
}

test('GrimTheBuilder builds a functional music generator from an agent prompt', { timeout: 30000 }, async t => {
  const port = await freePort();
  const dataDir = await mkdtemp(path.join(os.tmpdir(), 'grim-music-e2e-'));
  const child = spawn(process.execPath, ['server.mjs'], {
    cwd: APP_ROOT,
    env: {
      ...process.env,
      PORT: String(port),
      HOST: '127.0.0.1',
      GRIM_DATA_DIR: dataDir,
      GRIM_ALLOWED_COMMANDS: 'npm,npx,node,pnpm,python,python3,pip,pip3,git,bash,sh',
      OPENAI_API_KEY: '',
      OPENAI_MODEL: ''
    },
    stdio: ['ignore', 'pipe', 'pipe']
  });
  let logs = '';
  child.stdout.on('data', d => { logs += String(d); });
  child.stderr.on('data', d => { logs += String(d); });
  t.after(async () => {
    child.kill('SIGTERM');
    await new Promise(r => setTimeout(r, 100));
    if (!child.killed) child.kill('SIGKILL');
    await rm(dataDir, { recursive: true, force: true });
  });

  const base = `http://127.0.0.1:${port}`;
  await waitFor(`${base}/api/health`).catch(err => { throw new Error(`${err.message}\n${logs}`); });

  const capabilities = await json(`${base}/api/capabilities`);
  assert.equal(capabilities.projects, true);
  assert.equal(capabilities.terminal, true);
  assert.ok(capabilities.localBlueprints.includes('music-generator-v1'));

  const created = await json(`${base}/api/projects`, {
    method: 'POST',
    body: JSON.stringify({ name: 'GrimBeat Music Generator', template: 'static' })
  });
  const id = created.project.id;
  assert.ok(id);

  const prompt = 'Build a fully functional browser music generator app with prompt-aware original beat generation, trap house ambient and synthwave styles, BPM and key controls, Web Audio synthesis, a sequencer, play and stop controls, browser recording, pattern export, responsive design, and no paid external API.';
  const built = await json(`${base}/api/projects/${encodeURIComponent(id)}/agent`, {
    method: 'POST',
    body: JSON.stringify({ prompt, mode: 'build' })
  });
  assert.equal(built.provider, 'local');
  assert.equal(built.blueprint, 'music-generator-v1');
  assert.ok(built.operations.length >= 4);

  const project = await json(`${base}/api/projects/${encodeURIComponent(id)}`);
  for (const required of ['index.html', 'style.css', 'script.js', 'README.md']) assert.ok(project.project.files.includes(required), `missing ${required}`);
  assert.ok(project.checkpoints.length >= 1, 'agent build must create a checkpoint');

  const preview = await (await fetch(`${base}/preview/${encodeURIComponent(id)}/`)).text();
  assert.match(preview, /GrimBeat Generator/);
  assert.match(preview, /Generate/);
  assert.match(preview, /Record/);

  const script = await (await fetch(`${base}/api/projects/${encodeURIComponent(id)}/file?path=script.js`)).text();
  assert.match(script, /AudioContext/);
  assert.match(script, /scheduleStep/);
  assert.match(script, /MediaRecorder/);
  assert.match(script, /downloadPattern/);
  new Function(script);

  const terminalOutput = await terminalRoundTrip(`ws://127.0.0.1:${port}/ws/projects/${encodeURIComponent(id)}/terminal`);
  assert.match(terminalOutput, /GRIM_TERM_OK/);

  const health = await json(`${base}/api/health`);
  assert.equal(health.status, 'ok');
  assert.equal(health.projects, 1);
});
