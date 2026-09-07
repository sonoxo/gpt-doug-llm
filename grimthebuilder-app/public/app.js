import {
  chatGptDoug,
  createAgentMessages,
  discoverGptDoug,
  parseAgentResult,
} from './gpt-doug-connector.js';

const $ = selector => document.querySelector(selector);
const BRIDGE_URL = 'http://127.0.0.1:8791';
const BRIDGE_MODEL = 'qwen2.5-coder:7b';
let projects = [];
let project = null;
let currentFile = null;
let editor = null;
let terminalSocket = null;
let saveTimer = null;
let bridge = {
  connected: false,
  baseUrl: localStorage.getItem('grim.gptDoug.url') || BRIDGE_URL,
  token: sessionStorage.getItem('grim.gptDoug.token') || '',
  model: localStorage.getItem('grim.gptDoug.model') || BRIDGE_MODEL,
  models: [],
};

const api = async (url, options = {}) => {
  const response = await fetch(url, {
    headers: { 'content-type': 'application/json', ...(options.headers || {}) },
    ...options,
  });
  if (!response.ok) {
    const failure = await response.json().catch(() => ({}));
    throw new Error(failure.error || `Request failed (${response.status})`);
  }
  const contentType = response.headers.get('content-type') || '';
  return contentType.includes('json') ? response.json() : response.text();
};

function toast(text) {
  $('#toast').textContent = text;
  $('#toast').classList.add('show');
  setTimeout(() => $('#toast').classList.remove('show'), 1800);
}

function setBridgeStatus(state, title, detail = '') {
  const card = $('#bridgeStatus');
  card.className = `connectorStatus ${state}`;
  $('#bridgeStatusText').textContent = title;
  $('#bridgeStatusDetail').textContent = detail;
  $('#bridgeQuickConnect').textContent = bridge.connected ? 'SETTINGS' : state === 'connecting' ? 'WAIT…' : 'CONNECT';
}

function renderBridgeModels(models = bridge.models) {
  const select = $('#bridgeModel');
  const choices = models.length ? models : [bridge.model || BRIDGE_MODEL];
  select.innerHTML = '';
  for (const name of choices) {
    const option = document.createElement('option');
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  }
  if (choices.includes(bridge.model)) select.value = bridge.model;
  bridge.model = select.value || BRIDGE_MODEL;
}

function openBridgeSettings() {
  $('#bridgeUrl').value = bridge.baseUrl;
  $('#bridgeToken').value = bridge.token;
  $('#bridgeOrigin').textContent = location.origin;
  $('#bridgeCommand').textContent = `DOUG_BRIDGE_ORIGINS='${location.origin}' python3 -m wakeup3lm.bridge`;
  renderBridgeModels();
  $('#bridgeModal').hidden = false;
  $('#bridgeUrl').focus();
}

function closeBridgeSettings() {
  $('#bridgeModal').hidden = true;
}

async function connectBridge({ quiet = false } = {}) {
  const baseUrl = $('#bridgeUrl').value.trim() || bridge.baseUrl;
  const token = $('#bridgeToken').value.trim();
  const requestedModel = $('#bridgeModel').value || bridge.model;
  setBridgeStatus('connecting', 'CONNECTING TO GPT DOUG', baseUrl);
  $('#bridgeResult').textContent = 'Checking /health and discovering /api/tags…';
  $('#bridgeConnect').disabled = true;
  try {
    const result = await discoverGptDoug({ baseUrl, token, model: requestedModel });
    bridge = {
      connected: true,
      baseUrl: result.baseUrl,
      token,
      model: result.model,
      models: result.models,
    };
    localStorage.setItem('grim.gptDoug.url', bridge.baseUrl);
    localStorage.setItem('grim.gptDoug.model', bridge.model);
    localStorage.setItem('grim.gptDoug.enabled', '1');
    if (token) sessionStorage.setItem('grim.gptDoug.token', token);
    else sessionStorage.removeItem('grim.gptDoug.token');
    renderBridgeModels(result.models);
    $('#bridgeModel').value = bridge.model;
    $('#bridgeResult').textContent = `CONNECTED\nBridge: ${result.bridge}\nModel: ${bridge.model}`;
    setBridgeStatus('connected', 'GPT DOUG ONLINE', bridge.model);
    if (!quiet) toast('GPT DOUG CONNECTED');
    return bridge;
  } catch (error) {
    bridge.connected = false;
    localStorage.setItem('grim.gptDoug.enabled', '0');
    $('#bridgeResult').textContent = `${error.message}\n\nKeep Ollama and the bridge running. The bridge must allow this exact origin: ${location.origin}`;
    setBridgeStatus('error', 'GPT DOUG CONNECTION FAILED', error.message);
    throw error;
  } finally {
    $('#bridgeConnect').disabled = false;
  }
}

function disconnectBridge() {
  bridge.connected = false;
  bridge.token = '';
  bridge.models = [];
  localStorage.setItem('grim.gptDoug.enabled', '0');
  sessionStorage.removeItem('grim.gptDoug.token');
  $('#bridgeToken').value = '';
  $('#bridgeResult').textContent = 'Disconnected. The session token was cleared.';
  setBridgeStatus('disconnected', 'GPT DOUG OFFLINE', 'Click CONNECT to use your local model.');
  toast('GPT DOUG DISCONNECTED');
}

async function restoreBridge() {
  $('#bridgeUrl').value = bridge.baseUrl;
  $('#bridgeToken').value = bridge.token;
  renderBridgeModels();
  if (localStorage.getItem('grim.gptDoug.enabled') !== '1') {
    setBridgeStatus('disconnected', 'GPT DOUG OFFLINE', 'Click CONNECT to use your local model.');
    return;
  }
  try {
    await connectBridge({ quiet: true });
  } catch {
    // connectBridge already shows the actionable failure.
  }
}

async function boot() {
  $('#agentProvider').value = localStorage.getItem('grim.agent.provider') || 'gpt-doug';
  restoreBridge();
  try {
    const health = await api('/api/health');
    $('#status').textContent = `${health.status.toUpperCase()} · NODE RUNTIME`;
    await loadProjects();
    initMonaco();
  } catch (error) {
    $('#status').textContent = 'RUNTIME ERROR';
    toast(error.message);
  }
}

function renderProjects() {
  $('#projectList').innerHTML = '';
  for (const item of projects) {
    const button = document.createElement('button');
    button.className = `item${project?.id === item.id ? ' active' : ''}`;
    button.textContent = item.name;
    button.onclick = () => openProject(item.id);
    $('#projectList').appendChild(button);
  }
}

async function loadProjects() {
  projects = (await api('/api/projects')).projects;
  renderProjects();
  if (!project && projects[0]) await openProject(projects[0].id);
}

async function openProject(id) {
  await saveCurrent();
  project = (await api(`/api/projects/${encodeURIComponent(id)}`)).project;
  currentFile = project.files[0] || null;
  projects = (await api('/api/projects')).projects;
  renderProjects();
  renderFiles();
  if (currentFile) await openFile(currentFile, { save: false });
  connectTerminal();
  refreshPreview();
}

function renderFiles() {
  const wrapper = $('#fileList');
  wrapper.innerHTML = '';
  for (const file of project?.files || []) {
    const button = document.createElement('button');
    button.className = `item${file === currentFile ? ' active' : ''}`;
    button.textContent = file;
    button.onclick = () => openFile(file);
    wrapper.appendChild(button);
  }
}

async function openFile(file, { save = true } = {}) {
  if (save) await saveCurrent();
  currentFile = file;
  renderFiles();
  const text = await api(`/api/projects/${encodeURIComponent(project.id)}/file?path=${encodeURIComponent(file)}`);
  setEditor(text, languageFor(file));
}

function getEditor() {
  return editor ? editor.getValue() : $('#fallbackEditor').value;
}

function setEditor(value, language) {
  if (editor) {
    const old = editor.getModel();
    const model = monaco.editor.createModel(value, language);
    editor.setModel(model);
    old?.dispose();
    editor.focus();
  } else {
    $('#fallbackEditor').value = value;
  }
}

async function saveCurrent() {
  if (!project || !currentFile) return;
  await api(`/api/projects/${encodeURIComponent(project.id)}/file?path=${encodeURIComponent(currentFile)}`, {
    method: 'PUT',
    body: JSON.stringify({ content: getEditor() }),
  }).catch(error => toast(error.message));
}

function scheduleSave() {
  clearTimeout(saveTimer);
  saveTimer = setTimeout(async () => {
    await saveCurrent();
    refreshPreview();
  }, 500);
}

function initMonaco() {
  if (!window.require) {
    $('#fallbackEditor').style.display = 'block';
    $('#fallbackEditor').addEventListener('input', scheduleSave);
    return;
  }
  window.require.config({ paths: { vs: 'https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/vs' } });
  window.require(['vs/editor/editor.main'], () => {
    editor = monaco.editor.create($('#editor'), {
      value: '',
      language: 'javascript',
      theme: 'vs-dark',
      automaticLayout: true,
      fontSize: 13,
      minimap: { enabled: false },
      wordWrap: 'on',
    });
    editor.onDidChangeModelContent(scheduleSave);
    if (project && currentFile) openFile(currentFile, { save: false });
  });
}

function languageFor(file) {
  const extension = file.split('.').pop();
  return ({
    js: 'javascript', mjs: 'javascript', ts: 'typescript', tsx: 'typescript', jsx: 'javascript',
    html: 'html', css: 'css', json: 'json', py: 'python', md: 'markdown',
    yml: 'yaml', yaml: 'yaml', sh: 'shell',
  })[extension] || 'plaintext';
}

function refreshPreview() {
  if (project) $('#preview').src = `/preview/${encodeURIComponent(project.id)}/?t=${Date.now()}`;
}

function switchTab(name) {
  document.querySelectorAll('[data-tab]').forEach(button => button.classList.toggle('active', button.dataset.tab === name));
  document.querySelectorAll('.pane').forEach(pane => pane.classList.remove('active'));
  $(`#${name}Pane`).classList.add('active');
  if (name === 'preview') refreshPreview();
}

document.querySelectorAll('[data-tab]').forEach(button => {
  button.onclick = () => switchTab(button.dataset.tab);
});

$('#newProject').onclick = async () => {
  const name = prompt('Project name?', 'New Grim App');
  if (!name) return;
  const template = prompt('Template: static, node, or python?', 'static') || 'static';
  const created = (await api('/api/projects', {
    method: 'POST',
    body: JSON.stringify({ name, template }),
  })).project;
  await loadProjects();
  await openProject(created.id);
  toast('PROJECT CREATED');
};

$('#newFile').onclick = async () => {
  if (!project) return;
  const file = prompt('File path?', 'src/new.js');
  if (!file) return;
  await api(`/api/projects/${project.id}/file?path=${encodeURIComponent(file)}`, {
    method: 'PUT',
    body: JSON.stringify({ content: '' }),
  });
  project = (await api(`/api/projects/${project.id}`)).project;
  renderFiles();
  await openFile(file, { save: false });
};

$('#checkpoint').onclick = async () => {
  if (!project) return;
  await saveCurrent();
  await api(`/api/projects/${project.id}/checkpoints`, {
    method: 'POST',
    body: JSON.stringify({ label: 'Manual checkpoint' }),
  });
  toast('CHECKPOINT SAVED');
};

$('#runProject').onclick = async () => {
  if (!project) return;
  await saveCurrent();
  try {
    const process = (await api(`/api/projects/${project.id}/start`, { method: 'POST' })).process;
    appendTerm(`\n[process ${process.id}] ${process.command} ${process.args.join(' ')} · port ${process.port}\n`);
    switchTab('preview');
    setTimeout(refreshPreview, 800);
  } catch (error) {
    toast(error.message);
    switchTab('preview');
  }
};

function textFile(path) {
  return !/\.(png|jpe?g|gif|webp|ico|woff2?|ttf|zip|gz|pdf|mp3|wav|mp4|mov)$/i.test(path)
    && !/(^|\/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock)$/i.test(path);
}

async function collectProjectFiles() {
  const files = [];
  let remaining = 15_000;
  for (const path of (project.files || []).filter(textFile).slice(0, 40)) {
    if (remaining <= 0) break;
    try {
      const content = await api(`/api/projects/${project.id}/file?path=${encodeURIComponent(path)}`);
      const selected = String(content).slice(0, Math.min(4_000, remaining));
      files.push({ path, content: selected });
      remaining -= selected.length;
    } catch {
      // Skip unreadable or non-text files.
    }
  }
  return files;
}

async function applyAgentOperations(operations, mode) {
  if ((mode === 'plan' || mode === 'explain') && operations.length) {
    throw new Error(`${mode.toUpperCase()} mode cannot modify files.`);
  }
  if (!operations.length) return;
  await api(`/api/projects/${project.id}/checkpoints`, {
    method: 'POST',
    body: JSON.stringify({ label: `Before GPT Doug ${mode}` }),
  });
  for (const operation of operations) {
    const endpoint = `/api/projects/${project.id}/file?path=${encodeURIComponent(operation.path)}`;
    if (operation.op === 'write_file') {
      await api(endpoint, { method: 'PUT', body: JSON.stringify({ content: operation.content }) });
    } else {
      await api(endpoint, { method: 'DELETE' });
    }
  }
}

async function runGptDoug(promptText, mode) {
  if (!bridge.connected) await connectBridge({ quiet: true });
  const files = await collectProjectFiles();
  const messages = createAgentMessages({ prompt: promptText, mode, files });
  const raw = await chatGptDoug(
    { baseUrl: bridge.baseUrl, token: bridge.token, model: bridge.model },
    messages,
    { projectId: project.id, timeoutMs: 180_000 },
  );
  const result = parseAgentResult(raw.message.content);
  await applyAgentOperations(result.operations, mode);
  return {
    provider: 'gpt-doug-bridge',
    model: bridge.model,
    cached: Boolean(raw.cached),
    ...result,
  };
}

$('#agentRun').onclick = async () => {
  if (!project) return;
  const promptText = $('#agentPrompt').value.trim();
  if (!promptText) return;
  const mode = $('#agentMode').value;
  const provider = $('#agentProvider').value;
  addMsg('you', promptText);
  $('#agentRun').disabled = true;
  $('#agentRun').textContent = provider === 'gpt-doug' ? 'GPT DOUG WORKING…' : 'AGENT WORKING…';
  try {
    await saveCurrent();
    const result = provider === 'gpt-doug'
      ? await runGptDoug(promptText, mode)
      : await api(`/api/projects/${project.id}/agent`, {
          method: 'POST',
          body: JSON.stringify({ prompt: promptText, mode }),
        });
    const engine = [result.provider, result.model, result.cached ? 'cache hit' : 'fresh'].filter(Boolean).join(' · ');
    addMsg('grim', `${result.message}\n${result.operations?.length || 0} file operation(s).${engine ? `\n${engine}` : ''}`);
    project = (await api(`/api/projects/${project.id}`)).project;
    if (!project.files.includes(currentFile)) currentFile = project.files[0] || null;
    renderFiles();
    if (currentFile) await openFile(currentFile, { save: false });
    refreshPreview();
  } catch (error) {
    addMsg('grim', `ERROR: ${error.message}`);
    if (provider === 'gpt-doug') openBridgeSettings();
  } finally {
    $('#agentRun').disabled = false;
    $('#agentRun').textContent = 'RUN AGENT';
  }
};

function addMsg(role, text) {
  const message = document.createElement('div');
  message.className = `msg ${role}`;
  message.innerHTML = `<b>${role === 'you' ? 'YOU' : 'GRIM'}</b><div></div>`;
  message.querySelector('div').textContent = text;
  $('#agentFeed').appendChild(message);
  $('#agentFeed').scrollTop = $('#agentFeed').scrollHeight;
}

function connectTerminal() {
  if (terminalSocket) terminalSocket.close();
  if (!project) return;
  const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
  terminalSocket = new WebSocket(`${protocol}://${location.host}/ws/projects/${encodeURIComponent(project.id)}/terminal`);
  terminalSocket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.type === 'terminal') appendTerm(message.text);
    if (message.type === 'ready') appendTerm(`\n[real shell connected · process ${message.process.id}]\n`);
    if (message.type === 'exit') appendTerm(`\n[process exited ${message.code ?? message.signal}]\n`);
    if (message.type === 'error') appendTerm(`\nERROR ${message.message}\n`);
  };
  terminalSocket.onerror = () => appendTerm('\n[terminal websocket error]\n');
}

function appendTerm(text) {
  $('#term').textContent += text;
  $('#term').scrollTop = $('#term').scrollHeight;
}

$('#termForm').onsubmit = event => {
  event.preventDefault();
  const value = $('#termInput').value;
  if (terminalSocket?.readyState === 1) terminalSocket.send(JSON.stringify({ type: 'stdin', data: `${value}\n` }));
  $('#termInput').value = '';
};

$('#bridgeSettings').onclick = openBridgeSettings;
$('#bridgeQuickConnect').onclick = openBridgeSettings;
$('#bridgeClose').onclick = closeBridgeSettings;
$('#bridgeCancel').onclick = closeBridgeSettings;
$('#bridgeDisconnect').onclick = disconnectBridge;
$('#bridgeConnect').onclick = () => connectBridge().catch(() => {});
$('#bridgeModel').onchange = () => {
  bridge.model = $('#bridgeModel').value;
  localStorage.setItem('grim.gptDoug.model', bridge.model);
  if (bridge.connected) setBridgeStatus('connected', 'GPT DOUG ONLINE', bridge.model);
};
$('#agentProvider').onchange = () => localStorage.setItem('grim.agent.provider', $('#agentProvider').value);
$('#bridgeCopyCommand').onclick = async () => {
  try {
    await navigator.clipboard.writeText($('#bridgeCommand').textContent);
    toast('START COMMAND COPIED');
  } catch {
    toast('COPY FAILED');
  }
};
$('#bridgeModal').onclick = event => {
  if (event.target === $('#bridgeModal')) closeBridgeSettings();
};
window.addEventListener('keydown', event => {
  if (event.key === 'Escape' && !$('#bridgeModal').hidden) closeBridgeSettings();
});
window.addEventListener('beforeunload', () => terminalSocket?.close());

boot();
