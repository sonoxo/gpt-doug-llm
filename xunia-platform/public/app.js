const $ = (id) => document.getElementById(id);
let selectedAgent = 'xunia-analyst';
let apiToken = sessionStorage.getItem('xuniaApiKey') || '';
$('apiKey').value = apiToken;

async function api(url, options = {}) {
  const headers = new Headers(options.headers || {});
  if (apiToken) headers.set('authorization', `Bearer ${apiToken}`);
  const res = await fetch(url, { ...options, headers });
  const type = res.headers.get('content-type') || '';
  const data = type.includes('application/json') ? await res.json() : await res.text();
  if (!res.ok) throw new Error((data && data.error) || `HTTP ${res.status}`);
  return data;
}

function esc(value) {
  return String(value).replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[ch]));
}

function setView(name) {
  document.querySelectorAll('.view').forEach((el) => el.classList.toggle('active', el.id === name));
  document.querySelectorAll('.nav').forEach((el) => el.classList.toggle('active', el.dataset.view === name));
  $('viewTitle').textContent = name === 'aip' ? 'AIP' : name[0].toUpperCase() + name.slice(1);
}

document.querySelectorAll('.nav').forEach((button) => button.addEventListener('click', () => setView(button.dataset.view)));

async function loadSession() {
  const session = await api('/api/session');
  $('roleStatus').textContent = session.principal ? `ROLE ${session.principal.role.toUpperCase()}` : session.authRequired ? 'AUTH REQUIRED' : 'ROLE DEV';
  if (session.authRequired && !session.principal) {
    $('healthLabel').textContent = 'API key required';
    return false;
  }
  return true;
}

async function loadPlatform() {
  const health = await api('/health');
  $('healthLabel').textContent = health.ok ? 'Platform online' : 'Degraded';
  const connected = await loadSession();
  if (!connected) return;
  const [status, ontology, agents, tools, audit] = await Promise.all([
    api('/api/platform/status'), api('/api/ontology'), api('/api/aip/agents'), api('/api/aip/tools'), api('/api/aip/audit')
  ]);
  $('objectCount').textContent = health.ontologyObjects;
  $('agentCount').textContent = health.agents;
  $('toolCount').textContent = health.tools;
  $('auditCount').textContent = audit.records.length;
  $('auditIntegrity').textContent = audit.integrity?.ok ? 'INTEGRITY OK' : 'INTEGRITY ALERT';
  $('modelStatus').textContent = `MODEL ${status.integrations.modelGateway.toUpperCase()}`;
  $('moduleList').innerHTML = status.modules.map((module) => `<div><span class="dot"></span><b>${esc(module)}</b><small>ready</small></div>`).join('');
  $('integrationList').innerHTML = Object.entries(status.integrations).map(([key, value]) => `<div><span>${esc(key)}</span><code>${esc(value)}</code></div>`).join('');
  $('runtimeStatus').textContent = JSON.stringify(status, null, 2);
  renderOntology(ontology);
  renderAgents(agents.agents, tools.tools);
  renderAudit(audit.records);
}

function renderOntology(data) {
  $('ontologyObjectCount').textContent = data.objects.length;
  $('ontologyLinkCount').textContent = data.links.length;
  $('objects').innerHTML = data.objects.map((object) => `
    <button class="object-card" data-object-id="${esc(object.id)}">
      <span class="object-type">${esc(object.type)}</span>
      <strong>${esc(object.id)}</strong>
      <small>${esc(JSON.stringify(object.properties))}</small>
    </button>`).join('') || '<p class="muted">No objects.</p>';
  $('links').innerHTML = data.links.map((link) => `
    <div class="link-card"><b>${esc(link.from)}</b><span>${esc(link.type)}</span><b>${esc(link.to)}</b></div>`).join('') || '<p class="muted">No links.</p>';
  document.querySelectorAll('.object-card').forEach((el) => el.addEventListener('click', () => {
    setView('aip');
    $('prompt').value = `Analyze ${el.dataset.objectId} and its connected ontology context.`;
  }));
}

function renderAgents(agents, tools) {
  $('agents').innerHTML = agents.map((agent) => `
    <button class="agent-card ${agent.id === selectedAgent ? 'selected' : ''}" data-agent="${esc(agent.id)}">
      <strong>${esc(agent.name)}</strong><small>${esc(agent.id)}</small><span>${agent.tools.length} tools</span>
    </button>`).join('');
  document.querySelectorAll('.agent-card').forEach((el) => el.addEventListener('click', () => {
    selectedAgent = el.dataset.agent;
    $('selectedAgentLabel').textContent = selectedAgent;
    renderAgents(agents, tools);
  }));
  $('tools').innerHTML = tools.map((tool) => `<div class="tool"><b>${esc(tool.name)}</b><span class="risk ${tool.risk}">${esc(tool.risk)}</span><small>${esc(tool.description)}</small></div>`).join('');
}

function addMessage(role, text) {
  const div = document.createElement('div');
  div.className = `message ${role}`;
  div.innerHTML = `<span>${role === 'user' ? 'YOU' : 'AIP'}</span><p>${esc(text)}</p>`;
  $('messages').appendChild(div);
  $('messages').scrollTop = $('messages').scrollHeight;
}

function renderPlan(run) {
  $('plan').innerHTML = run.steps.map((step, index) => `
    <div class="step">
      <div class="step-index">${index + 1}</div>
      <div><strong>${esc(step.tool)}</strong><p>${esc(step.reason)}</p><span class="status ${step.status}">${esc(step.status)}</span></div>
      ${step.status === 'approval_required' ? `<button class="approve" data-step="${esc(step.id)}">Approve</button>` : ''}
    </div>`).join('') || '<p class="muted">No tool steps proposed.</p>';
  document.querySelectorAll('.approve').forEach((button) => button.addEventListener('click', async () => {
    button.disabled = true;
    try {
      const result = await api(`/api/aip/runs/${encodeURIComponent(run.id)}/approve/${encodeURIComponent(button.dataset.step)}`, { method: 'POST' });
      renderPlan(result.run);
      await refreshAudit();
    } catch (error) {
      addMessage('assistant', `Approval failed: ${error.message}`);
    }
  }));
}

async function runAgent() {
  const message = $('prompt').value.trim();
  if (!message) return;
  addMessage('user', message);
  $('prompt').value = '';
  $('runAgent').disabled = true;
  try {
    const result = await api('/api/aip/run', {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ agentId: selectedAgent, message, contextIds: [] })
    });
    addMessage('assistant', result.run.response);
    renderPlan(result.run);
    await refreshAudit();
  } catch (error) {
    addMessage('assistant', `Run failed: ${error.message}`);
  } finally {
    $('runAgent').disabled = false;
  }
}

async function searchOntology() {
  const q = $('ontologyQuery').value;
  const result = await api(`/api/ontology/search?q=${encodeURIComponent(q)}`);
  const full = await api('/api/ontology');
  renderOntology({ objects: result.objects, links: full.links });
}

async function refreshAudit() {
  const result = await api('/api/aip/audit');
  $('auditCount').textContent = result.records.length;
  $('auditIntegrity').textContent = result.integrity?.ok ? 'INTEGRITY OK' : 'INTEGRITY ALERT';
  renderAudit(result.records);
}

function renderAudit(records) {
  $('auditRows').innerHTML = records.map((record) => `
    <div class="audit-row"><time>${esc(new Date(record.at).toLocaleString())}</time><b>${esc(record.event)}</b><code>${esc(record.runId.slice(0, 8))}</code><span>${esc(record.actor || 'system')} · ${esc(JSON.stringify(record.details))}</span></div>`).join('') || '<p class="muted">No audit events yet.</p>';
}

$('connect').addEventListener('click', async () => {
  apiToken = $('apiKey').value.trim();
  if (apiToken) sessionStorage.setItem('xuniaApiKey', apiToken); else sessionStorage.removeItem('xuniaApiKey');
  try { await loadPlatform(); } catch (error) { $('healthLabel').textContent = error.message; }
});
$('runAgent').addEventListener('click', runAgent);
$('prompt').addEventListener('keydown', (event) => { if ((event.metaKey || event.ctrlKey) && event.key === 'Enter') runAgent(); });
$('ontologySearch').addEventListener('click', searchOntology);
$('refresh').addEventListener('click', () => loadPlatform().catch((error) => { $('healthLabel').textContent = error.message; }));

loadPlatform().catch((error) => {
  $('healthLabel').textContent = error.message === 'authentication_required' ? 'API key required' : 'Connection failed';
  console.error(error);
});
