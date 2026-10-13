/* GPT-DOUG × GPT-CHAOS local defensive swarm. No external model or TAK API. */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const base = new URL('./api/v1/', window.location.href);
  const offlineRoles = [
    ['gpt-doug-planner', 'Reasoning plan / schema'],
    ['gpt-chaos-critic', 'Adversarial consistency checks'],
    ['zyra-guardian', 'Boundaries / execution policy'],
    ['ontology-verifier', 'Typed entity contract'],
    ['provenance-sentinel', 'Source and synthetic attribution'],
    ['pulse-watchdog', 'Heartbeat and resource budgets'],
  ];
  const session = { token: '', connected: false, busy: false, view: null, audit: null, lastError: '' };

  async function request(endpoint, data) {
    const opts = { method:data === undefined ? 'GET' : 'POST', cache:'no-store', headers:{'Accept':'application/json'} };
    if (data !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.headers['X-TAK-OS-Token'] = session.token;
      opts.body = JSON.stringify(data);
    }
    const response = await fetch(new URL(endpoint, base), opts);
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(String(body.error || `HTTP ${response.status}`).slice(0, 180));
    return body;
  }

  function clear(el) { el.replaceChildren(); }
  function textEl(tag, className, value) {
    const el = document.createElement(tag);
    if (className) el.className = className;
    el.textContent = String(value ?? '');
    return el;
  }
  function feedback(message, failed = false) {
    const el = $('#swarm-feedback'); if (!el) return;
    el.textContent = message;
    el.style.color = failed ? '#ffbc95' : '#93e0c8';
  }
  function roles(data) {
    const parent = $('#swarm-agents'); clear(parent);
    const agents = Array.isArray(data?.agents) ? data.agents : offlineRoles.map(([id,role]) => ({id,role,status:'OFFLINE'}));
    for (const agent of agents) {
      const row = textEl('div', 'swarm-agent', '');
      const meta = document.createElement('span');
      meta.append(textEl('strong', '', String(agent.id).slice(0, 70)), textEl('small', '', String(agent.role).slice(0, 120)));
      const status = textEl('em', '', agent.status || 'OFFLINE');
      row.append(meta, status); parent.append(row);
    }
  }
  function proposals(data) {
    const parent = $('#swarm-proposals'); clear(parent);
    const records = Array.isArray(data?.proposals) ? data.proposals : [];
    if (!records.length) { parent.append(textEl('p','body-copy','No pending or historical proposals. Start the swarm to evaluate a synthetic candidate.')); return; }
    for (const proposal of records) {
      const row = textEl('article', 'swarm-proposal' + (proposal.risk === 'high' ? ' high' : '') + (proposal.status !== 'pending_review' ? ' reviewed' : ''), '');
      const c = proposal.candidate || {};
      row.append(textEl('strong','',`#${proposal.id} · ${String(c.id || 'UNKNOWN').slice(0,80)}`));
      row.append(textEl('small','',`${proposal.status} · ${proposal.risk} risk · ${proposal.created || ''}`));
      row.append(textEl('small','',`${c.type || ''} · ${c.lat}, ${c.lon} · ${String(c.label || '').slice(0,80)}`));
      const votes = textEl('div','swarm-votes','');
      for (const vote of (Array.isArray(proposal.votes) ? proposal.votes : [])) {
        const item = textEl('span', 'swarm-vote' + (vote.verdict === 'REVIEW' ? ' review' : ''), `${vote.agent}: ${vote.verdict}`);
        item.title = String(vote.reason || '').slice(0,160);
        votes.append(item);
      }
      row.append(votes);
      if (proposal.status === 'pending_review' && session.view?.mode === 'running') {
        const controls = textEl('div','swarm-review-controls','');
        const reject = textEl('button','btn btn-muted','✕ REJECT');
        reject.addEventListener('click', () => review(proposal.id, 'reject'));
        controls.append(reject);
        const approve = textEl('button','btn btn-primary','✓ APPROVE LAB CHANGE');
        approve.disabled = proposal.risk !== 'low' || session.view.integrity !== 'VERIFIED';
        approve.title = approve.disabled ? 'High-risk proposals cannot be promoted by one local operator' : 'Requires typed human confirmation';
        approve.addEventListener('click', () => review(proposal.id,'approve'));
        controls.append(approve); row.append(controls);
      }
      parent.append(row);
    }
  }
  function ledger(audit) {
    const box = $('#swarm-audit'); clear(box);
    const entries = Array.isArray(audit?.events) ? audit.events : [];
    if (!entries.length) { box.append(textEl('p','body-copy','No local audit events.')); return; }
    for (const event of entries.slice(0, 20)) {
      const row = textEl('div','swarm-audit-entry','');
      row.append(textEl('strong','',`${event.action} · #${event.seq}`));
      row.append(textEl('small','',`${event.ts} · SHA-256 ${String(event.hash).slice(0,32)}…`));
      const summary = event.data && typeof event.data === 'object' ? JSON.stringify(event.data) : '';
      row.append(textEl('small','',summary.slice(0,260)));
      box.append(row);
    }
  }
  function render(data, audit) {
    session.view = data;
    session.audit = audit;
    session.connected = true;
    const mode = String(data.mode || 'OFFLINE').toUpperCase();
    const integrity = String(data.integrity || 'UNKNOWN');
    $('#swarm-stat-mode').textContent = mode;
    $('#swarm-stat-agents').textContent = Array.isArray(data.agents) ? String(data.agents.length) : '6';
    $('#swarm-stat-pending').textContent = String(data.pending ?? 0);
    $('#swarm-stat-integrity').textContent = integrity;
    $('#swarm-mode-pill').textContent = `LOCAL SWARM / ${mode}`;
    $('#swarm-nav-badge').textContent = mode;
    const localModel = data.optionalLocalModel || {};
    const llmLine = localModel.configured
      ? `Optional localhost LLM: ${localModel.lastResponseVerified ? 'last advisory received' : 'configured / not verified'}. No execution authority.`
      : 'LLM adapter: disabled (six deterministic reviewers).';
    $('#swarm-status-text').textContent = `Local ${mode.toLowerCase()} · ${data.pulses || 0} bounded watchdog checks · real TAK offline. ${llmLine} ${integrity === 'VERIFIED' ? 'Audit hash chain verified.' : 'AUDIT FAILED: new work locked.'}`;
    const active = integrity === 'VERIFIED';
    $('#swarm-start').disabled = !active || mode !== 'PAUSED' || session.busy;
    $('#swarm-pause').disabled = !active || mode !== 'RUNNING' || session.busy;
    $('#swarm-stop').disabled = mode === 'STOPPED' || session.busy;
    $('#swarm-rearm').disabled = !active || mode !== 'STOPPED' || session.busy;
    $('#swarm-evaluate').disabled = !active || mode !== 'RUNNING' || session.busy;
    $('#swarm-export').disabled = !audit;
    const budget = data.budget || {};
    $('#swarm-budget').textContent = `Budget: ${budget.remaining ?? 0}/${budget.evaluationsPerMinute ?? 30} evaluations remaining this minute · ${data.pending ?? 0}/${budget.maxPending ?? 64} pending. No outside actions.`;
    roles(data); proposals(data); ledger(audit);
  }
  function offline(message = 'Start the Python CoT gateway locally with: sh start.sh web') {
    session.connected = false; session.token = ''; session.view = null; session.audit = null;
    $('#swarm-stat-mode').textContent = 'OFFLINE';
    $('#swarm-stat-pending').textContent = '0';
    $('#swarm-stat-integrity').textContent = 'OFFLINE';
    $('#swarm-mode-pill').textContent = 'LOCAL SWARM / OFFLINE';
    $('#swarm-nav-badge').textContent = 'OFFLINE';
    $('#swarm-status-text').textContent = message;
    ['swarm-start','swarm-pause','swarm-stop','swarm-rearm','swarm-evaluate','swarm-export'].forEach(id => { $('#' + id).disabled = true; });
    roles(null); proposals(null); ledger(null);
  }
  async function refresh() {
    if (session.busy || window.location.protocol === 'file:') { if (window.location.protocol === 'file:') offline(); return; }
    try {
      if (!session.token) {
        const server = await request('session');
        if (server.mode !== 'synthetic-lab' || typeof server.csrfToken !== 'string') throw new Error('not a local synthetic gateway');
        session.token = server.csrfToken;
      }
      const [view, audit] = await Promise.all([request('swarm'), request('swarm/audit')]);
      render(view, audit);
      session.lastError = '';
    } catch (error) {
      session.lastError = String(error.message || 'gateway offline').slice(0,160);
      offline('Swarm service offline; static browser simulator remains available. ' + session.lastError);
    }
  }
  async function send(path, body, success) {
    if (session.busy || !session.connected || !session.token) return;
    session.busy = true;
    try {
      await request(path, body);
      feedback(success);
    } catch (error) {
      feedback('REJECTED / ' + String(error.message).slice(0,180), true);
    } finally {
      session.busy = false;
      await refresh();
    }
  }
  function control(action, confirmation = '') {
    if (action === 'stop' && !window.confirm('STOP THE KRAKEN: persistently stop all local swarm evaluations? Existing browser simulation will continue.')) return;
    return send('swarm/control', {action, confirmation}, `Swarm ${action} command processed locally`);
  }
  async function evaluateCandidate() {
    let candidate;
    try {
      if ($('#swarm-candidate').value.length > 2048) throw new Error('input is too large');
      candidate = JSON.parse($('#swarm-candidate').value);
    } catch (error) { return feedback('Invalid candidate JSON: ' + String(error.message).slice(0,100), true); }
    return send('swarm/evaluate', {candidate}, 'Six bounded reviewers evaluated the synthetic proposal. Human decision required.');
  }
  function review(id, decision) {
    let confirmation = '';
    if (decision === 'approve') {
      const response = window.prompt(`Only a low-risk synthetic proposal can update the local lab map. Type APPROVE SYNTHETIC PROPOSAL to approve #${id}:`, '');
      if (response === null) return;
      confirmation = response;
    } else if (!window.confirm(`Reject synthetic proposal #${id}? This does not change the map.`)) return;
    return send('swarm/review', {id,decision,confirmation}, `Human ${decision} decision stored in local audit chain`);
  }
  function downloadAudit() {
    if (!session.audit) return;
    const payload = JSON.stringify({mode:session.view?.mode, status:session.audit.integrity, source:'local-synthetic-rule-based-swarm', ...session.audit},null,2);
    const object = URL.createObjectURL(new Blob([payload], {type:'application/json'}));
    const link = document.createElement('a'); link.href = object; link.download = 'gpt-chaos-local-audit.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(object), 3000);
  }
  function boot() {
    if (!$('#view-swarm')) return;
    offline('Connecting to optional free local swarm gateway…');
    $('#swarm-start').addEventListener('click', () => control('start'));
    $('#swarm-pause').addEventListener('click', () => control('pause'));
    $('#swarm-stop').addEventListener('click', () => control('stop'));
    $('#swarm-rearm').addEventListener('click', () => control('rearm', $('#swarm-rearm-phrase').value));
    $('#swarm-evaluate').addEventListener('click', evaluateCandidate);
    $('#swarm-refresh').addEventListener('click', refresh);
    $('#swarm-export').addEventListener('click', downloadAudit);
    document.querySelector('[data-view="swarm"]')?.addEventListener('click', refresh);
    refresh();
    setInterval(() => { if (document.visibilityState === 'visible' && !session.busy) refresh(); }, 6000);
  }
  // Same-origin, public app-shell cache only. No CoT/telemetry or OSM tiles cached.
  if ('serviceWorker' in navigator && location.protocol !== 'file:') {
    window.addEventListener('load', () => {
      navigator.serviceWorker.register('./sw.js').catch(() => {});
    });
  }
  document.addEventListener('DOMContentLoaded', boot);
})();
