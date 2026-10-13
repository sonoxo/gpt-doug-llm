/* GPT-DOUG TAK-OS local-only CoT bridge viewer. No upstream TAK transport. */
(() => {
  'use strict';
  const $ = (s) => document.querySelector(s);
  const base = new URL('./api/v1/', window.location.href);
  const state = { token: '', connected: false, attempts: 0, stream: null, units: new Map(), records: [], health: null, lastEvent: null };
  const safe = (v) => String(v === undefined || v === null ? '' : v).slice(0, 180);

  function appendInterface() {
    const container = document.createElement('section');
    container.className = 'panel padded takos-gateway-panel';
    container.setAttribute('aria-label', 'Local TAK CoT legacy gateway');
    container.innerHTML = `
      <div class="panel-label">END-TO-END LEGACY INTEROPERABILITY / LOCAL ONLY</div>
      <h2>CoT 2.0 Gateway <span id="gateway-badge" class="outlined-badge warn-text">LOCAL GATEWAY OFFLINE</span></h2>
      <p id="gateway-explainer" class="body-copy">The optional Python gateway is offline. Browser simulation remains available without it.</p>
      <div class="gateway-metrics">
        <div><small>TRANSPORT</small><b id="gateway-transport">—</b></div>
        <div><small>CoT EVENTS ACCEPTED</small><b id="gateway-count">0</b></div>
        <div><small>REAL TAK CONNECTION</small><b class="warn-text">OFFLINE / NOT CONFIGURED</b></div>
        <div><small>LEGACY UDP</small><b id="gateway-udp">DISABLED</b></div>
      </div>
      <div class="button-row left gateway-buttons">
        <button id="gateway-retry" class="btn btn-muted">↻ Retry Local Gateway</button>
        <button id="gateway-ingest" class="btn btn-primary" disabled>↧ Ingest XML from Inspector</button>
        <button id="gateway-incident" class="btn btn-muted" disabled>＋ Add Local Drill Incident</button>
        <a id="gateway-export" class="btn btn-muted" href="./api/v1/cot.xml?uid=LAB-RESCUE-01" download="lab-rescue.cot" aria-disabled="true">⇩ Export CoT XML</a>
      </div>
      <p class="notice">Legacy CoT XML is handled only by the locally installed gateway. XML posted from this panel must have a DEMO-/LAB- UID by default. No public TAK Server or government website is contacted.</p>
      <h3>Persistent local event log <small>(SQLite in gateway mode)</small></h3>
      <div id="gateway-records" class="gateway-records" role="log" aria-live="polite"><p>Waiting for local gateway.</p></div>
    `;
    $('#view-feeds').appendChild(container);
    const label = document.createElement('div');
    label.id = 'gateway-map-status'; label.className = 'takos-map-status';
    label.textContent = 'LEGACY CoT: LOCAL GATEWAY OFFLINE';
    $('.map-stage').appendChild(label);
    $('#gateway-retry').addEventListener('click', connect);
    $('#gateway-ingest').addEventListener('click', submitXML);
    $('#gateway-incident').addEventListener('click', newIncident);
  }

  function status(connected, message) {
    state.connected = connected;
    const tag = $('#gateway-badge');
    if (!tag) return;
    tag.textContent = connected ? 'LOCAL LAB CONNECTED' : 'LOCAL GATEWAY OFFLINE';
    tag.className = connected ? 'outlined-badge ok-text' : 'outlined-badge warn-text';
    $('#gateway-map-status').textContent = connected ? 'CoT 2.0 LAB • LOCAL SSE CONNECTED • NOT REAL TAK' : 'CoT LAB OFFLINE • BROWSER DEMO ONLY';
    $('#gateway-explainer').textContent = message;
    $('#gateway-ingest').disabled = !connected;
    $('#gateway-incident').disabled = !connected;
    $('#gateway-export').setAttribute('aria-disabled', String(!connected));
    $('#gateway-export').tabIndex = connected ? 0 : -1;
    window.TAKOSApp?.setGatewayConnection?.(connected);
  }

  function showHealth(health) {
    state.health = health;
    $('#gateway-transport').textContent = safe(health.transport);
    $('#gateway-count').textContent = safe(health.acceptedCoT);
    $('#gateway-udp').textContent = health.udpLoopbackPort ? '127.0.0.1:' + health.udpLoopbackPort : 'DISABLED';
  }

  function ingestFrame(frame) {
    if (!frame || !Array.isArray(frame.units)) return;
    const units = frame.units.filter((u) => u && typeof u.id === 'string' && Number.isFinite(Number(u.lat)) && Number.isFinite(Number(u.lon)));
    units.forEach((u) => state.units.set(u.id, u));
    window.TAKOSApp?.setGatewayUnits?.(Array.from(state.units.values()));
    if (Array.isArray(frame.events)) {
      state.records = frame.events;
      renderRecords();
    }
  }

  function addCot(unit) {
    if (!unit || typeof unit.id !== 'string') return;
    state.units.set(unit.id, unit);
    window.TAKOSApp?.setGatewayUnits?.(Array.from(state.units.values()));
  }

  function renderRecords() {
    const list = $('#gateway-records');
    list.replaceChildren();
    state.records.slice(0, 18).forEach((r) => {
      const row = document.createElement('div'); row.className = 'gateway-record';
      const text = document.createElement('span');
      const heading = document.createElement('strong'); heading.textContent = safe(r.kind).toUpperCase() + ' · ' + safe(r.uid || r.detail);
      const detail = document.createElement('small'); detail.textContent = safe(r.ts) + ' · ' + safe(r.source) + ' · ' + (r.synthetic ? 'SYNTHETIC' : 'UNVERIFIED');
      text.append(heading, detail); row.appendChild(text);
      if (r.kind === 'incident') {
        const b = document.createElement('button'); b.className = 'tiny-button'; b.textContent = r.acknowledged ? '✓ ACKED' : 'ACK'; b.disabled = !!r.acknowledged;
        b.addEventListener('click', () => ack(r.id)); row.appendChild(b);
      }
      list.appendChild(row);
    });
    if (!state.records.length) list.textContent = 'No events recorded yet.';
  }

  async function api(endpoint, method = 'GET', body = null, mime = 'application/json') {
    const opts = {method, cache:'no-store', headers:{'Accept':'application/json'}};
    if (method !== 'GET') {
      opts.headers['Content-Type'] = mime;
      opts.headers['X-TAK-OS-Token'] = state.token;
      opts.body = body;
    }
    const response = await fetch(new URL(endpoint, base), opts);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || 'HTTP ' + response.status);
    return data;
  }

  async function submitXML() {
    if (!state.connected || !state.token) return;
    const xml = $('#cot-input').value;
    try {
      const result = await api('cot','POST',xml,'application/xml');
      $('#cot-output').textContent = 'LOCALLY ACCEPTED by CoT gateway: ' + safe(result.unit.id) + '\nSQLite event persisted. No real TAK endpoint contacted.';
      addCot(result.unit);
      await refreshRecords();
    } catch (error) { $('#cot-output').textContent = 'GATEWAY REJECTED: ' + safe(error.message); }
  }
  async function newIncident() {
    try {await api('incident','POST',JSON.stringify({title:'Synthetic local CoT exercise alert'})); await refreshRecords();}
    catch (error) { status(false, 'Incident call failed: ' + safe(error.message)); }
  }
  async function ack(id) {
    try { await api('ack','POST',JSON.stringify({id})); await refreshRecords(); }
    catch (error) { status(false, 'ACK call failed: ' + safe(error.message)); }
  }
  async function refreshRecords() {
    const obj = await api('events'); state.records = obj.events || []; renderRecords();
  }

  async function connect() {
    if (state.stream) { state.stream.close(); state.stream = null; }
    if (window.location.protocol === 'file:') return status(false, 'Static file mode: gateway requires python3 gateway.py and localhost HTTP.');
    try {
      const info = await api('session');
      if (info.mode !== 'synthetic-lab' || typeof info.csrfToken !== 'string') throw Error('unexpected service');
      state.token = info.csrfToken;
      showHealth(info);
      const initial = await api('snapshot'); ingestFrame(initial);
      status(true, 'Local Python gateway with SQLite, CoT XML and Server-Sent Events. External TAK: not connected.');
      const stream = new EventSource(new URL('stream', base)); state.stream = stream;
      stream.addEventListener('snapshot', (e) => { try { ingestFrame(JSON.parse(e.data)); } catch (_) {} });
      stream.addEventListener('telemetry', (e) => { try { ingestFrame(JSON.parse(e.data)); } catch (_) {} });
      stream.addEventListener('cot', (e) => { try { addCot(JSON.parse(e.data)); } catch (_) {} });
      stream.addEventListener('record', (e) => { try { const r = JSON.parse(e.data); state.records.unshift(r); state.records=state.records.slice(0,30); renderRecords(); } catch (_) {} });
      stream.addEventListener('ack', (e) => { try { const r=JSON.parse(e.data); const item=state.records.find(x=>x.id===r.id); if(item)item.acknowledged=true; renderRecords(); } catch(_) {} });
      stream.onerror = () => { status(false,'SSE reconnecting. Browser simulator remains available; verify local gateway.'); };
      stream.onopen = () => { status(true,'Local gateway streaming live synthetic telemetry via SSE; external TAK remains offline.'); };
    } catch (_) {
      state.token = '';
      status(false, 'Gateway unavailable. Start with: sh start.sh web. Static GitHub Pages runs the browser simulation without a backend.');
    }
  }

  function boot() {
    if (!$('#view-feeds') || !$('.map-stage')) return;
    appendInterface();
    connect();
    // Keep the static Pages experience responsive; retry is optional and not aggressive.
    window.addEventListener('online', () => { if (!state.connected) connect(); });
  }
  document.addEventListener('DOMContentLoaded', boot);
})();