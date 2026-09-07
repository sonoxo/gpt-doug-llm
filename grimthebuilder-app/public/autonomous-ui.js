import {
  createAgentMessages,
  discoverGptDoug,
  parseAgentResult,
} from './gpt-doug-connector.js';
import { runAutonomousWorkflow } from './autonomous-agent.js';

const $ = selector => document.querySelector(selector);
const sleep = milliseconds => new Promise(resolve => setTimeout(resolve, milliseconds));
const BINARY_RE = /\.(?:png|jpe?g|gif|webp|ico|bmp|tiff?|avif|mp3|wav|ogg|flac|mp4|mov|avi|mkv|webm|woff2?|ttf|otf|zip|gz|tgz|7z|rar|pdf)$/i;
const LOCK_RE = /(?:^|\/)(?:package-lock\.json|pnpm-lock\.yaml|yarn\.lock)$/i;

let controller = null;
let activeProcessId = null;
let activeProjectId = null;

function api(url, options = {}) {
  return fetch(url, {
    cache: 'no-store',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  }).then(async response => {
    const contentType = response.headers.get('content-type') || '';
    const body = contentType.includes('json')
      ? await response.json().catch(() => ({}))
      : await response.text();
    if (!response.ok) {
      const error = new Error(body?.error || body?.message || `Request failed (${response.status})`);
      error.status = response.status;
      error.body = body;
      throw error;
    }
    return body;
  });
}

function bridgeConfig() {
  return {
    baseUrl: localStorage.getItem('grim.gptDoug.url') || 'http://127.0.0.1:8791',
    token: sessionStorage.getItem('grim.gptDoug.token') || '',
    model: localStorage.getItem('grim.gptDoug.model') || 'qwen2.5-coder:7b',
  };
}

async function currentProject() {
  const payload = await api('/api/projects');
  const projects = Array.isArray(payload.projects) ? payload.projects : [];
  if (!projects.length) throw new Error('No project exists. Create a project first.');
  const buttons = [...document.querySelectorAll('.projects .item')];
  const activeIndex = buttons.findIndex(button => button.classList.contains('active'));
  return projects[activeIndex >= 0 ? activeIndex : 0] || projects[0];
}

function setupUi() {
  if ($('#autonomousRuntime')) return;
  const style = document.createElement('style');
  style.textContent = `
    #autonomousRuntime{border:1px solid #263345;background:#0a1018;padding:9px;margin-bottom:2px;font:11px/1.45 ui-monospace,monospace}
    #autonomousRuntime .autoHead{display:flex;align-items:center;gap:7px;margin-bottom:7px}
    #autonomousRuntime .autoDot{width:8px;height:8px;border-radius:50%;background:#6df08d;box-shadow:0 0 10px #6df08d88}
    #autonomousRuntime strong{font-size:10px;letter-spacing:.08em}
    #autonomousRuntime small{color:#8f9bad}
    #autonomousRuntime .autoStages{display:grid;gap:3px;max-height:116px;overflow:auto}
    #autonomousRuntime .autoStage{display:grid;grid-template-columns:66px 1fr;gap:7px;color:#8f9bad}
    #autonomousRuntime .autoStage b{color:#dfe8f5;font-weight:700}
    #autonomousRuntime .autoStage.running b{color:#ffb25f}
    #autonomousRuntime .autoStage.success b{color:#76ef98}
    #autonomousRuntime .autoStage.failed b{color:#ff6f7d}
    #autonomousRuntime .autoActions{display:flex;gap:6px;margin-top:7px}
    #autonomousRuntime button{font-size:10px;padding:5px 8px}
    #autoCancel[hidden]{display:none}
  `;
  document.head.appendChild(style);

  const panel = document.createElement('section');
  panel.id = 'autonomousRuntime';
  panel.innerHTML = `
    <div class="autoHead"><span class="autoDot"></span><strong>AUTONOMOUS RUNTIME ON</strong><small>default for every GPT Doug build</small></div>
    <div id="autoSummary">Ready: generate → apply → install → start → verify → repair.</div>
    <div id="autoStages" class="autoStages"></div>
    <div class="autoActions"><button id="autoCancel" type="button" hidden>CANCEL RUN</button></div>
  `;
  const agentFeed = $('#agentFeed');
  agentFeed?.parentNode?.insertBefore(panel, agentFeed);
  $('#autoCancel').onclick = () => controller?.abort();
}

function resetStages() {
  $('#autoStages').innerHTML = '';
  $('#autoSummary').textContent = 'Starting autonomous build…';
}

function stageRow(event) {
  const key = `${event.stage}-${event.attempt || 0}`;
  let row = document.querySelector(`[data-auto-stage="${CSS.escape(key)}"]`);
  if (!row) {
    row = document.createElement('div');
    row.className = 'autoStage';
    row.dataset.autoStage = key;
    row.innerHTML = '<b></b><span></span>';
    $('#autoStages').appendChild(row);
  }
  row.className = `autoStage ${event.status || ''}`;
  row.querySelector('b').textContent = String(event.stage || 'work').toUpperCase();
  row.querySelector('span').textContent = event.detail || event.status || '';
  $('#autoStages').scrollTop = $('#autoStages').scrollHeight;
  $('#autoSummary').textContent = event.status === 'failed'
    ? `Failed during ${event.stage}.`
    : event.status === 'success' && event.stage === 'complete'
      ? 'Application generated and verified.'
      : event.detail || 'Autonomous build running…';
}

async function collectFiles(project) {
  const files = [];
  let remaining = 15_000;
  for (const path of (project.files || []).filter(file => !BINARY_RE.test(file) && !LOCK_RE.test(file)).slice(0, 40)) {
    if (remaining <= 0) break;
    try {
      const response = await fetch(`/api/projects/${encodeURIComponent(project.id)}/file?path=${encodeURIComponent(path)}`, { cache: 'no-store' });
      if (!response.ok) continue;
      const text = await response.text();
      const content = text.slice(0, Math.min(4_000, remaining));
      files.push({ path, content });
      remaining -= content.length;
    } catch {
      // A single unreadable file must not block the entire build.
    }
  }
  return files;
}

async function streamModel(config, messages, { projectId, signal, onProgress }) {
  const headers = { Accept: 'application/x-ndjson', 'Content-Type': 'application/json' };
  if (config.token) headers.Authorization = `Bearer ${config.token}`;
  if (projectId) headers['X-Doug-Project'] = projectId;
  const response = await fetch(`${config.baseUrl.replace(/\/+$/, '')}/api/chat/stream`, {
    method: 'POST',
    mode: 'cors',
    cache: 'no-store',
    headers,
    signal,
    body: JSON.stringify({
      model: config.model,
      messages,
      stream: true,
      format: 'json',
      options: { temperature: 0.15, num_predict: 2048, num_ctx: 8192 },
    }),
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.error || `Streaming request failed (${response.status}). Restart with npm run start:full.`);
  }
  if (!response.body) throw new Error('The browser did not expose the streaming response body.');

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let content = '';
  let finalChunk = null;
  while (true) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
    const lines = buffer.split('\n');
    buffer = lines.pop() || '';
    for (const line of lines) {
      if (!line.trim()) continue;
      const chunk = JSON.parse(line);
      if (chunk.error) throw new Error(chunk.error);
      const token = chunk.message?.content || '';
      content += token;
      finalChunk = chunk;
      onProgress?.(content.length, token.length);
    }
    if (done) break;
  }
  if (buffer.trim()) {
    const chunk = JSON.parse(buffer);
    if (chunk.error) throw new Error(chunk.error);
    content += chunk.message?.content || '';
    finalChunk = chunk;
  }
  if (!finalChunk?.done || !content.trim()) throw new Error('GPT Doug stream ended before a complete response was produced.');
  return { ...finalChunk, message: { role: 'assistant', content } };
}

async function applyOperations(projectId, operations, mode, { signal } = {}) {
  if ((mode === 'plan' || mode === 'explain') && operations.length) {
    throw new Error(`${mode.toUpperCase()} mode cannot modify files.`);
  }
  if (!operations.length) return;
  await api(`/api/projects/${encodeURIComponent(projectId)}/checkpoints`, {
    method: 'POST',
    body: JSON.stringify({ label: `Before autonomous ${mode}` }),
    signal,
  });
  for (const operation of operations) {
    if (signal?.aborted) throw new DOMException('Agent run cancelled.', 'AbortError');
    if (operation.op === 'write_file' && BINARY_RE.test(operation.path)) {
      throw new Error(`Text models cannot create binary file ${operation.path}. Use SVG or CSS artwork.`);
    }
    const endpoint = `/api/projects/${encodeURIComponent(projectId)}/file?path=${encodeURIComponent(operation.path)}`;
    if (operation.op === 'write_file') {
      await api(endpoint, { method: 'PUT', body: JSON.stringify({ content: operation.content }), signal });
    } else {
      await api(endpoint, { method: 'DELETE', signal });
    }
  }
}

async function inspectProject(projectId) {
  const project = (await api(`/api/projects/${encodeURIComponent(projectId)}`)).project;
  const files = project.files || [];
  if (files.includes('package.json')) {
    const packageText = await fetch(`/api/projects/${encodeURIComponent(projectId)}/file?path=package.json`, { cache: 'no-store' }).then(response => response.text());
    let packageJson;
    try { packageJson = JSON.parse(packageText); } catch { throw new Error('package.json is invalid JSON.'); }
    const dependencies = { ...(packageJson.dependencies || {}), ...(packageJson.devDependencies || {}) };
    return { kind: 'node', project, needsInstall: Object.keys(dependencies).length > 0, installCommand: 'npm', installArgs: files.includes('package-lock.json') ? ['ci'] : ['install'] };
  }
  if (files.includes('app.py') || files.includes('main.py')) {
    return { kind: 'python', project, needsInstall: files.includes('requirements.txt'), installCommand: 'python3', installArgs: ['-m', 'pip', 'install', '-r', 'requirements.txt'] };
  }
  if (files.includes('index.html')) return { kind: 'static', project, needsInstall: false };
  throw new Error('No runnable entrypoint was generated. Expected index.html, package.json, app.py, or main.py.');
}

async function waitForProcess(projectId, processId, { signal, timeoutMs = 300_000 } = {}) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (signal?.aborted) {
      await api(`/api/processes/${encodeURIComponent(processId)}/stop`, { method: 'POST' }).catch(() => {});
      throw new DOMException('Agent run cancelled.', 'AbortError');
    }
    const processes = (await api(`/api/projects/${encodeURIComponent(projectId)}/processes`)).processes || [];
    const process = processes.find(item => item.id === processId);
    if (process && process.status !== 'running' && process.status !== 'starting') {
      const logs = await api(`/api/processes/${encodeURIComponent(processId)}/logs`).catch(() => ({ logs: [] }));
      const output = (logs.logs || []).map(item => item.text).join('').slice(-12_000);
      if (process.exitCode === 0) return { process, output };
      const error = new Error(`Process failed with exit code ${process.exitCode ?? 'unknown'}.`);
      error.output = output;
      throw error;
    }
    await sleep(500);
  }
  await api(`/api/processes/${encodeURIComponent(processId)}/stop`, { method: 'POST' }).catch(() => {});
  throw new Error('Process timed out.');
}

async function installDependencies(projectId, inspection, { signal } = {}) {
  if (!inspection.needsInstall) return { detail: 'No dependencies required.' };
  const spawned = await api(`/api/projects/${encodeURIComponent(projectId)}/processes`, {
    method: 'POST',
    body: JSON.stringify({ command: inspection.installCommand, args: inspection.installArgs }),
    signal,
  });
  const completed = await waitForProcess(projectId, spawned.process.id, { signal });
  return { detail: 'Dependencies installed.', logs: completed.output };
}

async function stopRunningApps(projectId) {
  const processes = (await api(`/api/projects/${encodeURIComponent(projectId)}/processes`)).processes || [];
  for (const process of processes.filter(item => item.status === 'running' && !['bash', 'sh'].includes(item.command))) {
    await api(`/api/processes/${encodeURIComponent(process.id)}/stop`, { method: 'POST' }).catch(() => {});
  }
}

async function startProject(projectId, inspection, { signal } = {}) {
  if (inspection.kind === 'static') {
    activeProcessId = null;
    return { kind: 'static', previewUrl: `/preview/${encodeURIComponent(projectId)}/`, detail: 'Static preview ready.' };
  }
  await stopRunningApps(projectId);
  const started = await api(`/api/projects/${encodeURIComponent(projectId)}/start`, { method: 'POST', signal });
  activeProcessId = started.process.id;
  return { kind: inspection.kind, process: started.process, previewUrl: `/preview/${encodeURIComponent(projectId)}/`, detail: `Runtime started on port ${started.process.port}.` };
}

async function processLogs(processId) {
  if (!processId) return '';
  const payload = await api(`/api/processes/${encodeURIComponent(processId)}/logs`).catch(() => ({ logs: [] }));
  return (payload.logs || []).map(item => item.text).join('').slice(-12_000);
}

async function verifyProject(projectId, runtime, inspection, { signal } = {}) {
  const deadline = Date.now() + (inspection.kind === 'static' ? 12_000 : 35_000);
  let lastDetail = '';
  while (Date.now() < deadline) {
    if (signal?.aborted) throw new DOMException('Agent run cancelled.', 'AbortError');
    if (runtime.process?.id) {
      const processes = (await api(`/api/projects/${encodeURIComponent(projectId)}/processes`)).processes || [];
      const process = processes.find(item => item.id === runtime.process.id);
      if (process && !['running', 'starting'].includes(process.status)) {
        return { verified: false, detail: `Runtime exited with code ${process.exitCode ?? 'unknown'}.`, logs: await processLogs(process.id) };
      }
    }
    try {
      const route = inspection.kind === 'static'
        ? runtime.previewUrl
        : `${runtime.previewUrl.replace(/\/$/, '')}/api/health`;
      const response = await fetch(route, { cache: 'no-store', signal });
      const text = await response.text();
      if (response.ok) {
        if (inspection.kind === 'static') {
          return { verified: true, detail: 'Static preview returned successfully.' };
        }
        let health = null;
        try { health = JSON.parse(text); } catch { health = null; }
        if (health && (health.ok === true || health.status === 'ok' || health.healthy === true)) {
          return { verified: true, detail: 'Backend health endpoint verified.', health };
        }
        lastDetail = 'GET /api/health did not return a truthful healthy JSON response.';
      } else {
        lastDetail = `Health route returned HTTP ${response.status}.`;
      }
    } catch (error) {
      if (error.name === 'AbortError') throw error;
      lastDetail = error.message;
    }
    await sleep(750);
  }
  return { verified: false, detail: lastDetail || 'Application did not become healthy before the timeout.', logs: await processLogs(runtime.process?.id) };
}

async function refreshWorkspace() {
  const active = document.querySelector('.projects .item.active');
  active?.click();
  await sleep(200);
  document.querySelector('[data-tab="preview"]')?.click();
}

async function runAutonomous(event) {
  const provider = $('#agentProvider')?.value;
  if (provider !== 'gpt-doug') return;
  event.preventDefault();
  event.stopImmediatePropagation();
  if (controller) return;

  const prompt = $('#agentPrompt')?.value.trim();
  if (!prompt) return;
  const mode = $('#agentMode')?.value || 'build';
  const button = $('#agentRun');
  resetStages();
  controller = new AbortController();
  $('#autoCancel').hidden = false;
  button.disabled = true;
  button.textContent = 'AUTONOMOUS BUILD RUNNING…';

  try {
    const project = await currentProject();
    activeProjectId = project.id;
    const config = bridgeConfig();
    const discovered = await discoverGptDoug(config);
    config.baseUrl = discovered.baseUrl;
    config.model = discovered.model;

    const result = await runAutonomousWorkflow({
      prompt,
      mode,
      maxRepairs: 3,
      signal: controller.signal,
      onStage: stageRow,
      generate: async ({ prompt: request, mode: requestMode, signal, emit }) => {
        emit('generate', 'running', 'GPT Doug is streaming project files.');
        const latest = (await api(`/api/projects/${encodeURIComponent(project.id)}`)).project;
        const files = await collectFiles(latest);
        const messages = createAgentMessages({ prompt: request, mode: requestMode, files });
        const raw = await streamModel(config, messages, {
          projectId: project.id,
          signal,
          onProgress: characters => emit('generate', 'running', `Streaming model output: ${characters.toLocaleString()} characters.`),
        });
        const parsed = parseAgentResult(raw.message.content);
        emit('generate', 'success', `Generated ${parsed.operations.length} file operation(s).`);
        return { ...parsed, provider: 'gpt-doug-stream', model: config.model };
      },
      apply: (operations, applyMode, context) => applyOperations(project.id, operations, applyMode, context),
      inspect: () => inspectProject(project.id),
      install: (inspection, context) => installDependencies(project.id, inspection, context),
      start: (inspection, context) => startProject(project.id, inspection, context),
      verify: (runtime, inspection, context) => verifyProject(project.id, runtime, inspection, context),
    });

    const summary = `${result.message}\nVerified: ${result.verified ? 'yes' : 'no'}\nRepairs: ${result.repairs}\nModel: ${result.model || config.model}`;
    const message = document.createElement('div');
    message.className = 'msg grim';
    message.innerHTML = '<b>GRIM AUTONOMOUS</b><div></div>';
    message.querySelector('div').textContent = summary;
    $('#agentFeed')?.appendChild(message);
    await refreshWorkspace();
  } catch (error) {
    const cancelled = error?.name === 'AbortError';
    stageRow({ stage: cancelled ? 'cancelled' : (error.stage || 'failed'), status: 'failed', detail: cancelled ? 'Run cancelled.' : error.message, attempt: error.attempts || 0 });
    if (activeProcessId) await api(`/api/processes/${encodeURIComponent(activeProcessId)}/stop`, { method: 'POST' }).catch(() => {});
  } finally {
    controller = null;
    activeProcessId = null;
    activeProjectId = null;
    $('#autoCancel').hidden = true;
    button.disabled = false;
    button.textContent = 'RUN AGENT';
  }
}

setupUi();
localStorage.setItem('grim.autonomous.default', '1');
$('#agentRun')?.addEventListener('click', runAutonomous, true);
window.addEventListener('beforeunload', () => controller?.abort());
