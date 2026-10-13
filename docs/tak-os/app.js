/* GPT-DOUG TAK-OS - independent, free, synthetic-data-only civilian demo.
 * No external telemetry, credential collection, remote CoT ingestion or privileged controls.
 */
(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const $$ = (selector) => Array.from(document.querySelectorAll(selector));
  const storageKey = 'gpt-doug-tak-os-demo-v1';
  const symbols = { ground: '◇', air: '✦', sensor: '◎', maritime: '≈' };
  const types = { ground: 'Ground Response', air: 'Air Observation', sensor: 'Environment Sensor', maritime: 'Marine Observation' };
  const seed = [
    { id: 'CIV-RESCUE-01', type: 'ground', lat: 37.5391, lon: -77.4360, status: 'EN ROUTE', label: 'Richmond staging' },
    { id: 'CIV-RESCUE-02', type: 'ground', lat: 37.5943, lon: -77.4907, status: 'AVAILABLE', label: 'West Richmond district' },
    { id: 'CIV-MED-03', type: 'ground', lat: 37.3339, lon: -77.4439, status: 'EN ROUTE', label: 'Chesterfield exercise' },
    { id: 'CIV-UTIL-04', type: 'ground', lat: 37.7232, lon: -77.1900, status: 'AVAILABLE', label: 'Ashland utilities' },
    { id: 'CIV-OPS-05', type: 'ground', lat: 38.3032, lon: -77.4605, status: 'AVAILABLE', label: 'Fredericksburg exercise' },
    { id: 'CIV-OPS-06', type: 'ground', lat: 36.8529, lon: -76.2859, status: 'EN ROUTE', label: 'Norfolk exercise' },
    { id: 'OBS-AIR-07', type: 'air', lat: 37.4499, lon: -77.3196, status: 'OBSERVING', label: 'Aerial weather observation' },
    { id: 'OBS-AIR-08', type: 'air', lat: 38.0107, lon: -78.4523, status: 'OBSERVING', label: 'Charlottesville observation' },
    { id: 'MET-SENSOR-09', type: 'sensor', lat: 37.8906, lon: -76.3117, status: 'SAMPLING', label: 'Northern Neck weather' },
    { id: 'MET-SENSOR-10', type: 'sensor', lat: 36.7422, lon: -77.9202, status: 'SAMPLING', label: 'Southern region weather' },
    { id: 'SEA-OBS-11', type: 'maritime', lat: 37.0028, lon: -76.3200, status: 'OBSERVING', label: 'Hampton Roads weather buoy' },
    { id: 'SEA-OBS-12', type: 'maritime', lat: 37.1858, lon: -76.1911, status: 'OBSERVING', label: 'Chesapeake synthetic track' },
  ];
  const cities = [
    { name: 'RICHMOND', lat: 37.541, lon: -77.436, main: true },
    { name: 'FREDERICKSBURG', lat: 38.303, lon: -77.46 },
    { name: 'CHARLOTTESVILLE', lat: 38.03, lon: -78.48 },
    { name: 'NORFOLK', lat: 36.85, lon: -76.29 },
    { name: 'WILLIAMSBURG', lat: 37.27, lon: -76.71 },
    { name: 'PETERSBURG', lat: 37.23, lon: -77.4 },
    { name: 'WASHINGTON, DC', lat: 38.907, lon: -77.036 },
    { name: 'RALEIGH', lat: 35.78, lon: -78.64 },
  ];
  const tabs = ['map', 'system', 'feeds', 'events', 'ontology', 'swarm', 'settings'];
  let local = {};
  try { local = JSON.parse(localStorage.getItem(storageKey) || '{}') || {}; } catch (_) { local = {}; }
  const preferences = {
    tiles: local.tiles !== false,
    trails: local.trails !== false,
    zone: local.zone !== false,
    motion: !!local.motion,
  };
  const state = {
    units: [], gatewayUnits: [], gatewayConnected: false, events: [], annotations: Array.isArray(local.annotations) ? local.annotations.filter((p) => Number.isFinite(p.lat) && Number.isFinite(p.lon)).slice(0, 40) : [],
    selected: 'CIV-RESCUE-01', running: true, speed: 1, tick: 0, packets: 0, latency: 42,
    search: '', filter: 'all', view: 'map', center: { lat: 37.75, lon: -77.27 }, zoom: 8, selectedType: null,
    drag: null, moved: false, toastTimer: null, refreshN: 0,
  };
  const uuid = (prefix) => `${prefix}-${String(state.tick).padStart(4, '0')}-${String(state.events.length + 1).padStart(2, '0')}`;
  function saveLocal() {
    try { localStorage.setItem(storageKey, JSON.stringify({ ...preferences, annotations: state.annotations })); } catch (_) { /* file/privacy mode */ }
  }
  function toast(message) {
    const element = $('#toast'); element.textContent = message; element.classList.add('show');
    clearTimeout(state.toastTimer); state.toastTimer = setTimeout(() => element.classList.remove('show'), 2900);
  }
  function readableTime(iso) { return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }); }
  function timestamp() { return new Date().toISOString(); }
  function escapeHTML(v) { return String(v ?? '').replace(/[&<>"']/g, x => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[x])); }
  function makeEvent(type, title, description, incident = false) {
    const event = { id: uuid('EVT'), type, title, description, ts: timestamp(), synthetic: true, acknowledged: !incident };
    state.events.unshift(event); state.events = state.events.slice(0, 100);
    return event;
  }
  function resetScenario({ keepPrefs = true } = {}) {
    state.units = seed.map((p, index) => ({ ...p, idx: index, baseLat: p.lat, baseLon: p.lon, history: [[p.lat, p.lon]] }));
    state.events = []; state.selected = seed[0].id; state.running = true; state.tick = 0; state.speed = 1;
    state.packets = 0; state.latency = 42;
    makeEvent('system', 'Simulator initialized', 'A local, deterministic synthetic asset generator is running.');
    makeEvent('activity', 'Civilian exercise network ready', '12 fictional assets are mapped; no actual tracking or third-party telemetry.');
    makeEvent('incident', 'Weather drill: visibility advisory', 'Synthetic low-visibility event in the Richmond exercise area.', true);
    if (!keepPrefs) state.annotations = [];
    $('#speed-select').value = '1';
    syncControls(); renderAll(); saveLocal();
  }
  function advance() {
    if (!state.running) return;
    state.tick += state.speed; state.packets += 3 * state.speed + state.units.length;
    state.latency = Math.round(40 + 11 * Math.sin(state.tick / 5) + 5 * Math.sin(state.tick / 11));
    state.units.forEach((unit) => {
      const i = unit.idx; const phase = state.tick * 0.036 * (unit.type === 'air' ? 2.5 : 1) + i * 1.4;
      const radius = unit.type === 'air' ? 0.038 : unit.type === 'ground' ? 0.014 : unit.type === 'maritime' ? 0.011 : 0;
      unit.lat = unit.baseLat + Math.sin(phase) * radius;
      unit.lon = unit.baseLon + Math.cos(phase * 0.87) * radius * 1.4;
      if (state.tick % 2 === 0) {
        unit.history.push([unit.lat, unit.lon]); if (unit.history.length > 28) unit.history.shift();
      }
    });
    if (state.tick % 12 === 0) {
      const unit = state.units[(state.tick / 12) % state.units.length];
      makeEvent('activity', `${unit.id} position sample`, `Synthetic status ${unit.status.toLowerCase()} recorded by local simulator.`);
    }
    if (state.tick % 45 === 0) makeEvent('system', 'Heartbeat sample validated', 'Browser generator clock and synthetic positions checked.');
    renderAll();
  }
  function syncControls() {
    $('#sim-play').textContent = state.running ? 'Ⅱ Pause' : '▶ Resume';
    $('#sim-run-state').textContent = state.running ? 'SIMULATION RUNNING' : 'SIMULATION PAUSED';
    $('#footer-tick').textContent = `T+${String(state.tick).padStart(4, '0')}`;
    $('#sim-run-state').style.color = state.running ? '#82edc8' : '#ffbc62';
  }
  function renderStats() {
    $('#stat-units').textContent = state.units.length + state.gatewayUnits.length;
    $('#stat-packets').textContent = state.packets.toLocaleString();
    $('#stat-latency').textContent = state.latency;
    const open = state.events.filter((e) => e.type === 'incident' && !e.acknowledged).length;
    $('#stat-alerts').textContent = open; $('#nav-alert-count').textContent = open;
    if (state.tick % 4 !== 0 && state.tick !== 0) return;
    ['spark-a', 'spark-b', 'spark-c', 'spark-d'].forEach((id, i) => {
      const values = Array.from({ length: 20 }, (_, k) => {
        const base = 12 + i * 5;
        return base + 12 * Math.sin((k + state.tick * 0.1) * .62 + i) + 5 * Math.sin(k * 1.55 + i);
      });
      const points = values.map((v, k) => `${k * 5.2},${40 - v}`).join(' ');
      $('#' + id).innerHTML = `<svg viewBox="0 0 100 34" preserveAspectRatio="none" aria-hidden="true"><polyline points="${points}" stroke="${i === 3 ? '#ffb967' : '#3ee7d5'}" stroke-width="2.5" fill="none"/></svg>`;
    });
  }
  function navigate(view) {
    if (!tabs.includes(view)) return;
    state.view = view;
    $$('.view').forEach((node) => node.classList.toggle('active', node.id === `view-${view}`));
    $$('.nav-link').forEach((node) => {
      const selected = node.dataset.view === view;
      node.classList.toggle('active', selected);
      if (selected) node.setAttribute('aria-current', 'page'); else node.removeAttribute('aria-current');
    });
    $('#breadcrumb-view').textContent = ({map:'LIVE OPERATIONS',system:'SYSTEM / VM',feeds:'DATA FEEDS',events:'EVENT TIMELINE',ontology:'ONTOLOGY',swarm:'DEFENSIVE SWARM',settings:'SETTINGS'})[view];
    $('.sidebar').classList.remove('open'); $('#mobile-menu').setAttribute('aria-expanded', 'false');
    if (view === 'map') { requestAnimationFrame(() => { renderTiles(); renderMap(); }); }
    if (view === 'events') renderEvents();
    if (view === 'ontology') renderOntology();
    if (view === 'feeds') renderFeeds();
  }
  function mercator(lat, lon, zoom) {
    const scale = 256 * Math.pow(2, zoom);
    const rad = Math.max(-85.0511, Math.min(85.0511, lat)) * Math.PI / 180;
    return { x: (lon + 180) / 360 * scale, y: (1 - Math.log(Math.tan(rad) + 1 / Math.cos(rad)) / Math.PI) / 2 * scale };
  }
  function unmercator(x, y, zoom) {
    const scale = 256 * Math.pow(2, zoom);
    return { lon: x / scale * 360 - 180, lat: (180 / Math.PI) * Math.atan(Math.sinh(Math.PI * (1 - 2 * y / scale))) };
  }
  function size() { return { width: $('#map-stage').clientWidth, height: $('#map-stage').clientHeight }; }
  function project(lat, lon) {
    const { width, height } = size(); const p = mercator(lat, lon, state.zoom); const c = mercator(state.center.lat, state.center.lon, state.zoom);
    return { x: p.x - c.x + width / 2, y: p.y - c.y + height / 2 };
  }
  function unproject(x, y) {
    const c = mercator(state.center.lat, state.center.lon, state.zoom); const { width, height } = size();
    return unmercator(c.x + x - width / 2, c.y + y - height / 2, state.zoom);
  }
  function setMapCenter(point) {
    state.center = { lat: Math.max(-82, Math.min(82, point.lat)), lon: ((point.lon + 540) % 360) - 180 };
    renderTiles(); renderMap();
  }
  function setZoom(zoom) { state.zoom = Math.max(5, Math.min(13, zoom)); renderTiles(); renderMap(); }
  function renderTiles() {
    const layer = $('#map-tiles'); layer.replaceChildren();
    const { width, height } = size(); if (!width || !height) return;
    $('#map-mode-label').textContent = preferences.tiles ? 'VECTOR + OSM TILES' : 'OFFLINE VECTOR GRID';
    if (!preferences.tiles) return;
    const center = mercator(state.center.lat, state.center.lon, state.zoom);
    const minX = Math.floor((center.x - width / 2) / 256);
    const maxX = Math.floor((center.x + width / 2) / 256);
    const minY = Math.floor((center.y - height / 2) / 256);
    const maxY = Math.floor((center.y + height / 2) / 256);
    const count = 2 ** state.zoom;
    for (let x = minX; x <= maxX; x++) for (let y = minY; y <= maxY; y++) {
      if (y < 0 || y >= count) continue;
      const img = document.createElement('img');
      img.alt = ''; img.draggable = false; img.loading = 'eager';
      img.style.left = `${x * 256 - center.x + width / 2}px`;
      img.style.top = `${y * 256 - center.y + height / 2}px`;
      img.src = `https://tile.openstreetmap.org/${state.zoom}/${((x % count) + count) % count}/${y}.png`;
      img.onerror = () => { img.style.display = 'none'; };
      layer.appendChild(img);
    }
  }
  function addSvg(tag, properties, parent) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(properties)) node.setAttribute(key, String(value));
    parent.appendChild(node); return node;
  }
  function visibleUnit(unit) {
    const matched = unit.id.toLowerCase().includes(state.search.toLowerCase()) || unit.label.toLowerCase().includes(state.search.toLowerCase());
    return matched && (state.filter === 'all' || state.filter === unit.type);
  }
  function renderMap() {
    const { width, height } = size(); if (!width || !height) return;
    const markerLayer = $('#map-markers'); markerLayer.replaceChildren();
    const svg = $('#map-overlay'); svg.setAttribute('viewBox', `0 0 ${width} ${height}`); svg.replaceChildren();
    const cityLayer = $('#map-cities'); cityLayer.replaceChildren();
    cities.forEach((city) => {
      const p = project(city.lat, city.lon); if (p.x < -20 || p.x > width + 20 || p.y < -20 || p.y > height + 20) return;
      const div = document.createElement('div'); div.className = `city-label ${city.main ? 'main' : ''}`;
      div.style.left = `${p.x}px`; div.style.top = `${p.y}px`; div.textContent = city.name; cityLayer.appendChild(div);
    });
    if (preferences.zone) {
      const point = project(37.5407, -77.4360); const outer = project(37.5407 + 0.24, -77.4360);
      const radius = Math.abs(outer.y - point.y);
      addSvg('circle', { cx: point.x, cy: point.y, r: radius, fill: '#4af0df', 'fill-opacity': .035, stroke: '#39dec7', 'stroke-width': 1.5, 'stroke-dasharray': '6 6', 'stroke-opacity': .7 }, svg);
      addSvg('circle', { cx: point.x, cy: point.y, r: 3, fill: '#86fcdf' }, svg);
    }
    [...state.units,...state.gatewayUnits].filter(visibleUnit).forEach((unit) => {
      if (preferences.trails && unit.history.length > 1) {
        const pts = unit.history.map(([lat, lon]) => { const p = project(lat, lon); return `${p.x.toFixed(1)},${p.y.toFixed(1)}`; }).join(' ');
        addSvg('polyline', { points: pts, fill: 'none', stroke: unit.type === 'air' ? '#b28aff' : unit.type === 'maritime' ? '#ffbc62' : '#39d9d2', 'stroke-width': 1.6, 'stroke-opacity': .55, 'stroke-dasharray': '4 5' }, svg);
      }
      const p = project(unit.lat, unit.lon); if (p.x < -30 || p.y < -30 || p.x > width + 30 || p.y > height + 30) return;
      const button = document.createElement('button');
      button.className = `marker ${unit.type}${state.selected === unit.id ? ' selected' : ''}`;
      button.style.left = `${p.x}px`; button.style.top = `${p.y}px`; button.title = `${unit.synthetic === false ? 'UNVERIFIED LAB' : 'SYNTHETIC'} ${unit.id}`; button.setAttribute('aria-label', `Inspect lab asset ${unit.id}`);
      const glyph = document.createElement('span'); glyph.className = 'marker-symbol'; glyph.textContent = symbols[unit.type];
      const title = document.createElement('span'); title.className = 'marker-call'; title.textContent = unit.id;
      button.append(glyph, title);
      button.addEventListener('click', (e) => { e.stopPropagation(); state.selected = unit.id; renderMap(); renderInspector(); });
      markerLayer.appendChild(button);
    });
    state.annotations.forEach((annotation) => {
      const p = project(annotation.lat, annotation.lon); if (p.x < -20 || p.x > width + 20 || p.y < -20 || p.y > height + 20) return;
      const button = document.createElement('button'); button.className = 'marker sensor';
      button.style.left = `${p.x}px`; button.style.top = `${p.y}px`;
      button.title = 'Click to remove local annotation'; button.setAttribute('aria-label', `Remove local annotation ${annotation.id}`);
      const icon = document.createElement('span'); icon.className = 'marker-symbol'; icon.textContent = '✚';
      const label = document.createElement('span'); label.className = 'marker-call'; label.textContent = annotation.id;
      button.append(icon, label); button.addEventListener('click', (e) => {
        e.stopPropagation(); state.annotations = state.annotations.filter((a) => a !== annotation); saveLocal(); renderMap(); toast('Local annotation removed');
      }); markerLayer.appendChild(button);
    });
    $('#map-coordinates').textContent = `${Math.abs(state.center.lat).toFixed(3)}° ${state.center.lat >= 0 ? 'N' : 'S'} · ${Math.abs(state.center.lon).toFixed(3)}° ${state.center.lon >= 0 ? 'E' : 'W'} · Z${state.zoom}`;
  }
  function renderInspector() {
    const unit = [...state.units,...state.gatewayUnits].find((p) => p.id === state.selected) || state.units[0];
    const inspector = $('#asset-inspector'); if (!unit) return;
    const age = state.tick ? `T+${state.tick}` : 'T+0';
    const safeType = ['ground','air','sensor','maritime'].includes(unit.type) ? unit.type : 'ground';
    const source = escapeHTML(unit.source || 'LOCAL GENERATOR');
    const claim = unit.synthetic === false ? 'UNVERIFIED / LAB' : 'SYNTHETIC';
    inspector.innerHTML = `<div class="asset-top"><span class="asset-avatar">${symbols[safeType]}</span><span><b>${escapeHTML(unit.id)}</b><small>${types[safeType]} · ${claim}</small></span></div>
      <div class="inspector-desc">${escapeHTML(unit.label)} — ${unit.synthetic === false ? 'unverified local CoT input; not an authoritative track.' : 'synthetic laboratory data only.'}</div>
      <div class="inspector-grid"><div class="inspector-cell"><small>LAB STATUS</small><strong>${escapeHTML(unit.status)}</strong></div><div class="inspector-cell"><small>PROVENANCE</small><strong>${source}</strong></div><div class="inspector-cell"><small>LATITUDE</small><strong>${unit.lat.toFixed(5)}</strong></div><div class="inspector-cell"><small>LONGITUDE</small><strong>${unit.lon.toFixed(5)}</strong></div><div class="inspector-cell"><small>TRACK POINTS</small><strong>${unit.history.length}</strong></div><div class="inspector-cell"><small>UPDATE</small><strong>${escapeHTML(unit.timestamp || age)}</strong></div></div>`;
  }
  function renderRecentEvents() {
    const layer = $('#recent-events'); layer.replaceChildren();
    state.events.slice(0, 4).forEach((event) => {
      const item = document.createElement('div'); item.className = 'stream-item';
      const badge = document.createElement('div'); badge.className = `stream-icon ${event.type}`; badge.textContent = event.type === 'incident' ? '!' : event.type === 'system' ? '⌘' : '↗';
      const info = document.createElement('div'); const title = document.createElement('b'); title.textContent = event.title;
      const note = document.createElement('small'); note.textContent = `${readableTime(event.ts)} · SIMULATED`;
      info.append(title, note); item.append(badge, info); layer.appendChild(item);
    });
  }
  function renderTopology() {
    const nodes = [['▣', 'Browser VM Console', 'RUNNING / DEMO', false], ['⊙', 'Python + SQLite', state.gatewayConnected ? 'LOCAL / ONLINE' : 'OPTIONAL / OFFLINE', !state.gatewayConnected], ['⌁', 'CoT 2.0 Gateway', state.gatewayConnected ? 'SYNTHETIC / LOCAL' : 'OFFLINE', !state.gatewayConnected], ['◉', 'Map + Event View', 'ACTIVE / DEMO', false]];
    $('#topology').replaceChildren(...nodes.flatMap(([icon, title, stateText, offline], i) => {
      const item = document.createElement('div'); item.className = 'topology-item';
      const orb = document.createElement('span'); orb.className = `topology-node${offline ? ' offline' : ''}`; orb.textContent = icon;
      const text = document.createElement('span'); text.className = 'topology-label';
      const name = document.createElement('b'); name.textContent = title;
      const status = document.createElement('small'); status.className = offline ? 'offline' : ''; status.textContent = stateText;
      text.append(name, status); item.append(orb, text);
      if (i === nodes.length - 1) return [item];
      const edge = document.createElement('div'); edge.className = 'topology-edge'; return [item, edge];
    }));
  }
  function renderEvents() {
    const view = $('#event-filter').value;
    const onlyUnacked = $('#event-unacked').checked;
    const events = state.events.filter((e) => (view === 'all' || e.type === view) && (!onlyUnacked || !e.acknowledged));
    $('#event-count').textContent = `${events.length} records · synthetic`;
    const layer = $('#events-list'); layer.replaceChildren();
    if (!events.length) { const p = document.createElement('p'); p.className = 'body-copy'; p.textContent = 'No matching events.'; layer.appendChild(p); return; }
    events.forEach((event) => {
      const row = document.createElement('div'); row.className = 'timeline-item';
      const dot = document.createElement('span'); dot.className = `timeline-dot ${event.type}`;
      const body = document.createElement('div'); body.className = 'timeline-detail';
      const title = document.createElement('b'); title.textContent = event.title;
      const description = document.createElement('p'); description.textContent = event.description;
      const sub = document.createElement('small'); sub.textContent = `${event.ts} · ${event.type.toUpperCase()} · SYNTHETIC · ${event.id}`;
      body.append(title, description, sub); row.append(dot, body);
      if (event.type === 'incident') {
        const ack = document.createElement('button'); ack.className = 'timeline-ack';
        ack.textContent = event.acknowledged ? '✓ ACKED' : 'ACK EVENT'; ack.disabled = event.acknowledged;
        ack.addEventListener('click', () => { event.acknowledged = true; toast('Simulated incident acknowledged'); renderStats(); renderEvents(); });
        row.appendChild(ack);
      }
      layer.appendChild(row);
    });
  }
  function renderFeeds() {
    const cards = [
      ['◇','Ground telemetry','Local deterministic trajectories', 'SIMULATED · ACTIVE', false],
      ['✦','Aerial observations','Animated synthetic aerial tracks', 'SIMULATED · ACTIVE', false],
      ['◎','Weather stations','Static synthetic weather nodes', 'SIMULATED · ACTIVE', false],
      ['≋','TAK / CoT external','Reserved for authorized gateway', 'REAL INTERFACE · OFFLINE', true],
    ];
    $('#feed-cards').replaceChildren(...cards.map(([icon, title, description, status, offline]) => {
      const card = document.createElement('article'); card.className = 'feed-card';
      const symbol = document.createElement('div'); symbol.className = 'feed-glyph'; symbol.textContent = icon;
      const h3 = document.createElement('h3'); h3.textContent = title;
      const desc = document.createElement('p'); desc.textContent = description;
      const badge = document.createElement('div'); badge.className = `feed-status${offline ? ' offline' : ''}`; badge.textContent = `● ${status}`;
      card.append(symbol, h3, desc, badge); return card;
    }));
  }
  function renderOntology() {
    const container = $('#ontology-list'); container.replaceChildren();
    const data = [
      ['Simulator', 'Source', 'Deterministic browser engine'],
      ['ResponseUnit', `${state.units.filter((x) => x.type === 'ground').length} entities`, 'Synthetic geospatial assets'],
      ['ObservationAircraft', `${state.units.filter((x) => x.type === 'air').length} entities`, 'Synthetic flight tracks'],
      ['WeatherSensor', `${state.units.filter((x) => x.type === 'sensor').length} entities`, 'Synthetic environmental nodes'],
      ['MarineObservation', `${state.units.filter((x) => x.type === 'maritime').length} entities`, 'Synthetic maritime tracks'],
      ['ScenarioEvent', `${state.events.length} entities`, 'Browser-generated event records'],
      ['UserAnnotation', `${state.annotations.length} entities`, 'Browser-local, deletable'],
      ['LocalCoTGateway', `${state.gatewayUnits.length} entities`, state.gatewayConnected ? 'Local SSE and SQLite CoT lab' : 'Offline (browser only)'],
      ['RealCoTConnection', '0 entities', 'No authorized external endpoint connected'],
    ];
    data.forEach(([name, count, provenance]) => {
      const row = document.createElement('div'); row.className = 'ontology-entry';
      const main = document.createElement('div'); const title = document.createElement('b'); title.textContent = name;
      const sub = document.createElement('small'); sub.textContent = provenance; main.append(title, sub);
      const status = document.createElement('span'); status.textContent = count;
      row.append(main, status); container.appendChild(row);
    });
  }
  function renderAll() {
    renderStats(); renderInspector(); renderRecentEvents(); syncControls();
    if (state.view === 'map') renderMap();
    if (state.view === 'events') renderEvents();
    if (state.view === 'ontology') renderOntology();
  }
  const demoCot = `<event version="2.0" uid="DEMO-CIV-RESCUE-01" type="a-f-G-U-C" how="m-g" time="2026-10-13T13:00:00Z" start="2026-10-13T13:00:00Z" stale="2026-10-13T13:01:00Z">
  <point lat="37.5407" lon="-77.4360" hae="0" ce="25" le="25" />
  <detail><contact callsign="DEMO-RESCUE-01" /></detail>
</event>`;
  function validateCot() {
    const input = $('#cot-input').value; const out = $('#cot-output');
    if (!input.trim() || input.length > 16000) { out.textContent = 'Invalid: XML required, 16,000 characters maximum.'; return; }
    if (/<!\s*(?:DOCTYPE|ENTITY)/i.test(input)) { out.textContent = 'Rejected: DTD and entity declarations are disabled in this demo.'; return; }
    let doc;
    try { doc = new DOMParser().parseFromString(input, 'application/xml'); }
    catch (_) { out.textContent = 'Invalid XML.'; return; }
    if (doc.querySelector('parsererror') || doc.documentElement.localName !== 'event') {
      out.textContent = 'Invalid: expected a well-formed CoT <event> root element.'; return;
    }
    const root = doc.documentElement, point = root.querySelector('point');
    if (!point) { out.textContent = 'Invalid: CoT <point> element missing.'; return; }
    const lat = Number(point.getAttribute('lat')), lon = Number(point.getAttribute('lon'));
    if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180 || point.getAttribute('lat') === null || point.getAttribute('lon') === null) {
      out.textContent = 'Invalid: point latitude / longitude are missing or outside geographic bounds.'; return;
    }
    if (!root.getAttribute('uid') || !root.getAttribute('type') || !root.getAttribute('time')) {
      out.textContent = 'Invalid: uid, type and time are required attributes.'; return;
    }
    out.textContent = `VALID LOCAL XML EXAMPLE\nUID: ${root.getAttribute('uid').slice(0, 120)}\nTYPE: ${root.getAttribute('type').slice(0, 120)}\nPOINT: ${lat.toFixed(5)}, ${lon.toFixed(5)}\nThis parser does NOT transmit data, authenticate or connect to a TAK server.`;
  }
  async function copyText(text, success) {
    try {
      if (navigator.clipboard && window.isSecureContext) await navigator.clipboard.writeText(text);
      else {
        const area = document.createElement('textarea'); area.value = text; area.style.position = 'fixed'; area.style.left = '-1000px';
        document.body.appendChild(area); area.select(); const copied = document.execCommand('copy'); area.remove();
        if (!copied) throw new Error('clipboard unavailable');
      }
      toast(success);
    } catch (_) { toast('Clipboard unavailable: use the project README for launch commands'); }
  }
  function download(name, content, contentType = 'application/json') {
    const file = new Blob([content], { type: contentType }); const url = URL.createObjectURL(file);
    const link = document.createElement('a'); link.href = url; link.download = name; document.body.appendChild(link); link.click(); link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1200);
    toast(`Created ${name} locally`);
  }
  function snapshot() { return { generatedAt: timestamp(), source: 'synthetic browser simulator', simulationTick: state.tick, disclaimer: 'Independent demonstration; synthetic data only; not TAK Product Center software.', units: state.units.map(({ id, type, lat, lon, status, history }) => ({ id, type, lat, lon, status, history })), events: state.events, annotations: state.annotations }; }
  function vmCommand() {
    const cpu = Number($('#vm-cpus').value), mem = Number($('#vm-memory').value), disk = Number($('#vm-disk').value), port = Number($('#vm-port').value);
    const safePort = Number.isInteger(port) && port >= 1024 && port <= 65535 ? port : 8080;
    return `# Run locally after installing QEMU and downloading an authorized Ubuntu ISO.\n# Review configuration and update ISO filename before running.\nqemu-img create -f qcow2 tak-os-ubuntu.qcow2 ${disk}G\nqemu-system-x86_64 -accel kvm -smp ${cpu} -m ${mem} -drive file=tak-os-ubuntu.qcow2,if=virtio -cdrom ubuntu-24.04.3-live-server-amd64.iso -boot d -nic user,hostfwd=tcp:127.0.0.1:${safePort}-:8080\n# On macOS, replace '-accel kvm' with '-accel hvf' where supported.\n# This command installs Ubuntu only; deploy the included docker compose service inside the VM.`;
  }
  function csvEvents() {
    const cols = ['id','type','title','description','ts','synthetic','acknowledged'];
    return [cols.join(','), ...state.events.map((row) => cols.map((key) => `"${String(row[key] ?? '').replace(/"/g, '""')}"`).join(','))].join('\n');
  }
  function bind() {
    $$('.nav-link').forEach((button) => button.addEventListener('click', () => navigate(button.dataset.view)));
    $$('[data-go]').forEach((button) => button.addEventListener('click', () => navigate(button.dataset.go)));
    $('#mobile-menu').addEventListener('click', () => {
      const shown = $('.sidebar').classList.toggle('open'); $('#mobile-menu').setAttribute('aria-expanded', String(shown));
    });
    $('#sim-play').addEventListener('click', () => { state.running = !state.running; syncControls(); toast(state.running ? 'Demo simulation resumed' : 'Demo simulation paused'); });
    $('#speed-select').addEventListener('change', (event) => { state.speed = Number(event.target.value); toast(`Simulation speed set to ${state.speed}×`); });
    $('#reset-map').addEventListener('click', () => { resetScenario(); toast('Synthetic scenario reset'); });
    $('#map-center').addEventListener('click', () => setMapCenter({ lat: 37.75, lon: -77.27 }));
    $('#zoom-in').addEventListener('click', () => setZoom(state.zoom + 1));
    $('#zoom-out').addEventListener('click', () => setZoom(state.zoom - 1));
    $('#unit-search').addEventListener('input', (event) => { state.search = event.target.value.trim(); renderMap(); });
    $('#type-filter').addEventListener('change', (event) => { state.filter = event.target.value; renderMap(); });
    [['toggle-trails','trails','settings-trails'],['toggle-geofence','zone','settings-zone'],['toggle-tiles','tiles','settings-tiles']].forEach(([mapId, pref, settingsId]) => {
      const change = (event, other) => { preferences[pref] = event.target.checked; $(`#${other}`).checked = preferences[pref]; saveLocal(); renderTiles(); renderMap(); };
      $('#' + mapId).addEventListener('change', (e) => change(e, settingsId));
      $('#' + settingsId).addEventListener('change', (e) => change(e, mapId));
    });
    $('#settings-motion').addEventListener('change', (event) => { preferences.motion = event.target.checked; document.body.classList.toggle('reduced-motion', preferences.motion); saveLocal(); });
    $('#export-map').addEventListener('click', () => download('tak-os-synthetic-scenario.json', JSON.stringify(snapshot(), null, 2)));
    $('#settings-export').addEventListener('click', () => download('tak-os-synthetic-scenario.json', JSON.stringify(snapshot(), null, 2)));
    $('#settings-clear').addEventListener('click', () => { resetScenario({ keepPrefs: false }); toast('Local scenario and annotations reset'); });
    $('#export-events').addEventListener('click', () => download('tak-os-events.csv', csvEvents(), 'text/csv;charset=utf-8'));
    $('#create-incident').addEventListener('click', () => { makeEvent('incident', 'Operator-generated drill incident', 'Locally created synthetic incident requiring acknowledgment.', true); renderAll(); toast('Simulated incident recorded'); });
    $('#event-filter').addEventListener('change', renderEvents);
    $('#event-unacked').addEventListener('change', renderEvents);
    $('#export-ontology').addEventListener('click', () => download('tak-os-ontology-demo.json', JSON.stringify({ types: ['ResponseUnit','ObservationAircraft','WeatherSensor','MarineObservation','ScenarioEvent','UserAnnotation'], provenance: 'local synthetic demo', ...snapshot() }, null, 2)));
    $('#cot-input').value = demoCot;
    $('#cot-validate').addEventListener('click', validateCot);
    $('#cot-reset').addEventListener('click', () => { $('#cot-input').value = demoCot; $('#cot-output').textContent = 'Sample reset. Select Validate XML.'; });
    $('#cot-mock').addEventListener('click', () => { makeEvent('activity', 'Mock CoT event parsed', 'Generated synthetic local-only event; external adapter remains OFFLINE.'); renderAll(); toast('Mock event generated locally'); });
    $('#copy-vm').addEventListener('click', () => copyText(vmCommand(), 'QEMU example configuration copied'));
    $('#copy-compose').addEventListener('click', () => copyText('docker compose up -d', 'Local Docker Compose command copied'));
    $('#quick-help').addEventListener('click', () => $('#help-dialog').showModal());
    $('#close-help').addEventListener('click', () => $('#help-dialog').close());
    $('#help-done').addEventListener('click', () => $('#help-dialog').close());
    const stage = $('#map-stage');
    stage.addEventListener('pointerdown', (event) => {
      if (event.target.closest('button,a')) return;
      state.drag = { x: event.clientX, y: event.clientY, lat: state.center.lat, lon: state.center.lon, origin: mercator(state.center.lat, state.center.lon, state.zoom) };
      state.moved = false; stage.classList.add('dragging'); stage.setPointerCapture(event.pointerId);
    });
    stage.addEventListener('pointermove', (event) => {
      if (!state.drag) return;
      const deltaX = event.clientX - state.drag.x, deltaY = event.clientY - state.drag.y;
      if (Math.hypot(deltaX, deltaY) > 6) state.moved = true;
      if (state.moved) {
        const center = unmercator(state.drag.origin.x - deltaX, state.drag.origin.y - deltaY, state.zoom);
        setMapCenter(center);
      }
    });
    stage.addEventListener('pointerup', (event) => {
      if (!state.drag) return;
      if (!state.moved && !event.target.closest('button,a')) {
        const bounds = stage.getBoundingClientRect(); const coordinate = unproject(event.clientX - bounds.left, event.clientY - bounds.top);
        if (state.annotations.length >= 40) toast('Maximum 40 local annotations; remove a pin first');
        else {
          const id = `NOTE-${String(state.annotations.length + 1).padStart(2, '0')}`;
          state.annotations.push({ id, lat: coordinate.lat, lon: coordinate.lon, synthetic: true }); saveLocal(); renderMap(); toast('Local annotation added; click its marker to remove it');
        }
      }
      state.drag = null; stage.classList.remove('dragging');
      if (stage.hasPointerCapture(event.pointerId)) stage.releasePointerCapture(event.pointerId);
    });
    stage.addEventListener('pointercancel', () => { state.drag = null; stage.classList.remove('dragging'); });
    stage.addEventListener('wheel', (event) => { event.preventDefault(); setZoom(state.zoom + (event.deltaY < 0 ? 1 : -1)); }, { passive: false });
    document.addEventListener('keydown', (event) => {
      if (event.target.matches('input,textarea,select') || $('#help-dialog').open || event.ctrlKey || event.metaKey || event.altKey) return;
      if (/^[1-7]$/.test(event.key)) navigate(tabs[Number(event.key) - 1]);
      if (event.code === 'Space') { event.preventDefault(); $('#sim-play').click(); }
      if (event.key === '+' || event.key === '=') setZoom(state.zoom + 1);
      if (event.key === '-') setZoom(state.zoom - 1);
    });
    window.addEventListener('resize', () => { if (state.view === 'map') { renderTiles(); renderMap(); } });
  }
  // The only intentional integration boundary for the optional, same-origin
  // CoT/SSE lab service. Static GitHub Pages continues to work without it.
  window.TAKOSApp = Object.freeze({
    setGatewayConnection(connected) {
      state.gatewayConnected = !!connected;
      renderTopology();
      const local = $('#vm-gateway-local-state');
      if (local) { local.textContent = connected ? 'LOCAL SSE ONLINE' : 'NOT STARTED'; local.className = connected ? 'ok-text' : 'warn-text'; }
    },
    setGatewayUnits(raw) {
      if (!Array.isArray(raw)) return;
      state.gatewayUnits = raw.slice(0, 50).flatMap((unit) => {
        if (!unit || typeof unit.id !== 'string' || !/^[A-Za-z0-9_.:@/-]{1,128}$/.test(unit.id)) return [];
        const lat = Number(unit.lat), lon = Number(unit.lon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon) || Math.abs(lat) > 90 || Math.abs(lon) > 180) return [];
        const type = ['ground','air','sensor','maritime'].includes(unit.type) ? unit.type : 'ground';
        const history = Array.isArray(unit.history) ? unit.history.slice(-30).filter(pair => Array.isArray(pair) && pair.length === 2 && pair.every(Number.isFinite)) : [];
        return [{
          id: unit.id, type, lat, lon, label: String(unit.label || unit.id).slice(0,80),
          status: String(unit.status || 'LOCAL CoT').slice(0,70),
          timestamp: String(unit.timestamp || '').slice(0,60),
          source: String(unit.source || 'LOCAL GATEWAY').slice(0,55),
          synthetic: unit.synthetic === true, history,
        }];
      });
      renderAll();
      renderTopology();
    },
  });
  function startClock() {
    const draw = () => { $('#utc-clock').textContent = new Date().toISOString().slice(11, 19) + ' UTC'; };
    draw(); setInterval(draw, 1000); setInterval(advance, 1200);
  }
  function init() {
    Object.entries({ 'toggle-trails': 'trails', 'toggle-geofence': 'zone', 'toggle-tiles': 'tiles', 'settings-trails': 'trails', 'settings-zone': 'zone', 'settings-tiles': 'tiles', 'settings-motion': 'motion' }).forEach(([id, key]) => { $('#' + id).checked = preferences[key]; });
    document.body.classList.toggle('reduced-motion', preferences.motion);
    bind(); renderTopology(); renderFeeds(); resetScenario(); startClock();
    requestAnimationFrame(() => { renderTiles(); renderMap(); });
    if ('ResizeObserver' in window) new ResizeObserver(() => { if (state.view === 'map') { renderTiles(); renderMap(); } }).observe($('#map-stage'));
  }
  document.addEventListener('DOMContentLoaded', init);
})();
