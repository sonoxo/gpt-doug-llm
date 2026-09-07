import { spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const SCRIPT_PATH = fileURLToPath(import.meta.url);
const APP_ROOT = path.resolve(path.dirname(SCRIPT_PATH), '..');
const REPO_ROOT = path.resolve(APP_ROOT, '..');
const ownedChildren = new Map();
let shuttingDown = false;

const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));

export function resolveAppPort(value = process.env.PORT || '8787') {
  const port = Number(value);
  if (!Number.isInteger(port) || port < 1 || port > 65535) {
    throw new Error(`Invalid GrimTheBuilder port: ${value}`);
  }
  return port;
}

export function mergeBridgeOrigins(raw = '', port = 8787) {
  const origins = new Set(
    String(raw)
      .split(',')
      .map(value => value.trim())
      .filter(Boolean),
  );
  origins.add(`http://localhost:${port}`);
  origins.add(`http://127.0.0.1:${port}`);
  return [...origins].join(',');
}

function endpoint(baseUrl, pathname) {
  return `${String(baseUrl).replace(/\/+$/, '')}${pathname}`;
}

async function request(url, options = {}, timeoutMs = 3_000) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const text = await response.text();
    let body = {};
    if (text) {
      try {
        body = JSON.parse(text);
      } catch {
        body = { text };
      }
    }
    return { response, body };
  } finally {
    clearTimeout(timeout);
  }
}

async function waitFor(url, predicate, { options = {}, timeoutMs = 25_000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  let lastError = null;
  while (Date.now() < deadline) {
    try {
      const result = await request(url, options, 2_000);
      if (predicate(result)) return result;
    } catch (error) {
      lastError = error;
    }
    await sleep(500);
  }
  throw new Error(`Timed out waiting for ${url}${lastError ? `: ${lastError.message}` : ''}`);
}

function startOwned(name, command, args, options = {}) {
  console.log(`\n[start] ${name}: ${command} ${args.join(' ')}`);
  const child = spawn(command, args, {
    cwd: options.cwd,
    env: options.env || process.env,
    stdio: 'inherit',
  });
  ownedChildren.set(name, child);
  child.once('error', error => {
    if (!shuttingDown) fail(`${name} failed to start: ${error.message}`);
  });
  child.once('exit', (code, signal) => {
    ownedChildren.delete(name);
    if (!shuttingDown) {
      fail(`${name} stopped unexpectedly (${signal || code || 0}).`);
    }
  });
  return child;
}

function stopOwned(exitCode = 0) {
  if (shuttingDown) return;
  shuttingDown = true;
  for (const child of ownedChildren.values()) {
    if (!child.killed) child.kill('SIGTERM');
  }
  setTimeout(() => process.exit(exitCode), 300).unref();
}

function fail(message) {
  console.error(`\n[error] ${message}`);
  stopOwned(1);
}

async function ensureOllama(ollamaUrl) {
  const tagsUrl = endpoint(ollamaUrl, '/api/tags');
  try {
    const result = await request(tagsUrl);
    if (result.response.ok) {
      console.log(`[ready] Ollama: ${ollamaUrl}`);
      return;
    }
  } catch {
    // Start the local service below.
  }

  const parsed = new URL(ollamaUrl);
  if (parsed.protocol !== 'http:' || !['127.0.0.1', 'localhost', '::1'].includes(parsed.hostname)) {
    throw new Error(`Ollama is unavailable at ${ollamaUrl}. Start that configured service first.`);
  }

  startOwned('Ollama', process.env.OLLAMA_BIN || 'ollama', ['serve'], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      OLLAMA_HOST: `${parsed.hostname}:${parsed.port || '11434'}`,
    },
  });
  await waitFor(tagsUrl, result => result.response.ok, { timeoutMs: 30_000 });
  console.log(`[ready] Ollama: ${ollamaUrl}`);
}

async function probeBridge(bridgeUrl, appOrigin) {
  try {
    return await request(endpoint(bridgeUrl, '/health'), {
      headers: { Origin: appOrigin, Accept: 'application/json' },
    });
  } catch {
    return null;
  }
}

export async function probeStreamingBridge(bridgeUrl, appOrigin) {
  try {
    return await request(endpoint(bridgeUrl, '/api/chat/stream'), {
      method: 'OPTIONS',
      headers: {
        Origin: appOrigin,
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'Content-Type, X-Doug-Project',
      },
    });
  } catch {
    return null;
  }
}

async function ensureBridge({ bridgeUrl, ollamaUrl, appOrigin, appPort }) {
  const existing = await probeBridge(bridgeUrl, appOrigin);
  if (existing?.response.ok && existing.body.ok === true && existing.body.model_ready === true) {
    const allowedOrigin = existing.response.headers.get('access-control-allow-origin');
    if (allowedOrigin !== appOrigin) {
      throw new Error(
        `A bridge is already using ${bridgeUrl} but does not allow ${appOrigin}. `
        + "Stop it with: pkill -f '[w]akeup3lm'",
      );
    }
    const streaming = await probeStreamingBridge(bridgeUrl, appOrigin);
    if (!streaming?.response.ok || streaming.body.stream !== 'ndjson') {
      throw new Error(
        `A legacy non-streaming bridge is already using ${bridgeUrl}. `
        + "Stop the old launcher with Ctrl-C (or run: pkill -f '[w]akeup3lm') and run npm run start:full again.",
      );
    }
    console.log(`[ready] GPT Doug streaming bridge: ${bridgeUrl}`);
    return;
  }

  const origins = mergeBridgeOrigins(process.env.DOUG_BRIDGE_ORIGINS, appPort);
  startOwned('GPT Doug streaming bridge', process.env.PYTHON_BIN || 'python3', ['-m', 'wakeup3lm.stream_bridge'], {
    cwd: REPO_ROOT,
    env: {
      ...process.env,
      PYTHONUNBUFFERED: '1',
      PYTHONPATH: process.env.PYTHONPATH
        ? `${REPO_ROOT}${path.delimiter}${process.env.PYTHONPATH}`
        : REPO_ROOT,
      DOUG_BRIDGE_ORIGINS: origins,
      DOUG_BRIDGE_OLLAMA_URL: ollamaUrl,
      DOUG_BRIDGE_MODEL: process.env.DOUG_BRIDGE_MODEL || 'qwen2.5-coder:7b',
      DOUG_BRIDGE_MODELS: process.env.DOUG_BRIDGE_MODELS || process.env.DOUG_BRIDGE_MODEL || 'qwen2.5-coder:7b',
    },
  });

  const result = await waitFor(
    endpoint(bridgeUrl, '/health'),
    probe => probe.response.ok && probe.body.ok === true,
    {
      options: { headers: { Origin: appOrigin, Accept: 'application/json' } },
      timeoutMs: 30_000,
    },
  );
  if (result.body.model_ready !== true) {
    throw new Error(result.body.error || result.body.detail || 'GPT Doug model is not ready.');
  }
  await waitFor(
    endpoint(bridgeUrl, '/api/chat/stream'),
    probe => probe.response.ok && probe.body.stream === 'ndjson',
    {
      options: {
        method: 'OPTIONS',
        headers: {
          Origin: appOrigin,
          'Access-Control-Request-Method': 'POST',
          'Access-Control-Request-Headers': 'Content-Type, X-Doug-Project',
        },
      },
      timeoutMs: 10_000,
    },
  );
  console.log(`[ready] GPT Doug streaming bridge: ${bridgeUrl}`);
}

async function ensureApp(appOrigin) {
  try {
    const current = await request(endpoint(appOrigin, '/api/health'));
    if (current.response.ok && current.body.status === 'ok') {
      console.log(`[ready] GrimTheBuilder: ${appOrigin}`);
      return;
    }
  } catch {
    // Start the app below.
  }

  startOwned('GrimTheBuilder', process.execPath, ['server.mjs'], {
    cwd: APP_ROOT,
    env: process.env,
  });
  await waitFor(
    endpoint(appOrigin, '/api/health'),
    result => result.response.ok && result.body.status === 'ok',
  );
  console.log(`[ready] GrimTheBuilder: ${appOrigin}`);
}

async function ensureProject(appOrigin) {
  const projectsUrl = endpoint(appOrigin, '/api/projects');
  const listed = await request(projectsUrl, { headers: { Accept: 'application/json' } });
  if (!listed.response.ok) throw new Error(listed.body.error || 'Could not list projects.');
  if (Array.isArray(listed.body.projects) && listed.body.projects.length) {
    console.log(`[ready] Project: ${listed.body.projects[0].name}`);
    return listed.body.projects[0];
  }

  const created = await request(projectsUrl, {
    method: 'POST',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
    body: JSON.stringify({ name: 'GPT Doug Build', template: 'static' }),
  });
  if (!created.response.ok) throw new Error(created.body.error || 'Could not create the first project.');
  console.log(`[ready] Project created: ${created.body.project.name}`);
  return created.body.project;
}

function openBrowser(appOrigin) {
  if (process.env.GRIM_OPEN_BROWSER === '0') return;
  const command = process.platform === 'darwin'
    ? ['open', [appOrigin]]
    : process.platform === 'win32'
      ? ['cmd', ['/c', 'start', '', appOrigin]]
      : ['xdg-open', [appOrigin]];
  const child = spawn(command[0], command[1], { stdio: 'ignore', detached: true });
  child.unref();
}

export async function main() {
  const appPort = resolveAppPort();
  const appOrigin = process.env.GRIM_APP_ORIGIN || `http://localhost:${appPort}`;
  const bridgeUrl = process.env.DOUG_BRIDGE_URL || `http://127.0.0.1:${process.env.DOUG_BRIDGE_PORT || '8791'}`;
  const ollamaUrl = process.env.DOUG_BRIDGE_OLLAMA_URL || 'http://127.0.0.1:11434';

  console.log('GrimTheBuilder + GPT Doug autonomous startup');
  console.log(`Repository: ${REPO_ROOT}`);
  await ensureOllama(ollamaUrl);
  await ensureBridge({ bridgeUrl, ollamaUrl, appOrigin, appPort });
  await ensureApp(appOrigin);
  await ensureProject(appOrigin);

  console.log('\n==============================================');
  console.log(`ONLINE: ${appOrigin}`);
  console.log(`STREAMING MODEL BRIDGE: ${bridgeUrl}`);
  console.log('AUTONOMOUS MODE: default for every GPT Doug build');
  console.log('Leave this terminal open. Press Ctrl-C to stop.');
  console.log('==============================================\n');
  openBrowser(appOrigin);
}

process.on('SIGINT', () => stopOwned(0));
process.on('SIGTERM', () => stopOwned(0));

if (process.argv[1] && path.resolve(process.argv[1]) === SCRIPT_PATH) {
  main().catch(error => fail(error.message));
}
